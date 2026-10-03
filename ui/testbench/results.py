"""Read-only parsing of run directories and paired comparison (no Tk).

A run directory is written by ``scripts/run_*_aeb_scenarios.py``:
``run_metadata.json`` (command, configs, SHA-256, git state, ...),
``summary.json``/``summary.csv`` (one row per scenario-run) and
``aggregate_summary.*``.  Nothing here writes to it.
"""

from __future__ import absolute_import

import csv
import json
import os
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from ui.testbench.policies import classify_run, run_label, short_run_label


OUTCOME_PASS = "pass"
OUTCOME_FAIL = "fail"
OUTCOME_MIXED = "mixed"

_TRUE = ("true", "1", "yes")


def _bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in _TRUE


def _float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_json(path):
    try:
        with open(str(path), encoding="utf-8") as stream:
            return json.load(stream)
    except (IOError, OSError, ValueError):
        return None


class RunInfo(object):
    """One run directory, described from its metadata (or file times)."""

    def __init__(self, path, metadata):
        self.path = Path(path)
        self.run_id = self.path.name
        self.metadata = metadata or {}
        meta = self.metadata
        self.has_metadata = bool(metadata)
        created = meta.get("created_at")
        self.created_at = None
        if created:
            try:
                self.created_at = datetime.strptime(str(created)[:19], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                self.created_at = None
        try:
            self.mtime = os.path.getmtime(str(self.path))
        except OSError:
            self.mtime = 0.0
        if self.created_at is None and self.mtime:
            self.created_at = datetime.fromtimestamp(self.mtime)
        self.command = str(meta.get("command") or "")
        self.sensor_config = str(meta.get("sensor_config") or "")
        self.scenario_config = str(meta.get("scenario_config") or "")
        self.control_mode = str(meta.get("control_mode") or "")
        self.repeat = meta.get("repeat")
        self.seed = meta.get("seed")
        self.passed = meta.get("passed")
        self.failed = meta.get("failed")
        self.completed = meta.get("completed_scenario_runs")
        self.policy_key, self.device = classify_run(
            self.command,
            self.sensor_config,
            meta.get("model_providers_configured"),
        )
        self.policy_label = run_label(self.policy_key, self.device, self.sensor_config)

    @property
    def sort_time(self):
        if self.created_at is not None:
            return self.created_at.timestamp()
        return self.mtime

    @property
    def suite_name(self):
        return self.scenario_config.rsplit("/", 1)[-1] if self.scenario_config else ""

    @property
    def suite_stem(self):
        name = self.suite_name
        return name[:-5] if name.endswith(".yaml") else name

    @property
    def short_label(self):
        return short_run_label(self.policy_key, self.device)

    @property
    def short_date_text(self):
        if self.created_at is None:
            return ""
        return self.created_at.strftime("%y-%m-%d %H:%M")

    @property
    def pass_text(self):
        if self.passed is None or self.completed is None:
            return "—"
        return "{}/{}".format(self.passed, self.completed)

    @property
    def date_text(self):
        if self.created_at is None:
            return ""
        return self.created_at.strftime("%Y-%m-%d %H:%M")


def list_runs(logs_root):
    """Run directories under ``logs_root``, newest first."""
    root = Path(logs_root)
    if not root.is_dir():
        return []
    runs = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        metadata = _read_json(entry / "run_metadata.json")
        if metadata is None and not (entry / "summary.json").exists() and not (
            entry / "summary.csv"
        ).exists():
            continue
        runs.append(RunInfo(entry, metadata if isinstance(metadata, dict) else None))
    runs.sort(key=lambda run: (run.sort_time, run.run_id), reverse=True)
    return runs


def normalize_row(row):
    return OrderedDict(
        (
            ("scenario_id", str(row.get("scenario_id", ""))),
            ("run_index", int(_float(row.get("run_index")) or 1)),
            ("status", str(row.get("status", "")).upper()),
            ("expected_brake", _bool(row.get("expected_brake"))),
            ("brake_activated", _bool(row.get("brake_activated"))),
            ("expected_collision", _bool(row.get("expected_collision"))),
            ("collision", _bool(row.get("collision"))),
            ("minimum_bumper_gap_m", _float(row.get("minimum_bumper_gap_m"))),
            ("first_brake_s", _float(row.get("first_brake_s"))),
            ("brake_speed_kph", _float(row.get("brake_speed_kph"))),
            ("maximum_deceleration_mps2", _float(row.get("maximum_deceleration_mps2"))),
            ("radar_fallback_activated", _bool(row.get("radar_fallback_activated"))),
            ("fusion_blocked_tick_count", int(_float(row.get("fusion_blocked_tick_count")) or 0)),
            ("failure_reason", str(row.get("failure_reason") or "")),
            ("description", str(row.get("description") or "")),
        )
    )


def load_summaries(run_dir):
    """Normalised scenario-run rows from ``summary.json`` (or ``summary.csv``)."""
    run_dir = Path(run_dir)
    data = _read_json(run_dir / "summary.json")
    rows = []
    if isinstance(data, list):
        rows = [row for row in data if isinstance(row, dict)]
    elif (run_dir / "summary.csv").exists():
        with open(str(run_dir / "summary.csv"), encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
    return [normalize_row(row) for row in rows]


def totals(rows):
    """PASS count and brake confusion matrix (positive = brake expected)."""
    result = OrderedDict(
        (
            ("total", len(rows)),
            ("passed", 0),
            ("failed", 0),
            ("tp", 0),
            ("fp", 0),
            ("tn", 0),
            ("fn", 0),
            ("collisions", 0),
            ("fallback_runs", 0),
        )
    )
    for row in rows:
        if row["status"] == "PASS":
            result["passed"] += 1
        else:
            result["failed"] += 1
        expected = row["expected_brake"]
        braked = row["brake_activated"]
        if expected and braked:
            result["tp"] += 1
        elif expected and not braked:
            result["fn"] += 1
        elif braked:
            result["fp"] += 1
        else:
            result["tn"] += 1
        if row["collision"]:
            result["collisions"] += 1
        if row["radar_fallback_activated"]:
            result["fallback_runs"] += 1
    predicted = result["tp"] + result["fp"]
    actual = result["tp"] + result["fn"]
    result["precision"] = (float(result["tp"]) / predicted) if predicted else None
    result["recall"] = (float(result["tp"]) / actual) if actual else None
    return result


def condition_outcomes(rows):
    """``{scenario_id: pass|fail|mixed}`` over repeats of each named condition."""
    statuses = OrderedDict()
    for row in rows:
        statuses.setdefault(row["scenario_id"], []).append(row["status"] == "PASS")
    outcomes = OrderedDict()
    for scenario_id, passes in statuses.items():
        if all(passes):
            outcomes[scenario_id] = OUTCOME_PASS
        elif not any(passes):
            outcomes[scenario_id] = OUTCOME_FAIL
        else:
            outcomes[scenario_id] = OUTCOME_MIXED
    return outcomes


def paired_comparison(rows_a, rows_b):
    """Descriptive 2x2 table on named conditions shared by two runs.

    Same logic as the paper's paired (McNemar) table: a condition passes when
    all its repeats pass.  Conditions with mixed repeats are counted apart
    instead of being forced into a cell; no p-value is computed here.
    """
    outcome_a = condition_outcomes(rows_a)
    outcome_b = condition_outcomes(rows_b)
    common = [key for key in outcome_a if key in outcome_b]
    table = OrderedDict(
        (
            ("both_pass", []),
            ("a_only_pass", []),
            ("b_only_pass", []),
            ("both_fail", []),
            ("mixed", []),
        )
    )
    for key in common:
        a = outcome_a[key]
        b = outcome_b[key]
        if OUTCOME_MIXED in (a, b):
            table["mixed"].append(key)
        elif a == OUTCOME_PASS and b == OUTCOME_PASS:
            table["both_pass"].append(key)
        elif a == OUTCOME_PASS:
            table["a_only_pass"].append(key)
        elif b == OUTCOME_PASS:
            table["b_only_pass"].append(key)
        else:
            table["both_fail"].append(key)
    return OrderedDict(
        (
            ("common", common),
            ("only_in_a", [key for key in outcome_a if key not in outcome_b]),
            ("only_in_b", [key for key in outcome_b if key not in outcome_a]),
            ("table", table),
            ("outcome_a", outcome_a),
            ("outcome_b", outcome_b),
        )
    )


def find_run(runs, run_id):
    for run in runs:
        if run.run_id == run_id:
            return run
    return None
