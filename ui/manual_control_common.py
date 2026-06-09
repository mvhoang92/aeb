#!/usr/bin/env python

"""Shared helpers for AEB two-panel manual_control extensions."""

from __future__ import print_function

import argparse
import ast
import glob
import math
import os
import sys
import time
import weakref
from dataclasses import dataclass
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
ROOT = AEB_ROOT.parent
CARLA_DIST = ROOT / "PythonAPI" / "carla" / "dist"
EXAMPLES_DIR = ROOT / "PythonAPI" / "examples"

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

sys.path.insert(0, str(EXAMPLES_DIR))

import carla
from carla import ColorConverter as cc

try:
    import numpy as np
except ImportError:
    raise RuntimeError("cannot import numpy, make sure numpy package is installed")

from control.brake import compute_ttc

try:
    import pygame
except ImportError:
    raise RuntimeError("cannot import pygame, make sure pygame package is installed")

try:
    import yaml
except ImportError:
    raise RuntimeError("cannot import yaml, make sure PyYAML package is installed")

import manual_control


DEFAULT_CONFIG = AEB_ROOT / "configs" / "sensors.yaml"
DEFAULT_MODEL_PATH = AEB_ROOT / "models" / "yolo26n.pt"
DEFAULT_ONNX_MODEL_PATH = AEB_ROOT / "models" / "yolo26n.onnx"

COCO_NAMES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    4: "airplane",
    5: "bus",
    6: "train",
    7: "truck",
    8: "boat",
    9: "traffic light",
    10: "fire hydrant",
    11: "stop sign",
    12: "parking meter",
    13: "bench",
    14: "bird",
    15: "cat",
    16: "dog",
    17: "horse",
    18: "sheep",
    19: "cow",
    20: "elephant",
    21: "bear",
    22: "zebra",
    23: "giraffe",
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    27: "tie",
    28: "suitcase",
    29: "frisbee",
    30: "skis",
    31: "snowboard",
    32: "sports ball",
    33: "kite",
    34: "baseball bat",
    35: "baseball glove",
    36: "skateboard",
    37: "surfboard",
    38: "tennis racket",
    39: "bottle",
    40: "wine glass",
    41: "cup",
    42: "fork",
    43: "knife",
    44: "spoon",
    45: "bowl",
    46: "banana",
    47: "apple",
    48: "sandwich",
    49: "orange",
    50: "broccoli",
    51: "carrot",
    52: "hot dog",
    53: "pizza",
    54: "donut",
    55: "cake",
    56: "chair",
    57: "couch",
    58: "potted plant",
    59: "bed",
    60: "dining table",
    61: "toilet",
    62: "tv",
    63: "laptop",
    64: "mouse",
    65: "remote",
    66: "keyboard",
    67: "cell phone",
    68: "microwave",
    69: "oven",
    70: "toaster",
    71: "sink",
    72: "refrigerator",
    73: "book",
    74: "clock",
    75: "vase",
    76: "scissors",
    77: "teddy bear",
    78: "hair drier",
    79: "toothbrush",
}


def load_yaml(path):
    with open(path, "r") as stream:
        return yaml.safe_load(stream) or {}


def config_value(data, section, key, default):
    section_data = data.get(section, {})
    if not isinstance(section_data, dict):
        return default
    return section_data.get(key, default)


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


def attachment_from_config(value):
    value = str(value or "Rigid").lower()
    if value == "springarm":
        return carla.AttachmentType.SpringArm
    return carla.AttachmentType.Rigid


def prepare_manual_control_args(args, config, panel_width, panel_height, gamma):
    ego_cfg = config.get("ego", {})
    manual_cfg = config.get("manual_control", {})
    args.width = panel_width
    args.height = panel_height
    args.gamma = gamma
    args.filter = args.filter or manual_cfg.get(
        "actor_filter",
        ego_cfg.get("blueprint", "vehicle.tesla.model3"),
    )
    args.rolename = args.rolename or manual_cfg.get(
        "role_name",
        ego_cfg.get("role_name", "hero"),
    )
    return args


def load_or_get_world(client, config, args):
    world_cfg = config.get("world", {})
    map_name = args.map_name or world_cfg.get("map", "Town04")
    load_map = bool(world_cfg.get("load_map", True))
    world = client.get_world()
    current_map_name = world.get_map().name.split("/")[-1]
    if load_map and current_map_name != map_name:
        world = client.load_world(map_name)
    return world


def display_size_from_args(args, config):
    if args.res:
        try:
            width, height = [int(value) for value in args.res.lower().split("x")]
            return width, height
        except ValueError:
            raise ValueError("--res must be formatted as WIDTHxHEIGHT")
    return (
        int(config_value(config, "display", "panel_width", 1280)),
        int(config_value(config, "display", "panel_height", 720)),
    )


def add_common_args(parser, default_config=DEFAULT_CONFIG):
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--config", type=Path, default=default_config)
    parser.add_argument("--map-name", default=None)
    parser.add_argument(
        "--res",
        metavar="WIDTHxHEIGHT",
        default=None,
        help="per-panel resolution, for example 1280x720 or 960x540",
    )
    parser.add_argument("-a", "--autopilot", action="store_true")
    parser.add_argument("--filter", default=None)
    parser.add_argument("--rolename", default=None)
    return parser


def run_two_panel(args, panel_factory, caption):
    """Run manual_control.py unchanged on the left and a custom panel on the right."""

    config = load_yaml(args.config)
    panel_width, panel_height = display_size_from_args(args, config)
    fps = int(config_value(config, "display", "fps", 60))
    gamma = float(config_value(config, "display", "gamma", 2.2))
    args = prepare_manual_control_args(args, config, panel_width, panel_height, gamma)

    pygame.init()
    pygame.font.init()
    client = None
    manual_world = None
    right_panel = None

    try:
        client = carla.Client(args.host, args.port)
        client.set_timeout(args.timeout)

        display = pygame.display.set_mode(
            (panel_width * 2, panel_height),
            pygame.HWSURFACE | pygame.DOUBLEBUF,
        )
        pygame.display.set_caption(caption)
        display.fill((0, 0, 0))
        pygame.display.flip()

        hud = manual_control.HUD(panel_width, panel_height)
        carla_world = load_or_get_world(client, config, args)
        manual_world = manual_control.World(carla_world, hud, args)
        controller = manual_control.KeyboardControl(manual_world, args.autopilot)
        right_panel = panel_factory(manual_world, config, panel_width, panel_height, gamma, args)
        if hasattr(right_panel, "set_controller"):
            right_panel.set_controller(controller)

        clock = pygame.time.Clock()
        while True:
            clock.tick_busy_loop(fps)
            if controller.parse_events(client, manual_world, clock):
                return

            right_panel.tick()
            manual_world.tick(clock)
            manual_world.render(display)
            right_panel.render(display)
            pygame.display.flip()

    finally:
        if manual_world is not None and manual_world.recording_enabled and client is not None:
            client.stop_recorder()
        if right_panel is not None:
            right_panel.destroy()
        if manual_world is not None:
            manual_world.destroy()
        pygame.quit()


class CameraSensor(object):
    """RGB camera sensor that stores the newest frame for right-panel rendering."""

    def __init__(self, parent_actor, config, gamma):
        self.sensor = None
        self.surface = None
        self.latest_rgb = None
        self.latest_transform = None
        self.frame = None
        self.timestamp = None
        self._parent = parent_actor
        self.config = config
        self.width = int(config.get("image_size_x", 1280))
        self.height = int(config.get("image_size_y", 720))
        self.fov = float(config.get("fov", 70.0))
        self._spawn(gamma)

    def _spawn(self, gamma):
        world = self._parent.get_world()
        bp = world.get_blueprint_library().find(
            self.config.get("blueprint", "sensor.camera.rgb")
        )
        bp.set_attribute("image_size_x", str(self.width))
        bp.set_attribute("image_size_y", str(self.height))
        bp.set_attribute("fov", str(self.fov))
        if "sensor_tick" in self.config:
            bp.set_attribute("sensor_tick", str(self.config["sensor_tick"]))
        if bp.has_attribute("gamma"):
            bp.set_attribute("gamma", str(gamma))

        self.sensor = world.spawn_actor(
            bp,
            transform_from_config(self.config),
            attach_to=self._parent,
            attachment_type=attachment_from_config(self.config.get("attachment")),
        )
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda image: CameraSensor._parse_image(weak_self, image))

    def render_image(self, display, position, size):
        rect = pygame.Rect(position, size)
        if self.surface is None:
            pygame.draw.rect(display, (10, 10, 10), rect)
            return
        surface = self.surface
        if surface.get_size() != size:
            surface = pygame.transform.smoothscale(surface, size)
        display.blit(surface, position)

    def destroy(self):
        if self.sensor is not None:
            try:
                self.sensor.stop()
                self.sensor.destroy()
            except RuntimeError:
                pass
            self.sensor = None

    @staticmethod
    def _parse_image(weak_self, image):
        self = weak_self()
        if not self:
            return
        image.convert(cc.Raw)
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        self.latest_rgb = array.copy()
        self.latest_transform = getattr(image, "transform", None)
        if self.latest_transform is None and self.sensor is not None:
            self.latest_transform = self.sensor.get_transform()
        self.frame = image.frame
        self.timestamp = image.timestamp
        self.surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))


@dataclass
class RadarPoint(object):
    depth_m: float
    x_forward_m: float
    y_right_m: float
    z_up_m: float
    relative_velocity_mps: float
    velocity_towards_sensor_mps: float
    azimuth_rad: float
    altitude_rad: float
    world_location: object


class RadarSensor(object):
    """Front radar sensor that stores the newest detections."""

    def __init__(self, parent_actor, config):
        self.sensor = None
        self.points = []
        self.frame = None
        self.timestamp = None
        self._parent = parent_actor
        self.config = config
        self.range_m = float(config.get("range", 100.0))
        self.horizontal_fov = float(config.get("horizontal_fov", 30.0))
        self.vertical_fov = float(config.get("vertical_fov", 6.0))
        self._spawn()

    def _spawn(self):
        world = self._parent.get_world()
        bp = world.get_blueprint_library().find(
            self.config.get("blueprint", "sensor.other.radar")
        )
        for key in (
            "range",
            "horizontal_fov",
            "vertical_fov",
            "points_per_second",
            "sensor_tick",
        ):
            if key in self.config:
                bp.set_attribute(key, str(self.config[key]))

        self.sensor = world.spawn_actor(
            bp,
            transform_from_config(self.config),
            attach_to=self._parent,
            attachment_type=attachment_from_config(self.config.get("attachment")),
        )
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda radar_data: RadarSensor._parse_radar(weak_self, radar_data))

    def destroy(self):
        if self.sensor is not None:
            try:
                self.sensor.stop()
                self.sensor.destroy()
            except RuntimeError:
                pass
            self.sensor = None

    @staticmethod
    def _parse_radar(weak_self, radar_data):
        self = weak_self()
        if not self:
            return
        points = []
        current_rotation = radar_data.transform.rotation
        origin = radar_data.transform.location
        for detection in radar_data:
            azimuth = float(detection.azimuth)
            altitude = float(detection.altitude)
            depth = float(detection.depth)
            radar_velocity = float(detection.velocity)

            cos_altitude = math.cos(altitude)
            x_forward = depth * cos_altitude * math.cos(azimuth)
            y_right = depth * cos_altitude * math.sin(azimuth)
            z_up = depth * math.sin(altitude)

            fw_vec = carla.Vector3D(x=depth)
            carla.Transform(
                carla.Location(),
                carla.Rotation(
                    pitch=current_rotation.pitch + math.degrees(altitude),
                    yaw=current_rotation.yaw + math.degrees(azimuth),
                    roll=current_rotation.roll,
                ),
            ).transform(fw_vec)
            world_location = origin + fw_vec

            points.append(
                RadarPoint(
                    depth_m=depth,
                    x_forward_m=x_forward,
                    y_right_m=y_right,
                    z_up_m=z_up,
                    relative_velocity_mps=radar_velocity,
                    velocity_towards_sensor_mps=radar_velocity,
                    azimuth_rad=azimuth,
                    altitude_rad=altitude,
                    world_location=world_location,
                )
            )
        self.points = points
        self.frame = radar_data.frame
        self.timestamp = radar_data.timestamp


@dataclass
class Detection(object):
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    class_name: str


class YoloDetector(object):
    """Optional YOLO wrapper with ONNX Runtime GPU preferred for CARLA runtime."""

    def __init__(self, config):
        self.config = config or {}
        self.enabled = bool(self.config.get("enabled", True))
        self.backend = str(self.config.get("backend", "auto")).lower()
        self.confidence = float(self.config.get("confidence", 0.25))
        self.inference_interval_s = float(self.config.get("inference_interval_s", 0.15))
        self.allowed_classes = self.config.get("allowed_classes")
        self.input_size = int(self.config.get("input_size", 640))
        self.providers = self.config.get(
            "providers",
            ["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.model = None
        self.session = None
        self.input_name = None
        self.output_names = None
        self.runtime_label = "YOLO"
        self.names = {}
        self.status = "YOLO chưa tải"
        self._last_inference_time = 0.0
        self._last_detections = []
        self._load_model()

    def _load_model(self):
        if not self.enabled:
            self.status = "YOLO đang tắt trong config"
            return

        default_path = DEFAULT_ONNX_MODEL_PATH if self.backend in ("auto", "onnx") else DEFAULT_MODEL_PATH
        model_path = Path(str(self.config.get("path", default_path)))
        if not model_path.is_absolute():
            model_path = ROOT / model_path
        if not model_path.exists():
            self.status = "Không thấy model: {}".format(model_path)
            return

        suffix = model_path.suffix.lower()
        if self.backend == "auto":
            self.backend = "onnx" if suffix == ".onnx" else "ultralytics"
        if self.backend == "onnx" or suffix == ".onnx":
            self._load_onnx_model(model_path)
            return
        self._load_ultralytics_model(model_path)

    def _load_onnx_model(self, model_path):
        try:
            import onnxruntime as ort
        except ImportError:
            self.status = "Thiếu package onnxruntime-gpu"
            return

        try:
            available = set(ort.get_available_providers())
            providers = [provider for provider in self.providers if provider in available]
            if not providers:
                providers = ["CPUExecutionProvider"]
            self.session = ort.InferenceSession(str(model_path), providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [output.name for output in self.session.get_outputs()]
            self.names = onnx_model_names(
                self.session.get_modelmeta().custom_metadata_map,
                COCO_NAMES,
            )
            active_providers = self.session.get_providers()
            self.runtime_label = (
                "ONNX CUDA" if "CUDAExecutionProvider" in active_providers else "ONNX CPU"
            )
            self.status = "ONNX YOLO26n: {}".format(",".join(self.session.get_providers()))
        except Exception as exc:  # pylint: disable=broad-except
            self.status = "Lỗi tải ONNX: {}".format(exc)

    def _load_ultralytics_model(self, model_path):
        try:
            from ultralytics import YOLO
        except ImportError:
            self.status = "Thiếu package ultralytics"
            return

        try:
            self.model = YOLO(str(model_path))
            self.names = getattr(self.model, "names", {}) or {}
            self.status = "YOLO: {}".format(model_path.name)
        except Exception as exc:  # pylint: disable=broad-except
            self.status = "Lỗi tải YOLO: {}".format(exc)

    def infer(self, rgb_image):
        if rgb_image is None or (self.model is None and self.session is None):
            return list(self._last_detections)
        now = time.time()
        if now - self._last_inference_time < self.inference_interval_s:
            return list(self._last_detections)

        try:
            if self.session is not None:
                detections = self._infer_onnx(rgb_image)
            else:
                detections = self._infer_ultralytics(rgb_image)
            self._last_detections = detections
            self._last_inference_time = now
            self.status = "{}: {} object".format(self.runtime_label, len(detections))
        except Exception as exc:  # pylint: disable=broad-except
            self.status = "Lỗi inference YOLO: {}".format(exc)
        return list(self._last_detections)

    def _infer_onnx(self, rgb_image):
        model_input, scale, pad_x, pad_y = preprocess_yolo_onnx(rgb_image, self.input_size)
        outputs = self.session.run(self.output_names, {self.input_name: model_input})
        detections = parse_yolo26_onnx_output(
            outputs[0],
            original_size=(rgb_image.shape[1], rgb_image.shape[0]),
            scale=scale,
            pad_x=pad_x,
            pad_y=pad_y,
            names=self.names,
            confidence_threshold=self.confidence,
        )
        return self._filter_allowed_classes(detections)

    def _infer_ultralytics(self, rgb_image):
        results = self.model(rgb_image, verbose=False)
        result = results[0]
        detections = parse_ultralytics_result(result, self.names, self.confidence)
        return self._filter_allowed_classes(detections)

    def _filter_allowed_classes(self, detections):
        if not self.allowed_classes:
            return detections
        allowed = set(str(name) for name in self.allowed_classes)
        return [det for det in detections if det.class_name in allowed]


def preprocess_yolo_onnx(rgb_image, input_size):
    height, width = rgb_image.shape[:2]
    scale = min(float(input_size) / float(width), float(input_size) / float(height))
    new_width = int(round(width * scale))
    new_height = int(round(height * scale))
    pad_x = (input_size - new_width) / 2.0
    pad_y = (input_size - new_height) / 2.0

    try:
        import cv2
    except ImportError:
        raise RuntimeError("Thiếu package opencv-python để resize ảnh cho ONNX")

    resized = cv2.resize(rgb_image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((input_size, input_size, 3), 114, dtype=np.uint8)
    left = int(round(pad_x - 0.1))
    top = int(round(pad_y - 0.1))
    canvas[top : top + new_height, left : left + new_width] = resized
    tensor = canvas.astype(np.float32) / 255.0
    tensor = np.transpose(tensor, (2, 0, 1))[None]
    return np.ascontiguousarray(tensor), scale, float(left), float(top)


def onnx_model_names(metadata, fallback):
    raw_names = (metadata or {}).get("names")
    if not raw_names:
        return dict(fallback or {})
    try:
        parsed = ast.literal_eval(raw_names)
    except (SyntaxError, ValueError):
        return dict(fallback or {})
    if isinstance(parsed, dict):
        return {
            int(class_id): str(class_name)
            for class_id, class_name in parsed.items()
        }
    if isinstance(parsed, (list, tuple)):
        return {
            index: str(class_name)
            for index, class_name in enumerate(parsed)
        }
    return dict(fallback or {})


def parse_yolo26_onnx_output(
    output,
    *,
    original_size,
    scale,
    pad_x,
    pad_y,
    names,
    confidence_threshold,
):
    predictions = np.asarray(output)
    if predictions.ndim == 3:
        predictions = predictions[0]
    width, height = original_size
    detections = []
    for row in predictions:
        if len(row) < 6:
            continue
        confidence = float(row[4])
        if confidence < confidence_threshold:
            continue
        class_id = int(row[5])
        x1 = (float(row[0]) - pad_x) / scale
        y1 = (float(row[1]) - pad_y) / scale
        x2 = (float(row[2]) - pad_x) / scale
        y2 = (float(row[3]) - pad_y) / scale
        x1 = clamp_float(x1, 0.0, float(width - 1))
        y1 = clamp_float(y1, 0.0, float(height - 1))
        x2 = clamp_float(x2, 0.0, float(width - 1))
        y2 = clamp_float(y2, 0.0, float(height - 1))
        if x2 <= x1 or y2 <= y1:
            continue
        detections.append(
            Detection(
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                confidence=confidence,
                class_id=class_id,
                class_name=str(names.get(class_id, class_id)),
            )
        )
    return detections


def clamp_float(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def parse_ultralytics_result(result, default_names, confidence_threshold):
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return []
    names = getattr(result, "names", None) or default_names or {}
    xyxy = tensor_to_numpy(getattr(boxes, "xyxy", []))
    cls_values = tensor_to_numpy(getattr(boxes, "cls", []))
    conf_values = tensor_to_numpy(getattr(boxes, "conf", []))
    detections = []
    for index, bbox in enumerate(xyxy):
        confidence = float(conf_values[index]) if index < len(conf_values) else 0.0
        if confidence < confidence_threshold:
            continue
        class_id = int(cls_values[index]) if index < len(cls_values) else -1
        class_name = str(names.get(class_id, class_id))
        detections.append(
            Detection(
                x1=float(bbox[0]),
                y1=float(bbox[1]),
                x2=float(bbox[2]),
                y2=float(bbox[3]),
                confidence=confidence,
                class_id=class_id,
                class_name=class_name,
            )
        )
    return detections


def tensor_to_numpy(value):
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        return value.numpy()
    return np.asarray(value)


def select_front_radar_target(
    points,
    max_lateral_offset_m=2.4,
    min_z_up_m=-0.35,
    max_z_up_m=2.5,
    min_forward_distance_m=1.5,
    max_range_m=None,
):
    candidates = [
        point
        for point in points
        if point.x_forward_m >= min_forward_distance_m
        and (max_range_m is None or point.x_forward_m <= max_range_m)
        and abs(point.y_right_m) <= max_lateral_offset_m
        and min_z_up_m <= point.z_up_m <= max_z_up_m
    ]
    if not candidates:
        return None

    def sort_key(point):
        ttc = compute_ttc(point.x_forward_m, point.relative_velocity_mps)
        has_ttc = 0 if math.isfinite(ttc) else 1
        return has_ttc, ttc, point.x_forward_m

    return min(candidates, key=sort_key)


def camera_intrinsic(width, height, fov_degrees):
    focal = width / (2.0 * math.tan(math.radians(fov_degrees) / 2.0))
    return np.array(
        [
            [focal, 0.0, width / 2.0],
            [0.0, focal, height / 2.0],
            [0.0, 0.0, 1.0],
        ]
    )


def project_world_to_camera(world_location, camera_transform, intrinsic):
    if world_location is None or camera_transform is None:
        return None
    world_point = np.array(
        [world_location.x, world_location.y, world_location.z, 1.0]
    )
    world_to_camera = np.array(camera_transform.get_inverse_matrix())
    point = np.dot(world_to_camera, world_point)
    camera_point = np.array([point[1], -point[2], point[0]])
    if camera_point[2] <= 0.0:
        return None
    pixel = np.dot(intrinsic, camera_point)
    return pixel[0] / pixel[2], pixel[1] / pixel[2]


def scale_detection(det, image_size, panel_size, panel_x=0):
    scale_x = float(panel_size[0]) / float(image_size[0])
    scale_y = float(panel_size[1]) / float(image_size[1])
    return (
        int(panel_x + det.x1 * scale_x),
        int(det.y1 * scale_y),
        int((det.x2 - det.x1) * scale_x),
        int((det.y2 - det.y1) * scale_y),
    )


def draw_panel_label(display, panel_x, text):
    font = pygame.font.Font(pygame.font.get_default_font(), 18)
    surface = font.render(text, True, (255, 255, 255))
    bg = pygame.Surface((surface.get_width() + 16, surface.get_height() + 10))
    bg.set_alpha(150)
    bg.fill((0, 0, 0))
    display.blit(bg, (panel_x + 8, 8))
    display.blit(surface, (panel_x + 16, 14))


def draw_lines(display, lines, x, y, color=(255, 255, 255), font_size=16):
    font = pygame.font.Font(pygame.font.get_default_font(), font_size)
    for line in lines:
        surface = font.render(str(line), True, color)
        display.blit(surface, (x, y))
        y += font_size + 4


def draw_text_box(display, lines, position, width=420, alpha=150):
    font = pygame.font.Font(pygame.font.get_default_font(), 16)
    height = 10 + len(lines) * 20
    box = pygame.Surface((width, height))
    box.set_alpha(alpha)
    box.fill((0, 0, 0))
    display.blit(box, position)
    y = position[1] + 6
    for line in lines:
        surface = font.render(str(line), True, (255, 255, 255))
        display.blit(surface, (position[0] + 8, y))
        y += 20


def format_float(value, digits=1):
    if value is None:
        return "--"
    if math.isinf(value):
        return "inf"
    if math.isnan(value):
        return "nan"
    return ("{:.%df}" % digits).format(value)
