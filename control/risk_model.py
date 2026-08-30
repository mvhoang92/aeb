"""TTC and relative-motion stopping-distance risk model."""

from __future__ import annotations

import math
from typing import Optional

from control.types import BinaryBrakeConfig


def compute_ttc(distance_m: Optional[float], relative_velocity_mps: Optional[float]) -> float:
    """Compute TTC with project convention: negative relative velocity is closing."""

    if distance_m is None or relative_velocity_mps is None:
        return math.inf
    if distance_m <= 0.0:
        return 0.0
    if relative_velocity_mps >= 0.0:
        return math.inf
    return distance_m / (-relative_velocity_mps)


def required_stopping_distance(
    config: BinaryBrakeConfig,
    ego_speed_mps: Optional[float],
    relative_velocity_mps: Optional[float],
) -> Optional[float]:
    if ego_speed_mps is None or relative_velocity_mps is None:
        return None
    cfg = config
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
