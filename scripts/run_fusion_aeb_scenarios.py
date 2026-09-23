#!/usr/bin/env python

"""Run AEB scenarios with radar target selection gated by YOLO camera fusion."""

from __future__ import print_function

import argparse
import json
import sys
import time
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from core.brake_permission_policy import (  # noqa: E402
    BrakePermissionContext,
    fusion_policy_from_config,
)
from core.fusion_brake_gate import FusionBrakeGateConfig  # noqa: E402
from core.headless_aeb_runtime import PolicyControlledAEBRuntime  # noqa: E402
from core.radar_aeb_pipeline import RadarAEBPipeline  # noqa: E402
from scripts.run_radar_aeb_scenarios import (  # noqa: E402
    DEFAULT_LOG_ROOT,
    DEFAULT_SENSOR_CONFIG,
    ScenarioRunner,
)
from ui.manual_control_common import (  # noqa: E402
    CameraSensor,
    RadarSensor,
    YoloDetector,
    camera_intrinsic,
    project_world_to_camera,
    pygame,
)


DEFAULT_SCENARIO_CONFIG = (
    AEB_ROOT / "configs" / "scenarios" / "suites" / "fusion_regression.yaml"
)


class HeadlessFusionAEB(PolicyControlledAEBRuntime):
    """Camera-radar fusion AEB runtime for batch scenario validation.

    Radar still owns object distance and relative velocity. YOLO supplies
    positive vehicle confirmation. The default configuration preserves the
    original hard camera gate; an optional safety policy can additionally allow
    a stable, well-supported, critical radar target in the central predicted
    path to trigger an emergency fallback.
    """

    def __init__(self, ego, config, carla_map, detector=None):
        if not pygame.get_init():
            pygame.init()
        self.ego = ego
        self.config = config
        self.camera = CameraSensor(
            ego,
            config.get("driver_camera", {}),
            gamma=float(config.get("camera_gamma", 2.2)),
        )
        self.radar = RadarSensor(ego, config.get("front_radar", {}))
        self._owns_detector = detector is None
        self.detector = detector or YoloDetector(config.get("model", {}))
        self.detector.reset_sequence()
        pipeline = RadarAEBPipeline(ego, config, carla_map)
        gate_config = FusionBrakeGateConfig.from_mapping(config.get("fusion", {}))
        brake_policy = fusion_policy_from_config(gate_config)
        super(HeadlessFusionAEB, self).__init__(
            ego,
            self.radar,
            pipeline,
            brake_policy=brake_policy,
        )
        # Public compatibility alias retained for integrations that inspect it.
        self.brake_gate = self.brake_policy.gate
        self.last_detections = []
        self.last_projection = None
        self.fusion_confirmed = False
        self.fusion_reason = "not_started"
        self.fusion_gate_action = "not_started"
        self.fusion_gate_reason = "not_started"
        self.radar_fallback_active = False
        self.target_path_offset_m = None

    def _permission_context(self, frame):
        self.last_detections = self.detector.infer(
            self.camera.latest_rgb,
            timestamp_s=self.camera.timestamp,
        )
        self.fusion_confirmed, self.fusion_reason = self._confirm_target(
            frame.target,
        )
        self.target_path_offset_m = (
            self.pipeline.distance_to_predicted_path(frame.target)
            if frame.target is not None
            else None
        )
        return BrakePermissionContext(
            radar_decision=frame.decision,
            target=frame.target,
            camera_confirmed=self.fusion_confirmed,
            camera_reason=self.fusion_reason,
            timestamp_s=frame.radar_timestamp_s,
            target_path_offset_m=self.target_path_offset_m,
        )

    def _record_permission_result(self, result):
        super(HeadlessFusionAEB, self)._record_permission_result(result)
        self.fusion_gate_action = result.action
        self.fusion_gate_reason = result.reason
        self.radar_fallback_active = result.radar_fallback_active

    def destroy(self):
        super(HeadlessFusionAEB, self).destroy()
        self.camera.destroy()
        if self._owns_detector:
            self.detector.destroy()
        else:
            self.detector.reset_sequence()

    def reset_control_state(self):
        super(HeadlessFusionAEB, self).reset_control_state()
        self.fusion_gate_action = "reset"
        self.fusion_gate_reason = "reset"
        self.radar_fallback_active = False
        self.target_path_offset_m = None

    def _confirm_target(self, target):
        self.last_projection = None
        if target is None:
            return False, "no_radar_target"
        if target.world_location is None:
            return False, "radar_target_without_world_location"
        if self.camera.latest_transform is None or self.camera.latest_rgb is None:
            return False, "camera_not_ready"
        if not self.last_detections:
            return False, "no_yolo_detection"

        intrinsic = camera_intrinsic(
            self.camera.width,
            self.camera.height,
            self.camera.fov,
        )
        pixel = project_world_to_camera(
            target.world_location,
            self.camera.latest_transform,
            intrinsic,
        )
        if pixel is None:
            return False, "radar_target_behind_camera"
        u, v = pixel
        self.last_projection = (float(u), float(v))
        if not (0.0 <= u < self.camera.width and 0.0 <= v < self.camera.height):
            return False, "radar_target_outside_image"

        for detection in self.last_detections:
            if not self._is_vehicle_detection(detection):
                continue
            if detection.x1 <= u <= detection.x2 and detection.y1 <= v <= detection.y2:
                return True, "radar_target_inside_yolo_box"
        return False, "radar_target_not_in_yolo_box"

    def _is_vehicle_detection(self, detection):
        allowed = self.detector.allowed_classes
        if allowed:
            return detection.class_name in set(str(name) for name in allowed)
        return str(detection.class_name).lower() in ("car", "vehicle")


class FusionScenarioRunner(ScenarioRunner):
    """Scenario runner that reuses one detector session across all repetitions."""

    def __init__(self, args):
        super(FusionScenarioRunner, self).__init__(args)
        self.shared_detector = YoloDetector(self.sensor_config.get("model", {}))

    def run(self):
        try:
            return super(FusionScenarioRunner, self).run()
        finally:
            self.shared_detector.destroy()

    def _make_system(self, ego):
        return HeadlessFusionAEB(
            ego,
            self.sensor_config,
            self.carla_map,
            detector=self.shared_detector,
        )

    def _write_metadata(self, run_directory, summaries):
        super(FusionScenarioRunner, self)._write_metadata(run_directory, summaries)
        metadata_path = Path(run_directory) / "run_metadata.json"
        with open(str(metadata_path)) as stream:
            metadata = json.load(stream)
        metadata["model_runtime"] = self.shared_detector.diagnostics()
        with open(str(metadata_path), "w") as stream:
            json.dump(metadata, stream, ensure_ascii=False, indent=2)

    def _wait_for_radar(self, system, world_frame):
        timeout_s = float(self.runner_config.get("sensor_wait_timeout_s", 1.0))
        deadline = time.monotonic() + timeout_s
        while True:
            radar_ready = (
                system.radar is None
                or (system.radar.frame is not None and system.radar.frame >= world_frame)
            )
            camera_ready = (
                system.camera is None
                or (
                    system.camera.frame is not None
                    and system.camera.frame >= world_frame
                )
            )
            if radar_ready and camera_ready:
                return
            if time.monotonic() >= deadline:
                return
            time.sleep(0.001)

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
        row = super(FusionScenarioRunner, self)._make_tick_row(
            scenario,
            snapshot,
            elapsed_s,
            ego,
            hazard_entry,
            scenario_actors,
            system,
            collision,
        )
        row["fusion_confirmed"] = int(system.fusion_confirmed)
        row["fusion_gate_action"] = system.fusion_gate_action
        row["fusion_gate_reason"] = system.fusion_gate_reason
        row["radar_fallback_active"] = int(system.radar_fallback_active)
        row["target_path_offset_m"] = (
            None
            if system.target_path_offset_m is None
            else round(float(system.target_path_offset_m), 4)
        )
        if system.fusion_confirmed:
            row["aeb_reason"] = "{}|fusion_confirmed".format(row["aeb_reason"])
        return row


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
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument(
        "--control-mode",
        choices=("deterministic", "physics"),
        default=None,
    )
    parser.add_argument("--scenario", action="append")
    parser.add_argument("--record-evidence", action="store_true")
    parser.add_argument("--keep-evidence-frames", action="store_true")
    parser.add_argument("--scenario-cooldown-s", type=float, default=1.0)
    parser.add_argument("--reload-world-every", type=int, default=1)
    parser.add_argument("--reload-world-wait-s", type=float, default=2.0)
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
    summaries = FusionScenarioRunner(args).run()
    failed = [summary for summary in summaries if summary["status"] != "PASS"]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
