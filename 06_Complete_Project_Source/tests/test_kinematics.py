import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from robotarm.kinematics import IKError, RobotArm, rotation, translation


def test_rigid_transforms_and_zero_configuration():
    robot = RobotArm()
    transform = robot.fk(np.zeros(6))
    np.testing.assert_allclose(transform[:3, 3], [robot.reach, 0, robot.height], atol=1e-12)
    np.testing.assert_allclose(transform[:3, :3], np.eye(3), atol=1e-12)
    for axis in "xyz":
        rotated = rotation(axis, 0.731)
        np.testing.assert_allclose(rotated[:3, :3].T @ rotated[:3, :3], np.eye(3), atol=1e-12)
        assert np.linalg.det(rotated[:3, :3]) == pytest.approx(1)
    np.testing.assert_allclose(translation([1, 2, 3])[:3, 3], [1, 2, 3])


def test_vertical_reach_and_part_frames():
    robot = RobotArm()
    q = robot.config["poses"]["vertical"]
    np.testing.assert_allclose(robot.fk(q)[:3, 3], [0, 0, robot.height + robot.reach], atol=1e-12)
    frames = robot.frames(robot.config["home"])
    assert frames["joint_transforms"].shape == (6, 4, 4)
    np.testing.assert_allclose(frames["joint_transforms"][:, :3, 3], frames["joint_origins"])
    np.testing.assert_allclose(np.linalg.norm(frames["joint_axes"], axis=1), np.ones(6))


def test_jacobian_against_world_frame_finite_difference():
    robot = RobotArm()
    rng = np.random.default_rng(45)
    for _ in range(8):
        q = rng.uniform(robot.limits[:, 0] + 0.2, robot.limits[:, 1] - 0.2)
        analytical = robot.jacobian(q)
        numerical = np.zeros((6, 6))
        epsilon = 1e-6
        for joint in range(6):
            increment = np.zeros(6)
            increment[joint] = epsilon
            plus, minus = robot.fk(q + increment), robot.fk(q - increment)
            numerical[:3, joint] = (plus[:3, 3] - minus[:3, 3]) / (2 * epsilon)
            numerical[3:, joint] = Rotation.from_matrix(
                plus[:3, :3] @ minus[:3, :3].T
            ).as_rotvec() / (2 * epsilon)
        np.testing.assert_allclose(analytical, numerical, atol=3e-9)


def test_random_fk_ik_fk_from_perturbed_seeds():
    robot = RobotArm()
    rng = np.random.default_rng(20261005)
    for _ in range(20):
        q = rng.uniform(robot.limits[:, 0] + 0.15, robot.limits[:, 1] - 0.15)
        seed = np.clip(q + rng.normal(0, 0.3, 6), robot.limits[:, 0], robot.limits[:, 1])
        assert not np.allclose(q, seed)
        target = robot.fk(q)
        result = robot.solve_ik(target, seed)
        position_error, angular_error = robot.pose_error(result.q, target)
        assert position_error < robot.position_tolerance
        assert angular_error < robot.orientation_tolerance
        assert np.all(result.q >= robot.limits[:, 0]) and np.all(result.q <= robot.limits[:, 1])


def test_unreachable_pose_and_bad_transform():
    robot = RobotArm()
    target = np.eye(4)
    target[0, 3] = 10
    with pytest.raises(IKError, match="geometric reach"):
        robot.ik(target)
    target[0, 3] = 0.4
    target[0, 0] = 2
    with pytest.raises(ValueError, match="SO\\(3\\)"):
        robot.ik(target)


def test_joint_bound_enforcement_and_extension_singularity():
    robot = RobotArm()
    with pytest.raises(ValueError, match="limits"):
        robot.fk(robot.limits[:, 1] + 0.1)
    assert robot.singular_values(np.zeros(6))[-1] < 1e-12


@pytest.mark.parametrize("part", ["last_row", "rotation"])
def test_rigid_pose_absolute_tolerances_do_not_admit_relative_scale_error(part):
    robot = RobotArm()
    target = robot.fk(robot.config["home"])
    if part == "last_row":
        target[3, 3] += 1e-6
    else:
        target[:3, :3] *= 1 + 1e-6
    with pytest.raises(ValueError):
        robot.solve_ik(target)
