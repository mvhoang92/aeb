#!/usr/bin/env python

"""Run deterministic radar-only AEB scenarios and write tick-level logs."""

from __future__ import print_function

import argparse
import csv
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = AEB_ROOT.parent
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from control.brake import AEBState, apply_brake_override
from core.radar_aeb_pipeline import RadarAEBPipeline
from two_panel_common import RadarSensor, carla, load_yaml


DEFAULT_SENSOR_CONFIG = AEB_ROOT / "configs" / "sensors.yaml"
DEFAULT_SCENARIO_CONFIG = AEB_ROOT / "configs" / "radar_aeb_scenarios.yaml"
DEFAULT_LOG_ROOT = AEB_ROOT / "logs"

TICK_FIELDS = [
    "scenario_id",
    "frame",
    "sim_time_s",
    "elapsed_s",
    "ego_speed_mps",
    "ego_speed_kph",
    "ego_acceleration_mps2",
    "ego_jerk_mps3",
    "ego_x_m",
    "ego_y_m",
    "ego_lane_id",
    "target_speed_mps",
    "target_speed_kph",
    "target_x_m",
    "target_y_m",
    "target_lane_id",
    "center_distance_m",
    "bumper_gap_m",
    "lateral_offset_m",
    "radar_frame",
    "raw_points",
    "path_candidates",
    "ground_ignored",
    "clusters",
    "confirmed_clusters",
    "target_track_id",
    "target_cluster_points",
    "target_distance_m",
    "target_lateral_m",
    "target_relative_velocity_mps",
    "ttc_s",
    "required_distance_m",
    "distance_margin_m",
    "aeb_state",
    "aeb_reason",
    "brake_cmd",
    "throttle_cmd",
    "aeb_override",
    "collision_count",
    "control_mode",
]

SUMMARY_FIELDS = [
    "scenario_id",
    "run_index",
    "description",
    "status",
    "expected_brake",
    "brake_activated",
    "expected_collision",
    "collision",
    "duration_s",
    "first_warning_s",
    "first_brake_s",
    "brake_speed_kph",
    "brake_gap_m",
    "minimum_center_distance_m",
    "minimum_bumper_gap_m",
    "minimum_ttc_s",
    "brake_required_distance_m",
    "brake_distance_margin_m",
    "maximum_deceleration_mps2",
    "maximum_abs_jerk_mps3",
    "final_speed_kph",
    "target_confirmed_rate_pct",
    "maximum_raw_points",
    "maximum_path_candidates",
    "maximum_clusters",
    "maximum_confirmed_clusters",
    "log_file",
    "failure_reason",
]


class HeadlessRadarAEB(object):
    """Radar AEB runtime without creating a pygame/manual-control window."""

    def __init__(self, ego, config, carla_map):
        self.ego = ego
        self.radar = RadarSensor(ego, config.get("front_radar", {}))
        self.pipeline = RadarAEBPipeline(ego, config, carla_map)
        self.decision = self.pipeline.decision
        self.aeb_override_active = False

    def tick(self):
        frame = self.pipeline.update(self.radar)
        self.decision = frame.decision
        if self.decision.state == AEBState.BRAKE:
            apply_brake_override(self.ego, self.decision)
            self.aeb_override_active = True
        elif self.aeb_override_active:
            apply_brake_override(self.ego, self.decision)
            self.aeb_override_active = False
        return frame

    def destroy(self):
        self.pipeline.reset()
        self.radar.destroy()


class CollisionRecorder(object):
    def __init__(self, vehicle):
        self.events = []
        world = vehicle.get_world()
        blueprint = world.get_blueprint_library().find("sensor.other.collision")
        self.sensor = world.spawn_actor(
            blueprint,
            carla.Transform(),
            attach_to=vehicle,
        )
        self.sensor.listen(self.events.append)

    def destroy(self):
        if self.sensor is None:
            return
        try:
            self.sensor.stop()
            self.sensor.destroy()
        except RuntimeError:
            pass
        self.sensor = None


class ScenarioRunner(object):
    def __init__(self, args):
        self.args = args
        self.sensor_config = load_yaml(args.sensor_config)
        self.scenario_config = load_yaml(args.scenario_config)
        self.runner_config = self.scenario_config.get("runner", {})
        self.args.control_mode = (
            self.args.control_mode
            or str(self.runner_config.get("control_mode", "deterministic"))
        )
        self.client = carla.Client(args.host, args.port)
        self.client.set_timeout(args.timeout)
        self.world = self.client.get_world()
        self.original_settings = self.world.get_settings()
        self.carla_map = self.world.get_map()
        self.managed_actors = []

    def run(self):
        self._ensure_map()
        self._enable_synchronous_mode()
        run_directory = self._create_run_directory()
        summaries = []
        try:
            scenarios = self._selected_scenarios()
            jobs = [
                (scenario, run_index)
                for scenario in scenarios
                for run_index in range(1, self.args.repeat + 1)
            ]
            for index, (scenario, run_index) in enumerate(jobs, 1):
                print(
                    "[{}/{}] {} run {}/{}: {}".format(
                        index,
                        len(jobs),
                        scenario["id"],
                        run_index,
                        self.args.repeat,
                        scenario.get("description", ""),
                    )
                )
                summary = self._run_scenario(
                    scenario,
                    run_directory,
                    run_index,
                )
                summaries.append(summary)
                print(
                    "  {} | brake={} collision={} min_gap={}m log={}".format(
                        summary["status"],
                        summary["brake_activated"],
                        summary["collision"],
                        format_number(summary["minimum_bumper_gap_m"], 2),
                        summary["log_file"],
                    )
                )
        finally:
            self._destroy_managed_actors()
            self.world.apply_settings(self.original_settings)

        self._write_summary(run_directory, summaries)
        self._write_aggregate_summary(run_directory, summaries)
        self._write_metadata(run_directory, summaries)
        print("\nLog directory: {}".format(run_directory))
        return summaries

    def _ensure_map(self):
        expected_map = str(self.runner_config.get("map", "Town04"))
        current_map = self.world.get_map().name.split("/")[-1]
        if current_map == expected_map:
            return
        if not self.args.load_map:
            raise RuntimeError(
                "CARLA đang ở map {}, cần {}. Dùng --load-map để tự load.".format(
                    current_map,
                    expected_map,
                )
            )
        self.world = self.client.load_world(expected_map)
        self.carla_map = self.world.get_map()
        self.original_settings = self.world.get_settings()

    def _enable_synchronous_mode(self):
        settings = self.world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = float(
            self.runner_config.get("fixed_delta_seconds", 0.05)
        )
        self.world.apply_settings(settings)
        self.world.tick()

    def _create_run_directory(self):
        run_id = self.args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        run_directory = Path(self.args.log_root) / run_id
        run_directory.mkdir(parents=True, exist_ok=False)
        return run_directory

    def _selected_scenarios(self):
        scenarios = self.scenario_config.get("scenarios", [])
        if not self.args.scenario:
            return scenarios
        requested = set(self.args.scenario)
        selected = [scenario for scenario in scenarios if scenario["id"] in requested]
        missing = requested - set(scenario["id"] for scenario in selected)
        if missing:
            raise ValueError("Không tìm thấy scenario: {}".format(", ".join(sorted(missing))))
        return selected

    def _run_scenario(self, scenario, run_directory, run_index):
        self._destroy_managed_actors()
        ego = self._spawn_ego()
        collision = CollisionRecorder(ego)
        system = HeadlessRadarAEB(
            ego,
            self.sensor_config,
            self.carla_map,
        )
        target = None
        rows = []
        try:
            ego_speed_mps = kph_to_mps(scenario.get("ego_speed_kph", 0.0))
            self._initialize_vehicle_speed(ego, ego_speed_mps)
            target = self._spawn_target(ego, scenario)
            if target is not None:
                self.managed_actors.append(target)

            settle_ticks = int(self.runner_config.get("settle_ticks", 4))
            for _ in range(settle_ticks):
                self._apply_target_control(target, scenario, 0.0)
                self._maintain_ego_speed(ego, ego_speed_mps)
                frame = self.world.tick()
                self._wait_for_radar(system, frame)
                system.tick()

            start_snapshot = self.world.get_snapshot()
            start_time_s = start_snapshot.timestamp.elapsed_seconds
            max_duration_s = float(scenario.get("duration_s", 8.0))
            stop_hold_ticks = max(
                1,
                int(
                    round(
                        float(self.runner_config.get("stop_hold_time_s", 0.5))
                        / float(self.runner_config.get("fixed_delta_seconds", 0.05))
                    )
                ),
            )
            stop_ticks = 0
            brake_activated = False

            while True:
                snapshot = self.world.get_snapshot()
                elapsed_s = snapshot.timestamp.elapsed_seconds - start_time_s
                self._apply_target_control(target, scenario, elapsed_s)
                if not system.aeb_override_active:
                    self._maintain_ego_speed(ego, ego_speed_mps)

                frame = self.world.tick()
                self._wait_for_radar(system, frame)
                system.tick()
                snapshot = self.world.get_snapshot()
                elapsed_s = snapshot.timestamp.elapsed_seconds - start_time_s
                row = self._make_tick_row(
                    scenario,
                    snapshot,
                    elapsed_s,
                    ego,
                    target,
                    system,
                    collision,
                )
                add_motion_metrics(row, rows[-1] if rows else None)
                rows.append(row)
                brake_activated = brake_activated or system.aeb_override_active

                if collision.events:
                    break
                if brake_activated and vehicle_speed_mps(ego) <= float(
                    self.runner_config.get("stop_speed_mps", 0.30)
                ):
                    stop_ticks += 1
                else:
                    stop_ticks = 0
                if stop_ticks >= stop_hold_ticks:
                    break
                if elapsed_s >= max_duration_s:
                    break

            suffix = (
                "_run_{:02d}".format(run_index)
                if self.args.repeat > 1
                else ""
            )
            log_path = run_directory / "{}{}.csv".format(
                scenario["id"],
                suffix,
            )
            write_csv(log_path, TICK_FIELDS, rows)
            return summarize_scenario(
                scenario,
                rows,
                log_path.name,
                run_index,
            )
        finally:
            system.destroy()
            collision.destroy()
            self._destroy_actor(target)
            self._destroy_actor(ego)
            self.managed_actors = []
            self.world.tick()

    def _spawn_ego(self):
        spawn_index = int(self.runner_config.get("spawn_index", 18))
        spawn_points = self.carla_map.get_spawn_points()
        if spawn_index < 0 or spawn_index >= len(spawn_points):
            raise ValueError("spawn_index không hợp lệ: {}".format(spawn_index))
        blueprint = self.world.get_blueprint_library().find(
            self.sensor_config.get("ego", {}).get(
                "blueprint",
                "vehicle.tesla.model3",
            )
        )
        if blueprint.has_attribute("role_name"):
            blueprint.set_attribute("role_name", "aeb_scenario_ego")
        ego = self.world.try_spawn_actor(blueprint, spawn_points[spawn_index])
        if ego is None:
            raise RuntimeError("Không spawn được ego tại index {}".format(spawn_index))
        self.managed_actors.append(ego)
        self.world.tick()
        return ego

    def _initialize_vehicle_speed(self, vehicle, speed_mps):
        direction = vehicle.get_transform().get_forward_vector()
        vehicle.set_target_velocity(scale_vector(direction, speed_mps))
        for _ in range(2):
            self.world.tick()

    def _spawn_target(self, ego, scenario):
        scenario_type = scenario.get("type")
        if scenario_type == "clear_road":
            return None

        ego_waypoint = self.carla_map.get_waypoint(
            ego.get_location(),
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )
        if ego_waypoint is None:
            raise RuntimeError("Không tìm được waypoint cho ego")

        initial_gap_m = float(scenario.get("initial_gap_m", 25.0))
        target_blueprint = self.world.get_blueprint_library().find(
            self.runner_config.get("target_blueprint", "vehicle.audi.tt")
        )
        if target_blueprint.has_attribute("role_name"):
            target_blueprint.set_attribute("role_name", "aeb_scenario_target")

        provisional_waypoint = first_waypoint_ahead(ego_waypoint, initial_gap_m + 6.0)
        target = self.world.try_spawn_actor(
            target_blueprint,
            raised_transform(provisional_waypoint.transform),
        )
        if target is None:
            raise RuntimeError("Không spawn được xe mục tiêu")

        center_distance_m = (
            initial_gap_m
            + float(ego.bounding_box.extent.x)
            + float(target.bounding_box.extent.x)
        )
        target_waypoint = first_waypoint_ahead(ego_waypoint, center_distance_m)
        if scenario_type == "adjacent_stationary":
            target_waypoint = adjacent_driving_waypoint(
                target_waypoint,
                scenario.get("adjacent_lane", "left"),
            )
        target.set_transform(raised_transform(target_waypoint.transform))
        target.set_target_velocity(carla.Vector3D())
        target.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
        self.world.tick()
        return target

    def _maintain_ego_speed(self, ego, target_speed_mps):
        if self.args.control_mode == "physics":
            self._apply_speed_control(ego, target_speed_mps)
            return
        direction = ego.get_transform().get_forward_vector()
        ego.set_target_velocity(scale_vector(direction, target_speed_mps))
        ego.apply_control(carla.VehicleControl(throttle=0.0, steer=0.0, brake=0.0))

    def _apply_speed_control(self, vehicle, target_speed_mps):
        speed_error = float(target_speed_mps) - vehicle_speed_mps(vehicle)
        kp = float(self.runner_config.get("physics_speed_kp", 0.35))
        feedforward = float(
            self.runner_config.get("physics_throttle_feedforward", 0.18)
        )
        throttle_limit = float(
            self.runner_config.get("physics_throttle_limit", 0.70)
        )
        brake_limit = float(
            self.runner_config.get("physics_brake_limit", 0.40)
        )
        if speed_error >= 0.0:
            throttle = clamp(feedforward + kp * speed_error, 0.0, throttle_limit)
            brake = 0.0
        else:
            throttle = 0.0
            brake = clamp(-kp * speed_error, 0.0, brake_limit)
        vehicle.apply_control(
            carla.VehicleControl(
                throttle=throttle,
                steer=0.0,
                brake=brake,
            )
        )

    def _apply_target_control(self, target, scenario, elapsed_s):
        if target is None:
            return
        scenario_type = scenario.get("type")
        if scenario_type in ("stationary_lead", "adjacent_stationary"):
            target.apply_control(
                carla.VehicleControl(throttle=0.0, brake=1.0, hand_brake=True)
            )
            return
        if scenario_type == "braking_lead" and elapsed_s >= float(
            scenario.get("target_brake_time_s", 1.5)
        ):
            target.apply_control(
                carla.VehicleControl(
                    throttle=0.0,
                    brake=float(scenario.get("target_brake", 1.0)),
                )
            )
            return

        target_speed_mps = kph_to_mps(scenario.get("target_speed_kph", 0.0))
        if self.args.control_mode == "physics":
            self._apply_speed_control(target, target_speed_mps)
            return
        direction = target.get_transform().get_forward_vector()
        target.set_target_velocity(scale_vector(direction, target_speed_mps))
        target.apply_control(carla.VehicleControl(throttle=0.0, brake=0.0))

    def _wait_for_radar(self, system, world_frame):
        timeout_s = float(self.runner_config.get("sensor_wait_timeout_s", 1.0))
        deadline = time.monotonic() + timeout_s
        while system.radar is not None and (
            system.radar.frame is None or system.radar.frame < world_frame
        ):
            if time.monotonic() >= deadline:
                return
            time.sleep(0.001)

    def _make_tick_row(
        self,
        scenario,
        snapshot,
        elapsed_s,
        ego,
        target_actor,
        system,
        collision,
    ):
        pipeline = system.pipeline
        target_cluster = pipeline.selected_target
        raw_points = system.radar.points if system.radar is not None else []
        ego_control = ego.get_control()
        center_distance, bumper_gap, lateral_offset = actor_distances(
            ego,
            target_actor,
        )
        target_speed = vehicle_speed_mps(target_actor)
        ego_location = ego.get_location()
        target_location = target_actor.get_location() if target_actor is not None else None
        ego_forward = ego.get_transform().get_forward_vector()
        ego_acceleration = ego.get_acceleration()
        longitudinal_acceleration = (
            ego_acceleration.x * ego_forward.x
            + ego_acceleration.y * ego_forward.y
            + ego_acceleration.z * ego_forward.z
        )
        ego_waypoint = self.carla_map.get_waypoint(
            ego_location,
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )
        target_waypoint = (
            self.carla_map.get_waypoint(
                target_location,
                project_to_road=True,
                lane_type=carla.LaneType.Driving,
            )
            if target_location is not None
            else None
        )
        ttc_s = system.decision.ttc_s
        return {
            "scenario_id": scenario["id"],
            "frame": snapshot.frame,
            "sim_time_s": round(snapshot.timestamp.elapsed_seconds, 4),
            "elapsed_s": round(elapsed_s, 4),
            "ego_speed_mps": round(vehicle_speed_mps(ego), 4),
            "ego_speed_kph": round(vehicle_speed_mps(ego) * 3.6, 3),
            "ego_acceleration_mps2": round(longitudinal_acceleration, 4),
            "ego_jerk_mps3": None,
            "ego_x_m": round(ego_location.x, 4),
            "ego_y_m": round(ego_location.y, 4),
            "ego_lane_id": ego_waypoint.lane_id if ego_waypoint is not None else None,
            "target_speed_mps": optional_round(target_speed, 4),
            "target_speed_kph": optional_round(
                None if target_speed is None else target_speed * 3.6,
                3,
            ),
            "target_x_m": optional_round(
                target_location.x if target_location is not None else None,
                4,
            ),
            "target_y_m": optional_round(
                target_location.y if target_location is not None else None,
                4,
            ),
            "target_lane_id": (
                target_waypoint.lane_id if target_waypoint is not None else None
            ),
            "center_distance_m": optional_round(center_distance, 4),
            "bumper_gap_m": optional_round(bumper_gap, 4),
            "lateral_offset_m": optional_round(lateral_offset, 4),
            "radar_frame": system.radar.frame if system.radar is not None else None,
            "raw_points": len(raw_points),
            "path_candidates": len(pipeline.candidate_points),
            "ground_ignored": sum(
                1 for point in raw_points if pipeline.is_ground_point(point)
            ),
            "clusters": len(pipeline.tracked_clusters),
            "confirmed_clusters": sum(
                1
                for cluster in pipeline.tracked_clusters
                if cluster.confirmed and not cluster.is_stale
            ),
            "target_track_id": (
                target_cluster.track_id if target_cluster is not None else None
            ),
            "target_cluster_points": (
                target_cluster.point_count if target_cluster is not None else None
            ),
            "target_distance_m": optional_round(
                target_cluster.x_forward_m if target_cluster is not None else None,
                4,
            ),
            "target_lateral_m": optional_round(
                target_cluster.y_right_m if target_cluster is not None else None,
                4,
            ),
            "target_relative_velocity_mps": optional_round(
                (
                    target_cluster.relative_velocity_mps
                    if target_cluster is not None
                    else None
                ),
                4,
            ),
            "ttc_s": optional_round(ttc_s if math.isfinite(ttc_s) else None, 4),
            "required_distance_m": optional_round(
                system.decision.required_distance_m,
                4,
            ),
            "distance_margin_m": optional_round(
                system.decision.distance_margin_m,
                4,
            ),
            "aeb_state": system.decision.state.value,
            "aeb_reason": system.decision.reason,
            "brake_cmd": round(float(ego_control.brake), 4),
            "throttle_cmd": round(float(ego_control.throttle), 4),
            "aeb_override": int(system.aeb_override_active),
            "collision_count": len(collision.events),
            "control_mode": self.args.control_mode,
        }

    def _write_summary(self, run_directory, summaries):
        write_csv(run_directory / "summary.csv", SUMMARY_FIELDS, summaries)
        with open(str(run_directory / "summary.json"), "w") as stream:
            json.dump(summaries, stream, ensure_ascii=False, indent=2)

    def _write_aggregate_summary(self, run_directory, summaries):
        aggregate = aggregate_summaries(summaries)
        if not aggregate:
            return
        write_csv(
            run_directory / "aggregate_summary.csv",
            list(aggregate[0].keys()),
            aggregate,
        )
        with open(str(run_directory / "aggregate_summary.json"), "w") as stream:
            json.dump(aggregate, stream, ensure_ascii=False, indent=2)

    def _write_metadata(self, run_directory, summaries):
        metadata = {
            "created_at": datetime.now().isoformat(),
            "carla_map": self.world.get_map().name,
            "fixed_delta_seconds": self.runner_config.get(
                "fixed_delta_seconds",
                0.05,
            ),
            "sensor_config": str(self.args.sensor_config),
            "scenario_config": str(self.args.scenario_config),
            "scenario_count": len(summaries),
            "repeat": self.args.repeat,
            "control_mode": self.args.control_mode,
            "passed": sum(1 for summary in summaries if summary["status"] == "PASS"),
            "failed": sum(1 for summary in summaries if summary["status"] == "FAIL"),
        }
        with open(str(run_directory / "run_metadata.json"), "w") as stream:
            json.dump(metadata, stream, ensure_ascii=False, indent=2)

    def _destroy_actor(self, actor):
        if actor is None:
            return
        try:
            actor.destroy()
        except RuntimeError:
            pass
        if actor in self.managed_actors:
            self.managed_actors.remove(actor)

    def _destroy_managed_actors(self):
        for actor in list(reversed(self.managed_actors)):
            self._destroy_actor(actor)
        self.managed_actors = []


def summarize_scenario(scenario, rows, log_file, run_index=1):
    brake_rows = [row for row in rows if row["aeb_override"]]
    warning_rows = [
        row for row in rows if row["aeb_state"] in ("WARNING", "BRAKE")
    ]
    collision = any(row["collision_count"] for row in rows)
    brake_activated = bool(brake_rows)
    expected_brake = bool(scenario.get("expected_brake", False))
    expected_collision = bool(scenario.get("expected_collision", False))
    failures = []
    if brake_activated != expected_brake:
        failures.append(
            "expected_brake={} actual={}".format(expected_brake, brake_activated)
        )
    if collision != expected_collision:
        failures.append(
            "expected_collision={} actual={}".format(expected_collision, collision)
        )

    center_distances = numeric_values(rows, "center_distance_m")
    bumper_gaps = numeric_values(rows, "bumper_gap_m")
    finite_ttc = numeric_values(rows, "ttc_s")
    metric_start_s = float(scenario.get("metrics_ignore_initial_s", 0.25))
    metric_rows = [
        row for row in rows if float(row.get("elapsed_s", 0.0)) >= metric_start_s
    ]
    accelerations = numeric_values(metric_rows, "ego_acceleration_mps2")
    jerks = numeric_values(metric_rows, "ego_jerk_mps3")
    if expected_brake and not collision and bumper_gaps:
        minimum_stop_gap = float(scenario.get("min_stop_gap_m", 0.5))
        if min(bumper_gaps) < minimum_stop_gap:
            failures.append(
                "minimum_gap={:.3f}m below {:.3f}m".format(
                    min(bumper_gaps),
                    minimum_stop_gap,
                )
            )
    first_brake = brake_rows[0] if brake_rows else None
    first_warning = warning_rows[0] if warning_rows else None
    return {
        "scenario_id": scenario["id"],
        "run_index": run_index,
        "description": scenario.get("description", ""),
        "status": "FAIL" if failures else "PASS",
        "expected_brake": expected_brake,
        "brake_activated": brake_activated,
        "expected_collision": expected_collision,
        "collision": collision,
        "duration_s": optional_round(rows[-1]["elapsed_s"] if rows else 0.0, 3),
        "first_warning_s": optional_round(
            first_warning["elapsed_s"] if first_warning else None,
            3,
        ),
        "first_brake_s": optional_round(
            first_brake["elapsed_s"] if first_brake else None,
            3,
        ),
        "brake_speed_kph": optional_round(
            first_brake["ego_speed_kph"] if first_brake else None,
            3,
        ),
        "brake_gap_m": optional_round(
            first_brake["bumper_gap_m"] if first_brake else None,
            3,
        ),
        "minimum_center_distance_m": optional_round(
            min(center_distances) if center_distances else None,
            3,
        ),
        "minimum_bumper_gap_m": optional_round(
            (
                min(bumper_gaps)
                if bumper_gaps
                and scenario.get("type") != "adjacent_stationary"
                else None
            ),
            3,
        ),
        "minimum_ttc_s": optional_round(min(finite_ttc) if finite_ttc else None, 3),
        "brake_required_distance_m": optional_round(
            first_brake["required_distance_m"] if first_brake else None,
            3,
        ),
        "brake_distance_margin_m": optional_round(
            first_brake["distance_margin_m"] if first_brake else None,
            3,
        ),
        "maximum_deceleration_mps2": optional_round(
            max(0.0, -min(accelerations)) if accelerations else None,
            3,
        ),
        "maximum_abs_jerk_mps3": optional_round(
            max(abs(value) for value in jerks) if jerks else None,
            3,
        ),
        "final_speed_kph": optional_round(
            rows[-1]["ego_speed_kph"] if rows else None,
            3,
        ),
        "target_confirmed_rate_pct": optional_round(
            (
                100.0
                * sum(1 for row in rows if row["target_track_id"] is not None)
                / len(rows)
                if rows
                else None
            ),
            2,
        ),
        "maximum_raw_points": max_value(rows, "raw_points"),
        "maximum_path_candidates": max_value(rows, "path_candidates"),
        "maximum_clusters": max_value(rows, "clusters"),
        "maximum_confirmed_clusters": max_value(rows, "confirmed_clusters"),
        "log_file": log_file,
        "failure_reason": "; ".join(failures),
    }


def add_motion_metrics(row, previous_row):
    if previous_row is None:
        return
    dt = float(row["sim_time_s"]) - float(previous_row["sim_time_s"])
    if dt <= 1e-9:
        return
    acceleration = row.get("ego_acceleration_mps2")
    previous_acceleration = previous_row.get("ego_acceleration_mps2")
    if acceleration is not None and previous_acceleration is not None:
        row["ego_jerk_mps3"] = round(
            (float(acceleration) - float(previous_acceleration)) / dt,
            4,
        )


def aggregate_summaries(summaries):
    grouped = {}
    for summary in summaries:
        grouped.setdefault(summary["scenario_id"], []).append(summary)
    aggregate = []
    for scenario_id in sorted(grouped):
        rows = grouped[scenario_id]
        gaps = numeric_values(rows, "minimum_bumper_gap_m")
        brake_times = numeric_values(rows, "first_brake_s")
        decelerations = numeric_values(rows, "maximum_deceleration_mps2")
        aggregate.append(
            {
                "scenario_id": scenario_id,
                "runs": len(rows),
                "passes": sum(1 for row in rows if row["status"] == "PASS"),
                "pass_rate_pct": round(
                    100.0
                    * sum(1 for row in rows if row["status"] == "PASS")
                    / len(rows),
                    2,
                ),
                "brake_rate_pct": round(
                    100.0
                    * sum(1 for row in rows if row["brake_activated"])
                    / len(rows),
                    2,
                ),
                "minimum_gap_m": optional_round(min(gaps) if gaps else None, 3),
                "mean_brake_time_s": optional_round(
                    sum(brake_times) / len(brake_times)
                    if brake_times
                    else None,
                    3,
                ),
                "maximum_deceleration_mps2": optional_round(
                    max(decelerations) if decelerations else None,
                    3,
                ),
            }
        )
    return aggregate


def actor_distances(ego, target):
    if target is None:
        return None, None, None
    ego_location = ego.get_location()
    target_location = target.get_location()
    center_distance = ego_location.distance(target_location)
    delta_x = target_location.x - ego_location.x
    delta_y = target_location.y - ego_location.y
    forward = ego.get_transform().get_forward_vector()
    right_x = -forward.y
    right_y = forward.x
    longitudinal_distance = delta_x * forward.x + delta_y * forward.y
    lateral_offset = delta_x * right_x + delta_y * right_y
    bumper_gap = (
        longitudinal_distance
        - float(ego.bounding_box.extent.x)
        - float(target.bounding_box.extent.x)
    )
    return center_distance, bumper_gap, lateral_offset


def adjacent_driving_waypoint(waypoint, direction):
    getters = (
        ("left", waypoint.get_left_lane),
        ("right", waypoint.get_right_lane),
    )
    requested = str(direction).lower()
    ordered = sorted(getters, key=lambda item: item[0] != requested)
    for _, getter in ordered:
        candidate = getter()
        if candidate is None:
            continue
        if candidate.lane_type != carla.LaneType.Driving:
            continue
        if candidate.lane_id * waypoint.lane_id <= 0:
            continue
        return candidate
    raise RuntimeError("Không tìm được làn kế bên cùng chiều")


def first_waypoint_ahead(waypoint, distance_m):
    candidates = waypoint.next(float(distance_m))
    if not candidates:
        raise RuntimeError(
            "Không tìm được waypoint phía trước ở khoảng cách {} m".format(distance_m)
        )
    return min(
        candidates,
        key=lambda candidate: abs(
            normalized_angle_degrees(
                candidate.transform.rotation.yaw
                - waypoint.transform.rotation.yaw
            )
        ),
    )


def raised_transform(transform):
    location = transform.location
    return carla.Transform(
        carla.Location(x=location.x, y=location.y, z=location.z + 0.30),
        transform.rotation,
    )


def normalized_angle_degrees(value):
    return (float(value) + 180.0) % 360.0 - 180.0


def vehicle_speed_mps(vehicle):
    if vehicle is None:
        return None
    velocity = vehicle.get_velocity()
    return math.sqrt(
        velocity.x * velocity.x
        + velocity.y * velocity.y
        + velocity.z * velocity.z
    )


def scale_vector(vector, scale):
    return carla.Vector3D(
        x=vector.x * scale,
        y=vector.y * scale,
        z=vector.z * scale,
    )


def kph_to_mps(value):
    return float(value) / 3.6


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def optional_round(value, digits):
    if value is None:
        return None
    return round(float(value), digits)


def numeric_values(rows, key):
    return [
        float(row[key])
        for row in rows
        if row.get(key) is not None and row.get(key) != ""
    ]


def max_value(rows, key):
    values = numeric_values(rows, key)
    return max(values) if values else 0


def format_number(value, digits):
    if value is None:
        return "--"
    return ("{:." + str(digits) + "f}").format(float(value))


def write_csv(path, fieldnames, rows):
    with open(str(path), "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--sensor-config",
        type=Path,
        default=DEFAULT_SENSOR_CONFIG,
    )
    parser.add_argument(
        "--scenario-config",
        type=Path,
        default=DEFAULT_SCENARIO_CONFIG,
    )
    parser.add_argument("--log-root", type=Path, default=DEFAULT_LOG_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Số lần lặp mỗi scenario.",
    )
    parser.add_argument(
        "--control-mode",
        choices=("deterministic", "physics"),
        default=None,
        help="deterministic dùng set_target_velocity; physics dùng throttle/brake.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        help="Chỉ chạy scenario có ID này; có thể truyền nhiều lần.",
    )
    parser.add_argument("--load-map", action="store_true")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat phải lớn hơn hoặc bằng 1")
    return args


def main():
    args = parse_args()
    summaries = ScenarioRunner(args).run()
    failed = [summary for summary in summaries if summary["status"] != "PASS"]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
