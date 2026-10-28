"""Consistent SI labels, simple FK geometry, and repository-friendly animation."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np

from robotarm.kinematics import RobotArm
from robotarm.planning import Trajectory


COLORS = ["#1565a5", "#e67925", "#148a78", "#ab4685", "#7452aa", "#81702b"]


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.2,
            "figure.facecolor": "white",
            "axes.prop_cycle": plt.cycler(color=COLORS),
            "savefig.dpi": 180,
        }
    )


def save(figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def plot_joints(trajectory: Trajectory, path: Path, title: str) -> None:
    style()
    figure, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True, constrained_layout=True)
    for axis, values, label in zip(
        axes,
        (trajectory.q, trajectory.dq, trajectory.ddq),
        ("Position [rad]", "Velocity [rad/s]", "Acceleration [rad/s²]"),
    ):
        for joint in range(6):
            axis.plot(trajectory.t, values[:, joint], label=f"J{joint + 1}")
        axis.set_ylabel(label)
    axes[0].legend(ncol=6, loc="upper right")
    axes[-1].set_xlabel("Time [s]")
    figure.suptitle(title, weight="bold")
    save(figure, path)


def plot_tcp(robot: RobotArm, trajectory: Trajectory, path: Path, title: str) -> None:
    style()
    xyz = np.array([robot.fk(q)[:3, 3] for q in trajectory.q])
    figure = plt.figure(figsize=(12, 5), constrained_layout=True)
    three = figure.add_subplot(121, projection="3d")
    three.plot(*xyz.T, lw=2, color=COLORS[0])
    three.scatter(*xyz[0], s=40, color=COLORS[2], label="Start / finish")
    three.set(xlabel="X [m]", ylabel="Y [m]", zlabel="Z [m]")
    three.set_box_aspect(np.maximum(np.ptp(xyz, axis=0), 0.1))
    three.legend()
    time = figure.add_subplot(122)
    for coordinate, label in enumerate("XYZ"):
        time.plot(trajectory.t, xyz[:, coordinate], label=label)
    time.set(xlabel="Time [s]", ylabel="TCP coordinate [m]")
    time.legend()
    figure.suptitle(title, weight="bold")
    save(figure, path)


def representative_poses(robot: RobotArm, path: Path) -> None:
    style()
    figure = plt.figure(figsize=(13, 8), constrained_layout=True)
    for index, (name, q) in enumerate(robot.config["poses"].items()):
        axis = figure.add_subplot(2, 3, index + 1, projection="3d")
        frames = robot.frames(q)
        vertices = np.vstack(([0, 0, 0], frames["joint_origins"], frames["tcp"][:3, 3]))
        axis.plot(*vertices.T, "o-", color=COLORS[0], lw=4, ms=4)
        axis.set(
            xlim=(-0.85, 0.85),
            ylim=(-0.85, 0.85),
            zlim=(-0.25, 1.05),
            xlabel="X [m]",
            ylabel="Y [m]",
            zlabel="Z [m]",
            title=name.title(),
        )
        axis.set_box_aspect((1, 1, 0.8))
    figure.suptitle("INDRBT | representative poses from the actual FK chain", weight="bold")
    save(figure, path)


def coordinate_frames(robot: RobotArm, path: Path) -> None:
    style()
    frames = robot.frames(robot.config["home"])
    figure = plt.figure(figsize=(9, 7), constrained_layout=True)
    axis = figure.add_subplot(projection="3d")
    vertices = np.vstack(([0, 0, 0], frames["joint_origins"], frames["tcp"][:3, 3]))
    axis.plot(*vertices.T, "o-", lw=5, ms=5, color="#8996a7")
    for index, transform in enumerate([np.eye(4), *frames["joint_transforms"], frames["tcp"]]):
        origin = transform[:3, 3]
        for coordinate, color in enumerate(["#d34b4b", "#2b9960", "#3075c9"]):
            direction = transform[:3, coordinate] * 0.055
            axis.quiver(*origin, *direction, color=color, arrow_length_ratio=0.2)
        # J1/J2 share an origin; place labels at distinct offsets.
        axis.text(
            *(origin + [0, 0, 0.012 + index * 0.004]),
            "Base" if index == 0 else "TCP" if index == 7 else f"J{index}",
            fontsize=9,
        )
    axis.set(
        xlabel="X [m]",
        ylabel="Y [m]",
        zlabel="Z [m]",
        xlim=(-0.05, 0.65),
        ylim=(-0.2, 0.2),
        zlim=(0, 0.6),
    )
    axis.set_box_aspect((1.2, 0.6, 1))
    axis.set_title(
        "Local part frames after each joint rotation\nX red · Y green · Z blue", weight="bold"
    )
    save(figure, path)


def animate_fk(
    robot: RobotArm, trajectory: Trajectory, path: Path, events: list[dict], frames_count: int = 120
) -> None:
    """Each frame is evaluated from FK; geometry is an explicit proxy model."""
    style()
    figure = plt.figure(figsize=(8, 7))
    axis = figure.add_subplot(projection="3d")
    axis.set(
        xlim=(-0.05, 0.8),
        ylim=(-0.48, 0.48),
        zlim=(0, 0.85),
        xlabel="X [m]",
        ylabel="Y [m]",
        zlabel="Z [m]",
    )
    axis.set_box_aspect((1, 1, 1))
    axis.view_init(elev=23, azim=-55)
    axis.set_title(
        "INDRBT | FK-driven pick-and-place\nProxy geometry · ideal kinematic playback",
        weight="bold",
    )
    all_xyz = np.array([robot.fk(q)[:3, 3] for q in trajectory.q])
    axis.plot(*all_xyz.T, color="#b3c3d4", lw=1, alpha=0.65)
    (body,) = axis.plot([], [], [], "o-", color=COLORS[0], lw=8, ms=9)
    (jaw_a,) = axis.plot([], [], [], color=COLORS[1], lw=4)
    (jaw_b,) = axis.plot([], [], [], color=COLORS[1], lw=4)
    (payload,) = axis.plot([], [], [], "s", color=COLORS[2], ms=11)
    text_artist = axis.text2D(0.03, 0.92, "", transform=axis.transAxes)
    frame_times = np.linspace(trajectory.t[0], trajectory.t[-1], frames_count)
    pick_point = next((event["tcp_m"] for event in events if event["action"] == "close"), [0, 0, 0])
    place_point = next(
        (event["tcp_m"] for event in events if event["action"] == "open"), pick_point
    )

    def set_line(artist, points):
        artist.set_data(points[:, 0], points[:, 1])
        artist.set_3d_properties(points[:, 2])

    def update(frame_index):
        time = frame_times[frame_index]
        q = np.array([np.interp(time, trajectory.t, trajectory.q[:, j]) for j in range(6)])
        frames = robot.frames(q)
        tcp = frames["tcp"]
        vertices = np.vstack(([0, 0, 0], frames["joint_origins"], tcp[:3, 3]))
        set_line(body, vertices)
        occurred = [event for event in events if event["time_s"] <= time]
        last = occurred[-1] if occurred else None
        held = last is not None and last["action"] == "close"
        gap = (
            robot.config["demo"]["object_width"] if held else robot.config["gripper"]["max_opening"]
        )
        for artist, side in ((jaw_a, -1), (jaw_b, 1)):
            local = np.array([[-0.05, side * gap / 2, 0], [0, side * gap / 2, 0]])
            world = local @ tcp[:3, :3].T + tcp[:3, 3]
            set_line(artist, world)
        object_point = tcp[:3, 3] if held else place_point if last is not None else pick_point
        set_line(payload, np.asarray(object_point)[None])
        text_artist.set_text(
            f"t = {time:5.2f} s   |   jaws {'holding' if held else 'open'}\nObject follows scripted attachment; no contact physics"
        )
        return body, jaw_a, jaw_b, payload, text_artist

    animation = FuncAnimation(figure, update, frames=frames_count, interval=75, blit=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    animation.save(path, writer=PillowWriter(fps=15), dpi=90)
    plt.close(figure)
