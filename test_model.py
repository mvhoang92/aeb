#!/usr/bin/env python

"""Test YOLO model with manual_control.py on the left and camera detections on the right."""

from __future__ import print_function

import argparse

from two_panel_common import (
    CameraSensor,
    YoloDetector,
    add_common_args,
    draw_panel_label,
    draw_text_box,
    pygame,
    run_two_panel,
    scale_detection,
)


class ModelCameraPanel(object):
    """Right-side windshield camera with YOLO bounding boxes."""

    def __init__(self, manual_world, config, panel_width, panel_height, gamma, args):
        del args
        self.manual_world = manual_world
        self.config = config
        self.panel_width = panel_width
        self.panel_height = panel_height
        self.gamma = gamma
        self.camera_config = config.get("driver_camera", {})
        self.camera = None
        self._player_id = None
        self.detector = YoloDetector(config.get("model", {}))
        self.detections = []
        self._ensure_camera()

    def tick(self):
        self._ensure_camera()
        if self.camera is not None:
            self.detections = self.detector.infer(self.camera.latest_rgb)

    def _ensure_camera(self):
        player = self.manual_world.player
        if player is None:
            return
        if self.camera is not None and self._player_id == player.id:
            return
        self.destroy_camera()
        self.camera = CameraSensor(player, self.camera_config, self.gamma)
        self._player_id = player.id

    def render(self, display):
        panel_x = self.panel_width
        size = (self.panel_width, self.panel_height)
        if self.camera is not None:
            self.camera.render_image(display, (panel_x, 0), size)
        else:
            pygame.draw.rect(display, (10, 10, 10), pygame.Rect(panel_x, 0, *size))

        self._draw_detections(display, panel_x)
        pygame.draw.line(
            display,
            (240, 240, 240),
            (panel_x, 0),
            (panel_x, self.panel_height),
            2,
        )
        draw_panel_label(display, panel_x, "Camera + YOLO26n")
        self._draw_status(display, panel_x)

    def _draw_detections(self, display, panel_x):
        if self.camera is None:
            return
        image_size = (self.camera.width, self.camera.height)
        panel_size = (self.panel_width, self.panel_height)
        font = pygame.font.Font(pygame.font.get_default_font(), 16)
        for det in self.detections:
            rect = pygame.Rect(scale_detection(det, image_size, panel_size, panel_x))
            pygame.draw.rect(display, (40, 255, 120), rect, 2)
            label = "{} {:.2f}".format(det.class_name, det.confidence)
            text = font.render(label, True, (255, 255, 255))
            bg = pygame.Surface((text.get_width() + 8, text.get_height() + 6))
            bg.set_alpha(170)
            bg.fill((0, 0, 0))
            display.blit(bg, (rect.left, max(0, rect.top - bg.get_height())))
            display.blit(text, (rect.left + 4, max(0, rect.top - bg.get_height() + 3)))

    def _draw_status(self, display, panel_x):
        lines = [
            self.detector.status,
            "Detections: {}".format(len(self.detections)),
            "Model path: {}".format(self.config.get("model", {}).get("path", "--")),
        ]
        draw_text_box(display, lines, (panel_x + 12, self.panel_height - 92), width=520)

    def destroy_camera(self):
        if self.camera is not None:
            self.camera.destroy()
            self.camera = None
            self._player_id = None

    def destroy(self):
        self.destroy_camera()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        run_two_panel(args, ModelCameraPanel, "AEB model test - manual_control extended")
    except KeyboardInterrupt:
        print("\nĐã dừng bởi người dùng.")


if __name__ == "__main__":
    main()
