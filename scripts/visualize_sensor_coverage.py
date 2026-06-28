#!/usr/bin/env python

"""Visualize AEB camera/radar coverage on a Tesla Model 3 in CARLA."""

from __future__ import print_function

import argparse
import glob
import json
import math
import os
import queue
import sys
import time
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = AEB_ROOT.parent
CARLA_DIST = PROJECT_ROOT / "PythonAPI" / "carla" / "dist"

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
    import numpy as np
except ImportError:
    raise RuntimeError("Không import được NumPy.")

try:
    import yaml
except ImportError:
    raise RuntimeError("Không import được PyYAML.")

try:
    import cv2
except ImportError:
    raise RuntimeError("Không import được OpenCV. Cần cài opencv-python.")


DEFAULT_CONFIG = AEB_ROOT / "configs" / "sensors.yaml"
DEFAULT_OUTPUT_DIR = AEB_ROOT / "outputs" / "sensor_coverage"
TESLA_MODEL3 = "vehicle.tesla.model3"

CAMERA_COLOR = carla.Color(0, 120, 255)
CAMERA_TEXT_COLOR = carla.Color(80, 180, 255)
RADAR_COLOR = carla.Color(255, 70, 30)
RADAR_TEXT_COLOR = carla.Color(255, 150, 90)
EGO_COLOR = carla.Color(255, 255, 255)
CV_CAMERA_COLOR = (255, 180, 0)
CV_RADAR_COLOR = (0, 40, 255)
CV_EGO_COLOR = (255, 255, 255)


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


def vector_to_location(vector, scale=1.0):
    return carla.Location(
        x=float(vector.x) * scale,
        y=float(vector.y) * scale,
        z=float(vector.z) * scale,
    )


def add_location(first, second):
    return carla.Location(
        x=float(first.x) + float(second.x),
        y=float(first.y) + float(second.y),
        z=float(first.z) + float(second.z),
    )


def sub_location(first, second):
    return carla.Location(
        x=float(first.x) - float(second.x),
        y=float(first.y) - float(second.y),
        z=float(first.z) - float(second.z),
    )


def mul_location(location, scale):
    return carla.Location(
        x=float(location.x) * float(scale),
        y=float(location.y) * float(scale),
        z=float(location.z) * float(scale),
    )


def length(location):
    return math.sqrt(
        location.x * location.x + location.y * location.y + location.z * location.z
    )


def get_right_vector(transform):
    yaw = math.radians(float(transform.rotation.yaw) + 90.0)
    return carla.Location(x=math.cos(yaw), y=math.sin(yaw), z=0.0)


def transform_local_location(parent_transform, local_location):
    yaw = math.radians(float(parent_transform.rotation.yaw))
    cos_yaw = math.cos(yaw)
    sin_yaw = math.sin(yaw)
    return carla.Location(
        x=float(parent_transform.location.x)
        + float(local_location.x) * cos_yaw
        - float(local_location.y) * sin_yaw,
        y=float(parent_transform.location.y)
        + float(local_location.x) * sin_yaw
        + float(local_location.y) * cos_yaw,
        z=float(parent_transform.location.z) + float(local_location.z),
    )


def relative_to_world_transform(ego_transform, relative_transform):
    world_location = transform_local_location(ego_transform, relative_transform.location)
    return carla.Transform(
        world_location,
        carla.Rotation(
            pitch=float(ego_transform.rotation.pitch)
            + float(relative_transform.rotation.pitch),
            yaw=float(ego_transform.rotation.yaw) + float(relative_transform.rotation.yaw),
            roll=float(ego_transform.rotation.roll) + float(relative_transform.rotation.roll),
        ),
    )


def make_look_at_transform(location, target):
    direction = sub_location(target, location)
    horizontal = math.sqrt(direction.x * direction.x + direction.y * direction.y)
    yaw = math.degrees(math.atan2(direction.y, direction.x))
    pitch = math.degrees(math.atan2(direction.z, horizontal))
    return carla.Transform(location, carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0))


def image_to_bgr(image):
    bgra = np.frombuffer(image.raw_data, dtype=np.uint8)
    bgra = bgra.reshape((image.height, image.width, 4))
    return bgra[:, :, :3].copy()


def save_bgr_with_caption(path, image, caption):
    canvas = image.copy()
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 42), (0, 0, 0), -1)
    cv2.putText(
        canvas,
        caption,
        (16, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    if not cv2.imwrite(str(path), canvas):
        raise RuntimeError("Không ghi được ảnh: %s" % path)


def intrinsic_matrix(width, height, fov_deg):
    focal = float(width) / (2.0 * math.tan(math.radians(float(fov_deg)) * 0.5))
    return np.array(
        [
            [focal, 0.0, float(width) / 2.0],
            [0.0, focal, float(height) / 2.0],
            [0.0, 0.0, 1.0],
        ]
    )


def world_location_to_array(location):
    return np.array([float(location.x), float(location.y), float(location.z), 1.0])


class SensorCoverageVisualizer(object):
    def __init__(self, args):
        self.args = args
        self.config = load_yaml(args.config)
        self.client = carla.Client(args.host, args.port)
        self.client.set_timeout(args.timeout)
        self.world = self.client.get_world()
        self.ego = None
        self.spawned_ego = False
        self.capture_camera = None
        self.image_queue = None
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        ego_config = self.config.get("ego", {})
        blueprint = ego_config.get("blueprint", TESLA_MODEL3)
        if blueprint != TESLA_MODEL3:
            raise RuntimeError(
                "Sensor coverage visualization is locked to %s, config has %s"
                % (TESLA_MODEL3, blueprint)
            )

        self.camera_config = self.config.get("driver_camera", {})
        self.radar_config = self.config.get("front_radar", {})
        self.camera_relative = transform_from_config(self.camera_config)
        self.radar_relative = transform_from_config(self.radar_config)
        self.camera_range_m = float(args.camera_range)
        self.radar_range_m = float(self.radar_config.get("range", 100.0))
        self.camera_fov_deg = float(self.camera_config.get("fov", 70.0))
        self.radar_hfov_deg = float(self.radar_config.get("horizontal_fov", 30.0))
        self.radar_vfov_deg = float(self.radar_config.get("vertical_fov", 6.0))

    def run(self):
        try:
            if self.args.map_name:
                self._load_map_if_needed(self.args.map_name)
            self.ego = self._get_or_spawn_tesla_model3()
            time.sleep(0.3)
            self._draw_sensor_coverage()
            self._capture_views()
            self._write_metadata()
            print("Đã lưu ảnh minh họa sensor coverage vào: %s" % self.output_dir)
        finally:
            self._cleanup()

    def _load_map_if_needed(self, map_name):
        current = self.world.get_map().name.split("/")[-1]
        if current == map_name:
            return
        print("Đang load map %s..." % map_name)
        self.world = self.client.load_world(map_name)
        time.sleep(1.0)

    def _get_or_spawn_tesla_model3(self):
        role_name = self.config.get("ego", {}).get("role_name", "hero")
        if self.args.use_existing_ego:
            actors = self.world.get_actors().filter(TESLA_MODEL3)
            for actor in actors:
                if actor.attributes.get("role_name") == role_name:
                    print("Dùng Tesla Model 3 hiện có: id=%s" % actor.id)
                    return actor
            if not self.args.spawn_ego_if_missing:
                raise RuntimeError(
                    "Không tìm thấy %s role_name=%s trong world." % (TESLA_MODEL3, role_name)
                )

        blueprint = self.world.get_blueprint_library().find(TESLA_MODEL3)
        blueprint.set_attribute("role_name", role_name)
        spawn_points = self.world.get_map().get_spawn_points()
        if not spawn_points:
            raise RuntimeError("Map không có spawn point.")
        spawn_index = self.config.get("ego", {}).get("spawn_index")
        if spawn_index is None:
            spawn_index = int(self.args.spawn_index)
        spawn_transform = spawn_points[int(spawn_index) % len(spawn_points)]
        actor = self.world.try_spawn_actor(blueprint, spawn_transform)
        if actor is None:
            for candidate in spawn_points:
                actor = self.world.try_spawn_actor(blueprint, candidate)
                if actor is not None:
                    break
        if actor is None:
            raise RuntimeError("Không spawn được Tesla Model 3.")
        self.spawned_ego = True
        print("Spawn Tesla Model 3 mới: id=%s" % actor.id)
        return actor

    def _draw_sensor_coverage(self):
        ego_transform = self.ego.get_transform()
        camera_transform = relative_to_world_transform(ego_transform, self.camera_relative)
        radar_transform = relative_to_world_transform(ego_transform, self.radar_relative)

        lifetime = float(self.args.debug_lifetime)
        ego_box = carla.BoundingBox(
            transform_local_location(ego_transform, self.ego.bounding_box.location),
            self.ego.bounding_box.extent,
        )
        self.world.debug.draw_box(
            ego_box,
            ego_transform.rotation,
            thickness=0.06,
            color=EGO_COLOR,
            life_time=lifetime,
        )
        self._draw_horizontal_fov(
            camera_transform,
            self.camera_fov_deg,
            self.camera_range_m,
            CAMERA_COLOR,
            lifetime,
            z_offset=0.08,
            arc_segments=48,
            ray_segments=4,
        )
        self._draw_horizontal_fov(
            radar_transform,
            self.radar_hfov_deg,
            self.radar_range_m,
            RADAR_COLOR,
            lifetime,
            z_offset=0.32,
            arc_segments=48,
            ray_segments=4,
        )
        self._draw_vertical_fov(
            radar_transform,
            self.radar_vfov_deg,
            self.radar_range_m,
            RADAR_COLOR,
            lifetime,
            side_offset_m=0.15,
        )
        self._draw_vertical_fov(
            camera_transform,
            self._camera_vertical_fov_deg(),
            self.camera_range_m,
            CAMERA_COLOR,
            lifetime,
            side_offset_m=-0.15,
        )

    def _draw_sensor_marker(self, transform, label, color, text_color, lifetime):
        location = transform.location
        self.world.debug.draw_point(
            location,
            size=0.10,
            color=color,
            life_time=lifetime,
        )

    def _draw_horizontal_fov(
        self,
        transform,
        fov_deg,
        range_m,
        color,
        lifetime,
        z_offset=0.0,
        arc_segments=32,
        ray_segments=4,
    ):
        origin = add_location(transform.location, carla.Location(z=z_offset))
        start = None
        half = float(fov_deg) * 0.5
        for index in range(arc_segments + 1):
            ratio = float(index) / float(arc_segments)
            yaw_offset = -half + ratio * float(fov_deg)
            direction = self._direction_from_offsets(transform, yaw_offset, 0.0)
            end = add_location(origin, vector_to_location(direction, range_m))
            if start is not None:
                self.world.debug.draw_line(start, end, thickness=0.04, color=color, life_time=lifetime)
            start = end
        for index in range(int(ray_segments) + 1):
            ratio = float(index) / float(ray_segments)
            yaw_offset = -half + ratio * float(fov_deg)
            direction = self._direction_from_offsets(transform, yaw_offset, 0.0)
            end = add_location(origin, vector_to_location(direction, range_m))
            self.world.debug.draw_line(origin, end, thickness=0.06, color=color, life_time=lifetime)

    def _draw_vertical_fov(self, transform, fov_deg, range_m, color, lifetime, side_offset_m=0.0):
        right = get_right_vector(transform)
        origin = add_location(transform.location, mul_location(right, side_offset_m))
        half = float(fov_deg) * 0.5
        upper = add_location(origin, vector_to_location(self._direction_from_offsets(transform, 0.0, -half), range_m))
        center = add_location(origin, vector_to_location(self._direction_from_offsets(transform, 0.0, 0.0), range_m))
        lower = add_location(origin, vector_to_location(self._direction_from_offsets(transform, 0.0, half), range_m))
        self.world.debug.draw_line(origin, upper, thickness=0.045, color=color, life_time=lifetime)
        self.world.debug.draw_line(origin, center, thickness=0.035, color=color, life_time=lifetime)
        self.world.debug.draw_line(origin, lower, thickness=0.045, color=color, life_time=lifetime)
        self.world.debug.draw_line(upper, lower, thickness=0.04, color=color, life_time=lifetime)

    def _direction_from_offsets(self, transform, yaw_offset_deg, pitch_offset_deg):
        yaw = math.radians(float(transform.rotation.yaw) + float(yaw_offset_deg))
        pitch = math.radians(float(transform.rotation.pitch) + float(pitch_offset_deg))
        return carla.Vector3D(
            x=math.cos(pitch) * math.cos(yaw),
            y=math.cos(pitch) * math.sin(yaw),
            z=math.sin(pitch),
        )

    def _camera_vertical_fov_deg(self):
        width = float(self.camera_config.get("image_size_x", 1280))
        height = float(self.camera_config.get("image_size_y", 720))
        horizontal = math.radians(self.camera_fov_deg)
        vertical = 2.0 * math.atan(math.tan(horizontal * 0.5) * height / width)
        return math.degrees(vertical)

    def _capture_views(self):
        ego_transform = self.ego.get_transform()
        forward = vector_to_location(ego_transform.get_forward_vector())
        right = get_right_vector(ego_transform)
        up = carla.Location(z=1.0)
        base = ego_transform.location

        views = [
            (
                "near_top_view.png",
                "Near top view - sensor placement on Tesla Model 3",
                add_location(base, carla.Location(z=11.0)),
                base,
                52.0,
            ),
            (
                "far_top_view.png",
                "Far top view - radar 100 m and camera illustrative range",
                add_location(add_location(base, mul_location(forward, 50.0)), carla.Location(z=180.0)),
                add_location(base, mul_location(forward, 50.0)),
                62.0,
            ),
            (
                "near_side_view.png",
                "Near side view - sensor heights and mounting positions",
                add_location(add_location(base, mul_location(right, 22.0)), carla.Location(z=1.75)),
                add_location(base, carla.Location(z=1.10)),
                22.0,
            ),
            (
                "far_side_view.png",
                "Far side orthographic-style view - sensor height and range",
                add_location(
                    add_location(add_location(base, mul_location(forward, 26.0)), mul_location(right, 82.0)),
                    carla.Location(z=8.0),
                ),
                add_location(add_location(base, mul_location(forward, 26.0)), carla.Location(z=1.3)),
                42.0,
            ),
        ]

        for filename, caption, location, target, fov in views:
            view_transform = make_look_at_transform(location, target)
            image = self._capture_camera_image(view_transform, fov)
            image = self._overlay_coverage(image, view_transform, fov)
            save_bgr_with_caption(self.output_dir / filename, image, caption)

    def _overlay_coverage(self, image, view_transform, view_fov):
        overlay = image.copy()
        ego_transform = self.ego.get_transform()
        camera_transform = relative_to_world_transform(ego_transform, self.camera_relative)
        radar_transform = relative_to_world_transform(ego_transform, self.radar_relative)

        self._draw_projected_horizontal_fov(
            overlay,
            view_transform,
            view_fov,
            camera_transform,
            self.camera_fov_deg,
            self.camera_range_m,
            CV_CAMERA_COLOR,
            z_offset=0.08,
        )
        self._draw_projected_vertical_fov(
            overlay,
            view_transform,
            view_fov,
            camera_transform,
            self._camera_vertical_fov_deg(),
            self.camera_range_m,
            CV_CAMERA_COLOR,
            side_offset_m=-0.15,
        )
        self._draw_projected_horizontal_fov(
            overlay,
            view_transform,
            view_fov,
            radar_transform,
            self.radar_hfov_deg,
            self.radar_range_m,
            CV_RADAR_COLOR,
            z_offset=0.32,
        )
        self._draw_projected_vertical_fov(
            overlay,
            view_transform,
            view_fov,
            radar_transform,
            self.radar_vfov_deg,
            self.radar_range_m,
            CV_RADAR_COLOR,
            side_offset_m=0.15,
        )
        self._draw_projected_marker(
            overlay,
            view_transform,
            view_fov,
            camera_transform.location,
            "CAM",
            CV_CAMERA_COLOR,
        )
        self._draw_projected_marker(
            overlay,
            view_transform,
            view_fov,
            radar_transform.location,
            "RADAR",
            CV_RADAR_COLOR,
        )
        self._draw_legend(overlay)
        return overlay

    def _project_location(self, location, view_transform, view_fov, image_shape):
        height, width = image_shape[:2]
        world_to_camera = np.array(view_transform.get_inverse_matrix())
        camera_point = np.dot(world_to_camera, world_location_to_array(location))
        if camera_point[0] <= 0.05:
            return None
        point = np.array([camera_point[1], -camera_point[2], camera_point[0]])
        matrix = intrinsic_matrix(width, height, view_fov)
        pixel = np.dot(matrix, point)
        x = int(pixel[0] / pixel[2])
        y = int(pixel[1] / pixel[2])
        margin = 200
        if x < -margin or x > width + margin or y < -margin or y > height + margin:
            return None
        return (x, y)

    def _draw_projected_marker(
        self,
        image,
        view_transform,
        view_fov,
        location,
        label,
        color,
    ):
        point = self._project_location(location, view_transform, view_fov, image.shape)
        if point is None:
            return
        cv2.circle(image, point, 4, color, -1, cv2.LINE_AA)
        cv2.circle(image, point, 6, (255, 255, 255), 1, cv2.LINE_AA)

    def _draw_projected_horizontal_fov(
        self,
        image,
        view_transform,
        view_fov,
        sensor_transform,
        sensor_fov,
        sensor_range,
        color,
        z_offset=0.0,
    ):
        origin = add_location(sensor_transform.location, carla.Location(z=z_offset))
        half = float(sensor_fov) * 0.5
        arc_points = []
        for index in range(65):
            ratio = float(index) / 64.0
            yaw_offset = -half + ratio * float(sensor_fov)
            direction = self._direction_from_offsets(sensor_transform, yaw_offset, 0.0)
            arc_points.append(add_location(origin, vector_to_location(direction, sensor_range)))
        self._draw_projected_polyline(image, view_transform, view_fov, arc_points, color, 3)
        for yaw_offset in (-half, 0.0, half):
            direction = self._direction_from_offsets(sensor_transform, yaw_offset, 0.0)
            end = add_location(origin, vector_to_location(direction, sensor_range))
            self._draw_projected_line(image, view_transform, view_fov, origin, end, color, 3)

    def _draw_projected_vertical_fov(
        self,
        image,
        view_transform,
        view_fov,
        sensor_transform,
        sensor_fov,
        sensor_range,
        color,
        side_offset_m=0.0,
    ):
        right = get_right_vector(sensor_transform)
        origin = add_location(sensor_transform.location, mul_location(right, side_offset_m))
        half = float(sensor_fov) * 0.5
        upper = add_location(
            origin,
            vector_to_location(
                self._direction_from_offsets(sensor_transform, 0.0, -half),
                sensor_range,
            ),
        )
        lower = add_location(
            origin,
            vector_to_location(
                self._direction_from_offsets(sensor_transform, 0.0, half),
                sensor_range,
            ),
        )
        center = add_location(
            origin,
            vector_to_location(
                self._direction_from_offsets(sensor_transform, 0.0, 0.0),
                sensor_range,
            ),
        )
        self._draw_projected_line(image, view_transform, view_fov, origin, upper, color, 2)
        self._draw_projected_line(image, view_transform, view_fov, origin, lower, color, 2)
        self._draw_projected_line(image, view_transform, view_fov, origin, center, color, 2)
        self._draw_projected_line(image, view_transform, view_fov, upper, lower, color, 2)

    def _draw_projected_line(
        self,
        image,
        view_transform,
        view_fov,
        start_location,
        end_location,
        color,
        thickness,
    ):
        start = self._project_location(start_location, view_transform, view_fov, image.shape)
        end = self._project_location(end_location, view_transform, view_fov, image.shape)
        if start is None or end is None:
            return
        cv2.line(image, start, end, color, thickness, cv2.LINE_AA)

    def _draw_projected_polyline(
        self,
        image,
        view_transform,
        view_fov,
        locations,
        color,
        thickness,
    ):
        previous = None
        for location in locations:
            point = self._project_location(location, view_transform, view_fov, image.shape)
            if previous is not None and point is not None:
                cv2.line(image, previous, point, color, thickness, cv2.LINE_AA)
            previous = point

    def _draw_legend(self, image):
        height, width = image.shape[:2]
        x = width - 360
        y = 58
        cv2.rectangle(image, (x - 12, y - 28), (width - 16, y + 76), (0, 0, 0), -1)
        cv2.putText(
            image,
            "Camera FOV: blue",
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            CV_CAMERA_COLOR,
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            "Radar FOV: red",
            (x, y + 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            CV_RADAR_COLOR,
            2,
            cv2.LINE_AA,
        )

    def _capture_camera_image(self, transform, fov):
        blueprint = self.world.get_blueprint_library().find("sensor.camera.rgb")
        blueprint.set_attribute("image_size_x", str(int(self.args.image_width)))
        blueprint.set_attribute("image_size_y", str(int(self.args.image_height)))
        blueprint.set_attribute("fov", str(float(fov)))
        blueprint.set_attribute("sensor_tick", "0.0")
        image_queue = queue.Queue()
        camera = self.world.spawn_actor(blueprint, transform)
        camera.listen(image_queue.put)
        try:
            # Give debug lines at least one render frame before capture.
            for _ in range(3):
                self._advance_world()
            image = image_queue.get(timeout=float(self.args.capture_timeout))
            return image_to_bgr(image)
        finally:
            try:
                camera.stop()
                camera.destroy()
            except RuntimeError:
                pass

    def _advance_world(self):
        settings = self.world.get_settings()
        if settings.synchronous_mode:
            self.world.tick()
        else:
            self.world.wait_for_tick()

    def _write_metadata(self):
        ego_transform = self.ego.get_transform()
        camera_transform = relative_to_world_transform(ego_transform, self.camera_relative)
        radar_transform = relative_to_world_transform(ego_transform, self.radar_relative)
        metadata = {
            "ego_blueprint": TESLA_MODEL3,
            "ego_actor_id": int(self.ego.id),
            "ego_transform": {
                "location": location_dict(ego_transform.location),
                "rotation": rotation_dict(ego_transform.rotation),
            },
            "camera": {
                "config": self.camera_config,
                "illustrative_range_m": self.camera_range_m,
                "computed_vertical_fov_deg": self._camera_vertical_fov_deg(),
                "world_transform": {
                    "location": location_dict(camera_transform.location),
                    "rotation": rotation_dict(camera_transform.rotation),
                },
            },
            "radar": {
                "config": self.radar_config,
                "world_transform": {
                    "location": location_dict(radar_transform.location),
                    "rotation": rotation_dict(radar_transform.rotation),
                },
            },
            "outputs": [
                "near_top_view.png",
                "far_top_view.png",
                "near_side_view.png",
                "far_side_view.png",
            ],
        }
        with open(self.output_dir / "sensor_coverage_metadata.json", "w") as stream:
            json.dump(metadata, stream, indent=2, sort_keys=True)

    def _cleanup(self):
        if self.spawned_ego and self.ego is not None:
            try:
                self.ego.destroy()
            except RuntimeError:
                pass
            self.ego = None


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Draw camera/radar coverage on a Tesla Model 3 and save CARLA screenshots."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=2000, type=int)
    parser.add_argument("--timeout", default=10.0, type=float)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--map-name", default=None)
    parser.add_argument("--spawn-index", default=53, type=int)
    parser.add_argument("--use-existing-ego", action="store_true", default=True)
    parser.add_argument("--no-use-existing-ego", dest="use_existing_ego", action="store_false")
    parser.add_argument("--spawn-ego-if-missing", action="store_true", default=True)
    parser.add_argument("--no-spawn-ego-if-missing", dest="spawn_ego_if_missing", action="store_false")
    parser.add_argument("--camera-range", default=80.0, type=float)
    parser.add_argument("--image-width", default=1920, type=int)
    parser.add_argument("--image-height", default=1080, type=int)
    parser.add_argument("--debug-lifetime", default=12.0, type=float)
    parser.add_argument("--capture-timeout", default=5.0, type=float)
    return parser


def main():
    args = build_arg_parser().parse_args()
    visualizer = SensorCoverageVisualizer(args)
    visualizer.run()


if __name__ == "__main__":
    main()
