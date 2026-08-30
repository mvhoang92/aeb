"""AEB state validation, hysteresis and transition implementation mixin."""

from __future__ import annotations

import math
from typing import Optional

from control.types import AEBDecision, AEBState
from control.utils import clamp


class AEBStateMachineMixin(object):
    def _valid_target(
        self,
        distance_m: Optional[float],
        relative_velocity_mps: Optional[float],
    ) -> bool:
        cfg = self.config
        if distance_m is None or relative_velocity_mps is None:
            return False
        if distance_m < cfg.min_valid_distance_m:
            return False
        if distance_m > cfg.max_valid_distance_m:
            return False
        return (
            relative_velocity_mps <= -cfg.min_closing_speed_mps
            or self._static_obstacle_brake(distance_m, relative_velocity_mps)
        )

    def _static_obstacle_brake(
        self,
        distance_m: Optional[float],
        relative_velocity_mps: Optional[float],
    ) -> bool:
        cfg = self.config
        if cfg.static_obstacle_brake_distance_m <= 0.0:
            return False
        if distance_m is None:
            return False
        if distance_m > cfg.static_obstacle_brake_distance_m:
            return False
        if relative_velocity_mps is None:
            return True
        return relative_velocity_mps <= cfg.min_closing_speed_mps

    def _desired_state(self, ttc_s: float) -> AEBState:
        cfg = self.config
        if ttc_s <= cfg.brake_ttc_s:
            return AEBState.BRAKE
        if ttc_s <= cfg.warning_ttc_s:
            return AEBState.WARNING
        return AEBState.NORMAL

    def _apply_hysteresis(
        self,
        desired: AEBState,
        ttc_s: float,
        now: float,
        ego_speed_mps: Optional[float],
    ) -> AEBState:
        cfg = self.config
        hold_active = now - self._state_entered_at < cfg.min_brake_hold_time_s

        if self.state == AEBState.BRAKE:
            if (
                hold_active
                or self._must_hold_until_stopped(ego_speed_mps)
                or ttc_s <= cfg.release_ttc_s
            ):
                return AEBState.BRAKE
            return AEBState.RELEASE

        if self.state == AEBState.WARNING:
            if desired == AEBState.NORMAL and ttc_s > cfg.release_ttc_s:
                return AEBState.RELEASE

        if self.state == AEBState.RELEASE and desired == AEBState.NORMAL:
            return AEBState.NORMAL

        return desired

    def _must_hold_until_stopped(
        self,
        ego_speed_mps: Optional[float],
    ) -> bool:
        cfg = self.config
        if self.state != AEBState.BRAKE:
            return False
        if not cfg.hold_brake_until_stopped:
            return False
        if ego_speed_mps is None:
            return False
        return ego_speed_mps > cfg.release_speed_mps

    def _transition(
        self,
        state: AEBState,
        *,
        brake: float,
        ttc_s: float,
        target_distance_m: Optional[float],
        relative_velocity_mps: Optional[float],
        should_override: bool,
        reason: str,
        required_distance_m: Optional[float],
        distance_margin_m: Optional[float],
        now: float,
    ) -> AEBDecision:
        if state != self.state:
            self.state = state
            self._state_entered_at = now

        return AEBDecision(
            state=state,
            brake=clamp(brake, 0.0, 1.0),
            throttle=0.0,
            ttc_s=ttc_s,
            target_distance_m=target_distance_m,
            relative_velocity_mps=relative_velocity_mps,
            should_override=should_override,
            reason=reason,
            required_distance_m=required_distance_m,
            distance_margin_m=distance_margin_m,
        )

    def _reason(
        self,
        state: AEBState,
        ttc_s: float,
        distance_brake: bool,
    ) -> str:
        if state == AEBState.BRAKE:
            if not math.isfinite(ttc_s):
                return "brake_held_until_stopped"
            if ttc_s <= 0.0:
                return "static_obstacle_distance_fallback"
            if ttc_s > self.config.brake_ttc_s:
                if distance_brake:
                    return "distance_below_stopping_threshold"
                return "brake_held_until_stopped"
            if distance_brake:
                return "distance_and_ttc_brake"
            return "ttc_below_brake_threshold"
        if state == AEBState.WARNING:
            return "ttc_below_warning_threshold"
        if state == AEBState.RELEASE:
            return "ttc_recovered"
        return "normal"
