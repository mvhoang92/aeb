"""Safety policy for camera-gated radar AEB brake decisions.

The camera detector is positive evidence that a radar target is a vehicle, but
an absent camera detection must not always be treated as proof that the path is
clear.  This module keeps the original hard-gate behavior as the default and
adds an optional, explicitly conservative radar emergency fallback for stable,
well-supported targets in the central predicted path.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, replace
from typing import Mapping, Optional

from control.brake import AEBDecision, AEBState, as_bool


@dataclass(frozen=True)
class FusionBrakeGateConfig:
    """Configuration for the final camera/radar brake gate."""

    confirmation_hold_s: float = 0.35
    radar_fallback_enabled: bool = False
    radar_fallback_max_path_offset_m: float = 0.65
    radar_fallback_min_track_age_frames: int = 3
    radar_fallback_min_hit_streak: int = 3
    radar_fallback_min_cluster_points: int = 6
    radar_fallback_min_confidence: float = 0.70
    radar_fallback_max_ttc_s: float = 1.10
    radar_fallback_max_distance_margin_m: float = -2.0
    radar_fallback_require_both_risk_conditions: bool = True

    @classmethod
    def from_mapping(cls, data: Optional[Mapping[str, object]]):
        data = data or {}
        fallback = data.get("radar_emergency_fallback", {}) or {}
        return cls(
            confirmation_hold_s=max(
                0.0,
                float(data.get("confirmation_hold_s", cls.confirmation_hold_s)),
            ),
            radar_fallback_enabled=as_bool(
                fallback.get("enabled", cls.radar_fallback_enabled)
            ),
            radar_fallback_max_path_offset_m=max(
                0.0,
                float(
                    fallback.get(
                        "max_path_offset_m",
                        cls.radar_fallback_max_path_offset_m,
                    )
                ),
            ),
            radar_fallback_min_track_age_frames=max(
                1,
                int(
                    fallback.get(
                        "min_track_age_frames",
                        cls.radar_fallback_min_track_age_frames,
                    )
                ),
            ),
            radar_fallback_min_hit_streak=max(
                1,
                int(
                    fallback.get(
                        "min_hit_streak",
                        cls.radar_fallback_min_hit_streak,
                    )
                ),
            ),
            radar_fallback_min_cluster_points=max(
                1,
                int(
                    fallback.get(
                        "min_cluster_points",
                        cls.radar_fallback_min_cluster_points,
                    )
                ),
            ),
            radar_fallback_min_confidence=max(
                0.0,
                min(
                    1.0,
                    float(
                        fallback.get(
                            "min_confidence",
                            cls.radar_fallback_min_confidence,
                        )
                    ),
                ),
            ),
            radar_fallback_max_ttc_s=max(
                0.0,
                float(
                    fallback.get(
                        "max_ttc_s",
                        cls.radar_fallback_max_ttc_s,
                    )
                ),
            ),
            radar_fallback_max_distance_margin_m=float(
                fallback.get(
                    "max_distance_margin_m",
                    cls.radar_fallback_max_distance_margin_m,
                )
            ),
            radar_fallback_require_both_risk_conditions=as_bool(
                fallback.get(
                    "require_both_risk_conditions",
                    cls.radar_fallback_require_both_risk_conditions,
                )
            ),
        )


@dataclass(frozen=True)
class FusionBrakeGateResult:
    """One gate decision plus diagnostics for tick-level evidence."""

    decision: AEBDecision
    action: str
    reason: str
    radar_fallback_active: bool = False
    target_path_offset_m: Optional[float] = None


class FusionBrakeGate(object):
    """Apply camera confirmation, confirmation hold and radar fallback."""

    def __init__(self, config: Optional[FusionBrakeGateConfig] = None):
        self.config = config or FusionBrakeGateConfig()
        self._last_confirmed_timestamp_s = None

    def reset(self):
        self._last_confirmed_timestamp_s = None

    def apply(
        self,
        radar_decision,
        target,
        *,
        fusion_confirmed,
        fusion_reason,
        timestamp_s=None,
        target_path_offset_m=None,
    ):
        now = time.monotonic() if timestamp_s is None else float(timestamp_s)
        if fusion_confirmed:
            self._last_confirmed_timestamp_s = now

        if radar_decision.state != AEBState.BRAKE:
            return FusionBrakeGateResult(
                decision=radar_decision,
                action="radar_no_brake",
                reason="radar_decision_not_brake",
                target_path_offset_m=target_path_offset_m,
            )

        if fusion_confirmed:
            return FusionBrakeGateResult(
                decision=radar_decision,
                action="camera_confirmed",
                reason=str(fusion_reason),
                target_path_offset_m=target_path_offset_m,
            )

        if self._recently_confirmed(now):
            return FusionBrakeGateResult(
                decision=radar_decision,
                action="confirmation_hold",
                reason="recent_camera_confirmation",
                target_path_offset_m=target_path_offset_m,
            )

        fallback_rejection = self._fallback_rejection_reason(
            radar_decision,
            target,
            target_path_offset_m,
        )
        if fallback_rejection is None:
            fallback_decision = replace(
                radar_decision,
                reason="radar_emergency_fallback:{}|radar={}".format(
                    fusion_reason,
                    radar_decision.reason,
                ),
            )
            return FusionBrakeGateResult(
                decision=fallback_decision,
                action="radar_emergency_fallback",
                reason="critical_central_radar_track",
                radar_fallback_active=True,
                target_path_offset_m=target_path_offset_m,
            )

        blocked_reason = "fusion_blocked_brake:{}|fallback_blocked:{}".format(
            fusion_reason,
            fallback_rejection,
        )
        return FusionBrakeGateResult(
            decision=AEBDecision(
                state=AEBState.RELEASE,
                brake=0.0,
                throttle=0.0,
                ttc_s=radar_decision.ttc_s,
                target_distance_m=radar_decision.target_distance_m,
                relative_velocity_mps=radar_decision.relative_velocity_mps,
                should_override=False,
                reason=blocked_reason,
                required_distance_m=radar_decision.required_distance_m,
                distance_margin_m=radar_decision.distance_margin_m,
            ),
            action="fusion_blocked_brake",
            reason=fallback_rejection,
            target_path_offset_m=target_path_offset_m,
        )

    def _recently_confirmed(self, now):
        if self._last_confirmed_timestamp_s is None:
            return False
        elapsed = now - self._last_confirmed_timestamp_s
        return 0.0 <= elapsed <= self.config.confirmation_hold_s

    def _fallback_rejection_reason(
        self,
        radar_decision,
        target,
        target_path_offset_m,
    ):
        cfg = self.config
        if not cfg.radar_fallback_enabled:
            return "disabled"
        if target is None:
            return "no_radar_target"
        if not bool(getattr(target, "confirmed", False)):
            return "unconfirmed_track"
        if bool(getattr(target, "is_stale", False)):
            return "stale_track"
        if int(getattr(target, "age_frames", 0)) < cfg.radar_fallback_min_track_age_frames:
            return "track_too_young"
        if int(getattr(target, "hit_streak", 0)) < cfg.radar_fallback_min_hit_streak:
            return "insufficient_hit_streak"
        if int(getattr(target, "point_count", 0)) < cfg.radar_fallback_min_cluster_points:
            return "insufficient_cluster_points"
        if float(getattr(target, "confidence", 0.0)) < cfg.radar_fallback_min_confidence:
            return "low_track_confidence"
        if target_path_offset_m is None:
            return "unknown_path_offset"
        if abs(float(target_path_offset_m)) > cfg.radar_fallback_max_path_offset_m:
            return "outside_central_path"

        ttc_s = radar_decision.ttc_s
        ttc_critical = math.isfinite(ttc_s) and ttc_s <= cfg.radar_fallback_max_ttc_s
        margin = radar_decision.distance_margin_m
        margin_critical = (
            margin is not None
            and float(margin) <= cfg.radar_fallback_max_distance_margin_m
        )
        if cfg.radar_fallback_require_both_risk_conditions:
            if not ttc_critical:
                return "ttc_not_critical"
            if not margin_critical:
                return "distance_margin_not_critical"
        elif not (ttc_critical or margin_critical):
            return "risk_not_critical"
        return None
