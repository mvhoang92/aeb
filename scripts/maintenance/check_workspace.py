#!/usr/bin/env python3
"""Check the external AEB workspace and print resolved artifact locations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infrastructure.workspace import dataset_root, workspace_directories


def collect_status():
    directories = workspace_directories()
    checks = {
        name: {
            "path": str(path),
            "exists": path.is_dir(),
        }
        for name, path in directories.items()
    }
    datasets = {}
    for generation in (
        "dataset",
        "dataset_v2",
        "dataset_v3",
        "dataset_v4",
        "dataset_v5",
        "dataset_v6",
        "dataset_v7_same_lane",
    ):
        path = dataset_root(generation)
        datasets[generation] = {
            "path": str(path),
            "exists": path.is_dir(),
            "dataset_yaml": (path / "dataset.yaml").is_file(),
        }
    passed = all(item["exists"] for item in checks.values()) and all(
        item["exists"] and item["dataset_yaml"] for item in datasets.values()
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "directories": checks,
        "datasets": datasets,
    }


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    return parser.parse_args()


def main():
    args = parse_args()
    status = collect_status()
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print("Workspace: {}".format(status["directories"]["workspace"]["path"]))
        for name, item in status["datasets"].items():
            marker = "OK" if item["exists"] and item["dataset_yaml"] else "MISSING"
            print("{:<24} {:<7} {}".format(name, marker, item["path"]))
        print("Status: {}".format(status["status"]))
    return 0 if status["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
