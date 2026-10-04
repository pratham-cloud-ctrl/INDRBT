"""Read the shared SI specification, including packaged installations."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import yaml


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
    if not isinstance(cfg, dict) or cfg.get("units", {}).get("length") != "m":
        raise ValueError("Configuration must declare SI length units (m).")
    cfg = deepcopy(cfg)
    cfg["joint_limits"] = np.deg2rad(np.asarray(cfg["joint_limits_deg"], float))
    cfg["velocity_limits"] = np.deg2rad(np.asarray(cfg["velocity_limits_deg_s"], float))
    cfg["acceleration_limits"] = np.deg2rad(
        np.asarray(cfg["acceleration_limits_deg_s2"], float)
    )
    cfg["home"] = np.deg2rad(np.asarray(cfg["home_deg"], float))
    cfg["poses"] = {name: np.deg2rad(q) for name, q in cfg["poses_deg"].items()}
    limits = cfg["joint_limits"]
    if limits.shape != (6, 2) or not np.all(np.isfinite(limits)) or np.any(limits[:, 0] >= limits[:, 1]):
        raise ValueError("Expected six ordered, finite joint bounds.")
    for field in ("velocity_limits", "acceleration_limits"):
        values = cfg[field]
        if values.shape != (6,) or np.any(values <= 0) or not np.all(np.isfinite(values)):
            raise ValueError(f"{field} must contain six positive finite numbers.")
    for q in [cfg["home"], *cfg["poses"].values()]:
        if q.shape != (6,) or np.any(q < limits[:, 0]) or np.any(q > limits[:, 1]):
            raise ValueError("A named pose violates configured joint bounds.")
    required_geometry = (
        "shoulder_height", "upper_arm_length", "forearm_length", "wrist_roll_length",
        "wrist_pitch_length", "tool_length",
    )
    if any(not np.isfinite(cfg["geometry"][key]) or cfg["geometry"][key] <= 0 for key in required_geometry):
        raise ValueError("Kinematic dimensions must be positive finite SI values.")
    if cfg["gripper"]["max_opening"] <= 0 or not 0 < cfg["gripper"]["screw_efficiency"] <= 1:
        raise ValueError("Invalid gripper range or screw efficiency.")
    return cfg
