"""Unit tests for radar clustering and binary AEB decisions."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from pathlib import Path

from control.brake import AEBState, BinaryAEB, BinaryBrakeConfig
from core.radar_aeb_pipeline import RadarAEBPipeline
from core.radar_object import radar_object_from_cluster
from core.target_selector import select_aeb_target
from perception.radar.radar_object_tracker import RadarClusterConfig, RadarClusterTracker
from scripts.run_radar_aeb_scenarios import (
    legacy_target_spec,
    match_cluster_to_scenario_actor,
    nearest_frame_path,
    select_evidence_events,
)


@dataclass
class Point:
    x_forward_m: float
    y_right_m: float
    z_up_m: float
    relative_velocity_mps: float
    world_location: object = None


@dataclass
class ClusterLike:
    track_id: int
    x_forward_m: float
    y_right_m: float
    z_up_m: float
    relative_velocity_mps: float
    point_count: int
    max_height_above_road_m: object
    world_location: object
    confirmed: bool = True
    hit_streak: int = 3
    age_frames: int = 3
    missed_frames: int = 0

    @property
    def is_stale(self):
        return self.missed_frames > 0


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

    def test_brake_can_release_before_stop_when_hold_disabled(self):
        aeb = BinaryAEB(BinaryBrakeConfig(hold_brake_until_stopped=False))
        first = aeb.decide(10.0, -10.0, timestamp_s=1.0, ego_speed_mps=10.0)
        self.assertEqual(first.state, AEBState.BRAKE)
        released = aeb.decide(None, None, timestamp_s=2.0, ego_speed_mps=5.0)
        self.assertEqual(released.state, AEBState.RELEASE)

    def test_staged_brake_uses_lower_command_for_moderate_risk(self):
        config = BinaryBrakeConfig(
            brake_mode="staged",
            brake_ttc_s=1.5,
            use_stopping_distance=True,
            response_time_s=0.2,
            ego_emergency_decel_mps2=8.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=1.0,
            staged_medium_brake=0.75,
            staged_hard_brake=0.90,
            staged_emergency_brake=1.0,
        )
        aeb = BinaryAEB(config)

        decision = aeb.decide(
            32.0,
            -20.0,
            timestamp_s=1.0,
            ego_speed_mps=21.0,
        )

        self.assertEqual(AEBState.BRAKE, decision.state)
        self.assertAlmostEqual(0.75, decision.brake)

    def test_staged_brake_keeps_full_command_for_emergency(self):
        config = BinaryBrakeConfig(
            brake_mode="staged",
            staged_emergency_distance_m=18.0,
            staged_emergency_brake=1.0,
        )
        aeb = BinaryAEB(config)

        decision = aeb.decide(
            12.0,
            -15.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
        )

        self.assertEqual(AEBState.BRAKE, decision.state)
        self.assertAlmostEqual(1.0, decision.brake)

    def test_pid_brake_ramps_moderate_risk(self):
        config = BinaryBrakeConfig(
            brake_mode="pid",
            brake_ttc_s=1.5,
            use_stopping_distance=True,
            response_time_s=0.2,
            ego_emergency_decel_mps2=8.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=1.0,
            pid_min_brake=0.35,
            pid_brake_rise_rate_per_s=4.0,
            pid_default_dt_s=0.05,
            pid_emergency_distance_m=10.0,
            pid_emergency_margin_m=-10.0,
            pid_emergency_ttc_s=0.5,
        )
        aeb = BinaryAEB(config)

        first = aeb.decide(
            32.0,
            -20.0,
            timestamp_s=1.0,
            ego_speed_mps=21.0,
        )
        second = aeb.decide(
            31.0,
            -20.0,
            timestamp_s=1.05,
            ego_speed_mps=21.0,
        )

        self.assertEqual(AEBState.BRAKE, first.state)
        self.assertGreater(first.brake, 0.0)
        self.assertLess(first.brake, 1.0)
        self.assertGreater(second.brake, first.brake)
        self.assertLess(second.brake, 1.0)

    def test_pid_brake_reaches_full_for_emergency(self):
        config = BinaryBrakeConfig(
            brake_mode="pid",
            pid_emergency_distance_m=18.0,
            pid_emergency_rise_rate_per_s=30.0,
            pid_default_dt_s=0.05,
        )
        aeb = BinaryAEB(config)

        decision = aeb.decide(
            12.0,
            -15.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
        )

        self.assertEqual(AEBState.BRAKE, decision.state)
        self.assertAlmostEqual(1.0, decision.brake)

    def test_pid_hold_brake_keeps_vehicle_stopping(self):
        config = BinaryBrakeConfig(
            brake_mode="pid",
            hold_brake_until_stopped=True,
            pid_hold_brake=0.75,
            pid_brake_rise_rate_per_s=10.0,
            pid_default_dt_s=0.05,
        )
        aeb = BinaryAEB(config)

        aeb.decide(10.0, -10.0, timestamp_s=1.0, ego_speed_mps=10.0)
        held = aeb.decide(None, None, timestamp_s=1.05, ego_speed_mps=2.0)

        self.assertEqual(AEBState.BRAKE, held.state)
        self.assertGreaterEqual(held.brake, 0.75)

    def test_pid_target_margin_increases_brake_demand(self):
        base_config = BinaryBrakeConfig(
            brake_mode="pid_v1",
            use_stopping_distance=True,
            response_time_s=0.2,
            ego_emergency_decel_mps2=8.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=1.0,
            pid_kp=0.16,
            pid_ki=0.0,
            pid_kd=0.0,
            pid_min_brake=0.35,
            pid_brake_rise_rate_per_s=20.0,
            pid_default_dt_s=0.05,
            pid_emergency_distance_m=10.0,
            pid_emergency_margin_m=-10.0,
            pid_emergency_ttc_s=0.5,
        )
        comfort_config = BinaryBrakeConfig(
            brake_mode="pid_v2_comfort",
            use_stopping_distance=True,
            response_time_s=0.2,
            ego_emergency_decel_mps2=8.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=1.0,
            pid_kp=0.16,
            pid_ki=0.0,
            pid_kd=0.0,
            pid_min_brake=0.35,
            pid_target_margin_m=2.0,
            pid_brake_rise_rate_per_s=20.0,
            pid_default_dt_s=0.05,
            pid_emergency_distance_m=10.0,
            pid_emergency_margin_m=-10.0,
            pid_emergency_ttc_s=0.5,
        )

        base = BinaryAEB(base_config).decide(
            26.0,
            -15.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
        )
        comfort = BinaryAEB(comfort_config).decide(
            26.0,
            -15.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
        )

        self.assertEqual(AEBState.BRAKE, base.state)
        self.assertEqual(AEBState.BRAKE, comfort.state)
        self.assertGreater(comfort.brake, base.brake)

    def test_pid_target_margin_can_start_braking_early(self):
        base_config = BinaryBrakeConfig(
            brake_mode="pid_v1",
            brake_ttc_s=1.5,
            use_stopping_distance=True,
            response_time_s=0.2,
            ego_emergency_decel_mps2=8.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=1.0,
        )
        comfort_config = BinaryBrakeConfig(
            brake_mode="pid_v2_comfort",
            brake_ttc_s=1.5,
            use_stopping_distance=True,
            response_time_s=0.2,
            ego_emergency_decel_mps2=8.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=1.0,
            pid_target_margin_m=2.0,
        )

        base = BinaryAEB(base_config).decide(
            29.0,
            -15.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
        )
        comfort = BinaryAEB(comfort_config).decide(
            29.0,
            -15.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
        )

        self.assertEqual(AEBState.WARNING, base.state)
        self.assertEqual(AEBState.BRAKE, comfort.state)

    def test_pid_target_margin_respects_lateral_gate(self):
        config = BinaryBrakeConfig(
            brake_mode="pid_v2_comfort",
            brake_ttc_s=1.5,
            use_stopping_distance=True,
            response_time_s=0.2,
            ego_emergency_decel_mps2=8.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=1.0,
            pid_target_margin_m=4.0,
            pid_target_margin_max_lateral_m=0.95,
        )

        centered = BinaryAEB(config).decide(
            29.0,
            -15.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
            target_lateral_m=0.2,
        )
        leaving_lane = BinaryAEB(config).decide(
            29.0,
            -15.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
            target_lateral_m=1.2,
        )

        self.assertEqual(AEBState.BRAKE, centered.state)
        self.assertEqual(AEBState.WARNING, leaving_lane.state)

    def test_staged_pid_soft_stage_caps_early_brake(self):
        config = BinaryBrakeConfig(
            brake_mode="staged_pid",
            brake_ttc_s=1.5,
            use_stopping_distance=True,
            response_time_s=0.2,
            ego_emergency_decel_mps2=8.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=1.0,
            pid_kp=0.80,
            pid_ki=0.0,
            pid_kd=0.0,
            pid_min_brake=0.25,
            pid_target_margin_m=4.0,
            pid_target_margin_max_lateral_m=0.95,
            pid_brake_rise_rate_per_s=50.0,
            pid_default_dt_s=0.05,
            pid_emergency_distance_m=10.0,
            pid_emergency_margin_m=-10.0,
            pid_emergency_ttc_s=0.5,
            staged_soft_brake=0.55,
        )

        decision = BinaryAEB(config).decide(
            29.0,
            -15.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
            target_lateral_m=0.2,
        )

        self.assertEqual(AEBState.BRAKE, decision.state)
        self.assertLessEqual(decision.brake, 0.55)

    def test_staged_pid_hard_stage_allows_stronger_brake(self):
        config = BinaryBrakeConfig(
            brake_mode="staged_pid",
            brake_ttc_s=1.5,
            staged_hard_ttc_s=1.1,
            staged_emergency_ttc_s=0.5,
            staged_soft_brake=0.55,
            staged_medium_brake=0.75,
            staged_hard_brake=0.90,
            staged_emergency_brake=1.0,
            staged_emergency_distance_m=10.0,
            staged_emergency_margin_m=-20.0,
            use_stopping_distance=True,
            response_time_s=0.2,
            ego_emergency_decel_mps2=8.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=1.0,
            pid_kp=0.16,
            pid_ki=0.0,
            pid_kd=0.0,
            pid_min_brake=0.25,
            pid_brake_rise_rate_per_s=50.0,
            pid_default_dt_s=0.05,
            pid_emergency_distance_m=10.0,
            pid_emergency_margin_m=-20.0,
            pid_emergency_ttc_s=0.5,
        )

        decision = BinaryAEB(config).decide(
            16.0,
            -15.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
        )

        self.assertEqual(AEBState.BRAKE, decision.state)
        self.assertGreaterEqual(decision.brake, 0.75)
        self.assertLessEqual(decision.brake, 0.90)

    def test_staged_pid_keeps_lateral_gate_from_pid_v2(self):
        config = BinaryBrakeConfig(
            brake_mode="staged_pid",
            brake_ttc_s=1.5,
            use_stopping_distance=True,
            response_time_s=0.2,
            ego_emergency_decel_mps2=8.0,
            target_emergency_decel_mps2=6.0,
            stopping_distance_offset_m=1.0,
            pid_target_margin_m=4.0,
            pid_target_margin_max_lateral_m=0.95,
        )

        leaving_lane = BinaryAEB(config).decide(
            29.0,
            -15.0,
            timestamp_s=1.0,
            ego_speed_mps=20.0,
            target_lateral_m=1.2,
        )

        self.assertEqual(AEBState.WARNING, leaving_lane.state)


class RadarObjectTests(unittest.TestCase):
    def test_cluster_is_exposed_as_radar_object(self):
        cluster = self._cluster(
            track_id=7,
            x_forward_m=30.0,
            y_right_m=-0.5,
            relative_velocity_mps=-8.0,
            point_count=3,
        )

        obj = radar_object_from_cluster(cluster)

        self.assertEqual(7, obj.object_id)
        self.assertEqual(7, obj.track_id)
        self.assertEqual(30.0, obj.x_forward_m)
        self.assertEqual(-0.5, obj.y_right_m)
        self.assertEqual(8.0, obj.closing_speed_mps)
        self.assertAlmostEqual(3.75, obj.ttc_s)
        self.assertGreater(obj.confidence, 0.0)

    def test_selector_keeps_previous_ttc_priority(self):
        far_fast = radar_object_from_cluster(
            self._cluster(
                track_id=1,
                x_forward_m=40.0,
                relative_velocity_mps=-20.0,
            )
        )
        near_slow = radar_object_from_cluster(
            self._cluster(
                track_id=2,
                x_forward_m=20.0,
                relative_velocity_mps=-5.0,
            )
        )

        target = select_aeb_target([near_slow, far_fast])

        self.assertEqual(1, target.object_id)

    def test_selector_ignores_unconfirmed_or_stale_objects(self):
        unconfirmed = radar_object_from_cluster(
            self._cluster(track_id=1, confirmed=False)
        )
        stale = radar_object_from_cluster(
            self._cluster(track_id=2, missed_frames=1)
        )
        valid = radar_object_from_cluster(self._cluster(track_id=3))

        target = select_aeb_target([unconfirmed, stale, valid])

        self.assertEqual(3, target.object_id)

    def test_target_gate_waits_for_stable_non_urgent_target(self):
        pipeline = RadarAEBPipeline(
            None,
            {
                "target_gate": {
                    "enabled": True,
                    "selected_confirm_frames": 3,
                    "immediate_brake_distance_m": 10.0,
                    "immediate_distance_margin_m": -5.0,
                },
                "brake": {
                    "use_stopping_distance": True,
                    "response_time_s": 0.2,
                    "ego_emergency_decel_mps2": 8.0,
                    "target_emergency_decel_mps2": 6.0,
                    "stopping_distance_offset_m": 1.0,
                },
            },
        )
        target = radar_object_from_cluster(
            self._cluster(
                track_id=10,
                x_forward_m=35.0,
                relative_velocity_mps=-18.0,
            )
        )

        self.assertIsNone(pipeline.target_after_gate(target, 20.0))
        self.assertIsNone(pipeline.target_after_gate(target, 20.0))
        self.assertIs(target, pipeline.target_after_gate(target, 20.0))

    def test_target_gate_allows_urgent_target_immediately(self):
        pipeline = RadarAEBPipeline(
            None,
            {
                "target_gate": {
                    "enabled": True,
                    "selected_confirm_frames": 5,
                    "immediate_brake_distance_m": 22.0,
                    "immediate_distance_margin_m": -4.0,
                },
            },
        )
        target = radar_object_from_cluster(
            self._cluster(
                track_id=11,
                x_forward_m=18.0,
                relative_velocity_mps=-15.0,
            )
        )

        self.assertIs(target, pipeline.target_after_gate(target, 20.0))

    def _cluster(
        self,
        track_id=1,
        x_forward_m=20.0,
        y_right_m=0.0,
        z_up_m=0.5,
        relative_velocity_mps=-10.0,
        point_count=4,
        confirmed=True,
        hit_streak=3,
        age_frames=3,
        missed_frames=0,
    ):
        return ClusterLike(
            track_id=track_id,
            x_forward_m=x_forward_m,
            y_right_m=y_right_m,
            z_up_m=z_up_m,
            relative_velocity_mps=relative_velocity_mps,
            point_count=point_count,
            max_height_above_road_m=0.5,
            world_location=None,
            confirmed=confirmed,
            hit_streak=hit_streak,
            age_frames=age_frames,
            missed_frames=missed_frames,
        )


class ScenarioEvidenceTests(unittest.TestCase):
    def test_selects_warning_brake_and_minimum_gap(self):
        rows = [
            {
                "frame": 10,
                "elapsed_s": 0.1,
                "ego_speed_kph": 50.0,
                "bumper_gap_m": 20.0,
                "ttc_s": 4.0,
                "aeb_state": "NORMAL",
                "aeb_override": 0,
            },
            {
                "frame": 12,
                "elapsed_s": 0.2,
                "ego_speed_kph": 49.0,
                "bumper_gap_m": 18.0,
                "ttc_s": 2.8,
                "aeb_state": "WARNING",
                "aeb_override": 0,
            },
            {
                "frame": 14,
                "elapsed_s": 0.3,
                "ego_speed_kph": 48.0,
                "bumper_gap_m": 15.0,
                "ttc_s": 1.4,
                "aeb_state": "BRAKE",
                "aeb_override": 1,
            },
            {
                "frame": 18,
                "elapsed_s": 0.5,
                "ego_speed_kph": 35.0,
                "bumper_gap_m": 9.0,
                "ttc_s": 1.0,
                "aeb_state": "BRAKE",
                "aeb_override": 1,
            },
        ]

        events = select_evidence_events(rows)

        self.assertEqual(
            ["first_warning", "first_brake", "minimum_gap"],
            [event["name"] for event in events],
        )
        self.assertEqual([12, 14, 18], [event["frame"] for event in events])

    def test_nearest_frame_path(self):
        paths = [Path("00000010.png"), Path("00000014.png")]

        self.assertEqual(Path("00000014.png"), nearest_frame_path(paths, 13))

    def test_can_omit_minimum_gap_for_cut_out(self):
        rows = [
            {
                "frame": 10,
                "elapsed_s": 0.1,
                "ego_speed_kph": 50.0,
                "bumper_gap_m": 20.0,
                "ttc_s": 2.8,
                "aeb_state": "WARNING",
                "aeb_override": 0,
            },
            {
                "frame": 20,
                "elapsed_s": 1.0,
                "ego_speed_kph": 50.0,
                "bumper_gap_m": -5.0,
                "ttc_s": None,
                "aeb_state": "RELEASE",
                "aeb_override": 0,
            },
        ]

        events = select_evidence_events(rows, include_minimum_gap=False)

        self.assertEqual(["first_warning"], [event["name"] for event in events])


@dataclass
class Location:
    x: float
    y: float
    z: float = 0.0


class Actor:
    def __init__(self, location):
        self.location = location

    def get_location(self):
        return self.location


class Cluster:
    def __init__(self, world_location):
        self.world_location = world_location


class ScenarioActorTests(unittest.TestCase):
    def test_legacy_braking_target_is_converted(self):
        spec = legacy_target_spec(
            {
                "type": "braking_lead",
                "initial_gap_m": 30.0,
                "target_speed_kph": 50.0,
                "target_brake_time_s": 1.5,
                "target_brake": 1.0,
            }
        )

        self.assertEqual("target", spec["role"])
        self.assertTrue(spec["hazard"])
        self.assertEqual(50.0, spec["speed_kph"])
        self.assertEqual(1.5, spec["brake_event"]["start_s"])

    def test_cluster_matches_nearest_scenario_actor(self):
        near = {"role": "near", "actor": Actor(Location(10.0, 0.0))}
        far = {"role": "far", "actor": Actor(Location(20.0, 0.0))}

        entry, error = match_cluster_to_scenario_actor(
            Cluster(Location(11.5, 0.0)),
            [far, near],
        )

        self.assertEqual("near", entry["role"])
        self.assertAlmostEqual(1.5, error)

    def test_cluster_outside_match_gate_is_unassigned(self):
        entry, error = match_cluster_to_scenario_actor(
            Cluster(Location(50.0, 0.0)),
            [{"role": "near", "actor": Actor(Location(10.0, 0.0))}],
        )

        self.assertIsNone(entry)
        self.assertEqual(40.0, error)


if __name__ == "__main__":
    unittest.main()
