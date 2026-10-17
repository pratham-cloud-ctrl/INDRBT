import numpy as np
import pytest
import yaml

from robotarm.config import load_config
from robotarm.kinematics import RobotArm


def test_configuration_has_si_and_derived_radians():
    config = load_config()
    assert config["units"]["length"] == "m"
    assert config["joint_limits"].shape == (6, 2)
    np.testing.assert_allclose(config["home"], np.deg2rad(config["home_deg"]))


def test_loading_does_not_share_mutable_arrays():
    first = load_config()
    first["home"][0] = 100
    assert load_config()["home"][0] == 0


def test_bad_configuration_rejected(tmp_path):
    config = load_config()
    clean = {
        key: value
        for key, value in config.items()
        if key not in ("home", "poses", "joint_limits", "velocity_limits", "acceleration_limits")
    }
    clean["velocity_limits_deg_s"][2] = -1
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(clean), encoding="utf-8")
    with pytest.raises(ValueError, match="velocity_limits"):
        load_config(path)


@pytest.mark.parametrize("pose_field", ["home_deg", "poses_deg"])
def test_nonfinite_named_pose_rejected_when_loading(tmp_path, pose_field):
    config = load_config()
    raw = {
        key: value
        for key, value in config.items()
        if key not in ("home", "poses", "joint_limits", "velocity_limits", "acceleration_limits")
    }
    if pose_field == "home_deg":
        raw[pose_field][0] = float("nan")
    else:
        raw[pose_field]["pick"][2] = float("nan")
    path = tmp_path / "nonfinite-pose.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="finite angles"):
        load_config(path)


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("units", "torque", "N*mm"),
        ("gripper", "screw_lead", 0),
        ("gripper", "max_opening", float("nan")),
        ("gripper", "grip_safety_factor", 0.5),
        ("control", "inertia", [1, 1, 0, 1, 1, 1]),
        ("control", "viscous_damping", [1, 1, -1, 1, 1, 1]),
        ("control", "kp", [1, 1, float("nan"), 1, 1, 1]),
        ("control", "dt", float("inf")),
        ("mass", "payload", -1),
        ("materials", "aluminum", {"density": 2700, "young_modulus": 0, "yield_strength": 240e6}),
        ("actuators", "efficiencies", [0.75, 0.75, 1.1, 0.75, 0.75, 0.75]),
        ("geometry", "wall_thickness", 0.1),
        ("targets", "ik_position_tolerance_m", float("nan")),
        ("demo", "object_width", 0.2),
    ],
)
def test_modified_configuration_cannot_bypass_model_validation(section, field, value):
    config = load_config()
    config[section][field] = value
    with pytest.raises(ValueError):
        RobotArm(config)


def test_unloaded_models_and_zero_controller_gains_are_valid():
    config = load_config()
    config["mass"]["payload"] = 0
    config["gripper"]["total_normal_force_target"] = 0
    config["control"]["ki"] = [0] * 6
    RobotArm(config)
