"""Public BinaryAEB orchestration over risk, command and state modules."""

from __future__ import annotations

import math
import time
from typing import Optional

from control.risk_model import compute_ttc, required_stopping_distance
from control.staged_pid import BrakeCommandMixin
from control.state_machine import AEBStateMachineMixin
from control.types import AEBDecision, AEBState, BinaryBrakeConfig
from control.utils import first_existing_attr


class BinaryAEB(BrakeCommandMixin, AEBStateMachineMixin):
    """Frozen AEB decision/controller behavior with separated collaborators."""

    def __init__(self, config: Optional[BinaryBrakeConfig] = None) -> None:
        self.config = config or BinaryBrakeConfig()
        self.state = AEBState.NORMAL
        self._state_entered_at = time.monotonic()
        self._pid_integral = 0.0
        self._pid_previous_error = 0.0
        self._pid_last_timestamp = None
        self._last_brake = 0.0

    def reset(self) -> None:
        self.state = AEBState.NORMAL
        self._state_entered_at = time.monotonic()
        self._pid_integral = 0.0
        self._pid_previous_error = 0.0
        self._pid_last_timestamp = None
        self._last_brake = 0.0

    def decide_from_target(
        self,
        target: Optional[object],
        *,
        timestamp_s: Optional[float] = None,
        ego_speed_mps: Optional[float] = None,
    ) -> AEBDecision:
        if target is None:
            return self.decide(
                None,
                None,
                timestamp_s=timestamp_s,
                ego_speed_mps=ego_speed_mps,
            )
        distance_m = first_existing_attr(target, "x_forward_m", "distance_m", "depth_m")
        target_lateral_m = first_existing_attr(target, "y_right_m", "lateral_m")
        relative_velocity_mps = first_existing_attr(
            target,
            "relative_velocity_mps",
            "rel_velocity_mps",
        )
        return self.decide(
            distance_m,
            relative_velocity_mps,
            timestamp_s=timestamp_s,
            ego_speed_mps=ego_speed_mps,
            target_lateral_m=target_lateral_m,
        )

    def decide(
        self,
        distance_m: Optional[float],
        relative_velocity_mps: Optional[float],
        *,
        timestamp_s: Optional[float] = None,
        ego_speed_mps: Optional[float] = None,
        target_lateral_m: Optional[float] = None,
    ) -> AEBDecision:
        now = time.monotonic() if timestamp_s is None else float(timestamp_s)
        cfg = self.config

        if not self._valid_target(distance_m, relative_velocity_mps):
            if self._must_hold_until_stopped(ego_speed_mps):
                brake = self._hold_brake_command(now)
                return self._transition(
                    AEBState.BRAKE,
                    brake=brake,
                    ttc_s=math.inf,
                    target_distance_m=distance_m,
                    relative_velocity_mps=relative_velocity_mps,
                    should_override=True,
                    reason="brake_held_until_stopped",
                    required_distance_m=None,
                    distance_margin_m=None,
                    now=now,
                )
            return self._transition(
                AEBState.RELEASE if self.state != AEBState.NORMAL else AEBState.NORMAL,
                brake=0.0,
                ttc_s=math.inf,
                target_distance_m=distance_m,
                relative_velocity_mps=relative_velocity_mps,
                should_override=self.state == AEBState.BRAKE,
                reason="no_valid_closing_target",
                required_distance_m=None,
                distance_margin_m=None,
                now=now,
            )

        ttc_s = compute_ttc(distance_m, relative_velocity_mps)
        desired = self._desired_state(ttc_s)
        required_distance_m = self.required_stopping_distance(
            ego_speed_mps,
            relative_velocity_mps,
        )
        distance_margin_m = (
            None
            if required_distance_m is None or distance_m is None
            else distance_m - required_distance_m
        )
        distance_brake_threshold_m = self._distance_brake_threshold(
            target_lateral_m
        )
        distance_brake = (
            cfg.use_stopping_distance
            and distance_margin_m is not None
            and distance_margin_m <= distance_brake_threshold_m
        )
        if distance_brake:
            desired = AEBState.BRAKE
        if self._static_obstacle_brake(distance_m, relative_velocity_mps):
            desired = AEBState.BRAKE
            ttc_s = 0.0
        next_state = self._apply_hysteresis(
            desired,
            ttc_s,
            now,
            ego_speed_mps,
        )
        brake = self._brake_command(
            next_state,
            ttc_s,
            distance_m,
            distance_margin_m,
            target_lateral_m,
            now,
        )

        return self._transition(
            next_state,
            brake=brake,
            ttc_s=ttc_s,
            target_distance_m=distance_m,
            relative_velocity_mps=relative_velocity_mps,
            should_override=next_state == AEBState.BRAKE,
            reason=self._reason(next_state, ttc_s, distance_brake),
            required_distance_m=required_distance_m,
            distance_margin_m=distance_margin_m,
            now=now,
        )

    def required_stopping_distance(
        self,
        ego_speed_mps: Optional[float],
        relative_velocity_mps: Optional[float],
    ) -> Optional[float]:
        return required_stopping_distance(
            self.config,
            ego_speed_mps,
            relative_velocity_mps,
        )
