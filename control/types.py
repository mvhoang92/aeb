"""Public AEB state, configuration, decision and control data types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional

from control.utils import as_bool, clamp


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
    brake_mode: str = "binary"
    full_brake: float = 1.0
    staged_soft_brake: float = 0.55
    staged_medium_brake: float = 0.75
    staged_hard_brake: float = 0.90
    staged_emergency_brake: float = 1.0
    staged_hard_ttc_s: float = 1.10
    staged_emergency_ttc_s: float = 0.80
    staged_hard_margin_m: float = -2.0
    staged_emergency_margin_m: float = -5.0
    staged_emergency_distance_m: float = 18.0
    pid_kp: float = 0.16
    pid_ki: float = 0.02
    pid_kd: float = 0.04
    pid_ttc_kp: float = 0.15
    pid_min_brake: float = 0.35
    pid_hold_brake: float = 0.75
    pid_max_brake: float = 1.0
    pid_integral_limit: float = 8.0
    pid_margin_deadband_m: float = 0.2
    pid_target_margin_m: float = 0.0
    pid_target_margin_max_lateral_m: float = 999.0
    pid_default_dt_s: float = 0.05
    pid_brake_rise_rate_per_s: float = 3.0
    pid_brake_fall_rate_per_s: float = 5.0
    pid_emergency_rise_rate_per_s: float = 20.0
    pid_emergency_distance_m: float = 18.0
    pid_emergency_margin_m: float = -5.0
    pid_emergency_ttc_s: float = 0.80
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
            brake_mode=str(data.get("brake_mode", cls.brake_mode)).lower(),
            full_brake=float(data.get("full_brake", cls.full_brake)),
            staged_soft_brake=clamp(
                float(data.get("staged_soft_brake", cls.staged_soft_brake)),
                0.0,
                1.0,
            ),
            staged_medium_brake=clamp(
                float(data.get("staged_medium_brake", cls.staged_medium_brake)),
                0.0,
                1.0,
            ),
            staged_hard_brake=clamp(
                float(data.get("staged_hard_brake", cls.staged_hard_brake)),
                0.0,
                1.0,
            ),
            staged_emergency_brake=clamp(
                float(
                    data.get(
                        "staged_emergency_brake",
                        cls.staged_emergency_brake,
                    )
                ),
                0.0,
                1.0,
            ),
            staged_hard_ttc_s=max(
                0.0,
                float(data.get("staged_hard_ttc_s", cls.staged_hard_ttc_s)),
            ),
            staged_emergency_ttc_s=max(
                0.0,
                float(
                    data.get(
                        "staged_emergency_ttc_s",
                        cls.staged_emergency_ttc_s,
                    )
                ),
            ),
            staged_hard_margin_m=float(
                data.get("staged_hard_margin_m", cls.staged_hard_margin_m)
            ),
            staged_emergency_margin_m=float(
                data.get(
                    "staged_emergency_margin_m",
                    cls.staged_emergency_margin_m,
                )
            ),
            staged_emergency_distance_m=max(
                0.0,
                float(
                    data.get(
                        "staged_emergency_distance_m",
                        cls.staged_emergency_distance_m,
                    )
                ),
            ),
            pid_kp=float(data.get("pid_kp", cls.pid_kp)),
            pid_ki=float(data.get("pid_ki", cls.pid_ki)),
            pid_kd=float(data.get("pid_kd", cls.pid_kd)),
            pid_ttc_kp=float(data.get("pid_ttc_kp", cls.pid_ttc_kp)),
            pid_min_brake=clamp(
                float(data.get("pid_min_brake", cls.pid_min_brake)),
                0.0,
                1.0,
            ),
            pid_hold_brake=clamp(
                float(data.get("pid_hold_brake", cls.pid_hold_brake)),
                0.0,
                1.0,
            ),
            pid_max_brake=clamp(
                float(data.get("pid_max_brake", cls.pid_max_brake)),
                0.0,
                1.0,
            ),
            pid_integral_limit=max(
                0.0,
                float(data.get("pid_integral_limit", cls.pid_integral_limit)),
            ),
            pid_margin_deadband_m=max(
                0.0,
                float(
                    data.get(
                        "pid_margin_deadband_m",
                        cls.pid_margin_deadband_m,
                    )
                ),
            ),
            pid_target_margin_m=max(
                0.0,
                float(data.get("pid_target_margin_m", cls.pid_target_margin_m)),
            ),
            pid_target_margin_max_lateral_m=max(
                0.0,
                float(
                    data.get(
                        "pid_target_margin_max_lateral_m",
                        cls.pid_target_margin_max_lateral_m,
                    )
                ),
            ),
            pid_default_dt_s=max(
                1e-3,
                float(data.get("pid_default_dt_s", cls.pid_default_dt_s)),
            ),
            pid_brake_rise_rate_per_s=max(
                0.0,
                float(
                    data.get(
                        "pid_brake_rise_rate_per_s",
                        cls.pid_brake_rise_rate_per_s,
                    )
                ),
            ),
            pid_brake_fall_rate_per_s=max(
                0.0,
                float(
                    data.get(
                        "pid_brake_fall_rate_per_s",
                        cls.pid_brake_fall_rate_per_s,
                    )
                ),
            ),
            pid_emergency_rise_rate_per_s=max(
                0.0,
                float(
                    data.get(
                        "pid_emergency_rise_rate_per_s",
                        cls.pid_emergency_rise_rate_per_s,
                    )
                ),
            ),
            pid_emergency_distance_m=max(
                0.0,
                float(
                    data.get(
                        "pid_emergency_distance_m",
                        cls.pid_emergency_distance_m,
                    )
                ),
            ),
            pid_emergency_margin_m=float(
                data.get("pid_emergency_margin_m", cls.pid_emergency_margin_m)
            ),
            pid_emergency_ttc_s=max(
                0.0,
                float(data.get("pid_emergency_ttc_s", cls.pid_emergency_ttc_s)),
            ),
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
