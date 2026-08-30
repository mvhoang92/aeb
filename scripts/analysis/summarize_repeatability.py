#!/usr/bin/env python3
"""Summarize repeated AEB scenario runs for paper/report evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional


NUMERIC_FIELDS = (
    "first_brake_s",
    "brake_gap_m",
    "minimum_bumper_gap_m",
    "maximum_deceleration_mps2",
    "maximum_abs_jerk_mps3",
    "target_confirmed_rate_pct",
    "radar_target_hazard_match_rate_pct",
)


def scenario_family(scenario_id: str) -> str:
    if scenario_id.startswith("ccrm_"):
        return "CCRm"
    if scenario_id.startswith("ccrb_"):
        return "CCRb"
    if scenario_id.startswith("cutin_"):
        return "Cut-in"
    if scenario_id.startswith("ccrs_"):
        return "CCRs"
    return scenario_id.split("_", 1)[0]


def parse_float(value: str) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"--", "None", "nan", "NaN", "inf", "Infinity"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def stats(values: Iterable[float]) -> Dict[str, Optional[float]]:
    data = list(values)
    if not data:
        return {"mean": None, "std": None, "min": None, "max": None, "range": None}
    return {
        "mean": statistics.mean(data),
        "std": statistics.pstdev(data) if len(data) > 1 else 0.0,
        "min": min(data),
        "max": max(data),
        "range": max(data) - min(data),
    }


def fmt(value: Optional[float], digits: int = 3) -> str:
    if value is None:
        return "--"
    return ("{:." + str(digits) + "f}").format(value)


def read_summary(run_dir: Path) -> List[dict]:
    summary_path = run_dir / "summary.csv"
    if not summary_path.is_file():
        raise FileNotFoundError("Missing summary.csv: {}".format(summary_path))
    with summary_path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def scenario_rows(rows: List[dict]) -> List[dict]:
    by_scenario = defaultdict(list)
    for row in rows:
        by_scenario[row["scenario_id"]].append(row)

    output = []
    for scenario_id in sorted(by_scenario):
        items = by_scenario[scenario_id]
        status_counts = Counter(item.get("status", "") for item in items)
        collision_count = sum(1 for item in items if item.get("collision") == "True")
        brake_count = sum(1 for item in items if item.get("brake_activated") == "True")
        row = {
            "scenario_id": scenario_id,
            "family": scenario_family(scenario_id),
            "runs": len(items),
            "pass": status_counts.get("PASS", 0),
            "fail": status_counts.get("FAIL", 0),
            "collision": collision_count,
            "brake": brake_count,
            "mixed_outcome": len([k for k, v in status_counts.items() if k and v]) > 1,
        }
        for field in NUMERIC_FIELDS:
            values = [parse_float(item.get(field, "")) for item in items]
            field_stats = stats(value for value in values if value is not None)
            for name, value in field_stats.items():
                row["{}_{}".format(field, name)] = value
        output.append(row)
    return output


def family_rows(rows: List[dict]) -> List[dict]:
    by_family = defaultdict(list)
    for row in rows:
        by_family[scenario_family(row["scenario_id"])].append(row)
    output = []
    for family in sorted(by_family):
        items = by_family[family]
        output.append(
            {
                "family": family,
                "runs": len(items),
                "pass": sum(1 for item in items if item.get("status") == "PASS"),
                "fail": sum(1 for item in items if item.get("status") == "FAIL"),
                "collision": sum(1 for item in items if item.get("collision") == "True"),
                "brake": sum(1 for item in items if item.get("brake_activated") == "True"),
            }
        )
    return output


def write_csv(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_markdown(path: Path, run_dir: Path, rows: List[dict], families: List[dict]) -> None:
    total_runs = sum(row["runs"] for row in rows)
    total_pass = sum(row["pass"] for row in rows)
    total_fail = sum(row["fail"] for row in rows)
    total_collision = sum(row["collision"] for row in rows)
    total_brake = sum(row["brake"] for row in rows)
    all_pass = sum(1 for row in rows if row["pass"] == row["runs"])
    all_fail = sum(1 for row in rows if row["fail"] == row["runs"])
    mixed = [row for row in rows if row["mixed_outcome"]]

    lines = []
    lines.append("# Repeatability Summary")
    lines.append("")
    lines.append("Run directory: `{}`".format(run_dir))
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append("| Scenarios | {} |".format(len(rows)))
    lines.append("| Runs | {} |".format(total_runs))
    lines.append("| PASS runs | {} |".format(total_pass))
    lines.append("| FAIL runs | {} |".format(total_fail))
    lines.append("| Collision runs | {} |".format(total_collision))
    lines.append("| Brake activated runs | {} |".format(total_brake))
    lines.append("| All-PASS scenarios | {} |".format(all_pass))
    lines.append("| All-FAIL scenarios | {} |".format(all_fail))
    lines.append("| Mixed-outcome scenarios | {} |".format(len(mixed)))
    lines.append("")

    lines.append("## By family")
    lines.append("")
    lines.append("| Family | Runs | PASS | FAIL | Collision | Brake |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for row in families:
        lines.append(
            "| {family} | {runs} | {pass} | {fail} | {collision} | {brake} |".format(**row)
        )
    lines.append("")

    lines.append("## Scenario outcomes")
    lines.append("")
    lines.append(
        "| Scenario | Runs | PASS | FAIL | Collision | Brake | First brake mean/std (s) | Brake gap mean/std (m) | Min gap mean/std (m) | Min gap min/max (m) | Hazard match mean (%) |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} | {}/{} | {}/{} | {}/{} | {}/{} | {} |".format(
                row["scenario_id"],
                row["runs"],
                row["pass"],
                row["fail"],
                row["collision"],
                row["brake"],
                fmt(row["first_brake_s_mean"]),
                fmt(row["first_brake_s_std"]),
                fmt(row["brake_gap_m_mean"]),
                fmt(row["brake_gap_m_std"]),
                fmt(row["minimum_bumper_gap_m_mean"]),
                fmt(row["minimum_bumper_gap_m_std"]),
                fmt(row["minimum_bumper_gap_m_min"]),
                fmt(row["minimum_bumper_gap_m_max"]),
                fmt(row["radar_target_hazard_match_rate_pct_mean"], 1),
            )
        )
    lines.append("")

    variable = sorted(
        rows,
        key=lambda row: row.get("minimum_bumper_gap_m_std") or 0.0,
        reverse=True,
    )[:10]
    lines.append("## Largest minimum-gap variation")
    lines.append("")
    lines.append("| Scenario | Mean min gap | Std | Range | Min | Max |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for row in variable:
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} |".format(
                row["scenario_id"],
                fmt(row["minimum_bumper_gap_m_mean"]),
                fmt(row["minimum_bumper_gap_m_std"]),
                fmt(row["minimum_bumper_gap_m_range"]),
                fmt(row["minimum_bumper_gap_m_min"]),
                fmt(row["minimum_bumper_gap_m_max"]),
            )
        )
    lines.append("")

    if mixed:
        lines.append("## Mixed-outcome scenarios")
        lines.append("")
        for row in mixed:
            lines.append("- `{}`: PASS {}, FAIL {}".format(row["scenario_id"], row["pass"], row["fail"]))
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="Directory containing summary.csv")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated repeatability_summary.* files. Defaults to run_dir.",
    )
    args = parser.parse_args()

    rows = read_summary(args.run_dir)
    scenarios = scenario_rows(rows)
    families = family_rows(rows)
    output_dir = args.output_dir or args.run_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    write_csv(output_dir / "repeatability_by_scenario.csv", scenarios)
    write_csv(output_dir / "repeatability_by_family.csv", families)
    write_markdown(output_dir / "repeatability_summary.md", args.run_dir, scenarios, families)
    with (output_dir / "repeatability_summary.json").open("w", encoding="utf-8") as stream:
        json.dump({"scenarios": scenarios, "families": families}, stream, indent=2)

    print("Wrote repeatability summary to {}".format(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
