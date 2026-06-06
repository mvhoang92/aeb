#!/usr/bin/env python

"""Test radar-only binary AEB brake with manual_control.py on the left."""

from __future__ import print_function

import argparse
import math

from control.brake import (
    AEBState,
    apply_brake_override,
    compute_ttc,
)
from core.radar_aeb_pipeline import RadarAEBPipeline
from test_radar import RadarBirdEyePanel
from two_panel_common import (
    add_common_args,
    format_float,
    pygame,
    run_two_panel,
)


class BrakeRadarPanel(RadarBirdEyePanel):
    """Radar bird-eye panel plus radar-only AEB brake override."""

    def __init__(self, manual_world, config, panel_width, panel_height, gamma, args):
        super(BrakeRadarPanel, self).__init__(
            manual_world,
            config,
            panel_width,
            panel_height,
            gamma,
            args,
        )
        player = self.manual_world.player
        carla_map = player.get_world().get_map() if player is not None else None
        self.pipeline = RadarAEBPipeline(player, config, carla_map)
        self.aeb_config = self.pipeline.aeb_config
        self.aeb = self.pipeline.aeb
        self.controller = None
        self.decision = self.pipeline.decision
        self.aeb_override_active = False
        self.restore_autopilot_after_brake = False
        self.last_control = None
        self.cluster_config = self.pipeline.cluster_config
        self.warning_icon_font = pygame.font.Font(
            pygame.font.get_default_font(),
            52,
        )
        self.warning_icon_font.set_bold(True)
        self._sync_pipeline_state()

    def set_controller(self, controller):
        self.controller = controller

    def tick(self):
        super(BrakeRadarPanel, self).tick()
        player = self.manual_world.player
        self.pipeline.set_ego(player)
        frame = self.pipeline.update(self.radar)
        self.decision = frame.decision
        self._sync_pipeline_state()
        self._apply_brake_decision()

    def render(self, display):
        super(BrakeRadarPanel, self).render(display)
        self._draw_warning_icon(display)

    def _draw_warning_icon(self, display):
        if self.decision.state == AEBState.WARNING:
            fill_color = (255, 196, 35)
            border_color = (255, 232, 150)
            text_color = (25, 25, 20)
        elif self.decision.state == AEBState.BRAKE:
            fill_color = (220, 48, 48)
            border_color = (255, 210, 210)
            text_color = (255, 255, 255)
        else:
            return

        center = (
            self.panel_width * 2 - 58,
            58,
        )
        pygame.draw.circle(display, (8, 10, 12), center, 38)
        pygame.draw.circle(display, fill_color, center, 33)
        pygame.draw.circle(display, border_color, center, 33, 3)
        icon = self.warning_icon_font.render("!", True, text_color)
        display.blit(icon, icon.get_rect(center=(center[0], center[1] - 1)))

    def _sync_pipeline_state(self):
        self.tracked_clusters = self.pipeline.tracked_clusters
        self.predicted_path = self.pipeline.predicted_path
        self.path_curvature_1pm = self.pipeline.path_curvature_1pm
        self.path_horizon_m = self.pipeline.path_horizon_m

    def _selected_target(self):
        return self.pipeline.selected_target

    def _valid_path_target(self, point):
        return self.pipeline.valid_path_target(point)

    def _is_ground_point(self, point):
        return self.pipeline.is_ground_point(point)

    def _height_above_road(self, point):
        return self.pipeline.height_above_road(point)

    def _brake_lateral_limit(self):
        return self.pipeline.brake_lateral_limit()

    def _point_color(self, point):
        if self._is_ground_point(point):
            return 130, 135, 140
        return super(BrakeRadarPanel, self)._point_color(point)

    def _color_legend_rows(self):
        rows = super(BrakeRadarPanel, self)._color_legend_rows()
        return rows[:-1] + [
            ((130, 135, 140), "ground: ignored by AEB"),
            ((255, 190, 70), "ring: cluster not confirmed"),
            ((235, 245, 245), "filled center: confirmed cluster"),
            rows[-1],
        ]

    def _draw_radar_points(self, display, panel_x):
        super(BrakeRadarPanel, self)._draw_radar_points(display, panel_x)
        range_m = float(self.radar_config.get("range", 100.0))
        horizontal_fov = float(self.radar_config.get("horizontal_fov", 30.0))
        scale = self._scale(range_m, horizontal_fov)
        target = self._selected_target()

        for cluster in self.tracked_clusters:
            screen = self._to_screen(
                panel_x,
                cluster.x_forward_m,
                cluster.y_right_m,
                scale,
            )
            if cluster.confirmed:
                color = self._ttc_color(cluster)
                radius = 9 if cluster is target else 6
                pygame.draw.circle(display, color, screen, radius)
                pygame.draw.circle(display, (235, 245, 245), screen, radius + 2, 1)
            else:
                pygame.draw.circle(display, (255, 190, 70), screen, 7, 2)
            if cluster is target:
                pygame.draw.circle(display, (255, 255, 255), screen, 13, 2)

    def _draw_grid(self, display, panel_x):
        super(BrakeRadarPanel, self)._draw_grid(display, panel_x)
        range_m = float(self.radar_config.get("range", 100.0))
        horizontal_fov = float(self.radar_config.get("horizontal_fov", 30.0))
        scale = self._scale(range_m, horizontal_fov)
        corridor_half_width = self._brake_lateral_limit()
        left_boundary = []
        right_boundary = []
        centerline = []
        for x_forward, y_right, heading_rad in self.predicted_path:
            normal_x = -math.sin(heading_rad)
            normal_y = math.cos(heading_rad)
            left_boundary.append(
                self._to_screen(
                    panel_x,
                    x_forward - corridor_half_width * normal_x,
                    y_right - corridor_half_width * normal_y,
                    scale,
                )
            )
            right_boundary.append(
                self._to_screen(
                    panel_x,
                    x_forward + corridor_half_width * normal_x,
                    y_right + corridor_half_width * normal_y,
                    scale,
                )
            )
            centerline.append(self._to_screen(panel_x, x_forward, y_right, scale))

        if len(left_boundary) > 1:
            pygame.draw.lines(display, (255, 210, 70), False, left_boundary, 2)
            pygame.draw.lines(display, (255, 210, 70), False, right_boundary, 2)
            pygame.draw.lines(display, (150, 128, 55), False, centerline, 1)

    def _distance_to_predicted_path(self, point):
        return self.pipeline.distance_to_predicted_path(point)

    def _path_description(self):
        return self.pipeline.path_description()

    def _apply_brake_decision(self):
        player = self.manual_world.player
        if player is None:
            return

        if self.decision.state == AEBState.BRAKE:
            if not self.aeb_override_active:
                self.restore_autopilot_after_brake = self._controller_autopilot_enabled()
                if self.restore_autopilot_after_brake:
                    player.set_autopilot(False)
                self.aeb_override_active = True
            self.last_control = apply_brake_override(player, self.decision)
            return

        if self.aeb_override_active:
            self.last_control = apply_brake_override(player, self.decision)
            if self.restore_autopilot_after_brake and self._controller_autopilot_enabled():
                player.set_autopilot(True)
            self.aeb_override_active = False
            self.restore_autopilot_after_brake = False

    def _controller_autopilot_enabled(self):
        return bool(getattr(self.controller, "_autopilot_enabled", False))

    def _draw_info(self, display, panel_x):
        if self.radar is None:
            self._draw_info_card(
                display,
                panel_x + 16,
                48,
                360,
                "AEB BRAKE",
                [("Status", "waiting")],
            )
            self._draw_color_legend(display, panel_x)
            return

        x = panel_x + 16
        width = 360
        next_y = self._draw_info_card(
            display,
            x,
            48,
            width,
            "AEB BRAKE",
            [
                ("Radar points", len(self.radar.points)),
                (
                    "Path candidates",
                    sum(
                        1
                        for point in self.radar.points
                        if self._valid_path_target(point)
                    ),
                ),
                (
                    "Ground ignored",
                    sum(1 for point in self.radar.points if self._is_ground_point(point)),
                ),
                ("Clusters", len(self.tracked_clusters)),
                (
                    "Confirmed",
                    sum(1 for cluster in self.tracked_clusters if cluster.confirmed),
                ),
                ("State", self.decision.state.value),
                ("Brake cmd", "{:.2f}".format(self.decision.brake)),
                ("Override", "ON" if self.aeb_override_active else "OFF"),
                (
                    "Path",
                    "{} +/-{}m".format(
                        self._path_description(),
                        format_float(self._brake_lateral_limit(), 2),
                    ),
                ),
                ("Path horizon", "{} m".format(format_float(self.path_horizon_m, 1))),
                ("Warn TTC", "{} s".format(format_float(self.aeb_config.warning_ttc_s, 1))),
                ("Brake TTC", "{} s".format(format_float(self.aeb_config.brake_ttc_s, 1))),
                ("Release TTC", "{} s".format(format_float(self.aeb_config.release_ttc_s, 1))),
                (
                    "Required dist",
                    "{} m".format(
                        format_float(self.decision.required_distance_m, 1)
                    ),
                ),
                (
                    "Distance margin",
                    "{} m".format(
                        format_float(self.decision.distance_margin_m, 1)
                    ),
                ),
                ("Reason", self._short_reason(self.decision.reason)),
            ],
        )

        target = self._selected_target()
        if target is None:
            target_rows = [("Target", "--"), ("TTC", "inf")]
        else:
            ttc = compute_ttc(target.x_forward_m, target.relative_velocity_mps)
            road_height = target.max_height_above_road_m
            target_rows = [
                ("Target", self._ttc_label(ttc)),
                ("Track ID", target.track_id),
                ("Cluster points", target.point_count),
                (
                    "Confirmation",
                    "{}/{}".format(
                        target.hit_streak,
                        self.cluster_config.confirm_frames,
                    ),
                ),
                ("Missed frames", target.missed_frames),
                ("Distance", "{} m".format(format_float(target.x_forward_m, 1))),
                ("Lateral", "{} m".format(format_float(target.y_right_m, 1))),
                ("Road height", "{} m".format(format_float(road_height, 2))),
                ("Rel v", "{} m/s".format(format_float(target.relative_velocity_mps, 1))),
                ("TTC", "{} s".format(format_float(ttc, 2))),
            ]
        target_x = x + width + 12
        target_y = 48
        if target_x + width > panel_x + self.panel_width - 16:
            target_x = x
            target_y = next_y + 10
        self._draw_info_card(
            display,
            target_x,
            target_y,
            width,
            "TARGET",
            target_rows,
        )
        self._draw_color_legend(display, panel_x)

    def destroy(self):
        pipeline = getattr(self, "pipeline", None)
        if pipeline is not None:
            pipeline.reset()
        super(BrakeRadarPanel, self).destroy()

    def _short_reason(self, reason):
        labels = {
            "no_valid_closing_target": "no closing target",
            "ttc_below_brake_threshold": "TTC brake",
            "ttc_below_warning_threshold": "TTC warning",
            "ttc_recovered": "TTC recovered",
            "normal": "normal",
            "reverse_gear_aeb_disabled": "reverse disabled",
            "static_obstacle_distance_fallback": "static fallback",
            "brake_held_until_stopped": "hold until stopped",
            "distance_below_stopping_threshold": "stopping distance",
            "distance_and_ttc_brake": "TTC + stopping dist",
        }
        return labels.get(reason, reason)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        run_two_panel(
            args,
            BrakeRadarPanel,
            "AEB radar-only brake test - manual_control extended",
        )
    except KeyboardInterrupt:
        print("\nĐã dừng bởi người dùng.")


if __name__ == "__main__":
    main()
