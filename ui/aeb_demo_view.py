#!/usr/bin/env python

"""Final AEB demo UI: camera/fusion, manual view, and radar bird-eye."""

from __future__ import print_function

import argparse
import copy
import math
import subprocess
import sys
from pathlib import Path

AEB_ROOT = Path(__file__).resolve().parents[1]
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from control.brake import AEBState, compute_ttc
from ui.manual_control_common import (
    CameraSensor,
    YoloDetector,
    add_common_args,
    apply_runtime_overrides,
    camera_intrinsic,
    carla,
    config_value,
    draw_panel_label,
    draw_text_box,
    format_float,
    load_or_get_world,
    load_yaml,
    manual_control,
    prepare_manual_control_args,
    project_world_to_camera,
    pygame,
    scale_detection,
)
from ui.radar_aeb_view import BrakeRadarPanel, DEFAULT_SCENARIO_CONFIG


DEFAULT_WINDOW_WIDTH = 1920
DEFAULT_WINDOW_HEIGHT = 1080
LEFT_WIDTH = 1120
TOP_HEIGHT = 630
MIN_WINDOW_WIDTH = 1280
MIN_WINDOW_HEIGHT = 720


class PygameFrameRecorder(object):
    """Encode rendered pygame frames directly, avoiding black X11 captures."""

    def __init__(self, path, size, fps=20, codec="libx264"):
        self.path = Path(path) if path else None
        self.size = size
        self.fps = int(fps)
        self.codec = codec
        self.process = None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._start()

    def _start(self):
        width, height = self.size
        if self.codec == "h264_nvenc":
            encoder_args = ["-c:v", "h264_nvenc", "-preset", "p4"]
        else:
            encoder_args = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            "{}x{}".format(width, height),
            "-r",
            str(self.fps),
            "-i",
            "-",
        ] + encoder_args + [
            "-pix_fmt",
            "yuv420p",
            str(self.path),
        ]
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def write(self, surface):
        if self.process is None or self.process.stdin is None:
            return
        if self.process.poll() is not None:
            return
        try:
            self.process.stdin.write(pygame.image.tostring(surface, "RGB"))
        except (IOError, BrokenPipeError):
            pass

    def close(self):
        if self.process is None:
            return
        try:
            if self.process.stdin is not None:
                self.process.stdin.close()
            self.process.wait(timeout=15)
        except Exception:
            try:
                self.process.terminate()
            except Exception:
                pass
        self.process = None


def parse_window_size(args, config):
    if args.res:
        try:
            width, height = [int(value) for value in args.res.lower().split("x")]
            return width, height
        except ValueError:
            raise ValueError("--res phải có dạng WIDTHxHEIGHT, ví dụ 1600x900")
    display_cfg = config.get("display", {})
    return (
        int(display_cfg.get("demo_width", DEFAULT_WINDOW_WIDTH)),
        int(display_cfg.get("demo_height", DEFAULT_WINDOW_HEIGHT)),
    )


def fit_window_to_desktop(width, height, args):
    """Fit the window inside the current desktop without using fullscreen."""

    if args.res or args.fullscreen or not getattr(args, "fit_screen", True):
        return width, height
    info = pygame.display.Info()
    if info.current_w <= 0 or info.current_h <= 0:
        return width, height
    margin_x = max(0, int(getattr(args, "fit_margin_x", 120)))
    margin_y = max(0, int(getattr(args, "fit_margin_y", 120)))
    usable_w = max(MIN_WINDOW_WIDTH, info.current_w - margin_x)
    usable_h = max(MIN_WINDOW_HEIGHT, info.current_h - margin_y)
    return min(width, usable_w), min(height, usable_h)


def demo_layout(window_width, window_height):
    left_width = min(LEFT_WIDTH, int(window_width * 0.58))
    right_width = window_width - left_width
    top_height = min(TOP_HEIGHT, int(window_height * 0.60))
    manual_height = window_height - top_height
    return left_width, right_width, top_height, manual_height


def demo_aeb_state(radar_panel):
    runtime = getattr(radar_panel, "scenario_runtime", None)
    decision = getattr(radar_panel, "decision", None)
    if runtime is not None and runtime.ego_stop_latched and runtime.stopped_at is not None:
        if str(runtime.status_message).startswith("parked"):
            return "PARKED", 0.0, "hand brake"
        return "STOPPED", 0.0, "final stop"
    if decision is None:
        return AEBState.NORMAL.value, 0.0, "normal"
    if decision.state == AEBState.BRAKE:
        return demo_brake_stage(radar_panel, decision), decision.brake, decision.reason
    return decision.state.value, decision.brake, decision.reason


def demo_brake_stage(radar_panel, decision):
    """Map the staged-PID brake command to a user-facing intervention level."""

    config = getattr(radar_panel, "aeb_config", None)
    brake = float(getattr(decision, "brake", 0.0))
    reason = str(getattr(decision, "reason", ""))
    if config is None:
        if brake >= 0.95:
            return "EMERGENCY"
        if brake >= 0.75:
            return "HARD BRAKE"
        if brake >= 0.55:
            return "MEDIUM BRAKE"
        return "SOFT BRAKE"

    if (
        brake >= float(config.staged_emergency_brake) - 1e-3
        or reason in ("static_obstacle_distance_fallback",)
    ):
        return "EMERGENCY"
    if brake >= float(config.staged_hard_brake) - 1e-3:
        return "HARD BRAKE"
    if brake >= float(config.staged_medium_brake) - 1e-3:
        return "MEDIUM BRAKE"
    return "SOFT BRAKE"


class CameraFusionPanel(object):
    """Top-left camera panel with YOLO boxes and projected radar/fusion data."""

    def __init__(self, manual_world, config, width, height, gamma, radar_panel):
        self.manual_world = manual_world
        self.config = config
        self.width = width
        self.height = height
        self.gamma = gamma
        self.radar_panel = radar_panel
        self.camera_config = config.get("driver_camera", {})
        self.fusion_config = config.get("fusion", {})
        self.radar_config = config.get("front_radar", {})
        self.brake_config = config.get("brake", {})
        self.camera = None
        self._player_id = None
        self.detector = YoloDetector(config.get("model", {}))
        self.detections = []
        self.projected_radar = []
        self.matches = {}
        self._ensure_camera()

    def tick(self):
        self._ensure_camera()
        if self.camera is not None:
            self.detections = self.detector.infer(self.camera.latest_rgb)
        self.projected_radar = self._project_radar_points()
        self.matches = self._match_radar_to_boxes()

    def _ensure_camera(self):
        player = self.manual_world.player
        if player is None:
            return
        if self.camera is not None and self._player_id == player.id:
            return
        self.destroy()
        self.camera = CameraSensor(player, self.camera_config, self.gamma)
        self._player_id = player.id

    def _project_radar_points(self):
        radar = getattr(self.radar_panel, "radar", None)
        if self.camera is None or radar is None:
            return []
        if self.camera.latest_transform is None:
            return []
        intrinsic = camera_intrinsic(
            self.camera.width,
            self.camera.height,
            self.camera.fov,
        )
        projected = []
        for point in radar.points:
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
        pipeline = getattr(self.radar_panel, "pipeline", None)
        if pipeline is not None:
            return pipeline.valid_path_target(point)
        return (
            point.x_forward_m
            >= float(self.fusion_config.get("min_radar_forward_distance_m", 1.5))
            and point.x_forward_m <= float(self.radar_config.get("range", 100.0))
            and abs(point.y_right_m)
            <= float(self.fusion_config.get("max_lateral_offset_m", 2.4))
        )

    def _match_radar_to_boxes(self):
        matches = {}
        for index, det in enumerate(self.detections):
            inside = [
                item
                for item in self.projected_radar
                if det.x1 <= item[1] <= det.x2 and det.y1 <= item[2] <= det.y2
            ]
            if inside:
                matches[index] = min(inside, key=lambda item: item[0].x_forward_m)
        return matches

    def render(self, display, position):
        rect = pygame.Rect(position, (self.width, self.height))
        if self.camera is not None:
            self.camera.render_image(display, position, (self.width, self.height))
        else:
            pygame.draw.rect(display, (10, 10, 12), rect)
        self._draw_projected_radar(display, position)
        self._draw_detections(display, position)
        self._draw_top_status(display, position)
        pygame.draw.rect(display, (230, 235, 235), rect, 2)
        draw_panel_label(display, position[0], "Camera + YOLO + radar fusion")

    def _draw_projected_radar(self, display, position):
        if self.camera is None:
            return
        scale_x = float(self.width) / float(self.camera.width)
        scale_y = float(self.height) / float(self.camera.height)
        for point, u, v in self.projected_radar:
            x = int(position[0] + u * scale_x)
            y = int(position[1] + v * scale_y)
            pygame.draw.circle(display, self._ttc_color(point), (x, y), 3)

    def _draw_detections(self, display, position):
        if self.camera is None:
            return
        image_size = (self.camera.width, self.camera.height)
        panel_size = (self.width, self.height)
        font = pygame.font.Font(pygame.font.get_default_font(), 16)
        for index, det in enumerate(self.detections):
            rect = pygame.Rect(scale_detection(det, image_size, panel_size, position[0]))
            rect.y += position[1]
            match = self.matches.get(index)
            color = (40, 255, 120) if match is not None else (255, 210, 70)
            pygame.draw.rect(display, color, rect, 2)
            label = "{} {:.2f}".format(det.class_name, det.confidence)
            if match is not None:
                point = match[0]
                ttc = compute_ttc(point.x_forward_m, point.relative_velocity_mps)
                label += " | d={}m TTC={}s".format(
                    format_float(point.x_forward_m, 1),
                    format_float(ttc, 2),
                )
            text = font.render(label, True, (255, 255, 255))
            bg = pygame.Surface((text.get_width() + 8, text.get_height() + 6))
            bg.set_alpha(185)
            bg.fill((0, 0, 0))
            label_y = max(position[1], rect.top - bg.get_height())
            display.blit(bg, (rect.left, label_y))
            display.blit(text, (rect.left + 4, label_y + 3))

    def _draw_top_status(self, display, position):
        decision = getattr(self.radar_panel, "decision", None)
        state, brake, reason = demo_aeb_state(self.radar_panel)
        target = self.radar_panel._selected_target()
        lines = [
            self.detector.status,
            "Boxes: {} | matched: {}".format(len(self.detections), len(self.matches)),
            "AEB: {} | brake={:.2f}".format(state, brake),
            "Reason: {}".format(reason),
        ]
        if target is not None:
            ttc = compute_ttc(target.x_forward_m, target.relative_velocity_mps)
            lines.append(
                "Target: d={}m rv={}m/s TTC={}s".format(
                    format_float(target.x_forward_m, 1),
                    format_float(target.relative_velocity_mps, 1),
                    format_float(ttc, 2),
                )
            )
        else:
            lines.append("Target: --")
        draw_text_box(
            display,
            lines,
            (position[0] + 12, position[1] + self.height - 118),
            width=620,
            alpha=165,
        )
        self._draw_aeb_badge(display, position, state)

    def _draw_aeb_badge(self, display, position, state):
        colors = {
            AEBState.NORMAL.value: (45, 190, 95),
            AEBState.WARNING.value: (255, 196, 35),
            AEBState.RELEASE.value: (80, 140, 230),
            "SOFT BRAKE": (245, 170, 60),
            "MEDIUM BRAKE": (240, 120, 45),
            "HARD BRAKE": (225, 70, 45),
            "EMERGENCY": (225, 48, 48),
            "STOPPED": (62, 150, 220),
            "PARKED": (68, 180, 120),
        }
        color = colors.get(state, (45, 190, 95))
        font = pygame.font.Font(pygame.font.get_default_font(), 28)
        font.set_bold(True)
        label = "SAFE" if state == AEBState.NORMAL.value else str(state).upper()
        text = font.render(label, True, (255, 255, 255))
        pad = 14
        box = pygame.Surface((text.get_width() + pad * 2, text.get_height() + 12))
        box.set_alpha(220)
        box.fill(color)
        x = position[0] + self.width - box.get_width() - 18
        y = position[1] + 18
        display.blit(box, (x, y))
        display.blit(text, (x + pad, y + 6))

    def _ttc_color(self, point):
        ttc = compute_ttc(point.x_forward_m, point.relative_velocity_mps)
        if ttc <= float(self.brake_config.get("brake_ttc_s", 1.8)):
            return 255, 80, 60
        if ttc <= float(self.brake_config.get("warning_ttc_s", 3.0)):
            return 70, 140, 255
        return 90, 230, 120

    def destroy(self):
        if self.camera is not None:
            self.camera.destroy()
            self.camera = None
            self._player_id = None


def render_manual_panel(manual_world, display, area):
    surface = display.subsurface(area)
    manual_world.render(surface)
    pygame.draw.rect(display, (230, 235, 235), area, 2)


def render_radar_panel(radar_panel, display, right_area):
    offscreen = pygame.Surface((right_area.width * 2, right_area.height))
    radar_panel.render(offscreen)
    radar_view = offscreen.subsurface(
        pygame.Rect(right_area.width, 0, right_area.width, right_area.height)
    )
    display.blit(radar_view, right_area.topleft)
    draw_demo_radar_overlay(radar_panel, display, right_area)
    pygame.draw.rect(display, (230, 235, 235), right_area, 2)


def draw_demo_radar_overlay(radar_panel, display, area):
    state, brake, reason = demo_aeb_state(radar_panel)
    target = radar_panel._selected_target()
    runtime = getattr(radar_panel, "scenario_runtime", None)
    radar = getattr(radar_panel, "radar", None)
    state_color = {
        AEBState.NORMAL.value: (45, 190, 95),
        AEBState.WARNING.value: (255, 196, 35),
        "SOFT BRAKE": (245, 170, 60),
        "MEDIUM BRAKE": (240, 120, 45),
        "HARD BRAKE": (225, 70, 45),
        "EMERGENCY": (225, 48, 48),
        "STOPPED": (62, 150, 220),
        "PARKED": (68, 180, 120),
    }.get(state, (45, 190, 95))

    font = pygame.font.Font(pygame.font.get_default_font(), 18)
    font.set_bold(True)
    state_text = "SAFE" if state == AEBState.NORMAL.value else state
    badge = font.render("{}  brake={:.2f}".format(state_text, brake), True, (255, 255, 255))
    badge_box = pygame.Surface((badge.get_width() + 24, badge.get_height() + 14))
    badge_box.set_alpha(225)
    badge_box.fill(state_color)
    display.blit(badge_box, (area.x + 14, area.y + 46))
    display.blit(badge, (area.x + 26, area.y + 53))

    lines = [
        "Scenario: {}".format(
            runtime.scenario["id"] if runtime is not None and runtime.scenario else "--"
        ),
        "Status: {}".format(runtime.status_message if runtime is not None else "--"),
        "Reason: {}".format(reason),
        "Radar points: {}".format(len(radar.points) if radar is not None else 0),
        "Clusters: {} | confirmed: {}".format(
            len(getattr(radar_panel, "tracked_clusters", [])),
            sum(
                1
                for cluster in getattr(radar_panel, "tracked_clusters", [])
                if cluster.confirmed
            ),
        ),
    ]
    if target is not None:
        ttc = compute_ttc(target.x_forward_m, target.relative_velocity_mps)
        lines.extend(
            [
                "Target: d={}m lat={}m".format(
                    format_float(target.x_forward_m, 1),
                    format_float(target.y_right_m, 1),
                ),
                "Rel v={}m/s TTC={}s".format(
                    format_float(target.relative_velocity_mps, 1),
                    format_float(ttc, 2),
                ),
            ]
        )
    else:
        lines.append("Target: --")
    if runtime is not None and runtime.final_gap_m is not None:
        lines.append("Final gap: {}m".format(format_float(runtime.final_gap_m, 2)))

    box_width = min(area.width - 28, 460)
    box_height = 14 + len(lines) * 20
    box_x = area.x + 14
    box_y = area.bottom - box_height - 16
    panel = pygame.Surface((box_width, box_height))
    panel.set_alpha(178)
    panel.fill((0, 0, 0))
    display.blit(panel, (box_x, box_y))
    row_font = pygame.font.Font(pygame.font.get_default_font(), 16)
    y = box_y + 8
    for line in lines:
        surface = row_font.render(str(line), True, (245, 248, 248))
        display.blit(surface, (box_x + 10, y))
        y += 20


def run_demo(args):
    config = load_yaml(args.config)
    config = apply_runtime_overrides(config, args)
    if getattr(args, "keep_driving_after_aeb", False):
        config = copy.deepcopy(config)
        brake_config = config.setdefault("brake", {})
        brake_config["hold_brake_until_stopped"] = False
        brake_config["realistic_release_mode"] = True
    scenario_config = load_yaml(args.scenario_config) if args.scenario_config else {}
    runner_config = scenario_config.get("runner", {})
    fixed_delta_seconds = float(runner_config.get("fixed_delta_seconds", 0.05))
    window_width, window_height = parse_window_size(args, config)
    if args.sync:
        fps = max(1, int(round(1.0 / fixed_delta_seconds)))
    else:
        fps = int(config_value(config, "display", "fps", 60))
    gamma = float(config_value(config, "display", "gamma", 2.2))

    pygame.init()
    pygame.font.init()
    window_width, window_height = fit_window_to_desktop(
        window_width,
        window_height,
        args,
    )
    if args.fullscreen:
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            window_width, window_height = info.current_w, info.current_h
    left_width, right_width, top_height, manual_height = demo_layout(
        window_width,
        window_height,
    )
    args = prepare_manual_control_args(args, config, left_width, manual_height, gamma)
    client = None
    manual_world = None
    radar_panel = None
    camera_panel = None
    recorder = None
    original_settings = None
    sync_owned = False

    try:
        client = carla.Client(args.host, args.port)
        client.set_timeout(args.timeout)
        flags = pygame.HWSURFACE | pygame.DOUBLEBUF
        if args.fullscreen:
            flags |= pygame.FULLSCREEN
        display = pygame.display.set_mode((window_width, window_height), flags)
        pygame.display.set_caption("AEB final demo - camera/fusion + manual + radar")
        display.fill((0, 0, 0))
        pygame.display.flip()
        recorder = PygameFrameRecorder(
            getattr(args, "record_video_path", None),
            (window_width, window_height),
            getattr(args, "record_video_fps", fps),
            getattr(args, "record_video_codec", "libx264"),
        )

        hud = manual_control.HUD(left_width, manual_height)
        carla_world = load_or_get_world(client, config, args)
        original_settings = carla_world.get_settings()
        if args.sync:
            settings = carla_world.get_settings()
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = fixed_delta_seconds
            carla_world.apply_settings(settings)
            sync_owned = True
            carla_world.tick()
        manual_world = manual_control.World(carla_world, hud, args)
        controller = manual_control.KeyboardControl(manual_world, args.autopilot)
        radar_panel = BrakeRadarPanel(
            manual_world,
            config,
            right_width,
            window_height,
            gamma,
            args,
        )
        if getattr(args, "hide_world_debug_labels", True):
            radar_panel.scenario_runtime._draw_scenario_debug = lambda ego: None
        if getattr(args, "clean_radar_overlay", True):
            radar_panel._draw_info = lambda display, panel_x: None
            radar_panel._draw_scenario_info = lambda display: None
        radar_panel.set_controller(controller)
        camera_panel = CameraFusionPanel(
            manual_world,
            config,
            left_width,
            top_height,
            gamma,
            radar_panel,
        )

        top_area = pygame.Rect(0, 0, left_width, top_height)
        manual_area = pygame.Rect(0, top_height, left_width, manual_height)
        right_area = pygame.Rect(left_width, 0, right_width, window_height)
        clock = pygame.time.Clock()
        try:
            while True:
                clock.tick_busy_loop(fps)
                if controller.parse_events(client, manual_world, clock):
                    return
                if args.sync:
                    carla_world.tick()

                radar_panel.tick()
                camera_panel.tick()
                manual_world.tick(clock)

                display.fill((0, 0, 0))
                camera_panel.render(display, top_area.topleft)
                render_manual_panel(manual_world, display, manual_area)
                render_radar_panel(radar_panel, display, right_area)
                pygame.display.flip()
                if recorder is not None:
                    recorder.write(display)
        except RuntimeError as error:
            print("CARLA connection/runtime stopped: {}".format(error))
            print("UI sẽ thoát sạch. Hãy bật lại CARLA server rồi chạy lại demo.")
            return

    finally:
        if recorder is not None:
            recorder.close()
        if manual_world is not None and manual_world.recording_enabled and client is not None:
            client.stop_recorder()
        if camera_panel is not None:
            camera_panel.destroy()
        if radar_panel is not None:
            radar_panel.destroy()
        if manual_world is not None:
            manual_world.destroy()
        if sync_owned and original_settings is not None and client is not None:
            try:
                carla_world = client.get_world()
                carla_world.apply_settings(original_settings)
            except RuntimeError:
                pass
        pygame.quit()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    parser.set_defaults(config=Path(AEB_ROOT / "configs" / "sensors.yaml"))
    parser.add_argument(
        "--scenario-config",
        type=Path,
        default=DEFAULT_SCENARIO_CONFIG,
    )
    parser.add_argument("--scenario")
    parser.add_argument(
        "--control-mode",
        choices=("deterministic", "physics"),
        default="physics",
    )
    parser.add_argument(
        "--scenario-camera",
        choices=("wide_chase", "high_chase", "manual"),
        default="wide_chase",
    )
    parser.add_argument("--keep-driving-after-aeb", action="store_true")
    parser.add_argument("--scenario-debug-interval-s", type=float, default=0.10)
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Mở UI full màn hình thật. Không khuyến nghị cho demo thường.",
    )
    parser.add_argument(
        "--fit-screen",
        action="store_true",
        default=True,
        help=(
            "Mặc định: mở cửa sổ thường nhưng tự thu nhỏ để vừa màn hình hiện tại."
        ),
    )
    parser.add_argument(
        "--no-fit-screen",
        action="store_false",
        dest="fit_screen",
        help="Không tự fit màn hình; dùng đúng kích thước từ --res hoặc config.",
    )
    parser.add_argument(
        "--fit-margin-x",
        type=int,
        default=120,
        help="Số pixel trừ ngang khi tự fit màn hình.",
    )
    parser.add_argument(
        "--fit-margin-y",
        type=int,
        default=140,
        help="Số pixel trừ dọc khi tự fit màn hình, để tránh top bar/terminal.",
    )
    parser.add_argument(
        "--clean-radar-overlay",
        action="store_true",
        default=True,
        help="Dùng overlay radar gọn riêng cho UI final, tránh che vùng quét.",
    )
    parser.add_argument(
        "--debug-radar-overlay",
        action="store_false",
        dest="clean_radar_overlay",
        help="Hiện lại card debug radar gốc nếu cần kiểm tra chi tiết.",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        default=True,
        help="Chạy CARLA synchronous mode theo fixed_delta_seconds của scenario config.",
    )
    parser.add_argument(
        "--no-sync",
        action="store_false",
        dest="sync",
        help="Tắt synchronous mode, dùng async như manual_control gốc.",
    )
    parser.add_argument(
        "--hide-world-debug-labels",
        action="store_true",
        default=True,
        help=(
            "Ẩn label debug vẽ trực tiếp trong CARLA world. Label này dễ thành "
            "mảng đen ở xa khi quay demo."
        ),
    )
    parser.add_argument(
        "--show-world-debug-labels",
        action="store_false",
        dest="hide_world_debug_labels",
        help="Hiện lại debug line/label trong CARLA world khi cần debug scenario.",
    )
    parser.add_argument("--scenario-warmup-s", type=float, default=1.0)
    parser.add_argument("--scenario-autoexit-s", type=float, default=0.0)
    parser.add_argument(
        "--record-video-path",
        type=Path,
        help="Ghi trực tiếp frame Pygame ra MP4, tránh lỗi video đen của x11grab.",
    )
    parser.add_argument("--record-video-fps", type=int, default=20)
    parser.add_argument(
        "--record-video-codec",
        choices=("libx264", "h264_nvenc"),
        default="libx264",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        run_demo(args)
    except KeyboardInterrupt:
        print("\nĐã dừng bởi người dùng.")


if __name__ == "__main__":
    main()
