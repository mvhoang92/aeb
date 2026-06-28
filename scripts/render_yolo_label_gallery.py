#!/usr/bin/env python3
"""Render YOLO label boxes into one review folder."""

from __future__ import print_function

import argparse
import csv
import random
import shutil
from pathlib import Path

import cv2


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")
DEFAULT_SPLITS = ("train", "val", "test")
DEFAULT_COLORS = (
    (60, 230, 90),
    (80, 180, 255),
    (255, 190, 80),
    (230, 90, 230),
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Draw YOLO labels on images and copy train/val/test outputs into "
            "one review directory."
        )
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("dataset_v5"),
        help="Dataset root containing images/ and labels/ directories.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/dataset_v5_box_check"),
        help="Directory for rendered review images.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=list(DEFAULT_SPLITS),
        help="Dataset splits to render.",
    )
    parser.add_argument(
        "--max-per-split",
        type=int,
        default=0,
        help="Optional max images per split. 0 means render all images.",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="Shuffle images before applying --max-per-split.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
        help="Random seed used with --shuffle.",
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        default=True,
        help="Render images with empty label files.",
    )
    parser.add_argument(
        "--skip-empty",
        action="store_true",
        help="Skip images without labels/boxes.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete output directory before rendering.",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=92,
        help="JPEG quality for rendered images.",
    )
    return parser.parse_args()


def load_class_names(dataset_root):
    dataset_yaml = dataset_root / "dataset.yaml"
    if not dataset_yaml.is_file():
        return {0: "car"}

    names = {}
    in_names = False
    for raw_line in dataset_yaml.read_text().splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "names:":
            in_names = True
            continue
        if in_names and not raw_line.startswith((" ", "\t")):
            break
        if in_names and ":" in stripped:
            key, value = stripped.split(":", 1)
            try:
                class_id = int(key.strip())
            except ValueError:
                continue
            names[class_id] = value.strip().strip("\"'")
    if not names:
        names[0] = "car"
    return names


def list_images(dataset_root, split):
    image_dir = dataset_root / "images" / split
    if not image_dir.is_dir():
        return []
    images = []
    for path in image_dir.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(path)
    return sorted(images)


def read_yolo_labels(label_path):
    labels = []
    if not label_path.is_file():
        return labels
    for line_number, raw_line in enumerate(label_path.read_text().splitlines(), 1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) < 5:
            print(
                "Skip malformed label line {}:{} -> {}".format(
                    label_path,
                    line_number,
                    raw_line,
                )
            )
            continue
        try:
            class_id = int(float(parts[0]))
            x_center = float(parts[1])
            y_center = float(parts[2])
            width = float(parts[3])
            height = float(parts[4])
        except ValueError:
            print(
                "Skip invalid label line {}:{} -> {}".format(
                    label_path,
                    line_number,
                    raw_line,
                )
            )
            continue
        labels.append((class_id, x_center, y_center, width, height))
    return labels


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def yolo_to_pixels(label, image_width, image_height):
    class_id, x_center, y_center, width, height = label
    x1 = (x_center - width / 2.0) * image_width
    y1 = (y_center - height / 2.0) * image_height
    x2 = (x_center + width / 2.0) * image_width
    y2 = (y_center + height / 2.0) * image_height
    return (
        class_id,
        int(round(clamp(x1, 0, image_width - 1))),
        int(round(clamp(y1, 0, image_height - 1))),
        int(round(clamp(x2, 0, image_width - 1))),
        int(round(clamp(y2, 0, image_height - 1))),
    )


def draw_header(image, text, box_count):
    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (image.shape[1], 42), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.45, image, 0.55, 0, image)
    cv2.putText(
        image,
        "{} | boxes={}".format(text, box_count),
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


def draw_labels(image, labels, class_names):
    image_height, image_width = image.shape[:2]
    for index, label in enumerate(labels):
        class_id, x1, y1, x2, y2 = yolo_to_pixels(label, image_width, image_height)
        color = DEFAULT_COLORS[class_id % len(DEFAULT_COLORS)]
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        class_name = class_names.get(class_id, "class_{}".format(class_id))
        text = "{} {}".format(class_name, index + 1)
        text_size, baseline = cv2.getTextSize(
            text,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            1,
        )
        text_width, text_height = text_size
        text_x = x1
        text_y = max(y1 - 6, text_height + 8)
        bg_x2 = min(text_x + text_width + 8, image_width - 1)
        bg_y1 = max(text_y - text_height - 7, 0)
        bg_y2 = min(text_y + baseline + 4, image_height - 1)
        cv2.rectangle(image, (text_x, bg_y1), (bg_x2, bg_y2), color, -1)
        cv2.putText(
            image,
            text,
            (text_x + 4, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )


def render_image(image_path, label_path, output_path, split, class_names, quality):
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError("Cannot read image: {}".format(image_path))

    labels = read_yolo_labels(label_path)
    draw_labels(image, labels, class_names)
    draw_header(image, "{} / {}".format(split, image_path.name), len(labels))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(
        str(output_path),
        image,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)],
    )
    if not ok:
        raise RuntimeError("Cannot write rendered image: {}".format(output_path))
    return len(labels)


def choose_images(images, max_per_split, shuffle, seed):
    selected = list(images)
    if shuffle:
        rng = random.Random(seed)
        rng.shuffle(selected)
    if max_per_split and max_per_split > 0:
        selected = selected[:max_per_split]
    return selected


def main():
    args = parse_args()
    dataset_root = args.dataset_root
    output_dir = args.output_dir

    if args.clean and output_dir.exists():
        shutil.rmtree(str(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    class_names = load_class_names(dataset_root)
    manifest_path = output_dir / "manifest.csv"
    total_images = 0
    total_boxes = 0
    split_counts = {}

    with manifest_path.open("w", newline="") as manifest_file:
        writer = csv.DictWriter(
            manifest_file,
            fieldnames=[
                "split",
                "image",
                "label",
                "output",
                "box_count",
            ],
        )
        writer.writeheader()

        for split in args.splits:
            images = choose_images(
                list_images(dataset_root, split),
                args.max_per_split,
                args.shuffle,
                args.seed,
            )
            rendered = 0
            split_boxes = 0
            for image_path in images:
                label_path = dataset_root / "labels" / split / (
                    image_path.stem + ".txt"
                )
                labels = read_yolo_labels(label_path)
                if args.skip_empty and not labels:
                    continue
                output_name = "{}__{}.jpg".format(split, image_path.stem)
                output_path = output_dir / output_name
                box_count = render_image(
                    image_path,
                    label_path,
                    output_path,
                    split,
                    class_names,
                    args.jpeg_quality,
                )
                writer.writerow(
                    {
                        "split": split,
                        "image": str(image_path),
                        "label": str(label_path),
                        "output": str(output_path),
                        "box_count": box_count,
                    }
                )
                rendered += 1
                split_boxes += box_count
            split_counts[split] = (rendered, split_boxes)
            total_images += rendered
            total_boxes += split_boxes

    for split in args.splits:
        rendered, split_boxes = split_counts.get(split, (0, 0))
        print(
            "{}: rendered {} images, {} boxes".format(
                split,
                rendered,
                split_boxes,
            )
        )
    print("Output: {}".format(output_dir.resolve()))
    print("Manifest: {}".format(manifest_path.resolve()))
    print("Total: {} images, {} boxes".format(total_images, total_boxes))


if __name__ == "__main__":
    main()
