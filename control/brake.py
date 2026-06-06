"""Binary AEB brake logic and CARLA brake override helpers."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional


class AEBState(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    BRAKE = "BRAKE"
    RELEASE = "RELEASE"


@dataclass(frozen=True)
class BinaryBrakeConfig:
    warning_ttc_s: float = 3.0
    brake_ttc_s: float = 1.8
    release_ttc_s: float = 3.5
    min_brake_hold_time_s: float = 0.3
    full_brake: float = 1.0
    min_valid_distance_m: float = 0.5
    max_valid_distance_m: float = 120.0
    min_closing_speed_mps: float = 0.2
    static_obstacle_brake_distance_m: float = 0.0
    hold_brake_until_stopped: bool = True
    release_speed_mps: float = 0.3
    use_stopping_distance: bool = True
    response_time_s: float = 0.35
    ego_emergency_decel_mps2: float = 7.0
    target_emergency_decel_mps2: float = 6.0
    stopping_distance_offset_m: float = 2.0

    @classmethod
    def from_mapping(cls, data: Optional[Mapping[str, float]]) -> "BinaryBrakeConfig":
        data = data or {}
        return cls(
            warning_ttc_s=float(
                data.get("warning_ttc_s", data.get("warning_ttc", cls.warning_ttc_s))
            ),
            brake_ttc_s=float(
                data.get("brake_ttc_s", data.get("brake_ttc", cls.brake_ttc_s))
            ),
            release_ttc_s=float(
                data.get("release_ttc_s", data.get("release_ttc", cls.release_ttc_s))
            ),
            min_brake_hold_time_s=float(
                data.get(
                    "min_brake_hold_time_s",
                    data.get("min_brake_hold_time", cls.min_brake_hold_time_s),
                )
            ),
            full_brake=float(data.get("full_brake", cls.full_brake)),
            min_valid_distance_m=float(
                data.get("min_valid_distance_m", cls.min_valid_distance_m)
            ),
            max_valid_distance_m=float(
                data.get("max_valid_distance_m", cls.max_valid_distance_m)
            ),
            min_closing_speed_mps=float(
                data.get("min_closing_speed_mps", cls.min_closing_speed_mps)
            ),
            static_obstacle_brake_distance_m=float(
                data.get(
                    "static_obstacle_brake_distance_m",
                    cls.static_obstacle_brake_distance_m,
                )
            ),
            hold_brake_until_stopped=as_bool(
                data.get(
                    "hold_brake_until_stopped",
                    cls.hold_brake_until_stopped,
                )
            ),
            release_speed_mps=float(
                data.get("release_speed_mps", cls.release_speed_mps)
            ),
            use_stopping_distance=as_bool(
                data.get("use_stopping_distance", cls.use_stopping_distance)
            ),
            response_time_s=max(
                0.0,
                float(data.get("response_time_s", cls.response_time_s)),
            ),
            ego_emergency_decel_mps2=max(
                0.1,
                float(
                    data.get(
                        "ego_emergency_decel_mps2",
                        cls.ego_emergency_decel_mps2,
                    )
                ),
            ),
            target_emergency_decel_mps2=max(
                0.1,
                float(
                    data.get(
                        "target_emergency_decel_mps2",
                        cls.target_emergency_decel_mps2,
                    )
                ),
            ),
            stopping_distance_offset_m=max(
                0.0,
                float(
                    data.get(
                        "stopping_distance_offset_m",
                        cls.stopping_distance_offset_m,
                    )
                ),
            ),
        )


@dataclass(frozen=True)
class AEBDecision:
    state: AEBState
    brake: float
    throttle: float
    ttc_s: float
    target_distance_m: Optional[float]
    relative_velocity_mps: Optional[float]
    should_override: bool
    reason: str
    required_distance_m: Optional[float] = None
    distance_margin_m: Optional[float] = None


@dataclass
class SimpleVehicleControl:
    throttle: float = 0.0
    steer: float = 0.0
    brake: float = 0.0
    hand_brake: bool = False
    reverse: bool = False
    manual_gear_shift: bool = False
    gear: int = 0


def compute_ttc(distance_m: Optional[float], relative_velocity_mps: Optional[float]) -> float:
    """Compute TTC with project convention: negative relative velocity is closing."""

    if distance_m is None or relative_velocity_mps is None:
        return math.inf
    if distance_m <= 0.0:
        return 0.0
    if relative_velocity_mps >= 0.0:
        return math.inf
    return distance_m / (-relative_velocity_mps)


class BinaryAEB:
    """Small state machine for the first AEB brake tests.

    This class intentionally starts simple: it outputs either no brake or full
    brake. PID modulation can later replace the brake command while keeping the
    same decision data structure.
    """

    def __init__(self, config: Optional[BinaryBrakeConfig] = None) -> None:
        self.config = config or BinaryBrakeConfig()
        self.state = AEBState.NORMAL
        self._state_entered_at = time.monotonic()

    def reset(self) -> None:
        self.state = AEBState.NORMAL
        self._state_entered_at = time.monotonic()

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
        )

    def decide(
        self,
        distance_m: Optional[float],
        relative_velocity_mps: Optional[float],
        *,
        timestamp_s: Optional[float] = None,
        ego_speed_mps: Optional[float] = None,
    ) -> AEBDecision:
        now = time.monotonic() if timestamp_s is None else float(timestamp_s)
        cfg = self.config

        if not self._valid_target(distance_m, relative_velocity_mps):
            if self._must_hold_until_stopped(ego_speed_mps):
                return self._transition(
                    AEBState.BRAKE,
                    brake=cfg.full_brake,
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
        distance_brake = (
            cfg.use_stopping_distance
            and distance_margin_m is not None
            and distance_margin_m <= 0.0
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
        brake = cfg.full_brake if next_state == AEBState.BRAKE else 0.0

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
        if ego_speed_mps is None or relative_velocity_mps is None:
            return None
        cfg = self.config
        ego_speed = max(0.0, float(ego_speed_mps))
        target_speed = max(0.0, ego_speed + float(relative_velocity_mps))
        ego_distance = (
            ego_speed * cfg.response_time_s
            + ego_speed * ego_speed / (2.0 * cfg.ego_emergency_decel_mps2)
        )
        target_distance = (
            target_speed
            * target_speed
            / (2.0 * cfg.target_emergency_decel_mps2)
        )
        return max(
            cfg.stopping_distance_offset_m,
            ego_distance - target_distance + cfg.stopping_distance_offset_m,
        )

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


def make_brake_control(
    decision: AEBDecision,
    base_control: Optional[object] = None,
) -> object:
    control = clone_vehicle_control(base_control)
    if decision.state == AEBState.BRAKE:
        set_if_present(control, "throttle", 0.0)
        set_if_present(control, "brake", clamp(decision.brake, 0.0, 1.0))
        set_if_present(control, "hand_brake", False)
    elif decision.state == AEBState.RELEASE:
        set_if_present(control, "brake", 0.0)
    return control


def apply_brake_override(
    vehicle: object,
    decision: AEBDecision,
    base_control: Optional[object] = None,
) -> object:
    if base_control is None and hasattr(vehicle, "get_control"):
        base_control = vehicle.get_control()
    control = make_brake_control(decision, base_control)
    vehicle.apply_control(control)
    return control


def clone_vehicle_control(base_control: Optional[object]) -> object:
    if base_control is None:
        return SimpleVehicleControl()

    try:
        control = base_control.__class__()
    except Exception:  # pylint: disable=broad-except
        control = SimpleVehicleControl()

    for name in (
        "throttle",
        "steer",
        "brake",
        "hand_brake",
        "reverse",
        "manual_gear_shift",
        "gear",
    ):
        if hasattr(base_control, name) and hasattr(control, name):
            setattr(control, name, getattr(base_control, name))
    return control


def first_existing_attr(obj: object, *names: str) -> Optional[float]:
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return float(value)
    return None


def set_if_present(obj: object, name: str, value: object) -> None:
    if hasattr(obj, name):
        setattr(obj, name, value)


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def as_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)
