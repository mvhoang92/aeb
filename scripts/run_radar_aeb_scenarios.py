#!/usr/bin/env python

"""Run deterministic radar-only AEB scenarios and write tick-level logs."""

from __future__ import print_function

import argparse
import json
import math
import platform
import random
import shlex
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from control.brake import AEBState, BinaryBrakeConfig, apply_brake_override, as_bool
from core.radar_aeb_pipeline import RadarAEBPipeline
from evaluation.artifact_io import (
    git_state,
    resolve_project_path,
    sha256_file,
    write_csv,
)
from evaluation.evidence import (
    nearest_frame_path,
    select_evidence_events,
)
from evaluation.metrics import (
    add_motion_metrics,
    aggregate_summaries,
    format_number,
    max_value,
    numeric_values,
    optional_round,
    summarize_scenario,
)
from evaluation.schemas import SUMMARY_FIELDS, TICK_FIELDS
from ui.manual_control_common import RadarPoint, RadarSensor, carla, load_yaml


DEFAULT_SENSOR_CONFIG = AEB_ROOT / "configs" / "sensors.yaml"
DEFAULT_SCENARIO_CONFIG = (
    AEB_ROOT / "configs" / "scenarios" / "suites" / "smoke_basic.yaml"
)
DEFAULT_LOG_ROOT = AEB_ROOT / "logs"


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

    def reset_control_state(self):
        self.pipeline.reset_control_state()
        self.decision = self.pipeline.decision
        self.aeb_override_active = False

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


class ScenarioEvidenceRecorder(object):
    """Record a chase-camera video and event screenshots for one scenario."""

    def __init__(
        self,
        world,
        vehicle,
        run_directory,
        scenario_id,
        run_index,
        repeat,
        fixed_delta_seconds,
    ):
        suffix = "_run_{:02d}".format(run_index) if repeat > 1 else ""
        self.name = "{}{}".format(scenario_id, suffix)
        self.output_directory = Path(run_directory) / "evidence" / self.name
        self.frames_directory = self.output_directory / "frames"
        self.frames_directory.mkdir(parents=True, exist_ok=False)
        self.video_path = self.output_directory / "{}.mp4".format(self.name)
        self.events_path = self.output_directory / "events.json"
        self._callback_error = None
        self._lock = threading.Lock()
        self.saved_frames = {}
        self.latest_frame = None

        blueprint = world.get_blueprint_library().find("sensor.camera.rgb")
        blueprint.set_attribute("image_size_x", "960")
        blueprint.set_attribute("image_size_y", "540")
        blueprint.set_attribute("fov", "90")
        camera_tick = float(fixed_delta_seconds)
        blueprint.set_attribute("sensor_tick", str(camera_tick))
        self.frame_rate = 1.0 / camera_tick
        transform = carla.Transform(
            carla.Location(x=-8.0, y=0.0, z=2.8),
            carla.Rotation(pitch=-5.0),
        )
        attachment_type = getattr(carla.AttachmentType, "SpringArm", None)
        spawn_kwargs = {"attach_to": vehicle}
        if attachment_type is not None:
            spawn_kwargs["attachment_type"] = attachment_type
        self.sensor = world.spawn_actor(blueprint, transform, **spawn_kwargs)
        self.sensor.listen(self._save_frame)

    def _save_frame(self, image):
        path = self.frames_directory / "{:08d}.png".format(image.frame)
        try:
            image.save_to_disk(str(path))
            with self._lock:
                self.saved_frames[int(image.frame)] = path
                self.latest_frame = int(image.frame)
        except Exception as exc:  # pylint: disable=broad-except
            self._callback_error = str(exc)

    def wait_for_frame(self, world_frame, timeout_s=2.0):
        deadline = time.monotonic() + float(timeout_s)
        while time.monotonic() < deadline:
            with self._lock:
                latest_frame = self.latest_frame
            if latest_frame is not None and latest_frame >= int(world_frame):
                return True
            if self._callback_error is not None:
                return False
            time.sleep(0.001)
        return False

    def finalize(self, rows, keep_frames=False, include_minimum_gap=True):
        self.destroy()
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if any(self.frames_directory.glob("*.png")):
                break
            time.sleep(0.02)

        frame_paths = sorted(self.frames_directory.glob("*.png"))
        event_records = []
        for event in select_evidence_events(
            rows,
            include_minimum_gap=include_minimum_gap,
        ):
            source = nearest_frame_path(frame_paths, int(event["frame"]))
            record = dict(event)
            record["image"] = None
            if source is not None:
                destination = self.output_directory / "{}.png".format(event["name"])
                shutil.copyfile(str(source), str(destination))
                record["image"] = destination.name
            event_records.append(record)

        video_created = self._encode_video() if frame_paths else False
        payload = {
            "scenario": self.name,
            "camera": {
                "view": "third_person_chase",
                "resolution": [960, 540],
                "frame_rate": round(self.frame_rate, 3),
            },
            "video": self.video_path.name if video_created else None,
            "callback_error": self._callback_error,
            "events": event_records,
        }
        with open(str(self.events_path), "w") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)

        if video_created and not keep_frames:
            shutil.rmtree(str(self.frames_directory))
        evidence_root = self.output_directory.parent.parent
        return {
            "video": (
                str(self.video_path.relative_to(evidence_root))
                if video_created
                else None
            ),
            "events": str(self.events_path.relative_to(evidence_root)),
        }

    def _encode_video(self):
        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-framerate",
            "{:.3f}".format(self.frame_rate),
            "-pattern_type",
            "glob",
            "-i",
            str(self.frames_directory / "*.png"),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "22",
            "-pix_fmt",
            "yuv420p",
            str(self.video_path),
        ]
        try:
            subprocess.run(command, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            self._callback_error = "{}; ffmpeg: {}".format(
                self._callback_error or "",
                exc,
            ).strip("; ")
            return False
        return self.video_path.exists() and self.video_path.stat().st_size > 0

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
        self.seed = int(getattr(args, "seed", 2026))
        random.seed(self.seed)
        try:
            import numpy as np  # pylint: disable=import-outside-toplevel

            np.random.seed(self.seed)
        except ImportError:
            pass
        self.client = carla.Client(args.host, args.port)
        self.client.set_timeout(args.timeout)
        self.world = self.client.get_world()
        self.original_settings = self.world.get_settings()
        self.carla_map = self.world.get_map()
        self.managed_actors = []
        self.speed_control_integral = {}

    def run(self):
        self._ensure_map()
        self._enable_synchronous_mode()
        run_directory = self._create_run_directory()
        summaries = self._load_resume_summaries(run_directory)
        completed_jobs = {
            (str(summary["scenario_id"]), int(summary.get("run_index", 1)))
            for summary in summaries
        }
        try:
            scenarios = self._selected_scenarios()
            all_jobs = [
                (scenario, run_index)
                for scenario in scenarios
                for run_index in range(1, self.args.repeat + 1)
            ]
            jobs = [
                (scenario, run_index)
                for scenario, run_index in all_jobs
                if (str(scenario["id"]), int(run_index)) not in completed_jobs
            ]
            if completed_jobs:
                print(
                    "Resume: bỏ qua {}/{} scenario-runs đã hoàn thành".format(
                        len(all_jobs) - len(jobs),
                        len(all_jobs),
                    )
                )
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
                self._write_summary(run_directory, summaries)
                self._write_aggregate_summary(run_directory, summaries)
                self._write_metadata(run_directory, summaries)
                print(
                    "  {} | brake={} collision={} min_gap={}m log={}".format(
                        summary["status"],
                        summary["brake_activated"],
                        summary["collision"],
                        format_number(summary["minimum_bumper_gap_m"], 2),
                        summary["log_file"],
                    )
                )
                self._stabilize_between_scenarios(index, len(jobs))
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

    def _stabilize_between_scenarios(self, index, total):
        if index >= total:
            return
        self._destroy_managed_actors()
        self._destroy_stale_aeb_actors()
        cooldown_s = max(0.0, float(getattr(self.args, "scenario_cooldown_s", 0.0)))
        if cooldown_s > 0.0:
            fixed_dt = float(self.runner_config.get("fixed_delta_seconds", 0.05))
            ticks = max(1, int(round(cooldown_s / max(fixed_dt, 0.001))))
            for _ in range(ticks):
                self.world.tick()

        reload_every = int(getattr(self.args, "reload_world_every", 0) or 0)
        if reload_every > 0 and index % reload_every == 0:
            print("  Reload world để giảm rủi ro crash CARLA sau {} scenario".format(index))
            self.world.apply_settings(self.original_settings)
            self.world = self.client.reload_world() or self.client.get_world()
            wait_s = max(0.0, float(getattr(self.args, "reload_world_wait_s", 2.0)))
            if wait_s > 0.0:
                time.sleep(wait_s)
            self.carla_map = self.world.get_map()
            self.original_settings = self.world.get_settings()
            self._enable_synchronous_mode()
            self._destroy_stale_aeb_actors()

    def _create_run_directory(self):
        run_id = self.args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        run_directory = Path(self.args.log_root) / run_id
        resume = bool(getattr(self.args, "resume", False))
        if run_directory.exists():
            if not resume:
                raise FileExistsError(
                    "Run directory đã tồn tại: {}. Dùng --resume để tiếp tục.".format(
                        run_directory
                    )
                )
            self._validate_resume_configs(run_directory)
            return run_directory

        run_directory.mkdir(parents=True, exist_ok=False)
        config_directory = run_directory / "config_snapshot"
        config_directory.mkdir()
        shutil.copyfile(
            str(self.args.sensor_config),
            str(config_directory / Path(self.args.sensor_config).name),
        )
        shutil.copyfile(
            str(self.args.scenario_config),
            str(config_directory / Path(self.args.scenario_config).name),
        )
        return run_directory

    def _validate_resume_configs(self, run_directory):
        metadata_path = Path(run_directory) / "run_metadata.json"
        if metadata_path.exists():
            with open(str(metadata_path)) as stream:
                metadata = json.load(stream)
            current_commit, current_dirty = git_state(AEB_ROOT)
            recorded_commit = metadata.get("git_commit")
            if current_dirty:
                raise RuntimeError(
                    "Không thể resume evidence khi working tree đang có thay đổi."
                )
            if recorded_commit and current_commit != recorded_commit:
                raise RuntimeError(
                    "Không thể resume qua commit khác: run={} current={}".format(
                        recorded_commit,
                        current_commit,
                    )
                )

        config_directory = Path(run_directory) / "config_snapshot"
        expected = (self.args.sensor_config, self.args.scenario_config)
        for source in expected:
            snapshot = config_directory / Path(source).name
            if not snapshot.exists():
                raise RuntimeError(
                    "Không thể resume: thiếu config snapshot {}".format(snapshot)
                )
            if sha256_file(source) != sha256_file(snapshot):
                raise RuntimeError(
                    "Không thể resume vì config đã thay đổi: {}".format(source)
                )

    def _load_resume_summaries(self, run_directory):
        if not bool(getattr(self.args, "resume", False)):
            return []
        summary_path = Path(run_directory) / "summary.json"
        if not summary_path.exists():
            return []
        with open(str(summary_path)) as stream:
            summaries = json.load(stream)
        if not isinstance(summaries, list):
            raise RuntimeError("summary.json không phải một danh sách hợp lệ")
        return summaries

    def _selected_scenarios(self):
        scenarios = self.scenario_config.get("scenarios", [])
        if not self.args.scenario:
            selected = scenarios
        else:
            requested = set(self.args.scenario)
            selected = [
                scenario for scenario in scenarios if scenario["id"] in requested
            ]
            missing = requested - set(scenario["id"] for scenario in selected)
            if missing:
                raise ValueError(
                    "Không tìm thấy scenario: {}".format(
                        ", ".join(sorted(missing))
                    )
                )
        return [
            scenario
            for scenario in selected
            if self._scenario_supports_control_mode(scenario)
        ]

    def _scenario_supports_control_mode(self, scenario):
        control_modes = scenario.get("control_modes")
        if not control_modes:
            return True
        return self.args.control_mode in [str(mode) for mode in control_modes]

    def _run_scenario(self, scenario, run_directory, run_index):
        self._destroy_managed_actors()
        self._destroy_stale_aeb_actors()
        ego = self._spawn_ego(scenario)
        collision = CollisionRecorder(ego)
        system = self._make_system(ego)
        scenario_actors = []
        hazard_entry = None
        evidence = None
        rows = []
        try:
            ego_speed_mps = kph_to_mps(scenario.get("ego_speed_kph", 0.0))
            scenario_actors = self._spawn_scenario_actors(ego, scenario)
            hazard_entry = next(
                (entry for entry in scenario_actors if entry["hazard"]),
                scenario_actors[0] if scenario_actors else None,
            )
            settle_ticks = int(self.runner_config.get("settle_ticks", 4))
            for _ in range(settle_ticks):
                ego.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
                for entry in scenario_actors:
                    actor = entry["actor"]
                    if is_vehicle_actor(actor):
                        actor.apply_control(
                            carla.VehicleControl(throttle=0.0, brake=1.0)
                        )
                frame = self.world.tick()
                self._wait_for_radar(system, frame)
                system.tick()

            self._set_vehicle_speed(ego, ego_speed_mps)
            for entry in scenario_actors:
                if is_vehicle_actor(entry["actor"]):
                    self._set_vehicle_speed(
                        entry["actor"],
                        kph_to_mps(entry["spec"].get("speed_kph", 0.0)),
                    )
            self._reset_system_control_state(system)
            self.speed_control_integral = {}
            start_snapshot = self.world.get_snapshot()
            start_time_s = start_snapshot.timestamp.elapsed_seconds
            if self.args.record_evidence:
                evidence = ScenarioEvidenceRecorder(
                    self.world,
                    ego,
                    run_directory,
                    scenario["id"],
                    run_index,
                    self.args.repeat,
                    self.runner_config.get("fixed_delta_seconds", 0.05),
                )
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
                self._apply_scenario_actor_controls(
                    scenario_actors,
                    scenario,
                    elapsed_s,
                )
                if not brake_activated and not system.aeb_override_active:
                    self._maintain_ego_speed(ego, ego_speed_mps, scenario)

                frame = self.world.tick()
                self._wait_for_radar(system, frame)
                if evidence is not None:
                    evidence.wait_for_frame(frame)
                self._inject_synthetic_radar_points(system, scenario)
                system.tick()
                snapshot = self.world.get_snapshot()
                elapsed_s = snapshot.timestamp.elapsed_seconds - start_time_s
                row = self._make_tick_row(
                    scenario,
                    snapshot,
                    elapsed_s,
                    ego,
                    hazard_entry,
                    scenario_actors,
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
            summary = summarize_scenario(
                scenario,
                rows,
                log_path.name,
                run_index,
            )
            if evidence is not None:
                evidence_paths = evidence.finalize(
                    rows,
                    keep_frames=self.args.keep_evidence_frames,
                    include_minimum_gap=as_bool(
                        scenario.get("report_minimum_gap", True)
                    ),
                )
                evidence = None
                summary["evidence_video"] = evidence_paths["video"]
                summary["evidence_events"] = evidence_paths["events"]
            return summary
        finally:
            if evidence is not None:
                try:
                    evidence.destroy()
                except RuntimeError:
                    pass
            try:
                system.destroy()
            except RuntimeError:
                pass
            try:
                collision.destroy()
            except RuntimeError:
                pass
            for entry in scenario_actors:
                self._destroy_actor(entry["actor"])
            self._destroy_actor(ego)
            self.managed_actors = []
            try:
                self.world.tick()
            except RuntimeError:
                pass

    def _reset_system_control_state(self, system):
        if hasattr(system, "reset_control_state"):
            system.reset_control_state()
            return
        pipeline = getattr(system, "pipeline", None)
        if pipeline is not None and hasattr(pipeline, "reset_control_state"):
            pipeline.reset_control_state()
        if hasattr(system, "aeb_override_active"):
            system.aeb_override_active = False

    def _spawn_ego(self, scenario):
        spawn_index = int(
            scenario.get(
                "spawn_index",
                self.runner_config.get("spawn_index", 18),
            )
        )
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

    def _set_vehicle_speed(self, vehicle, speed_mps):
        direction = vehicle.get_transform().get_forward_vector()
        vehicle.set_target_velocity(scale_vector(direction, speed_mps))
        vehicle.apply_control(
            carla.VehicleControl(throttle=0.0, steer=0.0, brake=0.0, hand_brake=False)
        )

    def _spawn_scenario_actors(self, ego, scenario):
        scenario_type = scenario.get("type")
        if scenario_type == "clear_road":
            return []

        ego_waypoint = self.carla_map.get_waypoint(
            ego.get_location(),
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )
        if ego_waypoint is None:
            raise RuntimeError("Không tìm được waypoint cho ego")

        actor_specs = scenario.get("actors")
        if not actor_specs:
            actor_specs = [legacy_target_spec(scenario)]
        entries = []
        for index, raw_spec in enumerate(actor_specs):
            spec = dict(raw_spec)
            role = str(spec.get("role", "target_{:02d}".format(index + 1)))
            entry = self._spawn_scenario_actor(
                ego,
                ego_waypoint,
                scenario,
                spec,
                role,
            )
            entries.append(entry)
            self.managed_actors.append(entry["actor"])
        self.world.tick()
        return entries

    def _spawn_scenario_actor(
        self,
        ego,
        ego_waypoint,
        scenario,
        spec,
        role,
    ):
        initial_gap_m = float(spec.get("initial_gap_m", 25.0))
        target_blueprint = self.world.get_blueprint_library().find(
            spec.get(
                "blueprint",
                self.runner_config.get("target_blueprint", "vehicle.audi.tt"),
            )
        )
        if target_blueprint.has_attribute("role_name"):
            target_blueprint.set_attribute(
                "role_name",
                "aeb_scenario_{}".format(role),
            )

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
        spawn_lane = str(spec.get("spawn_lane", "ego")).lower()
        if spawn_lane in ("left", "right"):
            target_waypoint = adjacent_driving_waypoint(
                target_waypoint,
                spawn_lane,
            )
        target_transform = offset_transform(
            raised_transform(target_waypoint.transform),
            lateral_m=float(spec.get("lateral_offset_m", 0.0)),
            forward_m=float(spec.get("forward_offset_m", 0.0)),
            z_m=float(spec.get("z_offset_m", 0.0)),
            yaw_deg=float(spec.get("yaw_offset_deg", 0.0)),
        )
        target.set_transform(target_transform)
        if is_vehicle_actor(target):
            target.set_target_velocity(carla.Vector3D())
            target.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
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

    def _inject_synthetic_radar_points(self, system, scenario):
        """Append configured synthetic radar returns before AEB processing.

        This is used only by explicit stress scenarios to emulate radar false
        objects without adding a camera-visible vehicle. It helps test whether
        camera-gated fusion can suppress radar-only false braking. Real CARLA
        radar detections remain unchanged for all normal scenarios.
        """

        specs = scenario.get("synthetic_radar_points") or []
        if not specs or getattr(system, "radar", None) is None:
            return
        radar = system.radar
        if radar.frame is None:
            return

        points = list(getattr(radar, "points", []) or [])
        for spec in specs:
            points.extend(self._make_synthetic_radar_points(system, spec))
        radar.points = points

    def _make_synthetic_radar_points(self, system, spec):
        count = max(1, int(spec.get("count", 3)))
        x_forward = float(spec.get("x_forward_m", spec.get("distance_m", 18.0)))
        y_right = float(spec.get("y_right_m", 0.0))
        z_up = float(spec.get("z_up_m", 0.8))
        relative_velocity = float(spec.get("relative_velocity_mps", -20.0))
        spacing = float(spec.get("spacing_m", 0.18))
        velocity_step = float(spec.get("velocity_step_mps", 0.0))

        radar_transform = (
            system.radar.sensor.get_transform()
            if getattr(system.radar, "sensor", None) is not None
            else system.ego.get_transform()
        )
        origin = radar_transform.location
        forward = radar_transform.get_forward_vector()
        right = carla.Vector3D(x=-forward.y, y=forward.x, z=0.0)

        points = []
        for index in range(count):
            offset_index = index - 0.5 * (count - 1)
            px = x_forward + offset_index * spacing
            py = y_right + offset_index * 0.05
            pz = z_up
            world_location = carla.Location(
                x=origin.x + forward.x * px + right.x * py,
                y=origin.y + forward.y * px + right.y * py,
                z=origin.z + forward.z * px + pz,
            )
            depth = math.sqrt(px * px + py * py + pz * pz)
            azimuth = math.atan2(py, max(0.001, px))
            altitude = math.atan2(pz, max(0.001, math.hypot(px, py)))
            velocity = relative_velocity + offset_index * velocity_step
            points.append(
                RadarPoint(
                    depth_m=depth,
                    x_forward_m=px,
                    y_right_m=py,
                    z_up_m=pz,
                    relative_velocity_mps=velocity,
                    velocity_towards_sensor_mps=velocity,
                    azimuth_rad=azimuth,
                    altitude_rad=altitude,
                    world_location=world_location,
                )
            )
        return points

    def _maintain_ego_speed(self, ego, target_speed_mps, scenario):
        steer = self._lane_follow_steer(ego, scenario)
        if self.args.control_mode == "physics":
            self._apply_speed_control(ego, target_speed_mps, steer)
            return
        direction = ego.get_transform().get_forward_vector()
        ego.set_target_velocity(scale_vector(direction, target_speed_mps))
        ego.apply_control(
            carla.VehicleControl(throttle=0.0, steer=steer, brake=0.0)
        )

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
        feedforward = float(
            self.runner_config.get("physics_throttle_feedforward", 0.18)
        )
        feedforward += float(
            self.runner_config.get("physics_throttle_per_mps", 0.0)
        ) * float(target_speed_mps)
        throttle_limit = float(
            self.runner_config.get("physics_throttle_limit", 0.70)
        )
        brake_limit = float(
            self.runner_config.get("physics_brake_limit", 0.40)
        )
        speed_deadband = max(
            0.0,
            float(self.runner_config.get("physics_speed_deadband_mps", 0.0)),
        )
        if speed_error >= -speed_deadband:
            throttle = clamp(
                feedforward + kp * speed_error + ki * integral,
                0.0,
                throttle_limit,
            )
            brake = 0.0
        else:
            throttle = 0.0
            brake = clamp(
                kp * (-speed_error - speed_deadband) - ki * integral,
                0.0,
                brake_limit,
            )
        vehicle.apply_control(
            carla.VehicleControl(
                throttle=throttle,
                steer=steer,
                brake=brake,
            )
        )

    def _physics_velocity_lock_enabled(self):
        return as_bool(self.runner_config.get("physics_velocity_lock", True))

    def _apply_scenario_actor_controls(self, entries, scenario, elapsed_s):
        for entry in entries:
            self._apply_scenario_actor_control(entry, scenario, elapsed_s)

    def _apply_scenario_actor_control(self, entry, scenario, elapsed_s):
        actor = entry["actor"]
        spec = entry["spec"]
        if not is_vehicle_actor(actor):
            return
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
        steer = self._scenario_actor_steer(entry, scenario, elapsed_s)
        if self.args.control_mode == "physics":
            self._apply_speed_control(actor, target_speed_mps, steer)
            return
        direction = actor.get_transform().get_forward_vector()
        actor.set_target_velocity(scale_vector(direction, target_speed_mps))
        actor.apply_control(
            carla.VehicleControl(throttle=0.0, steer=steer, brake=0.0)
        )

    def _scenario_actor_steer(self, entry, scenario, elapsed_s):
        lane_change = entry["spec"].get("lane_change") or {}
        if lane_change and elapsed_s >= float(lane_change.get("start_s", 1.0)):
            target_lane_id = entry.get("target_lane_id")
            waypoint = self.carla_map.get_waypoint(
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
        actor_scenario = dict(scenario)
        actor_scenario["lane_follow"] = as_bool(
            entry["spec"].get(
                "lane_follow",
                scenario.get("lane_follow", False),
            )
        )
        return self._lane_follow_steer(entry["actor"], actor_scenario)

    def _lane_change_steer(self, vehicle, direction, config):
        waypoint = self.carla_map.get_waypoint(
            vehicle.get_location(),
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )
        if waypoint is None:
            return 0.0
        destination = adjacent_driving_waypoint(waypoint, direction)
        lookahead_m = float(config.get("lookahead_m", 14.0))
        target_waypoint = first_waypoint_ahead(destination, lookahead_m)
        return steer_towards_location(
            vehicle,
            target_waypoint.transform.location,
            float(config.get("gain", 1.35)),
            float(config.get("full_steer_angle_deg", 35.0)),
        )

    def _lane_follow_steer(self, vehicle, scenario):
        if not as_bool(scenario.get("lane_follow", False)):
            return 0.0
        waypoint = self.carla_map.get_waypoint(
            vehicle.get_location(),
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )
        if waypoint is None:
            return 0.0
        speed_mps = vehicle_speed_mps(vehicle)
        lookahead_m = clamp(
            float(scenario.get("lane_follow_min_lookahead_m", 8.0))
            + speed_mps
            * float(scenario.get("lane_follow_speed_lookahead_s", 0.35)),
            8.0,
            float(scenario.get("lane_follow_max_lookahead_m", 20.0)),
        )
        try:
            target_waypoint = first_waypoint_ahead(waypoint, lookahead_m)
        except RuntimeError:
            return 0.0
        vehicle_transform = vehicle.get_transform()
        vehicle_location = vehicle_transform.location
        target_location = target_waypoint.transform.location
        delta_x = target_location.x - vehicle_location.x
        delta_y = target_location.y - vehicle_location.y
        forward = vehicle_transform.get_forward_vector()
        right_x = -forward.y
        right_y = forward.x
        local_forward = delta_x * forward.x + delta_y * forward.y
        local_right = delta_x * right_x + delta_y * right_y
        heading_error = math.atan2(local_right, max(0.1, local_forward))
        steer_angle = math.radians(
            float(scenario.get("lane_follow_full_steer_angle_deg", 35.0))
        )
        gain = float(scenario.get("lane_follow_gain", 1.25))
        return clamp(gain * heading_error / max(0.1, steer_angle), -1.0, 1.0)

    def _wait_for_radar(self, system, world_frame):
        timeout_s = float(self.runner_config.get("sensor_wait_timeout_s", 1.0))
        deadline = time.monotonic() + timeout_s
        while system.radar is not None and (
            system.radar.frame is None or system.radar.frame < world_frame
        ):
            if time.monotonic() >= deadline:
                return
            time.sleep(0.001)

    def _make_system(self, ego):
        return HeadlessRadarAEB(
            ego,
            self.sensor_config,
            self.carla_map,
        )

    def _make_tick_row(
        self,
        scenario,
        snapshot,
        elapsed_s,
        ego,
        hazard_entry,
        scenario_actors,
        system,
        collision,
    ):
        pipeline = system.pipeline
        target_cluster = pipeline.selected_target
        raw_points = system.radar.points if system.radar is not None else []
        ego_control = ego.get_control()
        logged_brake = float(ego_control.brake)
        logged_throttle = float(ego_control.throttle)
        if system.decision.state == AEBState.BRAKE:
            logged_brake = float(system.decision.brake)
            logged_throttle = 0.0
        target_actor = hazard_entry["actor"] if hazard_entry is not None else None
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
        lane_offset, heading_error = lane_pose_errors(ego, ego_waypoint)
        matched_entry, match_error = match_cluster_to_scenario_actor(
            target_cluster,
            scenario_actors,
        )
        hazard_role = hazard_entry["role"] if hazard_entry is not None else None
        matched_role = matched_entry["role"] if matched_entry is not None else None
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
            "ego_lane_center_offset_m": optional_round(lane_offset, 4),
            "ego_heading_error_deg": optional_round(heading_error, 4),
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
            "scenario_actor_count": len(scenario_actors),
            "hazard_actor_role": hazard_role,
            "radar_target_actor_role": matched_role,
            "radar_target_actor_error_m": optional_round(match_error, 4),
            "radar_target_matches_hazard": (
                None
                if target_cluster is None or hazard_role is None
                else int(matched_role == hazard_role)
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
            "target_track_age_frames": (
                target_cluster.age_frames if target_cluster is not None else None
            ),
            "target_hit_streak": (
                target_cluster.hit_streak if target_cluster is not None else None
            ),
            "target_confidence": optional_round(
                target_cluster.confidence if target_cluster is not None else None,
                4,
            ),
            "target_distance_m": optional_round(
                target_cluster.x_forward_m if target_cluster is not None else None,
                4,
            ),
            "target_lateral_m": optional_round(
                target_cluster.y_right_m if target_cluster is not None else None,
                4,
            ),
            "target_path_offset_m": optional_round(
                (
                    pipeline.distance_to_predicted_path(target_cluster)
                    if target_cluster is not None
                    else None
                ),
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
            "brake_stage": brake_stage_label(
                system.decision,
                system_brake_config(system),
            ),
            "brake_cmd": round(logged_brake, 4),
            "throttle_cmd": round(logged_throttle, 4),
            "steer_cmd": round(float(ego_control.steer), 4),
            "aeb_override": int(system.aeb_override_active),
            "fusion_confirmed": None,
            "fusion_gate_action": None,
            "fusion_gate_reason": None,
            "radar_fallback_active": 0,
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
        git_commit, git_dirty = git_state(AEB_ROOT)
        model_path = resolve_project_path(
            self.sensor_config.get("model", {}).get("path")
        )
        metadata = {
            "created_at": datetime.now().isoformat(),
            "command": " ".join(shlex.quote(str(arg)) for arg in sys.argv),
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "carla_client_version": self.client.get_client_version(),
            "carla_server_version": self.client.get_server_version(),
            "carla_map": self.world.get_map().name,
            "fixed_delta_seconds": self.runner_config.get(
                "fixed_delta_seconds",
                0.05,
            ),
            "seed": self.seed,
            "sensor_config": str(self.args.sensor_config),
            "sensor_config_sha256": sha256_file(self.args.sensor_config),
            "scenario_config": str(self.args.scenario_config),
            "scenario_config_sha256": sha256_file(self.args.scenario_config),
            "model_path": str(model_path) if model_path is not None else None,
            "model_providers_configured": self.sensor_config.get("model", {}).get(
                "providers"
            ),
            "model_inference_interval_s": self.sensor_config.get("model", {}).get(
                "inference_interval_s"
            ),
            "model_sha256": (
                sha256_file(model_path)
                if model_path is not None and model_path.exists()
                else None
            ),
            "config_snapshot_directory": "config_snapshot",
            "git_commit": git_commit,
            "git_dirty": git_dirty,
            "completed_scenario_runs": len(summaries),
            "repeat": self.args.repeat,
            "control_mode": self.args.control_mode,
            "resume_enabled": bool(getattr(self.args, "resume", False)),
            "record_evidence": self.args.record_evidence,
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
        self.speed_control_integral = {}

    def _destroy_stale_aeb_actors(self):
        try:
            actors = self.world.get_actors()
        except RuntimeError:
            return
        stale = []
        for actor in actors:
            role_name = str(actor.attributes.get("role_name", ""))
            if role_name.startswith("aeb_scenario_"):
                stale.append(actor)
        if not stale:
            return
        print("  Dọn {} actor AEB còn sót".format(len(stale)))
        for actor in stale:
            try:
                actor.destroy()
            except RuntimeError:
                pass
        try:
            self.world.tick()
        except RuntimeError:
            pass


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


def legacy_target_spec(scenario):
    scenario_type = str(scenario.get("type", "moving_lead"))
    spec = {
        "role": "target",
        "hazard": scenario_type != "adjacent_stationary",
        "initial_gap_m": float(scenario.get("initial_gap_m", 25.0)),
        "speed_kph": float(scenario.get("target_speed_kph", 0.0)),
        "spawn_lane": (
            scenario.get("adjacent_lane", "left")
            if scenario_type == "adjacent_stationary"
            else "ego"
        ),
        "motion": (
            "stationary"
            if scenario_type in ("stationary_lead", "adjacent_stationary")
            else "moving"
        ),
        "lane_follow": as_bool(scenario.get("lane_follow", False)),
    }
    if scenario_type == "braking_lead":
        spec["brake_event"] = {
            "start_s": float(scenario.get("target_brake_time_s", 1.5)),
            "brake": float(scenario.get("target_brake", 1.0)),
        }
    return spec


def match_cluster_to_scenario_actor(cluster, entries, max_error_m=6.0):
    if cluster is None or cluster.world_location is None or not entries:
        return None, None
    candidates = []
    for entry in entries:
        actor = entry["actor"]
        location = actor.get_location()
        delta_x = float(cluster.world_location.x) - float(location.x)
        delta_y = float(cluster.world_location.y) - float(location.y)
        delta_z = float(cluster.world_location.z) - float(location.z)
        error = math.sqrt(
            delta_x * delta_x + delta_y * delta_y + delta_z * delta_z
        )
        candidates.append((error, entry))
    error, entry = min(candidates, key=lambda item: item[0])
    if error > float(max_error_m):
        return None, error
    return entry, error


def lane_pose_errors(vehicle, waypoint):
    if vehicle is None or waypoint is None:
        return None, None
    vehicle_transform = vehicle.get_transform()
    vehicle_location = vehicle_transform.location
    lane_transform = waypoint.transform
    lane_location = lane_transform.location
    lane_forward = lane_transform.get_forward_vector()
    lane_right_x = -lane_forward.y
    lane_right_y = lane_forward.x
    delta_x = vehicle_location.x - lane_location.x
    delta_y = vehicle_location.y - lane_location.y
    lane_offset = delta_x * lane_right_x + delta_y * lane_right_y
    heading_error = normalized_angle_degrees(
        vehicle_transform.rotation.yaw - lane_transform.rotation.yaw
    )
    return lane_offset, heading_error


def steer_towards_location(
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


def offset_transform(transform, lateral_m=0.0, forward_m=0.0, z_m=0.0, yaw_deg=0.0):
    """Return a transform offset in the local forward/right/up frame."""

    forward = transform.get_forward_vector()
    right = carla.Vector3D(x=-forward.y, y=forward.x, z=0.0)
    location = transform.location
    return carla.Transform(
        carla.Location(
            x=location.x + forward.x * forward_m + right.x * lateral_m,
            y=location.y + forward.y * forward_m + right.y * lateral_m,
            z=location.z + forward.z * forward_m + z_m,
        ),
        carla.Rotation(
            pitch=transform.rotation.pitch,
            yaw=transform.rotation.yaw + yaw_deg,
            roll=transform.rotation.roll,
        ),
    )


def is_vehicle_actor(actor):
    return str(getattr(actor, "type_id", "")).startswith("vehicle.")


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


def brake_stage_label(decision, config):
    if decision is None:
        return "SAFE"
    state = getattr(decision, "state", None)
    brake = float(getattr(decision, "brake", 0.0) or 0.0)
    reason = str(getattr(decision, "reason", "") or "")
    if state == AEBState.WARNING:
        return "WARNING"
    if state != AEBState.BRAKE or brake <= 0.0:
        if state == AEBState.RELEASE:
            return "RELEASE"
        return "SAFE"
    if reason == "brake_held_until_stopped":
        return "HOLD_STOP"
    if brake >= float(config.staged_emergency_brake) - 1e-3:
        return "EMERGENCY"
    if brake >= float(config.staged_hard_brake) - 1e-3:
        return "HARD_BRAKE"
    if brake >= float(config.staged_medium_brake) - 1e-3:
        return "MEDIUM_BRAKE"
    return "SOFT_BRAKE"


def system_brake_config(system):
    config = getattr(system, "aeb_config", None)
    if config is not None:
        return config
    pipeline = getattr(system, "pipeline", None)
    config = getattr(pipeline, "aeb_config", None)
    if config is not None:
        return config
    return BinaryBrakeConfig.from_mapping(getattr(system, "brake_config", {}))


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
        "--resume",
        action="store_true",
        help="Tiếp tục run-id hiện có và bỏ qua scenario-runs đã hoàn thành.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
        help="Seed được ghi vào metadata và áp dụng cho Python/NumPy.",
    )
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
    parser.add_argument(
        "--record-evidence",
        action="store_true",
        help="Ghi video chase camera và ảnh tại các mốc AEB.",
    )
    parser.add_argument(
        "--keep-evidence-frames",
        action="store_true",
        help="Giữ toàn bộ frame PNG sau khi đã tạo video.",
    )
    parser.add_argument(
        "--scenario-cooldown-s",
        type=float,
        default=1.0,
        help=(
            "Nghỉ/tick thêm giữa các scenario để CARLA kịp dọn actor/sensor. "
            "CARLA 0.9.11 ổn định hơn khi chạy batch dài."
        ),
    )
    parser.add_argument(
        "--reload-world-every",
        type=int,
        default=1,
        help=(
            "Nếu > 0, reload world sau mỗi N scenario để tránh CARLA tích trạng thái. "
            "Chậm hơn nhưng hữu ích khi UE4 văng sau vài bài."
        ),
    )
    parser.add_argument(
        "--reload-world-wait-s",
        type=float,
        default=2.0,
        help="Số giây đợi sau reload_world trước khi chạy scenario tiếp theo.",
    )
    parser.add_argument("--load-map", action="store_true")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat phải lớn hơn hoặc bằng 1")
    if args.scenario_cooldown_s < 0:
        parser.error("--scenario-cooldown-s không được âm")
    if args.reload_world_every < 0:
        parser.error("--reload-world-every không được âm")
    if args.reload_world_wait_s < 0:
        parser.error("--reload-world-wait-s không được âm")
    return args


def main():
    args = parse_args()
    summaries = ScenarioRunner(args).run()
    failed = [summary for summary in summaries if summary["status"] != "PASS"]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
