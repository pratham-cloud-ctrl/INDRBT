"""Generate real ASTER-6 numerical results: python -m robotarm.demo --all."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

from robotarm import RobotArm
from robotarm.control import simulate_pid
from robotarm.gripper import ParallelGripper
from robotarm.planning import joint_trajectory, move_linear, stationary
from robotarm.simulation import pick_and_place
from robotarm.visualization.plots import (
    COLORS,
    animate_fk,
    coordinate_frames,
    plot_joints,
    plot_tcp,
    representative_poses,
    save,
    style,
)


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def save_trajectory(path: Path, trajectory) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = np.column_stack((trajectory.t, trajectory.q, trajectory.dq, trajectory.ddq))
    header = ",".join(
        [
            "time_s",
            *[f"q{j}_rad" for j in range(1, 7)],
            *[f"dq{j}_rad_s" for j in range(1, 7)],
            *[f"ddq{j}_rad_s2" for j in range(1, 7)],
        ]
    )
    np.savetxt(path, columns, delimiter=",", header=header, comments="", fmt="%.10g")


def workspace_demo(robot: RobotArm, output: Path, sample_count: int | None = None) -> dict:
    import matplotlib.pyplot as plt

    settings = robot.config["demo"]
    sample_count = settings["workspace_samples"] if sample_count is None else sample_count
    if sample_count < 100:
        raise ValueError("Use at least 100 samples for the workspace report.")
    seed = settings["workspace_seed"]
    voxel_pitch = settings["workspace_voxel_pitch"]
    rng = np.random.default_rng(seed)
    angles = rng.uniform(robot.limits[:, 0], robot.limits[:, 1], (sample_count, 6))
    positions = np.array([robot.fk(q)[:3, 3] for q in angles])
    sigma_min = np.array([robot.singular_values(q)[-1] for q in angles])
    hull = ConvexHull(positions)
    voxels = np.unique(np.floor(positions / voxel_pitch).astype(int), axis=0)
    metrics = {
        "status": "SIMULATED joint-limit-only sampling; obstacles and self-collision excluded",
        "seed": seed,
        "samples": sample_count,
        "kinematic_max_reach_from_shoulder_m": robot.reach,
        "sampled_max_radius_from_shoulder_m": float(
            np.max(np.linalg.norm(positions - [0, 0, robot.height], axis=1))
        ),
        "coordinate_min_m": positions.min(axis=0).tolist(),
        "coordinate_max_m": positions.max(axis=0).tolist(),
        "convex_hull_envelope_volume_m3": float(hull.volume),
        "volume_caveat": "Convex hull fills inaccessible holes; sampled voxels depend on pitch and density. Neither is certified reachable volume.",
        "voxel_pitch_m": voxel_pitch,
        "occupied_voxel_proxy_volume_m3": float(len(voxels) * voxel_pitch**3),
        "fraction_scaled_sigma_min_below_0_01": float(np.mean(sigma_min < 0.01)),
        "below_base_plane_fraction": float(np.mean(positions[:, 2] < 0)),
        "above_floor_samples": int(np.sum(positions[:, 2] >= 0)),
        "above_floor_caveat": "Filtering TCP z>=0 alone does not ensure that links clear the floor or each other.",
        "smallest_dimensionless_singular_value": float(sigma_min.min()),
    }
    directory = output / "workspace"
    directory.mkdir(parents=True, exist_ok=True)
    np.savetxt(
        directory / "samples.csv",
        np.column_stack((positions, sigma_min)),
        delimiter=",",
        header="x_m,y_m,z_m,scaled_sigma_min",
        comments="",
        fmt="%.9g",
    )
    write_json(directory / "metrics.json", metrics)
    style()
    figure, axes = plt.subplots(1, 3, figsize=(14, 4.8), constrained_layout=True)
    for axis, (first, second) in zip(axes, [(0, 1), (0, 2), (1, 2)]):
        cloud = axis.scatter(
            positions[:, first],
            positions[:, second],
            c=np.log10(np.maximum(sigma_min, 1e-7)),
            s=2,
            alpha=0.5,
            cmap="viridis",
            vmin=-4,
            vmax=-1,
        )
        axis.set(
            xlabel=f"{'XYZ'[first]} [m]",
            ylabel=f"{'XYZ'[second]} [m]",
            title=f"{'XYZ'[first]}–{'XYZ'[second]} projection",
        )
        axis.set_aspect("equal")
    figure.colorbar(
        cloud, ax=axes, label="log₁₀ smallest scaled Jacobian singular value", shrink=0.75
    )
    figure.suptitle(
        f"ASTER-6 | {sample_count:,} joint-limit workspace samples\nKinematic reach envelope; collision and ground clearance not filtered",
        weight="bold",
    )
    save(figure, directory / "workspace_projections.png")
    figure = plt.figure(figsize=(9, 8), constrained_layout=True)
    axis = figure.add_subplot(projection="3d")
    cloud = axis.scatter(*positions.T, c=positions[:, 2], cmap="viridis", s=2, alpha=0.4)
    axis.scatter(0, 0, robot.height, color=COLORS[1], s=60, label="Shoulder")
    axis.set(
        xlabel="X [m]",
        ylabel="Y [m]",
        zlabel="Z [m]",
        title="ASTER-6 | sampled Cartesian position envelope",
    )
    axis.set_box_aspect((1, 1, 1))
    axis.legend()
    figure.colorbar(cloud, ax=axis, shrink=0.6, label="TCP Z [m]")
    save(figure, directory / "workspace_3d.png")
    figure, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    cloud = axes[0].scatter(
        np.rad2deg(angles[:, 2]),
        np.rad2deg(angles[:, 4]),
        c=np.log10(np.maximum(sigma_min, 1e-7)),
        s=4,
        cmap="magma",
        vmin=-4,
        vmax=-1,
    )
    axes[0].set(
        xlabel="Elbow J3 [deg]",
        ylabel="Wrist pitch J5 [deg]",
        title="Singularity sensitivity (other joints also vary)",
    )
    figure.colorbar(cloud, ax=axes[0], label="log₁₀ smallest scaled singular value")
    axes[1].hist(sigma_min, bins=50, color=COLORS[0])
    axes[1].axvline(0.01, color=COLORS[1], linestyle="--", label="Diagnostic threshold 0.01")
    axes[1].set(
        xlabel="Smallest scaled singular value",
        ylabel="Sample count",
        title="Jacobian conditioning distribution",
    )
    axes[1].legend()
    figure.suptitle(
        f"Translation rows scaled by the {robot.reach:.3g} m characteristic reach", weight="bold"
    )
    save(figure, directory / "singularity_analysis.png")
    representative_poses(robot, directory / "representative_poses.png")
    coordinate_frames(robot, directory / "coordinate_frames.png")
    useful = positions[positions[:, 2] >= 0]
    figure = plt.figure(figsize=(9, 8), constrained_layout=True)
    axis = figure.add_subplot(projection="3d")
    axis.scatter(*useful.T, c=useful[:, 2], cmap="viridis", s=2, alpha=0.4)
    axis.set(
        xlabel="X [m]",
        ylabel="Y [m]",
        zlabel="Z [m]",
        title="Above-floor TCP samples (z ≥ 0)\nLink clearance and self-collision not checked",
    )
    axis.set_box_aspect((1, 1, 0.7))
    save(figure, directory / "workspace_above_floor.png")
    return metrics


def trajectory_demo(robot: RobotArm, output: Path) -> dict:
    import matplotlib.pyplot as plt

    start, end = robot.config["home"], robot.config["poses"]["place"]
    duration = robot.config["demo"]["trajectory_duration_s"]
    motions = {
        kind: joint_trajectory(robot, start, end, duration=duration, kind=kind)
        for kind in ("linear", "cubic", "quintic")
    }
    directory = output / "trajectories"
    style()
    figure, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    # J5 is the largest move in this demonstration.
    for kind, trajectory in motions.items():
        for axis, values in zip(axes, (trajectory.q, trajectory.dq, trajectory.ddq)):
            axis.plot(trajectory.t, values[:, 4], label=kind)
    for axis, label in zip(
        axes, ("J5 position [rad]", "J5 velocity [rad/s]", "J5 acceleration [rad/s²]")
    ):
        axis.set_ylabel(label)
    axes[0].legend(ncol=3)
    axes[-1].set_xlabel("Time [s]")
    figure.suptitle(
        f"Interpolation comparison | {duration:g} s MOVE J\nLinear start/stop acceleration is impulsive and is not shown",
        weight="bold",
    )
    save(figure, directory / "interpolation_comparison.png")
    plot_joints(
        motions["quintic"],
        directory / "move_j_joints.png",
        "Quintic MOVE J | analytic position, velocity and acceleration",
    )
    plot_tcp(
        robot,
        motions["quintic"],
        directory / "move_j_tcp.png",
        "MOVE J | TCP follows the joint-space path",
    )
    initial = robot.config["poses"]["pick"]
    target = robot.fk(initial)
    target[2, 3] += robot.config["demo"]["approach_clearance"]
    cartesian = move_linear(robot, initial, target)
    plot_joints(
        cartesian,
        directory / "move_l_joints.png",
        "MOVE L | sampled IK continuation and time scaling",
    )
    plot_tcp(robot, cartesian, directory / "move_l_tcp.png", "MOVE L | straight vertical TCP path")
    save_trajectory(directory / "move_j.csv", motions["quintic"])
    save_trajectory(directory / "move_l.csv", cartesian)
    positions = np.array([robot.fk(q)[:3, 3] for q in cartesian.q])
    metrics = {
        "MOVE_J": motions["quintic"].metrics(robot),
        "MOVE_L": cartesian.metrics(robot),
        "move_l_max_xy_drift_m": float(
            np.max(np.linalg.norm(positions[:, :2] - positions[0, :2], axis=1))
        ),
        "linear_caveat": "Constant-velocity interior only; instantaneous boundary acceleration unbounded.",
        "move_l_caveat": "Derivative limits verified at sampled points; no continuous-path or collision certificate.",
    }
    write_json(directory / "trajectory_metrics.json", metrics)
    return metrics


def pick_place_demo(robot: RobotArm, output: Path, animation: bool = True) -> tuple[dict, object]:
    trajectory, events, phases = pick_and_place(robot)
    directory = output / "trajectories"
    plot_joints(
        trajectory, directory / "pick_place_joints.png", "ASTER-6 | pick-and-place joint motion"
    )
    plot_tcp(
        robot, trajectory, directory / "pick_place_tcp.png", "ASTER-6 | pick-and-place TCP path"
    )
    save_trajectory(directory / "pick_place.csv", trajectory)
    xyz = np.array([robot.fk(q)[:3, 3] for q in trajectory.q])
    write_json(
        directory / "pick_place_samples.json",
        {
            "t_s": trajectory.t.tolist(),
            "q_rad": trajectory.q.tolist(),
            "tcp_m": xyz.tolist(),
            "events": events,
            "phases": phases,
        },
    )
    metrics = {
        **trajectory.metrics(robot),
        "path_length_m": float(np.linalg.norm(np.diff(xyz, axis=0), axis=1).sum()),
        "samples": len(trajectory.t),
        "events": events,
        "phases": phases,
        "gripper": ParallelGripper(robot.config).metrics(),
        "status": "SIMULATED ideal kinematics with scripted object attachment; no contact or collision physics",
    }
    write_json(directory / "pick_place_metrics.json", metrics)
    if animation:
        animate_fk(robot, trajectory, directory / "pick_place_fk.gif", events)
    return metrics, trajectory


def control_demo(robot: RobotArm, output: Path, trajectory=None) -> dict:
    import matplotlib.pyplot as plt

    directory = output / "control"
    target = robot.config["home"] + np.deg2rad(robot.config["demo"]["control_step_deg"])
    step = simulate_pid(
        robot,
        stationary(target, duration=robot.config["demo"]["control_step_duration_s"], samples=501),
        initial=robot.config["home"],
    )
    if trajectory is None:
        trajectory = joint_trajectory(
            robot,
            robot.config["home"],
            robot.config["poses"]["place"],
            duration=robot.config["demo"]["trajectory_duration_s"],
        )
    tracking = simulate_pid(robot, trajectory)
    style()
    figure, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True, constrained_layout=True)
    for j in range(6):
        axes[0].plot(
            step.t, np.rad2deg(step.actual[:, j] - robot.config["home"][j]), label=f"J{j + 1}"
        )
        axes[1].plot(step.t, np.rad2deg(step.error[:, j]))
        axes[2].plot(step.t, step.torque[:, j])
    axes[0].axhline(5, color="#aaa", ls=":")
    axes[0].axhline(-5, color="#aaa", ls=":")
    axes[0].legend(ncol=6)
    axes[0].set_ylabel("Motion from start [deg]")
    axes[1].set_ylabel("Position error [deg]")
    axes[2].set(ylabel="Command torque [N·m]", xlabel="Time [s]")
    figure.suptitle(
        "PID position step | assumed independent inertia and damping plants", weight="bold"
    )
    save(figure, directory / "pid_step_response.png")
    figure, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True, constrained_layout=True)
    for j in range(6):
        axes[0].plot(tracking.t, tracking.desired[:, j], ls="--", color=COLORS[j], alpha=0.45)
        axes[0].plot(tracking.t, tracking.actual[:, j], color=COLORS[j], label=f"J{j + 1}")
        axes[1].plot(tracking.t, np.rad2deg(tracking.error[:, j]), color=COLORS[j])
        axes[2].plot(tracking.t, tracking.torque[:, j], color=COLORS[j])
    axes[0].legend(ncol=6)
    axes[0].set_ylabel("Position [rad]\nDesired dashed / actual solid")
    axes[1].set_ylabel("Position error [deg]")
    axes[2].set(ylabel="Command torque [N·m]", xlabel="Time [s]")
    figure.suptitle("PID trajectory tracking | no feedforward, gravity or coupling", weight="bold")
    save(figure, directory / "pid_tracking.png")
    np.savetxt(
        directory / "tracking.csv",
        np.column_stack((tracking.t, tracking.desired, tracking.actual, tracking.torque)),
        delimiter=",",
        header=",".join(
            [
                "t_s",
                *[f"desired_q{j}_rad" for j in range(1, 7)],
                *[f"actual_q{j}_rad" for j in range(1, 7)],
                *[f"torque{j}_Nm" for j in range(1, 7)],
            ]
        ),
        comments="",
        fmt="%.10g",
    )
    settlement = []
    for j in range(6):
        outside = np.flatnonzero(
            np.abs(step.error[:, j])
            > abs(np.deg2rad(robot.config["demo"]["control_step_deg"][j])) * 0.02
        )
        settlement.append(
            None
            if len(outside) and outside[-1] == len(step.t) - 1
            else float(step.t[outside[-1] + 1])
            if len(outside)
            else 0.0
        )
    metrics = {
        "step": {**step.metrics(), "settling_time_2percent_s": settlement},
        "tracking": {
            **tracking.metrics(),
            "overall_rmse_rad": float(np.sqrt(np.mean(tracking.error**2))),
        },
        "status": "SIMULATED simplified independent second-order joints; not full manipulator dynamics or physical performance",
    }
    write_json(directory / "metrics.json", metrics)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all", action="store_true", help="Generate all numerical demonstrations (default)."
    )
    parser.add_argument("--workspace", action="store_true")
    parser.add_argument("--trajectory", action="store_true")
    parser.add_argument("--pick-place", action="store_true", dest="pick_place")
    parser.add_argument("--control", action="store_true")
    parser.add_argument("--no-animation", action="store_true")
    parser.add_argument("--samples", type=int, help="Override workspace sample count.")
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    arguments = parser.parse_args()
    run_all = arguments.all or not any(
        [arguments.workspace, arguments.trajectory, arguments.pick_place, arguments.control]
    )
    robot = RobotArm()
    metrics = {}
    trajectory = None
    if run_all or arguments.workspace:
        metrics["workspace"] = workspace_demo(robot, arguments.output_dir, arguments.samples)
    if run_all or arguments.trajectory:
        metrics["trajectory"] = trajectory_demo(robot, arguments.output_dir)
    if run_all or arguments.pick_place:
        metrics["pick_place"], trajectory = pick_place_demo(
            robot, arguments.output_dir, not arguments.no_animation
        )
    if run_all or arguments.control:
        metrics["control"] = control_demo(robot, arguments.output_dir, trajectory)
    summary = {"robot": robot.config["name"], "results": str(arguments.output_dir.resolve())}
    if "workspace" in metrics:
        summary["workspace_samples"] = metrics["workspace"]["samples"]
        summary["shoulder_reach_m"] = robot.reach
    if "trajectory" in metrics:
        summary["move_l_xy_drift_m"] = metrics["trajectory"]["move_l_max_xy_drift_m"]
    if "pick_place" in metrics:
        summary["pick_place_duration_s"] = metrics["pick_place"]["duration_s"]
        summary["pick_place_acceleration_limit_fraction"] = metrics["pick_place"][
            "max_acceleration_limit_fraction"
        ]
    if "control" in metrics:
        summary["tracking_rmse_rad"] = metrics["control"]["tracking"]["overall_rmse_rad"]
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
