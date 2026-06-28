#!/usr/bin/env python

"""Run AEB scenarios with radar target selection gated by YOLO camera fusion."""

from __future__ import print_function

import argparse
import sys
import time
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from control.brake import AEBDecision, AEBState, apply_brake_override  # noqa: E402
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


class HeadlessFusionAEB(object):
    """Camera-radar fusion AEB runtime for batch scenario validation.

    Radar still owns object distance and relative velocity. YOLO only confirms
    that the selected radar target projects into a camera car box before the
    binary brake command is allowed through.
    """

    def __init__(self, ego, config, carla_map):
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
        self.detector = YoloDetector(config.get("model", {}))
        self.pipeline = RadarAEBPipeline(ego, config, carla_map)
        self.decision = self.pipeline.decision
        self.aeb_override_active = False
        self.last_detections = []
        self.last_projection = None
        self.fusion_confirmed = False
        self.fusion_reason = "not_started"
        self._last_confirmed_at = None

    def tick(self):
        frame = self.pipeline.update(self.radar)
        self.last_detections = self.detector.infer(self.camera.latest_rgb)
        self.fusion_confirmed, self.fusion_reason = self._confirm_target(
            frame.target,
        )
        if self.fusion_confirmed:
            self._last_confirmed_at = time.monotonic()
        self.decision = self._fusion_gated_decision(frame.decision)

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
        self.camera.destroy()

    def reset_control_state(self):
        self.pipeline.reset_control_state()
        self.decision = self.pipeline.decision
        self.aeb_override_active = False
        self._last_confirmed_at = None

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

    def _fusion_gated_decision(self, radar_decision):
        if radar_decision.state != AEBState.BRAKE:
            return radar_decision
        if self._recently_confirmed():
            return radar_decision
        return AEBDecision(
            state=AEBState.RELEASE,
            brake=0.0,
            throttle=0.0,
            ttc_s=radar_decision.ttc_s,
            target_distance_m=radar_decision.target_distance_m,
            relative_velocity_mps=radar_decision.relative_velocity_mps,
            should_override=False,
            reason="fusion_blocked_brake:{}".format(self.fusion_reason),
            required_distance_m=radar_decision.required_distance_m,
            distance_margin_m=radar_decision.distance_margin_m,
        )

    def _recently_confirmed(self):
        if self.fusion_confirmed:
            return True
        hold_s = float(
            self.config.get("fusion", {}).get(
                "confirmation_hold_s",
                0.35,
            )
        )
        if self._last_confirmed_at is None:
            return False
        return time.monotonic() - self._last_confirmed_at <= hold_s


class FusionScenarioRunner(ScenarioRunner):
    def _make_system(self, ego):
        return HeadlessFusionAEB(
            ego,
            self.sensor_config,
            self.carla_map,
        )

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
        if system.fusion_confirmed:
            row["aeb_reason"] = "{}|fusion_confirmed".format(row["aeb_reason"])
        elif system.decision.state == AEBState.RELEASE and str(row["aeb_reason"]).startswith(
            "fusion_blocked_brake"
        ):
            row["aeb_reason"] = system.decision.reason
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
