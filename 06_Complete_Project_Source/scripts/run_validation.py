"""Execute numerical tests and audit evidence; --full regenerates primary outputs.

PASS means the named digital check executed successfully. PARTIAL entries retain
scope limitations; absence of a tool never becomes a fabricated passing result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from robotarm import RobotArm  # noqa: E402 — repository bootstrap precedes imports
from robotarm.config import load_config  # noqa: E402
from scripts.evidence import read_json, validation_sources, verify_packaging  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_output(text: str) -> str:
    """Keep diagnostics useful without publishing local account/install paths."""
    text = text.replace(str(ROOT), "<repo>").replace(ROOT.as_posix(), "<repo>")
    return re.sub(r"[A-Za-z]:[\\/]Users[\\/][^\\/\r\n\"' ]+", "<user-profile>", text)


def numeric_validation(trials: int = 60) -> dict:
    if not isinstance(trials, int) or trials < 1:
        raise ValueError("Numerical validation needs at least one trial")
    arm = RobotArm()
    rng = np.random.default_rng(1052026)
    margin = 0.06
    qs = rng.uniform(arm.limits[:, 0] + margin, arm.limits[:, 1] - margin, (trials, 6))
    positions, orientations, matrix_errors, jacobian_errors = [], [], [], []
    for q in qs:
        target = arm.fk(q)
        seed = np.clip(q + rng.normal(0, 0.28, 6), arm.limits[:, 0] + 1e-6, arm.limits[:, 1] - 1e-6)
        solution = arm.solve_ik(target, seed)
        arm.check_joints(solution.q)
        position_error, orientation_error = arm.pose_error(solution.q, target)
        positions.append(position_error)
        orientations.append(orientation_error)
        matrix_errors.append(float(np.max(np.abs(arm.fk(solution.q) - target))))
        eps = 1e-6
        numerical = np.zeros((6, 6))
        for j in range(6):
            plus, minus = arm.fk(q + np.eye(6)[j] * eps), arm.fk(q - np.eye(6)[j] * eps)
            numerical[:3, j] = (plus[:3, 3] - minus[:3, 3]) / (2 * eps)
            numerical[3:, j] = Rotation.from_matrix(plus[:3, :3] @ minus[:3, :3].T).as_rotvec() / (
                2 * eps
            )
        jacobian_errors.append(float(np.max(np.abs(numerical - arm.jacobian(q)))))
    g = arm.config["geometry"]
    # Independent planar closed form checks full transform order for q4=q6=0.
    planar_errors = []
    for q in qs:
        q[[3, 5]] = 0
        a, b, c = q[1], q[1] + q[2], q[1] + q[2] + q[4]
        radial = (
            g["upper_arm_length"] * np.cos(a)
            + (g["forearm_length"] + g["wrist_roll_length"]) * np.cos(b)
            + (g["wrist_pitch_length"] + g["tool_length"]) * np.cos(c)
        )
        z = (
            arm.height
            - g["upper_arm_length"] * np.sin(a)
            - (g["forearm_length"] + g["wrist_roll_length"]) * np.sin(b)
            - (g["wrist_pitch_length"] + g["tool_length"]) * np.sin(c)
        )
        expected = [radial * np.cos(q[0]), radial * np.sin(q[0]), z]
        planar_errors.append(float(np.linalg.norm(arm.fk(q)[:3, 3] - expected)))
    measurements = {
        "ik_max_position_error_m": float(np.max(positions)),
        "ik_max_orientation_error_rad": float(np.max(orientations)),
        "ik_max_matrix_error": float(np.max(matrix_errors)),
        "jacobian_max_abs_error": float(np.max(jacobian_errors)),
        "independent_planar_fk_max_error_m": float(np.max(planar_errors)),
    }
    limits = {
        "ik_max_position_error_m": arm.position_tolerance,
        "ik_max_orientation_error_rad": arm.orientation_tolerance,
        "ik_max_matrix_error": max(arm.position_tolerance, arm.orientation_tolerance),
        "jacobian_max_abs_error": 1e-6,
        "independent_planar_fk_max_error_m": 1e-10,
    }
    for name, value in measurements.items():
        if not np.isfinite(value) or value > limits[name]:
            raise ValueError(f"Numerical acceptance failed: {name}={value}, limit={limits[name]}")
    return {
        "status": "VERIFIED DIGITALLY",
        "trials": trials,
        "seed": 1052026,
        "seeds": "Targets sampled within limits; seeds perturbed by Gaussian sigma .28 rad, not copied target joints",
        **measurements,
        "acceptance_limits": limits,
    }


def documentation_check() -> dict:
    required = [
        "README.md",
        "docs/engineering_report.md",
        "docs/validation_matrix.md",
        "docs/01_requirements.md",
        "docs/02_kinematics.md",
        "docs/03_mechanical_analysis.md",
        "docs/04_cad.md",
        "docs/05_electronics.md",
        "docs/component_catalog.md",
        "docs/electronics_components.md",
        "docs/theory_guide.md",
        "docs/project_alignment.md",
        "docs/README.md",
        "docs/cad_tour.md",
        "docs/electronics_tour.md",
        "docs/engineering_walkthrough.md",
        "cad/README.md",
        "electronics/README.md",
        "docs/design_decisions.md",
        "docs/project_journal.md",
        "LICENSE",
        "CITATION.cff",
        "CHANGELOG.md",
    ]
    missing = [p for p in required if not (ROOT / p).is_file()]
    broken = []
    for md in ROOT.rglob("*.md"):
        if any(p in (".venv", "build", ".git") for p in md.parts):
            continue
        for target in re.findall(r"\]\(([^)]+)\)", md.read_text(encoding="utf-8")):
            if re.match(r"(?:https?://|mailto:|#)", target):
                continue
            target = target.split("#")[0].strip("<>")
            if target and not (md.parent / target).exists():
                broken.append(f"{md.relative_to(ROOT)} -> {target}")
    if missing or broken:
        raise ValueError(f"Missing documents: {missing}; broken local links: {broken}")
    return {"required_documents": len(required), "broken_local_links": broken}


def artifacts_check() -> dict:
    c = load_config()
    pcb = read_json(ROOT / "electronics/pcb_verification.json")
    if not (ROOT / "electronics/joint_interface.kicad_pcb").is_file():
        raise ValueError("Native routed PCB is missing")
    for field in ("native_drc_errors", "native_drc_warnings", "unconnected_items"):
        if pcb.get(field) != 0:
            raise ValueError(f"PCB evidence is missing or has unresolved {field}")
    pcb_files = dict(pcb["source_sha256"])
    pcb_files.update(pcb["fabrication_exports"]["file_sha256"])
    pcb_files.update(pcb["review_export_sha256"])
    for name, expected in pcb_files.items():
        if sha256(ROOT / "electronics" / name) != expected:
            raise ValueError(f"PCB source/export evidence is stale: {name}")
    packaging = read_json(ROOT / "results/validation/packaging_validation.json")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    if packaging["status"] != "PASS" or packaging["package_version"] != version:
        raise ValueError("A successful isolated wheel check is required for the current version")
    verify_packaging(ROOT, packaging)
    cad = read_json(ROOT / "results/validation/cad_validation.json")
    if cad["component_count"] < 20 or any(
        not p["valid"] or p["volume_mm3"] <= 0 for p in cad["components"]
    ):
        raise ValueError("CAD components missing/invalid")
    for name, pose in cad["poses"].items():
        np.testing.assert_allclose(pose["q_deg"], c["poses_deg"][name])
        if (
            not pose["step_reimport_valid"]
            or pose["step_volume_relative_error"] > 1e-6
            or pose["max_cad_fk_transform_error"] > 1e-9
        ):
            raise ValueError(f"CAD pose verification failed: {name}")
    if any(check["result"] != "PASS" for check in cad["interference_checks"]):
        raise ValueError("Selected CAD poses still have interference")
    clearance = read_json(ROOT / "results/validation/cad_motion_clearance.json")
    for field in ("robot.yaml", "geometry.py"):
        source = ROOT / (
            "config/robot.yaml" if field == "robot.yaml" else "cad/build123d/geometry.py"
        )
        if clearance["source_sha256"][field] != sha256(source):
            raise ValueError(f"CAD clearance evidence is stale for {field}")
    if (
        clearance["status"] != "PASS"
        or clearance["failures"]
        or clearance["max_all_pair_overlap_mm3"] > 1e-6
        or clearance["trajectory_sha256"]
        != sha256(ROOT / "results/trajectories/pick_place_samples.json")
    ):
        raise ValueError("Trajectory clearance evidence is stale or failed")
    trajectory = read_json(ROOT / "results/trajectories/pick_place_samples.json")
    arm = RobotArm(c)
    q = np.asarray(trajectory["q_rad"])
    for sample in q:
        arm.check_joints(sample)
    computed = np.array([arm.fk(sample)[:3, 3] for sample in q])
    np.testing.assert_allclose(computed, trajectory["tcp_m"], atol=1e-9)
    metrics = read_json(ROOT / "results/trajectories/pick_place_metrics.json")
    if any(
        not 0 <= metrics[name] <= 1.0001
        for name in ("max_velocity_limit_fraction", "max_acceleration_limit_fraction")
    ):
        raise ValueError("Task samples violate configured motion limits")
    mesh = read_json(ROOT / "cad/exports/meshes/assembly_meshes.json")
    if len(mesh["components"]) != cad["component_count"] or mesh["length_unit"] != "mm":
        raise ValueError("CAD twin mesh count or units inconsistent")
    viewer = read_json(ROOT / "results/validation/viewer_validation.json")
    html_hash = hashlib.sha256(
        (ROOT / "simulations/indrbt_twin.html").read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()
    if (
        viewer["html_sha256"] != html_hash
        or viewer["page_errors"]
        or not 0 <= viewer["maximum_js_python_matrix_difference"] <= 1e-9
    ):
        raise ValueError("Retained browser evidence does not match current twin artifact")
    native_review = read_json(ROOT / "results/validation/cad_release_consistency.json")
    if native_review.get("status") != "PASS":
        raise ValueError("Native CAD consistency review did not pass")
    native_sources = native_review.get("source_sha256", {})
    required_sources = {
        "config/robot.yaml",
        "cad/build123d/geometry.py",
        "cad/build123d/assembly.py",
        "cad/build123d/export_all.py",
        "cad/freecad/inspect_step.py",
        "cad/build123d/render_blender.py",
        "cad/build123d/inspect_blender.py",
        "scripts/review_cad.py",
    }
    if not required_sources.issubset(native_sources) or not native_review.get("checked_artifacts"):
        raise ValueError("Native CAD evidence is incomplete")
    for name, expected in native_sources.items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Native CAD source evidence is stale: {name}")
    for artifact in native_review["checked_artifacts"]:
        if sha256(ROOT / artifact["file"]) != artifact["sha256"]:
            raise ValueError(f"Native CAD evidence is stale: {artifact['file']}")
    grip = metrics["gripper"]
    if not np.isclose(grip["opening_m"], c["gripper"]["max_opening"]):
        raise ValueError("Gripper report and configuration inconsistent")
    torque = read_json(ROOT / "results/mechanical/joint_torque.json")
    from analysis.joint_torque_analysis import gravity_torques

    np.testing.assert_allclose(
        torque["extended_gravity_torque_nm"], gravity_torques(arm, np.zeros(6)), atol=1e-8
    )
    return {
        "cad_components": cad["component_count"],
        "task_samples_recomputed": len(q),
        "named_poses": len(cad["poses"]),
        "configuration_sha256": sha256(ROOT / "config/robot.yaml"),
        "pcb_footprints": pcb["footprint_count"],
    }


def run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full", action="store_true", help="Regenerate CAD, all demos and analyses first"
    )
    parser.add_argument("--kicad-cli")
    parser.add_argument(
        "--freecad-cmd", help="FreeCAD console executable for --full native refresh"
    )
    parser.add_argument("--blender", help="Blender executable for --full CAD render/native refresh")
    parser.add_argument("--skip-electronics", action="store_true")
    parser.add_argument(
        "--skip-pcb-render",
        action="store_true",
        help="Retain PCB preview images while executing fresh native electrical/fabrication checks",
    )
    args = parser.parse_args()
    out = ROOT / "results/validation"
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "executed_utc": datetime.now(timezone.utc).isoformat(),
        "project_version": tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
            "version"
        ],
        "project_status": "VALIDATION IN PROGRESS",
        "checks": [],
        "scope_limitations": [
            "Collision evidence is representative and sampled, not a continuous swept collision certificate",
            "Payload and repeatability remain design targets; no physical robot was built",
            "Analytical structure and independent-axis control are the documented educational models",
            "The conceptual PCB has no physical thermal, EMC, ESD or functional-safety validation",
        ],
    }
    initial_sources = validation_sources(ROOT)

    def check(name, action):
        try:
            evidence = action()
            report["checks"].append({"name": name, "result": "PASS", "evidence": evidence})
            print(f"{name:.<42}PASS", flush=True)
        except Exception as exc:
            reason = public_output(str(exc))
            report["checks"].append({"name": name, "result": "FAIL", "reason": reason})
            print(f"{name:.<42}FAIL: {reason}", flush=True)

    def command(argv):
        result = subprocess.run(
            argv, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return {
            "exit_code": result.returncode,
            "output": public_output(result.stdout + result.stderr)[-3000:],
        }

    if args.full:
        check("CAD regeneration", lambda: command([sys.executable, "scripts/generate_cad.py"]))
        check(
            "Results regeneration", lambda: command([sys.executable, "scripts/generate_results.py"])
        )
        refresh = [sys.executable, "scripts/refresh_cad.py"]
        if args.freecad_cmd:
            refresh += ["--freecad-cmd", args.freecad_cmd]
        if args.blender:
            refresh += ["--blender", args.blender]
        check("Native CAD/render/clearance refresh", lambda: command(refresh))
    # Refresh native evidence before tests/offline gates inspect its source hashes.
    if args.skip_electronics:
        report["checks"].append(
            {
                "name": "KiCad ERC / PCB DRC / connectivity",
                "result": "NOT VERIFIED in this run",
                "reason": "Explicitly skipped; retained evidence is in electronics/",
            }
        )
    else:
        argv = [sys.executable, "electronics/run_checks.py"]
        if args.kicad_cli:
            argv += ["--kicad-cli", args.kicad_cli]
        if args.skip_pcb_render:
            argv += ["--skip-pcb-render"]
        check("KiCad ERC / PCB DRC / connectivity", lambda: command(argv))
    with tempfile.TemporaryDirectory(prefix="indrbt-qa-") as temp:
        (out / "pytest.xml").unlink(missing_ok=True)
        check(
            "Automated numerical/CAD tests",
            lambda: command(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    f"--basetemp={temp}/pytest",
                    f"--junitxml={out / 'pytest.xml'}",
                ]
            ),
        )
    check("Configuration validation", lambda: {"name": load_config()["name"]})
    check("FK / IK / Jacobian random trials", lambda: numeric_validation())
    numerical = next(
        (
            c["evidence"]
            for c in report["checks"]
            if c["name"] == "FK / IK / Jacobian random trials" and c["result"] == "PASS"
        ),
        None,
    )
    if numerical:
        (out / "numerical_validation.json").write_text(json.dumps(numerical, indent=2) + "\n")
    check("CAD / task / parameter consistency", artifacts_check)
    check(
        "Code lint",
        lambda: command(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "src",
                "analysis",
                "scripts",
                "tests",
                "cad/build123d",
                "electronics",
            ]
        ),
    )
    # The report is itself a linked deliverable. Write current executed evidence
    # before auditing links, including on the first run without existing outputs.
    (out / "validation_report.md").write_text(
        "# Executed validation report\n\n| Check | Result |\n|---|---|\n"
        + "\n".join(f"| {c['name']} | {c['result']} |" for c in report["checks"])
        + "\n",
        encoding="utf-8",
    )
    check("Documentation links and coverage", documentation_check)

    def source_consistency():
        current_sources = validation_sources(ROOT)
        if current_sources != initial_sources:
            raise ValueError("Engineering sources changed during validation; rerun on one revision")
        return {"files_bound": len(current_sources)}

    check("Validation source revision consistency", source_consistency)
    report["source_sha256"] = initial_sources
    if (out / "pytest.xml").exists():
        junit = ET.parse(out / "pytest.xml")
        suites = junit.getroot()
        for suite in suites.findall("testsuite"):
            suite.attrib.pop("hostname", None)
        junit.write(out / "pytest.xml", encoding="utf-8", xml_declaration=True)
        totals = {
            name: sum(int(s.get(name, 0)) for s in suites.findall("testsuite"))
            for name in ("tests", "failures", "errors", "skipped")
        }
        report["test_totals"] = totals
        if not totals["tests"] or any(totals[name] for name in ("failures", "errors", "skipped")):
            report["checks"].append(
                {
                    "name": "Complete test-suite execution",
                    "result": "FAIL",
                    "reason": "All project tests must execute without failures, errors or skips",
                    "evidence": totals,
                }
            )
    else:
        report["checks"].append(
            {
                "name": "Complete test-suite execution",
                "result": "FAIL",
                "reason": "No JUnit evidence was produced by this run",
            }
        )
    report["configuration_sha256"] = sha256(ROOT / "config/robot.yaml")
    report["project_status"] = (
        "DIGITAL SCOPE COMPLETE"
        if all(c["result"] == "PASS" for c in report["checks"])
        else "VALIDATION FAILED"
        if any(c["result"] == "FAIL" for c in report["checks"])
        else "DIGITAL SCOPE NOT FULLY VERIFIED IN THIS RUN"
    )
    (out / "validation_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Executed validation report",
        "",
        f"Status: **{report['project_status']}**. Physical performance is unverified.",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    lines += [f"| {c['name']} | {c['result']} |" for c in report["checks"]]
    lines += [
        "",
        "## Verified scope limitations",
        "",
        *[f"- {v}" for v in report["scope_limitations"]],
    ]
    (out / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return int(any(c["result"] == "FAIL" for c in report["checks"]))


if __name__ == "__main__":
    raise SystemExit(run())
