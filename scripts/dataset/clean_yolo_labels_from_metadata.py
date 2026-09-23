#!/usr/bin/env python3
"""Clean YOLO labels using CARLA metadata visibility and overlap rules."""

from __future__ import print_function

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import cv2
import yaml


AEB_ROOT = Path(__file__).resolve().parents[2]
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from infrastructure.workspace import dataset_root  # noqa: E402

DEFAULT_DATASET_ROOT = dataset_root("dataset_v6")
DEFAULT_CONFIG = AEB_ROOT / "configs" / "dataset_collection.yaml"
SPLITS = ("train", "val", "test")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--splits", nargs="+", default=list(SPLITS))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--render-previews", action="store_true")
    parser.add_argument("--jpeg-quality", type=int, default=92)
    return parser.parse_args()


def load_yaml(path):
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def box_area(box):
    x1, y1, x2, y2 = box
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def overlap_stats(first, second):
    ax1, ay1, ax2, ay2 = first
    bx1, by1, bx2, by2 = second
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    first_area = box_area(first)
    second_area = box_area(second)
    union = first_area + second_area - intersection
    minimum = min(first_area, second_area)
    return (
        intersection / union if union > 0.0 else 0.0,
        intersection / minimum if minimum > 0.0 else 0.0,
    )


def passes_heavy_occlusion(obj, config):
    ratio_threshold = float(config.get("heavy_occlusion_visible_ratio", 0.0))
    visible_ratio = obj.get("visible_ratio")
    if visible_ratio is None or ratio_threshold <= 0.0:
        return True
    if float(visible_ratio) >= ratio_threshold:
        return True

    min_pixels = int(config.get("heavy_occlusion_min_visible_pixels", 0))
    if int(obj.get("visible_pixels") or 0) >= min_pixels:
        return True

    min_area = float(config.get("heavy_occlusion_min_fitted_area_px", 0.0))
    return box_area(obj["bbox_xyxy"]) >= min_area


def suppress_overlaps(objects, config):
    if not bool(config.get("suppress_overlapping_boxes", True)):
        return objects, 0

    iou_threshold = float(config.get("overlap_suppression_iou", 0.55))
    containment_threshold = float(
        config.get("overlap_suppression_containment", 0.75)
    )
    kept = []
    dropped = 0
    for obj in sorted(objects, key=lambda item: float(item.get("distance_m", 0.0))):
        duplicate = False
        for kept_obj in kept:
            iou, containment = overlap_stats(
                obj["bbox_xyxy"],
                kept_obj["bbox_xyxy"],
            )
            if iou >= iou_threshold or containment >= containment_threshold:
                duplicate = True
                break
        if duplicate:
            dropped += 1
        else:
            kept.append(obj)
    return kept, dropped


def yolo_line(obj, image_width, image_height):
    x1, y1, x2, y2 = obj["bbox_xyxy"]
    x_center = ((x1 + x2) * 0.5) / float(image_width)
    y_center = ((y1 + y2) * 0.5) / float(image_height)
    width = (x2 - x1) / float(image_width)
    height = (y2 - y1) / float(image_height)
    return "0 {:.6f} {:.6f} {:.6f} {:.6f}".format(
        x_center,
        y_center,
        width,
        height,
    )


def draw_preview(dataset_root, split, record, objects, jpeg_quality):
    image_path = dataset_root / record["image"]
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        return False
    for obj in objects:
        x1, y1, x2, y2 = [int(round(value)) for value in obj["bbox_xyxy"]]
        cv2.rectangle(image, (x1, y1), (x2, y2), (60, 230, 90), 2)
        text = "car id={} d={:.1f}m".format(
            obj.get("actor_id", "?"),
            float(obj.get("distance_m", 0.0)),
        )
        if obj.get("visible_ratio") is not None:
            text += " vis={:.2f}".format(float(obj["visible_ratio"]))
        cv2.putText(
            image,
            text,
            (x1, max(18, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (60, 230, 90),
            2,
            cv2.LINE_AA,
        )

    cv2.putText(
        image,
        "{} | boxes={}".format(record["sample"], len(objects)),
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    preview_path = dataset_root / "previews" / split / "{}.jpg".format(
        record["sample"]
    )
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    return cv2.imwrite(
        str(preview_path),
        image,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)],
    )


def backup_labels(dataset_root):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = dataset_root / "labels_backup_{}".format(timestamp)
    shutil.copytree(str(dataset_root / "labels"), str(backup_root))
    return backup_root


def clean_split(dataset_root, split, filter_config, apply_changes, render_previews, jpeg_quality):
    metadata_dir = dataset_root / "metadata" / split
    label_dir = dataset_root / "labels" / split
    records = 0
    old_boxes = 0
    new_boxes = 0
    heavy_dropped = 0
    overlap_dropped = 0

    for metadata_path in sorted(metadata_dir.glob("*.jsonl")):
        for raw_line in metadata_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            record = json.loads(raw_line)
            objects = list(record.get("objects", []))
            records += 1
            old_boxes += len(objects)

            filtered = []
            for obj in objects:
                if passes_heavy_occlusion(obj, filter_config):
                    filtered.append(obj)
                else:
                    heavy_dropped += 1
            filtered, dropped = suppress_overlaps(filtered, filter_config)
            overlap_dropped += dropped
            new_boxes += len(filtered)

            if not apply_changes:
                continue

            image_width = int(record["camera"]["width"])
            image_height = int(record["camera"]["height"])
            label_path = label_dir / "{}.txt".format(record["sample"])
            label_path.parent.mkdir(parents=True, exist_ok=True)
            with label_path.open("w", encoding="utf-8") as stream:
                for obj in filtered:
                    stream.write(yolo_line(obj, image_width, image_height) + "\n")
            if render_previews:
                draw_preview(
                    dataset_root,
                    split,
                    record,
                    filtered,
                    jpeg_quality,
                )

    return {
        "records": records,
        "old_boxes": old_boxes,
        "new_boxes": new_boxes,
        "heavy_dropped": heavy_dropped,
        "overlap_dropped": overlap_dropped,
    }


def main():
    args = parse_args()
    dataset_root = args.dataset_root.resolve()
    config = load_yaml(args.config)
    filter_config = config.get("filter", {})

    backup_root = None
    if args.apply:
        backup_root = backup_labels(dataset_root)
        print("Đã backup label cũ vào: {}".format(backup_root))
    else:
        print("Dry-run: chưa ghi đè label. Thêm --apply để áp dụng.")

    totals = {
        "records": 0,
        "old_boxes": 0,
        "new_boxes": 0,
        "heavy_dropped": 0,
        "overlap_dropped": 0,
    }
    for split in args.splits:
        result = clean_split(
            dataset_root,
            split,
            filter_config,
            args.apply,
            args.render_previews,
            args.jpeg_quality,
        )
        for key, value in result.items():
            totals[key] += value
        print(
            "{:5s}: {:4d} ảnh | {:5d} -> {:5d} box | che khuất bỏ {:4d} | overlap bỏ {:4d}".format(
                split,
                result["records"],
                result["old_boxes"],
                result["new_boxes"],
                result["heavy_dropped"],
                result["overlap_dropped"],
            )
        )

    print(
        "Tổng: {} ảnh | {} -> {} box | bỏ do che khuất {} | bỏ do overlap {}".format(
            totals["records"],
            totals["old_boxes"],
            totals["new_boxes"],
            totals["heavy_dropped"],
            totals["overlap_dropped"],
        )
    )


if __name__ == "__main__":
    main()
