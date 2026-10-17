"""Read the shared SI specification, including packaged installations."""

from __future__ import annotations

from copy import deepcopy
from numbers import Real
from pathlib import Path

import numpy as np
import yaml


def _scalar(section: dict, key: str, *, zero_allowed: bool = False) -> float:
    """Validate a physical scalar before it enters a denominator or model."""
    value = section[key]
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not np.isfinite(value)
        or value < 0
        or (value == 0 and not zero_allowed)
    ):
        qualifier = "nonnegative" if zero_allowed else "positive"
        raise ValueError(f"{key} must be a {qualifier} finite scalar.")
    return float(value)


def _vector(section: dict, key: str, *, zero_allowed: bool = False) -> np.ndarray:
    values = np.asarray(section[key], dtype=float)
    if (
        values.shape != (6,)
        or not np.all(np.isfinite(values))
        or np.any(values < 0 if zero_allowed else values <= 0)
    ):
        qualifier = "nonnegative" if zero_allowed else "positive"
        raise ValueError(f"{key} must contain six {qualifier} finite numbers.")
    return values


def validate_control(control: dict) -> None:
    """Check independent-axis plant and gain parameters, including runtime edits."""
    _scalar(control, "dt")
    for key in ("inertia", "torque_limits"):
        _vector(control, key)
    for key in ("viscous_damping", "kp", "ki", "kd"):
        _vector(control, key, zero_allowed=True)


def validate_config(cfg: dict) -> None:
    """Validate the shared model's units, finite values and physical domains.

    This checks admissible inputs, not whether chosen gains are stable or a
    proposed mechanism is physically qualified. It accepts zero payload/forces
    for unloaded analyses and zero gains for controller comparisons.
    """
    expected_units = {"length": "m", "angle": "rad", "mass": "kg", "time": "s", "torque": "N*m"}
    try:
        if any(cfg["units"].get(key) != unit for key, unit in expected_units.items()):
            raise ValueError("Configuration must declare SI units: m, rad, kg, s, N*m.")
        limits = np.asarray(cfg["joint_limits"], dtype=float)
        if (
            limits.shape != (6, 2)
            or not np.all(np.isfinite(limits))
            or np.any(limits[:, 0] >= limits[:, 1])
        ):
            raise ValueError("Expected six ordered, finite joint bounds.")
        for key in ("velocity_limits", "acceleration_limits"):
            _vector(cfg, key)
        for q in [cfg["home"], *cfg["poses"].values()]:
            q = np.asarray(q, dtype=float)
            if (
                q.shape != (6,)
                or not np.all(np.isfinite(q))
                or np.any(q < limits[:, 0])
                or np.any(q > limits[:, 1])
            ):
                raise ValueError("A named pose must contain six finite angles within joint bounds.")
        geometry = cfg["geometry"]
        for key in (
            "shoulder_height",
            "upper_arm_length",
            "forearm_length",
            "wrist_roll_length",
            "wrist_pitch_length",
            "tool_length",
            "upper_arm_width",
            "upper_arm_depth",
            "forearm_width",
            "forearm_depth",
            "wall_thickness",
            "base_diameter",
            "tool_flange_diameter",
        ):
            _scalar(geometry, key)
        if 2 * geometry["wall_thickness"] >= min(
            geometry[key]
            for key in ("upper_arm_width", "upper_arm_depth", "forearm_width", "forearm_depth")
        ):
            raise ValueError("wall_thickness leaves no hollow link section.")
        for key in (
            "base",
            "turret",
            "upper_arm",
            "forearm",
            "wrist_roll",
            "wrist_pitch",
            "flange_gripper",
            "payload",
        ):
            _scalar(cfg["mass"], key, zero_allowed=True)
        for material in cfg["materials"].values():
            for key in material:
                _scalar(material, key)
        gripper = cfg["gripper"]
        for key in (
            "max_opening",
            "finger_length",
            "finger_width",
            "finger_thickness",
            "screw_lead",
            "grip_safety_factor",
        ):
            _scalar(gripper, key)
        for key in ("total_normal_force_target", "friction_coefficient", "motor_torque"):
            _scalar(gripper, key, zero_allowed=True)
        if _scalar(gripper, "screw_efficiency") > 1 or gripper["grip_safety_factor"] < 1:
            raise ValueError("Screw efficiency must be <= 1 and grip_safety_factor must be >= 1.")
        actuators = cfg["actuators"]
        _vector(actuators, "gear_ratios")
        if (
            np.any(_vector(actuators, "efficiencies") > 1)
            or _scalar(actuators, "safety_factor") < 1
        ):
            raise ValueError("Actuator efficiencies must be <= 1 and safety_factor must be >= 1.")
        validate_control(cfg["control"])
        for key in (
            "repeatability_m",
            "gravity",
            "ik_position_tolerance_m",
            "ik_orientation_tolerance_rad",
        ):
            _scalar(cfg["targets"], key)
        _scalar(cfg["targets"], "payload_kg", zero_allowed=True)
        demo = cfg["demo"]
        for key in (
            "approach_clearance",
            "gripper_dwell_s",
            "workspace_voxel_pitch",
            "trajectory_duration_s",
            "control_step_duration_s",
            "object_width",
        ):
            _scalar(demo, key)
        if demo["object_width"] > gripper["max_opening"]:
            raise ValueError("object_width exceeds max_opening.")
        count = demo["workspace_samples"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 4:
            raise ValueError("workspace_samples must be an integer >= 4.")
        step = np.asarray(demo["control_step_deg"], dtype=float)
        if step.shape != (6,) or not np.all(np.isfinite(step)):
            raise ValueError("control_step_deg must contain six finite angles.")
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError(f"Missing or malformed configuration field: {error}") from error


def load_config(path: str | Path | None = None) -> dict:
    """Load and validate robot parameters; derived angle arrays use radians.

    A checkout uses config/robot.yaml. A wheel must include robotarm/data/robot.yaml,
    copied from that authoritative source by the packaging build hook.
    """
    if path is None:
        checkout = Path(__file__).resolve().parents[2] / "config" / "robot.yaml"
        packaged = Path(__file__).parent / "data" / "robot.yaml"
        path = checkout if checkout.exists() else packaged
    with Path(path).open(encoding="utf-8") as stream:
        cfg = yaml.safe_load(stream)
    if not isinstance(cfg, dict):
        raise ValueError("Configuration must contain a parameter mapping.")
    cfg = deepcopy(cfg)
    try:
        cfg["joint_limits"] = np.deg2rad(np.asarray(cfg["joint_limits_deg"], float))
        cfg["velocity_limits"] = np.deg2rad(np.asarray(cfg["velocity_limits_deg_s"], float))
        cfg["acceleration_limits"] = np.deg2rad(
            np.asarray(cfg["acceleration_limits_deg_s2"], float)
        )
        cfg["home"] = np.deg2rad(np.asarray(cfg["home_deg"], float))
        cfg["poses"] = {name: np.deg2rad(q) for name, q in cfg["poses_deg"].items()}
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError(f"Missing or malformed angle configuration field: {error}") from error
    validate_config(cfg)
    return cfg
