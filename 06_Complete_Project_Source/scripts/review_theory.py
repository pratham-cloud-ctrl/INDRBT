"""Cross-check the digital models and retained numerical evidence without regenerating plots."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
from scipy.integrate import quad
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]


def read_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def elementary_rotation(axis, angle):
    """Elementary sin/cos matrices, independent of the production SciPy rotations."""
    c, s = np.cos(angle), np.sin(angle)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def independent_fk(arm, q):
    orientation, position = np.eye(3), np.array([0.0, 0.0, arm.height])
    for axis, angle, length in zip("zyyxyx", q, arm.lengths):
        orientation = orientation @ elementary_rotation(axis, angle)
        position += orientation[:, 0] * length
    return position, orientation


def virtual_work_deflection(config):
    """Apply a unit TCP force to the whole extended arm and integrate M*m/(EI)."""
    g, mass = config["geometry"], config["mass"]
    gravity = config["targets"]["gravity"]
    young = config["materials"]["aluminum"]["young_modulus"]
    l1, l2, roll, pitch, tool = [
        g[key]
        for key in (
            "upper_arm_length",
            "forearm_length",
            "wrist_roll_length",
            "wrist_pitch_length",
            "tool_length",
        )
    ]
    reach = l1 + l2 + roll + pitch + tool
    points = [
        (mass["wrist_roll"], l1 + l2 + roll / 2),
        (mass["wrist_pitch"], l1 + l2 + roll + pitch / 2),
        (mass["flange_gripper"], l1 + l2 + roll + pitch + tool / 2),
        (mass["payload"], reach),
    ]
    distributed = [(0, l1, mass["upper_arm"] / l1), (l1, l1 + l2, mass["forearm"] / l2)]

    def moment(x):
        value = sum(weight * gravity * max(position - x, 0) for weight, position in points)
        return value + sum(
            density * gravity * ((end - x) ** 2 - (max(start, x) - x) ** 2) / 2
            for start, end, density in distributed
            if end > x
        )

    total = 0.0
    for start, end, width, depth in [
        (0, l1, g["upper_arm_width"], g["upper_arm_depth"]),
        (l1, l1 + l2, g["forearm_width"], g["forearm_depth"]),
    ]:
        wall = g["wall_thickness"]
        second_moment = (width * depth**3 - (width - 2 * wall) * (depth - 2 * wall) ** 3) / 12
        total += quad(lambda x: moment(x) * (reach - x) / (young * second_moment), start, end)[0]
    return total * 1000


def review(pytest_xml=None):
    # Audit this checkout explicitly, even if an older wheel is also installed.
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    from analysis.joint_torque_analysis import gravity_torques, potential_energy
    from analysis.structural_analysis import calculate
    from robotarm.config import load_config
    from robotarm.control import simulate_pid
    from robotarm.gripper import ParallelGripper
    from robotarm.kinematics import IKError, RobotArm
    from robotarm.planning import stationary, joint_trajectory

    cfg = load_config()
    arm = RobotArm(cfg)
    rng = np.random.default_rng(202610051)
    checks = {}
    assert cfg["units"] == {
        "length": "m",
        "angle": "rad",
        "mass": "kg",
        "time": "s",
        "torque": "N*m",
    }
    for group in [cfg["geometry"], cfg["gripper"], cfg["targets"]]:
        assert all(np.isfinite(value) and value > 0 for value in group.values())
    assert all(
        np.isfinite(value) and value > 0 for key, value in cfg["mass"].items() if key != "status"
    )
    for values in cfg["control"].values():
        assert np.all(np.isfinite(values)) and np.all(np.asarray(values) > 0)
    np.testing.assert_allclose(cfg["joint_limits"], np.deg2rad(cfg["joint_limits_deg"]))
    checks["units_and_parameters"] = {
        "status": "PASS",
        "scope": "Current authoritative SI configuration and degree-to-radian conversion",
    }

    poses = rng.uniform(arm.limits[:, 0] + 0.2, arm.limits[:, 1] - 0.2, (40, 6))
    fk_position_errors, fk_rotation_errors = [], []
    ik_position, ik_orientation, jacobian_errors = [], [], []
    for q in poses:
        p, r = independent_fk(arm, q)
        actual = arm.fk(q)
        fk_position_errors.append(float(np.linalg.norm(actual[:3, 3] - p)))
        fk_rotation_errors.append(float(np.max(np.abs(actual[:3, :3] - r))))
        seed = np.clip(q + rng.normal(0, 0.35, 6), arm.limits[:, 0], arm.limits[:, 1])
        assert not np.allclose(seed, q)
        solved = arm.solve_ik(actual, seed)
        assert np.all(solved.q >= arm.limits[:, 0]) and np.all(solved.q <= arm.limits[:, 1])
        ik_position.append(solved.position_error_m)
        ik_orientation.append(solved.orientation_error_rad)
        numerical = np.zeros((6, 6))
        for index in range(6):
            delta = np.eye(6)[index] * 1e-6
            plus, minus = arm.fk(q + delta), arm.fk(q - delta)
            numerical[:3, index] = (plus[:3, 3] - minus[:3, 3]) / 2e-6
            numerical[3:, index] = (
                Rotation.from_matrix(plus[:3, :3] @ minus[:3, :3].T).as_rotvec() / 2e-6
            )
        jacobian_errors.append(float(np.max(np.abs(arm.jacobian(q) - numerical))))
    assert max(fk_position_errors) < 1e-12 and max(fk_rotation_errors) < 1e-12
    assert max(jacobian_errors) < 3e-9
    assert (
        max(ik_position) <= arm.position_tolerance
        and max(ik_orientation) <= arm.orientation_tolerance
    )
    np.testing.assert_allclose(arm.fk(np.zeros(6))[:3, 3], [arm.reach, 0, arm.height], atol=1e-12)
    vertical = np.zeros(6)
    vertical[1] = -np.pi / 2
    np.testing.assert_allclose(arm.fk(vertical)[:3, 3], [0, 0, arm.height + arm.reach], atol=1e-12)
    unreachable = np.eye(4)
    unreachable[:3, 3] = [arm.reach + 0.001, 0, arm.height]
    try:
        arm.ik(unreachable)
    except IKError:
        pass
    else:
        raise AssertionError("Geometric unreachable target was accepted")
    checks["kinematics"] = {
        "status": "PASS",
        "seed": 202610051,
        "independent_fk_and_perturbed_ik_trials": len(poses),
        "max_fk_position_discrepancy_m": max(fk_position_errors),
        "max_fk_rotation_element_discrepancy": max(fk_rotation_errors),
        "max_ik_position_error_m": max(ik_position),
        "max_ik_orientation_error_rad": max(ik_orientation),
        "max_jacobian_finite_difference_discrepancy": max(jacobian_errors),
        "shoulder_reach_m": arm.reach,
        "vertical_tcp_height_m": arm.height + arm.reach,
        "outside_radial_bound_rejected": True,
        "scope": "Necessary radial bound, bounded local IK and geometric world Jacobian; no exhaustive reachability or collision proof",
    }

    workspace = read_json("results/workspace/metrics.json")
    cloud = np.loadtxt(ROOT / "results/workspace/samples.csv", delimiter=",", skiprows=1)
    assert len(cloud) == workspace["samples"] and np.all(np.isfinite(cloud))
    assert np.max(np.linalg.norm(cloud[:, :3] - [0, 0, arm.height], axis=1)) <= arm.reach + 1e-8
    np.testing.assert_allclose(
        ConvexHull(cloud[:, :3]).volume,
        workspace["convex_hull_envelope_volume_m3"],
        atol=1e-8,
        rtol=0,
    )
    assert np.count_nonzero(cloud[:, 2] >= 0) == workspace["above_floor_samples"]
    assert np.mean(cloud[:, 3] < 0.01) == workspace["fraction_scaled_sigma_min_below_0_01"]
    checks["workspace"] = {
        "status": "PASS",
        "saved_samples_rechecked": len(cloud),
        "scope": "Stored sample envelope, hull, above-floor count and dimensionless singularity threshold; no reachable-volume certificate",
    }

    task = read_json("results/trajectories/pick_place_samples.json")
    task_metrics = read_json("results/trajectories/pick_place_metrics.json")
    t, q = np.asarray(task["t_s"]), np.asarray(task["q_rad"])
    tcp = np.array([arm.fk(joints)[:3, 3] for joints in q])
    np.testing.assert_allclose(tcp, task["tcp_m"], atol=1e-12, rtol=0)
    np.testing.assert_allclose(
        np.sum(np.linalg.norm(np.diff(tcp, axis=0), axis=1)),
        task_metrics["path_length_m"],
        atol=1e-12,
    )
    assert np.all(np.diff(t) > 0) and len(t) == task_metrics["samples"]
    np.testing.assert_allclose(t[-1] - t[0], task_metrics["duration_s"], atol=1e-12)
    saved = np.loadtxt(ROOT / "results/trajectories/pick_place.csv", delimiter=",", skiprows=1)
    for key, observed in [
        ("max_velocity_limit_fraction", np.max(np.abs(saved[:, 7:13]) / cfg["velocity_limits"])),
        (
            "max_acceleration_limit_fraction",
            np.max(np.abs(saved[:, 13:19]) / cfg["acceleration_limits"]),
        ),
    ]:
        np.testing.assert_allclose(observed, task_metrics[key], atol=1e-8, rtol=0)
        assert observed <= 1
    np.testing.assert_allclose(q[0], cfg["home"], atol=1e-12)
    np.testing.assert_allclose(q[-1], cfg["home"], atol=1e-12)
    assert [event["action"] for event in task["events"]] == ["close", "open"]
    checks["recorded_task"] = {
        "status": "PASS",
        "fk_samples_recomputed": len(q),
        "duration_s": float(t[-1] - t[0]),
        "path_length_m": task_metrics["path_length_m"],
        "scope": "Stored FK/path/limits/events; finite-difference MOVE L limits remain sampled",
    }

    endpoint = cfg["home"] + np.deg2rad([20, 15, -20, 30, -25, 40])
    delta = endpoint - cfg["home"]
    motion = joint_trajectory(arm, cfg["home"], endpoint, samples=4001)
    exact_velocity = 1.875 * np.abs(delta) / motion.duration
    exact_acceleration = 10 / np.sqrt(3) * np.abs(delta) / motion.duration**2
    assert np.all(exact_velocity <= cfg["velocity_limits"]) and np.all(
        exact_acceleration <= cfg["acceleration_limits"]
    )
    checks["quintic_analytic_limits"] = {
        "status": "PASS",
        "duration_s": motion.duration,
        "max_exact_speed_fraction": float(np.max(exact_velocity / cfg["velocity_limits"])),
        "max_exact_acceleration_fraction": float(
            np.max(exact_acceleration / cfg["acceleration_limits"])
        ),
    }

    gravity_errors = []
    for joints in poses[:12]:
        gradient = np.array(
            [
                (
                    potential_energy(arm, joints + np.eye(6)[j] * 1e-6)
                    - potential_energy(arm, joints - np.eye(6)[j] * 1e-6)
                )
                / 2e-6
                for j in range(6)
            ]
        )
        gravity_errors.append(float(np.max(np.abs(gravity_torques(arm, joints) + gradient))))
    torque = read_json("results/mechanical/joint_torque.json")
    sampled = np.array([gravity_torques(arm, joints) for joints in poses])
    assert max(gravity_errors) < 2e-7
    assert np.all(np.abs(sampled) <= np.asarray(torque["conservative_gravity_bound_nm"]) + 1e-10)
    np.testing.assert_allclose(
        gravity_torques(arm, np.zeros(6)), torque["extended_gravity_torque_nm"], atol=1e-12
    )
    output = cfg["actuators"]["safety_factor"] * (
        np.asarray(torque["conservative_gravity_bound_nm"])
        + np.asarray(cfg["control"]["inertia"]) * cfg["acceleration_limits"]
        + np.asarray(cfg["control"]["viscous_damping"]) * cfg["velocity_limits"]
    )
    np.testing.assert_allclose(output, torque["concept_output_torque_nm"], atol=1e-12)
    np.testing.assert_allclose(
        output / np.asarray(cfg["actuators"]["gear_ratios"]) / cfg["actuators"]["efficiencies"],
        torque["concept_motor_torque_nm"],
        atol=1e-12,
    )
    assert np.all(output <= cfg["control"]["torque_limits"])
    structure = calculate(cfg)
    integral = virtual_work_deflection(cfg)
    np.testing.assert_allclose(integral, structure["serial_tcp_beam_deflection_mm"], atol=1e-12)
    np.testing.assert_allclose(
        structure["upper_arm"]["root_moment_nm"],
        abs(gravity_torques(arm, np.zeros(6))[1]),
        atol=1e-12,
    )
    checks["gravity_and_structure"] = {
        "status": "PASS",
        "gravity_gradient_trials": len(gravity_errors),
        "max_gravity_gradient_discrepancy_Nm": max(gravity_errors),
        "gravity_bound_samples": len(sampled),
        "serial_tcp_deflection_mm": structure["serial_tcp_beam_deflection_mm"],
        "independent_virtual_work_deflection_mm": integral,
        "forearm_rotation_contribution_mm": structure["serial_tcp_deflection_terms_mm"][
            "forearm_rotation"
        ],
        "correction": "Included forearm tip slope multiplied by rigid wrist/tool reach; earlier total omitted that term",
        "scope": "Extended-pose ideal beam/load models with assumed COMs and materials; no complete CAD stiffness, physical repeatability or load rating",
    }

    gripper = ParallelGripper(cfg)
    grip = cfg["gripper"]
    expected_torque = (
        grip["total_normal_force_target"]
        * grip["screw_lead"]
        / (2 * np.pi * grip["screw_efficiency"])
    )
    np.testing.assert_allclose(gripper.required_torque(), expected_torque, atol=1e-14)
    np.testing.assert_allclose(
        gripper.screw_revolutions(0, grip["max_opening"]),
        grip["max_opening"] / (2 * grip["screw_lead"]),
    )
    np.testing.assert_allclose(
        gripper.metrics()["friction_limited_payload_kg_with_safety_factor"],
        grip["friction_coefficient"]
        * grip["total_normal_force_target"]
        / (cfg["targets"]["gravity"] * grip["grip_safety_factor"]),
    )
    assert expected_torque <= grip["motor_torque"]
    gripper_metrics = gripper.metrics()
    assumption_class = gripper_metrics.pop("status")
    checks["gripper_work_and_friction"] = {
        "status": "PASS",
        **gripper_metrics,
        "model_evidence_class": assumption_class,
        "scope": "Both-jaw work balance and static ideal friction capacity; no contact/acceleration or motor validation",
    }

    control = cfg["control"]
    inertia, damping, kp, ki, kd = [
        np.asarray(control[key]) for key in ("inertia", "viscous_damping", "kp", "ki", "kd")
    ]
    assert np.all((damping + kd) * kp > inertia * ki)
    target = cfg["home"] + np.deg2rad(cfg["demo"]["control_step_deg"])
    command = stationary(target, cfg["demo"]["control_step_duration_s"], 501)
    coarse = simulate_pid(arm, command, initial=cfg["home"])
    fine_config = deepcopy(cfg)
    fine_config["control"]["dt"] /= 2
    fine = simulate_pid(RobotArm(fine_config), command, initial=cfg["home"])
    expected_first_torque = np.clip(
        kp * (target - cfg["home"]) + ki * (target - cfg["home"]) * (coarse.t[1] - coarse.t[0]),
        -np.asarray(control["torque_limits"]),
        control["torque_limits"],
    )
    np.testing.assert_allclose(coarse.torque[0], expected_first_torque, atol=1e-12)
    np.testing.assert_allclose(
        coarse.metrics()["rmse_rad"],
        read_json("results/control/metrics.json")["step"]["rmse_rad"],
        atol=1e-12,
    )
    interpolated = np.column_stack(
        [np.interp(fine.t, coarse.t, coarse.actual[:, j]) for j in range(6)]
    )
    checks["pid_model"] = {
        "status": "PASS",
        "unsaturated_linear_routh_hurwitz_condition": True,
        "first_feedback_command_agrees": True,
        "coarse_dt_s": control["dt"],
        "fine_dt_s": fine_config["control"]["dt"],
        "max_step_position_difference_on_time_refinement_rad": float(
            np.max(np.abs(interpolated - fine.actual))
        ),
        "scope": "Independent inertia/damping plant, conditional antiwindup and semi-implicit Euler; two-step-size comparison is a sensitivity check, not an error-bound proof",
    }

    research = read_json("results/research/experiments.json")
    geometry = cfg["geometry"]
    common = np.random.default_rng(research["seed"]).uniform(
        arm.limits[:, 0], arm.limits[:, 1], (research["RQ1"]["samples_per_ratio"], 6)
    )
    total_length = geometry["upper_arm_length"] + geometry["forearm_length"]
    for row in research["RQ1"]["values"]:
        varied = deepcopy(cfg)
        varied["geometry"]["upper_arm_length"] = total_length * row["ratio"] / (1 + row["ratio"])
        varied["geometry"]["forearm_length"] = total_length / (1 + row["ratio"])
        model = RobotArm(varied)
        points = np.array([independent_fk(model, joints)[0] for joints in common])
        radii = np.linalg.norm(points - [0, 0, arm.height], axis=1)
        np.testing.assert_allclose(
            [radii.min(), radii.max()],
            [row["sample_min_shoulder_radius_m"], row["sample_max_shoulder_radius_m"]],
            atol=1e-12,
        )
        above = points[points[:, 2] >= 0]
        assert len(above) == row["above_floor_sample_count"]
        assert (
            len(np.unique(np.floor(above / 0.04).astype(int), axis=0))
            == row["occupied_40mm_voxels"]
        )
        assert model.reach == arm.reach
    for joint, key, lever in [
        (1, "shoulder_nm", arm.reach),
        (2, "elbow_nm", arm.reach - geometry["upper_arm_length"]),
    ]:
        baseline = gravity_torques(arm, np.zeros(6), 0)[joint]
        expected = (
            baseline + np.asarray(research["RQ2"]["payload_kg"]) * cfg["targets"]["gravity"] * lever
        )
        np.testing.assert_allclose(expected, research["RQ2"][key], atol=1e-12)
    durations = np.array([row["duration_s"] for row in research["RQ3"]])
    velocities = np.array([row["max_velocity_rad_s"] for row in research["RQ3"]])
    accelerations = np.array([row["max_acceleration_rad_s2"] for row in research["RQ3"]])
    np.testing.assert_allclose(
        velocities * durations, np.repeat(velocities[0] * durations[0], len(durations)), atol=1e-12
    )
    np.testing.assert_allclose(
        accelerations * durations**2,
        np.repeat(accelerations[0] * durations[0] ** 2, len(durations)),
        atol=1e-12,
    )
    step_target = cfg["home"] + np.deg2rad([0, 15, 0, 0, 0, 0])
    for row in research["RQ4"]:
        result = simulate_pid(
            arm, stationary(step_target, 5, 501), initial=cfg["home"], gain_scale=row["gain_scale"]
        )
        error = np.abs(result.error[:, 1])
        outside = np.flatnonzero(error > np.deg2rad(15) * 0.02)
        settling = float(result.t[outside[-1] + 1]) if outside[-1] < len(result.t) - 1 else None
        np.testing.assert_allclose(np.sqrt(np.mean(error**2)), row["joint2_rmse_rad"], atol=1e-12)
        np.testing.assert_allclose(settling, row["settling_time_2percent_s"], atol=1e-12)
        np.testing.assert_allclose(
            np.max(np.abs(result.torque[:, 1])), row["peak_torque_nm"], atol=1e-12
        )
    lengths = np.asarray(research["RQ5"]["finger_length_m"])
    force = grip["total_normal_force_target"] / 2
    width, thickness = grip["finger_width"], grip["finger_thickness"]
    stress = 6 * force * lengths / (width * thickness**2) / 1e6
    deflection = (
        4
        * force
        * lengths**3
        / (cfg["materials"]["aluminum"]["young_modulus"] * width * thickness**3)
        * 1000
    )
    np.testing.assert_allclose(stress, research["RQ5"]["stress_mpa"], atol=1e-12)
    np.testing.assert_allclose(deflection, research["RQ5"]["deflection_mm"], atol=1e-12)
    np.testing.assert_allclose(
        expected_torque, research["RQ5"]["required_screw_torque_nm"], atol=1e-14
    )
    checks["five_research_sweeps"] = {
        "status": "PASS",
        "RQ1_independent_FK_samples": len(common) * len(research["RQ1"]["values"]),
        "RQ2_payload_points": len(research["RQ2"]["payload_kg"]),
        "RQ3_durations": len(durations),
        "RQ4_repeated_controller_cases": len(research["RQ4"]),
        "RQ5_finger_lengths": len(lengths),
        "scope": "Rechecked stored data with independent FK, lever/beam relations and replayed controller cases; numerical sensitivity, no physical experiments",
    }

    report = {
        "status": "PASS",
        "scope": "Independent digital engineering theory/evidence review; no physical qualification or exhaustive continuous-motion certificate",
        "checks": checks,
    }
    if pytest_xml:
        root = ET.parse(pytest_xml).getroot()
        suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
        totals = {
            field: sum(int(suite.get(field, 0)) for suite in suites)
            for field in ("tests", "failures", "errors", "skipped")
        }
        assert totals["tests"] >= 34 and not sum(
            totals[field] for field in ("failures", "errors", "skipped")
        )
        report["pytest"] = {
            "status": "PASS",
            **totals,
            "junit_sha256": hashlib.sha256(Path(pytest_xml).read_bytes()).hexdigest(),
            "evidence_input": "Successful retained pytest JUnit supplied via --pytest-xml",
            "note": "The JUnit hash binds the reviewed totals. Integrated execution output is retained in validation_report.json; this review does not rerun pytest.",
        }
    sources = [
        "config/robot.yaml",
        "src/robotarm/config.py",
        "src/robotarm/kinematics/model.py",
        "src/robotarm/planning/trajectories.py",
        "src/robotarm/control/pid.py",
        "src/robotarm/gripper/model.py",
        "analysis/joint_torque_analysis.py",
        "analysis/structural_analysis.py",
        "analysis/research_experiments.py",
        "tests/test_mechanical.py",
        "scripts/review_theory.py",
        "results/mechanical/structural.json",
        "results/research/experiments.json",
    ]
    report["source_and_evidence_sha256"] = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources
    }
    report["primary_formula_references"] = [
        "https://www.ocw.mit.edu/courses/6-152j-micro-nano-processing-technology-fall-2005/4e555db93fbd2b7473f14100fbaadcc8_lecture13.pdf",
        "https://www.thomsonlinear.com/downloads/screws/Lead_Screws_cten.pdf",
    ]
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pytest-xml", type=Path, help="Existing successful pytest JUnit report to bind"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results/validation/final_theory_review.json"
    )
    args = parser.parse_args()
    result = review(args.pytest_xml)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "checks": len(result["checks"]),
                "test_totals": result.get("pytest"),
                "serial_tcp_beam_deflection_mm": result["checks"]["gravity_and_structure"][
                    "serial_tcp_deflection_mm"
                ],
            },
            indent=2,
        )
    )
