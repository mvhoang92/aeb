#!/usr/bin/env python

"""Collect CARLA RGB images and one-class YOLO labels from vehicle ground truth."""

from __future__ import print_function

import argparse
import glob
import json
import os
import queue
import random
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = AEB_ROOT.parent
ROOT = PROJECT_ROOT
CARLA_DIST = ROOT / "PythonAPI" / "carla" / "dist"

if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

try:
    sys.path.append(
        glob.glob(
            str(
                CARLA_DIST
                / (
                    "carla-*%d.%d-%s.egg"
                    % (
                        sys.version_info.major,
                        sys.version_info.minor,
                        "win-amd64" if os.name == "nt" else "linux-x86_64",
                    )
                )
            )
        )[0]
    )
except IndexError:
    pass

import carla

try:
    import cv2
except ImportError:
    raise RuntimeError("Không import được OpenCV. Cần cài package opencv-python.")

try:
    import numpy as np
except ImportError:
    raise RuntimeError("Không import được NumPy.")

try:
    import yaml
except ImportError:
    raise RuntimeError("Không import được PyYAML.")

from core.ground_truth_labels import (
    camera_intrinsic,
    decode_carla_depth,
    decode_carla_semantic_tags,
    estimate_box_visibility,
    fit_box_to_visible_vehicle,
    project_vehicle_box,
)


DEFAULT_CONFIG = AEB_ROOT / "configs" / "dataset_collection.yaml"


def load_yaml(path):
    with open(path, "r") as stream:
        return yaml.safe_load(stream) or {}


def transform_from_config(config):
    location = config.get("location", {})
    rotation = config.get("rotation", {})
    return carla.Transform(
        carla.Location(
            x=float(location.get("x", 0.0)),
            y=float(location.get("y", 0.0)),
            z=float(location.get("z", 0.0)),
        ),
        carla.Rotation(
            pitch=float(rotation.get("pitch", 0.0)),
            yaw=float(rotation.get("yaw", 0.0)),
            roll=float(rotation.get("roll", 0.0)),
        ),
    )


def image_to_bgr(image):
    bgra = np.frombuffer(image.raw_data, dtype=np.uint8)
    bgra = bgra.reshape((image.height, image.width, 4))
    return bgra[:, :, :3].copy()


def vector_length(vector):
    return float(
        (vector.x * vector.x + vector.y * vector.y + vector.z * vector.z)
        ** 0.5
    )


def heading_difference_degrees(first, second):
    return abs((float(second) - float(first) + 180.0) % 360.0 - 180.0)


def location_dict(location):
    return {
        "x": float(location.x),
        "y": float(location.y),
        "z": float(location.z),
    }


def rotation_dict(rotation):
    return {
        "pitch": float(rotation.pitch),
        "yaw": float(rotation.yaw),
        "roll": float(rotation.roll),
    }


class GroundTruthCollector(object):
    def __init__(self, args):
        self.args = args
        self.config = load_yaml(args.config)
        self.world_config = self.config.get("world", {})
        self.tm_config = self.config.get("traffic_manager", {})
        self.traffic_config = self.config.get("traffic", {})
        self.ego_config = self.config.get("ego", {})
        self.camera_config = self.config.get("camera", {})
        self.dataset_config = self.config.get("dataset", {})
        self.filter_config = self.config.get("filter", {})
        if args.seed is not None:
            self.tm_config["seed"] = int(args.seed)
            self.dataset_config["random_seed"] = int(args.seed)
        if args.number_of_vehicles is not None:
            self.traffic_config["number_of_vehicles"] = int(
                args.number_of_vehicles
            )
        if args.same_lane_vehicles is not None:
            self.traffic_config["same_lane_vehicles_ahead"] = int(
                args.same_lane_vehicles
            )
        self.client = carla.Client(args.host, args.port)
        self.client.set_timeout(args.timeout)
        self.world = self.client.get_world()
        self.traffic_manager = self.client.get_trafficmanager(
            int(self.tm_config.get("port", 8000))
        )
        self.original_settings = None
        self.world_sync_owned = False
        self.traffic_manager_sync_owned = False
        self.ego = None
        self.rgb_camera = None
        self.depth_camera = None
        self.semantic_camera = None
        self.world_queue = queue.Queue()
        self.rgb_queue = queue.Queue()
        self.depth_queue = queue.Queue()
        self.semantic_queue = queue.Queue()
        self.world_tick_id = None
        self.managed_vehicle_ids = []
        self.same_lane_vehicle_ids = []
        self.random = random.Random(
            int(self.dataset_config.get("random_seed", 2026))
        )
        self.session_id = args.session_id or datetime.now().strftime(
            "town04_%Y%m%d_%H%M%S"
        )
        self.dataset_root = self._resolve_dataset_root()
        self.split = str(args.split or self.dataset_config.get("split", "train"))
        self.directories = {}
        self.metadata_path = None
        self.session_config_path = None
        self.metadata_stream = None
        self.dataset_prepared = False
        self.resumed_from_samples = 0
        self.saved_samples = 0
        self.positive_samples = 0
        self.negative_samples = 0
        self.saved_boxes = 0
        self.reject_counts = Counter()
        self.started_at = datetime.now().isoformat()
        self.stop_requested = False

    def run(self):
        try:
            self._preflight_dataset()
            self._ensure_map()
            self.original_settings = self.world.get_settings()
            self._prepare_dataset()
            self._enable_synchronous_mode()
            self._configure_traffic_manager()
            self.ego = self._spawn_ego()
            self.world.tick()
            self._spawn_traffic()
            self._spawn_cameras()
            self.world_tick_id = self.world.on_tick(self.world_queue.put)
            self._settle()
            self._report_same_lane_traffic()
            self._collect_loop()
        finally:
            self._write_summary()
            self._cleanup()

    def _resolve_dataset_root(self):
        configured = Path(
            self.args.output or self.dataset_config.get("root", "aeb/dataset")
        )
        if not configured.is_absolute():
            configured = ROOT / configured
        return configured

    def _ensure_map(self):
        expected_map = str(self.world_config.get("map", "Town04"))
        current_map = self.world.get_map().name.split("/")[-1]
        load_map = bool(self.world_config.get("load_map", True))
        if current_map == expected_map:
            return
        if not load_map:
            raise RuntimeError(
                "CARLA đang ở map {}, cần {}.".format(current_map, expected_map)
            )
        print("Đang load map {}...".format(expected_map))
        self.world = self.client.load_world(expected_map)
        self.traffic_manager = self.client.get_trafficmanager(
            int(self.tm_config.get("port", 8000))
        )

    def _preflight_dataset(self):
        self.directories = {
            "images": self.dataset_root / "images" / self.split,
            "labels": self.dataset_root / "labels" / self.split,
            "previews": self.dataset_root / "previews" / self.split,
            "metadata": self.dataset_root / "metadata" / self.split,
        }
        self.metadata_path = (
            self.directories["metadata"] / "{}.jsonl".format(self.session_id)
        )
        self.session_config_path = (
            self.directories["metadata"]
            / "{}_config.json".format(self.session_id)
        )

        if self.metadata_path.exists() and not self.args.resume:
            raise RuntimeError(
                "Session {} đã tồn tại: {}\n"
                "Dùng một tên mới, ví dụ '--session-id {}_02', hoặc thêm "
                "'--resume' để chạy tiếp session bị ngắt.".format(
                    self.session_id,
                    self.metadata_path,
                    self.session_id,
                )
            )
        if self.args.resume and not self.metadata_path.exists():
            raise RuntimeError(
                "Không thể resume vì session {} chưa tồn tại: {}".format(
                    self.session_id,
                    self.metadata_path,
                )
            )
        if self.args.resume:
            self._validate_resume_config()
            self._load_resume_state()

    def _validate_resume_config(self):
        if not self.session_config_path.exists():
            raise RuntimeError(
                "Session {} thiếu file config {}, không thể resume an toàn."
                .format(self.session_id, self.session_config_path)
            )
        with self.session_config_path.open("r") as stream:
            previous_config = json.load(stream)
        if previous_config != self.config:
            raise RuntimeError(
                "Config hiện tại khác config của session {}. Không resume để "
                "tránh trộn dữ liệu khác cấu hình; hãy dùng session-id mới."
                .format(self.session_id)
            )

    def _load_resume_state(self):
        records = []
        with self.metadata_path.open("r") as stream:
            for line_number, line in enumerate(stream, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except ValueError as error:
                    raise RuntimeError(
                        "Metadata lỗi tại dòng {} của {}: {}".format(
                            line_number,
                            self.metadata_path,
                            error,
                        )
                    )

        for index, record in enumerate(records):
            expected_name = "{}_{:06d}".format(self.session_id, index)
            sample_name = record.get("sample")
            if sample_name != expected_name:
                raise RuntimeError(
                    "Session {} không liên tục: cần {}, nhận {}. Không resume "
                    "để tránh ghi đè file.".format(
                        self.session_id,
                        expected_name,
                        sample_name,
                    )
                )
            image_path = self.dataset_root / record.get("image", "")
            label_path = self.dataset_root / record.get("label", "")
            if not image_path.is_file() or not label_path.is_file():
                raise RuntimeError(
                    "Session {} thiếu ảnh hoặc label của mẫu {}."
                    .format(self.session_id, sample_name)
                )

        self.saved_samples = len(records)
        self.positive_samples = sum(
            1 for record in records if record.get("objects")
        )
        self.negative_samples = self.saved_samples - self.positive_samples
        self.saved_boxes = sum(
            len(record.get("objects", [])) for record in records
        )
        self.resumed_from_samples = self.saved_samples

    def _prepare_dataset(self):
        for directory in self.directories.values():
            directory.mkdir(parents=True, exist_ok=True)

        mode = "a" if self.args.resume else "w"
        self.metadata_stream = self.metadata_path.open(mode)
        self.dataset_prepared = True
        self._write_dataset_yaml()
        if not self.args.resume:
            with self.session_config_path.open("w") as stream:
                json.dump(self.config, stream, ensure_ascii=False, indent=2)
        else:
            print(
                "Tiếp tục session {} từ mẫu {:06d}.".format(
                    self.session_id,
                    self.saved_samples,
                )
            )

    def _write_dataset_yaml(self):
        dataset_yaml = self.dataset_root / "dataset.yaml"
        data = {
            "path": str(self.dataset_root.resolve()),
            "train": "images/train",
            "val": "images/val",
            "test": "images/test",
            "names": {
                int(self.dataset_config.get("class_id", 0)): str(
                    self.dataset_config.get("class_name", "car")
                )
            },
        }
        with dataset_yaml.open("w") as stream:
            yaml.safe_dump(data, stream, sort_keys=False, allow_unicode=True)

    def _enable_synchronous_mode(self):
        if self.original_settings.synchronous_mode:
            raise RuntimeError(
                "CARLA đã ở synchronous mode trước khi collector chạy. "
                "Hãy dừng client đang tick hoặc chạy "
                "'PythonAPI/util/config.py --no-sync' rồi thử lại."
            )
        settings = self.world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = float(
            self.world_config.get("fixed_delta_seconds", 0.05)
        )
        self.world.apply_settings(settings)
        self.world_sync_owned = True

    def _configure_traffic_manager(self):
        self.traffic_manager.set_synchronous_mode(True)
        self.traffic_manager_sync_owned = True
        self.traffic_manager.set_global_distance_to_leading_vehicle(
            float(
                self.tm_config.get(
                    "global_distance_to_leading_vehicle_m",
                    2.5,
                )
            )
        )
        self.traffic_manager.global_percentage_speed_difference(
            float(self.tm_config.get("global_speed_difference_percent", 0.0))
        )
        if "seed" in self.tm_config:
            self.traffic_manager.set_random_device_seed(
                int(self.tm_config["seed"])
            )

    def _spawn_ego(self):
        blueprint_id = str(
            self.ego_config.get("blueprint", "vehicle.tesla.model3")
        )
        blueprint = self.world.get_blueprint_library().find(blueprint_id)
        if blueprint.has_attribute("role_name"):
            blueprint.set_attribute(
                "role_name",
                str(self.ego_config.get("role_name", "hero")),
            )

        spawn_points = list(self.world.get_map().get_spawn_points())
        spawn_index = self.ego_config.get("spawn_index")
        if spawn_index is not None:
            ordered_points = [spawn_points[int(spawn_index)]]
        else:
            self.random.shuffle(spawn_points)
            ordered_points = spawn_points

        ego = None
        for transform in ordered_points:
            ego = self.world.try_spawn_actor(blueprint, transform)
            if ego is not None:
                break
        if ego is None:
            raise RuntimeError("Không tìm được spawn point trống cho ego.")

        if bool(self.ego_config.get("autopilot", True)):
            ego.set_autopilot(True, int(self.tm_config.get("port", 8000)))
        print(
            "Ego: {} id={} | map={}".format(
                blueprint_id,
                ego.id,
                self.world.get_map().name.split("/")[-1],
            )
        )
        return ego

    def _spawn_traffic(self):
        if not bool(self.traffic_config.get("spawn_vehicles", True)):
            print("Không tự spawn traffic theo config.")
            return

        requested = max(
            0,
            int(self.traffic_config.get("number_of_vehicles", 30)),
        )
        if requested == 0:
            return

        actor_filter = str(
            self.traffic_config.get("actor_filter", "vehicle.*")
        )
        blueprints = list(
            self.world.get_blueprint_library().filter(actor_filter)
        )
        if bool(self.traffic_config.get("safe_blueprints", True)):
            unsafe_suffixes = (
                "isetta",
                "carlacola",
                "cybertruck",
                "t2",
            )
            blueprints = [
                blueprint
                for blueprint in blueprints
                if blueprint.has_attribute("number_of_wheels")
                and int(blueprint.get_attribute("number_of_wheels")) == 4
                and not blueprint.id.endswith(unsafe_suffixes)
            ]
        if not blueprints:
            raise RuntimeError(
                "Không tìm thấy vehicle blueprint phù hợp để spawn traffic."
            )

        same_lane_requested = min(
            requested,
            max(
                0,
                int(
                    self.traffic_config.get(
                        "same_lane_vehicles_ahead",
                        0,
                    )
                ),
            ),
        )
        same_lane_points = self._same_lane_spawn_points(
            same_lane_requested
        )

        spawn_points = list(self.world.get_map().get_spawn_points())
        self.random.shuffle(spawn_points)
        ego_location = self.ego.get_transform().location
        spawn_points = [
            transform
            for transform in spawn_points
            if transform.location.distance(ego_location) > 8.0
            and all(
                transform.location.distance(preferred.location) > 8.0
                for preferred in same_lane_points
            )
        ]
        remaining = max(0, requested - len(same_lane_points))
        selected_points = [
            (transform, True) for transform in same_lane_points
        ] + [
            (transform, False) for transform in spawn_points[:remaining]
        ]

        SpawnActor = carla.command.SpawnActor
        SetAutopilot = carla.command.SetAutopilot
        SetVehicleLightState = carla.command.SetVehicleLightState
        FutureActor = carla.command.FutureActor
        light_state = (
            carla.VehicleLightState.Position
            | carla.VehicleLightState.LowBeam
            if bool(self.traffic_config.get("car_lights_on", False))
            else carla.VehicleLightState.NONE
        )
        batch = []
        for transform, _ in selected_points:
            blueprint = self.random.choice(blueprints)
            if blueprint.has_attribute("color"):
                colors = blueprint.get_attribute("color").recommended_values
                if colors:
                    blueprint.set_attribute("color", self.random.choice(colors))
            if blueprint.has_attribute("driver_id"):
                drivers = blueprint.get_attribute("driver_id").recommended_values
                if drivers:
                    blueprint.set_attribute(
                        "driver_id",
                        self.random.choice(drivers),
                    )
            if blueprint.has_attribute("role_name"):
                blueprint.set_attribute("role_name", "autopilot")
            batch.append(
                SpawnActor(blueprint, transform)
                .then(
                    SetAutopilot(
                        FutureActor,
                        True,
                        self.traffic_manager.get_port(),
                    )
                )
                .then(SetVehicleLightState(FutureActor, light_state))
            )

        for response, (_, is_same_lane) in zip(
            self.client.apply_batch_sync(batch, False),
            selected_points,
        ):
            if response.error:
                self.reject_counts["traffic_spawn_failed"] += 1
            else:
                self.managed_vehicle_ids.append(response.actor_id)
                if is_same_lane:
                    self.same_lane_vehicle_ids.append(response.actor_id)
        print(
            "Traffic: đã spawn {}/{} xe NPC, trong đó {} xe cùng làn phía "
            "trước ego.".format(
                len(self.managed_vehicle_ids),
                requested,
                len(self.same_lane_vehicle_ids),
            )
        )

    def _same_lane_spawn_points(self, requested):
        if requested <= 0:
            return []

        carla_map = self.world.get_map()
        ego_waypoint = carla_map.get_waypoint(
            self.ego.get_transform().location,
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )
        if ego_waypoint is None:
            return []

        first_distance = max(
            12.0,
            float(
                self.traffic_config.get(
                    "same_lane_first_distance_m",
                    22.0,
                )
            ),
        )
        spacing = max(
            10.0,
            float(
                self.traffic_config.get(
                    "same_lane_spacing_m",
                    20.0,
                )
            ),
        )
        points = []
        current = ego_waypoint
        for index in range(requested):
            step = first_distance if index == 0 else spacing
            candidates = [
                waypoint
                for waypoint in current.next(step)
                if waypoint.lane_type == carla.LaneType.Driving
            ]
            if not candidates:
                break
            current = min(
                candidates,
                key=lambda waypoint: heading_difference_degrees(
                    current.transform.rotation.yaw,
                    waypoint.transform.rotation.yaw,
                ),
            )
            transform = current.transform
            transform.location.z += 0.35
            points.append(transform)
        return points

    def _configure_lane_behavior(self):
        if bool(self.ego_config.get("autopilot", True)):
            self.traffic_manager.auto_lane_change(
                self.ego,
                bool(self.ego_config.get("auto_lane_change", False)),
            )
        following_distance = max(
            2.0,
            float(
                self.traffic_config.get(
                    "same_lane_following_distance_m",
                    8.0,
                )
            ),
        )
        for actor_id in self.same_lane_vehicle_ids:
            actor = self.world.get_actor(actor_id)
            if actor is None:
                continue
            self.traffic_manager.auto_lane_change(actor, False)
            self.traffic_manager.distance_to_leading_vehicle(
                actor,
                following_distance,
            )

    def _report_same_lane_traffic(self):
        if not self.same_lane_vehicle_ids:
            return
        ego_location = self.ego.get_location()
        distances = []
        for actor_id in self.same_lane_vehicle_ids:
            actor = self.world.get_actor(actor_id)
            if actor is not None:
                location = actor.get_location()
                distances.append(
                    location.distance(ego_location)
                )
        print(
            "Khoảng cách nhóm cùng làn sau settle: {}".format(
                ", ".join(
                    "{:.0f}m".format(distance)
                    for distance in sorted(distances)
                )
            )
        )

    def _camera_blueprint(self, blueprint_id):
        blueprint = self.world.get_blueprint_library().find(blueprint_id)
        blueprint.set_attribute(
            "image_size_x",
            str(int(self.camera_config.get("image_size_x", 1280))),
        )
        blueprint.set_attribute(
            "image_size_y",
            str(int(self.camera_config.get("image_size_y", 720))),
        )
        blueprint.set_attribute(
            "fov",
            str(float(self.camera_config.get("fov", 70.0))),
        )
        blueprint.set_attribute(
            "sensor_tick",
            str(
                float(
                    self.camera_config.get(
                        "sensor_tick",
                        0.0,
                    )
                )
            ),
        )
        if blueprint.has_attribute("gamma"):
            blueprint.set_attribute(
                "gamma",
                str(float(self.camera_config.get("gamma", 2.2))),
            )
        if blueprint.has_attribute("enable_postprocess_effects"):
            blueprint.set_attribute(
                "enable_postprocess_effects",
                str(
                    bool(
                        self.camera_config.get(
                            "enable_postprocess_effects",
                            True,
                        )
                    )
                ).lower(),
            )
        return blueprint

    def _spawn_cameras(self):
        transform = transform_from_config(self.camera_config)
        self.rgb_camera = self.world.spawn_actor(
            self._camera_blueprint("sensor.camera.rgb"),
            transform,
            attach_to=self.ego,
            attachment_type=carla.AttachmentType.Rigid,
        )
        self.rgb_camera.listen(self.rgb_queue.put)

        if bool(self.filter_config.get("use_depth_visibility", True)):
            self.depth_camera = self.world.spawn_actor(
                self._camera_blueprint("sensor.camera.depth"),
                transform,
                attach_to=self.ego,
                attachment_type=carla.AttachmentType.Rigid,
            )
            self.depth_camera.listen(self.depth_queue.put)

        if bool(self.filter_config.get("use_semantic_visibility", True)):
            self.semantic_camera = self.world.spawn_actor(
                self._camera_blueprint(
                    "sensor.camera.semantic_segmentation"
                ),
                transform,
                attach_to=self.ego,
                attachment_type=carla.AttachmentType.Rigid,
            )
            self.semantic_camera.listen(self.semantic_queue.put)

    def _settle(self):
        settle_frames = max(
            1,
            int(self.dataset_config.get("settle_frames", 10)),
        )
        self._tick_synced()
        self._configure_lane_behavior()
        for _ in range(settle_frames - 1):
            self._tick_synced()

    def _collect_loop(self):
        legacy_interval = max(
            1,
            int(self.dataset_config.get("save_interval_frames", 4)),
        )
        interval_min = max(
            1,
            int(
                self.dataset_config.get(
                    "save_interval_frames_min",
                    legacy_interval,
                )
            ),
        )
        interval_max = max(
            interval_min,
            int(
                self.dataset_config.get(
                    "save_interval_frames_max",
                    interval_min,
                )
            ),
        )
        max_samples = int(
            self.args.max_samples
            if self.args.max_samples is not None
            else self.dataset_config.get("max_samples", 2000)
        )
        ticks_until_sample = 0
        print(
            "Bắt đầu thu dữ liệu: split={} | tối đa {} mẫu | lưu cách "
            "{}-{} frame".format(
                self.split,
                max_samples,
                interval_min,
                interval_max,
            )
        )
        while self.saved_samples < max_samples and not self.stop_requested:
            snapshot, rgb_image, depth_image, semantic_image = (
                self._tick_synced()
            )

            if ticks_until_sample <= 0:
                self._process_sample(
                    snapshot,
                    rgb_image,
                    depth_image,
                    semantic_image,
                )
                ticks_until_sample = (
                    self.random.randint(interval_min, interval_max) - 1
                )
            else:
                ticks_until_sample -= 1

    def _tick_synced(self):
        frame = self.world.tick()
        snapshot = self._queue_frame(self.world_queue, frame, "world")
        rgb_image = self._queue_frame(self.rgb_queue, frame, "rgb")
        depth_image = (
            self._queue_frame(self.depth_queue, frame, "depth")
            if self.depth_camera is not None
            else None
        )
        semantic_image = (
            self._queue_frame(self.semantic_queue, frame, "semantic")
            if self.semantic_camera is not None
            else None
        )
        return snapshot, rgb_image, depth_image, semantic_image

    def _queue_frame(self, sensor_queue, expected_frame, stream_name):
        while True:
            try:
                data = sensor_queue.get(timeout=self.args.sensor_timeout)
            except queue.Empty:
                raise RuntimeError(
                    "Timeout chờ stream '{}' ở frame {}. "
                    "Kiểm tra CARLA server/GPU và đảm bảo không có client "
                    "khác cùng điều khiển synchronous mode.".format(
                        stream_name,
                        expected_frame,
                    )
                )
            if data.frame < expected_frame:
                continue
            if data.frame > expected_frame:
                raise RuntimeError(
                    "Stream '{}' vượt frame: cần {}, nhận {}".format(
                        stream_name,
                        expected_frame,
                        data.frame,
                    )
                )
            return data

    def _process_sample(
        self,
        snapshot,
        rgb_image,
        depth_image,
        semantic_image,
    ):
        bgr = image_to_bgr(rgb_image)
        depth_m = (
            decode_carla_depth(depth_image)
            if depth_image is not None
            else None
        )
        semantic_tags = (
            decode_carla_semantic_tags(semantic_image)
            if semantic_image is not None
            else None
        )

        boxes = self._collect_boxes(
            snapshot,
            rgb_image.transform,
            depth_m,
            semantic_tags,
            rgb_image.width,
            rgb_image.height,
        )
        if not boxes and not self._keep_empty_frame():
            self.reject_counts["empty_frame_skipped"] += 1
            return

        sample_name = "{}_{:06d}".format(
            self.session_id,
            self.saved_samples,
        )
        image_path = self.directories["images"] / "{}.jpg".format(sample_name)
        label_path = self.directories["labels"] / "{}.txt".format(sample_name)
        jpeg_quality = int(self.dataset_config.get("jpeg_quality", 95))
        if not cv2.imwrite(
            str(image_path),
            bgr,
            [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
        ):
            raise RuntimeError("Không ghi được ảnh {}".format(image_path))

        class_id = int(self.dataset_config.get("class_id", 0))
        with label_path.open("w") as stream:
            for item in boxes:
                stream.write(
                    item["box"].as_yolo(
                        rgb_image.width,
                        rgb_image.height,
                        class_id,
                    )
                    + "\n"
                )

        preview = self._draw_preview(bgr, boxes, sample_name)
        if bool(self.dataset_config.get("save_previews", True)):
            preview_path = (
                self.directories["previews"] / "{}.jpg".format(sample_name)
            )
            cv2.imwrite(
                str(preview_path),
                preview,
                [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
            )
        self._show_preview(preview)
        self._write_metadata(sample_name, rgb_image, snapshot, boxes)

        self.saved_samples += 1
        self.saved_boxes += len(boxes)
        if boxes:
            self.positive_samples += 1
        else:
            self.negative_samples += 1

        if self.saved_samples % 25 == 0 or self.saved_samples == 1:
            print(
                "Đã lưu {:4d} mẫu | positive={} | negative={} | boxes={}".format(
                    self.saved_samples,
                    self.positive_samples,
                    self.negative_samples,
                    self.saved_boxes,
                )
            )

    def _collect_boxes(
        self,
        snapshot,
        camera_transform,
        depth_m,
        semantic_tags,
        image_width,
        image_height,
    ):
        intrinsic = camera_intrinsic(
            image_width,
            image_height,
            float(self.camera_config.get("fov", 70.0)),
        )
        camera_location = camera_transform.location
        actor_pattern = str(
            self.filter_config.get("actor_pattern", "vehicle.*")
        )
        boxes = []
        for actor in self.world.get_actors().filter(actor_pattern):
            if actor.id == self.ego.id:
                continue
            if not self._is_four_wheel_vehicle(actor):
                self.reject_counts["not_car"] += 1
                continue
            actor_snapshot = snapshot.find(actor.id)
            if actor_snapshot is None:
                self.reject_counts["missing_snapshot"] += 1
                continue
            actor_transform = actor_snapshot.get_transform()
            distance_m = camera_location.distance(actor_transform.location)
            if distance_m > float(
                self.filter_config.get("max_distance_m", 100.0)
            ):
                self.reject_counts["too_far"] += 1
                continue

            projected = project_vehicle_box(
                actor.bounding_box,
                actor_transform,
                camera_transform,
                intrinsic,
                image_width,
                image_height,
                near_plane_m=float(
                    self.filter_config.get("near_plane_m", 0.10)
                ),
            )
            if projected is None:
                self.reject_counts["outside_camera"] += 1
                continue
            original_projected = projected
            if projected.width < float(
                self.filter_config.get("min_box_width_px", 8)
            ):
                self.reject_counts["box_too_narrow"] += 1
                continue
            if projected.height < float(
                self.filter_config.get("min_box_height_px", 8)
            ):
                self.reject_counts["box_too_short"] += 1
                continue
            if projected.area < float(
                self.filter_config.get("min_box_area_px", 100)
            ):
                self.reject_counts["box_too_small"] += 1
                continue
            if projected.truncation > float(
                self.filter_config.get("max_truncation", 0.75)
            ):
                self.reject_counts["too_truncated"] += 1
                continue

            visibility = None
            if depth_m is not None and semantic_tags is not None:
                visibility = fit_box_to_visible_vehicle(
                    depth_m,
                    semantic_tags,
                    projected,
                    vehicle_tag=int(
                        self.filter_config.get(
                            "vehicle_semantic_tag",
                            10,
                        )
                    ),
                    depth_tolerance_m=float(
                        self.filter_config.get("depth_tolerance_m", 1.5)
                    ),
                    padding_px=int(
                        self.filter_config.get(
                            "visible_box_padding_px",
                            2,
                        )
                    ),
                )
                if visibility.visible_pixels < int(
                    self.filter_config.get("min_visible_pixels", 20)
                ):
                    self.reject_counts["semantic_visible_pixels"] += 1
                    continue
                if visibility.visible_ratio < float(
                    self.filter_config.get("min_visible_ratio", 0.02)
                ):
                    self.reject_counts["semantic_visible_ratio"] += 1
                    continue
                if not self._passes_heavy_occlusion_filter(visibility):
                    self.reject_counts["semantic_heavy_occlusion"] += 1
                    continue
                if bool(
                    self.filter_config.get(
                        "fit_box_to_visible_pixels",
                        True,
                    )
                ):
                    projected = visibility.fitted_box
                    if projected is None:
                        self.reject_counts["semantic_no_fitted_box"] += 1
                        continue
            elif depth_m is not None:
                visibility = estimate_box_visibility(
                    depth_m,
                    projected,
                    depth_tolerance_m=float(
                        self.filter_config.get("depth_tolerance_m", 1.5)
                    ),
                    sample_step_px=2,
                )
                if visibility.visible_pixels < int(
                    self.filter_config.get("min_visible_pixels", 6)
                ):
                    self.reject_counts["occluded_pixels"] += 1
                    continue
                if visibility.visible_ratio < float(
                    self.filter_config.get("min_visible_ratio", 0.01)
                ):
                    self.reject_counts["occluded_ratio"] += 1
                    continue
                if not self._passes_heavy_occlusion_filter(visibility):
                    self.reject_counts["depth_heavy_occlusion"] += 1
                    continue

            if projected.width < float(
                self.filter_config.get("min_box_width_px", 8)
            ) or projected.height < float(
                self.filter_config.get("min_box_height_px", 8)
            ) or projected.area < float(
                self.filter_config.get("min_box_area_px", 100)
            ):
                self.reject_counts["fitted_box_too_small"] += 1
                continue

            velocity = actor_snapshot.get_velocity()
            boxes.append(
                {
                    "actor": actor,
                    "box": projected,
                    "original_box": original_projected,
                    "distance_m": float(distance_m),
                    "visibility": visibility,
                    "transform": actor_transform,
                    "speed_mps": vector_length(velocity),
                }
            )
        boxes.sort(key=lambda item: item["distance_m"])
        boxes = self._suppress_overlapping_boxes(boxes)
        return boxes

    def _suppress_overlapping_boxes(self, boxes):
        if not bool(self.filter_config.get("suppress_overlapping_boxes", True)):
            return boxes

        iou_threshold = float(
            self.filter_config.get("overlap_suppression_iou", 0.55)
        )
        containment_threshold = float(
            self.filter_config.get("overlap_suppression_containment", 0.75)
        )
        kept = []
        for item in boxes:
            duplicate = False
            for kept_item in kept:
                overlap = self._box_overlap_stats(item["box"], kept_item["box"])
                if (
                    overlap["iou"] >= iou_threshold
                    or overlap["min_containment"] >= containment_threshold
                ):
                    duplicate = True
                    break
            if duplicate:
                self.reject_counts["overlap_suppressed"] += 1
                continue
            kept.append(item)
        return kept

    @staticmethod
    def _box_overlap_stats(first, second):
        intersection_x1 = max(first.x1, second.x1)
        intersection_y1 = max(first.y1, second.y1)
        intersection_x2 = min(first.x2, second.x2)
        intersection_y2 = min(first.y2, second.y2)
        intersection_width = max(0.0, intersection_x2 - intersection_x1)
        intersection_height = max(0.0, intersection_y2 - intersection_y1)
        intersection_area = intersection_width * intersection_height

        first_area = max(0.0, first.area)
        second_area = max(0.0, second.area)
        union_area = first_area + second_area - intersection_area
        min_area = min(first_area, second_area)

        return {
            "iou": intersection_area / union_area if union_area > 0.0 else 0.0,
            "min_containment": (
                intersection_area / min_area if min_area > 0.0 else 0.0
            ),
        }

    def _passes_heavy_occlusion_filter(self, visibility):
        heavy_ratio = float(
            self.filter_config.get("heavy_occlusion_visible_ratio", 0.0)
        )
        if heavy_ratio <= 0.0 or visibility.visible_ratio >= heavy_ratio:
            return True

        min_visible_pixels = int(
            self.filter_config.get("heavy_occlusion_min_visible_pixels", 0)
        )
        if visibility.visible_pixels >= min_visible_pixels:
            return True

        fitted_box = visibility.fitted_box
        min_fitted_area = float(
            self.filter_config.get("heavy_occlusion_min_fitted_area_px", 0.0)
        )
        if fitted_box is not None and fitted_box.area >= min_fitted_area:
            return True

        return False

    def _is_four_wheel_vehicle(self, actor):
        minimum_wheels = int(
            self.filter_config.get("minimum_wheels", 4)
        )
        try:
            return int(actor.attributes.get("number_of_wheels", 0)) >= minimum_wheels
        except (TypeError, ValueError):
            return False

    def _keep_empty_frame(self):
        if not bool(self.dataset_config.get("save_empty_images", True)):
            return False
        ratio = float(
            self.dataset_config.get("empty_frame_keep_ratio", 0.15)
        )
        return self.random.random() <= max(0.0, min(1.0, ratio))

    def _draw_preview(self, bgr, boxes, sample_name):
        preview = bgr.copy()
        class_name = str(self.dataset_config.get("class_name", "car"))
        for item in boxes:
            box = item["box"]
            point1 = (int(round(box.x1)), int(round(box.y1)))
            point2 = (int(round(box.x2)), int(round(box.y2)))
            cv2.rectangle(preview, point1, point2, (60, 230, 90), 2)
            visibility = item["visibility"]
            label = "{} id={} d={:.1f}m".format(
                class_name,
                item["actor"].id,
                item["distance_m"],
            )
            if visibility is not None:
                label += " vis={:.2f}".format(visibility.visible_ratio)
            text_y = max(18, point1[1] - 5)
            cv2.putText(
                preview,
                label,
                (point1[0], text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (60, 230, 90),
                1,
                cv2.LINE_AA,
            )
        cv2.putText(
            preview,
            "{} | boxes={} | saved={}".format(
                sample_name,
                len(boxes),
                self.saved_samples + 1,
            ),
            (12, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return preview

    def _show_preview(self, preview):
        enabled = bool(
            self.dataset_config.get("show_preview_window", True)
        ) and not self.args.no_window
        if enabled and os.name != "nt" and not os.environ.get("DISPLAY"):
            enabled = False
        if not enabled:
            return
        cv2.imshow("CARLA ground-truth dataset collector", preview)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            self.stop_requested = True

    def _write_metadata(self, sample_name, image, snapshot, boxes):
        ego_snapshot = snapshot.find(self.ego.id)
        ego_transform = (
            ego_snapshot.get_transform()
            if ego_snapshot is not None
            else self.ego.get_transform()
        )
        record = {
            "sample": sample_name,
            "split": self.split,
            "frame": int(image.frame),
            "timestamp_s": float(image.timestamp),
            "map": self.world.get_map().name.split("/")[-1],
            "image": "images/{}/{}.jpg".format(self.split, sample_name),
            "label": "labels/{}/{}.txt".format(self.split, sample_name),
            "camera": {
                "width": int(image.width),
                "height": int(image.height),
                "fov": float(self.camera_config.get("fov", 70.0)),
                "location": location_dict(image.transform.location),
                "rotation": rotation_dict(image.transform.rotation),
            },
            "ego": {
                "actor_id": int(self.ego.id),
                "blueprint": self.ego.type_id,
                "location": location_dict(ego_transform.location),
                "rotation": rotation_dict(ego_transform.rotation),
            },
            "objects": [
                self._object_metadata(item)
                for item in boxes
            ],
        }
        self.metadata_stream.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )
        self.metadata_stream.flush()

    def _object_metadata(self, item):
        box = item["box"]
        visibility = item["visibility"]
        return {
            "class_id": int(self.dataset_config.get("class_id", 0)),
            "class_name": str(self.dataset_config.get("class_name", "car")),
            "actor_id": int(item["actor"].id),
            "blueprint": item["actor"].type_id,
            "color": item["actor"].attributes.get("color"),
            "same_lane_seeded": (
                int(item["actor"].id) in self.same_lane_vehicle_ids
            ),
            "distance_m": item["distance_m"],
            "speed_mps": item["speed_mps"],
            "bbox_xyxy": [box.x1, box.y1, box.x2, box.y2],
            "projected_bbox_xyxy": [
                item["original_box"].x1,
                item["original_box"].y1,
                item["original_box"].x2,
                item["original_box"].y2,
            ],
            "truncation": box.truncation,
            "min_depth_m": box.min_depth_m,
            "max_depth_m": box.max_depth_m,
            "visible_pixels": (
                visibility.visible_pixels if visibility is not None else None
            ),
            "visible_ratio": (
                visibility.visible_ratio if visibility is not None else None
            ),
            "location": location_dict(item["transform"].location),
            "rotation": rotation_dict(item["transform"].rotation),
        }

    def _write_summary(self):
        if not self.dataset_prepared:
            return
        summary = {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "finished_at": datetime.now().isoformat(),
            "split": self.split,
            "resumed_from_samples": self.resumed_from_samples,
            "same_lane_spawned": len(self.same_lane_vehicle_ids),
            "saved_samples": self.saved_samples,
            "positive_samples": self.positive_samples,
            "negative_samples": self.negative_samples,
            "saved_boxes": self.saved_boxes,
            "reject_counts": dict(self.reject_counts),
        }
        summary_path = (
            self.directories["metadata"]
            / "{}_summary.json".format(self.session_id)
        )
        with summary_path.open("w") as stream:
            json.dump(summary, stream, ensure_ascii=False, indent=2)

    def _cleanup(self):
        if self.metadata_stream is not None:
            self.metadata_stream.close()
            self.metadata_stream = None
        if self.world_tick_id is not None:
            try:
                self.world.remove_on_tick(self.world_tick_id)
            except RuntimeError:
                pass
            self.world_tick_id = None
        for sensor in (
            self.semantic_camera,
            self.depth_camera,
            self.rgb_camera,
        ):
            if sensor is not None:
                try:
                    sensor.stop()
                except RuntimeError:
                    pass
        if self.ego is not None:
            try:
                self.ego.set_autopilot(
                    False,
                    int(self.tm_config.get("port", 8000)),
                )
            except RuntimeError:
                pass
        if self.traffic_manager_sync_owned:
            try:
                self.traffic_manager.set_synchronous_mode(False)
            except RuntimeError:
                pass
            self.traffic_manager_sync_owned = False
        if self.world_sync_owned and self.original_settings is not None:
            try:
                self.world.apply_settings(self.original_settings)
            except RuntimeError:
                pass
            self.world_sync_owned = False
        for sensor in (
            self.semantic_camera,
            self.depth_camera,
            self.rgb_camera,
        ):
            if sensor is not None:
                try:
                    sensor.destroy()
                except RuntimeError:
                    pass
        actor_ids = list(self.managed_vehicle_ids)
        if self.ego is not None:
            actor_ids.append(self.ego.id)
        if actor_ids:
            try:
                self.client.apply_batch(
                    [
                        carla.command.DestroyActor(actor_id)
                        for actor_id in actor_ids
                    ]
                )
            except RuntimeError:
                pass
        cv2.destroyAllWindows()
        if self.saved_samples:
            print(
                "Hoàn tất: {} mẫu, {} box. Dataset: {}".format(
                    self.saved_samples,
                    self.saved_boxes,
                    self.dataset_root,
                )
            )


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--sensor-timeout", type=float, default=10.0)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--split", choices=("train", "val", "test"), default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Ghi đè seed của Traffic Manager và collector cho session này.",
    )
    parser.add_argument(
        "--number-of-vehicles",
        type=int,
        default=None,
        help="Ghi đè tổng số NPC; đặt 0 để thu negative session đường trống.",
    )
    parser.add_argument(
        "--same-lane-vehicles",
        type=int,
        default=None,
        help="Ghi đè số NPC được đặt cùng làn phía trước ego.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Chạy tiếp session đã tồn tại nếu config và dữ liệu hợp lệ.",
    )
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--no-window", action="store_true")
    return parser.parse_args()


def main():
    collector = GroundTruthCollector(parse_args())
    try:
        collector.run()
    except KeyboardInterrupt:
        print("\nĐã dừng bởi người dùng.")


if __name__ == "__main__":
    main()
