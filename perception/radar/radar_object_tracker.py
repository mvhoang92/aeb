"""Radar point clustering and short-term tracking for radar-only AEB."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class RadarClusterConfig:
    tolerance_m: float = 1.0
    velocity_tolerance_mps: float = 2.0
    vertical_tolerance_m: float = 1.5
    min_points: int = 2
    confirm_frames: int = 3
    release_frames: int = 4
    match_distance_m: float = 2.5
    match_velocity_mps: float = 3.0
    distance_percentile: float = 0.20
    min_max_height_above_road_m: float = 0.25
    prediction_enabled: bool = True
    max_prediction_time_s: float = 0.30

    @classmethod
    def from_mapping(
        cls,
        data: Optional[Mapping[str, object]],
    ) -> "RadarClusterConfig":
        data = data or {}
        return cls(
            tolerance_m=max(0.05, float(data.get("tolerance_m", cls.tolerance_m))),
            velocity_tolerance_mps=max(
                0.0,
                float(
                    data.get(
                        "velocity_tolerance_mps",
                        cls.velocity_tolerance_mps,
                    )
                ),
            ),
            vertical_tolerance_m=max(
                0.0,
                float(data.get("vertical_tolerance_m", cls.vertical_tolerance_m)),
            ),
            min_points=max(1, int(data.get("min_points", cls.min_points))),
            confirm_frames=max(
                1,
                int(data.get("confirm_frames", cls.confirm_frames)),
            ),
            release_frames=max(
                1,
                int(data.get("release_frames", cls.release_frames)),
            ),
            match_distance_m=max(
                0.05,
                float(data.get("match_distance_m", cls.match_distance_m)),
            ),
            match_velocity_mps=max(
                0.05,
                float(data.get("match_velocity_mps", cls.match_velocity_mps)),
            ),
            distance_percentile=min(
                1.0,
                max(
                    0.0,
                    float(
                        data.get(
                            "distance_percentile",
                            cls.distance_percentile,
                        )
                    ),
                ),
            ),
            min_max_height_above_road_m=float(
                data.get(
                    "min_max_height_above_road_m",
                    cls.min_max_height_above_road_m,
                )
            ),
            prediction_enabled=as_bool(
                data.get("prediction_enabled", cls.prediction_enabled)
            ),
            max_prediction_time_s=max(
                0.0,
                float(
                    data.get(
                        "max_prediction_time_s",
                        cls.max_prediction_time_s,
                    )
                ),
            ),
        )


@dataclass
class RadarCluster:
    track_id: int
    points: Tuple[object, ...]
    x_forward_m: float
    y_right_m: float
    z_up_m: float
    relative_velocity_mps: float
    point_count: int
    max_height_above_road_m: Optional[float]
    world_location: object
    confirmed: bool = False
    hit_streak: int = 1
    age_frames: int = 1
    missed_frames: int = 0
    last_timestamp_s: Optional[float] = None

    @property
    def depth_m(self) -> float:
        return math.hypot(self.x_forward_m, self.y_right_m)

    @property
    def is_stale(self) -> bool:
        return self.missed_frames > 0


@dataclass
class _ClusterMeasurement:
    points: Tuple[object, ...]
    x_forward_m: float
    y_right_m: float
    z_up_m: float
    relative_velocity_mps: float
    max_height_above_road_m: Optional[float]
    world_location: object


class RadarClusterTracker:
    """Cluster sparse radar returns and confirm objects across sensor frames."""

    def __init__(self, config: Optional[RadarClusterConfig] = None) -> None:
        self.config = config or RadarClusterConfig()
        self._tracks: Dict[int, RadarCluster] = {}
        self._next_track_id = 1

    def reset(self) -> None:
        self._tracks = {}
        self._next_track_id = 1

    def update(
        self,
        points: Iterable[object],
        height_getter: Optional[Callable[[object], Optional[float]]] = None,
        timestamp_s: Optional[float] = None,
    ) -> List[RadarCluster]:
        measurements = cluster_radar_points(
            list(points),
            self.config,
            height_getter=height_getter,
        )
        matches = self._associate(measurements, timestamp_s)
        matched_tracks = set()
        matched_measurements = set()

        for track_id, measurement_index in matches:
            track = self._tracks[track_id]
            measurement = measurements[measurement_index]
            self._update_track(track, measurement, timestamp_s)
            matched_tracks.add(track_id)
            matched_measurements.add(measurement_index)

        for track_id, track in list(self._tracks.items()):
            if track_id in matched_tracks:
                continue
            track.age_frames += 1
            track.missed_frames += 1
            track.hit_streak = 0
            track.confirmed = False
            if track.missed_frames >= self.config.release_frames:
                del self._tracks[track_id]

        for index, measurement in enumerate(measurements):
            if index in matched_measurements:
                continue
            self._create_track(measurement, timestamp_s)

        return sorted(
            self._tracks.values(),
            key=lambda track: (track.x_forward_m, abs(track.y_right_m)),
        )

    def _associate(
        self,
        measurements: Sequence[_ClusterMeasurement],
        timestamp_s: Optional[float],
    ) -> List[Tuple[int, int]]:
        candidates = []
        for track_id, track in self._tracks.items():
            predicted_x, predicted_y = self._predicted_position(
                track,
                timestamp_s,
            )
            for index, measurement in enumerate(measurements):
                distance = math.hypot(
                    predicted_x - measurement.x_forward_m,
                    predicted_y - measurement.y_right_m,
                )
                velocity_delta = abs(
                    track.relative_velocity_mps
                    - measurement.relative_velocity_mps
                )
                if distance > self.config.match_distance_m:
                    continue
                if velocity_delta > self.config.match_velocity_mps:
                    continue
                score = (
                    distance / self.config.match_distance_m
                    + velocity_delta / self.config.match_velocity_mps
                )
                candidates.append((score, track_id, index))

        candidates.sort()
        used_tracks = set()
        used_measurements = set()
        matches = []
        for _, track_id, index in candidates:
            if track_id in used_tracks or index in used_measurements:
                continue
            used_tracks.add(track_id)
            used_measurements.add(index)
            matches.append((track_id, index))
        return matches

    def _predicted_position(
        self,
        track: RadarCluster,
        timestamp_s: Optional[float],
    ) -> Tuple[float, float]:
        if (
            not self.config.prediction_enabled
            or timestamp_s is None
            or track.last_timestamp_s is None
        ):
            return track.x_forward_m, track.y_right_m
        dt = max(
            0.0,
            min(
                self.config.max_prediction_time_s,
                float(timestamp_s) - track.last_timestamp_s,
            ),
        )
        return (
            track.x_forward_m + track.relative_velocity_mps * dt,
            track.y_right_m,
        )

    def _update_track(
        self,
        track: RadarCluster,
        measurement: _ClusterMeasurement,
        timestamp_s: Optional[float],
    ) -> None:
        track.points = measurement.points
        track.x_forward_m = measurement.x_forward_m
        track.y_right_m = measurement.y_right_m
        track.z_up_m = measurement.z_up_m
        track.relative_velocity_mps = measurement.relative_velocity_mps
        track.point_count = len(measurement.points)
        track.max_height_above_road_m = measurement.max_height_above_road_m
        track.world_location = measurement.world_location
        track.age_frames += 1
        track.hit_streak += 1
        track.missed_frames = 0
        track.last_timestamp_s = timestamp_s
        track.confirmed = track.hit_streak >= self.config.confirm_frames

    def _create_track(
        self,
        measurement: _ClusterMeasurement,
        timestamp_s: Optional[float],
    ) -> None:
        track_id = self._next_track_id
        self._next_track_id += 1
        self._tracks[track_id] = RadarCluster(
            track_id=track_id,
            points=measurement.points,
            x_forward_m=measurement.x_forward_m,
            y_right_m=measurement.y_right_m,
            z_up_m=measurement.z_up_m,
            relative_velocity_mps=measurement.relative_velocity_mps,
            point_count=len(measurement.points),
            max_height_above_road_m=measurement.max_height_above_road_m,
            world_location=measurement.world_location,
            confirmed=self.config.confirm_frames <= 1,
            last_timestamp_s=timestamp_s,
        )


def cluster_radar_points(
    points: Sequence[object],
    config: RadarClusterConfig,
    height_getter: Optional[Callable[[object], Optional[float]]] = None,
) -> List[_ClusterMeasurement]:
    """Build connected radar clusters using position and radial velocity."""

    visited = set()
    measurements = []
    for start_index in range(len(points)):
        if start_index in visited:
            continue
        component = []
        queue = [start_index]
        visited.add(start_index)
        while queue:
            index = queue.pop()
            component.append(points[index])
            for neighbor_index in range(len(points)):
                if neighbor_index in visited:
                    continue
                if _points_are_neighbors(
                    points[index],
                    points[neighbor_index],
                    config,
                ):
                    visited.add(neighbor_index)
                    queue.append(neighbor_index)

        if len(component) < config.min_points:
            continue
        measurement = _make_measurement(component, config, height_getter)
        if measurement is not None:
            measurements.append(measurement)
    return measurements


def _points_are_neighbors(
    first: object,
    second: object,
    config: RadarClusterConfig,
) -> bool:
    planar_distance = math.hypot(
        float(first.x_forward_m) - float(second.x_forward_m),
        float(first.y_right_m) - float(second.y_right_m),
    )
    if planar_distance > config.tolerance_m:
        return False
    if (
        abs(float(first.z_up_m) - float(second.z_up_m))
        > config.vertical_tolerance_m
    ):
        return False
    return (
        abs(
            float(first.relative_velocity_mps)
            - float(second.relative_velocity_mps)
        )
        <= config.velocity_tolerance_mps
    )


def _make_measurement(
    points: Sequence[object],
    config: RadarClusterConfig,
    height_getter: Optional[Callable[[object], Optional[float]]],
) -> Optional[_ClusterMeasurement]:
    heights = []
    if height_getter is not None:
        heights = [
            height
            for height in (height_getter(point) for point in points)
            if height is not None
        ]
    max_height = max(heights) if heights else None
    if (
        max_height is not None
        and max_height < config.min_max_height_above_road_m
    ):
        return None

    x_forward = _percentile(
        [float(point.x_forward_m) for point in points],
        config.distance_percentile,
    )
    y_right = _median([float(point.y_right_m) for point in points])
    z_up = _median([float(point.z_up_m) for point in points])
    relative_velocity = _median(
        [float(point.relative_velocity_mps) for point in points]
    )
    representative = min(
        points,
        key=lambda point: (
            abs(float(point.x_forward_m) - x_forward)
            + abs(float(point.y_right_m) - y_right)
        ),
    )
    return _ClusterMeasurement(
        points=tuple(points),
        x_forward_m=x_forward,
        y_right_m=y_right,
        z_up_m=z_up,
        relative_velocity_mps=relative_velocity,
        max_height_above_road_m=max_height,
        world_location=getattr(representative, "world_location", None),
    )


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return 0.5 * (ordered[middle - 1] + ordered[middle])


def _percentile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = quantile * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def as_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)
