#!/usr/bin/env python3
"""Export a trained YOLO26n .pt weight to ONNX."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from ultralytics import YOLO


AEB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = AEB_ROOT / "configs" / "model_training.yaml"
DEFAULT_RUNS = AEB_ROOT / "training_runs" / "detect"


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def newest_best_weight(runs_root: Path) -> Optional[Path]:
    candidates = list(runs_root.glob("*/weights/best.pt"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--weights",
        type=Path,
        help="Path to best.pt. Default: newest best.pt in training_runs/detect.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional destination .onnx path. Default: beside the .pt file.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Export device. CPU is the stable default; use 0 for CUDA.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and load weights without exporting.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_yaml(args.config)
    training = config.get("training", {})
    export_config = config.get("export", {})

    weights = args.weights.resolve() if args.weights else newest_best_weight(DEFAULT_RUNS)
    if weights is None or not weights.is_file():
        raise RuntimeError(
            "Không tìm thấy best.pt. Hãy truyền --weights /duong/dan/best.pt"
        )

    print("Weights : {}".format(weights))
    model = YOLO(str(weights))
    if args.dry_run:
        print("Dry-run OK: model đã load, chưa export ONNX.")
        return 0

    exported = Path(
        model.export(
            format="onnx",
            imgsz=int(training.get("imgsz", 640)),
            opset=int(export_config.get("opset", 17)),
            simplify=bool(export_config.get("simplify", True)),
            dynamic=bool(export_config.get("dynamic", False)),
            half=bool(export_config.get("half", False)),
            device=args.device,
        )
    )

    output = exported
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if exported.resolve() != output:
            shutil.copy2(str(exported), str(output))

    print("ONNX    : {}".format(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
