import numpy as np
import pytest

from robotarm.kinematics import RobotArm
from robotarm.planning import concatenate, joint_trajectory, move_linear, stationary
from robotarm.simulation import pick_and_place


@pytest.mark.parametrize("kind", ["linear", "cubic", "quintic"])
def test_joint_trajectory_endpoints_and_limits(kind):
    robot = RobotArm()
    start, end = robot.config["home"], robot.config["poses"]["place"]
    trajectory = joint_trajectory(robot, start, end, kind=kind, samples=1001)
    np.testing.assert_allclose(trajectory.q[0], start)
    np.testing.assert_allclose(trajectory.q[-1], end)
    assert np.all(trajectory.q >= robot.limits[:, 0]) and np.all(trajectory.q <= robot.limits[:, 1])
    assert np.max(np.abs(trajectory.dq) / robot.config["velocity_limits"]) <= 1
    assert np.max(np.abs(trajectory.ddq) / robot.config["acceleration_limits"]) <= 1
    if kind != "linear":
        np.testing.assert_allclose(trajectory.dq[[0, -1]], 0, atol=1e-12)
    if kind == "quintic":
        np.testing.assert_allclose(trajectory.ddq[[0, -1]], 0, atol=1e-12)


def test_too_short_or_invalid_trajectory_rejected():
    robot = RobotArm()
    with pytest.raises(ValueError, match="below required"):
        joint_trajectory(robot, robot.config["home"], robot.config["poses"]["place"], duration=0.01)
    with pytest.raises(ValueError, match="kind"):
        joint_trajectory(robot, robot.config["home"], robot.config["home"], kind="bad")


def test_cartesian_move_l_tracks_line_and_limits():
    robot = RobotArm()
    start = robot.config["poses"]["pick"]
    initial = robot.fk(start)
    target = initial.copy()
    target[2, 3] += 0.06
    trajectory = move_linear(robot, start, target, samples=61)
    poses = np.array([robot.fk(q) for q in trajectory.q])
    np.testing.assert_allclose(
        poses[:, :2, 3], np.tile(initial[:2, 3], (61, 1)), atol=robot.position_tolerance
    )
    np.testing.assert_allclose(poses[-1], target, atol=1e-5)
    assert np.max(np.abs(trajectory.dq) / robot.config["velocity_limits"]) < 1
    assert np.max(np.abs(trajectory.ddq) / robot.config["acceleration_limits"]) < 1


@pytest.mark.parametrize("invalid_kind", ["homogeneous", "rotation", "nonfinite", "shape"])
def test_cartesian_move_l_rejects_invalid_pose_before_interpolation(invalid_kind):
    robot = RobotArm()
    target = robot.fk(robot.config["home"])
    if invalid_kind == "homogeneous":
        target[3, 3] = 2
    elif invalid_kind == "rotation":
        target[:3, :3] *= 2
    elif invalid_kind == "nonfinite":
        target[0, 3] = np.nan
    else:
        target = target[:3]
    with pytest.raises(ValueError):
        move_linear(robot, robot.config["home"], target, samples=21)


def test_concatenation_preserves_endpoints_and_rejects_discontinuity():
    robot = RobotArm()
    home, place = robot.config["home"], robot.config["poses"]["place"]
    first = joint_trajectory(robot, home, place)
    dwell = stationary(place)
    combined = concatenate(first, dwell)
    assert combined.duration == pytest.approx(first.duration + dwell.duration)
    assert np.all(np.diff(combined.t) > 0)
    with pytest.raises(ValueError, match="position discontinuity"):
        concatenate(first, stationary(home))


def test_pick_place_returns_home_with_valid_events_and_segment_limits():
    robot = RobotArm()
    trajectory, events, phases = pick_and_place(robot)
    np.testing.assert_allclose(trajectory.q[0], robot.config["home"])
    np.testing.assert_allclose(trajectory.q[-1], robot.config["home"], atol=1e-9)
    assert [event["action"] for event in events] == ["close", "open"]
    assert events[0]["time_s"] < events[1]["time_s"] < trajectory.duration
    for event, pose_name in zip(events, ["pick", "place"]):
        index = np.argmin(np.abs(trajectory.t - event["time_s"]))
        actual = robot.fk(trajectory.q[index])
        np.testing.assert_allclose(actual, robot.fk(robot.config["poses"][pose_name]), atol=1e-5)
    assert all(phase["max_velocity_limit_fraction"] <= 1 for phase in phases)
    assert all(phase["max_acceleration_limit_fraction"] <= 1 for phase in phases)
