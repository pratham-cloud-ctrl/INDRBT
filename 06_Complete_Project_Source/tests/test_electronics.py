"""Regress evidence freshness and regulator energy accounting without KiCad."""

import importlib.util
import json
from pathlib import Path
import shutil
import sys

import pytest


ELECTRONICS = Path(__file__).resolve().parents[1] / "electronics"


def load_electronics(name):
    # These runnable electronics scripts also import their sibling modules.
    sys.path.insert(0, str(ELECTRONICS))
    try:
        spec = importlib.util.spec_from_file_location(name, ELECTRONICS / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


@pytest.fixture
def evidence_copy(tmp_path):
    target = tmp_path / "electronics"
    shutil.copytree(
        ELECTRONICS,
        target,
        ignore=shutil.ignore_patterns("exports", "fabrication", "__pycache__", "*.kicad_prl"),
    )
    return target


def test_offline_pcb_rejects_removed_route_with_old_clean_drc(evidence_copy, monkeypatch):
    verifier = load_electronics("verify_pcb")
    monkeypatch.setattr(verifier, "ROOT", evidence_copy)
    assert verifier.verify()["status"] == "PASS"
    board_path = evidence_copy / "joint_interface.kicad_pcb"
    board = verifier.parse(board_path.read_text(encoding="utf-8"))
    removed = [
        item for item in verifier.nodes(board, "segment") if verifier.net_name(item) == "/+5V_IN"
    ]
    assert removed
    for segment in removed:
        board.remove(segment)
    # This preserves the old clean DRC JSON and all pin-net assignments. Only
    # physical routing changed, which the old offline check failed to notice.
    from generate_interface import dumps

    board_path.write_text(dumps(board) + "\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="Stale native PCB evidence.*kicad_pcb"):
        verifier.verify()


def test_offline_pcb_rejects_incomplete_source_binding(evidence_copy, monkeypatch):
    verifier = load_electronics("verify_pcb")
    monkeypatch.setattr(verifier, "ROOT", evidence_copy)
    path = evidence_copy / "pcb_verification.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["source_sha256"] = {}
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(AssertionError, match="binding is incomplete"):
        verifier.verify()


def test_native_runner_does_not_use_previous_manifest_and_rejects_nonzero_exit(
    evidence_copy, monkeypatch
):
    runner = load_electronics("run_pcb_checks")
    monkeypatch.setattr(runner, "ROOT", evidence_copy)
    native_calls, verification_modes = [], []

    def failed_native(cli, arguments, log, require_success=True):
        native_calls.append(arguments)
        log.append({"command": ["<kicad-cli>", *arguments], "exit_code": 5})
        return 5

    def inspect_fresh_report(*, fresh_native_report=False):
        verification_modes.append(fresh_native_report)
        return {"status": "PASS"}

    monkeypatch.setattr(runner, "command", failed_native)
    monkeypatch.setattr(runner, "verify", inspect_fresh_report)
    with pytest.raises(RuntimeError, match="PCB DRC"):
        runner.check_board("unused-native-executable", render=False)
    assert verification_modes == [True]
    assert len(native_calls) == 1, "A failed native DRC must stop before fabrication exports"
    assert "--exit-code-violations" in native_calls[0]
    assert "--schematic-parity" in native_calls[0]
    result = json.loads((evidence_copy / "pcb_verification.json").read_text(encoding="utf-8"))
    assert result["status"] == "FAIL" and result["native_drc_exit_code"] == 5


def test_ldo_heat_accounts_for_all_input_power():
    analysis = load_electronics("interface_analysis")
    assumptions = json.loads((ELECTRONICS / "electrical_assumptions.json").read_text())
    result = analysis.calculate()
    vin = assumptions["input_nominal_v"] * (1 + assumptions["input_tolerance_fraction"])
    # Independent input/output energy balance, neglecting upstream drops as
    # stated in the estimate, must include current that does not reach the load.
    supplied = vin * (assumptions["logic_budget_a"] + assumptions["ldo_max_quiescent_a"])
    delivered = assumptions["logic_nominal_v"] * assumptions["logic_budget_a"]
    assert result["ldo_conservative_dissipation_bound_w"] == pytest.approx(supplied - delivered)


def test_ldo_heat_is_not_zero_when_output_is_unloaded(evidence_copy, monkeypatch):
    analysis = load_electronics("interface_analysis")
    monkeypatch.setattr(analysis, "ROOT", evidence_copy)
    path = evidence_copy / "electrical_assumptions.json"
    assumptions = json.loads(path.read_text(encoding="utf-8"))
    assumptions["logic_budget_a"] = 0
    path.write_text(json.dumps(assumptions), encoding="utf-8")
    assert analysis.calculate()["ldo_conservative_dissipation_bound_w"] > 0
