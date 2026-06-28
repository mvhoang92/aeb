#!/usr/bin/env python

"""Test front radar with manual_control.py on the left and bird-eye radar on the right."""

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
    add_common_args,
    camera_intrinsic,
    carla,
    compute_ttc,
    config_value,
    draw_panel_label,
    display_size_from_args,
    format_float,
    load_or_get_world,
    load_yaml,
    manual_control,
    prepare_manual_control_args,
    pygame,
    project_world_to_camera,
    select_front_radar_target,
    transform_from_config,
)


class RadarBirdEyePanel(object):
    """Right-side bird-eye visualization of the front radar sweep."""

    def __init__(self, manual_world, config, panel_width, panel_height, gamma, args):
        del gamma, args
        self.manual_world = manual_world
        self.config = config
        self.panel_width = panel_width
        self.panel_height = panel_height
        self.radar_config = config.get("front_radar", {})
        self.fusion_config = config.get("fusion", {})
        self.brake_config = config.get("brake", {})
        self.radar = None
        self._player_id = None
        self._ensure_radar()

    def tick(self):
        self._ensure_radar()

    def _ensure_radar(self):
        player = self.manual_world.player
        if player is None:
            return
        if self.radar is not None and self._player_id == player.id:
            return
        self.destroy()
        self.radar = RadarSensor(player, self.radar_config)
        self._player_id = player.id

    def render(self, display):
        panel_x = self.panel_width
        rect = pygame.Rect(panel_x, 0, self.panel_width, self.panel_height)
        pygame.draw.rect(display, (8, 10, 12), rect)
        self._draw_grid(display, panel_x)
        self._draw_radar_points(display, panel_x)
        pygame.draw.line(
            display,
            (240, 240, 240),
            (panel_x, 0),
            (panel_x, self.panel_height),
            2,
        )
        draw_panel_label(display, panel_x, "AEB front radar bird-eye")
        self._draw_info(display, panel_x)

    def _draw_grid(self, display, panel_x, view_range_m=None):
        range_m = self._view_range(view_range_m)
        horizontal_fov = float(self.radar_config.get("horizontal_fov", 30.0))
        scale = self._scale(range_m, horizontal_fov)
        origin = self._origin(panel_x, scale)

        pygame.draw.polygon(
            display,
            (22, 42, 50),
            [origin]
            + [
                self._to_screen(panel_x, distance, offset, scale)
                for distance, offset in self._fan_edge_points(range_m, horizontal_fov)
            ],
        )

        step_m = self._grid_step(range_m)
        for distance in range(step_m, int(range_m) + 1, step_m):
            points = [
                self._to_screen(
                    panel_x,
                    distance,
                    distance * math.sin(math.radians(angle)),
                    scale,
                )
                for angle in range(
                    -int(horizontal_fov / 2.0),
                    int(horizontal_fov / 2.0) + 1,
                    2,
                )
            ]
            if len(points) > 1:
                pygame.draw.lines(display, (70, 90, 95), False, points, 1)
            label = "{}m".format(distance)
            self._draw_small_text(display, label, (panel_x + 18, origin[1] - distance * scale))

        for sign in (-1, 1):
            end_distance = range_m
            end_offset = sign * range_m * math.sin(math.radians(horizontal_fov / 2.0))
            pygame.draw.line(
                display,
                (90, 120, 125),
                origin,
                self._to_screen(panel_x, end_distance, end_offset, scale),
                1,
            )

        self._draw_ego_outline(display, panel_x, scale)
        pygame.draw.circle(display, (255, 255, 255), origin, 5)
        pygame.draw.circle(display, (20, 20, 20), origin, 3)

    def _draw_radar_points(self, display, panel_x, view_range_m=None):
        if self.radar is None:
            return
        range_m = self._view_range(view_range_m)
        horizontal_fov = float(self.radar_config.get("horizontal_fov", 30.0))
        scale = self._scale(range_m, horizontal_fov)
        target = self._selected_target()

        for point in self.radar.points:
            if not self._raw_point_in_view(point, view_range_m):
                continue
            screen = self._to_screen(panel_x, point.x_forward_m, point.y_right_m, scale)
            color = self._point_color(point)
            radius = 7 if point is target else 3
            pygame.draw.circle(display, color, screen, radius)
            if point is target:
                pygame.draw.circle(display, (255, 255, 255), screen, radius + 3, 1)

    def _draw_info(self, display, panel_x):
        if self.radar is None:
            self._draw_info_card(
                display,
                panel_x + 16,
                48,
                310,
                "RADAR",
                [("Status", "waiting")],
            )
            self._draw_color_legend(display, panel_x)
            return

        target = self._selected_target()
        visible_raw_points = [
            point for point in self.radar.points if self._raw_point_in_view(point)
        ]
        filtered_points = [
            point for point in self.radar.points if self._valid_front_point(point)
        ]

        x = panel_x + 16
        width = 330
        next_y = self._draw_info_card(
            display,
            x,
            48,
            width,
            "SCAN",
            [
                ("Raw points", len(self.radar.points)),
                ("Shown points", len(visible_raw_points)),
                ("AEB candidates", len(filtered_points)),
                ("Range", "{} m".format(self.radar_config.get("range", 100))),
                ("HFOV", "{} deg".format(self.radar_config.get("horizontal_fov", 30))),
                ("VFOV", "{} deg".format(self.radar_config.get("vertical_fov", 6))),
            ],
        )

        if target is None:
            target_rows = [("Target", "--"), ("TTC", "inf")]
        else:
            ttc = compute_ttc(target.x_forward_m, target.relative_velocity_mps)
            target_rows = [
                ("Target", self._ttc_label(ttc)),
                ("Distance", "{} m".format(format_float(target.x_forward_m, 1))),
                ("Lateral", "{} m".format(format_float(target.y_right_m, 1))),
                ("Rel v", "{} m/s".format(format_float(target.relative_velocity_mps, 1))),
                ("TTC", "{} s".format(format_float(ttc, 2))),
            ]
        self._draw_info_card(display, x, next_y + 10, width, "TARGET", target_rows)
        self._draw_color_legend(display, panel_x)

    def _selected_target(self):
        if self.radar is None:
            return None
        return select_front_radar_target(
            self.radar.points,
            float(self.fusion_config.get("max_lateral_offset_m", 2.4)),
            min_z_up_m=float(self.fusion_config.get("min_radar_z_up_m", -0.35)),
            max_z_up_m=float(self.fusion_config.get("max_radar_z_up_m", 2.5)),
            min_forward_distance_m=float(
                self.fusion_config.get("min_radar_forward_distance_m", 1.5)
            ),
            max_range_m=float(self.radar_config.get("range", 100.0)),
        )

    def _draw_info_card(self, display, x, y, width, title, rows):
        title_font = pygame.font.Font(pygame.font.get_default_font(), 15)
        row_font = pygame.font.Font(pygame.font.get_default_font(), 15)
        row_height = 22
        height = 38 + len(rows) * row_height
        card = pygame.Surface((width, height), pygame.SRCALPHA)
        card.fill((0, 0, 0, 172))
        pygame.draw.rect(card, (48, 74, 82, 210), card.get_rect(), 1)

        title_surface = title_font.render(str(title), True, (230, 244, 246))
        card.blit(title_surface, (12, 10))
        pygame.draw.line(card, (60, 90, 96), (12, 32), (width - 12, 32), 1)

        for index, row in enumerate(rows):
            label, value = row
            row_y = 39 + index * row_height
            label_surface = row_font.render(str(label), True, (158, 174, 178))
            value_surface = row_font.render(str(value), True, (245, 248, 248))
            card.blit(label_surface, (12, row_y))
            card.blit(value_surface, (width - value_surface.get_width() - 12, row_y))

        display.blit(card, (x, y))
        return y + height

    def _draw_color_legend(self, display, panel_x):
        width = 330
        x = panel_x + self.panel_width - width - 18
        rows = self._color_legend_rows()
        card_height = 40 + len(rows) * 18
        y = self.panel_height - card_height - 20

        card = pygame.Surface((width, card_height), pygame.SRCALPHA)
        card.fill((0, 0, 0, 150))
        pygame.draw.rect(card, (48, 74, 82, 200), card.get_rect(), 1)
        font = pygame.font.Font(pygame.font.get_default_font(), 15)
        title = font.render("COLOR", True, (230, 244, 246))
        card.blit(title, (12, 10))
        for index, (color, text) in enumerate(rows):
            row_y = 36 + index * 18
            pygame.draw.circle(card, color, (20, row_y + 7), 5)
            if text == "large dot = AEB target":
                pygame.draw.circle(card, (255, 255, 255), (20, row_y + 7), 8, 1)
            surface = font.render(text, True, (230, 236, 236))
            card.blit(surface, (34, row_y))
        display.blit(card, (x, y))

    def _color_legend_rows(self):
        return [
            ((255, 80, 60), "danger: TTC <= brake"),
            ((70, 140, 255), "risk: TTC <= warning"),
            ((90, 230, 120), "safe / TTC is inf"),
            ((255, 255, 255), "large dot = AEB target"),
        ]

    def _point_color(self, point):
        return self._ttc_color(point)

    def _ttc_color(self, point):
        ttc = compute_ttc(point.x_forward_m, point.relative_velocity_mps)
        if ttc <= self._brake_ttc_threshold():
            return 255, 80, 60
        if ttc <= self._warning_ttc_threshold():
            return 70, 140, 255
        return 90, 230, 120

    def _ttc_label(self, ttc):
        if ttc <= self._brake_ttc_threshold():
            return "danger"
        if ttc <= self._warning_ttc_threshold():
            return "risk"
        if math.isfinite(ttc):
            return "safe"
        return "safe / no closing"

    def _warning_ttc_threshold(self):
        return float(self.brake_config.get("warning_ttc_s", 3.0))

    def _brake_ttc_threshold(self):
        return float(self.brake_config.get("brake_ttc_s", 1.8))

    def _fan_edge_points(self, range_m, horizontal_fov):
        points = []
        for angle in range(
            -int(horizontal_fov / 2.0),
            int(horizontal_fov / 2.0) + 1,
            2,
        ):
            offset = range_m * math.sin(math.radians(angle))
            distance = range_m * math.cos(math.radians(angle))
            points.append((distance, offset))
        return points

    def _origin(self, panel_x, scale=None):
        origin_x = int(panel_x + self.panel_width / 2.0)
        if scale is None:
            return origin_x, int(self.panel_height - 54)
        bottom_margin_px = 30
        origin_y = self.panel_height - bottom_margin_px - self._rear_context_m() * scale
        return origin_x, int(origin_y)

    def _scale(self, range_m, horizontal_fov):
        max_width = 2.0 * range_m * math.sin(math.radians(horizontal_fov / 2.0))
        top_margin_px = 115.0
        bottom_margin_px = 30.0
        vertical_span_m = range_m + self._rear_context_m()
        scale_y = (self.panel_height - top_margin_px - bottom_margin_px) / max(
            vertical_span_m,
            1.0,
        )
        scale_x = (self.panel_width - 100.0) / max(max_width, 1.0)
        return min(scale_x, scale_y)

    def _to_screen(self, panel_x, x_forward, y_right, scale):
        origin = self._origin(panel_x, scale)
        return int(origin[0] + y_right * scale), int(origin[1] - x_forward * scale)

    def _draw_ego_outline(self, display, panel_x, scale):
        player = self.manual_world.player
        if player is None:
            return

        bbox = player.bounding_box
        radar_location = self.radar_config.get("location", {})
        radar_x = float(radar_location.get("x", 0.0))
        radar_y = float(radar_location.get("y", 0.0))

        min_x = bbox.location.x - bbox.extent.x - radar_x
        max_x = bbox.location.x + bbox.extent.x - radar_x
        min_y = bbox.location.y - bbox.extent.y - radar_y
        max_y = bbox.location.y + bbox.extent.y - radar_y
        corners = [
            self._to_screen(panel_x, min_x, min_y, scale),
            self._to_screen(panel_x, max_x, min_y, scale),
            self._to_screen(panel_x, max_x, max_y, scale),
            self._to_screen(panel_x, min_x, max_y, scale),
        ]

        pygame.draw.polygon(display, (34, 38, 42), corners)
        pygame.draw.polygon(display, (230, 230, 230), corners, 2)

        front_center = self._to_screen(panel_x, max_x, 0.0 - radar_y, scale)
        rear_center = self._to_screen(panel_x, min_x, 0.0 - radar_y, scale)
        pygame.draw.line(display, (230, 230, 230), rear_center, front_center, 1)

    def _rear_context_m(self):
        player = self.manual_world.player
        if player is None:
            return 0.0
        bbox = player.bounding_box
        radar_location = self.radar_config.get("location", {})
        radar_x = float(radar_location.get("x", 0.0))
        rear_x_relative_to_radar = bbox.location.x - bbox.extent.x - radar_x
        return max(0.0, -rear_x_relative_to_radar)

    def _raw_point_in_view(self, point, view_range_m=None):
        return 0.0 <= point.x_forward_m <= self._view_range(view_range_m)

    def _view_range(self, view_range_m=None):
        if view_range_m is not None:
            return float(view_range_m)
        return float(self.radar_config.get("range", 100.0))

    def _grid_step(self, range_m):
        if range_m <= 15.0:
            return 2
        if range_m <= 30.0:
            return 5
        if range_m <= 60.0:
            return 10
        return 20

    def _valid_front_point(self, point):
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

    def _draw_small_text(self, display, text, pos):
        font = pygame.font.Font(pygame.font.get_default_font(), 14)
        surface = font.render(str(text), True, (180, 190, 190))
        display.blit(surface, pos)

    def destroy(self):
        if self.radar is not None:
            self.radar.destroy()
            self.radar = None
            self._player_id = None


class DualRangeRadarPanel(RadarBirdEyePanel):
    """Middle 10 m radar view plus right full-range radar view."""

    NEAR_RANGE_M = 10.0

    def __init__(self, manual_world, config, panel_width, panel_height, gamma, args):
        self._gamma = gamma
        self.bird_eye_camera = None
        self._camera_player_id = None
        self.bird_eye_config = None
        self.bird_eye_intrinsic = None
        super(DualRangeRadarPanel, self).__init__(
            manual_world,
            config,
            panel_width,
            panel_height,
            gamma,
            args,
        )
        self._ensure_bird_eye_camera()

    def tick(self):
        super(DualRangeRadarPanel, self).tick()
        self._ensure_bird_eye_camera()

    def _ensure_bird_eye_camera(self):
        player = self.manual_world.player
        if player is None:
            return
        if self.bird_eye_camera is not None and self._camera_player_id == player.id:
            return
        self._destroy_bird_eye_camera()
        self.bird_eye_config = self._bird_eye_camera_config()
        self.bird_eye_intrinsic = camera_intrinsic(
            int(self.bird_eye_config["image_size_x"]),
            int(self.bird_eye_config["image_size_y"]),
            float(self.bird_eye_config["fov"]),
        )
        self.bird_eye_camera = CameraSensor(player, self.bird_eye_config, self._gamma)
        self._camera_player_id = player.id

    def _bird_eye_camera_config(self):
        defaults = {
            "blueprint": "sensor.camera.rgb",
            "attachment": "Rigid",
            "image_size_x": self.panel_width,
            "image_size_y": self.panel_height,
            "fov": 45,
            "sensor_tick": 0.05,
            "location": {
                "x": 4.5,
                "y": 0.0,
                "z": 36.0,
            },
            "rotation": {
                "pitch": -90.0,
                "yaw": 0.0,
                "roll": 0.0,
            },
        }
        override = self.config.get("radar_view", {}).get("near_bird_eye_camera", {})
        return self._merge_nested_config(defaults, override)

    def _merge_nested_config(self, defaults, override):
        merged = dict(defaults)
        for key, value in (override or {}).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                nested = dict(merged[key])
                nested.update(value)
                merged[key] = nested
            else:
                merged[key] = value
        return merged

    def render(self, display):
        middle_x = self.panel_width
        right_x = self.panel_width * 2
        full_range_m = float(self.radar_config.get("range", 100.0))

        self._render_camera_bird_eye_view(
            display,
            middle_x,
            self.NEAR_RANGE_M,
            "AEB CARLA bird-eye radar 10m",
        )
        self._draw_near_info(display, middle_x, self.NEAR_RANGE_M)

        self._render_radar_view(
            display,
            right_x,
            full_range_m,
            "AEB front radar bird-eye {}m".format(format_float(full_range_m, 0)),
        )
        self._draw_info(display, right_x)

        self._draw_vertical_divider(display, self.panel_width)
        self._draw_vertical_divider(display, self.panel_width * 2)

    def _render_radar_view(self, display, panel_x, view_range_m, title):
        rect = pygame.Rect(panel_x, 0, self.panel_width, self.panel_height)
        pygame.draw.rect(display, (8, 10, 12), rect)
        self._draw_grid(display, panel_x, view_range_m)
        self._draw_radar_points(display, panel_x, view_range_m)
        draw_panel_label(display, panel_x, title)

    def _render_camera_bird_eye_view(self, display, panel_x, view_range_m, title):
        rect = pygame.Rect(panel_x, 0, self.panel_width, self.panel_height)
        if self.bird_eye_camera is None:
            pygame.draw.rect(display, (8, 10, 12), rect)
        else:
            self.bird_eye_camera.render_image(
                display,
                (panel_x, 0),
                (self.panel_width, self.panel_height),
            )
            self._draw_camera_overlay_scrim(display, panel_x)
        self._draw_projected_metric_grid(display, panel_x, view_range_m)
        self._draw_projected_range_fan(display, panel_x, view_range_m)
        self._draw_projected_radar_points(display, panel_x, view_range_m)
        draw_panel_label(display, panel_x, title)

    def _draw_camera_overlay_scrim(self, display, panel_x):
        scrim = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        scrim.fill((0, 0, 0, 34))
        display.blit(scrim, (panel_x, 0))

    def _draw_projected_range_fan(self, display, panel_x, view_range_m):
        radar_screen = self._radar_sensor_screen(panel_x)
        if radar_screen is None:
            return

        horizontal_fov = float(self.radar_config.get("horizontal_fov", 30.0))
        ground_z_up = self._radar_ground_z_up()
        edge_points = []
        for sign in (-1, 1):
            angle = math.radians(sign * horizontal_fov / 2.0)
            world_location = self._radar_local_to_world(
                view_range_m * math.cos(angle),
                view_range_m * math.sin(angle),
                ground_z_up,
            )
            projected = self._project_to_bird_eye(panel_x, world_location)
            if projected is not None:
                edge_points.append(projected)

        overlay = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        local_radar = (radar_screen[0] - panel_x, radar_screen[1])
        local_edges = [(point[0] - panel_x, point[1]) for point in edge_points]
        if len(local_edges) == 2:
            pygame.draw.polygon(
                overlay,
                (80, 225, 245, 50),
                [local_radar] + local_edges,
            )
            pygame.draw.line(overlay, (130, 245, 255, 180), local_radar, local_edges[0], 2)
            pygame.draw.line(overlay, (130, 245, 255, 180), local_radar, local_edges[1], 2)

        for distance in range(2, int(view_range_m) + 1, 2):
            arc_points = []
            for angle_deg in range(
                -int(horizontal_fov / 2.0),
                int(horizontal_fov / 2.0) + 1,
                2,
            ):
                angle = math.radians(angle_deg)
                world_location = self._radar_local_to_world(
                    distance * math.cos(angle),
                    distance * math.sin(angle),
                    ground_z_up,
                )
                projected = self._project_to_bird_eye(panel_x, world_location)
                if projected is not None:
                    arc_points.append((projected[0] - panel_x, projected[1]))
            if len(arc_points) > 1:
                pygame.draw.lines(overlay, (130, 245, 255, 130), False, arc_points, 1)

        display.blit(overlay, (panel_x, 0))
        pygame.draw.circle(display, (255, 255, 255), radar_screen, 6)
        pygame.draw.circle(display, (20, 20, 20), radar_screen, 3)

    def _draw_projected_metric_grid(self, display, panel_x, view_range_m):
        horizontal_fov = float(self.radar_config.get("horizontal_fov", 30.0))
        lateral_limit = max(
            3.0,
            view_range_m * math.sin(math.radians(horizontal_fov / 2.0)) + 0.8,
        )
        ground_z_up = self._radar_ground_z_up()
        overlay = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)

        x_steps = range(0, int(view_range_m) + 1)
        y_min = -int(math.ceil(lateral_limit))
        y_max = int(math.ceil(lateral_limit))
        y_steps = range(y_min, y_max + 1)

        for x_forward in x_steps:
            points = self._project_radar_polyline(
                panel_x,
                [
                    (float(x_forward), y_right * 0.25, ground_z_up)
                    for y_right in range(int(y_min * 4), int(y_max * 4) + 1)
                ],
            )
            if len(points) > 1:
                color = (255, 255, 255, 55) if x_forward % 2 else (255, 255, 255, 90)
                pygame.draw.lines(overlay, color, False, points, 1)

        for y_right in y_steps:
            points = self._project_radar_polyline(
                panel_x,
                [
                    (x_forward * 0.25, float(y_right), ground_z_up)
                    for x_forward in range(0, int(view_range_m * 4) + 1)
                ],
            )
            if len(points) > 1:
                color = (255, 255, 255, 55)
                if y_right == 0:
                    color = (255, 225, 90, 135)
                pygame.draw.lines(overlay, color, False, points, 1)

        display.blit(overlay, (panel_x, 0))

    def _project_radar_polyline(self, panel_x, local_points):
        points = []
        for x_forward, y_right, z_up in local_points:
            world_location = self._radar_local_to_world(x_forward, y_right, z_up)
            projected = self._project_to_bird_eye(panel_x, world_location)
            if projected is None:
                continue
            points.append((projected[0] - panel_x, projected[1]))
        return points

    def _draw_projected_radar_points(self, display, panel_x, view_range_m):
        if self.radar is None:
            return
        target = self._selected_target()
        for point in self.radar.points:
            if not self._raw_point_in_view(point, view_range_m):
                continue
            screen = self._project_to_bird_eye(panel_x, point.world_location)
            if screen is None:
                continue
            radius = 8 if point is target else 4
            pygame.draw.circle(display, self._point_color(point), screen, radius)
            if point is target:
                pygame.draw.circle(display, (255, 255, 255), screen, radius + 3, 2)

        closest = self._closest_near_point(view_range_m)
        radar_screen = self._radar_sensor_screen(panel_x)
        closest_screen = (
            self._project_to_bird_eye(panel_x, closest.world_location)
            if closest is not None
            else None
        )
        if radar_screen is not None and closest_screen is not None:
            pygame.draw.line(display, (255, 255, 255), radar_screen, closest_screen, 2)
            label = "{} m".format(format_float(closest.depth_m, 2))
            mid_x = int((radar_screen[0] + closest_screen[0]) / 2.0)
            mid_y = int((radar_screen[1] + closest_screen[1]) / 2.0)
            self._draw_text_with_shadow(display, label, (mid_x + 8, mid_y - 8))

    def _project_to_bird_eye(self, panel_x, world_location):
        if (
            self.bird_eye_camera is None
            or self.bird_eye_intrinsic is None
            or world_location is None
        ):
            return None
        projected = project_world_to_camera(
            world_location,
            self.bird_eye_camera.latest_transform,
            self.bird_eye_intrinsic,
        )
        if projected is None:
            return None
        u, v = projected
        if u < 0 or v < 0 or u >= self.panel_width or v >= self.panel_height:
            return None
        return int(panel_x + u), int(v)

    def _radar_sensor_screen(self, panel_x):
        radar_transform = self._radar_world_transform()
        if radar_transform is None:
            return None
        return self._project_to_bird_eye(panel_x, radar_transform.location)

    def _radar_local_to_world(self, x_forward, y_right, z_up):
        radar_transform = self._radar_world_transform()
        if radar_transform is None:
            return None
        location = carla.Location(x=float(x_forward), y=float(y_right), z=float(z_up))
        radar_transform.transform(location)
        return location

    def _radar_ground_z_up(self):
        radar_location = self.radar_config.get("location", {})
        return -float(radar_location.get("z", 0.0))

    def _radar_world_transform(self):
        if self.radar is not None and self.radar.sensor is not None:
            try:
                return self.radar.sensor.get_transform()
            except RuntimeError:
                return None
        player = self.manual_world.player
        if player is None:
            return None
        return player.get_transform() * transform_from_config(self.radar_config)

    def _draw_text_with_shadow(self, display, text, pos):
        font = pygame.font.Font(pygame.font.get_default_font(), 16)
        shadow = font.render(str(text), True, (0, 0, 0))
        surface = font.render(str(text), True, (255, 255, 255))
        display.blit(shadow, (pos[0] + 1, pos[1] + 1))
        display.blit(surface, pos)

    def _draw_vertical_divider(self, display, x):
        pygame.draw.line(display, (240, 240, 240), (x, 0), (x, self.panel_height), 2)

    def _draw_near_info(self, display, panel_x, view_range_m):
        if self.radar is None:
            self._draw_info_card(
                display,
                panel_x + 16,
                48,
                300,
                "NEAR SCAN",
                [("Status", "waiting")],
            )
            return

        near_points = self._near_points(view_range_m)
        near_candidates = [
            point
            for point in near_points
            if abs(point.y_right_m)
            <= float(self.fusion_config.get("max_lateral_offset_m", 2.4))
            and float(self.fusion_config.get("min_radar_z_up_m", -0.35))
            <= point.z_up_m
            <= float(self.fusion_config.get("max_radar_z_up_m", 2.5))
        ]
        closest = self._closest_near_point(view_range_m)
        rows = [
            ("Shown points", len(near_points)),
            ("AEB candidates", len(near_candidates)),
            ("Range", "{} m".format(format_float(view_range_m, 0))),
        ]
        if closest is not None:
            rows.extend(
                [
                    ("Forward", "{} m".format(format_float(closest.x_forward_m, 2))),
                    ("Depth", "{} m".format(format_float(closest.depth_m, 2))),
                    ("Lateral", "{} m".format(format_float(closest.y_right_m, 2))),
                    ("Rel v", "{} m/s".format(format_float(closest.relative_velocity_mps, 1))),
                ]
            )

        self._draw_info_card(display, panel_x + 16, 48, 300, "NEAR SCAN", rows)

    def _draw_radar_points(self, display, panel_x, view_range_m=None):
        super(DualRangeRadarPanel, self)._draw_radar_points(display, panel_x, view_range_m)
        if view_range_m is None or float(view_range_m) > self.NEAR_RANGE_M:
            return
        closest = self._closest_near_point(view_range_m)
        if closest is None:
            return

        horizontal_fov = float(self.radar_config.get("horizontal_fov", 30.0))
        scale = self._scale(self._view_range(view_range_m), horizontal_fov)
        origin = self._origin(panel_x, scale)
        closest_screen = self._to_screen(
            panel_x,
            closest.x_forward_m,
            closest.y_right_m,
            scale,
        )
        forward_screen = self._to_screen(panel_x, closest.x_forward_m, 0.0, scale)

        pygame.draw.line(display, (245, 245, 245), origin, forward_screen, 2)
        pygame.draw.line(display, (245, 245, 245), forward_screen, closest_screen, 1)
        pygame.draw.circle(display, (245, 245, 245), forward_screen, 4)

        label = "{} m forward".format(format_float(closest.x_forward_m, 2))
        label_pos = (forward_screen[0] + 8, int((origin[1] + forward_screen[1]) / 2.0) - 8)
        self._draw_small_text(display, label, label_pos)

    def _near_points(self, view_range_m):
        if self.radar is None:
            return []
        return [
            point for point in self.radar.points if self._raw_point_in_view(point, view_range_m)
        ]

    def _closest_near_point(self, view_range_m):
        near_points = self._near_points(view_range_m)
        if not near_points:
            return None
        return min(near_points, key=lambda point: point.x_forward_m)

    def _destroy_bird_eye_camera(self):
        if self.bird_eye_camera is not None:
            self.bird_eye_camera.destroy()
            self.bird_eye_camera = None
            self._camera_player_id = None

    def destroy(self):
        self._destroy_bird_eye_camera()
        super(DualRangeRadarPanel, self).destroy()


def run_three_panel(args, panel_factory, caption):
    """Run manual_control.py on the left and two custom panels on the right."""

    config = load_yaml(args.config)
    panel_width, panel_height = display_size_from_args(args, config)
    fps = int(config_value(config, "display", "fps", 60))
    gamma = float(config_value(config, "display", "gamma", 2.2))
    args = prepare_manual_control_args(args, config, panel_width, panel_height, gamma)

    pygame.init()
    pygame.font.init()
    client = None
    manual_world = None
    panel = None

    try:
        client = carla.Client(args.host, args.port)
        client.set_timeout(args.timeout)

        display = pygame.display.set_mode(
            (panel_width * 3, panel_height),
            pygame.HWSURFACE | pygame.DOUBLEBUF,
        )
        pygame.display.set_caption(caption)
        display.fill((0, 0, 0))
        pygame.display.flip()

        hud = manual_control.HUD(panel_width, panel_height)
        carla_world = load_or_get_world(client, config, args)
        manual_world = manual_control.World(carla_world, hud, args)
        controller = manual_control.KeyboardControl(manual_world, args.autopilot)
        panel = panel_factory(manual_world, config, panel_width, panel_height, gamma, args)
        if hasattr(panel, "set_controller"):
            panel.set_controller(controller)

        clock = pygame.time.Clock()
        while True:
            clock.tick_busy_loop(fps)
            if controller.parse_events(client, manual_world, clock):
                return

            panel.tick()
            manual_world.tick(clock)
            manual_world.render(display)
            panel.render(display)
            pygame.display.flip()

    finally:
        if manual_world is not None and manual_world.recording_enabled and client is not None:
            client.stop_recorder()
        if panel is not None:
            panel.destroy()
        if manual_world is not None:
            manual_world.destroy()
        pygame.quit()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        run_three_panel(args, DualRangeRadarPanel, "AEB radar test - manual_control extended")
    except KeyboardInterrupt:
        print("\nĐã dừng bởi người dùng.")


if __name__ == "__main__":
    main()
