"""Straight-line checks of robot.py (pure math, no ROS needed)."""
import math

import pytest

pytest.importorskip('rclpy')   # robot.py imports ROS messages; runs inside the container

from drawer_picking.robot import check_straight, cup_axis, retime  # noqa: E402

DOWN = (1.0, 0.0, 0.0, 0.0)                      # 180 deg about x: cup axis = -z


def about_z(q, deg):
    """q rotated about its own cup axis (roll) when the axis is world -z."""
    h = math.radians(deg) / 2
    rz = (0.0, 0.0, math.sin(h), math.cos(h))
    x1, y1, z1, w1 = rz
    x2, y2, z2, w2 = q
    return (w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2)


def test_cup_axis_of_down_pose():
    assert cup_axis(DOWN) == pytest.approx((0, 0, -1))


def test_straight_down_along_the_axis_is_ok_and_roll_is_free():
    assert check_straight(((0, 0, 0.1), DOWN), ((0, 0, 0.02), about_z(DOWN, 60))) == pytest.approx(0.08)


def test_sideways_move_is_refused():
    with pytest.raises(RuntimeError, match='off the cup axis'):
        check_straight(((0, 0, 0.1), DOWN), ((0.03, 0, 0.02), DOWN))


def test_tilting_the_cup_is_refused():
    h = math.radians(10) / 2
    tilted = (math.cos(h), 0.0, math.sin(h), 0.0)   # DOWN tilted 10 deg
    with pytest.raises(RuntimeError, match='tilts'):
        check_straight(((0, 0, 0.1), DOWN), ((0, 0, 0.02), tilted))


def test_retime_slows_down_only():
    from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
    traj = JointTrajectory(points=[JointTrajectoryPoint(positions=[0.0], velocities=[1.0])])
    traj.points[0].time_from_start.sec = 1
    retime(traj, 4.0)
    assert traj.points[0].time_from_start.sec == 4 and list(traj.points[0].velocities) == [0.25]
    retime(traj, 1.0)
    assert traj.points[0].time_from_start.sec == 4
