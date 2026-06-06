"""Unit tests for radar clustering and binary AEB decisions."""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from control.brake import AEBState, BinaryAEB, BinaryBrakeConfig
from radar_cluster import RadarClusterConfig, RadarClusterTracker


@dataclass
class Point:
    x_forward_m: float
    y_right_m: float
    z_up_m: float
    relative_velocity_mps: float
    world_location: object = None


class RadarTrackerTests(unittest.TestCase):
    def setUp(self):
        self.config = RadarClusterConfig(
            min_points=2,
            confirm_frames=3,
            release_frames=4,
            min_max_height_above_road_m=0.2,
        )
        self.tracker = RadarClusterTracker(self.config)

    def points(self, x=20.0, velocity=-5.0):
        return [
            Point(x, 0.0, 0.3, velocity),
            Point(x + 0.3, 0.1, 0.5, velocity + 0.1),
        ]

    def test_track_requires_confirmation(self):
        for frame in range(1, 4):
            tracks = self.tracker.update(
                self.points(20.0 - frame * 0.25),
                height_getter=lambda point: 0.5,
                timestamp_s=frame * 0.05,
            )
            self.assertEqual(len(tracks), 1)
            self.assertEqual(tracks[0].confirmed, frame >= 3)

    def test_missed_track_cannot_remain_confirmed(self):
        for frame in range(1, 4):
            tracks = self.tracker.update(
                self.points(),
                height_getter=lambda point: 0.5,
                timestamp_s=frame * 0.05,
            )
        self.assertTrue(tracks[0].confirmed)

        tracks = self.tracker.update([], timestamp_s=0.20)
        self.assertTrue(tracks[0].is_stale)
        self.assertFalse(tracks[0].confirmed)

        tracks = self.tracker.update(
            self.points(19.0),
            height_getter=lambda point: 0.5,
            timestamp_s=0.25,
        )
        self.assertFalse(tracks[0].is_stale)
        self.assertFalse(tracks[0].confirmed)
        self.assertEqual(tracks[0].hit_streak, 1)

    def test_prediction_keeps_fast_closing_track_identity(self):
        config = RadarClusterConfig(
            min_points=2,
            confirm_frames=1,
            match_distance_m=0.75,
            match_velocity_mps=2.0,
            prediction_enabled=True,
            max_prediction_time_s=0.30,
            min_max_height_above_road_m=0.2,
        )
        tracker = RadarClusterTracker(config)
        first = tracker.update(
            self.points(x=20.0, velocity=-10.0),
            height_getter=lambda point: 0.5,
            timestamp_s=1.0,
        )
        second = tracker.update(
            self.points(x=18.0, velocity=-10.0),
            height_getter=lambda point: 0.5,
            timestamp_s=1.2,
        )
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0].track_id, first[0].track_id)


class BinaryAEBTests(unittest.TestCase):
    def test_stopping_distance_can_trigger_before_ttc(self):
        config = BinaryBrakeConfig(
            brake_ttc_s=1.0,
            use_stopping_distance=True,
            response_time_s=0.5,
            ego_emergency_decel_mps2=6.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=2.0,
        )
        aeb = BinaryAEB(config)
        decision = aeb.decide(
            16.0,
            -5.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
        )
        self.assertEqual(decision.state, AEBState.BRAKE)
        self.assertLess(decision.distance_margin_m, 0.0)
        self.assertIn("distance", decision.reason)

    def test_brake_is_held_until_stopped(self):
        aeb = BinaryAEB(BinaryBrakeConfig(hold_brake_until_stopped=True))
        first = aeb.decide(10.0, -10.0, timestamp_s=1.0, ego_speed_mps=10.0)
        self.assertEqual(first.state, AEBState.BRAKE)
        held = aeb.decide(9.0, -1.0, timestamp_s=2.0, ego_speed_mps=2.0)
        self.assertEqual(held.state, AEBState.BRAKE)
        released = aeb.decide(None, None, timestamp_s=3.0, ego_speed_mps=0.1)
        self.assertEqual(released.state, AEBState.RELEASE)


if __name__ == "__main__":
    unittest.main()
