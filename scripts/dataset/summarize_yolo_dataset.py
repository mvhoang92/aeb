#!/usr/bin/env python3
"""Summarize CARLA YOLO dataset metadata."""

from __future__ import print_function

import argparse
import json
from collections import Counter
from pathlib import Path


DEFAULT_SPLITS = ("train", "val", "test")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--top-k", type=int, default=30)
    return parser.parse_args()


def median(values):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def summarize_split(dataset_root, split, top_k):
    metadata_dir = dataset_root / "metadata" / split
    result = {
        "sessions": 0,
        "images": 0,
        "boxes": 0,
        "positive_images": 0,
        "empty_images": 0,
        "same_lane_boxes": 0,
        "distance_m": {},
        "visible_ratio": {},
        "blueprints": [],
        "colors": [],
    }
    if not metadata_dir.is_dir():
        return result

    distances = []
    visible_ratios = []
    blueprints = Counter()
    colors = Counter()

    for metadata_path in sorted(metadata_dir.glob("*.jsonl")):
        result["sessions"] += 1
        for raw_line in metadata_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            record = json.loads(raw_line)
            objects = record.get("objects", [])
            result["images"] += 1
            result["boxes"] += len(objects)
            if objects:
                result["positive_images"] += 1
            else:
                result["empty_images"] += 1
            for obj in objects:
                if obj.get("same_lane_seeded"):
                    result["same_lane_boxes"] += 1
                if obj.get("distance_m") is not None:
                    distances.append(float(obj["distance_m"]))
                if obj.get("visible_ratio") is not None:
                    visible_ratios.append(float(obj["visible_ratio"]))
                blueprints[obj.get("blueprint", "unknown")] += 1
                colors[obj.get("color") or "unknown"] += 1

    if result["images"]:
        result["empty_ratio"] = result["empty_images"] / float(result["images"])
    else:
        result["empty_ratio"] = 0.0

    if distances:
        result["distance_m"] = {
            "min": min(distances),
            "median": median(distances),
            "max": max(distances),
        }
    if visible_ratios:
        result["visible_ratio"] = {
            "min": min(visible_ratios),
            "median": median(visible_ratios),
            "max": max(visible_ratios),
        }
    result["unique_blueprints"] = len(blueprints)
    result["unique_colors"] = len([color for color in colors if color != "unknown"])
    result["blueprints"] = blueprints.most_common(top_k)
    result["colors"] = colors.most_common(top_k)
    return result


def main():
    args = parse_args()
    dataset_root = args.dataset_root.resolve()
    summary = {
        "dataset_root": str(dataset_root),
        "splits": {
            split: summarize_split(dataset_root, split, args.top_k)
            for split in DEFAULT_SPLITS
        },
    }

    payload = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print("Wrote {}".format(args.output))
    else:
        print(payload)


if __name__ == "__main__":
    main()
