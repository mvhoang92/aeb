#!/usr/bin/env python

"""Test front radar with manual_control.py on the left and bird-eye radar on the right."""

from __future__ import print_function

import argparse
import math

from two_panel_common import (
    RadarSensor,
    add_common_args,
    compute_ttc,
    draw_panel_label,
    format_float,
    pygame,
    run_two_panel,
    select_front_radar_target,
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

    def _draw_grid(self, display, panel_x):
        range_m = float(self.radar_config.get("range", 100.0))
        horizontal_fov = float(self.radar_config.get("horizontal_fov", 30.0))
        origin = self._origin(panel_x)
        scale = self._scale(range_m, horizontal_fov)

        pygame.draw.polygon(
            display,
            (22, 42, 50),
            [origin]
            + [
                self._to_screen(panel_x, distance, offset, scale)
                for distance, offset in self._fan_edge_points(range_m, horizontal_fov)
            ],
        )

        for distance in range(20, int(range_m) + 1, 20):
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

    def _draw_radar_points(self, display, panel_x):
        if self.radar is None:
            return
        range_m = float(self.radar_config.get("range", 100.0))
        horizontal_fov = float(self.radar_config.get("horizontal_fov", 30.0))
        scale = self._scale(range_m, horizontal_fov)
        target = self._selected_target()

        for point in self.radar.points:
            if not self._raw_point_in_view(point):
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

    def _origin(self, panel_x):
        return int(panel_x + self.panel_width / 2.0), int(self.panel_height - 54)

    def _scale(self, range_m, horizontal_fov):
        max_width = 2.0 * range_m * math.sin(math.radians(horizontal_fov / 2.0))
        scale_y = (self.panel_height - 120.0) / max(range_m, 1.0)
        scale_x = (self.panel_width - 100.0) / max(max_width, 1.0)
        return min(scale_x, scale_y)

    def _to_screen(self, panel_x, x_forward, y_right, scale):
        origin = self._origin(panel_x)
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

    def _raw_point_in_view(self, point):
        return 0.0 <= point.x_forward_m <= float(self.radar_config.get("range", 100.0))

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


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        run_two_panel(args, RadarBirdEyePanel, "AEB radar test - manual_control extended")
    except KeyboardInterrupt:
        print("\nĐã dừng bởi người dùng.")


if __name__ == "__main__":
    main()
