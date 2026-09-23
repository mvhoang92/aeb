#!/usr/bin/env python3
"""Check the YOLO dataset without training or exporting a model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[2]
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from scripts.train_yolo_pipeline import audit_dataset, load_yaml, print_audit


DEFAULT_CONFIG = AEB_ROOT / "configs" / "model_training.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit_dataset(load_yaml(args.config))
    print_audit(report)
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
