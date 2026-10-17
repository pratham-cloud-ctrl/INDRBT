"""Gravity loading from configured lumped masses and the actual serial frames.

Run from the repository: python -m analysis.joint_torque_analysis
No dynamic rigid-body or commercial actuator validation is implied.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from robotarm.config import load_config
from robotarm.kinematics import RobotArm

ROOT = Path(__file__).resolve().parents[1]


def mass_points(arm: RobotArm, q: np.ndarray, payload: float | None = None):
    """Return (mass, world COM, last affected joint) for every moving lump.

    Motors/reducers/bearings are included in ASSUMED link masses, not inferred
    from the CAD exterior volume. Each group uses a midpoint approximation.
    """
    c = arm.config
    g, m = c["geometry"], c["mass"]
    payload = m["payload"] if payload is None else float(payload)
    if not np.isfinite(payload) or payload < 0:
        raise ValueError("Payload mass must be nonnegative and finite, in kg.")
    frames = arm.frames(q)["joint_transforms"]
    specs = [
        ("upper_arm", 1, g["upper_arm_length"] / 2),
        ("forearm", 2, g["forearm_length"] / 2),
        ("wrist_roll", 3, g["wrist_roll_length"] / 2),
        ("wrist_pitch", 4, g["wrist_pitch_length"] / 2),
        ("flange_gripper", 5, g["tool_length"] / 2),
    ]
    points = [(m[name], (frames[j] @ [x, 0, 0, 1])[:3], j) for name, j, x in specs]
    points.append((payload, arm.fk(q)[:3, 3], 5))
    return points


def gravity_torques(arm: RobotArm, q: np.ndarray, payload: float | None = None):
    """External gravity moment about each axis, in N*m; holding torque = minus this."""
    frames = arm.frames(q)
    origins, axes = frames["joint_origins"], frames["joint_axes"]
    gravity = arm.config["targets"]["gravity"]
    torque = np.zeros(6)
    for mass, position, last_joint in mass_points(arm, q, payload):
        force = np.array([0, 0, -mass * gravity])
        for j in range(last_joint + 1):
            torque[j] += axes[j] @ np.cross(position - origins[j], force)
    return torque


def potential_energy(arm: RobotArm, q: np.ndarray, payload: float | None = None):
    return sum(
        mass * arm.config["targets"]["gravity"] * p[2]
        for mass, p, _ in mass_points(arm, q, payload)
    )


def point_mass_inertia_bounds(arm: RobotArm) -> np.ndarray:
    """All-angle bounds on diagonal inertia of the assumed COM point masses.

    Each contribution is m*r_perpendicular**2. Triangle-inequality lever bounds
    follow the same serial geometry and midpoint COMs as gravity_torques. The
    roll-axis lever excludes offsets along that roll axis. This is a bound for
    the point-mass model, not a complete inertia tensor for the manufactured arm.
    """
    g, m = arm.config["geometry"], arm.config["mass"]
    l1, l2, wr, wp, tool = [
        g[key]
        for key in (
            "upper_arm_length",
            "forearm_length",
            "wrist_roll_length",
            "wrist_pitch_length",
            "tool_length",
        )
    ]
    masses = np.array(
        [
            m[key]
            for key in (
                "upper_arm",
                "forearm",
                "wrist_roll",
                "wrist_pitch",
                "flange_gripper",
                "payload",
            )
        ]
    )
    shoulder = [
        l1 / 2,
        l1 + l2 / 2,
        l1 + l2 + wr / 2,
        l1 + l2 + wr + wp / 2,
        l1 + l2 + wr + wp + tool / 2,
        l1 + l2 + wr + wp + tool,
    ]
    elbow = [0, l2 / 2, l2 + wr / 2, l2 + wr + wp / 2, l2 + wr + wp + tool / 2, l2 + wr + wp + tool]
    wrist = [0, 0, 0, wp / 2, wp + tool / 2, wp + tool]
    lever_bounds = np.array([shoulder, shoulder, elbow, wrist, wrist, np.zeros(6)])
    return lever_bounds**2 @ masses


def sizing_inertias(arm: RobotArm) -> np.ndarray:
    """Keep the independent control plant separate from mass-based drive sizing."""
    return np.maximum(arm.config["control"]["inertia"], point_mass_inertia_bounds(arm))


def run_analysis(samples: int = 6000, seed: int = 412):
    c = load_config()
    arm = RobotArm(c)
    rng = np.random.default_rng(seed)
    qs = rng.uniform(c["joint_limits"][:, 0], c["joint_limits"][:, 1], (samples, 6))
    qs = np.vstack([np.zeros(6), qs])
    torques = np.array([gravity_torques(arm, q) for q in qs])
    absolute = np.abs(torques)
    idx = np.argmax(absolute, axis=0)
    sampled = absolute[idx, np.arange(6)]
    # Triangle inequality bound for all joint angles, deliberately conservative.
    # Upper/forearm lengths and all downstream offsets produce closed form bounds.
    g, m = c["geometry"], c["mass"]
    l1, l2, wr, wp, tool = [
        g[k]
        for k in (
            "upper_arm_length",
            "forearm_length",
            "wrist_roll_length",
            "wrist_pitch_length",
            "tool_length",
        )
    ]
    grav = c["targets"]["gravity"]
    elbow_bound = grav * (
        m["forearm"] * l2 / 2
        + m["wrist_roll"] * (l2 + wr / 2)
        + m["wrist_pitch"] * (l2 + wr + wp / 2)
        + m["flange_gripper"] * (l2 + wr + wp + tool / 2)
        + m["payload"] * (l2 + wr + wp + tool)
    )
    shoulder_bound = elbow_bound + grav * l1 * (
        m["upper_arm"] / 2
        + m["forearm"]
        + m["wrist_roll"]
        + m["wrist_pitch"]
        + m["flange_gripper"]
        + m["payload"]
    )
    wrist5_bound = grav * (
        m["wrist_pitch"] * wp / 2
        + m["flange_gripper"] * (wp + tool / 2)
        + m["payload"] * (wp + tool)
    )
    # J4 roll: offsets along its own X do not make a moment about X; pitch can
    # bend the last two lumps sideways, bounded by their lever about J5.
    bound = np.array([0, shoulder_bound, elbow_bound, wrist5_bound, wrist5_bound, 0])
    inertia = sizing_inertias(arm)
    damping = np.array(c["control"]["viscous_damping"])
    dynamic = inertia * c["acceleration_limits"] + damping * c["velocity_limits"]
    sf = c["actuators"]["safety_factor"]
    output = sf * (bound + dynamic)
    motor = output / np.array(c["actuators"]["gear_ratios"]) / c["actuators"]["efficiencies"]
    report = {
        "status": "CALCULATED with ASSUMED lumped masses and mass-consistent equivalent diagonal sizing inertia",
        "sample_count": len(qs),
        "seed": seed,
        "extended_gravity_torque_nm": gravity_torques(arm, np.zeros(6)).tolist(),
        "sampled_absolute_gravity_max_nm": sampled.tolist(),
        "sampled_worst_q_deg": [np.rad2deg(qs[i]).tolist() for i in idx],
        "conservative_gravity_bound_nm": bound.tolist(),
        "point_mass_inertia_bound_kg_m2": point_mass_inertia_bounds(arm).tolist(),
        "configured_control_inertia_kg_m2": list(c["control"]["inertia"]),
        "sizing_inertia_kg_m2": inertia.tolist(),
        "sizing_inertia_policy": "Per joint max(configured independent-axis plant inertia, all-angle point-COM lever bound). This preserves the educational control plant while preventing actuator sizing below the same assumed point-mass model.",
        "dynamic_allowance_nm": dynamic.tolist(),
        "safety_factor": sf,
        "concept_output_torque_nm": output.tolist(),
        "concept_motor_torque_nm": motor.tolist(),
        "assumed_total_manipulator_mass_kg": sum(
            m[k]
            for k in (
                "base",
                "turret",
                "upper_arm",
                "forearm",
                "wrist_roll",
                "wrist_pitch",
                "flange_gripper",
            )
        ),
        "moving_mass_kg": sum(
            m[k]
            for k in (
                "turret",
                "upper_arm",
                "forearm",
                "wrist_roll",
                "wrist_pitch",
                "flange_gripper",
            )
        ),
        "limitations": "COM midpoint point masses; no centroidal body rotation tensors, inertia coupling, Coriolis/centrifugal torque, reflected drive inertia, friction/backlash/cable/thermal/fatigue modelling. Gravity and diagonal point-mass bounds cover their stated model only, not full manipulator dynamics; sampling is not proof of a maximum.",
    }
    out = ROOT / "results" / "mechanical"
    out.mkdir(parents=True, exist_ok=True)
    (out / "joint_torque.json").write_text(json.dumps(report, indent=2) + "\n")
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(6)
    ax.bar(x - 0.2, sampled, 0.4, label="Sampled gravity moment", color="#137e91")
    ax.bar(
        x + 0.2, output, 0.4, label="Concept torque incl. dynamics × safety factor", color="#e49f40"
    )
    ax.set(
        xticks=x,
        xticklabels=[f"J{i + 1}" for i in x],
        ylabel="Torque (N·m)",
        title="ASTER-6 | actuator envelope from assumed masses",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "joint_torque.png", dpi=180)
    plt.close(fig)
    return report


if __name__ == "__main__":
    print(json.dumps(run_analysis(), indent=2))
