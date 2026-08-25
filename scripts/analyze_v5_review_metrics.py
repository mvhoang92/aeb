#!/usr/bin/env python3
"""Derive scenario-level and severity metrics requested by paper-v5 review.

This script does not alter the frozen campaign or rerun CARLA. It reads the
checked final summaries/tick CSV and writes a separate derived-evidence folder.
"""

from __future__ import annotations

import csv
import json
import math
import shutil
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = "paper_v4_gpu_final_locked_20260825"
LOG_ROOT = ROOT / "logs"
OUT = ROOT / "docs" / "log" / "repeatability" / "paper_v5_derived"
CONFIGS = ("radar_only", "hard_gate", "safe_fallback")
CORE_SUITES = (
    "system_limit_extended_sweep",
    "radar_only_regression",
    "fusion_physical_false_positive_v2",
    "fusion_nonvehicle_hazard_limitation",
)


def load_json(path):
    with path.open() as stream:
        return json.load(stream)


def as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes")


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def wilson(successes, total, z=1.96):
    if not total:
        return (None, None)
    p = successes / float(total)
    den = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / den
    half = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / den
    return (max(0.0, center - half), min(1.0, center + half))


def percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * q
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return values[low]
    return values[low] + (values[high] - values[low]) * (pos - low)


def fmt(value, digits=3):
    return "" if value is None else round(float(value), digits)


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def job_dir(job):
    return LOG_ROOT / (CAMPAIGN + "_" + job)


def summary_rows(job):
    return load_json(job_dir(job) / "summary.json")


def named_metrics(config, scope, jobs):
    groups = defaultdict(list)
    for job in jobs:
        for row in summary_rows(job):
            groups[(job, str(row["scenario_id"]))].append(row)
    decisions = []
    for (job, scenario), rows in sorted(groups.items()):
        expected = {as_bool(row["expected_brake"]) for row in rows}
        predicted = {as_bool(row["brake_activated"]) for row in rows}
        statuses = {str(row["status"]) for row in rows}
        collisions = {as_bool(row["collision"]) for row in rows}
        if len(expected) != 1 or len(predicted) != 1 or len(statuses) != 1 or len(collisions) != 1:
            raise RuntimeError("Mixed repeated outcome for {} {}".format(job, scenario))
        decisions.append((expected.pop(), predicted.pop(), statuses.pop() == "PASS", collisions.pop()))
    tp = sum(expected and predicted for expected, predicted, _, _ in decisions)
    fp = sum(not expected and predicted for expected, predicted, _, _ in decisions)
    tn = sum(not expected and not predicted for expected, predicted, _, _ in decisions)
    fn = sum(expected and not predicted for expected, predicted, _, _ in decisions)
    precision = tp / float(tp + fp) if tp + fp else None
    recall = tp / float(tp + fn) if tp + fn else None
    p_lo, p_hi = wilson(tp, tp + fp)
    r_lo, r_hi = wilson(tp, tp + fn)
    return {
        "scope": scope,
        "config": config,
        "named_conditions": len(decisions),
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "precision": fmt(precision, 4),
        "precision_ci95_low": fmt(p_lo, 4),
        "precision_ci95_high": fmt(p_hi, 4),
        "recall": fmt(recall, 4),
        "recall_ci95_low": fmt(r_lo, 4),
        "recall_ci95_high": fmt(r_hi, 4),
        "pass_conditions": sum(passed for _, _, passed, _ in decisions),
        "collision_conditions": sum(collision for _, _, _, collision in decisions),
    }


def named_status_map(jobs):
    output = {}
    for job in jobs:
        grouped = defaultdict(list)
        for row in summary_rows(job):
            grouped[str(row["scenario_id"])].append(row)
        for scenario, rows in grouped.items():
            status = {row["status"] == "PASS" for row in rows}
            if len(status) != 1:
                raise RuntimeError("Mixed status for {} {}".format(job, scenario))
            # Strip policy prefix so paired policy jobs use the same key.
            suite = job
            for config in CONFIGS:
                prefix = config + "_"
                if suite.startswith(prefix):
                    suite = suite[len(prefix) :]
            if suite.startswith("holdout_"):
                suite = "holdout"
            output[(suite, scenario)] = status.pop()
    return output


def paired_named(scope, policy_a, jobs_a, policy_b, jobs_b):
    a = named_status_map(jobs_a)
    b = named_status_map(jobs_b)
    common = sorted(set(a) & set(b))
    return {
        "scope": scope,
        "policy_a": policy_a,
        "policy_b": policy_b,
        "paired_named_conditions": len(common),
        "both_pass": sum(a[key] and b[key] for key in common),
        "a_only_pass": sum(a[key] and not b[key] for key in common),
        "b_only_pass": sum(not a[key] and b[key] for key in common),
        "both_fail": sum(not a[key] and not b[key] for key in common),
    }


def read_ticks(job, row):
    path = job_dir(job) / str(row["log_file"])
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def collision_record(config, scope, job, summary):
    ticks = read_ticks(job, summary)
    first_collision = next(
        (index for index, tick in enumerate(ticks) if (as_float(tick.get("collision_count")) or 0) > 0),
        None,
    )
    if first_collision is None:
        return None
    before = ticks[max(0, first_collision - 1)]
    at = ticks[first_collision]
    return {
        "scope": scope,
        "config": config,
        "scenario_id": summary["scenario_id"],
        "run_index": summary.get("run_index", 1),
        "brake_activated": as_bool(summary["brake_activated"]),
        "first_brake_s": summary.get("first_brake_s"),
        "first_brake_gap_m": summary.get("brake_gap_m"),
        "preimpact_speed_kph": fmt(as_float(before.get("ego_speed_kph"))),
        "collision_tick_speed_kph": fmt(as_float(at.get("ego_speed_kph"))),
        "preimpact_elapsed_s": fmt(as_float(before.get("elapsed_s"))),
        "note": "preimpact speed is the last 0.05-s tick before first collision_count>0",
    }


def false_brake_record(config, job, summary):
    if as_bool(summary["expected_brake"]) or not as_bool(summary["brake_activated"]):
        return None
    ticks = read_ticks(job, summary)
    brake_ticks = [tick for tick in ticks if as_bool(tick.get("aeb_override"))]
    if not brake_ticks:
        return None
    onset = brake_ticks[0]
    start = as_float(onset.get("elapsed_s")) or 0.0
    valid = [
        tick
        for tick in brake_ticks
        if (as_float(tick.get("elapsed_s")) or 0.0) >= max(0.25, start)
        and (as_float(tick.get("ego_speed_kph")) or 0.0) >= 1.0
        and not as_bool(tick.get("collision_count"))
    ]
    decels = [-(as_float(tick.get("ego_acceleration_mps2")) or 0.0) for tick in valid]
    speed_values = [as_float(tick.get("ego_speed_kph")) for tick in ticks]
    speed_values = [value for value in speed_values if value is not None]
    return {
        "config": config,
        "scenario_id": summary["scenario_id"],
        "run_index": summary.get("run_index", 1),
        "first_brake_s": fmt(start),
        "onset_speed_kph": fmt(as_float(onset.get("ego_speed_kph"))),
        "brake_duration_s": fmt(len(brake_ticks) * 0.05),
        "peak_deceleration_mps2": fmt(max(decels) if decels else None),
        "minimum_logged_speed_kph": fmt(min(speed_values) if speed_values else None),
        "stopped_below_1kph": bool(speed_values and min(speed_values) < 1.0),
    }


def aggregate_severity(records, keys, value_fields):
    groups = defaultdict(list)
    for row in records:
        groups[tuple(row[key] for key in keys)].append(row)
    output = []
    for key_values, rows in sorted(groups.items()):
        item = dict(zip(keys, key_values))
        item["runs"] = len(rows)
        for field in value_fields:
            values = [as_float(row.get(field)) for row in rows]
            values = [value for value in values if value is not None]
            item[field + "_median"] = fmt(statistics.median(values) if values else None)
            item[field + "_min"] = fmt(min(values) if values else None)
            item[field + "_max"] = fmt(max(values) if values else None)
        if "stopped_below_1kph" in rows[0]:
            item["stopped_runs"] = sum(bool(row["stopped_below_1kph"]) for row in rows)
        output.append(item)
    return output


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    core_jobs = {
        config: [config + "_" + suite for suite in CORE_SUITES]
        for config in CONFIGS
    }
    holdout_jobs = {config: ["holdout_" + config] for config in CONFIGS}
    perturbation_jobs = {config: ["perturbation_" + config] for config in CONFIGS}
    degradation_jobs = {
        "hard_gate": ["degradation_hard_gate_camera_off"],
        "safe_fallback": ["degradation_safe_fallback_camera_off"],
    }

    named = []
    for config in CONFIGS:
        named.append(named_metrics(config, "core_without_synthetic_fault", core_jobs[config]))
        named.append(named_metrics(config, "perturbation", perturbation_jobs[config]))
        named.append(named_metrics(config, "frozen_adverse_holdout", holdout_jobs[config]))
    for config in ("hard_gate", "safe_fallback"):
        named.append(named_metrics(config, "camera_disabled", degradation_jobs[config]))

    paired = []
    for scope, jobs in (("core_without_synthetic_fault", core_jobs), ("frozen_adverse_holdout", holdout_jobs)):
        for policy_a, policy_b in (("radar_only", "hard_gate"), ("radar_only", "safe_fallback"), ("hard_gate", "safe_fallback")):
            paired.append(paired_named(scope, policy_a, jobs[policy_a], policy_b, jobs[policy_b]))

    collisions = []
    for scope, jobs in (("core_without_synthetic_fault", core_jobs), ("frozen_adverse_holdout", holdout_jobs)):
        for config in CONFIGS:
            for job in jobs[config]:
                for summary in summary_rows(job):
                    if as_bool(summary.get("collision")):
                        record = collision_record(config, scope, job, summary)
                        if record:
                            collisions.append(record)

    false_brakes = []
    for config in CONFIGS:
        job = holdout_jobs[config][0]
        for summary in summary_rows(job):
            record = false_brake_record(config, job, summary)
            if record:
                false_brakes.append(record)

    collision_summary = aggregate_severity(
        collisions,
        ("scope", "config", "scenario_id"),
        ("preimpact_speed_kph", "first_brake_s", "first_brake_gap_m"),
    )
    false_summary = aggregate_severity(
        false_brakes,
        ("config", "scenario_id"),
        ("onset_speed_kph", "brake_duration_s", "peak_deceleration_mps2", "minimum_logged_speed_kph"),
    )

    write_csv(OUT / "named_scenario_metrics.csv", named)
    write_csv(OUT / "named_paired_outcomes.csv", paired)
    write_csv(OUT / "collision_severity_runs.csv", collisions)
    write_csv(OUT / "collision_severity_summary.csv", collision_summary)
    write_csv(OUT / "false_brake_severity_runs.csv", false_brakes)
    write_csv(OUT / "false_brake_severity_summary.csv", false_summary)

    core = {row["config"]: row for row in named if row["scope"] == "core_without_synthetic_fault"}
    holdout = {row["config"]: row for row in named if row["scope"] == "frozen_adverse_holdout"}
    figure_dir = OUT / "figures"
    figure_dir.mkdir(exist_ok=True)
    labels = {"radar_only": "Radar-only", "hard_gate": "Hard gate", "safe_fallback": "Fallback"}
    colors = {"radar_only": "#4C78A8", "hard_gate": "#F58518", "safe_fallback": "#54A24B"}
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.5))
    for config in CONFIGS:
        row = core[config]
        axes[0].errorbar(
            row["recall"], row["precision"],
            xerr=[[row["recall"] - row["recall_ci95_low"]], [row["recall_ci95_high"] - row["recall"]]],
            yerr=[[row["precision"] - row["precision_ci95_low"]], [row["precision_ci95_high"] - row["precision"]]],
            fmt="o", capsize=3, color=colors[config], label=labels[config],
        )
    axes[0].set(xlim=(0.88, 1.01), ylim=(0.82, 1.01), xlabel="Recall", ylabel="Precision", title="Core: 105 named conditions")
    axes[0].grid(alpha=0.25)
    axes[0].legend(fontsize=7, loc="lower left")
    x = list(range(3))
    passes = [holdout[config]["pass_conditions"] for config in CONFIGS]
    axes[1].bar(x, passes, color=[colors[config] for config in CONFIGS])
    axes[1].set_xticks(x, [labels[config] for config in CONFIGS], rotation=12)
    axes[1].set(ylim=(0, 14), ylabel="PASS conditions", title="Frozen adverse hold-out (N=14)")
    axes[1].grid(axis="y", alpha=0.25)
    for xpos, value in zip(x, passes):
        axes[1].text(xpos, value + 0.25, "{}/14".format(value), ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(str(figure_dir / "scenario_level_tradeoff.png"), dpi=240)
    fig.savefig(str(figure_dir / "scenario_level_tradeoff.pdf"))
    plt.close(fig)
    paper_figure_dir = ROOT / "paper" / "paper_v5" / "figures"
    paper_figure_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        str(figure_dir / "scenario_level_tradeoff.png"),
        str(paper_figure_dir / "scenario_level_tradeoff.png"),
    )

    ghost = aggregate_severity(
        false_brakes,
        ("config",),
        ("onset_speed_kph", "brake_duration_s", "peak_deceleration_mps2", "minimum_logged_speed_kph"),
    )
    physical = [
        row for row in collision_summary
        if row["scope"] == "frozen_adverse_holdout"
        and row["scenario_id"] in {
            "holdout_cart_center_v50_g18",
            "holdout_bench_center_v60_g22",
            "holdout_warning_center_v70_g25",
        }
    ]

    lines = [
        "# Paper v5 reviewer-derived evidence",
        "",
        "No CARLA run was added or removed. Metrics are derived from the frozen campaign tick logs.",
        "",
        "## Named-condition confusion (primary statistical unit)",
        "",
        "| Scope | Policy | N | TP | FP | TN | FN | Precision (95% Wilson) | Recall (95% Wilson) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scope_rows in (core, holdout):
        for config in CONFIGS:
            row = scope_rows[config]
            lines.append(
                "| {} | {} | {} | {} | {} | {} | {} | {:.3f} [{:.3f}, {:.3f}] | {:.3f} [{:.3f}, {:.3f}] |".format(
                    row["scope"], config, row["named_conditions"], row["TP"], row["FP"], row["TN"], row["FN"],
                    row["precision"], row["precision_ci95_low"], row["precision_ci95_high"],
                    row["recall"], row["recall_ci95_low"], row["recall_ci95_high"],
                )
            )
    lines.extend(["", "## False-brake severity on adverse hold-out", ""])
    for row in ghost:
        lines.append(
            "- {}: {} false-brake runs; median onset {:.1f} km/h, duration {:.2f} s, peak deceleration {:.2f} m/s^2; {}/{} stopped below 1 km/h.".format(
                row["config"], row["runs"], row["onset_speed_kph_median"], row["brake_duration_s_median"],
                row["peak_deceleration_mps2_median"], row["stopped_runs"], row["runs"]
            )
        )
    lines.extend([
        "",
        "Binary FP counts therefore represent full simulated emergency stops in these injected-ghost cases, not one-tick brake pulses.",
        "",
        "## Physical hold-out collision severity",
        "",
        "Pre-impact speed is the ego speed at the last 0.05-s tick before the first collision event.",
        "",
        "| Policy | Scenario | Runs | Median pre-impact speed | Median first-brake gap |",
        "|---|---|---:|---:|---:|",
    ])
    for row in physical:
        lines.append(
            "| {} | {} | {} | {:.2f} km/h | {} |".format(
                row["config"], row["scenario_id"], row["runs"], row["preimpact_speed_kph_median"],
                "no brake" if row["first_brake_gap_m_median"] == "" else "{:.2f} m".format(row["first_brake_gap_m_median"]),
            )
        )
    lines.extend([
        "",
        "## Scoring definition audited from the frozen runner",
        "",
        "- `brake_activated`: at least one logged tick with `aeb_override=true`.",
        "- Brake confusion compares this binary event with the scenario's preassigned `expected_brake` label.",
        "- Collision is true when any logged tick has `collision_count>0`; final scenarios normally set `expected_collision=false`.",
        "- `PASS` requires brake and collision expectations to match. Positive non-collision scenarios additionally require minimum bumper gap >= the configured threshold (default 0.5 m); selected scenarios also enforce lane/target assertions.",
        "- Collision and PASS remain separate from brake TP/FN because a brake may activate too late.",
    ])
    (OUT / "V5_REVIEW_DERIVED_EVIDENCE.md").write_text("\n".join(lines) + "\n")
    print("Wrote paper-v5 derived evidence to {}".format(OUT))


if __name__ == "__main__":
    main()
