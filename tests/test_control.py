import numpy as np

from robotarm.kinematics import RobotArm
from robotarm.planning import joint_trajectory, stationary
from robotarm.control import simulate_pid


def test_pid_reduces_step_error_and_respects_saturation():
    robot = RobotArm()
    target = robot.config["home"] + np.deg2rad([5, 5, -5, 5, 5, 5])
    result = simulate_pid(robot, stationary(target, duration=5, samples=501), initial=robot.config["home"])
    assert np.max(np.abs(result.error[-1])) < 0.005
    assert np.linalg.norm(result.error[-1]) < np.linalg.norm(result.error[0]) * 0.1
    assert np.all(np.abs(result.torque) <= np.asarray(robot.config["control"]["torque_limits"]) + 1e-12)


def test_saturation_antiwindup_and_joint_bounds():
    robot = RobotArm()
    robot.config["control"]["torque_limits"] = [0.01] * 6
    target = robot.limits[:, 1] - 0.05
    result = simulate_pid(robot, stationary(target, duration=0.05), initial=robot.limits[:, 0] + 0.05)
    assert np.max(np.abs(result.integrator)) < 1e-12
    assert np.all(result.actual >= robot.limits[:, 0]) and np.all(result.actual <= robot.limits[:, 1])


def test_tracking_finite_and_feedforward_improves_rmse():
    robot = RobotArm()
    trajectory = joint_trajectory(robot, robot.config["home"], robot.config["poses"]["place"], duration=4)
    plain = simulate_pid(robot, trajectory)
    feedforward = simulate_pid(robot, trajectory, feedforward=True)
    assert np.all(np.isfinite(plain.actual))
    assert np.sqrt(np.mean(feedforward.error**2)) < np.sqrt(np.mean(plain.error**2))
