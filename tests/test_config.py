import numpy as np
import pytest
import yaml

from robotarm.config import load_config


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
    clean = {key: value for key, value in config.items() if key not in ("home", "poses", "joint_limits", "velocity_limits", "acceleration_limits")}
    clean["velocity_limits_deg_s"][2] = -1
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(clean), encoding="utf-8")
    with pytest.raises(ValueError, match="velocity_limits"):
        load_config(path)
