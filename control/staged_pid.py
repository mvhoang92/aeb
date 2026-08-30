"""Binary, staged and PID brake-command implementation mixin."""

from __future__ import annotations

import math
from typing import Optional

from control.types import AEBState
from control.utils import clamp


class BrakeCommandMixin(object):
    def _brake_command(
        self,
        state: AEBState,
        ttc_s: float,
        distance_m: Optional[float],
        distance_margin_m: Optional[float],
        target_lateral_m: Optional[float],
        now: float,
    ) -> float:
        cfg = self.config
        if state != AEBState.BRAKE:
            self._pid_integral = 0.0
            self._pid_previous_error = 0.0
            self._pid_last_timestamp = None
            self._last_brake = 0.0
            return 0.0
        if self._is_pid_mode():
            return self._pid_brake_command(
                ttc_s,
                distance_m,
                distance_margin_m,
                target_lateral_m,
                now,
            )
        if cfg.brake_mode != "staged":
            self._last_brake = cfg.full_brake
            return cfg.full_brake
        if not math.isfinite(ttc_s):
            self._last_brake = cfg.full_brake
            return cfg.full_brake
        if distance_m is not None and distance_m <= cfg.staged_emergency_distance_m:
            self._last_brake = cfg.staged_emergency_brake
            return cfg.staged_emergency_brake
        if (
            distance_margin_m is not None
            and distance_margin_m <= cfg.staged_emergency_margin_m
        ):
            self._last_brake = cfg.staged_emergency_brake
            return cfg.staged_emergency_brake
        if ttc_s <= cfg.staged_emergency_ttc_s:
            self._last_brake = cfg.staged_emergency_brake
            return cfg.staged_emergency_brake
        if (
            distance_margin_m is not None
            and distance_margin_m <= cfg.staged_hard_margin_m
        ):
            self._last_brake = cfg.staged_hard_brake
            return cfg.staged_hard_brake
        if ttc_s <= cfg.staged_hard_ttc_s:
            self._last_brake = cfg.staged_hard_brake
            return cfg.staged_hard_brake
        if distance_margin_m is not None and distance_margin_m <= 0.0:
            self._last_brake = cfg.staged_medium_brake
            return cfg.staged_medium_brake
        if ttc_s <= cfg.brake_ttc_s:
            self._last_brake = cfg.staged_medium_brake
            return cfg.staged_medium_brake
        self._last_brake = cfg.staged_soft_brake
        return cfg.staged_soft_brake

    def _pid_brake_command(
        self,
        ttc_s: float,
        distance_m: Optional[float],
        distance_margin_m: Optional[float],
        target_lateral_m: Optional[float],
        now: float,
    ) -> float:
        cfg = self.config
        dt = self._pid_dt(now)
        emergency = self._pid_emergency(
            ttc_s,
            distance_m,
            distance_margin_m,
        ) or self._staged_pid_emergency(ttc_s, distance_m, distance_margin_m)
        if emergency:
            target = (
                cfg.staged_emergency_brake
                if self._is_staged_pid_mode()
                else cfg.pid_max_brake
            )
            return self._rate_limited_brake(target, dt, emergency=True)

        margin_error = 0.0
        if distance_margin_m is not None:
            margin_error = max(
                0.0,
                self._distance_brake_threshold(target_lateral_m)
                - float(distance_margin_m)
                - cfg.pid_margin_deadband_m,
            )
        ttc_error = 0.0
        if math.isfinite(ttc_s):
            ttc_error = max(0.0, cfg.brake_ttc_s - float(ttc_s))
        error = margin_error + cfg.pid_ttc_kp * ttc_error
        self._pid_integral = clamp(
            self._pid_integral + error * dt,
            -cfg.pid_integral_limit,
            cfg.pid_integral_limit,
        )
        derivative = max(
            0.0,
            (error - self._pid_previous_error) / max(1e-3, dt),
        )
        self._pid_previous_error = error

        target = (
            cfg.pid_min_brake
            + cfg.pid_kp * error
            + cfg.pid_ki * self._pid_integral
            + cfg.pid_kd * derivative
        )
        target = clamp(target, cfg.pid_min_brake, cfg.pid_max_brake)
        target = self._staged_pid_target(
            target,
            ttc_s,
            distance_m,
            distance_margin_m,
        )
        return self._rate_limited_brake(target, dt, emergency=False)

    def _staged_pid_target(
        self,
        target: float,
        ttc_s: float,
        distance_m: Optional[float],
        distance_margin_m: Optional[float],
    ) -> float:
        if not self._is_staged_pid_mode():
            return target

        cfg = self.config
        if (
            distance_m is not None
            and distance_m <= cfg.staged_emergency_distance_m
        ):
            return cfg.staged_emergency_brake
        if (
            distance_margin_m is not None
            and distance_margin_m <= cfg.staged_emergency_margin_m
        ):
            return cfg.staged_emergency_brake
        if math.isfinite(ttc_s) and ttc_s <= cfg.staged_emergency_ttc_s:
            return cfg.staged_emergency_brake

        if (
            distance_margin_m is not None
            and distance_margin_m <= cfg.staged_hard_margin_m
        ):
            return clamp(target, cfg.staged_medium_brake, cfg.staged_hard_brake)
        if math.isfinite(ttc_s) and ttc_s <= cfg.staged_hard_ttc_s:
            return clamp(target, cfg.staged_medium_brake, cfg.staged_hard_brake)

        if distance_margin_m is not None and distance_margin_m <= 0.0:
            return clamp(target, cfg.staged_soft_brake, cfg.staged_medium_brake)
        if math.isfinite(ttc_s) and ttc_s <= cfg.brake_ttc_s:
            return clamp(target, cfg.staged_soft_brake, cfg.staged_medium_brake)

        return clamp(target, cfg.pid_min_brake, cfg.staged_soft_brake)

    def _pid_emergency(
        self,
        ttc_s: float,
        distance_m: Optional[float],
        distance_margin_m: Optional[float],
    ) -> bool:
        cfg = self.config
        if distance_m is not None and distance_m <= cfg.pid_emergency_distance_m:
            return True
        if (
            distance_margin_m is not None
            and distance_margin_m <= cfg.pid_emergency_margin_m
        ):
            return True
        return math.isfinite(ttc_s) and ttc_s <= cfg.pid_emergency_ttc_s

    def _staged_pid_emergency(
        self,
        ttc_s: float,
        distance_m: Optional[float],
        distance_margin_m: Optional[float],
    ) -> bool:
        if not self._is_staged_pid_mode():
            return False
        cfg = self.config
        if distance_m is not None and distance_m <= cfg.staged_emergency_distance_m:
            return True
        if (
            distance_margin_m is not None
            and distance_margin_m <= cfg.staged_emergency_margin_m
        ):
            return True
        return math.isfinite(ttc_s) and ttc_s <= cfg.staged_emergency_ttc_s

    def _pid_dt(self, now: float) -> float:
        cfg = self.config
        if self._pid_last_timestamp is None:
            self._pid_last_timestamp = now
            return cfg.pid_default_dt_s
        dt = max(1e-3, float(now) - float(self._pid_last_timestamp))
        self._pid_last_timestamp = now
        return dt

    def _distance_brake_threshold(
        self,
        target_lateral_m: Optional[float],
    ) -> float:
        cfg = self.config
        if not self._is_pid_mode():
            return 0.0
        if target_lateral_m is not None:
            if abs(float(target_lateral_m)) > cfg.pid_target_margin_max_lateral_m:
                return 0.0
        return cfg.pid_target_margin_m

    def _rate_limited_brake(self, target: float, dt: float, emergency: bool) -> float:
        cfg = self.config
        rise_rate = (
            cfg.pid_emergency_rise_rate_per_s
            if emergency
            else cfg.pid_brake_rise_rate_per_s
        )
        if target >= self._last_brake:
            limit = rise_rate * dt
            brake = min(target, self._last_brake + limit)
        else:
            limit = cfg.pid_brake_fall_rate_per_s * dt
            brake = max(target, self._last_brake - limit)
        self._last_brake = clamp(brake, 0.0, cfg.pid_max_brake)
        return self._last_brake

    def _hold_brake_command(self, now: float) -> float:
        cfg = self.config
        if self._is_pid_mode():
            dt = self._pid_dt(now)
            return self._rate_limited_brake(
                max(self._last_brake, cfg.pid_hold_brake),
                dt,
                emergency=False,
            )
        return cfg.full_brake

    def _is_pid_mode(self) -> bool:
        return self.config.brake_mode in (
            "pid",
            "pid_v1",
            "pid_v2",
            "pid_v2_comfort",
            "staged_pid",
        )

    def _is_staged_pid_mode(self) -> bool:
        return self.config.brake_mode == "staged_pid"
