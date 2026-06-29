#!/usr/bin/env python

"""Plot AEB brake profile charts from tick-level scenario CSV logs."""

from __future__ import print_function

import argparse
import csv
import math
import sys
from pathlib import Path


STAGE_COLORS = {
    "SAFE": "#dff5e7",
    "NORMAL": "#dff5e7",
    "WARNING": "#fff0b3",
    "SOFT_BRAKE": "#ffd6a5",
    "MEDIUM_BRAKE": "#ffad66",
    "HARD_BRAKE": "#ff7b54",
    "EMERGENCY": "#ef476f",
    "HOLD_STOP": "#b8c0ff",
    "STOPPED": "#b8c0ff",
    "RELEASE": "#d7e3fc",
}

STAGE_LABELS = {
    "SAFE": "SAFE - an toàn",
    "NORMAL": "SAFE/NORMAL - an toàn",
    "WARNING": "WARNING - cảnh báo",
    "SOFT_BRAKE": "SOFT - phanh nhẹ",
    "MEDIUM_BRAKE": "MEDIUM - phanh vừa",
    "HARD_BRAKE": "HARD - phanh mạnh",
    "EMERGENCY": "EMERGENCY - nguy hiểm/phanh khẩn cấp",
    "HOLD_STOP": "HOLD_STOP - giữ xe dừng",
    "STOPPED": "STOPPED - xe đã dừng",
    "RELEASE": "RELEASE - nhả phanh",
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", type=Path, help="Một file log scenario .csv")
    source.add_argument("--run-dir", type=Path, help="Folder log chứa nhiều .csv")
    parser.add_argument(
        "--scenario",
        help="Chỉ vẽ scenario id này khi dùng --run-dir, ví dụ cutin_80_50_gap_25",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dpi", type=int, default=140)
    return parser.parse_args()


def read_rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def safe_float(row, key):
    value = row.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def values(rows, key, default=math.nan):
    result = []
    for row in rows:
        value = safe_float(row, key)
        result.append(default if value is None else value)
    return result


def infer_stage(row):
    explicit = row.get("brake_stage")
    if explicit:
        return explicit
    state = row.get("aeb_state") or "NORMAL"
    reason = row.get("aeb_reason") or ""
    brake = safe_float(row, "brake_cmd") or 0.0
    if state == "WARNING":
        return "WARNING"
    if state == "RELEASE":
        return "RELEASE"
    if state != "BRAKE" or brake <= 0.0:
        return "SAFE"
    if reason.startswith("brake_held_until_stopped"):
        return "HOLD_STOP"
    if brake >= 0.98:
        return "EMERGENCY"
    if brake >= 0.88:
        return "HARD_BRAKE"
    if brake >= 0.70:
        return "MEDIUM_BRAKE"
    return "SOFT_BRAKE"


def stage_spans(rows, times):
    if not rows or not times:
        return []
    spans = []
    start = times[0]
    current = infer_stage(rows[0])
    previous_time = times[0]
    for row, time_s in zip(rows[1:], times[1:]):
        stage = infer_stage(row)
        if stage != current:
            spans.append((start, previous_time, current))
            start = time_s
            current = stage
        previous_time = time_s
    spans.append((start, previous_time, current))
    return spans


def scenario_id_from_rows(path, rows):
    if rows and rows[0].get("scenario_id"):
        return rows[0]["scenario_id"]
    return path.stem


def candidate_csvs(run_dir, scenario=None):
    result = []
    for path in sorted(run_dir.glob("*.csv")):
        if path.name in ("summary.csv", "aggregate_summary.csv"):
            continue
        if scenario and path.stem != scenario:
            rows = read_rows(path)
            if not rows or rows[0].get("scenario_id") != scenario:
                continue
        result.append(path)
    return result


def import_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except ImportError:
        raise SystemExit(
            "Thiếu matplotlib. Cài bằng: python -m pip install matplotlib"
        )


def plot_one(csv_path, output_dir, dpi):
    plt = import_matplotlib()
    from matplotlib.patches import Patch

    rows = read_rows(csv_path)
    if not rows:
        return None

    scenario_id = scenario_id_from_rows(csv_path, rows)
    times = values(rows, "elapsed_s")
    brake = values(rows, "brake_cmd", default=0.0)
    speed = values(rows, "ego_speed_kph")
    gap = values(rows, "bumper_gap_m")
    ttc = values(rows, "ttc_s")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "{}_brake_profile.png".format(scenario_id)

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(11.5, 8.0),
        sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.2, 1.2]},
    )
    fig.suptitle("AEB brake profile - {}".format(scenario_id), fontsize=14)

    spans = stage_spans(rows, times)
    for axis in axes:
        for start, end, stage in spans:
            color = STAGE_COLORS.get(stage, "#eeeeee")
            axis.axvspan(start, end, color=color, alpha=0.22, linewidth=0)
        axis.grid(True, alpha=0.25)

    axes[0].plot(times, brake, color="#d62828", linewidth=2.2, label="brake_cmd")
    axes[0].set_ylabel("Brake")
    axes[0].set_ylim(-0.05, 1.05)
    axes[0].legend(loc="upper right")

    axes[1].plot(times, speed, color="#1d4ed8", linewidth=2.0, label="ego speed")
    axes[1].set_ylabel("Speed (km/h)")
    axes[1].legend(loc="upper right")

    axes[2].plot(times, gap, color="#0f766e", linewidth=2.0, label="bumper gap")
    finite_ttc = [min(value, 10.0) if math.isfinite(value) else math.nan for value in ttc]
    axes[2].plot(
        times,
        finite_ttc,
        color="#7c3aed",
        linewidth=1.6,
        linestyle="--",
        label="TTC clipped 10s",
    )
    axes[2].set_ylabel("Gap/TTC")
    axes[2].set_xlabel("Elapsed time (s)")
    axes[2].legend(loc="upper right")

    stage_labels = []
    for _, _, stage in spans:
        if stage not in stage_labels:
            stage_labels.append(stage)
    handles = [
        Patch(
            facecolor=STAGE_COLORS.get(stage, "#eeeeee"),
            edgecolor="none",
            alpha=0.35,
            label=STAGE_LABELS.get(stage, stage),
        )
        for stage in stage_labels
    ]
    if handles:
        fig.legend(
            handles=handles,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.012),
            ncol=min(4, len(handles)),
            fontsize=8,
            frameon=False,
            title="Dải màu nền: trạng thái AEB theo thời gian",
            title_fontsize=8,
        )
    fig.tight_layout(rect=[0, 0.08, 1, 0.96])
    fig.savefig(str(output_path), dpi=dpi)
    plt.close(fig)
    return output_path


def write_index(output_dir, paths):
    index_path = output_dir / "brake_profile_index.md"
    lines = ["# Brake Profile Charts", ""]
    for path in paths:
        lines.append("- [{}]({})".format(path.name, path.name))
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index_path


def main():
    args = parse_args()
    if args.csv:
        csv_paths = [args.csv]
        default_output = args.csv.parent / "plots"
    else:
        csv_paths = candidate_csvs(args.run_dir, args.scenario)
        default_output = args.run_dir / "plots"
    if not csv_paths:
        raise SystemExit("Không tìm thấy scenario CSV phù hợp")

    output_dir = args.output_dir or default_output
    outputs = []
    for csv_path in csv_paths:
        output = plot_one(csv_path, output_dir, args.dpi)
        if output is not None:
            outputs.append(output)
            print(output)
    if len(outputs) > 1:
        print(write_index(output_dir, outputs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
