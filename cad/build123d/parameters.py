"""Read the authoritative SI specification and convert only at the CAD boundary."""

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def parameters():
    cfg = yaml.safe_load((ROOT / "config/robot.yaml").read_text(encoding="utf-8"))
    mm = {key: value * 1000.0 for key, value in cfg["geometry"].items()}
    mm.update(
        {
            "opening": cfg["gripper"]["max_opening"] * 1000,
            "finger_length": cfg["gripper"]["finger_length"] * 1000,
            "finger_width": cfg["gripper"]["finger_width"] * 1000,
            "finger_thickness": cfg["gripper"]["finger_thickness"] * 1000,
        }
    )
    return cfg, mm
