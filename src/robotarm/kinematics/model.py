"""Explicit body-frame transform chain, geometric Jacobian, bounded numerical IK."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from robotarm.config import load_config


def translation(vector: np.ndarray | list[float]) -> np.ndarray:
    transform = np.eye(4)
    transform[:3, 3] = vector
    return transform


def rotation(axis: str, angle: float) -> np.ndarray:
    transform = np.eye(4)
    vector = np.zeros(3)
    vector["xyz".index(axis.lower())] = angle
    transform[:3, :3] = Rotation.from_rotvec(vector).as_matrix()
    return transform


class IKError(ValueError):
    """Pose could not be reconstructed within limits and residual tolerances."""


@dataclass(frozen=True)
class IKResult:
    q: np.ndarray
    position_error_m: float
    orientation_error_rad: float
    attempts: int
    evaluations: int


class RobotArm:
    """Six revolute joints; angles in radians, distances in metres."""

    axes = ("z", "y", "y", "x", "y", "x")

    def __init__(self, config: dict | None = None):
        self.config = load_config() if config is None else config
        geometry = self.config["geometry"]
        self.height = float(geometry["shoulder_height"])
        self.lengths = np.array(
            [
                0.0,
                geometry["upper_arm_length"],
                geometry["forearm_length"],
                geometry["wrist_roll_length"],
                geometry["wrist_pitch_length"],
                geometry["tool_length"],
            ]
        )
        self.limits = np.asarray(self.config["joint_limits"], float)
        self.reach = float(self.lengths.sum())
        self.position_tolerance = self.config["targets"]["ik_position_tolerance_m"]
        self.orientation_tolerance = self.config["targets"]["ik_orientation_tolerance_rad"]

    def check_joints(self, q: np.ndarray, enforce_limits: bool = True) -> np.ndarray:
        q = np.asarray(q, float)
        if q.shape != (6,) or not np.all(np.isfinite(q)):
            raise ValueError("Expected six finite joint angles in radians.")
        if enforce_limits and (
            np.any(q < self.limits[:, 0] - 1e-10) or np.any(q > self.limits[:, 1] + 1e-10)
        ):
            raise ValueError("Joint position exceeds configured limits.")
        return q

    def frames(self, q: np.ndarray, enforce_limits: bool = True) -> dict[str, np.ndarray]:
        """World origins/axes and local part frames after each joint rotation.

        joint_transforms, link_transforms, and transforms are aliases for the six
        transforms AFTER R(q_i) and BEFORE Tx(length_i). Base is identity; tcp is
        the final transform after the last tool translation. All values use SI.
        """
        q = self.check_joints(q, enforce_limits)
        transform = translation([0.0, 0.0, self.height])
        origins, axes, rotated, segments = [], [], [], []
        for axis, angle, length in zip(self.axes, q, self.lengths):
            origin = transform[:3, 3].copy()
            unit = np.zeros(3)
            unit["xyz".index(axis)] = 1.0
            origins.append(origin)
            axes.append(transform[:3, :3] @ unit)
            transform = transform @ rotation(axis, angle)
            rotated.append(transform.copy())
            transform = transform @ translation([length, 0.0, 0.0])
            segments.append([origin, transform[:3, 3].copy()])
        part_frames = np.asarray(rotated)
        return {
            "joint_origins": np.asarray(origins),
            "joint_axes": np.asarray(axes),
            "joint_transforms": part_frames,
            "link_transforms": part_frames,
            "transforms": part_frames,
            "link_segments": np.asarray(segments),
            "base": np.eye(4),
            "tcp": transform,
        }

    def fk(self, q: np.ndarray, enforce_limits: bool = True) -> np.ndarray:
        return self.frames(q, enforce_limits)["tcp"]

    def jacobian(self, q: np.ndarray) -> np.ndarray:
        """World-frame [linear m/s; angular rad/s] geometric Jacobian."""
        frames = self.frames(q)
        displacement = frames["tcp"][:3, 3] - frames["joint_origins"]
        linear = np.cross(frames["joint_axes"], displacement).T
        return np.vstack((linear, frames["joint_axes"].T))

    def singular_values(self, q: np.ndarray) -> np.ndarray:
        """Dimensionless Jacobian singular values, translation scaled by reach."""
        scaled = self.jacobian(q).copy()
        scaled[:3] /= self.reach
        return np.linalg.svd(scaled, compute_uv=False)

    def pose_error(self, q: np.ndarray, target: np.ndarray) -> tuple[float, float]:
        actual = self.fk(q)
        return (
            float(np.linalg.norm(actual[:3, 3] - target[:3, 3])),
            float(Rotation.from_matrix(target[:3, :3] @ actual[:3, :3].T).magnitude()),
        )

    @staticmethod
    def check_pose(target: np.ndarray) -> np.ndarray:
        """Validate a proper finite rigid transform before IK or interpolation."""
        target = np.asarray(target, float)
        if target.shape != (4, 4) or not np.all(np.isfinite(target)):
            raise ValueError("Target must be a finite 4x4 homogeneous transform.")
        if not np.allclose(target[3], [0, 0, 0, 1], atol=1e-9):
            raise ValueError("Target has invalid homogeneous last row.")
        orientation = target[:3, :3]
        if not np.allclose(orientation.T @ orientation, np.eye(3), atol=1e-7) or not np.isclose(
            np.linalg.det(orientation), 1, atol=1e-7
        ):
            raise ValueError("Target rotation must belong to SO(3).")
        return target

    def solve_ik(
        self, target: np.ndarray, seed: np.ndarray | None = None, max_attempts: int = 14
    ) -> IKResult:
        """Bounded multiseed least squares with position and SO(3) log residuals.

        Deterministic reseeding makes reports reproducible. This local numerical
        solver can fail for a reachable target; exhaustion is not a reachability
        proof. Every returned solution is verified against both pose tolerances.
        """
        target = self.check_pose(target)
        if max_attempts < 1:
            raise ValueError("At least one IK attempt is required.")
        if (
            np.linalg.norm(target[:3, 3] - [0, 0, self.height])
            > self.reach + self.position_tolerance
        ):
            raise IKError("Target is outside the shoulder-centred geometric reach bound.")
        lower, upper = self.limits.T
        rng = np.random.default_rng(611)
        first = self.config["home"] if seed is None else self.check_joints(seed, False)
        seeds = [first, self.config["home"], (lower + upper) / 2]
        seeds += list(rng.uniform(lower, upper, size=(max_attempts, 6)))
        best = (np.inf, np.inf)
        evaluations = 0

        def residual(q: np.ndarray) -> np.ndarray:
            actual = self.fk(q)
            # Position scaled by characteristic length balances metres/radians.
            position = (actual[:3, 3] - target[:3, 3]) / self.reach
            orientation_error = Rotation.from_matrix(target[:3, :3] @ actual[:3, :3].T).as_rotvec()
            return np.concatenate((position, orientation_error))

        for attempt, start in enumerate(seeds[:max_attempts], 1):
            solution = least_squares(
                residual,
                np.clip(start, lower + 1e-9, upper - 1e-9),
                bounds=(lower, upper),
                ftol=1e-11,
                xtol=1e-11,
                gtol=1e-11,
                max_nfev=350,
                x_scale="jac",
            )
            evaluations += solution.nfev
            position_error, orientation_error = self.pose_error(solution.x, target)
            if position_error + self.reach * orientation_error < best[0] + self.reach * best[1]:
                best = position_error, orientation_error
            if (
                position_error <= self.position_tolerance
                and orientation_error <= self.orientation_tolerance
            ):
                return IKResult(solution.x, position_error, orientation_error, attempt, evaluations)
        raise IKError(
            f"IK exhausted {max_attempts} starts; best errors {best[0]:.3g} m, "
            f"{best[1]:.3g} rad. Pose may be inaccessible or local search may have failed."
        )

    def ik(
        self, target: np.ndarray, seed: np.ndarray | None = None, max_attempts: int = 14
    ) -> np.ndarray:
        return self.solve_ik(target, seed, max_attempts).q
