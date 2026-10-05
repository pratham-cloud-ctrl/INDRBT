"""Kinematic tasks with explicit gripper event timing."""

from __future__ import annotations

from robotarm.kinematics import RobotArm
from robotarm.planning import Trajectory, concatenate, joint_trajectory, move_linear, stationary


def pick_and_place(robot: RobotArm) -> tuple[Trajectory, list[dict], list[dict]]:
    home = robot.config["home"]
    pick = robot.fk(robot.config["poses"]["pick"])
    place = robot.fk(robot.config["poses"]["place"])
    # Task clearance and dwell are demonstration assumptions, recorded in metrics.
    settings = robot.config["demo"]
    clearance = settings["approach_clearance"]
    dwell = settings["gripper_dwell_s"]
    above_pick, above_place = pick.copy(), place.copy()
    above_pick[2, 3] += clearance
    above_place[2, 3] += clearance
    q_above_pick = robot.ik(above_pick, robot.config["poses"]["pick"])
    q_above_place = robot.ik(above_place, robot.config["poses"]["place"])
    segments = []
    phases = []
    events = []
    elapsed = 0.0

    def append(name: str, trajectory: Trajectory):
        nonlocal elapsed
        phases.append(
            {
                "name": name,
                "start_s": elapsed,
                "end_s": elapsed + trajectory.duration,
                **trajectory.metrics(robot),
            }
        )
        segments.append(trajectory)
        elapsed += trajectory.duration

    append("MOVE J home to above object", joint_trajectory(robot, home, q_above_pick))
    descend = move_linear(robot, q_above_pick, pick)
    append("MOVE L descend to object", descend)
    append("gripper close dwell", stationary(descend.q[-1], dwell))
    events.append(
        {
            "time_s": elapsed - dwell / 2,
            "action": "close",
            "opening_m": settings["object_width"],
            "tcp_m": pick[:3, 3].tolist(),
        }
    )
    lift = move_linear(robot, descend.q[-1], above_pick)
    append("MOVE L lift object", lift)
    append("MOVE J transfer above destination", joint_trajectory(robot, lift.q[-1], q_above_place))
    lower = move_linear(robot, q_above_place, place)
    append("MOVE L lower object", lower)
    append("gripper open dwell", stationary(lower.q[-1], dwell))
    events.append(
        {
            "time_s": elapsed - dwell / 2,
            "action": "open",
            "opening_m": robot.config["gripper"]["max_opening"],
            "tcp_m": place[:3, 3].tolist(),
        }
    )
    retreat = move_linear(robot, lower.q[-1], above_place)
    append("MOVE L retreat", retreat)
    append("MOVE J return home", joint_trajectory(robot, retreat.q[-1], home))
    return concatenate(*segments), events, phases
