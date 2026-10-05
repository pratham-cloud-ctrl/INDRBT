"""Independent energy-gradient and hand calculation checks on load analysis."""

import numpy as np
import pytest

from analysis.joint_torque_analysis import gravity_torques, potential_energy
from analysis.structural_analysis import hollow_section, beam_response
from robotarm.kinematics import RobotArm


def test_gravity_matches_potential_gradient():
    arm = RobotArm()
    q = np.deg2rad([23, -31, 75, 22, -35, 18])
    eps = 1e-6
    gradient = np.array(
        [
            (
                potential_energy(arm, q + np.eye(6)[i] * eps)
                - potential_energy(arm, q - np.eye(6)[i] * eps)
            )
            / (2 * eps)
            for i in range(6)
        ]
    )
    np.testing.assert_allclose(gravity_torques(arm, q), -gradient, atol=1e-7)


def test_extended_payload_increment():
    arm = RobotArm()
    delta = gravity_torques(arm, np.zeros(6), 5) - gravity_torques(arm, np.zeros(6), 4)
    g = arm.config["geometry"]
    reach = sum(
        g[k]
        for k in (
            "upper_arm_length",
            "forearm_length",
            "wrist_roll_length",
            "wrist_pitch_length",
            "tool_length",
        )
    )
    assert delta[1] == pytest.approx(arm.config["targets"]["gravity"] * reach)
    assert delta[0] == pytest.approx(0)


def test_hollow_section_and_finger_hand_check():
    assert hollow_section(0.08, 0.10, 0.004) > 0
    with pytest.raises(ValueError):
        hollow_section(0.08, 0.10, 0.05)
    result = beam_response(0.06, 0.018 * 0.01**3 / 12, 0.01, 69e9, 100, 0, 0, 240e6)
    assert result["bending_stress_mpa"] == pytest.approx(20)
    assert result["yield_safety_factor"] == pytest.approx(12)
