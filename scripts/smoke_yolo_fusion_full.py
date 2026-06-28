#!/usr/bin/env python

"""Smoke test YOLO, camera-radar fusion and radar-only AEB end to end.

This script is intentionally small and operational: it connects to a running
CARLA server, spawns a Tesla Model 3 ego plus one lead vehicle, checks that the
configured YOLO model detects the car, checks that radar points can be projected
into the YOLO box, then runs one radar-only AEB validation scenario.
"""

from __future__ import print_function

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = AEB_ROOT.parent
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from scripts.run_radar_aeb_scenarios import (  # noqa: E402
    actor_distances,
)
from ui.manual_control_common import (  # noqa: E402
    CameraSensor,
    RadarSensor,
    YoloDetector,
    camera_intrinsic,
    carla,
    load_yaml,
    project_world_to_camera,
    pygame,
)


DEFAULT_SENSOR_CONFIG = AEB_ROOT / "configs" / "sensors.yaml"
DEFAULT_SCENARIO_CONFIG = (
    AEB_ROOT / "configs" / "scenarios" / "suites" / "radar_only_regression.yaml"
)
DEFAULT_OUTPUT = AEB_ROOT / "logs" / "smoke_yolo_fusion_full_latest.json"
DEFAULT_DEBUG_DIR = AEB_ROOT / "logs" / "smoke_debug"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--sensor-config", type=Path, default=DEFAULT_SENSOR_CONFIG)
    parser.add_argument("--scenario-config", type=Path, default=DEFAULT_SCENARIO_CONFIG)
    parser.add_argument("--map-name", default="Town04")
    parser.add_argument("--spawn-index", type=int, default=81)
    parser.add_argument("--target-gap-m", type=float, default=35.0)
    parser.add_argument("--warmup-ticks", type=int, default=12)
    parser.add_argument("--capture-ticks", type=int, default=16)
    parser.add_argument("--scenario", default="ccrs_60_demo_150")
    parser.add_argument("--run-id", default="smoke_full_latest")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--debug-dir", type=Path, default=DEFAULT_DEBUG_DIR)
    parser.add_argument("--load-map", action="store_true")
    parser.add_argument(
        "--skip-full",
        action="store_true",
        help="Only run YOLO/fusion smoke, skip radar-AEB scenario batch.",
    )
    return parser.parse_args()


def actor_blueprint(world, blueprint_id, role_name):
    blueprint = world.get_blueprint_library().find(blueprint_id)
    if blueprint.has_attribute("role_name"):
        blueprint.set_attribute("role_name", role_name)
    if blueprint.has_attribute("color"):
        colors = blueprint.get_attribute("color").recommended_values
        if colors:
            blueprint.set_attribute("color", colors[0])
    return blueprint


def destroy_actor(actor):
    if actor is None:
        return
    try:
        actor.destroy()
    except RuntimeError:
        pass


def wait_for_sensor_frames(world, camera, radar, ticks, timeout_s):
    deadline = time.monotonic() + float(timeout_s)
    for _ in range(max(1, int(ticks))):
        frame = world.tick()
        while time.monotonic() < deadline:
            camera_ready = camera.frame is not None and camera.frame >= frame
            radar_ready = radar.frame is not None and radar.frame >= frame
            if camera_ready and radar_ready:
                break
            time.sleep(0.002)
        if time.monotonic() >= deadline:
            break


def detection_center(det):
    return (0.5 * (det.x1 + det.x2), 0.5 * (det.y1 + det.y2))


def match_radar_to_detections(camera, radar, detections, fusion_config, radar_config):
    if camera.latest_transform is None:
        return [], {}
    intrinsic = camera_intrinsic(camera.width, camera.height, camera.fov)
    projected = []
    min_forward = float(fusion_config.get("min_radar_forward_distance_m", 1.5))
    max_range = float(radar_config.get("range", 100.0))
    max_lateral = float(fusion_config.get("max_lateral_offset_m", 2.4))
    min_z = float(fusion_config.get("min_radar_z_up_m", -0.35))
    max_z = float(fusion_config.get("max_radar_z_up_m", 2.5))
    for point in radar.points:
        if point.x_forward_m < min_forward or point.x_forward_m > max_range:
            continue
        if abs(point.y_right_m) > max_lateral:
            continue
        if point.z_up_m < min_z or point.z_up_m > max_z:
            continue
        pixel = project_world_to_camera(
            point.world_location,
            camera.latest_transform,
            intrinsic,
        )
        if pixel is None:
            continue
        u, v = pixel
        if 0 <= u < camera.width and 0 <= v < camera.height:
            projected.append((point, u, v))

    matches = {}
    for index, det in enumerate(detections):
        inside = [
            item
            for item in projected
            if det.x1 <= item[1] <= det.x2 and det.y1 <= item[2] <= det.y2
        ]
        if inside:
            matches[index] = min(inside, key=lambda item: item[0].x_forward_m)
    return projected, matches


def save_debug_image(args, camera, detections, projected, matches):
    if camera.latest_rgb is None:
        return None
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    args.debug_dir.mkdir(parents=True, exist_ok=True)
    image = camera.latest_rgb.copy()
    for _, u, v in projected:
        cv2.circle(image, (int(round(u)), int(round(v))), 3, (60, 220, 255), -1)
    for index, det in enumerate(detections):
        color = (60, 255, 80) if index in matches else (255, 220, 80)
        cv2.rectangle(
            image,
            (int(round(det.x1)), int(round(det.y1))),
            (int(round(det.x2)), int(round(det.y2))),
            color,
            2,
        )
        cv2.putText(
            image,
            "{} {:.2f}".format(det.class_name, det.confidence),
            (int(round(det.x1)), max(20, int(round(det.y1)) - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
    output_path = args.debug_dir / "{}_yolo_fusion.png".format(args.run_id)
    cv2.imwrite(str(output_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    return str(output_path)


def run_yolo_fusion_smoke(args, config):
    client = carla.Client(args.host, args.port)
    client.set_timeout(args.timeout)
    world = client.get_world()
    current_map = world.get_map().name.split("/")[-1]
    if current_map != args.map_name:
        if not args.load_map:
            raise RuntimeError(
                "CARLA đang ở {}, cần {}. Thêm --load-map nếu muốn tự chuyển map.".format(
                    current_map,
                    args.map_name,
                )
            )
        world = client.load_world(args.map_name)

    original_settings = world.get_settings()
    ego = None
    target = None
    camera = None
    radar = None
    pygame.init()
    try:
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.05
        world.apply_settings(settings)
        world.tick()

        carla_map = world.get_map()
        spawn_points = carla_map.get_spawn_points()
        if args.spawn_index < 0 or args.spawn_index >= len(spawn_points):
            raise RuntimeError("spawn-index không hợp lệ: {}".format(args.spawn_index))

        ego_bp = actor_blueprint(
            world,
            config.get("ego", {}).get("blueprint", "vehicle.tesla.model3"),
            "smoke_ego",
        )
        target_bp = actor_blueprint(world, "vehicle.audi.tt", "smoke_target")
        ego = world.try_spawn_actor(ego_bp, spawn_points[args.spawn_index])
        if ego is None:
            raise RuntimeError("Không spawn được ego tại index {}".format(args.spawn_index))
        ego.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
        world.tick()

        ego_transform = ego.get_transform()
        ego_location = ego_transform.location
        ego_forward = ego_transform.get_forward_vector()
        approximate_center_gap = (
            float(args.target_gap_m)
            + float(ego.bounding_box.extent.x)
            + 2.0
        )
        target_transform = carla.Transform(
            carla.Location(
                x=ego_location.x + ego_forward.x * approximate_center_gap,
                y=ego_location.y + ego_forward.y * approximate_center_gap,
                z=ego_location.z + 0.35,
            ),
            ego_transform.rotation,
        )
        target = world.try_spawn_actor(target_bp, target_transform)
        if target is None:
            fallback_index = (args.spawn_index + 1) % len(spawn_points)
            target = world.try_spawn_actor(target_bp, spawn_points[fallback_index])
        if target is None:
            raise RuntimeError("Không spawn được target smoke")
        # Sau khi spawn mới biết chính xác extent của xe mục tiêu; đặt lại để
        # bumper gap đúng với tham số smoke test.
        exact_center_gap = (
            float(args.target_gap_m)
            + float(ego.bounding_box.extent.x)
            + float(target.bounding_box.extent.x)
        )
        target.set_simulate_physics(False)
        exact_target_transform = carla.Transform(
            carla.Location(
                x=ego_location.x + ego_forward.x * exact_center_gap,
                y=ego_location.y + ego_forward.y * exact_center_gap,
                z=ego_location.z + 0.35,
            ),
            ego_transform.rotation,
        )
        target.set_transform(exact_target_transform)
        world.tick()
        target.set_transform(exact_target_transform)
        target.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
        world.tick()
        center_distance, bumper_gap, lateral_offset = actor_distances(ego, target)

        camera = CameraSensor(ego, config.get("driver_camera", {}), 2.2)
        radar = RadarSensor(ego, config.get("front_radar", {}))
        detector = YoloDetector(config.get("model", {}))

        wait_for_sensor_frames(
            world,
            camera,
            radar,
            args.warmup_ticks,
            args.timeout,
        )
        if camera.latest_rgb is None:
            raise RuntimeError("Camera không trả frame")
        if radar.frame is None:
            raise RuntimeError("Radar không trả frame")

        detections = []
        for _ in range(max(1, int(args.capture_ticks))):
            frame = world.tick()
            wait_for_sensor_frames(world, camera, radar, 1, args.timeout)
            detections = detector.infer(camera.latest_rgb)
            if detections:
                break

        projected, matches = match_radar_to_detections(
            camera,
            radar,
            detections,
            config.get("fusion", {}),
            config.get("front_radar", {}),
        )
        debug_image = save_debug_image(args, camera, detections, projected, matches)
        best_detection = max(detections, key=lambda det: det.confidence) if detections else None
        best_match = matches.get(detections.index(best_detection)) if best_detection else None

        return {
            "status": "PASS" if detections and matches else "FAIL",
            "detector_status": detector.status,
            "camera_frame": camera.frame,
            "radar_frame": radar.frame,
            "raw_radar_points": len(radar.points),
            "actual_center_distance_m": (
                None if center_distance is None else round(float(center_distance), 3)
            ),
            "actual_bumper_gap_m": (
                None if bumper_gap is None else round(float(bumper_gap), 3)
            ),
            "actual_lateral_offset_m": (
                None if lateral_offset is None else round(float(lateral_offset), 3)
            ),
            "ego_location": [
                round(float(ego.get_location().x), 3),
                round(float(ego.get_location().y), 3),
                round(float(ego.get_location().z), 3),
            ],
            "target_location": [
                round(float(target.get_location().x), 3),
                round(float(target.get_location().y), 3),
                round(float(target.get_location().z), 3),
            ],
            "detections": len(detections),
            "projected_radar_points": len(projected),
            "matched_boxes": len(matches),
            "debug_image": debug_image,
            "best_detection": (
                None
                if best_detection is None
                else {
                    "class_name": best_detection.class_name,
                    "confidence": round(float(best_detection.confidence), 4),
                    "bbox": [
                        round(float(best_detection.x1), 1),
                        round(float(best_detection.y1), 1),
                        round(float(best_detection.x2), 1),
                        round(float(best_detection.y2), 1),
                    ],
                    "center": [
                        round(detection_center(best_detection)[0], 1),
                        round(detection_center(best_detection)[1], 1),
                    ],
                }
            ),
            "best_match": (
                None
                if best_match is None
                else {
                    "distance_m": round(float(best_match[0].x_forward_m), 3),
                    "lateral_m": round(float(best_match[0].y_right_m), 3),
                    "relative_velocity_mps": round(
                        float(best_match[0].relative_velocity_mps),
                        3,
                    ),
                    "pixel": [
                        round(float(best_match[1]), 1),
                        round(float(best_match[2]), 1),
                    ],
                }
            ),
        }
    finally:
        if radar is not None:
            radar.destroy()
        if camera is not None:
            camera.destroy()
        destroy_actor(target)
        destroy_actor(ego)
        world.apply_settings(original_settings)
        try:
            world.tick()
        except RuntimeError:
            pass
        pygame.quit()


def run_full_scenario(args):
    command = [
        str(PROJECT_ROOT / "venv" / "bin" / "python"),
        str(AEB_ROOT / "scripts" / "run_radar_aeb_scenarios.py"),
        "--sensor-config",
        str(args.sensor_config),
        "--scenario-config",
        str(args.scenario_config),
        "--control-mode",
        "physics",
        "--run-id",
        args.run_id,
        "--scenario",
        args.scenario,
    ]
    result = subprocess.run(
        command,
        cwd=str(AEB_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    summary_path = AEB_ROOT / "logs" / args.run_id / "summary.json"
    summary = None
    if summary_path.exists():
        with summary_path.open("r", encoding="utf-8") as stream:
            summary = json.load(stream)
    return {
        "status": "PASS" if result.returncode == 0 and summary else "FAIL",
        "returncode": result.returncode,
        "log_dir": str(AEB_ROOT / "logs" / args.run_id),
        "stdout_tail": result.stdout.splitlines()[-12:],
        "summary": summary,
    }


def main():
    args = parse_args()
    config = load_yaml(args.sensor_config)
    report = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sensor_config": str(args.sensor_config),
        "scenario_config": str(args.scenario_config),
    }
    report["yolo_fusion"] = run_yolo_fusion_smoke(args, config)
    if not args.skip_full:
        report["full_radar_aeb"] = run_full_scenario(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    yolo_ok = report["yolo_fusion"]["status"] == "PASS"
    full_ok = args.skip_full or report.get("full_radar_aeb", {}).get("status") == "PASS"
    return 0 if yolo_ok and full_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
