import numpy as np
import pytest

from robotarm.gripper import ParallelGripper


def test_symmetric_jaw_range_and_screw_stroke():
    gripper = ParallelGripper()
    np.testing.assert_allclose(gripper.jaw_positions(gripper.max_opening), [-0.045, 0.045])
    np.testing.assert_allclose(gripper.jaw_positions(0), [0, 0])
    assert gripper.screw_revolutions(0, gripper.max_opening) == pytest.approx(11.25)
    for opening in (-0.001, gripper.max_opening + 0.001, np.nan):
        with pytest.raises(ValueError):
            gripper.jaw_positions(opening)


def test_screw_work_balance_and_motor_force():
    gripper = ParallelGripper()
    force = 200
    torque = gripper.required_torque(force)
    work_input = torque * 2 * np.pi * gripper.parameters["screw_efficiency"]
    work_output = force * gripper.parameters["screw_lead"]
    assert work_input == pytest.approx(work_output)
    assert gripper.ideal_total_normal_force() > force
    with pytest.raises(ValueError):
        gripper.required_torque(-1)
