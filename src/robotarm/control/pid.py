"""Independent inertia/damping plants with torque-saturated PID feedback."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from robotarm.kinematics import RobotArm
from robotarm.planning import Trajectory


@dataclass
class ControlResult:
    t: np.ndarray
    desired: np.ndarray
    actual: np.ndarray
    error: np.ndarray
    torque: np.ndarray
    velocity: np.ndarray
    integrator: np.ndarray

    def metrics(self) -> dict:
        return {
            "rmse_rad": np.sqrt(np.mean(self.error**2, axis=0)).tolist(),
            "max_abs_error_rad": np.max(np.abs(self.error), axis=0).tolist(),
            "final_error_rad": self.error[-1].tolist(),
            "peak_command_torque_Nm": np.max(np.abs(self.torque), axis=0).tolist(),
        }


def simulate_pid(
    robot: RobotArm,
    trajectory: Trajectory,
    initial: np.ndarray | None = None,
    gain_scale: float = 1.0,
    mode: str = "PID",
    feedforward: bool = False,
) -> ControlResult:
    """Integrate I*qdd + b*qd = command with semi-implicit Euler.

    Torque limits and conditional-integration antiwindup are modelled. No coupled
    rigid-body dynamics, gravity, backlash, sensor noise, friction or drive delay
    is represented. Optional inertia/damping feedforward is explicitly selected.
    """
    cfg = robot.config["control"]
    dt = float(cfg["dt"])
    if dt <= 0 or gain_scale <= 0 or mode not in ("P", "PI", "PD", "PID"):
        raise ValueError("Invalid integration step, gain scale, or controller mode.")
    if np.any(np.diff(trajectory.t) <= 0):
        raise ValueError("Trajectory times must be strictly increasing.")
    inertia, damping = np.asarray(cfg["inertia"]), np.asarray(cfg["viscous_damping"])
    kp = np.asarray(cfg["kp"]) * gain_scale
    ki = np.asarray(cfg["ki"]) * gain_scale if "I" in mode else np.zeros(6)
    kd = np.asarray(cfg["kd"]) * gain_scale if "D" in mode else np.zeros(6)
    limits = np.asarray(cfg["torque_limits"])
    if np.any(inertia <= 0) or np.any(limits <= 0):
        raise ValueError("Inertias and torque limits must be positive.")
    duration = trajectory.duration
    steps = int(np.ceil(duration / dt))
    t = np.linspace(trajectory.t[0], trajectory.t[-1], steps + 1)
    step = duration / steps
    desired = np.column_stack([np.interp(t, trajectory.t, trajectory.q[:, j]) for j in range(6)])
    desired_velocity = np.column_stack(
        [np.interp(t, trajectory.t, trajectory.dq[:, j]) for j in range(6)]
    )
    desired_acceleration = np.column_stack(
        [np.interp(t, trajectory.t, trajectory.ddq[:, j]) for j in range(6)]
    )
    actual, velocity, torque, integral_history = (np.zeros_like(desired) for _ in range(4))
    actual[0] = robot.check_joints(trajectory.q[0] if initial is None else initial)
    integral = np.zeros(6)
    for index in range(steps):
        error = desired[index] - actual[index]
        derivative = desired_velocity[index] - velocity[index]
        feed = (
            inertia * desired_acceleration[index] + damping * desired_velocity[index]
            if feedforward
            else 0.0
        )
        trial = integral + error * step
        raw = kp * error + ki * trial + kd * derivative + feed
        saturated = np.clip(raw, -limits, limits)
        integrate = (np.abs(raw) <= limits) | (error * (raw - saturated) < 0)
        integral = np.where(integrate, trial, integral)
        torque[index] = np.clip(
            kp * error + ki * integral + kd * derivative + feed, -limits, limits
        )
        integral_history[index] = integral
        acceleration = (torque[index] - damping * velocity[index]) / inertia
        velocity[index + 1] = velocity[index] + acceleration * step
        trial_position = actual[index] + velocity[index + 1] * step
        actual[index + 1] = np.clip(trial_position, robot.limits[:, 0], robot.limits[:, 1])
        velocity[index + 1] = np.where(actual[index + 1] != trial_position, 0, velocity[index + 1])
    torque[-1], integral_history[-1] = torque[-2], integral_history[-2]
    return ControlResult(t, desired, actual, desired - actual, torque, velocity, integral_history)
