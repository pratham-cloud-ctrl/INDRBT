"""Regression checks for actual false-positive acceptance failures found in review."""

from dataclasses import replace

import numpy as np
import pytest

from scripts.evidence import package_sources, read_json, verify_packaging
from scripts.run_validation import numeric_validation, public_output
from robotarm import RobotArm


def test_numerical_gate_rejects_a_wrong_jacobian(monkeypatch):
    original = RobotArm.jacobian
    monkeypatch.setattr(RobotArm, "jacobian", lambda self, q: original(self, q) + 0.001)
    with pytest.raises(ValueError, match="jacobian_max_abs_error"):
        numeric_validation(trials=1)


def test_numerical_gate_recomputes_pose_instead_of_trusting_reported_residuals(monkeypatch):
    original = RobotArm.solve_ik

    def wrong_solution(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        return replace(result, q=result.q + np.array([0.001, 0, 0, 0, 0, 0]))

    monkeypatch.setattr(RobotArm, "solve_ik", wrong_solution)
    with pytest.raises(ValueError, match="ik_max_position_error_m"):
        numeric_validation(trials=1)


def test_numerical_gate_rejects_nonfinite_results_in_a_later_trial(monkeypatch):
    original = RobotArm.jacobian
    calls = 0

    def nonfinite_second_jacobian(self, q):
        nonlocal calls
        calls += 1
        return original(self, q) if calls == 1 else np.full((6, 6), np.nan)

    monkeypatch.setattr(RobotArm, "jacobian", nonfinite_second_jacobian)
    with pytest.raises(ValueError, match="jacobian_max_abs_error"):
        numeric_validation(trials=2)


def test_packaging_evidence_rejects_changed_or_added_package_modules(tmp_path):
    for name in (
        "src/robotarm/__init__.py",
        "src/robotarm/planning.py",
        "config/robot.yaml",
        "pyproject.toml",
        "setup.py",
        "MANIFEST.in",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original\n", encoding="utf-8")
    report = {"status": "PASS", "source_sha256": package_sources(tmp_path)}
    verify_packaging(tmp_path, report)
    module = tmp_path / "src/robotarm/planning.py"
    module.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        verify_packaging(tmp_path, report)
    module.write_text("original\n", encoding="utf-8")
    (module.parent / "new_module.py").write_text("new\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        verify_packaging(tmp_path, report)


def test_saved_evidence_rejects_nonfinite_json_values_and_float_overflow(tmp_path):
    path = tmp_path / "evidence.json"
    for token in ("NaN", "Infinity", "-Infinity", "1e9999"):
        path.write_text('{"maximum_error": ' + token + "}", encoding="utf-8")
        with pytest.raises(ValueError, match="Non-finite"):
            read_json(path)


def test_diagnostics_remove_account_paths_but_preserve_error_details():
    sample_path = "\\".join(
        ["C:", "Users", "student", "AppData", "FreeCAD", "Mod", "bridge", "Init.py"]
    )
    raw = f"Traceback from {sample_path}: AttributeError GuiUp"
    text = public_output(raw)
    assert "student" not in text and "\\".join(["C:", "Users"]) not in text
    assert "<user-profile>" in text and "AttributeError GuiUp" in text
