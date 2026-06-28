#!/usr/bin/env python3
"""Train YOLO26n on the configured AEB dataset."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Union

import yaml
from ultralytics import YOLO


AEB_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = AEB_ROOT.parent
DEFAULT_CONFIG = AEB_ROOT / "configs" / "model_training.yaml"


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def resolve_path(value: Union[str, Path]) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--weights", type=Path, help="Override base_model.")
    parser.add_argument("--epochs", type=int, help="Override epochs.")
    parser.add_argument("--batch", type=int, help="Override batch size.")
    parser.add_argument("--device", help="Override device, for example 0 or cpu.")
    parser.add_argument("--name", help="Override training run name.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load model and print paths without starting training.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_yaml(args.config)
    training = config.get("training", {})
    dataset = config.get("dataset", {})

    dataset_root = resolve_path(dataset.get("root", "aeb/dataset_v7_same_lane"))
    dataset_yaml = dataset_root / "dataset.yaml"
    if not dataset_yaml.is_file():
        raise RuntimeError("Không tìm thấy dataset YAML: {}".format(dataset_yaml))

    weights = (
        args.weights.resolve()
        if args.weights is not None
        else resolve_path(training.get("base_model", "aeb/models/yolo26n.pt"))
    )
    if not weights.is_file():
        raise RuntimeError("Không tìm thấy weight: {}".format(weights))

    project = resolve_path(training.get("project", "aeb/training_runs/detect"))
    run_name = args.name or "{}_{}".format(
        training.get("name_prefix", "yolo26n_aeb"),
        datetime.now().strftime("%Y%m%d_%H%M%S"),
    )

    print("Model   : {}".format(weights))
    print("Dataset : {}".format(dataset_yaml))
    print("Output  : {}".format(project / run_name))
    print("")

    model = YOLO(str(weights))
    if args.dry_run:
        print("Dry-run OK: model đã load, chưa bắt đầu train.")
        return 0

    results = model.train(
        data=str(dataset_yaml),
        epochs=args.epochs or int(training.get("epochs", 100)),
        patience=int(training.get("patience", 20)),
        imgsz=int(training.get("imgsz", 640)),
        batch=args.batch or int(training.get("batch", 4)),
        workers=int(training.get("workers", 4)),
        device=args.device if args.device is not None else training.get("device", 0),
        project=str(project),
        name=run_name,
        cache=bool(training.get("cache", False)),
        amp=bool(training.get("amp", True)),
        seed=int(training.get("seed", 2026)),
        deterministic=bool(training.get("deterministic", True)),
        optimizer=str(training.get("optimizer", "auto")),
        lr0=float(training.get("lr0", 0.001)),
        mosaic=float(training.get("mosaic", 0.5)),
        mixup=float(training.get("mixup", 0.0)),
        copy_paste=float(training.get("copy_paste", 0.0)),
        close_mosaic=int(training.get("close_mosaic", 10)),
        single_cls=True,
        plots=True,
        exist_ok=False,
    )

    save_dir = Path(results.save_dir)
    print("")
    print("Train hoàn tất.")
    print("Best weight: {}".format(save_dir / "weights" / "best.pt"))
    print("Last weight: {}".format(save_dir / "weights" / "last.pt"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
