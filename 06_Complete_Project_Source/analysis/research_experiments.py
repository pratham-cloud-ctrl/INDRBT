"""Seeded parameter sweeps answering the five engineering research questions."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analysis.joint_torque_analysis import gravity_torques
from analysis.structural_analysis import beam_response
from robotarm.config import load_config
from robotarm.kinematics import RobotArm
from robotarm.planning import Trajectory, joint_trajectory
from robotarm.control import simulate_pid

ROOT = Path(__file__).resolve().parents[1]


def save_plot(fig, name):
    fig.tight_layout()
    fig.savefig(ROOT / "results" / "research" / name, dpi=180)
    plt.close(fig)


def run_experiments():
    cfg = load_config()
    arm = RobotArm(cfg)
    out = ROOT / "results" / "research"
    out.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    result = {"seed": 504, "status": "CALCULATED / SIMULATED; no physical experiments"}
    rng = np.random.default_rng(504)
    qs = rng.uniform(arm.limits[:, 0], arm.limits[:, 1], (2200, 6))
    # Same joint samples and 40 mm grid for a fair finite-sampling sensitivity study.
    ratios = [0.75, 1.0, 8 / 7, 1.5, 2.0]
    total = cfg["geometry"]["upper_arm_length"] + cfg["geometry"]["forearm_length"]
    reach_data = []
    for ratio in ratios:
        varied = deepcopy(cfg)
        varied["geometry"]["upper_arm_length"] = total * ratio / (1 + ratio)
        varied["geometry"]["forearm_length"] = total / (1 + ratio)
        model = RobotArm(varied)
        points = np.array([model.fk(q)[:3, 3] for q in qs])
        above = points[points[:, 2] >= 0]
        occupied = len(np.unique(np.floor(above / 0.04).astype(int), axis=0))
        distances = np.linalg.norm(points - [0, 0, arm.height], axis=1)
        reach_data.append(
            {
                "ratio": ratio,
                "upper_arm_m": varied["geometry"]["upper_arm_length"],
                "forearm_m": varied["geometry"]["forearm_length"],
                "sample_min_shoulder_radius_m": float(distances.min()),
                "sample_max_shoulder_radius_m": float(distances.max()),
                "above_floor_sample_count": len(above),
                "occupied_40mm_voxels": occupied,
            }
        )
    result["RQ1"] = {
        "samples_per_ratio": len(qs),
        "values": reach_data,
        "interpretation": "Outer geometric reach fixed. Voxel counts are a finite-sample index, not reachable volume or collision-free workspace.",
    }
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(
        ratios,
        [v["sample_min_shoulder_radius_m"] * 1000 for v in reach_data],
        "o-",
        color="#137e91",
    )
    axes[0].set(xlabel="Upper / forearm length ratio", ylabel="Minimum sampled radius (mm)")
    axes[1].plot(ratios, [v["occupied_40mm_voxels"] for v in reach_data], "o-", color="#d58b28")
    axes[1].set(xlabel="Upper / forearm length ratio", ylabel="Occupied grid cells (sample index)")
    fig.suptitle("RQ1 | link ratio changes the inner workspace, at fixed outer reach")
    save_plot(fig, "link_ratio.png")

    payloads = np.arange(0, 7)
    torques = np.array([gravity_torques(arm, np.zeros(6), float(p)) for p in payloads])
    result["RQ2"] = {
        "payload_kg": payloads.tolist(),
        "shoulder_nm": torques[:, 1].tolist(),
        "elbow_nm": torques[:, 2].tolist(),
    }
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(payloads, torques[:, 1], "o-", label="Shoulder", color="#137e91")
    ax.plot(payloads, torques[:, 2], "s-", label="Elbow", color="#d58b28")
    ax.set(
        xlabel="Payload (kg)",
        ylabel="Gravity holding torque magnitude (N·m)",
        title="RQ2 | extended arm torque increases linearly with payload",
    )
    ax.legend()
    save_plot(fig, "payload.png")

    start = cfg["home"]
    end = start + np.deg2rad([30, 15, -20, 25, -15, 20])
    durations = [2.0, 4.0, 8.0]
    timing = []
    for duration in durations:
        trajectory = joint_trajectory(arm, start, end, duration, samples=801)
        timing.append(
            {
                "duration_s": duration,
                "max_velocity_rad_s": float(np.max(np.abs(trajectory.dq))),
                "max_acceleration_rad_s2": float(np.max(np.abs(trajectory.ddq))),
            }
        )
    result["RQ3"] = timing
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(durations, [v["max_velocity_rad_s"] for v in timing], "o-", color="#137e91")
    axes[0].set(xlabel="Motion duration (s)", ylabel="Maximum joint velocity (rad/s)")
    axes[1].plot(durations, [v["max_acceleration_rad_s2"] for v in timing], "o-", color="#d58b28")
    axes[1].set(xlabel="Motion duration (s)", ylabel="Maximum joint acceleration (rad/s²)")
    fig.suptitle("RQ3 | quintic peaks scale as 1/T and 1/T²")
    save_plot(fig, "duration.png")

    t = np.linspace(0, 5, 501)
    step_target = start + np.deg2rad([0, 15, 0, 0, 0, 0])
    desired = np.tile(step_target, (len(t), 1))
    step = Trajectory(
        t, desired, np.zeros_like(desired), np.zeros_like(desired), "15 degree J2 step"
    )
    tuning = []
    fig, ax = plt.subplots(figsize=(8, 4))
    for scale in [0.5, 1.0, 2.0]:
        sim = simulate_pid(arm, step, initial=start, gain_scale=scale)
        error = np.abs(sim.error[:, 1])
        outside = np.flatnonzero(error > np.deg2rad(15) * 0.02)
        settling = 0.0
        # sim has its own fine integration grid, not the desired trajectory grid.
        if len(outside) and outside[-1] < len(sim.t) - 1:
            settling = float(sim.t[outside[-1] + 1])
        elif len(outside):
            settling = None
        tuning.append(
            {
                "gain_scale": scale,
                "joint2_rmse_rad": float(np.sqrt(np.mean(error**2))),
                "settling_time_2percent_s": settling,
                "overshoot_percent": float(
                    max(0, np.max(sim.actual[:, 1] - step_target[1])) / np.deg2rad(15) * 100
                ),
                "peak_torque_nm": float(np.max(np.abs(sim.torque[:, 1]))),
            }
        )
        ax.plot(sim.t, np.rad2deg(sim.actual[:, 1] - start[1]), label=f"Gains ×{scale}")
    ax.axhline(15, color="#777", ls="--", label="Target")
    ax.set(
        xlabel="Time (s)",
        ylabel="J2 displacement (deg)",
        title="RQ4 | PID tuning on the assumed inertia/damping plant",
    )
    ax.legend()
    save_plot(fig, "pid_tuning.png")
    result["RQ4"] = tuning

    grip = cfg["gripper"]
    lengths = np.linspace(0.03, 0.09, 7)
    inertia = grip["finger_width"] * grip["finger_thickness"] ** 3 / 12
    aluminum = cfg["materials"]["aluminum"]
    finger = [
        beam_response(
            float(length),
            inertia,
            grip["finger_thickness"],
            aluminum["young_modulus"],
            grip["total_normal_force_target"] / 2,
            0,
            0,
            aluminum["yield_strength"],
        )
        for length in lengths
    ]
    required_torque = (
        grip["total_normal_force_target"]
        * grip["screw_lead"]
        / (2 * np.pi * grip["screw_efficiency"])
    )
    result["RQ5"] = {
        "finger_length_m": lengths.tolist(),
        "stress_mpa": [v["bending_stress_mpa"] for v in finger],
        "deflection_mm": [v["elastic_deflection_mm"] for v in finger],
        "fixed_total_normal_force_N": grip["total_normal_force_target"],
        "required_screw_torque_nm": required_torque,
        "interpretation": "Finger length raises bending moment and cubic elastic deflection. Ideal lead-screw force and torque do not depend on finger length; guide moments and flexibility do.",
    }
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(lengths * 1000, [v["bending_stress_mpa"] for v in finger], "o-", color="#137e91")
    axes[0].set(xlabel="Finger length (mm)", ylabel="Bending stress (MPa)")
    axes[1].plot(
        lengths * 1000, [v["elastic_deflection_mm"] for v in finger], "o-", color="#d58b28"
    )
    axes[1].set(xlabel="Finger length (mm)", ylabel="Elastic tip deflection (mm)")
    fig.suptitle("RQ5 | finger stiffness at fixed 100 N per jaw")
    save_plot(fig, "finger_length.png")
    (out / "experiments.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(run_experiments(), indent=2))
