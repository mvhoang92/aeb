#!/usr/bin/env python

"""Extend CARLA manual_control.py with a second AEB camera panel.

Left panel: original manual_control.py UI and controls.
Right panel: windshield camera configured in configs/camera.yaml.
"""

from __future__ import print_function

import argparse
import glob
import os
import sys
import weakref
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

try:
    import pygame
except ImportError:
    raise RuntimeError("cannot import pygame, make sure pygame package is installed")

try:
    import yaml
except ImportError:
    raise RuntimeError("cannot import yaml, make sure PyYAML package is installed")

import manual_control


DEFAULT_CONFIG = AEB_ROOT / "configs" / "camera.yaml"


def load_yaml(path):
    with open(path, "r") as stream:
        return yaml.safe_load(stream) or {}


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


def config_value(data, section, key, default):
    section_data = data.get(section, {})
    if not isinstance(section_data, dict):
        return default
    return section_data.get(key, default)


class WindshieldCamera(object):
    """Second RGB camera rendered on the right half of the display."""

    def __init__(self, parent_actor, config, gamma):
        self.sensor = None
        self.surface = None
        self._parent = parent_actor
        self.config = config
        self.width = int(config.get("image_size_x", 800))
        self.height = int(config.get("image_size_y", 450))
        self._spawn(gamma)

    def _spawn(self, gamma):
        world = self._parent.get_world()
        bp = world.get_blueprint_library().find(
            self.config.get("blueprint", "sensor.camera.rgb")
        )
        bp.set_attribute("image_size_x", str(self.width))
        bp.set_attribute("image_size_y", str(self.height))
        bp.set_attribute("fov", str(self.config.get("fov", 70)))
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
        self.sensor.listen(lambda image: WindshieldCamera._parse_image(weak_self, image))

    def render(self, display, position, size):
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
        self.surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))


class AEBRightPanel(object):
    """Keep the extra AEB camera attached even after manual_control restarts."""

    def __init__(self, manual_world, config, panel_width, panel_height, gamma):
        self.manual_world = manual_world
        self.config = config
        self.panel_width = panel_width
        self.panel_height = panel_height
        self.gamma = gamma
        self.camera = None
        self._player_id = None
        self._ensure_camera()

    def tick(self):
        self._ensure_camera()

    def _ensure_camera(self):
        player = self.manual_world.player
        if player is None:
            return
        if self.camera is not None and self._player_id == player.id:
            return
        self.destroy()
        self.camera = WindshieldCamera(player, self.config, self.gamma)
        self._player_id = player.id

    def render(self, display):
        x = self.panel_width
        size = (self.panel_width, self.panel_height)
        if self.camera is not None:
            self.camera.render(display, (x, 0), size)
        pygame.draw.line(
            display,
            (240, 240, 240),
            (x, 0),
            (x, self.panel_height),
            2,
        )
        self._render_label(display)

    def _render_label(self, display):
        font = pygame.font.Font(pygame.font.get_default_font(), 18)
        text = self.config.get("name", "AEB windshield camera")
        surface = font.render(text, True, (255, 255, 255))
        bg = pygame.Surface((surface.get_width() + 16, surface.get_height() + 10))
        bg.set_alpha(140)
        bg.fill((0, 0, 0))
        display.blit(bg, (self.panel_width + 8, 8))
        display.blit(surface, (self.panel_width + 16, 14))

    def destroy(self):
        if self.camera is not None:
            self.camera.destroy()
            self.camera = None
            self._player_id = None


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


def game_loop(args):
    config = load_yaml(args.config)
    panel_width, panel_height = display_size_from_args(args, config)
    fps = int(config_value(config, "display", "fps", 60))
    gamma = float(config_value(config, "display", "gamma", 2.2))
    args = prepare_manual_control_args(args, config, panel_width, panel_height, gamma)

    pygame.init()
    pygame.font.init()
    manual_world = None
    right_panel = None

    try:
        client = carla.Client(args.host, args.port)
        client.set_timeout(args.timeout)

        display = pygame.display.set_mode(
            (panel_width * 2, panel_height),
            pygame.HWSURFACE | pygame.DOUBLEBUF,
        )
        pygame.display.set_caption("AEB camera test - manual_control extended")
        display.fill((0, 0, 0))
        pygame.display.flip()

        hud = manual_control.HUD(panel_width, panel_height)
        carla_world = load_or_get_world(client, config, args)
        manual_world = manual_control.World(carla_world, hud, args)
        controller = manual_control.KeyboardControl(manual_world, args.autopilot)
        right_panel = AEBRightPanel(
            manual_world,
            config.get("driver_camera", {}),
            panel_width,
            panel_height,
            gamma,
        )

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
        if manual_world is not None and manual_world.recording_enabled:
            client.stop_recorder()
        if right_panel is not None:
            right_panel.destroy()
        if manual_world is not None:
            manual_world.destroy()
        pygame.quit()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("-p", "--port", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
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
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        game_loop(args)
    except KeyboardInterrupt:
        print("\nCancelled by user.")


if __name__ == "__main__":
    main()
