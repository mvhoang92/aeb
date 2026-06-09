"""Radar object representation derived from CARLA radar clusters."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from control.brake import compute_ttc


@dataclass(frozen=True)
class RadarObject:
    """Object-level radar track used by AEB after clustering and tracking.

    CARLA gives the project radar detection points. The clustering layer groups
    those points into tracks; this object is the cleaner object-list view that a
    real automotive radar ECU would usually expose to downstream ADAS logic.
    """

    object_id: int
    longitudinal_m: float
    lateral_m: float
    height_m: float
    relative_velocity_mps: float
    point_count: int
    confidence: float
    confirmed: bool
    age_frames: int
    hit_streak: int
    missed_frames: int
    max_height_above_road_m: Optional[float]
    world_location: object
    source_cluster: object = None

    @property
    def track_id(self) -> int:
        return self.object_id

    @property
    def x_forward_m(self) -> float:
        return self.longitudinal_m

    @property
    def y_right_m(self) -> float:
        return self.lateral_m

    @property
    def z_up_m(self) -> float:
        return self.height_m

    @property
    def distance_m(self) -> float:
        return math.hypot(self.longitudinal_m, self.lateral_m)

    @property
    def depth_m(self) -> float:
        return self.distance_m

    @property
    def closing_speed_mps(self) -> float:
        return max(0.0, -float(self.relative_velocity_mps))

    @property
    def ttc_s(self) -> float:
        return compute_ttc(self.longitudinal_m, self.relative_velocity_mps)

    @property
    def is_stale(self) -> bool:
        return self.missed_frames > 0

    @property
    def points(self) -> Tuple[object, ...]:
        if self.source_cluster is None:
            return tuple()
        return tuple(getattr(self.source_cluster, "points", tuple()))


def radar_object_from_cluster(cluster: object) -> RadarObject:
    """Convert one confirmed/tracked radar cluster into an object-list entry."""

    return RadarObject(
        object_id=int(cluster.track_id),
        longitudinal_m=float(cluster.x_forward_m),
        lateral_m=float(cluster.y_right_m),
        height_m=float(cluster.z_up_m),
        relative_velocity_mps=float(cluster.relative_velocity_mps),
        point_count=int(cluster.point_count),
        confidence=cluster_confidence(cluster),
        confirmed=bool(cluster.confirmed),
        age_frames=int(cluster.age_frames),
        hit_streak=int(cluster.hit_streak),
        missed_frames=int(cluster.missed_frames),
        max_height_above_road_m=cluster.max_height_above_road_m,
        world_location=cluster.world_location,
        source_cluster=cluster,
    )


def radar_objects_from_clusters(clusters: Iterable[object]) -> List[RadarObject]:
    return [radar_object_from_cluster(cluster) for cluster in clusters]


def cluster_confidence(cluster: object) -> float:
    """Small deterministic confidence proxy for a CARLA radar object.

    CARLA radar points do not include radar existence probability, RCS or SNR.
    This score only expresses how stable and well-supported the project track is.
    It is not a production radar confidence value.
    """

    point_score = min(1.0, max(0.0, float(cluster.point_count) / 6.0))
    hit_score = min(1.0, max(0.0, float(cluster.hit_streak) / 3.0))
    stale_penalty = 0.0 if getattr(cluster, "is_stale", False) else 1.0
    confirmed_bonus = 1.0 if bool(cluster.confirmed) else 0.5
    score = 0.4 * point_score + 0.4 * hit_score + 0.2 * stale_penalty
    return round(score, 4) * confirmed_bonus
