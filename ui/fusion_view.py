#!/usr/bin/env python

"""Test camera-radar fusion with manual_control.py on the left."""

from __future__ import print_function

import argparse
import math
import sys
from pathlib import Path

AEB_ROOT = Path(__file__).resolve().parents[1]
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from ui.manual_control_common import (
    CameraSensor,
    RadarSensor,
    YoloDetector,
    add_common_args,
    camera_intrinsic,
    compute_ttc,
    draw_panel_label,
    draw_text_box,
    format_float,
    project_world_to_camera,
    pygame,
    run_two_panel,
    scale_detection,
    select_front_radar_target,
)


class FusionPanel(object):
    """Right-side windshield camera with YOLO boxes and radar measurements."""

    def __init__(self, manual_world, config, panel_width, panel_height, gamma, args):
        del args
        self.manual_world = manual_world
        self.config = config
        self.panel_width = panel_width
        self.panel_height = panel_height
        self.gamma = gamma
        self.camera_config = config.get("driver_camera", {})
        self.radar_config = config.get("front_radar", {})
        self.fusion_config = config.get("fusion", {})
        self.brake_config = config.get("brake", {})
        self.camera = None
        self.radar = None
        self._player_id = None
        self.detector = YoloDetector(config.get("model", {}))
        self.detections = []
        self.projected_radar = []
        self.matches = {}
        self._ensure_sensors()

    def tick(self):
        self._ensure_sensors()
        if self.camera is not None:
            self.detections = self.detector.infer(self.camera.latest_rgb)
        self.projected_radar = self._project_radar_points()
        self.matches = self._match_radar_to_boxes()

    def _ensure_sensors(self):
        player = self.manual_world.player
        if player is None:
            return
        if self.camera is not None and self.radar is not None and self._player_id == player.id:
            return
        self.destroy_sensors()
        self.camera = CameraSensor(player, self.camera_config, self.gamma)
        self.radar = RadarSensor(player, self.radar_config)
        self._player_id = player.id

    def render(self, display):
        panel_x = self.panel_width
        size = (self.panel_width, self.panel_height)
        if self.camera is not None:
            self.camera.render_image(display, (panel_x, 0), size)
        else:
            pygame.draw.rect(display, (10, 10, 10), pygame.Rect(panel_x, 0, *size))

        if bool(self.fusion_config.get("draw_projected_radar_points", True)):
            self._draw_projected_radar(display, panel_x)
        self._draw_detections(display, panel_x)
        pygame.draw.line(
            display,
            (240, 240, 240),
            (panel_x, 0),
            (panel_x, self.panel_height),
            2,
        )
        draw_panel_label(display, panel_x, "Camera + YOLO26n + radar")
        self._draw_status(display, panel_x)

    def _project_radar_points(self):
        if self.camera is None or self.radar is None:
            return []
        if self.camera.latest_transform is None:
            return []
        intrinsic = camera_intrinsic(self.camera.width, self.camera.height, self.camera.fov)
        projected = []
        for point in self.radar.points:
            if not self._valid_front_radar_point(point):
                continue
            pixel = project_world_to_camera(
                point.world_location,
                self.camera.latest_transform,
                intrinsic,
            )
            if pixel is None:
                continue
            u, v = pixel
            if 0 <= u < self.camera.width and 0 <= v < self.camera.height:
                projected.append((point, u, v))
        return projected

    def _valid_front_radar_point(self, point):
        return (
            point.x_forward_m
            >= float(self.fusion_config.get("min_radar_forward_distance_m", 1.5))
            and point.x_forward_m <= float(self.radar_config.get("range", 100.0))
            and abs(point.y_right_m)
            <= float(self.fusion_config.get("max_lateral_offset_m", 2.4))
            and float(self.fusion_config.get("min_radar_z_up_m", -0.35))
            <= point.z_up_m
            <= float(self.fusion_config.get("max_radar_z_up_m", 2.5))
        )

    def _match_radar_to_boxes(self):
        matches = {}
        for index, det in enumerate(self.detections):
            inside = [
                item
                for item in self.projected_radar
                if det.x1 <= item[1] <= det.x2 and det.y1 <= item[2] <= det.y2
            ]
            if not inside:
                continue
            point, u, v = min(inside, key=lambda item: item[0].x_forward_m)
            matches[index] = (point, u, v)
        return matches

    def _draw_projected_radar(self, display, panel_x):
        if self.camera is None:
            return
        scale_x = float(self.panel_width) / float(self.camera.width)
        scale_y = float(self.panel_height) / float(self.camera.height)
        for point, u, v in self.projected_radar:
            x = int(panel_x + u * scale_x)
            y = int(v * scale_y)
            color = self._ttc_color(point)
            pygame.draw.circle(display, color, (x, y), 3)

    def _draw_detections(self, display, panel_x):
        if self.camera is None:
            return
        image_size = (self.camera.width, self.camera.height)
        panel_size = (self.panel_width, self.panel_height)
        font = pygame.font.Font(pygame.font.get_default_font(), 16)

        for index, det in enumerate(self.detections):
            rect = pygame.Rect(scale_detection(det, image_size, panel_size, panel_x))
            match = self.matches.get(index)
            color = (40, 255, 120) if match is not None else (255, 210, 70)
            pygame.draw.rect(display, color, rect, 2)

            label = "{} {:.2f}".format(det.class_name, det.confidence)
            if match is not None:
                point = match[0]
                ttc = compute_ttc(point.x_forward_m, point.relative_velocity_mps)
                label += " | d={}m rv={}m/s ttc={}s".format(
                    format_float(point.x_forward_m, 1),
                    format_float(point.relative_velocity_mps, 1),
                    format_float(ttc, 2),
                )

            text = font.render(label, True, (255, 255, 255))
            bg = pygame.Surface((text.get_width() + 8, text.get_height() + 6))
            bg.set_alpha(180)
            bg.fill((0, 0, 0))
            y = max(0, rect.top - bg.get_height())
            display.blit(bg, (rect.left, y))
            display.blit(text, (rect.left + 4, y + 3))

    def _draw_status(self, display, panel_x):
        radar_points = len(self.radar.points) if self.radar is not None else 0
        target = None
        if self.radar is not None:
            target = select_front_radar_target(
                self.radar.points,
                float(self.fusion_config.get("max_lateral_offset_m", 2.4)),
                min_z_up_m=float(self.fusion_config.get("min_radar_z_up_m", -0.35)),
                max_z_up_m=float(self.fusion_config.get("max_radar_z_up_m", 2.5)),
                min_forward_distance_m=float(
                    self.fusion_config.get("min_radar_forward_distance_m", 1.5)
                ),
                max_range_m=float(self.radar_config.get("range", 100.0)),
            )

        lines = [
            self.detector.status,
            "YOLO boxes: {}".format(len(self.detections)),
            "Radar points: {}".format(radar_points),
            "Projected radar: {}".format(len(self.projected_radar)),
            "Matched boxes: {}".format(len(self.matches)),
        ]
        if target is not None:
            ttc = compute_ttc(target.x_forward_m, target.relative_velocity_mps)
            lines += [
                "Front target: d={}m rv={}m/s TTC={}s".format(
                    format_float(target.x_forward_m, 1),
                    format_float(target.relative_velocity_mps, 1),
                    format_float(ttc, 2),
                )
            ]
        else:
            lines.append("Front target: --")
        draw_text_box(display, lines, (panel_x + 12, self.panel_height - 152), width=620)

    def _ttc_color(self, point):
        ttc = compute_ttc(point.x_forward_m, point.relative_velocity_mps)
        if ttc <= float(self.brake_config.get("brake_ttc_s", 1.8)):
            return 255, 80, 60
        if ttc <= float(self.brake_config.get("warning_ttc_s", 3.0)):
            return 70, 140, 255
        return 90, 230, 120

    def destroy_sensors(self):
        if self.radar is not None:
            self.radar.destroy()
            self.radar = None
        if self.camera is not None:
            self.camera.destroy()
            self.camera = None
        self._player_id = None

    def destroy(self):
        self.destroy_sensors()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        run_two_panel(args, FusionPanel, "AEB fusion test - manual_control extended")
    except KeyboardInterrupt:
        print("\nĐã dừng bởi người dùng.")


if __name__ == "__main__":
    main()
