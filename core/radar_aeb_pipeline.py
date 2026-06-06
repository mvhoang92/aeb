"""Shared radar-only AEB pipeline for interactive UI and headless scenarios."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from control.brake import (
    AEBDecision,
    AEBState,
    BinaryAEB,
    BinaryBrakeConfig,
    as_bool,
    compute_ttc,
)
from radar_cluster import RadarCluster, RadarClusterConfig, RadarClusterTracker


@dataclass(frozen=True)
class RadarAEBFrame:
    radar_frame: Optional[int]
    radar_timestamp_s: Optional[float]
    ego_speed_mps: float
    raw_point_count: int
    candidate_point_count: int
    ground_point_count: int
    tracked_cluster_count: int
    confirmed_cluster_count: int
    target: Optional[RadarCluster]
    decision: AEBDecision
    required_distance_m: Optional[float]
    distance_margin_m: Optional[float]


class RadarAEBPipeline(object):
    """Process radar points, track obstacles and produce one AEB decision."""

    def __init__(self, ego, config, carla_map=None):
        self.config = config
        self.ego = ego
        self.ego_id = getattr(ego, "id", None)
        self.carla_map = carla_map
        self.radar_config = config.get("front_radar", {})
        self.fusion_config = config.get("fusion", {})
        self.brake_config = config.get("brake", {})
        self.aeb_config = BinaryBrakeConfig.from_mapping(self.brake_config)
        self.aeb = BinaryAEB(self.aeb_config)
        self.cluster_config = RadarClusterConfig.from_mapping(
            config.get("radar_cluster", {})
        )
        self.cluster_tracker = RadarClusterTracker(self.cluster_config)
        self.tracked_clusters = []
        self.candidate_points = []
        self.selected_target = None
        self.cluster_frame = None
        self.cluster_sensor_token = None
        self.path_curvature_1pm = 0.0
        self.path_horizon_m = 0.0
        self.predicted_path = []
        self.road_height_cache = {}
        self.road_height_cache_frame = None
        self.decision = self.aeb.decide(None, None)
        self.last_frame = RadarAEBFrame(
            radar_frame=None,
            radar_timestamp_s=None,
            ego_speed_mps=0.0,
            raw_point_count=0,
            candidate_point_count=0,
            ground_point_count=0,
            tracked_cluster_count=0,
            confirmed_cluster_count=0,
            target=None,
            decision=self.decision,
            required_distance_m=None,
            distance_margin_m=None,
        )
        self.update_predicted_path()

    def set_ego(self, ego):
        ego_id = getattr(ego, "id", None)
        if ego_id == self.ego_id:
            self.ego = ego
            return
        self.ego = ego
        self.ego_id = ego_id
        self.carla_map = (
            ego.get_world().get_map()
            if ego is not None
            else self.carla_map
        )
        self.reset()

    def reset(self):
        self.aeb.reset()
        self.cluster_tracker.reset()
        self.tracked_clusters = []
        self.candidate_points = []
        self.selected_target = None
        self.cluster_frame = None
        self.cluster_sensor_token = None
        self.path_curvature_1pm = 0.0
        self.path_horizon_m = 0.0
        self.predicted_path = []
        self.road_height_cache = {}
        self.road_height_cache_frame = None
        self.decision = self.aeb.decide(None, None)

    def update(self, radar) -> RadarAEBFrame:
        radar_frame = radar.frame if radar is not None else None
        radar_timestamp = radar.timestamp if radar is not None else None
        if radar_frame != self.road_height_cache_frame:
            self.road_height_cache = {}
            self.road_height_cache_frame = radar_frame

        self.update_predicted_path()
        ego_speed_mps = self.ego_speed_mps()
        if self.disable_in_reverse() and self.ego_is_reversing():
            self.cluster_tracker.reset()
            self.tracked_clusters = []
            self.candidate_points = []
            self.selected_target = None
            self.cluster_frame = None
            self.aeb.reset()
            self.decision = AEBDecision(
                state=AEBState.RELEASE,
                brake=0.0,
                throttle=0.0,
                ttc_s=math.inf,
                target_distance_m=None,
                relative_velocity_mps=None,
                should_override=False,
                reason="reverse_gear_aeb_disabled",
            )
            return self._build_frame(radar, ego_speed_mps)

        self._update_clusters(radar)
        self.selected_target = self.select_target()
        self.decision = self.aeb.decide_from_target(
            self.selected_target,
            timestamp_s=radar_timestamp,
            ego_speed_mps=ego_speed_mps,
        )
        return self._build_frame(radar, ego_speed_mps)

    def _build_frame(self, radar, ego_speed_mps):
        raw_points = radar.points if radar is not None else []
        ground_count = sum(1 for point in raw_points if self.is_ground_point(point))
        target = self.selected_target
        required_distance = self.decision.required_distance_m
        distance_margin = None
        if target is not None and required_distance is not None:
            distance_margin = target.x_forward_m - required_distance
        self.last_frame = RadarAEBFrame(
            radar_frame=radar.frame if radar is not None else None,
            radar_timestamp_s=radar.timestamp if radar is not None else None,
            ego_speed_mps=ego_speed_mps,
            raw_point_count=len(raw_points),
            candidate_point_count=len(self.candidate_points),
            ground_point_count=ground_count,
            tracked_cluster_count=len(self.tracked_clusters),
            confirmed_cluster_count=sum(
                1
                for cluster in self.tracked_clusters
                if cluster.confirmed and not cluster.is_stale
            ),
            target=target,
            decision=self.decision,
            required_distance_m=required_distance,
            distance_margin_m=distance_margin,
        )
        return self.last_frame

    def _update_clusters(self, radar):
        if radar is None or radar.frame is None:
            self.candidate_points = []
            return

        sensor_token = id(radar)
        if sensor_token != self.cluster_sensor_token:
            self.cluster_tracker.reset()
            self.tracked_clusters = []
            self.cluster_frame = None
            self.cluster_sensor_token = sensor_token
        if radar.frame == self.cluster_frame:
            return

        self.candidate_points = [
            point for point in radar.points if self.valid_path_target(point)
        ]
        self.tracked_clusters = self.cluster_tracker.update(
            self.candidate_points,
            height_getter=self.height_above_road,
            timestamp_s=radar.timestamp,
        )
        self.cluster_frame = radar.frame

    def select_target(self):
        candidates = [
            cluster
            for cluster in self.tracked_clusters
            if cluster.confirmed and not cluster.is_stale
        ]
        if not candidates:
            return None

        def sort_key(cluster):
            ttc = compute_ttc(
                cluster.x_forward_m,
                cluster.relative_velocity_mps,
            )
            has_ttc = 0 if math.isfinite(ttc) else 1
            return has_ttc, ttc, cluster.x_forward_m

        return min(candidates, key=sort_key)

    def valid_path_target(self, point):
        min_forward = float(
            self.fusion_config.get("min_radar_forward_distance_m", 1.5)
        )
        max_range = float(self.radar_config.get("range", 100.0))
        min_z = float(
            self.brake_config.get(
                "min_radar_z_up_m",
                self.fusion_config.get("min_radar_z_up_m", -0.35),
            )
        )
        max_z = float(
            self.brake_config.get(
                "max_radar_z_up_m",
                self.fusion_config.get("max_radar_z_up_m", 2.5),
            )
        )
        if point.x_forward_m < min_forward or point.x_forward_m > max_range:
            return False
        if point.z_up_m < min_z or point.z_up_m > max_z:
            return False
        if self.distance_to_predicted_path(point) > self.brake_lateral_limit():
            return False
        return not self.is_ground_point(point)

    def is_ground_point(self, point):
        min_height = float(
            self.brake_config.get("min_height_above_road_m", 0.20)
        )
        height_above_road = self.height_above_road(point)
        if height_above_road is None:
            return False
        return height_above_road < min_height

    def height_above_road(self, point):
        cache_key = id(point)
        if cache_key in self.road_height_cache:
            return self.road_height_cache[cache_key]
        if getattr(point, "world_location", None) is None or self.ego is None:
            self.road_height_cache[cache_key] = None
            return None

        if self.carla_map is None:
            self.carla_map = self.ego.get_world().get_map()
        waypoint = self.carla_map.get_waypoint(
            point.world_location,
            project_to_road=True,
        )
        if waypoint is None:
            self.road_height_cache[cache_key] = None
            return None

        road_location = waypoint.transform.location
        lateral_distance = math.hypot(
            point.world_location.x - road_location.x,
            point.world_location.y - road_location.y,
        )
        max_lateral = float(
            self.brake_config.get(
                "ground_filter_max_road_lateral_m",
                waypoint.lane_width * 0.75,
            )
        )
        if lateral_distance > max_lateral:
            self.road_height_cache[cache_key] = None
            return None

        height = point.world_location.z - road_location.z
        self.road_height_cache[cache_key] = height
        return height

    def brake_lateral_limit(self):
        configured = self.brake_config.get("max_lateral_offset_m")
        if configured is not None:
            return float(configured)
        if self.ego is None:
            return 1.25
        return float(self.ego.bounding_box.extent.y) + 0.15

    def update_predicted_path(self):
        if self.ego is None:
            self.predicted_path = []
            return

        speed_mps = self.ego_speed_mps()
        yaw_rate_rad_s = math.radians(self.ego.get_angular_velocity().z)
        steer = float(getattr(self.ego.get_control(), "steer", 0.0))
        min_speed = float(
            self.brake_config.get("path_min_speed_for_yaw_rate_mps", 1.0)
        )
        min_yaw_rate = math.radians(
            float(self.brake_config.get("path_min_yaw_rate_deg_s", 0.5))
        )
        steer_gain = float(
            self.brake_config.get("path_steer_curvature_per_unit", 0.06)
        )
        steer_curvature = steer * steer_gain
        if speed_mps >= min_speed and abs(yaw_rate_rad_s) >= min_yaw_rate:
            yaw_curvature = yaw_rate_rad_s / speed_mps
            desired_curvature = 0.75 * yaw_curvature + 0.25 * steer_curvature
        else:
            desired_curvature = steer_curvature

        max_curvature = float(
            self.brake_config.get("path_max_abs_curvature_1pm", 0.12)
        )
        desired_curvature = max(
            -max_curvature,
            min(max_curvature, desired_curvature),
        )
        smoothing = float(self.brake_config.get("path_curvature_smoothing", 0.35))
        smoothing = max(0.0, min(1.0, smoothing))
        self.path_curvature_1pm += smoothing * (
            desired_curvature - self.path_curvature_1pm
        )

        horizon_time_s = float(
            self.brake_config.get("path_horizon_time_s", 2.5)
        )
        min_horizon_m = float(
            self.brake_config.get("path_min_horizon_m", 12.0)
        )
        self.path_horizon_m = min(
            float(self.radar_config.get("range", 100.0)),
            max(min_horizon_m, speed_mps * horizon_time_s),
        )
        self.predicted_path = constant_curvature_path(
            self.path_curvature_1pm,
            self.path_horizon_m,
            float(self.brake_config.get("path_sample_step_m", 1.0)),
            float(self.brake_config.get("path_max_heading_change_deg", 75.0)),
            float(
                self.brake_config.get(
                    "path_max_lateral_deviation_m",
                    6.0,
                )
            ),
        )

    def distance_to_predicted_path(self, point):
        if len(self.predicted_path) < 2:
            return abs(point.y_right_m)

        best_distance_sq = float("inf")
        for index in range(len(self.predicted_path) - 1):
            start_x, start_y, _ = self.predicted_path[index]
            end_x, end_y, _ = self.predicted_path[index + 1]
            segment_x = end_x - start_x
            segment_y = end_y - start_y
            segment_length_sq = segment_x * segment_x + segment_y * segment_y
            if segment_length_sq <= 1e-9:
                continue
            projection = (
                (point.x_forward_m - start_x) * segment_x
                + (point.y_right_m - start_y) * segment_y
            ) / segment_length_sq
            projection = max(0.0, min(1.0, projection))
            nearest_x = start_x + projection * segment_x
            nearest_y = start_y + projection * segment_y
            distance_sq = (
                (point.x_forward_m - nearest_x) ** 2
                + (point.y_right_m - nearest_y) ** 2
            )
            best_distance_sq = min(best_distance_sq, distance_sq)
        return math.sqrt(best_distance_sq)

    def path_description(self):
        curvature = self.path_curvature_1pm
        if abs(curvature) < 0.002:
            return "straight"
        radius = 1.0 / abs(curvature)
        direction = "right" if curvature > 0.0 else "left"
        return "{} R={:.1f}m".format(direction, radius)

    def ego_speed_mps(self):
        if self.ego is None:
            return 0.0
        velocity = self.ego.get_velocity()
        return math.sqrt(
            velocity.x * velocity.x
            + velocity.y * velocity.y
            + velocity.z * velocity.z
        )

    def ego_is_reversing(self):
        if self.ego is None or not hasattr(self.ego, "get_control"):
            return False
        control = self.ego.get_control()
        return bool(getattr(control, "reverse", False)) or int(
            getattr(control, "gear", 0) or 0
        ) < 0

    def disable_in_reverse(self):
        return as_bool(self.brake_config.get("disable_in_reverse", True))


def constant_curvature_path(
    curvature_1pm,
    max_distance_m,
    sample_step_m,
    max_heading_change_deg,
    max_lateral_deviation_m,
):
    step = max(0.25, sample_step_m)
    max_heading = math.radians(max(5.0, max_heading_change_deg))
    points = []
    distance = 0.0
    while distance <= max_distance_m:
        heading = curvature_1pm * distance
        if abs(heading) > max_heading:
            break
        if abs(curvature_1pm) < 1e-5:
            x_forward = distance
            y_right = 0.0
        else:
            x_forward = math.sin(heading) / curvature_1pm
            y_right = (1.0 - math.cos(heading)) / curvature_1pm
        if abs(y_right) > max_lateral_deviation_m:
            break
        points.append((x_forward, y_right, heading))
        distance += step
    return points
