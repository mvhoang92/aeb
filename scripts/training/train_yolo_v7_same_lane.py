#!/usr/bin/env python3
"""Compatibility launcher for training YOLO26n on dataset_v7_same_lane.

The clean workflow is now split into:

- scripts/check_yolo_dataset.py
- scripts/train_yolo26n.py
- scripts/export_yolo26n_onnx.py

This wrapper is kept only so old notes/terminal history still work.
"""

from __future__ import print_function

import argparse
import sys
from pathlib import Path
import subprocess


AEB_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = AEB_ROOT / "configs" / "model_training.yaml"
CHECK_SCRIPT = AEB_ROOT / "scripts" / "check_yolo_dataset.py"
TRAIN_SCRIPT = AEB_ROOT / "scripts" / "train_yolo26n.py"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Training config. Default: configs/model_training.yaml",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Only audit the dataset; do not train.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch", type=int)
    parser.add_argument("--device")
    parser.add_argument("--name")
    return parser.parse_args()


def build_command(args):
    script = CHECK_SCRIPT if args.audit_only else TRAIN_SCRIPT
    command = [
        sys.executable,
        str(script),
        "--config",
        str(args.config),
    ]
    if not args.audit_only:
        for option in ("epochs", "batch", "device", "name"):
            value = getattr(args, option)
            if value is not None:
                command.extend(["--" + option, str(value)])
        if args.dry_run:
            command.append("--dry-run")
    return command


def run_training(command):
    """Run with the terminal attached directly so Ultralytics behaves normally."""
    return subprocess.call(command, cwd=str(AEB_ROOT))


def main():
    args = parse_args()
    command = build_command(args)

    print("AEB root : {}".format(AEB_ROOT), flush=True)
    print("Python   : {}".format(sys.executable), flush=True)
    print("Config   : {}".format(args.config), flush=True)
    print("", flush=True)
    if not (args.audit_only or args.dry_run):
        print(
            "Gợi ý: nên tắt CARLA server trước khi train thật để giải phóng GPU.",
            flush=True,
        )
        print("", flush=True)

    return run_training(command)


if __name__ == "__main__":
    sys.exit(main())
