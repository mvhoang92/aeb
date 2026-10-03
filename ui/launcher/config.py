"""Paths and catalogues used by the launcher (no Tkinter dependency)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

import yaml

from infrastructure.workspace import environments_root


AEB_ROOT = Path(__file__).resolve().parents[2]
CARLA_ROOT = AEB_ROOT.parent
CARLA_PYTHON = CARLA_ROOT / "venv" / "bin" / "python"
YOLO_PYTHON = Path(
    os.environ.get(
        "AEB_YOLO_PYTHON",
        str(environments_root() / "yolo310" / "bin" / "python"),
    )
)
CARLA_SCRIPT = CARLA_ROOT / "CarlaUE4.sh"
SENSOR_CONFIG = AEB_ROOT / "configs" / "sensors.yaml"
DEFAULT_SCENARIO_CONFIG = (
    AEB_ROOT / "configs" / "scenarios" / "suites" / "system_limit_extended_sweep.yaml"
)
SCENARIO_CONFIGS = {
    "Suite / report demo": AEB_ROOT / "configs" / "scenarios" / "suites" / "report_demo.yaml",
    "Suite / smoke basic": AEB_ROOT / "configs" / "scenarios" / "suites" / "smoke_basic.yaml",
    "Suite / radar-only regression": AEB_ROOT / "configs" / "scenarios" / "suites" / "radar_only_regression.yaml",
    "Suite / fusion regression": AEB_ROOT / "configs" / "scenarios" / "suites" / "fusion_regression.yaml",
    "Suite / CCRs system limit": AEB_ROOT / "configs" / "scenarios" / "suites" / "system_limit_ccrs_sweep.yaml",
    "Suite / extended system limit": AEB_ROOT / "configs" / "scenarios" / "suites" / "system_limit_extended_sweep.yaml",
    "Car-to-car / clear road": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "clear_road.yaml",
    "Car-to-car / CCRs stationary lead": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "ccrs_stationary_lead.yaml",
    "Car-to-car / CCRm moving lead": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "ccrm_moving_lead.yaml",
    "Car-to-car / CCRb braking lead": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "ccrb_braking_lead.yaml",
    "Car-to-car / cut-in": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "cut_in.yaml",
    "Car-to-car / cut-out": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "cut_out.yaml",
    "Car-to-car / adjacent vehicle": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "adjacent_vehicle.yaml",
    "Car-to-car / curve cases": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "curve_cases.yaml",
    "Car-to-car / multi actor": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "multi_actor.yaml",
}

UI_APPLICATIONS = {
    "Final demo 3 màn": AEB_ROOT / "ui" / "aeb_demo_view.py",
    "Radar AEB": AEB_ROOT / "ui" / "radar_aeb_view.py",
    "Camera": AEB_ROOT / "ui" / "camera_view.py",
    "Radar": AEB_ROOT / "ui" / "radar_view.py",
    "YOLO": AEB_ROOT / "ui" / "yolo_view.py",
    "Fusion": AEB_ROOT / "ui" / "fusion_view.py",
}

TEST_SCRIPTS = {
    "Radar scenario batch": AEB_ROOT / "scripts" / "run_radar_aeb_scenarios.py",
    "Fusion scenario batch": AEB_ROOT / "scripts" / "run_fusion_aeb_scenarios.py",
}

BRAKE_MODES = (
    "config default",
    "binary",
    "staged",
    "pid",
    "pid_v1",
    "pid_v2",
    "pid_v2_comfort",
    "staged_pid",
)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def scenario_ids(path: Path) -> List[str]:
    return [
        str(item["id"])
        for item in load_yaml(path).get("scenarios", [])
        if isinstance(item, dict) and item.get("id")
    ]


def check_prerequisites() -> int:
    checks = {
        "CARLA script": CARLA_SCRIPT.is_file(),
        "CARLA Python": CARLA_PYTHON.is_file(),
        "YOLO Python": YOLO_PYTHON.is_file(),
        "Sensor config": SENSOR_CONFIG.is_file(),
        "Scenario config": DEFAULT_SCENARIO_CONFIG.is_file(),
        "Final demo UI": UI_APPLICATIONS["Final demo 3 màn"].is_file(),
        "Video recorder": (AEB_ROOT / "scripts" / "record_scenario_videos.py").is_file(),
    }
    for name, passed in checks.items():
        print("{:<18} {}".format(name, "OK" if passed else "MISSING"))
    print("Scenarios          {}".format(len(scenario_ids(DEFAULT_SCENARIO_CONFIG))))
    return 0 if all(checks.values()) else 2
