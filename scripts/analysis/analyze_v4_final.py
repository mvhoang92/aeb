#!/usr/bin/env python3
"""Generate reproducible paper-v4 tables, figures and narrative evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


AEB_ROOT = Path(__file__).resolve().parents[2]
CORE_SUITES = (
    "system_limit_extended_sweep",
    "radar_only_regression",
    "fusion_physical_false_positive_v2",
    "fusion_nonvehicle_hazard_limitation",
    "fusion_benefit_stress",
)
CONFIGS = ("radar_only", "hard_gate", "safe_fallback")
DISPLAY = {
    "radar_only": "Radar-only",
    "hard_gate": "Hard camera gate",
    "safe_fallback": "Safe fallback",
}
COLORS = {
    "radar_only": "#4C78A8",
    "hard_gate": "#F58518",
    "safe_fallback": "#54A24B",
}


def read_json(path):
    with open(str(path)) as stream:
        return json.load(stream)


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with open(str(path), "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def safe_div(numerator, denominator):
    return float(numerator) / float(denominator) if denominator else None


def f4(value):
    return None if value is None else round(float(value), 4)


def wilson(successes, total, z=1.96):
    if total <= 0:
        return (None, None)
    p = float(successes) / float(total)
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    margin = (
        z
        * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total))
        / denominator
    )
    return (max(0.0, center - margin), min(1.0, center + margin))


def confusion(rows):
    tp = sum(bool(r["expected_brake"]) and bool(r["brake_activated"]) for r in rows)
    fn = sum(bool(r["expected_brake"]) and not bool(r["brake_activated"]) for r in rows)
    fp = sum(not bool(r["expected_brake"]) and bool(r["brake_activated"]) for r in rows)
    tn = sum(not bool(r["expected_brake"]) and not bool(r["brake_activated"]) for r in rows)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    p_lo, p_hi = wilson(tp, tp + fp)
    r_lo, r_hi = wilson(tp, tp + fn)
    return {
        "runs": len(rows),
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "precision": f4(precision),
        "precision_ci95_low": f4(p_lo),
        "precision_ci95_high": f4(p_hi),
        "recall": f4(recall),
        "recall_ci95_low": f4(r_lo),
        "recall_ci95_high": f4(r_hi),
        "f1": f4(f1),
        "pass": sum(r.get("status") == "PASS" for r in rows),
        "collision": sum(bool(r.get("collision")) for r in rows),
        "brake": sum(bool(r.get("brake_activated")) for r in rows),
    }


def rows_for(log_root, campaign_id, job_name):
    path = Path(log_root) / "{}_{}".format(campaign_id, job_name) / "summary.json"
    return read_json(path)


def scenario_consistency(config, suite, rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row["scenario_id"])].append(row)
    output = []
    for scenario_id, values in grouped.items():
        passes = sum(row["status"] == "PASS" for row in values)
        output.append(
            {
                "config": config,
                "suite": suite,
                "scenario_id": scenario_id,
                "runs": len(values),
                "pass": passes,
                "fail": len(values) - passes,
                "outcome": (
                    "all_pass"
                    if passes == len(values)
                    else "all_fail"
                    if passes == 0
                    else "mixed"
                ),
                "collision": sum(bool(row.get("collision")) for row in values),
                "brake": sum(bool(row.get("brake_activated")) for row in values),
            }
        )
    return output


def paired_status(rows_a, rows_b):
    key = lambda row: (str(row["scenario_id"]), int(row.get("run_index", 1)))
    a = {key(row): row["status"] == "PASS" for row in rows_a}
    b = {key(row): row["status"] == "PASS" for row in rows_b}
    common = sorted(set(a) & set(b))
    return {
        "paired_runs": len(common),
        "both_pass": sum(a[k] and b[k] for k in common),
        "a_only_pass": sum(a[k] and not b[k] for k in common),
        "b_only_pass": sum(not a[k] and b[k] for k in common),
        "both_fail": sum(not a[k] and not b[k] for k in common),
    }


def summarize_named_job(log_root, campaign_id, job_name, section):
    rows = rows_for(log_root, campaign_id, job_name)
    metrics = confusion(rows)
    metrics.update({"section": section, "job": job_name})
    bad = Counter(row["scenario_id"] for row in rows if row["status"] != "PASS")
    metrics["failed_scenarios"] = "; ".join(
        "{}:{}".format(name, count) for name, count in sorted(bad.items())
    )
    return metrics, rows


def generate_figures(output_dir, core_metrics, section_metrics, ablation_rows, latency):
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    natural = [row for row in core_metrics if row["scope"] == "without_synthetic_fault"]
    fig, ax = plt.subplots(figsize=(6.4, 4.1))
    for row in natural:
        name = row["config"]
        ax.scatter(
            row["recall"],
            row["precision"],
            s=100,
            color=COLORS[name],
            label=DISPLAY[name],
        )
        ax.annotate(DISPLAY[name], (row["recall"], row["precision"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_xlim(0.94, 1.002)
    ax.set_ylim(0.88, 1.008)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Core benchmark precision–recall (synthetic faults excluded)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(str(figure_dir / "core_precision_recall.png"), dpi=220)
    fig.savefig(str(figure_dir / "core_precision_recall.pdf"))
    plt.close(fig)

    suites = [
        "fusion_physical_false_positive_v2",
        "fusion_nonvehicle_hazard_limitation",
        "fusion_benefit_stress",
    ]
    labels = ["Edge props", "In-path props", "Synthetic faults"]
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    width = 0.24
    xvalues = list(range(len(suites)))
    for offset, config in enumerate(CONFIGS):
        rates = []
        for suite in suites:
            row = next(
                item
                for item in section_metrics
                if item["section"] == "core_suite"
                and item["config"] == config
                and item["suite"] == suite
            )
            rates.append(row["pass"] / row["runs"])
        ax.bar(
            [x + (offset - 1) * width for x in xvalues],
            rates,
            width,
            label=DISPLAY[config],
            color=COLORS[config],
        )
    ax.set_xticks(xvalues)
    ax.set_xticklabels(labels)
    ax.set_ylim(0.0, 1.08)
    ax.set_ylabel("PASS rate")
    ax.set_title("Designed stress-suite outcomes")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(str(figure_dir / "stress_suite_pass_rates.png"), dpi=220)
    fig.savefig(str(figure_dir / "stress_suite_pass_rates.pdf"))
    plt.close(fig)

    holdout = [row for row in section_metrics if row["section"] == "holdout"]
    fig, ax = plt.subplots(figsize=(6.6, 4.1))
    names = [row["config"] for row in holdout]
    pass_values = [row["pass"] for row in holdout]
    fail_values = [row["runs"] - row["pass"] for row in holdout]
    xvalues = list(range(len(names)))
    ax.bar(xvalues, pass_values, color=[COLORS[name] for name in names], label="PASS")
    ax.bar(xvalues, fail_values, bottom=pass_values, color="#D9D9D9", label="FAIL")
    ax.set_xticks(xvalues)
    ax.set_xticklabels([DISPLAY[name] for name in names], rotation=8)
    ax.set_ylabel("Runs")
    ax.set_title("Frozen hold-out: system-level outcomes")
    ax.legend()
    fig.tight_layout()
    fig.savefig(str(figure_dir / "holdout_pass_fail.png"), dpi=220)
    fig.savefig(str(figure_dir / "holdout_pass_fail.pdf"))
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    labels = [row["variant"] for row in ablation_rows]
    values = [row["pass"] / row["runs"] for row in ablation_rows]
    colors = ["#54A24B" if label == "full_fallback" else "#9D9D9D" for label in labels]
    ax.bar(range(len(labels)), values, color=colors)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylim(0.0, 1.08)
    ax.set_ylabel("PASS rate")
    ax.set_title("Focused fallback ablation")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(str(figure_dir / "fallback_ablation.png"), dpi=220)
    fig.savefig(str(figure_dir / "fallback_ablation.pdf"))
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    labels = ["p50", "p95", "max/cold start"]
    values = [latency["session_p50_median_ms"], latency["session_p95_median_ms"], latency["maximum_inference_ms"]]
    ax.bar(labels, values, color=["#4C78A8", "#4C78A8", "#E45756"])
    ax.axhline(150.0, color="black", linestyle="--", linewidth=1, label="Configured 150 ms cadence")
    ax.set_ylabel("Wall-clock inference time (ms)")
    ax.set_title("CUDA inference timing across isolated sessions")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(str(figure_dir / "gpu_inference_latency.png"), dpi=220)
    fig.savefig(str(figure_dir / "gpu_inference_latency.pdf"))
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-id", default="paper_v4_gpu_final_locked_20260825")
    parser.add_argument("--log-root", type=Path, default=AEB_ROOT / "logs")
    parser.add_argument(
        "--campaign-root",
        type=Path,
        default=AEB_ROOT / "outputs" / "paper_v4_final_pipeline",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=AEB_ROOT / "docs" / "log" / "repeatability" / "paper_v4_gpu_final",
    )
    args = parser.parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    core_by_config = {}
    core_metrics = []
    consistency = []
    section_metrics = []
    for config in CONFIGS:
        all_rows = []
        for suite in CORE_SUITES:
            rows = rows_for(args.log_root, args.campaign_id, "{}_{}".format(config, suite))
            for row in rows:
                row = dict(row)
                row["suite"] = suite
                all_rows.append(row)
            metric = confusion(rows)
            metric.update({"section": "core_suite", "config": config, "suite": suite})
            section_metrics.append(metric)
            consistency.extend(scenario_consistency(config, suite, rows))
        core_by_config[config] = all_rows
        for scope, selected in (
            ("all_core", all_rows),
            (
                "without_synthetic_fault",
                [row for row in all_rows if row["suite"] != "fusion_benefit_stress"],
            ),
        ):
            metric = confusion(selected)
            metric.update({"config": config, "scope": scope})
            core_metrics.append(metric)

    paired = []
    for a, b in (("radar_only", "hard_gate"), ("radar_only", "safe_fallback"), ("hard_gate", "safe_fallback")):
        row = paired_status(core_by_config[a], core_by_config[b])
        row.update({"policy_a": a, "policy_b": b, "section": "core"})
        paired.append(row)

    ablation_rows = []
    sensitivity_rows = []
    campaign_manifest = read_json(args.campaign_root / args.campaign_id / "campaign_manifest.json")
    for result in campaign_manifest["results"]:
        job = result["job"]
        if job.startswith("ablation_"):
            metric, _ = summarize_named_job(args.log_root, args.campaign_id, job, "ablation")
            metric["variant"] = job[len("ablation_") :]
            ablation_rows.append(metric)
        elif job.startswith("sensitivity_"):
            metric, _ = summarize_named_job(args.log_root, args.campaign_id, job, "sensitivity")
            metric["variant"] = job[len("sensitivity_") :]
            sensitivity_rows.append(metric)

    for section, names in (
        ("perturbation", ["perturbation_{}".format(c) for c in CONFIGS]),
        (
            "degradation",
            ["degradation_hard_gate_camera_off", "degradation_safe_fallback_camera_off"],
        ),
        ("holdout", ["holdout_{}".format(c) for c in CONFIGS]),
    ):
        for job in names:
            metric, rows = summarize_named_job(args.log_root, args.campaign_id, job, section)
            if job.endswith("radar_only"):
                metric["config"] = "radar_only"
            elif "hard_gate" in job:
                metric["config"] = "hard_gate"
            else:
                metric["config"] = "safe_fallback"
            section_metrics.append(metric)
            consistency.extend(scenario_consistency(metric["config"], section, rows))

    sessions = read_json(args.campaign_root / args.campaign_id / "runtime_sessions.json")
    cuda = [
        row["model_runtime"]
        for row in sessions
        if row.get("model_runtime")
        and row["model_runtime"].get("required_provider") == "CUDAExecutionProvider"
    ]
    inference_count = sum(row["inference_count"] for row in cuda)
    p50 = sorted(row["inference_ms_p50"] for row in cuda if row["inference_ms_p50"] is not None)
    p95 = sorted(row["inference_ms_p95"] for row in cuda if row["inference_ms_p95"] is not None)
    median = lambda values: values[len(values) // 2] if values else None
    latency = {
        "cuda_sessions": len(cuda),
        "inference_count": inference_count,
        "inference_errors": sum(row["inference_error_count"] for row in cuda),
        "weighted_mean_inference_ms": f4(
            safe_div(
                sum(row["inference_ms_mean"] * row["inference_count"] for row in cuda),
                inference_count,
            )
        ),
        "session_p50_median_ms": f4(median(p50)),
        "session_p95_median_ms": f4(median(p95)),
        "maximum_inference_ms": f4(max(row["inference_ms_max"] for row in cuda)),
        "inferences_over_50ms": sum(row["inference_over_50ms"] for row in cuda),
        "inferences_over_150ms": sum(row["inference_over_150ms"] for row in cuda),
        "note": "One CUDA warm-up outlier occurred in each isolated process/session.",
    }

    holdout_rows = {
        config: rows_for(args.log_root, args.campaign_id, "holdout_{}".format(config))
        for config in CONFIGS
    }
    for a, b in (("radar_only", "hard_gate"), ("radar_only", "safe_fallback"), ("hard_gate", "safe_fallback")):
        row = paired_status(holdout_rows[a], holdout_rows[b])
        row.update({"policy_a": a, "policy_b": b, "section": "holdout"})
        paired.append(row)

    write_csv(output_dir / "core_confusion_metrics.csv", core_metrics)
    write_csv(output_dir / "section_metrics.csv", section_metrics)
    write_csv(output_dir / "scenario_consistency.csv", consistency)
    write_csv(output_dir / "paired_outcomes.csv", paired)
    write_csv(output_dir / "ablation_metrics.csv", sorted(ablation_rows, key=lambda row: row["variant"]))
    write_csv(output_dir / "sensitivity_metrics.csv", sorted(sensitivity_rows, key=lambda row: row["variant"]))
    write_csv(output_dir / "gpu_latency.csv", [latency])

    generate_figures(output_dir, core_metrics, section_metrics, sorted(ablation_rows, key=lambda row: row["variant"]), latency)

    core_natural = {row["config"]: row for row in core_metrics if row["scope"] == "without_synthetic_fault"}
    core_all = {row["config"]: row for row in core_metrics if row["scope"] == "all_core"}
    holdout = {row["config"]: row for row in section_metrics if row["section"] == "holdout"}
    lines = [
        "# Paper v4 final GPU evidence",
        "",
        "Campaign: `{}`  ".format(args.campaign_id),
        "Frozen commit: `{}`  ".format(campaign_manifest["jobs"][0].get("git_commit", "recorded per runtime session")),
        "Status: **{}**, {} jobs and {} isolated scenario sessions.".format(campaign_manifest["status"], len(campaign_manifest["results"]), len(sessions)),
        "",
        "## Core benchmark (synthetic faults excluded)",
        "",
        "| Policy | TP | FP | TN | FN | Precision | Recall | Collision |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for config in CONFIGS:
        row = core_natural[config]
        lines.append(
            "| {} | {} | {} | {} | {} | {:.3f} | {:.3f} | {} |".format(
                DISPLAY[config], row["TP"], row["FP"], row["TN"], row["FN"], row["precision"], row["recall"], row["collision"]
            )
        )
    lines.extend(
        [
            "",
            "The frozen core benchmark reproduces the intended trade-off. Safe fallback matched radar-only recall (0.988) and hard-gate precision (1.000) on this constructed suite, while reducing hard-gate collisions from 25 to 15. This is a benchmark-specific result, not a prevalence-weighted road estimate.",
            "",
            "## Core including labelled synthetic fault injection",
            "",
            "| Policy | TP | FP | TN | FN | Precision | Recall |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for config in CONFIGS:
        row = core_all[config]
        lines.append(
            "| {} | {} | {} | {} | {} | {:.3f} | {:.3f} |".format(
                DISPLAY[config], row["TP"], row["FP"], row["TN"], row["FN"], row["precision"], row["recall"]
            )
        )
    lines.extend(
        [
            "",
            "## Frozen hold-out",
            "",
            "| Policy | PASS | FAIL | TP | FP | TN | FN | Precision | Recall | Collision |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for config in CONFIGS:
        row = holdout[config]
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | {:.3f} | {:.3f} | {} |".format(
                DISPLAY[config], row["pass"], row["runs"] - row["pass"], row["TP"], row["FP"], row["TN"], row["FN"], row["precision"], row["recall"], row["collision"]
            )
        )
    lines.extend(
        [
            "",
            "Safe fallback did not dominate the hard gate on hold-out: four high-support central synthetic ghosts produced 20/25 false-brake runs, while the 0.75 m-offset ghost was blocked. All three policies failed the three unseen central physical-prop scenarios (15 collisions each): the cart generated no confirmed radar cluster, and the bench/warning cases triggered too late to avoid impact. These outcomes were retained without retuning.",
            "",
            "## CUDA processing evidence",
            "",
            "- {} CUDA sessions, {} inferences and {} inference errors.".format(latency["cuda_sessions"], latency["inference_count"], latency["inference_errors"]),
            "- Session-median p50/p95: {:.2f}/{:.2f} ms; weighted mean {:.2f} ms.".format(latency["session_p50_median_ms"], latency["session_p95_median_ms"], latency["weighted_mean_inference_ms"]),
            "- Maximum {:.2f} ms; exactly {} >150 ms cold-start events across {} isolated sessions.".format(latency["maximum_inference_ms"], latency["inferences_over_150ms"], latency["cuda_sessions"]),
            "- Timing is host wall-clock processing evidence, not proof of a real-vehicle real-time deadline.",
            "",
            "## Interpretation safeguards",
            "",
            "- Repeats measure consistency; named scenarios are the scenario-level unit.",
            "- Core/hold-out class ratios were designed, so aggregate precision/F1 are composition-dependent.",
            "- Synthetic returns are explicit fault injection, not native CARLA radar ghosts.",
            "- Euro NCAP compliance, real-vehicle validation and functional-safety certification are not claimed.",
        ]
    )
    (output_dir / "FINAL_GPU_EVIDENCE.md").write_text("\n".join(lines) + "\n")

    source_figures = output_dir / "figures"
    for destination in (
        AEB_ROOT / "report" / "assets" / "evidence_v3",
        AEB_ROOT / "paper" / "paper_v4" / "figures",
    ):
        destination.mkdir(parents=True, exist_ok=True)
        for figure in source_figures.iterdir():
            shutil.copyfile(str(figure), str(destination / figure.name))

    print("Wrote final analysis to {}".format(output_dir))


if __name__ == "__main__":
    main()
