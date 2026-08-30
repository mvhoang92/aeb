"""Golden tests for the brake-permission policy boundary."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from control.brake import AEBDecision, AEBState
from core.brake_permission_policy import (
    BrakePermissionContext,
    EmergencyFallbackPolicy,
    HardCameraGatePolicy,
    RadarOnlyPolicy,
    fusion_policy_from_config,
)
from core.fusion_brake_gate import FusionBrakeGate, FusionBrakeGateConfig


def decision(state=AEBState.BRAKE, ttc_s=1.0, margin_m=-3.0):
    return AEBDecision(
        state=state,
        brake=1.0 if state == AEBState.BRAKE else 0.0,
        throttle=0.0,
        ttc_s=ttc_s,
        target_distance_m=17.0,
        relative_velocity_mps=-16.0,
        should_override=state == AEBState.BRAKE,
        reason="radar_reason",
        required_distance_m=20.0,
        distance_margin_m=margin_m,
    )


def target():
    return SimpleNamespace(
        confirmed=True,
        is_stale=False,
        age_frames=5,
        hit_streak=5,
        point_count=12,
        confidence=1.0,
    )


def context(**overrides):
    values = {
        "radar_decision": decision(),
        "target": target(),
        "camera_confirmed": False,
        "camera_reason": "no_yolo_detection",
        "timestamp_s": 10.0,
        "target_path_offset_m": 0.05,
    }
    values.update(overrides)
    return BrakePermissionContext(**values)


class BrakePermissionPolicyTests(unittest.TestCase):
    def test_radar_only_returns_identical_decision_object(self):
        provisional = decision()
        result = RadarOnlyPolicy().evaluate(context(radar_decision=provisional))

        self.assertIs(result.decision, provisional)
        self.assertEqual(result.action, "radar_only")
        self.assertFalse(result.radar_fallback_active)

    def test_hard_gate_blocks_without_camera_and_allows_confirmation(self):
        policy = HardCameraGatePolicy()

        blocked = policy.evaluate(context())
        allowed = policy.evaluate(
            context(camera_confirmed=True, timestamp_s=11.0)
        )

        self.assertEqual(blocked.decision.state, AEBState.RELEASE)
        self.assertEqual(blocked.action, "fusion_blocked_brake")
        self.assertEqual(allowed.decision.state, AEBState.BRAKE)
        self.assertEqual(allowed.action, "camera_confirmed")

    def test_hard_gate_forces_fallback_off_without_changing_other_values(self):
        source = FusionBrakeGateConfig(
            confirmation_hold_s=0.7,
            radar_fallback_enabled=True,
            radar_fallback_min_cluster_points=9,
        )
        policy = HardCameraGatePolicy(source)

        self.assertFalse(policy.config.radar_fallback_enabled)
        self.assertEqual(policy.config.confirmation_hold_s, 0.7)
        self.assertEqual(policy.config.radar_fallback_min_cluster_points, 9)

    def test_fallback_policy_forces_fallback_on(self):
        policy = EmergencyFallbackPolicy(FusionBrakeGateConfig())
        result = policy.evaluate(context())

        self.assertTrue(policy.config.radar_fallback_enabled)
        self.assertEqual(result.decision.state, AEBState.BRAKE)
        self.assertEqual(result.action, "radar_emergency_fallback")
        self.assertTrue(result.radar_fallback_active)

    def test_factory_uses_existing_fallback_flag(self):
        hard = fusion_policy_from_config(FusionBrakeGateConfig())
        fallback = fusion_policy_from_config(
            FusionBrakeGateConfig(radar_fallback_enabled=True)
        )

        self.assertIsInstance(hard, HardCameraGatePolicy)
        self.assertIsInstance(fallback, EmergencyFallbackPolicy)

    def test_adapter_matches_frozen_gate_tick_for_tick(self):
        config = FusionBrakeGateConfig(
            confirmation_hold_s=0.35,
            radar_fallback_enabled=True,
        )
        reference = FusionBrakeGate(config)
        policy = EmergencyFallbackPolicy(config)
        ticks = [
            context(camera_confirmed=True, timestamp_s=20.0),
            context(timestamp_s=20.3),
            context(timestamp_s=20.5),
            context(
                radar_decision=decision(
                    state=AEBState.WARNING,
                    ttc_s=2.0,
                    margin_m=5.0,
                ),
                timestamp_s=20.6,
            ),
        ]

        for tick in ticks:
            expected = reference.apply(
                tick.radar_decision,
                tick.target,
                fusion_confirmed=tick.camera_confirmed,
                fusion_reason=tick.camera_reason,
                timestamp_s=tick.timestamp_s,
                target_path_offset_m=tick.target_path_offset_m,
            )
            actual = policy.evaluate(tick)
            self.assertEqual(actual.decision, expected.decision)
            self.assertEqual(actual.action, expected.action)
            self.assertEqual(actual.reason, expected.reason)
            self.assertEqual(
                actual.radar_fallback_active,
                expected.radar_fallback_active,
            )
            self.assertEqual(
                actual.target_path_offset_m,
                expected.target_path_offset_m,
            )

    def test_reset_clears_temporal_hold(self):
        policy = HardCameraGatePolicy(
            FusionBrakeGateConfig(confirmation_hold_s=1.0)
        )
        policy.evaluate(context(camera_confirmed=True, timestamp_s=3.0))
        policy.reset()

        result = policy.evaluate(context(timestamp_s=3.1))

        self.assertEqual(result.decision.state, AEBState.RELEASE)


if __name__ == "__main__":
    unittest.main()
