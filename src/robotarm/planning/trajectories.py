"""Endpoint interpolation and sampled Cartesian continuation planning."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

from robotarm.kinematics import RobotArm


@dataclass
class Trajectory:
    t: np.ndarray
    q: np.ndarray
    dq: np.ndarray
    ddq: np.ndarray
    label: str = "joint motion"

    @property
    def duration(self) -> float:
        return float(self.t[-1] - self.t[0])

    def metrics(self, robot: RobotArm) -> dict:
        return {
            "duration_s": self.duration,
            "peak_velocity_rad_s": np.max(np.abs(self.dq), axis=0).tolist(),
            "peak_acceleration_rad_s2": np.max(np.abs(self.ddq), axis=0).tolist(),
            "max_velocity_limit_fraction": float(np.max(np.abs(self.dq) / robot.config["velocity_limits"])),
            "max_acceleration_limit_fraction": float(np.max(np.abs(self.ddq) / robot.config["acceleration_limits"])),
        }


def joint_trajectory(
    robot: RobotArm, start: np.ndarray, end: np.ndarray, duration: float | None = None,
    kind: str = "quintic", samples: int = 201,
) -> Trajectory:
    """MOVE J with analytic derivatives and conservative minimum duration.

    Linear denotes only a constant-velocity interior segment. Its instantaneous
    start/stop accelerations are unbounded; use cubic or quintic for stop-to-stop
    commands. Cubic has finite endpoint acceleration but an acceleration jump.
    """
    start, end = robot.check_joints(start), robot.check_joints(end)
    if samples < 3:
        raise ValueError("At least three trajectory samples are required.")
    delta = end - start
    factors = {"linear": (1.0, 0.0), "cubic": (1.5, 6.0), "quintic": (1.875, 10 / np.sqrt(3))}
    if kind not in factors:
        raise ValueError("Trajectory kind must be linear, cubic, or quintic.")
    velocity_factor, acceleration_factor = factors[kind]
    minimum = max(
        float(np.max(velocity_factor * np.abs(delta) / robot.config["velocity_limits"])),
        float(np.sqrt(np.max(acceleration_factor * np.abs(delta) / robot.config["acceleration_limits"]))),
        0.02,
    )
    if duration is None:
        duration = minimum * 1.001
    if not np.isfinite(duration) or duration <= 0:
        raise ValueError("Duration must be positive and finite.")
    if duration < minimum - 1e-10:
        raise ValueError(f"Duration {duration:.4g} s is below required {minimum:.4g} s.")
    t = np.linspace(0, duration, samples)
    u = t / duration
    if kind == "linear":
        s, ds, dds = u, np.ones_like(u), np.zeros_like(u)
    elif kind == "cubic":
        s, ds, dds = 3 * u**2 - 2 * u**3, 6 * u - 6 * u**2, 6 - 12 * u
    else:
        s = 10 * u**3 - 15 * u**4 + 6 * u**5
        ds = 30 * u**2 - 60 * u**3 + 30 * u**4
        dds = 60 * u - 180 * u**2 + 120 * u**3
    return Trajectory(t, start + s[:, None] * delta, ds[:, None] * delta / duration, dds[:, None] * delta / duration**2, kind)


def move_linear(
    robot: RobotArm, start: np.ndarray, target: np.ndarray,
    duration: float = 1.0, samples: int = 101,
) -> Trajectory:
    """MOVE L: straight TCP + shortest SO(3) SLERP, continuation numerical IK.

    Quintic Cartesian time law; joint derivatives are finite differences. A
    single uniform time scaling enforces limits at the returned samples. This
    does not certify derivative bounds between samples or collision clearance.
    """
    start = robot.check_joints(start)
    if samples < 21 or duration <= 0 or not np.isfinite(duration):
        raise ValueError("MOVE L requires at least 21 samples and a positive duration.")
    initial = robot.fk(start)
    u = np.linspace(0, 1, samples)
    progress = 10 * u**3 - 15 * u**4 + 6 * u**5
    rotations = Rotation.from_matrix(np.stack([initial[:3, :3], target[:3, :3]]))
    orientation = Slerp([0, 1], rotations)(progress).as_matrix()
    q = [start.copy()]
    for index in range(1, samples):
        pose = np.eye(4)
        pose[:3, :3] = orientation[index]
        pose[:3, 3] = initial[:3, 3] + progress[index] * (target[:3, 3] - initial[:3, 3])
        solved = robot.ik(pose, q[-1], max_attempts=6)
        if np.max(np.abs(solved - q[-1])) > np.deg2rad(30):
            raise ValueError("MOVE L encountered a discontinuous IK branch; choose another start/path.")
        q.append(solved)
    q = np.asarray(q)
    t = np.linspace(0, duration, samples)
    dq = np.gradient(q, t, axis=0, edge_order=2)
    ddq = np.gradient(dq, t, axis=0, edge_order=2)
    # Exact endpoint values of a stop-to-stop quintic law away from singularities.
    dq[[0, -1]] = 0
    ddq[[0, -1]] = 0
    scale = max(
        1.0, float(np.max(np.abs(dq) / robot.config["velocity_limits"])),
        float(np.sqrt(np.max(np.abs(ddq) / robot.config["acceleration_limits"]))),
    ) * 1.01
    return Trajectory(t * scale, q, dq / scale, ddq / scale**2, "MOVE L")


def stationary(q: np.ndarray, duration: float = 0.5, samples: int = 21) -> Trajectory:
    if duration <= 0 or samples < 2:
        raise ValueError("A dwell needs positive duration and at least two samples.")
    q = np.asarray(q, float)
    positions = np.tile(q, (samples, 1))
    return Trajectory(np.linspace(0, duration, samples), positions, np.zeros_like(positions), np.zeros_like(positions), "dwell")


def concatenate(*segments: Trajectory) -> Trajectory:
    if not segments:
        raise ValueError("At least one segment is required.")
    times, positions, velocities, accelerations = [], [], [], []
    elapsed = 0.0
    previous = None
    for index, segment in enumerate(segments):
        if previous is not None and not np.allclose(previous.q[-1], segment.q[0], atol=1e-7):
            raise ValueError("Trajectory concatenation has a position discontinuity.")
        if previous is not None and (not np.allclose(previous.dq[-1], segment.dq[0], atol=1e-7) or not np.allclose(previous.ddq[-1], segment.ddq[0], atol=1e-6)):
            raise ValueError("Trajectory concatenation has a velocity or acceleration discontinuity.")
        selection = slice(None) if index == 0 else slice(1, None)
        times.append(segment.t[selection] - segment.t[0] + elapsed)
        positions.append(segment.q[selection])
        velocities.append(segment.dq[selection])
        accelerations.append(segment.ddq[selection])
        elapsed += segment.duration
        previous = segment
    return Trajectory(np.concatenate(times), np.vstack(positions), np.vstack(velocities), np.vstack(accelerations), "concatenated motion")
