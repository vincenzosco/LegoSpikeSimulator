"""Kinematics of a two-wheel drive base.

Conventions used everywhere in the simulator:

* lengths are millimetres, angles are degrees, time is milliseconds;
* the field is a right-handed mathematical plane: ``+x`` east, ``+y`` north;
* ``heading`` is the direction the robot points, ``0`` = east, growing
  counter-clockwise (so 90 = north).
"""

from __future__ import annotations

import math

import pytest

from spikesim.kinematics import (
    Pose,
    integrate,
    motor_degrees_to_mm,
    motor_to_mm_s,
    steering_to_wheel_velocities,
)

WHEEL = 56.0
TRACK = 112.0


def test_motor_degrees_to_mm_uses_circumference():
    # One full turn of a 56 mm wheel rolls pi * 56 mm.
    assert motor_degrees_to_mm(360, WHEEL) == pytest.approx(math.pi * 56.0)
    assert motor_degrees_to_mm(180, WHEEL) == pytest.approx(math.pi * 28.0)
    assert motor_degrees_to_mm(-360, WHEEL) == pytest.approx(-math.pi * 56.0)
    assert motor_degrees_to_mm(0, WHEEL) == 0.0


def test_motor_to_mm_s_is_degrees_per_second_converted():
    assert motor_to_mm_s(360, WHEEL) == pytest.approx(math.pi * 56.0)
    assert motor_to_mm_s(0, WHEEL) == 0.0
    assert motor_to_mm_s(-720, WHEEL) == pytest.approx(-2 * math.pi * 56.0)


def test_straight_drive_moves_only_forward():
    pose = Pose()
    for _ in range(10):
        pose = integrate(pose, 100.0, 100.0, 100.0, TRACK)
    # 100 mm/s for 10 x 100 ms = 1 s -> 100 mm.
    assert pose.x == pytest.approx(100.0)
    assert pose.y == pytest.approx(0.0)
    assert pose.heading == pytest.approx(0.0)


def test_pivot_in_place_keeps_position_and_turns_counter_clockwise():
    pose = integrate(Pose(), -50.0, 50.0, 1000.0, 100.0)
    assert pose.x == pytest.approx(0.0)
    assert pose.y == pytest.approx(0.0)
    # omega = (right - left) / track = 100 / 100 = 1 rad/s during 1 s.
    assert pose.heading == pytest.approx(math.degrees(1.0))


def test_turning_left_is_counter_clockwise_and_right_is_clockwise():
    left_slow = integrate(Pose(), 50.0, 100.0, 1000.0, 100.0)
    assert left_slow.heading > 0, "left wheel slower -> turns left (CCW)"
    right_slow = integrate(Pose(), 100.0, 50.0, 1000.0, 100.0)
    assert right_slow.heading < 0, "right wheel slower -> turns right (CW)"


def test_curved_path_ends_where_a_circle_predicts():
    # v = 75 mm/s, omega = 0.5 rad/s -> radius 150 mm, half a second of travel.
    pose = Pose()
    for _ in range(10):
        pose = integrate(pose, 50.0, 100.0, 50.0, 100.0)
    heading_rad = math.radians(pose.heading)
    assert pose.x == pytest.approx(150.0 * math.sin(heading_rad), abs=1e-6)
    assert pose.y == pytest.approx(150.0 * (1 - math.cos(heading_rad)), abs=1e-6)


def test_pose_is_immutable():
    pose = Pose(1.0, 2.0, 3.0)
    with pytest.raises(Exception):
        pose.x = 9.0


def test_steering_zero_runs_both_wheels_at_velocity():
    assert steering_to_wheel_velocities(360, 0) == (360.0, 360.0)


def test_steering_positive_turns_right():
    # steering +100 -> right: the left wheel doubles, the right wheel stops.
    assert steering_to_wheel_velocities(360, 100) == (720.0, 0.0)


def test_steering_negative_turns_left():
    assert steering_to_wheel_velocities(360, -100) == (0.0, 720.0)


def test_steering_is_clamped_outside_minus_100_100():
    assert steering_to_wheel_velocities(360, 250) == (720.0, 0.0)
    assert steering_to_wheel_velocities(360, -250) == (0.0, 720.0)


def test_steering_survives_negative_velocity():
    # Driving backwards while steering right still curbs to the robot's right.
    assert steering_to_wheel_velocities(-360, 100) == (-720.0, 0.0)
