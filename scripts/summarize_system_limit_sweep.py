#!/usr/bin/env python
"""Summarize system limit sweep logs into a Markdown heatmap."""

from __future__ import print_function

import argparse
import csv
import re
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def scenario_key(scenario_id):
    match = re.search(r"ccrs_(\d+)_gap_(\d+)", scenario_id)
    if match:
        return "CCRs: xe đứng yên cùng làn", int(match.group(1)), int(match.group(2))

    match = re.search(r"ccrm_(\d+)_(\d+)_gap_(\d+)", scenario_id)
    if match:
        ego_speed = int(match.group(1))
        target_speed = int(match.group(2))
        return (
            "CCRm: xe trước chạy chậm hơn",
            "{} / {}".format(ego_speed, target_speed),
            int(match.group(3)),
        )

    match = re.search(r"ccrb_(\d+)_gap_(\d+)", scenario_id)
    if match:
        return "CCRb: xe trước phanh gấp", int(match.group(1)), int(match.group(2))

    match = re.search(r"cutin_(\d+)_(\d+)_gap_(\d+)", scenario_id)
    if match:
        ego_speed = int(match.group(1))
        target_speed = int(match.group(2))
        return (
            "Cut-in: xe cắt làn vào trước ego",
            "{} / {}".format(ego_speed, target_speed),
            int(match.group(3)),
        )

    return None, None, None


def read_rows(summary_path):
    rows = []
    with summary_path.open() as stream:
        for row in csv.DictReader(stream):
            group, speed, gap = scenario_key(row.get("scenario_id", ""))
            if group is None:
                continue
            row["group"] = group
            row["speed_kph"] = speed
            row["gap_m"] = gap
            rows.append(row)
    return rows


def cell(row):
    status = row.get("status", "")
    collision = row.get("collision") == "True"
    try:
        min_gap = float(row.get("minimum_bumper_gap_m") or "nan")
    except ValueError:
        min_gap = None
    if status == "PASS":
        return "PASS"
    if collision:
        return "COLLISION"
    if min_gap is not None:
        return "FAIL {:.2f}m".format(min_gap)
    return "FAIL"


def min_pass_gap(rows, speed):
    passed = [
        row["gap_m"]
        for row in rows
        if row["speed_kph"] == speed and row.get("status") == "PASS"
    ]
    return min(passed) if passed else None


def speed_sort_key(value):
    if isinstance(value, int):
        return (value,)
    return tuple(int(part.strip()) for part in str(value).split("/"))


def build_markdown(rows, run_dir):
    lines = [
        "# System Limit Sweep",
        "",
        "Run: `{}`".format(run_dir),
        "",
        "Ghi chú: PASS/FAIL ở đây là kết quả mô phỏng CARLA với controller hiện tại.",
        "Các giá trị jerk/decel nếu dùng thêm vẫn là metric mô phỏng, không phải giá trị xe thật tuyệt đối.",
        "",
    ]

    for group in sorted(set(row["group"] for row in rows)):
        group_rows = [row for row in rows if row["group"] == group]
        speeds = sorted(set(row["speed_kph"] for row in group_rows), key=speed_sort_key)
        gaps = sorted(set(row["gap_m"] for row in group_rows))
        by_key = {(row["speed_kph"], row["gap_m"]): row for row in group_rows}

        lines += ["", "## Heatmap {}".format(group), ""]
        if group.startswith("CCRm") or group.startswith("Cut-in"):
            speed_header = "Ego/Target \\ Gap"
        elif group.startswith("CCRb"):
            speed_header = "Speed \\ Gap"
        else:
            speed_header = "Speed \\ Gap"
        header = [speed_header] + ["{} m".format(gap) for gap in gaps]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for speed in speeds:
            row_label = "{} km/h".format(speed).replace(" / ", "/")
            row_cells = [row_label]
            for gap in gaps:
                row_cells.append(cell(by_key[(speed, gap)]))
            lines.append("| " + " | ".join(row_cells) + " |")

        lines += ["", "### Gap PASS Nhỏ Nhất", ""]
        lines.append("| Speed | Min PASS gap | Nhận xét |")
        lines.append("|---:|---:|---|")
        for speed in speeds:
            gap = min_pass_gap(group_rows, speed)
            label = "{} km/h".format(speed).replace(" / ", "/")
            if gap is None:
                lines.append("| {} | -- | Chưa có gap nào pass |".format(label))
            else:
                lines.append(
                    "| {} | {} m | Pass từ gap này trở lên trong sweep hiện tại |".format(
                        label, gap
                    )
                )

    lines += ["", "## Case Fail", ""]
    lines.append("| Scenario | Collision | Min gap | Lý do |")
    lines.append("|---|---:|---:|---|")
    failed = [row for row in rows if row.get("status") != "PASS"]
    if not failed:
        lines.append("| -- | -- | -- | Không có case fail trong sweep này |")
    for row in failed:
        lines.append(
            "| `{}` | {} | {} | {} |".format(
                row.get("scenario_id"),
                row.get("collision"),
                row.get("minimum_bumper_gap_m") or "--",
                row.get("failure_reason") or row.get("status"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def main():
    args = parse_args()
    summary_path = args.run_dir / "summary.csv"
    rows = read_rows(summary_path)
    if not rows:
        raise SystemExit("Không tìm thấy row CCRs trong {}".format(summary_path))
    output = args.output or (args.run_dir / "system_limit_heatmap.md")
    output.write_text(build_markdown(rows, args.run_dir), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
