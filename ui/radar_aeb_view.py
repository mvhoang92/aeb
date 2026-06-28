#!/usr/bin/env python

"""Test radar-only binary AEB brake with manual_control.py on the left."""

from __future__ import print_function

import argparse
import math
import sys
import time
from pathlib import Path

AEB_ROOT = Path(__file__).resolve().parents[1]
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from control.brake import (
    AEBState,
    apply_brake_override,
    as_bool,
    compute_ttc,
)
from core.radar_aeb_pipeline import RadarAEBPipeline
from scripts.run_radar_aeb_scenarios import (
    actor_distances,
    adjacent_driving_waypoint,
    clamp,
    first_waypoint_ahead,
    kph_to_mps,
    legacy_target_spec,
    raised_transform,
    scale_vector,
    vehicle_speed_mps,
)
from ui.radar_view import RadarBirdEyePanel
from ui.manual_control_common import (
    add_common_args,
    carla,
    format_float,
    load_yaml,
    pygame,
    run_two_panel,
)


DEFAULT_SCENARIO_CONFIG = (
    AEB_ROOT / "configs" / "scenarios" / "suites" / "radar_only_regression.yaml"
)


class LiveScenarioRuntime(object):
    """Run one radar-only validation scenario inside the pygame UI."""

    def __init__(self, manual_world, args):
        self.manual_world = manual_world
        self.args = args
        self.enabled = bool(args.scenario)
        self.scenario_config = {}
        self.runner_config = {}
        self.scenario = None
        self.control_mode = args.control_mode
        self.scenario_actors = []
        self._carla_map = None
        self.started = False
        self.drive_started = False
        self.completed = False
        self.start_time = None
        self.warmup_started_at = None
        self.warmup_s = max(0.0, float(getattr(args, "scenario_warmup_s", 1.0)))
        self.speed_control_integral = {}
        self.status_message = "manual mode"
        self.stop_after_aeb = not bool(getattr(args, "keep_driving_after_aeb", False))
        self.ego_stop_latched = False
        self.stop_latch_reason = ""
        self.stopped_at = None
        self.final_gap_m = None
        self.final_lateral_m = None
        self.completed_at = None
        self.scenario_autoexit_s = max(
            0.0, float(getattr(args, "scenario_autoexit_s", 0.0))
        )
        self.debug_draw_interval_s = max(
            0.0,
            float(getattr(args, "scenario_debug_interval_s", 0.10)),
        )
        self._last_debug_draw_at = 0.0
        if self.enabled:
            self.scenario_config = load_yaml(args.scenario_config)
            self.runner_config = self.scenario_config.get("runner", {})
            self.control_mode = self.control_mode or str(
                self.runner_config.get("control_mode", "deterministic")
            )
            self.scenario = self._select_scenario(args.scenario)
            self.status_message = "scenario ready: {}".format(self.scenario["id"])

    def start(self):
        if not self.enabled or self.started:
            return
        player = self.manual_world.player
        if player is None:
            return
        carla_map = player.get_world().get_map()
        self._carla_map = carla_map
        self._destroy_stale_scenario_actors(player)
        self._reset_ego(player, carla_map)
        self._sync_world_frame(player.get_world())
        self.scenario_actors = self._spawn_scenario_actors(player, carla_map)
        self._sync_world_frame(player.get_world())
        self._configure_manual_camera()
        self._settle_world(player.get_world())
        self._print_initial_distances(player)
        self.started = True
        self.drive_started = False
        self.completed = False
        self.ego_stop_latched = False
        self.stop_latch_reason = ""
        self.stopped_at = None
        self.completed_at = None
        self.final_gap_m = None
        self.final_lateral_m = None
        self.start_time = None
        self.warmup_started_at = self._sim_time_s()
        self.status_message = "warmup: {}".format(self.scenario["id"])

    def tick(self, aeb_braking=False):
        if not self.enabled:
            return
        if not self.started:
            self.start()
            return
        if not self.drive_started:
            player = self.manual_world.player
            if player is not None:
                self._draw_scenario_debug(player)
                self._apply_ego_hold_control(player, steer=0.0)
            if self._warmup_complete():
                self._begin_drive(player)
            return
        if self.completed:
            player = self.manual_world.player
            if player is not None:
                self._draw_scenario_debug(player)
            if player is not None and self.ego_stop_latched:
                self._hold_ego_stopped(player)
            elif player is not None and self.scenario.get("type") == "clear_road":
                self._maintain_ego_speed(
                    player,
                    kph_to_mps(self.scenario.get("ego_speed_kph", 0.0)),
                    self.scenario,
                )
            return
        player = self.manual_world.player
        if player is None:
            return
        elapsed_s = self.elapsed_s()
        self._apply_scenario_actor_controls(elapsed_s)
        self._draw_scenario_debug(player)
        if self.ego_stop_latched:
            self._hold_ego_stopped(player)
        elif aeb_braking:
            player.apply_control(carla.VehicleControl(throttle=0.0, brake=0.0))
        else:
            self._maintain_ego_speed(
                player,
                kph_to_mps(self.scenario.get("ego_speed_kph", 0.0)),
                self.scenario,
            )
        if elapsed_s >= float(self.scenario.get("duration_s", 8.0)):
            self.completed = True
            self.status_message = "complete: {}".format(self.scenario["id"])
            player.apply_control(
                carla.VehicleControl(
                    throttle=0.0,
                    steer=0.0,
                    brake=0.0,
                    hand_brake=False,
                )
            )

    def _warmup_complete(self):
        if self.warmup_started_at is None:
            return True
        return self._sim_time_s() - self.warmup_started_at >= self.warmup_s

    def _begin_drive(self, player):
        if player is None or self.drive_started:
            return
        self._set_initial_speeds(player)
        self.drive_started = True
        self.completed = False
        self.start_time = self._sim_time_s()
        self.status_message = "running: {}".format(self.scenario["id"])
        print(
            "Scenario drive started: id={} warmup={}s".format(
                self.scenario["id"],
                format_float(self.warmup_s, 1),
            )
        )

    def latch_ego_stop(self, reason="aeb_brake"):
        if not self.enabled or not self.stop_after_aeb:
            return
        if self.ego_stop_latched:
            return
        self.ego_stop_latched = True
        self.stop_latch_reason = str(reason or "aeb_brake")
        self.status_message = "AEB stop latched"
        player = self.manual_world.player
        if player is not None:
            self.speed_control_integral.pop(getattr(player, "id", id(player)), None)
            self._hold_ego_stopped(player)
        print("AEB stop latched: reason={}".format(self.stop_latch_reason))

    def _hold_ego_stopped(self, ego):
        steer = self._lane_follow_steer(ego, self.scenario)
        stop_speed_mps = float(self.runner_config.get("stop_speed_mps", 0.30))
        if vehicle_speed_mps(ego) <= stop_speed_mps:
            if self.stopped_at is None:
                self.stopped_at = self._sim_time_s()
                self._capture_final_gap(ego)
                self.completed = True
                self.status_message = "stopped after AEB"
            release_hold_s = float(
                self.runner_config.get("aeb_stop_release_hold_s", 1.0)
            )
            if self._sim_time_s() - self.stopped_at >= release_hold_s:
                # Đã dừng đủ lâu: nhả phanh chân và gài phanh tay để xe đứng yên
                # mà không phải giữ full brake mãi.
                ego.apply_control(
                    carla.VehicleControl(
                        throttle=0.0,
                        steer=0.0,
                        brake=0.0,
                        hand_brake=True,
                    )
                )
                self.status_message = "parked: brake released"
                return
        self._apply_ego_hold_control(ego, steer=steer)

    def _apply_ego_hold_control(self, ego, steer=0.0):
        ego.apply_control(
            carla.VehicleControl(
                throttle=0.0,
                steer=steer,
                brake=1.0,
                hand_brake=False,
            )
        )

    def _capture_final_gap(self, ego):
        hazard = next(
            (entry for entry in self.scenario_actors if entry["hazard"]),
            self.scenario_actors[0] if self.scenario_actors else None,
        )
        if hazard is None:
            return
        first_capture = self.final_gap_m is None
        _, bumper_gap, lateral_offset = actor_distances(ego, hazard["actor"])
        self.final_gap_m = bumper_gap
        self.final_lateral_m = lateral_offset
        if first_capture:
            print(
                "AEB final stop: gap={}m lateral={}m".format(
                    format_float(self.final_gap_m, 2),
                    format_float(self.final_lateral_m, 2),
                )
            )

    def elapsed_s(self):
        if self.start_time is None:
            return 0.0
        return max(0.0, self._sim_time_s() - self.start_time)

    def _sim_time_s(self):
        player = self.manual_world.player
        if player is None:
            return time.monotonic()
        try:
            return float(player.get_world().get_snapshot().timestamp.elapsed_seconds)
        except RuntimeError:
            return time.monotonic()

    def should_exit(self):
        # Tự thoát sau khi scenario hoàn tất (đã dừng/đủ thời lượng) và nán thêm
        # scenario_autoexit_s giây, phục vụ quay video tự động rồi thoát sạch.
        if not self.enabled or self.scenario_autoexit_s <= 0.0:
            return False
        if not self.completed:
            return False
        if self.completed_at is None:
            self.completed_at = self._sim_time_s()
            return False
        return self._sim_time_s() - self.completed_at >= self.scenario_autoexit_s

    def destroy(self):
        for entry in self.scenario_actors:
            actor = entry.get("actor")
            if actor is None:
                continue
            try:
                actor.destroy()
            except RuntimeError:
                pass
        self.scenario_actors = []

    def _destroy_stale_scenario_actors(self, ego):
        world = ego.get_world()
        destroyed = False
        for actor in world.get_actors().filter("vehicle.*"):
            if actor.id == ego.id:
                continue
            role_name = actor.attributes.get("role_name", "")
            if not role_name.startswith("aeb_scenario_"):
                continue
            try:
                actor.destroy()
                destroyed = True
            except RuntimeError:
                pass
        if destroyed:
            self._sync_world_frame(world)

    def _sync_world_frame(self, world):
        try:
            world.tick()
        except RuntimeError:
            try:
                world.wait_for_tick(1.0)
            except RuntimeError:
                pass

    def _settle_world(self, world):
        settle_ticks = int(self.runner_config.get("settle_ticks", 2))
        for _ in range(max(0, settle_ticks)):
            self._sync_world_frame(world)

    def _configure_manual_camera(self):
        camera_mode = str(getattr(self.args, "scenario_camera", "wide_chase"))
        if camera_mode == "manual":
            return
        camera_manager = getattr(self.manual_world, "camera_manager", None)
        if camera_manager is None:
            return

        Attachment = carla.AttachmentType
        if camera_mode == "high_chase":
            camera_transform = (
                carla.Transform(
                    carla.Location(x=-28.0, z=18.0),
                    carla.Rotation(pitch=18.0),
                ),
                Attachment.SpringArm,
            )
        else:
            camera_transform = (
                carla.Transform(
                    carla.Location(x=-18.0, z=10.0),
                    carla.Rotation(pitch=12.0),
                ),
                Attachment.SpringArm,
            )

        transforms = getattr(camera_manager, "_camera_transforms", None)
        if transforms is None:
            return
        transforms.append(camera_transform)
        camera_manager.transform_index = len(transforms) - 1
        sensor_index = camera_manager.index if camera_manager.index is not None else 0
        camera_manager.set_sensor(sensor_index, notify=False, force_respawn=True)

    def _draw_scenario_debug(self, ego):
        now = self._sim_time_s()
        if (
            self.debug_draw_interval_s > 0.0
            and now - self._last_debug_draw_at < self.debug_draw_interval_s
        ):
            return
        self._last_debug_draw_at = now
        life_time = max(0.08, self.debug_draw_interval_s * 1.5)
        world = ego.get_world()
        debug = world.debug
        ego_location = ego.get_location()
        start = carla.Location(
            x=ego_location.x,
            y=ego_location.y,
            z=ego_location.z + 0.9,
        )
        for entry in self.scenario_actors:
            actor = entry["actor"]
            if actor is None:
                continue
            actor_location = actor.get_location()
            _, bumper_gap, lateral_offset = actor_distances(ego, actor)
            hazard = entry["hazard"]
            color = carla.Color(255, 40, 40) if hazard else carla.Color(60, 220, 80)
            end = carla.Location(
                x=actor_location.x,
                y=actor_location.y,
                z=actor_location.z + 0.9,
            )
            debug.draw_line(
                start,
                end,
                thickness=0.07,
                color=color,
                life_time=life_time,
                persistent_lines=False,
            )
            debug.draw_point(
                end,
                size=0.22,
                color=color,
                life_time=life_time,
                persistent_lines=False,
            )
            label_location = carla.Location(
                x=actor_location.x,
                y=actor_location.y,
                z=actor_location.z + 2.4,
            )
            debug.draw_string(
                label_location,
                "{} gap={}m lat={}m".format(
                    entry["role"],
                    format_float(bumper_gap, 1),
                    format_float(lateral_offset, 1),
                ),
                draw_shadow=True,
                color=color,
                life_time=life_time,
                persistent_lines=False,
            )

    def summary_rows(self):
        if not self.enabled or self.scenario is None:
            return []
        player = self.manual_world.player
        hazard = next(
            (entry for entry in self.scenario_actors if entry["hazard"]),
            self.scenario_actors[0] if self.scenario_actors else None,
        )
        rows = [
            ("Scenario", self.scenario["id"]),
            ("Mode", self.control_mode),
            ("Status", self.status_message),
            ("Actors", len(self.scenario_actors)),
            ("Elapsed", "{} s".format(format_float(self.elapsed_s(), 1))),
            ("Drive started", "yes" if self.drive_started else "no"),
            (
                "Ego target",
                "{} km/h".format(format_float(self.scenario.get("ego_speed_kph", 0.0), 0)),
            ),
            ("Stop after AEB", "ON" if self.stop_after_aeb else "OFF"),
            ("Stop latch", "ON" if self.ego_stop_latched else "OFF"),
        ]
        if player is not None:
            rows.append(
                (
                    "Ego speed",
                    "{} km/h".format(format_float(vehicle_speed_mps(player) * 3.6, 1)),
                )
            )
        if hazard is not None and player is not None:
            _, bumper_gap, lateral_offset = actor_distances(player, hazard["actor"])
            rows.extend(
                [
                    (
                        "Hazard",
                        "{} ({})".format(
                            hazard["role"],
                            "yes" if hazard["hazard"] else "no",
                        ),
                    ),
                    ("Bumper gap", "{} m".format(format_float(bumper_gap, 1))),
                    ("Hazard lateral", "{} m".format(format_float(lateral_offset, 1))),
                ]
            )
        if self.final_gap_m is not None:
            rows.append(("Final gap", "{} m".format(format_float(self.final_gap_m, 1))))
        return rows

    def _select_scenario(self, scenario_id):
        scenarios = self.scenario_config.get("scenarios", [])
        for scenario in scenarios:
            if scenario.get("id") == scenario_id:
                if not self._scenario_supports_control_mode(scenario):
                    raise ValueError(
                        "Scenario {} không hỗ trợ control-mode {}".format(
                            scenario_id,
                            self.control_mode,
                        )
                    )
                return scenario
        raise ValueError("Không tìm thấy scenario: {}".format(scenario_id))

    def _scenario_supports_control_mode(self, scenario):
        control_modes = scenario.get("control_modes")
        if not control_modes:
            return True
        return self.control_mode in [str(mode) for mode in control_modes]

    def _reset_ego(self, ego, carla_map):
        spawn_index = int(
            self.scenario.get(
                "spawn_index",
                self.runner_config.get("spawn_index", 18),
            )
        )
        spawn_points = carla_map.get_spawn_points()
        if spawn_index < 0 or spawn_index >= len(spawn_points):
            raise ValueError("spawn_index không hợp lệ: {}".format(spawn_index))
        ego.set_autopilot(False)
        ego.set_transform(raised_transform(spawn_points[spawn_index]))
        ego.set_target_velocity(carla.Vector3D())
        ego.set_target_angular_velocity(carla.Vector3D())
        ego.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))

    def _set_initial_speeds(self, ego):
        self._set_vehicle_speed(ego, kph_to_mps(self.scenario.get("ego_speed_kph", 0.0)))
        for entry in self.scenario_actors:
            self._set_vehicle_speed(
                entry["actor"],
                kph_to_mps(entry["spec"].get("speed_kph", 0.0)),
            )

    def _set_vehicle_speed(self, vehicle, speed_mps):
        direction = vehicle.get_transform().get_forward_vector()
        vehicle.set_target_velocity(scale_vector(direction, speed_mps))
        vehicle.apply_control(
            carla.VehicleControl(throttle=0.0, steer=0.0, brake=0.0, hand_brake=False)
        )

    def _print_initial_distances(self, ego):
        for entry in self.scenario_actors:
            _, bumper_gap, lateral_offset = actor_distances(ego, entry["actor"])
            print(
                "  initial bumper_gap={}m lateral={}m".format(
                    format_float(bumper_gap, 1),
                    format_float(lateral_offset, 1),
                )
            )

    def _spawn_scenario_actors(self, ego, carla_map):
        scenario_type = self.scenario.get("type")
        if scenario_type == "clear_road":
            return []

        ego_waypoint = carla_map.get_waypoint(
            ego.get_location(),
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )
        if ego_waypoint is None:
            raise RuntimeError("Không tìm được waypoint cho ego")

        actor_specs = self.scenario.get("actors")
        if not actor_specs:
            actor_specs = [legacy_target_spec(self.scenario)]
        entries = []
        for index, raw_spec in enumerate(actor_specs):
            spec = dict(raw_spec)
            role = str(spec.get("role", "target_{:02d}".format(index + 1)))
            entries.append(
                self._spawn_scenario_actor(
                    ego,
                    ego_waypoint,
                    carla_map,
                    spec,
                    role,
                )
            )
        return entries

    def _spawn_scenario_actor(self, ego, ego_waypoint, carla_map, spec, role):
        initial_gap_m = float(spec.get("initial_gap_m", 25.0))
        blueprint = ego.get_world().get_blueprint_library().find(
            spec.get(
                "blueprint",
                self.runner_config.get("target_blueprint", "vehicle.audi.tt"),
            )
        )
        if blueprint.has_attribute("role_name"):
            blueprint.set_attribute("role_name", "aeb_scenario_{}".format(role))
        if blueprint.has_attribute("color"):
            blueprint.set_attribute("color", "255,0,0")

        provisional_waypoint = first_waypoint_ahead(ego_waypoint, initial_gap_m + 6.0)
        target = ego.get_world().try_spawn_actor(
            blueprint,
            raised_transform(provisional_waypoint.transform),
        )
        if target is None:
            raise RuntimeError("Không spawn được xe mục tiêu cho scenario")

        center_distance_m = (
            initial_gap_m
            + float(ego.bounding_box.extent.x)
            + float(target.bounding_box.extent.x)
        )
        target_waypoint = first_waypoint_ahead(ego_waypoint, center_distance_m)
        spawn_lane = str(spec.get("spawn_lane", "ego")).lower()
        if spawn_lane in ("left", "right"):
            target_waypoint = adjacent_driving_waypoint(target_waypoint, spawn_lane)
        target.set_transform(raised_transform(target_waypoint.transform))
        target.set_target_velocity(carla.Vector3D())
        target.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
        print(
            "Spawned scenario actor role={} hazard={} initial_gap={}m id={}".format(
                role,
                as_bool(spec.get("hazard", False)),
                format_float(initial_gap_m, 1),
                target.id,
            )
        )

        lane_change = spec.get("lane_change") or {}
        target_lane_id = None
        if lane_change:
            destination_waypoint = adjacent_driving_waypoint(
                target_waypoint,
                lane_change.get("direction", "left"),
            )
            target_lane_id = destination_waypoint.lane_id
        return {
            "actor": target,
            "role": role,
            "hazard": as_bool(spec.get("hazard", False)),
            "spec": spec,
            "initial_lane_id": target_waypoint.lane_id,
            "target_lane_id": target_lane_id,
            "lane_change_completed_s": None,
        }

    def _apply_scenario_actor_controls(self, elapsed_s):
        for entry in self.scenario_actors:
            self._apply_scenario_actor_control(entry, elapsed_s)

    def _apply_scenario_actor_control(self, entry, elapsed_s):
        actor = entry["actor"]
        spec = entry["spec"]
        motion = str(spec.get("motion", "moving"))
        if motion == "stationary":
            actor.apply_control(
                carla.VehicleControl(throttle=0.0, brake=1.0, hand_brake=True)
            )
            return
        brake_event = spec.get("brake_event") or {}
        if brake_event and elapsed_s >= float(brake_event.get("start_s", 1.5)):
            actor.apply_control(
                carla.VehicleControl(
                    throttle=0.0,
                    brake=float(brake_event.get("brake", 1.0)),
                )
            )
            return

        target_speed_mps = kph_to_mps(spec.get("speed_kph", 0.0))
        steer = self._scenario_actor_steer(entry, elapsed_s)
        if self.control_mode == "physics":
            self._apply_speed_control(actor, target_speed_mps, steer)
            return
        direction = actor.get_transform().get_forward_vector()
        actor.set_target_velocity(scale_vector(direction, target_speed_mps))
        actor.apply_control(carla.VehicleControl(throttle=0.0, steer=steer, brake=0.0))

    def _map(self):
        # Cache map: world.get_map() trong CARLA 0.9.11 dựng lại map từ OpenDRIVE
        # mỗi lần gọi nên rất nặng; không gọi lại mỗi frame.
        if self._carla_map is None:
            player = self.manual_world.player
            if player is not None:
                self._carla_map = player.get_world().get_map()
        return self._carla_map

    def _scenario_actor_steer(self, entry, elapsed_s):
        lane_change = entry["spec"].get("lane_change") or {}
        carla_map = self._map()
        if lane_change and elapsed_s >= float(lane_change.get("start_s", 1.0)):
            target_lane_id = entry.get("target_lane_id")
            waypoint = carla_map.get_waypoint(
                entry["actor"].get_location(),
                project_to_road=True,
                lane_type=carla.LaneType.Driving,
            )
            if waypoint is not None and waypoint.lane_id == target_lane_id:
                if entry["lane_change_completed_s"] is None:
                    entry["lane_change_completed_s"] = elapsed_s
            else:
                return self._lane_change_steer(
                    entry["actor"],
                    lane_change.get("direction", "left"),
                    lane_change,
                )
        actor_scenario = dict(self.scenario)
        actor_scenario["lane_follow"] = as_bool(
            entry["spec"].get(
                "lane_follow",
                self.scenario.get("lane_follow", False),
            )
        )
        return self._lane_follow_steer(entry["actor"], actor_scenario)

    def _lane_change_steer(self, vehicle, direction, config):
        carla_map = self._map()
        waypoint = carla_map.get_waypoint(
            vehicle.get_location(),
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )
        if waypoint is None:
            return 0.0
        destination = adjacent_driving_waypoint(waypoint, direction)
        target_waypoint = first_waypoint_ahead(
            destination,
            float(config.get("lookahead_m", 14.0)),
        )
        return self._steer_towards_location(
            vehicle,
            target_waypoint.transform.location,
            float(config.get("gain", 1.35)),
            float(config.get("full_steer_angle_deg", 35.0)),
        )

    def _maintain_ego_speed(self, ego, target_speed_mps, scenario):
        steer = self._lane_follow_steer(ego, scenario)
        if self.control_mode == "physics":
            self._apply_speed_control(ego, target_speed_mps, steer)
            return
        direction = ego.get_transform().get_forward_vector()
        ego.set_target_velocity(scale_vector(direction, target_speed_mps))
        ego.apply_control(carla.VehicleControl(throttle=0.0, steer=steer, brake=0.0))

    def _apply_speed_control(self, vehicle, target_speed_mps, steer=0.0):
        if self._physics_velocity_lock_enabled() and float(target_speed_mps) > 0.0:
            direction = vehicle.get_transform().get_forward_vector()
            vehicle.set_target_velocity(scale_vector(direction, target_speed_mps))
        speed_error = float(target_speed_mps) - vehicle_speed_mps(vehicle)
        kp = float(self.runner_config.get("physics_speed_kp", 0.35))
        ki = float(self.runner_config.get("physics_speed_ki", 0.0))
        fixed_delta_seconds = float(
            self.runner_config.get("fixed_delta_seconds", 0.05)
        )
        integral_limit = float(
            self.runner_config.get("physics_speed_integral_limit", 3.0)
        )
        vehicle_id = getattr(vehicle, "id", id(vehicle))
        integral = self.speed_control_integral.get(vehicle_id, 0.0)
        integral = clamp(
            integral + speed_error * fixed_delta_seconds,
            -integral_limit,
            integral_limit,
        )
        self.speed_control_integral[vehicle_id] = integral
        feedforward = float(self.runner_config.get("physics_throttle_feedforward", 0.18))
        feedforward += float(
            self.runner_config.get("physics_throttle_per_mps", 0.0)
        ) * float(target_speed_mps)
        throttle_limit = float(self.runner_config.get("physics_throttle_limit", 0.70))
        brake_limit = float(self.runner_config.get("physics_brake_limit", 0.40))
        speed_deadband = max(
            0.0,
            float(self.runner_config.get("physics_speed_deadband_mps", 0.0)),
        )
        if speed_error >= -speed_deadband:
            throttle = clamp(feedforward + kp * speed_error + ki * integral, 0.0, throttle_limit)
            brake = 0.0
        else:
            throttle = 0.0
            brake = clamp(
                kp * (-speed_error - speed_deadband) - ki * integral,
                0.0,
                brake_limit,
            )
        vehicle.apply_control(
            carla.VehicleControl(throttle=throttle, steer=steer, brake=brake)
        )

    def _physics_velocity_lock_enabled(self):
        return as_bool(self.runner_config.get("physics_velocity_lock", True))

    def _lane_follow_steer(self, vehicle, scenario):
        if not as_bool(scenario.get("lane_follow", False)):
            return 0.0
        carla_map = self._map()
        waypoint = carla_map.get_waypoint(
            vehicle.get_location(),
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )
        if waypoint is None:
            return 0.0
        speed_mps = vehicle_speed_mps(vehicle)
        lookahead_m = clamp(
            float(scenario.get("lane_follow_min_lookahead_m", 8.0))
            + speed_mps * float(scenario.get("lane_follow_speed_lookahead_s", 0.35)),
            8.0,
            float(scenario.get("lane_follow_max_lookahead_m", 20.0)),
        )
        try:
            target_waypoint = first_waypoint_ahead(waypoint, lookahead_m)
        except RuntimeError:
            return 0.0
        return self._steer_towards_location(
            vehicle,
            target_waypoint.transform.location,
            float(scenario.get("lane_follow_gain", 1.25)),
            float(scenario.get("lane_follow_full_steer_angle_deg", 35.0)),
        )

    def _steer_towards_location(
        self,
        vehicle,
        target_location,
        gain=1.25,
        full_steer_angle_deg=35.0,
    ):
        vehicle_transform = vehicle.get_transform()
        vehicle_location = vehicle_transform.location
        delta_x = target_location.x - vehicle_location.x
        delta_y = target_location.y - vehicle_location.y
        forward = vehicle_transform.get_forward_vector()
        right_x = -forward.y
        right_y = forward.x
        local_forward = delta_x * forward.x + delta_y * forward.y
        local_right = delta_x * right_x + delta_y * right_y
        heading_error = math.atan2(local_right, max(0.1, local_forward))
        steer_angle = math.radians(float(full_steer_angle_deg))
        return clamp(float(gain) * heading_error / max(0.1, steer_angle), -1.0, 1.0)


class BrakeRadarPanel(RadarBirdEyePanel):
    """Radar bird-eye panel plus radar-only AEB brake override."""

    def __init__(self, manual_world, config, panel_width, panel_height, gamma, args):
        super(BrakeRadarPanel, self).__init__(
            manual_world,
            config,
            panel_width,
            panel_height,
            gamma,
            args,
        )
        player = self.manual_world.player
        carla_map = player.get_world().get_map() if player is not None else None
        self.pipeline = RadarAEBPipeline(player, config, carla_map)
        self.aeb_config = self.pipeline.aeb_config
        self.aeb = self.pipeline.aeb
        self.controller = None
        self.decision = self.pipeline.decision
        self.aeb_override_active = False
        self.restore_autopilot_after_brake = False
        self.last_control = None
        self.cluster_config = self.pipeline.cluster_config
        self.scenario_runtime = LiveScenarioRuntime(manual_world, args)
        self.warning_icon_font = pygame.font.Font(
            pygame.font.get_default_font(),
            52,
        )
        self.warning_icon_font.set_bold(True)
        self._sync_pipeline_state()

    def set_controller(self, controller):
        self.controller = controller
        if self.scenario_runtime.enabled:
            controller._autopilot_enabled = True
            player = self.manual_world.player
            if player is not None:
                player.set_autopilot(False)

    def tick(self):
        super(BrakeRadarPanel, self).tick()
        scenario_was_started = self.scenario_runtime.started
        # Phương án A: chỉ ngừng đạp ga khi AEB THẬT SỰ phanh (BRAKE/override),
        # còn ở WARNING vẫn giữ tốc độ mục tiêu như xe thật (cảnh báo nhưng chưa
        # can thiệp). Lúc phanh, ga bị cắt và phanh ăn cùng lúc qua brake override.
        aeb_braking = self.aeb_override_active or self.decision.state == AEBState.BRAKE
        self.scenario_runtime.tick(aeb_braking)
        if self.scenario_runtime.started and not scenario_was_started:
            self.pipeline.reset()
        player = self.manual_world.player
        self.pipeline.set_ego(player)
        frame = self.pipeline.update(self.radar)
        self.decision = frame.decision
        self._sync_pipeline_state()
        self._apply_brake_decision()
        if self.scenario_runtime.should_exit():
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def render(self, display):
        super(BrakeRadarPanel, self).render(display)
        self._draw_scenario_info(display)
        self._draw_warning_icon(display)

    def _draw_warning_icon(self, display):
        if (
            self.scenario_runtime is not None
            and self.scenario_runtime.ego_stop_latched
            and self.scenario_runtime.stopped_at is not None
        ):
            return
        if self.decision.state == AEBState.WARNING:
            fill_color = (255, 196, 35)
            border_color = (255, 232, 150)
            text_color = (25, 25, 20)
        elif self.decision.state == AEBState.BRAKE:
            fill_color = (220, 48, 48)
            border_color = (255, 210, 210)
            text_color = (255, 255, 255)
        else:
            return

        center = (
            self.panel_width * 2 - 58,
            58,
        )
        pygame.draw.circle(display, (8, 10, 12), center, 38)
        pygame.draw.circle(display, fill_color, center, 33)
        pygame.draw.circle(display, border_color, center, 33, 3)
        icon = self.warning_icon_font.render("!", True, text_color)
        display.blit(icon, icon.get_rect(center=(center[0], center[1] - 1)))

    def _draw_scenario_info(self, display):
        if not self.scenario_runtime.enabled:
            return
        rows = self.scenario_runtime.summary_rows()
        if not rows:
            return
        self._draw_info_card(
            display,
            self.panel_width + 16,
            max(48, self.panel_height - 238),
            360,
            "LIVE SCENARIO",
            rows,
        )

    def _sync_pipeline_state(self):
        self.tracked_clusters = self.pipeline.tracked_clusters
        self.predicted_path = self.pipeline.predicted_path
        self.path_curvature_1pm = self.pipeline.path_curvature_1pm
        self.path_horizon_m = self.pipeline.path_horizon_m

    def _selected_target(self):
        return self.pipeline.selected_target

    def _valid_path_target(self, point):
        return self.pipeline.valid_path_target(point)

    def _is_ground_point(self, point):
        return self.pipeline.is_ground_point(point)

    def _height_above_road(self, point):
        return self.pipeline.height_above_road(point)

    def _brake_lateral_limit(self):
        return self.pipeline.brake_lateral_limit()

    def _point_color(self, point):
        if self._is_ground_point(point):
            return 130, 135, 140
        return super(BrakeRadarPanel, self)._point_color(point)

    def _color_legend_rows(self):
        rows = super(BrakeRadarPanel, self)._color_legend_rows()
        return rows[:-1] + [
            ((130, 135, 140), "ground: ignored by AEB"),
            ((255, 190, 70), "ring: cluster not confirmed"),
            ((235, 245, 245), "filled center: confirmed cluster"),
            rows[-1],
        ]

    def _draw_radar_points(self, display, panel_x):
        super(BrakeRadarPanel, self)._draw_radar_points(display, panel_x)
        range_m = float(self.radar_config.get("range", 100.0))
        horizontal_fov = float(self.radar_config.get("horizontal_fov", 30.0))
        scale = self._scale(range_m, horizontal_fov)
        target = self._selected_target()

        for cluster in self.tracked_clusters:
            screen = self._to_screen(
                panel_x,
                cluster.x_forward_m,
                cluster.y_right_m,
                scale,
            )
            if cluster.confirmed:
                color = self._ttc_color(cluster)
                radius = 9 if cluster is target else 6
                pygame.draw.circle(display, color, screen, radius)
                pygame.draw.circle(display, (235, 245, 245), screen, radius + 2, 1)
            else:
                pygame.draw.circle(display, (255, 190, 70), screen, 7, 2)
            if cluster is target:
                pygame.draw.circle(display, (255, 255, 255), screen, 13, 2)

    def _draw_grid(self, display, panel_x):
        super(BrakeRadarPanel, self)._draw_grid(display, panel_x)
        range_m = float(self.radar_config.get("range", 100.0))
        horizontal_fov = float(self.radar_config.get("horizontal_fov", 30.0))
        scale = self._scale(range_m, horizontal_fov)
        corridor_half_width = self._brake_lateral_limit()
        left_boundary = []
        right_boundary = []
        centerline = []
        for x_forward, y_right, heading_rad in self.predicted_path:
            normal_x = -math.sin(heading_rad)
            normal_y = math.cos(heading_rad)
            left_boundary.append(
                self._to_screen(
                    panel_x,
                    x_forward - corridor_half_width * normal_x,
                    y_right - corridor_half_width * normal_y,
                    scale,
                )
            )
            right_boundary.append(
                self._to_screen(
                    panel_x,
                    x_forward + corridor_half_width * normal_x,
                    y_right + corridor_half_width * normal_y,
                    scale,
                )
            )
            centerline.append(self._to_screen(panel_x, x_forward, y_right, scale))

        if len(left_boundary) > 1:
            pygame.draw.lines(display, (255, 210, 70), False, left_boundary, 2)
            pygame.draw.lines(display, (255, 210, 70), False, right_boundary, 2)
            pygame.draw.lines(display, (150, 128, 55), False, centerline, 1)

    def _distance_to_predicted_path(self, point):
        return self.pipeline.distance_to_predicted_path(point)

    def _path_description(self):
        return self.pipeline.path_description()

    def _apply_brake_decision(self):
        player = self.manual_world.player
        if player is None:
            return

        if self.decision.state == AEBState.BRAKE:
            if not self.aeb_override_active:
                self.restore_autopilot_after_brake = self._controller_autopilot_enabled()
                if self.restore_autopilot_after_brake:
                    player.set_autopilot(False)
                self.aeb_override_active = True
            self.scenario_runtime.latch_ego_stop(self.decision.reason)
            if (
                self.scenario_runtime.ego_stop_latched
                and self.scenario_runtime.stopped_at is not None
            ):
                # Khi scenario đã chốt xe dừng, không để decision BRAKE tiếp tục
                # ghi đè full brake mỗi tick. Runtime sẽ giữ xe bằng handbrake
                # sau release_hold_s để video/demo có trạng thái dừng rõ ràng.
                self.scenario_runtime._hold_ego_stopped(player)
                return
            self.last_control = apply_brake_override(player, self.decision)
            return

        if self.aeb_override_active:
            if self.scenario_runtime.ego_stop_latched:
                # Stop latch giữ ego dừng và đã áp full brake mỗi tick. Không để
                # nhánh nhả phanh của AEB ghi đè lệnh giữ phanh, tránh xe trôi tới
                # rồi phanh lại khi AEB chớp tắt lúc gần dừng.
                return
            self.last_control = apply_brake_override(player, self.decision)
            if self.restore_autopilot_after_brake and self._controller_autopilot_enabled():
                player.set_autopilot(True)
            self.aeb_override_active = False
            self.restore_autopilot_after_brake = False

    def _controller_autopilot_enabled(self):
        return bool(getattr(self.controller, "_autopilot_enabled", False))

    def _draw_info(self, display, panel_x):
        if self.radar is None:
            self._draw_info_card(
                display,
                panel_x + 16,
                48,
                360,
                "AEB BRAKE",
                [("Status", "waiting")],
            )
            self._draw_color_legend(display, panel_x)
            return

        x = panel_x + 16
        width = 360
        next_y = self._draw_info_card(
            display,
            x,
            48,
            width,
            "AEB BRAKE",
            [
                ("Radar points", len(self.radar.points)),
                (
                    "Path candidates",
                    sum(
                        1
                        for point in self.radar.points
                        if self._valid_path_target(point)
                    ),
                ),
                (
                    "Ground ignored",
                    sum(1 for point in self.radar.points if self._is_ground_point(point)),
                ),
                ("Clusters", len(self.tracked_clusters)),
                (
                    "Confirmed",
                    sum(1 for cluster in self.tracked_clusters if cluster.confirmed),
                ),
                ("State", self.decision.state.value),
                ("Brake cmd", "{:.2f}".format(self.decision.brake)),
                ("Override", "ON" if self.aeb_override_active else "OFF"),
                (
                    "Path",
                    "{} +/-{}m".format(
                        self._path_description(),
                        format_float(self._brake_lateral_limit(), 2),
                    ),
                ),
                ("Path horizon", "{} m".format(format_float(self.path_horizon_m, 1))),
                ("Warn TTC", "{} s".format(format_float(self.aeb_config.warning_ttc_s, 1))),
                ("Brake TTC", "{} s".format(format_float(self.aeb_config.brake_ttc_s, 1))),
                ("Release TTC", "{} s".format(format_float(self.aeb_config.release_ttc_s, 1))),
                (
                    "Required dist",
                    "{} m".format(
                        format_float(self.decision.required_distance_m, 1)
                    ),
                ),
                (
                    "Distance margin",
                    "{} m".format(
                        format_float(self.decision.distance_margin_m, 1)
                    ),
                ),
                ("Reason", self._short_reason(self.decision.reason)),
            ],
        )

        target = self._selected_target()
        if target is None:
            target_rows = [("Target", "--"), ("TTC", "inf")]
        else:
            ttc = compute_ttc(target.x_forward_m, target.relative_velocity_mps)
            road_height = target.max_height_above_road_m
            target_rows = [
                ("Target", self._ttc_label(ttc)),
                ("Track ID", target.track_id),
                ("Cluster points", target.point_count),
                (
                    "Confirmation",
                    "{}/{}".format(
                        target.hit_streak,
                        self.cluster_config.confirm_frames,
                    ),
                ),
                ("Missed frames", target.missed_frames),
                ("Distance", "{} m".format(format_float(target.x_forward_m, 1))),
                ("Lateral", "{} m".format(format_float(target.y_right_m, 1))),
                ("Road height", "{} m".format(format_float(road_height, 2))),
                ("Rel v", "{} m/s".format(format_float(target.relative_velocity_mps, 1))),
                ("TTC", "{} s".format(format_float(ttc, 2))),
            ]
        target_x = x + width + 12
        target_y = 48
        if target_x + width > panel_x + self.panel_width - 16:
            target_x = x
            target_y = next_y + 10
        self._draw_info_card(
            display,
            target_x,
            target_y,
            width,
            "TARGET",
            target_rows,
        )
        self._draw_color_legend(display, panel_x)

    def destroy(self):
        runtime = getattr(self, "scenario_runtime", None)
        if runtime is not None:
            runtime.destroy()
        pipeline = getattr(self, "pipeline", None)
        if pipeline is not None:
            pipeline.reset()
        super(BrakeRadarPanel, self).destroy()

    def _short_reason(self, reason):
        labels = {
            "no_valid_closing_target": "no closing target",
            "ttc_below_brake_threshold": "TTC brake",
            "ttc_below_warning_threshold": "TTC warning",
            "ttc_recovered": "TTC recovered",
            "normal": "normal",
            "reverse_gear_aeb_disabled": "reverse disabled",
            "static_obstacle_distance_fallback": "static fallback",
            "brake_held_until_stopped": "hold until stopped",
            "distance_below_stopping_threshold": "stopping distance",
            "distance_and_ttc_brake": "TTC + stopping dist",
        }
        return labels.get(reason, reason)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    parser.add_argument(
        "--scenario-config",
        type=Path,
        default=DEFAULT_SCENARIO_CONFIG,
        help="File YAML chứa các radar-only scenario để chạy trong UI.",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="ID scenario cần chạy trực tiếp trong UI, ví dụ ccrs_65.",
    )
    parser.add_argument(
        "--control-mode",
        choices=("deterministic", "physics"),
        default=None,
        help="deterministic dùng set_target_velocity; physics dùng throttle/brake.",
    )
    parser.add_argument(
        "--scenario-camera",
        choices=("wide_chase", "high_chase", "manual"),
        default="wide_chase",
        help=(
            "Camera bên trái khi chạy scenario: wide_chase dễ quan sát, "
            "high_chase nhìn xa hơn, manual giữ nguyên camera manual_control."
        ),
    )
    parser.add_argument(
        "--keep-driving-after-aeb",
        action="store_true",
        help=(
            "Giữ hành vi cũ: sau khi AEB nhả phanh, scenario controller tiếp tục "
            "bám tốc độ mục tiêu."
        ),
    )
    parser.add_argument(
        "--scenario-debug-interval-s",
        type=float,
        default=0.10,
        help="Chu kỳ vẽ debug line/label của live scenario; 0 là vẽ mỗi frame.",
    )
    parser.add_argument(
        "--scenario-warmup-s",
        type=float,
        default=1.0,
        help=(
            "Thời gian chờ sau khi spawn xe/đổi camera trước khi bắt đầu cho "
            "ego chạy và tính thời gian scenario."
        ),
    )
    parser.add_argument(
        "--scenario-autoexit-s",
        type=float,
        default=0.0,
        help=(
            "Nếu > 0: tự thoát UI sau khi scenario hoàn tất và nán lại số giây "
            "này (phục vụ quay video tự động). 0 = không tự thoát."
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        run_two_panel(
            args,
            BrakeRadarPanel,
            "AEB radar-only brake test - manual_control extended",
        )
    except KeyboardInterrupt:
        print("\nĐã dừng bởi người dùng.")


if __name__ == "__main__":
    main()
