"""Resolve machine-local datasets and generated artifacts outside the Git tree.

The workspace is optional while legacy paths still exist.  Resolution always
prefers an existing explicit/legacy path, then applies a deterministic mapping
to ``AEB_WORKSPACE_ROOT``.  No algorithm configuration is changed silently.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, Optional, Union


AEB_ROOT = Path(__file__).resolve().parents[1]
CARLA_ROOT = AEB_ROOT.parent
DEFAULT_WORKSPACE_ROOT = CARLA_ROOT / "aeb_workspace"
WORKSPACE_ENV = "AEB_WORKSPACE_ROOT"

_DATASET_DESTINATIONS = {
    "dataset": ("datasets", "archive", "v1"),
    "dataset_v2": ("datasets", "archive", "v2"),
    "dataset_v3": ("datasets", "archive", "v3"),
    "dataset_v4": ("datasets", "archive", "v4"),
    "dataset_v5": ("datasets", "archive", "v5"),
    "dataset_v6": ("datasets", "archive", "v6"),
    "dataset_v7_same_lane": ("datasets", "active", "v7_same_lane"),
}


def workspace_root(environment: Optional[Mapping[str, str]] = None) -> Path:
    """Return the configured workspace root without creating it."""

    environment = os.environ if environment is None else environment
    configured = environment.get(WORKSPACE_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_WORKSPACE_ROOT


def dataset_root(generation: str, environment=None) -> Path:
    """Return one known dataset generation in active/archive storage."""

    key = str(generation)
    if key not in _DATASET_DESTINATIONS:
        raise ValueError("Unknown dataset generation: {}".format(key))
    return workspace_root(environment).joinpath(*_DATASET_DESTINATIONS[key])


def logs_root(environment=None) -> Path:
    return workspace_root(environment) / "runs" / "logs"


def campaigns_root(environment=None) -> Path:
    return workspace_root(environment) / "runs" / "campaigns"


def videos_root(environment=None) -> Path:
    return workspace_root(environment) / "runs" / "videos"


def sensor_coverage_root(environment=None) -> Path:
    return workspace_root(environment) / "runs" / "sensor_coverage"


def dataset_checks_root(environment=None) -> Path:
    return workspace_root(environment) / "runs" / "dataset_box_checks"


def diagnostics_root(environment=None) -> Path:
    return workspace_root(environment) / "runs" / "diagnostics"


def report_support_root(environment=None) -> Path:
    return workspace_root(environment) / "runs" / "report_support"


def training_root(environment=None) -> Path:
    return workspace_root(environment) / "training"


def environments_root(environment=None) -> Path:
    return workspace_root(environment) / "environments"


def quarantine_root(environment=None) -> Path:
    return workspace_root(environment) / "quarantine"


def _output_destination(parts, environment=None):
    if not parts:
        return diagnostics_root(environment)
    name = parts[0]
    tail = parts[1:]
    if name.startswith("dataset_") and "box_check" in name:
        return dataset_checks_root(environment).joinpath(name, *tail)
    if name.startswith("paper_"):
        return campaigns_root(environment).joinpath(name, *tail)
    if name == "scenario_videos" or name.endswith(".mp4"):
        return videos_root(environment).joinpath(name, *tail)
    if name.startswith("sensor_coverage"):
        return sensor_coverage_root(environment).joinpath(name, *tail)
    if name.startswith("report_"):
        return report_support_root(environment).joinpath(name, *tail)
    return diagnostics_root(environment).joinpath(name, *tail)


def legacy_workspace_path(value: Union[str, Path], environment=None) -> Optional[Path]:
    """Map a known historical repository-relative path into the workspace."""

    path = Path(value)
    parts = list(path.parts)
    if parts and parts[0] == "aeb":
        parts = parts[1:]
    if not parts:
        return None

    first, tail = parts[0], parts[1:]
    if first in _DATASET_DESTINATIONS:
        return dataset_root(first, environment).joinpath(*tail)
    if first == "logs":
        return logs_root(environment).joinpath(*tail)
    if first == "training_runs":
        return training_root(environment).joinpath(*tail)
    if first == "outputs":
        return _output_destination(tail, environment)
    return None


def resolve_project_path(
    value: Union[str, Path],
    *,
    project_root: Path = CARLA_ROOT,
    aeb_root: Path = AEB_ROOT,
    environment=None,
) -> Path:
    """Resolve explicit, legacy and workspace paths in a predictable order."""

    path = Path(value).expanduser()
    if path.is_absolute():
        return path

    candidates = (project_root / path, aeb_root / path)
    for candidate in candidates:
        if candidate.exists():
            return candidate

    mapped = legacy_workspace_path(path, environment)
    if mapped is not None:
        return mapped
    return project_root / path


def workspace_directories(environment=None):
    """Return named top-level locations for checks and metadata."""

    return {
        "workspace": workspace_root(environment),
        "datasets_active": workspace_root(environment) / "datasets" / "active",
        "datasets_archive": workspace_root(environment) / "datasets" / "archive",
        "logs": logs_root(environment),
        "campaigns": campaigns_root(environment),
        "videos": videos_root(environment),
        "sensor_coverage": sensor_coverage_root(environment),
        "dataset_box_checks": dataset_checks_root(environment),
        "diagnostics": diagnostics_root(environment),
        "report_support": report_support_root(environment),
        "training": training_root(environment),
        "environments": environments_root(environment),
        "quarantine": quarantine_root(environment),
    }
