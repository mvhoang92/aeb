"""Target selection for object-level radar AEB."""

from __future__ import annotations

import math
from typing import Iterable, Optional

from control.brake import compute_ttc
from core.radar_object import RadarObject


def select_aeb_target(objects: Iterable[RadarObject]) -> Optional[RadarObject]:
    """Select the radar object that should drive the AEB decision.

    This intentionally preserves the previous radar-only behavior: use only
    confirmed, non-stale tracks, prefer the lowest finite TTC, then the nearest
    longitudinal distance.
    """

    candidates = [
        obj for obj in objects if bool(obj.confirmed) and not bool(obj.is_stale)
    ]
    if not candidates:
        return None

    def sort_key(obj):
        ttc = compute_ttc(obj.x_forward_m, obj.relative_velocity_mps)
        has_ttc = 0 if math.isfinite(ttc) else 1
        return has_ttc, ttc, obj.x_forward_m

    return min(candidates, key=sort_key)
