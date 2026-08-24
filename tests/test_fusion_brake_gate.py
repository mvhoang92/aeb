"""Unit tests for the fail-safe camera/radar brake gate."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from control.brake import AEBDecision, AEBState
from core.fusion_brake_gate import FusionBrakeGate, FusionBrakeGateConfig


def brake_decision(ttc_s=1.0, margin_m=-3.0):
    return AEBDecision(
        state=AEBState.BRAKE,
        brake=1.0,
        throttle=0.0,
        ttc_s=ttc_s,
        target_distance_m=17.0,
        relative_velocity_mps=-16.0,
        should_override=True,
        reason="distance_and_ttc_brake",
        required_distance_m=20.0,
        distance_margin_m=margin_m,
    )


def warning_decision():
    return AEBDecision(
        state=AEBState.WARNING,
        brake=0.0,
        throttle=0.0,
        ttc_s=2.0,
        target_distance_m=30.0,
        relative_velocity_mps=-15.0,
        should_override=False,
        reason="ttc_warning",
        required_distance_m=25.0,
        distance_margin_m=5.0,
    )


def radar_target(**overrides):
    values = {
        "confirmed": True,
        "is_stale": False,
        "age_frames": 5,
        "hit_streak": 5,
        "point_count": 12,
        "confidence": 1.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FusionBrakeGateTests(unittest.TestCase):
    def fallback_gate(self, **fallback_overrides):
        fallback = {
            "enabled": True,
            "max_path_offset_m": 0.65,
            "min_track_age_frames": 3,
            "min_hit_streak": 3,
            "min_cluster_points": 6,
            "min_confidence": 0.70,
            "max_ttc_s": 1.10,
            "max_distance_margin_m": -2.0,
            "require_both_risk_conditions": True,
        }
        fallback.update(fallback_overrides)
        config = FusionBrakeGateConfig.from_mapping(
            {
                "confirmation_hold_s": 0.35,
                "radar_emergency_fallback": fallback,
            }
        )
        return FusionBrakeGate(config)

    def apply(self, gate, decision=None, target=None, **kwargs):
        return gate.apply(
            decision or brake_decision(),
            target or radar_target(),
            fusion_confirmed=kwargs.pop("fusion_confirmed", False),
            fusion_reason=kwargs.pop("fusion_reason", "no_yolo_detection"),
            timestamp_s=kwargs.pop("timestamp_s", 10.0),
            target_path_offset_m=kwargs.pop("target_path_offset_m", 0.05),
            **kwargs
        )

    def test_default_config_preserves_hard_camera_gate(self):
        result = self.apply(FusionBrakeGate())

        self.assertEqual(AEBState.RELEASE, result.decision.state)
        self.assertEqual("fusion_blocked_brake", result.action)
        self.assertIn("fallback_blocked:disabled", result.decision.reason)

    def test_camera_confirmation_allows_radar_brake(self):
        result = self.apply(
            FusionBrakeGate(),
            fusion_confirmed=True,
            fusion_reason="radar_target_inside_yolo_box",
        )

        self.assertEqual(AEBState.BRAKE, result.decision.state)
        self.assertEqual("camera_confirmed", result.action)
        self.assertFalse(result.radar_fallback_active)

    def test_confirmation_hold_uses_simulation_timestamp(self):
        gate = FusionBrakeGate(
            FusionBrakeGateConfig.from_mapping({"confirmation_hold_s": 0.35})
        )
        self.apply(gate, fusion_confirmed=True, timestamp_s=20.0)

        held = self.apply(gate, timestamp_s=20.30)
        expired = self.apply(gate, timestamp_s=20.40)

        self.assertEqual(AEBState.BRAKE, held.decision.state)
        self.assertEqual("confirmation_hold", held.action)
        self.assertEqual(AEBState.RELEASE, expired.decision.state)

    def test_reset_clears_confirmation_hold(self):
        gate = FusionBrakeGate(
            FusionBrakeGateConfig.from_mapping({"confirmation_hold_s": 1.0})
        )
        self.apply(gate, fusion_confirmed=True, timestamp_s=5.0)
        gate.reset()

        result = self.apply(gate, timestamp_s=5.1)

        self.assertEqual(AEBState.RELEASE, result.decision.state)
        self.assertEqual("fusion_blocked_brake", result.action)

    def test_non_brake_decision_passes_without_fallback(self):
        result = self.apply(self.fallback_gate(), decision=warning_decision())

        self.assertIs(AEBState.WARNING, result.decision.state)
        self.assertEqual("radar_no_brake", result.action)

    def test_strong_critical_central_track_uses_radar_fallback(self):
        result = self.apply(self.fallback_gate())

        self.assertEqual(AEBState.BRAKE, result.decision.state)
        self.assertTrue(result.radar_fallback_active)
        self.assertEqual("radar_emergency_fallback", result.action)
        self.assertIn("radar_emergency_fallback", result.decision.reason)

    def test_lane_edge_target_is_blocked(self):
        result = self.apply(
            self.fallback_gate(),
            target_path_offset_m=1.15,
        )

        self.assertEqual(AEBState.RELEASE, result.decision.state)
        self.assertEqual("outside_central_path", result.reason)

    def test_weak_synthetic_track_is_blocked(self):
        result = self.apply(
            self.fallback_gate(),
            target=radar_target(point_count=4),
        )

        self.assertEqual(AEBState.RELEASE, result.decision.state)
        self.assertEqual("insufficient_cluster_points", result.reason)

    def test_noncritical_ttc_is_blocked_when_both_conditions_required(self):
        result = self.apply(
            self.fallback_gate(),
            decision=brake_decision(ttc_s=1.3, margin_m=-3.0),
        )

        self.assertEqual(AEBState.RELEASE, result.decision.state)
        self.assertEqual("ttc_not_critical", result.reason)

    def test_noncritical_margin_is_blocked_when_both_conditions_required(self):
        result = self.apply(
            self.fallback_gate(),
            decision=brake_decision(ttc_s=1.0, margin_m=-1.0),
        )

        self.assertEqual(AEBState.RELEASE, result.decision.state)
        self.assertEqual("distance_margin_not_critical", result.reason)

    def test_one_risk_condition_can_be_configured_as_sufficient(self):
        result = self.apply(
            self.fallback_gate(require_both_risk_conditions=False),
            decision=brake_decision(ttc_s=1.3, margin_m=-3.0),
        )

        self.assertEqual(AEBState.BRAKE, result.decision.state)
        self.assertTrue(result.radar_fallback_active)


if __name__ == "__main__":
    unittest.main()
