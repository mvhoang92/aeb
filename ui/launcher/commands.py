"""Pure command builders for every launcher action (no Tkinter dependency).

The launcher is an entry point for reproducible runs, so the argument lists
built here are part of the experiment record.  Keep them byte-for-byte stable;
``tests/test_launcher_commands.py`` pins representative outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from ui.launcher.config import (
    AEB_ROOT,
    CARLA_PYTHON,
    CARLA_SCRIPT,
    TEST_SCRIPTS,
    UI_APPLICATIONS,
    YOLO_PYTHON,
)


ALL_SCENARIOS = "Tất cả"
DEFAULT_BRAKE_MODE = "config default"
LIVE_SCENARIO_APPS = ("Radar AEB", "Final demo 3 màn")
NVIDIA_OFFLOAD_ENVIRONMENT = {
    "__NV_PRIME_RENDER_OFFLOAD": "1",
    "__GLX_VENDOR_LIBRARY_NAME": "nvidia",
}
NVIDIA_OFFLOAD_PREFIX = [
    "__NV_PRIME_RENDER_OFFLOAD=1",
    "__GLX_VENDOR_LIBRARY_NAME=nvidia",
]


def command_text(command: List[str]) -> str:
    return " ".join(
        "'{}'".format(part.replace("'", "'\\''"))
        if any(character.isspace() for character in part)
        else part
        for part in command
    )


# --------------------------------------------------------------------------- #
# CARLA server
# --------------------------------------------------------------------------- #
def server_command(quality: str, port: int, stable_mode: bool) -> List[str]:
    command = [
        str(CARLA_SCRIPT),
        "-quality-level={}".format(quality),
    ]
    if port != 2000 or stable_mode:
        command.append("-carla-rpc-port={}".format(port))
    if stable_mode:
        command.extend(["-nosound", "-windowed", "-ResX=1280", "-ResY=720"])
    return command


def server_environment(nvidia_offload: bool) -> Dict[str, str]:
    environment: Dict[str, str] = {}
    if nvidia_offload:
        environment.update(NVIDIA_OFFLOAD_ENVIRONMENT)
    return environment


def server_preview_command(command: List[str], nvidia_offload: bool) -> List[str]:
    command = list(command)
    if nvidia_offload:
        command = list(NVIDIA_OFFLOAD_PREFIX) + command
    return command


# --------------------------------------------------------------------------- #
# Visual applications
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AppSettings:
    name: str
    map_name: str
    resolution: str
    host: str
    port: int
    autopilot: bool
    brake_mode: str
    scenario_config: Path
    scenario: str
    control_mode: str
    camera: str
    warmup_s: float
    reload_world: bool
    behavior: str
    clean_overlay: bool
    sync: bool


def app_command(settings: AppSettings) -> List[str]:
    name = settings.name
    command = [
        str(CARLA_PYTHON),
        str(UI_APPLICATIONS[name]),
        "--map-name",
        settings.map_name,
        "--res",
        settings.resolution,
        "--host",
        settings.host,
        "--port",
        str(settings.port),
    ]
    if settings.autopilot:
        command.append("-a")
    if settings.brake_mode != DEFAULT_BRAKE_MODE:
        command.extend(["--brake-mode", settings.brake_mode])
    if name in LIVE_SCENARIO_APPS and settings.scenario:
        command.extend(
            [
                "--scenario-config",
                str(settings.scenario_config),
                "--scenario",
                settings.scenario,
                "--control-mode",
                settings.control_mode,
                "--scenario-camera",
                settings.camera,
                "--scenario-warmup-s",
                str(settings.warmup_s),
            ]
        )
        if settings.reload_world:
            command.append("--reload-world-on-start")
        if "Realistic" in settings.behavior:
            command.append("--keep-driving-after-aeb")
    if name == "Final demo 3 màn":
        command.append("--clean-radar-overlay" if settings.clean_overlay else "--debug-radar-overlay")
        command.append("--sync" if settings.sync else "--no-sync")
    return command


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CheckSettings:
    test_type: str
    scenario_config: Path
    control_mode: str
    repeat: int
    cooldown_s: float
    reload_every: int
    scenario: str
    load_map: bool
    record_evidence: bool
    run_id: str


def check_command(settings: CheckSettings) -> List[str]:
    test_type = settings.test_type
    if test_type == "Unit test":
        return [
            str(CARLA_PYTHON),
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
        ]
    if test_type == "Kiểm tra dataset YOLO":
        return [str(YOLO_PYTHON), str(AEB_ROOT / "scripts" / "check_yolo_dataset.py")]

    command = [
        str(CARLA_PYTHON),
        str(TEST_SCRIPTS[test_type]),
        "--scenario-config",
        str(settings.scenario_config),
        "--control-mode",
        settings.control_mode,
        "--repeat",
        str(settings.repeat),
        "--scenario-cooldown-s",
        str(settings.cooldown_s),
        "--reload-world-wait-s",
        "2.0",
    ]
    reload_every = settings.reload_every
    if reload_every > 0:
        command.extend(["--reload-world-every", str(reload_every)])
    if settings.scenario != ALL_SCENARIOS:
        command.extend(["--scenario", settings.scenario])
    if settings.load_map:
        command.append("--load-map")
    if settings.record_evidence:
        command.append("--record-evidence")
    if settings.run_id.strip():
        command.extend(["--run-id", settings.run_id.strip()])
    return command


# --------------------------------------------------------------------------- #
# Video recording
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class VideoSettings:
    scenario_config: Path
    run_id: str
    resolution: str
    encoder: str
    linger_s: float
    max_seconds: float
    cooldown_s: float
    reload_every: int
    scenario: str
    brake_mode: str
    realistic: bool


def video_command(settings: VideoSettings) -> List[str]:
    command = [
        str(CARLA_PYTHON),
        str(AEB_ROOT / "scripts" / "record_scenario_videos.py"),
        "--scenario-config",
        str(settings.scenario_config),
        "--run-id",
        settings.run_id.strip() or "final_demo_manual",
        "--capture-size",
        settings.resolution,
        "--screen-size",
        settings.resolution,
        "--encoder",
        settings.encoder,
        "--linger",
        str(settings.linger_s),
        "--max-seconds",
        str(settings.max_seconds),
        "--scenario-cooldown-s",
        str(settings.cooldown_s),
        "--reload-world-wait-s",
        "2.0",
        "--control-mode",
        "physics",
    ]
    reload_every = settings.reload_every
    if reload_every > 0:
        command.extend(["--reload-world-every", str(reload_every)])
    if settings.scenario != ALL_SCENARIOS:
        command.extend(["--scenario", settings.scenario])
    if settings.brake_mode != DEFAULT_BRAKE_MODE:
        command.extend(["--brake-mode", settings.brake_mode])
    if settings.realistic:
        command.append("--keep-driving-after-aeb")
    return command
