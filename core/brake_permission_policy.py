"""Brake-permission policies shared by radar-only and fusion runtimes.

The radar AEB pipeline owns hazard estimation and produces a provisional
:class:`~control.brake.AEBDecision`.  A permission policy may pass that decision
through or replace a provisional BRAKE with RELEASE.  It must not recompute TTC,
stopping distance or brake magnitude.

This module adapts the frozen :mod:`core.fusion_brake_gate` mechanism rather
than reimplementing it.  The explicit boundary is intended for runner
composition and future research branches; it does not change the evaluated
hard-gate or emergency-fallback algorithms.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Optional

from control.brake import AEBDecision
from core.fusion_brake_gate import FusionBrakeGate, FusionBrakeGateConfig


@dataclass(frozen=True)
class BrakePermissionContext:
    """Inputs available to a brake-permission policy for one simulation tick."""

    radar_decision: AEBDecision
    target: Optional[object] = None
    camera_confirmed: bool = False
    camera_reason: str = "not_applicable"
    timestamp_s: Optional[float] = None
    target_path_offset_m: Optional[float] = None


@dataclass(frozen=True)
class BrakePermissionResult:
    """Final decision and stable diagnostics consumed by runner telemetry."""

    decision: AEBDecision
    action: str
    reason: str
    radar_fallback_active: bool = False
    target_path_offset_m: Optional[float] = None


class BrakePermissionPolicy(ABC):
    """Interface between provisional radar decisions and brake actuation."""

    name = "abstract"

    @abstractmethod
    def evaluate(self, context: BrakePermissionContext) -> BrakePermissionResult:
        """Return the final decision for one tick."""

    def reset(self) -> None:
        """Clear temporal policy state between scenarios."""


class RadarOnlyPolicy(BrakePermissionPolicy):
    """Pass every provisional radar decision through unchanged."""

    name = "radar_only"

    def evaluate(self, context: BrakePermissionContext) -> BrakePermissionResult:
        return BrakePermissionResult(
            decision=context.radar_decision,
            action="radar_only",
            reason="radar_decision_passthrough",
            target_path_offset_m=context.target_path_offset_m,
        )


class _FusionGatePolicy(BrakePermissionPolicy):
    """Common adapter that preserves ``FusionBrakeGate`` output exactly."""

    def __init__(self, config: FusionBrakeGateConfig):
        self.config = config
        self.gate = FusionBrakeGate(config)

    def evaluate(self, context: BrakePermissionContext) -> BrakePermissionResult:
        gate_result = self.gate.apply(
            context.radar_decision,
            context.target,
            fusion_confirmed=context.camera_confirmed,
            fusion_reason=context.camera_reason,
            timestamp_s=context.timestamp_s,
            target_path_offset_m=context.target_path_offset_m,
        )
        return BrakePermissionResult(
            decision=gate_result.decision,
            action=gate_result.action,
            reason=gate_result.reason,
            radar_fallback_active=gate_result.radar_fallback_active,
            target_path_offset_m=gate_result.target_path_offset_m,
        )

    def reset(self) -> None:
        self.gate.reset()


class HardCameraGatePolicy(_FusionGatePolicy):
    """Require current/recent camera confirmation for provisional BRAKE."""

    name = "hard_camera_gate"

    def __init__(self, config: Optional[FusionBrakeGateConfig] = None):
        source = config or FusionBrakeGateConfig()
        super(HardCameraGatePolicy, self).__init__(
            replace(source, radar_fallback_enabled=False)
        )


class EmergencyFallbackPolicy(_FusionGatePolicy):
    """Hard camera gate plus the frozen critical-radar emergency fallback."""

    name = "emergency_fallback"

    def __init__(self, config: Optional[FusionBrakeGateConfig] = None):
        source = config or FusionBrakeGateConfig()
        super(EmergencyFallbackPolicy, self).__init__(
            replace(source, radar_fallback_enabled=True)
        )


def fusion_policy_from_config(
    config: Optional[FusionBrakeGateConfig] = None,
) -> BrakePermissionPolicy:
    """Select the evaluated fusion policy without introducing a new config key."""

    resolved = config or FusionBrakeGateConfig()
    if resolved.radar_fallback_enabled:
        return EmergencyFallbackPolicy(resolved)
    return HardCameraGatePolicy(resolved)
