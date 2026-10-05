"""Independent energy-gradient and hand calculation checks on load analysis."""

import numpy as np
import pytest
from scipy.integrate import quad

from analysis.joint_torque_analysis import gravity_torques, potential_energy
from analysis.structural_analysis import hollow_section, beam_response, calculate
from robotarm.config import load_config
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


def test_serial_tcp_beam_deflection_matches_independent_virtual_work():
    """Integrate curvature with a unit TCP force, including both rigid offsets."""
    config = load_config()
    g, mass = config["geometry"], config["mass"]
    gravity = config["targets"]["gravity"]
    young = config["materials"]["aluminum"]["young_modulus"]
    l1, l2, roll, pitch, tool = [
        g[name]
        for name in (
            "upper_arm_length",
            "forearm_length",
            "wrist_roll_length",
            "wrist_pitch_length",
            "tool_length",
        )
    ]
    reach = l1 + l2 + roll + pitch + tool
    points = [
        (mass["wrist_roll"], l1 + l2 + roll / 2),
        (mass["wrist_pitch"], l1 + l2 + roll + pitch / 2),
        (mass["flange_gripper"], l1 + l2 + roll + pitch + tool / 2),
        (mass["payload"], reach),
    ]
    distributed = [(0, l1, mass["upper_arm"] / l1), (l1, l1 + l2, mass["forearm"] / l2)]

    def moment(x):
        point_loads = sum(weight * gravity * max(position - x, 0) for weight, position in points)
        beam_loads = sum(
            density * gravity * ((end - x) ** 2 - (max(start, x) - x) ** 2) / 2
            for start, end, density in distributed
            if end > x
        )
        return point_loads + beam_loads

    independent = 0
    for start, end, width, depth in [
        (0, l1, g["upper_arm_width"], g["upper_arm_depth"]),
        (l1, l1 + l2, g["forearm_width"], g["forearm_depth"]),
    ]:
        wall = g["wall_thickness"]
        second_moment = (width * depth**3 - (width - 2 * wall) * (depth - 2 * wall) ** 3) / 12
        independent += quad(
            lambda x: moment(x) * (reach - x) / (young * second_moment), start, end
        )[0]
    result = calculate(config)
    assert result["serial_tcp_beam_deflection_mm"] == pytest.approx(independent * 1000, rel=1e-12)
    assert result["serial_tcp_deflection_terms_mm"]["forearm_rotation"] > 0
