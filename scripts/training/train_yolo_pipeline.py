#!/usr/bin/env python3

"""Audit a CARLA dataset, train YOLO26n, test it, and deploy accepted weights."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import cv2
import numpy as np
import yaml


AEB_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = AEB_ROOT.parent
ROOT = PROJECT_ROOT
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from infrastructure.workspace import resolve_project_path  # noqa: E402

DEFAULT_CONFIG = AEB_ROOT / "configs" / "model_training.yaml"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
SPLITS = ("train", "val", "test")


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def resolve_path(value: Union[str, Path]) -> Path:
    return resolve_project_path(
        value,
        project_root=PROJECT_ROOT,
        aeb_root=AEB_ROOT,
    )


def image_paths(dataset_root: Path, split: str) -> List[Path]:
    directory = dataset_root / "images" / split
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def parse_yolo_label(path: Path) -> Tuple[int, List[str]]:
    instances = 0
    errors = []
    if not path.is_file():
        return 0, ["Thiếu label: {}".format(path)]
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) != 5:
            errors.append(
                "{}:{} cần 5 trường, nhận {}".format(
                    path,
                    line_number,
                    len(fields),
                )
            )
            continue
        try:
            class_id = int(fields[0])
            values = [float(value) for value in fields[1:]]
        except ValueError:
            errors.append(
                "{}:{} chứa giá trị không hợp lệ".format(path, line_number)
            )
            continue
        if class_id != 0:
            errors.append(
                "{}:{} class_id phải là 0".format(path, line_number)
            )
            continue
        x_center, y_center, width, height = values
        if not (
            0.0 <= x_center <= 1.0
            and 0.0 <= y_center <= 1.0
            and 0.0 < width <= 1.0
            and 0.0 < height <= 1.0
        ):
            errors.append(
                "{}:{} tọa độ YOLO nằm ngoài miền hợp lệ".format(
                    path,
                    line_number,
                )
            )
            continue
        instances += 1
    return instances, errors


def difference_hash(path: Path, hash_size: int = 16) -> Optional[int]:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return None
    resized = cv2.resize(
        image,
        (hash_size + 1, hash_size),
        interpolation=cv2.INTER_AREA,
    )
    differences = resized[:, 1:] > resized[:, :-1]
    result = 0
    for value in differences.reshape(-1):
        result = (result << 1) | int(value)
    return result


def hamming_distance(first: int, second: int) -> int:
    return bin(first ^ second).count("1")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_sessions(dataset_root: Path, split: str) -> int:
    metadata_dir = dataset_root / "metadata" / split
    if not metadata_dir.is_dir():
        return 0
    return len(list(metadata_dir.glob("*.jsonl")))


def audit_split(
    dataset_root: Path,
    split: str,
    near_duplicate_distance: int,
) -> Dict[str, Any]:
    images = image_paths(dataset_root, split)
    labels_dir = dataset_root / "labels" / split
    missing_labels = []
    invalid_labels = []
    instances = 0
    empty_images = 0
    unreadable_images = []
    hashes = []

    for image_path in images:
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            unreadable_images.append(str(image_path))
        label_path = labels_dir / "{}.txt".format(image_path.stem)
        label_instances, label_errors = parse_yolo_label(label_path)
        if not label_path.is_file():
            missing_labels.append(str(label_path))
        invalid_labels.extend(label_errors)
        instances += label_instances
        if label_instances == 0 and not label_errors:
            empty_images += 1
        hashes.append(difference_hash(image_path))

    near_duplicates = 0
    comparable_pairs = 0
    for first, second in zip(hashes, hashes[1:]):
        if first is None or second is None:
            continue
        comparable_pairs += 1
        if hamming_distance(first, second) <= near_duplicate_distance:
            near_duplicates += 1

    image_stems = {path.stem for path in images}
    orphan_labels = []
    if labels_dir.is_dir():
        orphan_labels = [
            str(path)
            for path in labels_dir.glob("*.txt")
            if path.stem not in image_stems
        ]

    image_count = len(images)
    return {
        "images": image_count,
        "instances": instances,
        "sessions": count_sessions(dataset_root, split),
        "empty_images": empty_images,
        "empty_ratio": empty_images / float(image_count) if image_count else 0.0,
        "near_duplicate_pairs": near_duplicates,
        "near_duplicate_ratio": (
            near_duplicates / float(comparable_pairs)
            if comparable_pairs
            else 0.0
        ),
        "missing_labels": missing_labels,
        "invalid_labels": invalid_labels,
        "orphan_labels": orphan_labels,
        "unreadable_images": unreadable_images,
        "image_paths": [str(path) for path in images],
    }


def exact_cross_split_duplicates(
    split_reports: Dict[str, Dict[str, Any]],
) -> List[Dict[str, str]]:
    seen: Dict[str, Tuple[str, str]] = {}
    duplicates = []
    for split in SPLITS:
        for raw_path in split_reports[split]["image_paths"]:
            path = Path(raw_path)
            digest = file_sha256(path)
            previous = seen.get(digest)
            if previous is not None and previous[0] != split:
                duplicates.append(
                    {
                        "first_split": previous[0],
                        "first_image": previous[1],
                        "second_split": split,
                        "second_image": str(path),
                    }
                )
            else:
                seen[digest] = (split, str(path))
    return duplicates


def audit_dataset(config: Dict[str, Any]) -> Dict[str, Any]:
    dataset_config = config.get("dataset", {})
    readiness = config.get("readiness", {})
    dataset_root = resolve_path(dataset_config.get("root", "aeb/dataset_v3"))
    near_distance = int(
        readiness.get("near_duplicate_hamming_distance", 2)
    )
    reports = {
        split: audit_split(dataset_root, split, near_distance)
        for split in SPLITS
    }
    cross_duplicates = exact_cross_split_duplicates(reports)
    checks = []

    minimum_images = readiness.get("minimum_images", {})
    minimum_sessions = readiness.get("minimum_sessions", {})
    for split in SPLITS:
        report = reports[split]
        checks.extend(
            [
                make_check(
                    "{}_minimum_images".format(split),
                    report["images"] >= int(minimum_images.get(split, 0)),
                    "{} ảnh, cần tối thiểu {}".format(
                        report["images"],
                        int(minimum_images.get(split, 0)),
                    ),
                ),
                make_check(
                    "{}_minimum_sessions".format(split),
                    report["sessions"] >= int(minimum_sessions.get(split, 1)),
                    "{} session, cần tối thiểu {}".format(
                        report["sessions"],
                        int(minimum_sessions.get(split, 1)),
                    ),
                ),
                make_check(
                    "{}_valid_pairs".format(split),
                    not (
                        report["missing_labels"]
                        or report["invalid_labels"]
                        or report["orphan_labels"]
                        or report["unreadable_images"]
                    ),
                    "missing={} invalid={} orphan={} unreadable={}".format(
                        len(report["missing_labels"]),
                        len(report["invalid_labels"]),
                        len(report["orphan_labels"]),
                        len(report["unreadable_images"]),
                    ),
                ),
                make_check(
                    "{}_minimum_empty_ratio".format(split),
                    report["empty_ratio"]
                    >= float(readiness.get("minimum_empty_ratio", 0.0)),
                    "empty_ratio={:.3f}, cần tối thiểu {:.3f}".format(
                        report["empty_ratio"],
                        float(readiness.get("minimum_empty_ratio", 0.0)),
                    ),
                ),
                make_check(
                    "{}_empty_ratio".format(split),
                    report["empty_ratio"]
                    <= float(readiness.get("maximum_empty_ratio", 0.30)),
                    "empty_ratio={:.3f}, tối đa {:.3f}".format(
                        report["empty_ratio"],
                        float(readiness.get("maximum_empty_ratio", 0.30)),
                    ),
                ),
                make_check(
                    "{}_near_duplicates".format(split),
                    report["near_duplicate_ratio"]
                    <= float(
                        readiness.get(
                            "maximum_near_duplicate_ratio",
                            0.30,
                        )
                    ),
                    "near_duplicate_ratio={:.3f}, tối đa {:.3f}".format(
                        report["near_duplicate_ratio"],
                        float(
                            readiness.get(
                                "maximum_near_duplicate_ratio",
                                0.30,
                            )
                        ),
                    ),
                ),
            ]
        )

    checks.append(
        make_check(
            "train_minimum_instances",
            reports["train"]["instances"]
            >= int(readiness.get("minimum_train_instances", 3000)),
            "{} instances, cần tối thiểu {}".format(
                reports["train"]["instances"],
                int(readiness.get("minimum_train_instances", 3000)),
            ),
        )
    )
    checks.append(
        make_check(
            "cross_split_exact_duplicates",
            not cross_duplicates,
            "{} ảnh trùng tuyệt đối giữa các split".format(
                len(cross_duplicates)
            ),
        )
    )

    for report in reports.values():
        report.pop("image_paths", None)
    result = {
        "created_at": datetime.now().isoformat(),
        "dataset_root": str(dataset_root),
        "splits": reports,
        "cross_split_duplicates": cross_duplicates,
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
    }
    report_path = resolve_path(
        dataset_config.get(
            "report_path",
            "aeb/training_runs/dataset_audit.json",
        )
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def make_check(name: str, passed: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def print_audit(report: Dict[str, Any]) -> None:
    print("Dataset: {}".format(report["dataset_root"]))
    for split in SPLITS:
        data = report["splits"][split]
        print(
            "  {:5s}: {:4d} ảnh | {:5d} box | {:2d} session | "
            "empty={:.1%} | near-dup={:.1%}".format(
                split,
                data["images"],
                data["instances"],
                data["sessions"],
                data["empty_ratio"],
                data["near_duplicate_ratio"],
            )
        )
    failed = [check for check in report["checks"] if not check["passed"]]
    if failed:
        print("Data chưa đạt:")
        for check in failed:
            print("  - {}: {}".format(check["name"], check["detail"]))
    else:
        print("Data đạt toàn bộ quality gate.")


def gpu_ready(config: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        import torch
    except ImportError:
        return False, "Thiếu PyTorch trong Python train."
    if not torch.cuda.is_available():
        return False, "PyTorch không thấy CUDA."
    free_bytes, total_bytes = torch.cuda.mem_get_info(0)
    free_mb = free_bytes / (1024.0 * 1024.0)
    required = float(
        config.get("training", {}).get("minimum_free_gpu_memory_mb", 3000)
    )
    detail = "GPU free={:.0f}/{:.0f} MiB, cần tối thiểu {:.0f} MiB".format(
        free_mb,
        total_bytes / (1024.0 * 1024.0),
        required,
    )
    return free_mb >= required, detail


def write_dataset_yaml(dataset_root: Path) -> Path:
    path = dataset_root / "dataset.yaml"
    data = {
        "path": str(dataset_root.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {0: "car"},
    }
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def metric_value(metrics: Any, attribute: str) -> float:
    value = getattr(metrics.box, attribute, 0.0)
    return float(value)


def train_and_test(
    config: Dict[str, Any],
    audit_report: Dict[str, Any],
    no_deploy: bool,
) -> Dict[str, Any]:
    from ultralytics import YOLO

    dataset_root = Path(audit_report["dataset_root"])
    dataset_yaml = write_dataset_yaml(dataset_root)
    training = config.get("training", {})
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = "{}_{}".format(
        training.get("name_prefix", "yolo26n_aeb"),
        timestamp,
    )
    project = resolve_path(training.get("project", "aeb/training_runs/detect"))
    base_model = resolve_path(
        training.get("base_model", "aeb/models/yolo26n.pt")
    )
    model = YOLO(str(base_model))
    results = model.train(
        data=str(dataset_yaml),
        epochs=int(training.get("epochs", 100)),
        patience=int(training.get("patience", 20)),
        imgsz=int(training.get("imgsz", 640)),
        batch=int(training.get("batch", 4)),
        workers=int(training.get("workers", 4)),
        device=training.get("device", 0),
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
    best_pt = save_dir / "weights" / "best.pt"
    if not best_pt.is_file():
        raise RuntimeError("Không tìm thấy best.pt tại {}".format(best_pt))

    best_model = YOLO(str(best_pt))
    test_metrics = best_model.val(
        data=str(dataset_yaml),
        split="test",
        imgsz=int(training.get("imgsz", 640)),
        batch=int(training.get("batch", 4)),
        workers=int(training.get("workers", 4)),
        device=training.get("device", 0),
        project=str(project),
        name="{}_test".format(run_name),
        plots=True,
    )
    metrics = {
        "precision": metric_value(test_metrics, "mp"),
        "recall": metric_value(test_metrics, "mr"),
        "map50": metric_value(test_metrics, "map50"),
        "map50_95": metric_value(test_metrics, "map"),
    }
    quality_checks = quality_gate_checks(config, metrics)

    export_config = config.get("export", {})
    exported = best_model.export(
        format=str(export_config.get("format", "onnx")),
        imgsz=int(training.get("imgsz", 640)),
        opset=int(export_config.get("opset", 17)),
        simplify=bool(export_config.get("simplify", True)),
        dynamic=bool(export_config.get("dynamic", False)),
        half=bool(export_config.get("half", False)),
        device=training.get("device", 0),
    )
    onnx_path = Path(exported)
    benchmark = verify_and_benchmark_onnx(
        onnx_path,
        image_paths(dataset_root, "test"),
        int(training.get("imgsz", 640)),
        int(export_config.get("benchmark_images", 30)),
    )

    report = {
        "created_at": datetime.now().isoformat(),
        "run_name": run_name,
        "save_dir": str(save_dir),
        "best_pt": str(best_pt),
        "onnx": str(onnx_path),
        "test_metrics": metrics,
        "quality_checks": quality_checks,
        "quality_passed": all(check["passed"] for check in quality_checks),
        "onnx_benchmark": benchmark,
        "dataset_audit": audit_report,
        "deployed": False,
    }
    if report["quality_passed"] and not no_deploy:
        deploy_model(config, best_pt, onnx_path, report)
        report["deployed"] = True

    report_path = save_dir / "pipeline_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def quality_gate_checks(
    config: Dict[str, Any],
    metrics: Dict[str, float],
) -> List[Dict[str, Any]]:
    gate = config.get("quality_gate", {})
    mapping = {
        "precision": "minimum_precision",
        "recall": "minimum_recall",
        "map50": "minimum_map50",
        "map50_95": "minimum_map50_95",
    }
    return [
        make_check(
            metric,
            metrics[metric] >= float(gate.get(config_key, 0.0)),
            "{:.4f}, cần tối thiểu {:.4f}".format(
                metrics[metric],
                float(gate.get(config_key, 0.0)),
            ),
        )
        for metric, config_key in mapping.items()
    ]


def letterbox(image: np.ndarray, size: int) -> np.ndarray:
    height, width = image.shape[:2]
    scale = min(size / float(width), size / float(height))
    resized_width = int(round(width * scale))
    resized_height = int(round(height * scale))
    resized = cv2.resize(
        image,
        (resized_width, resized_height),
        interpolation=cv2.INTER_LINEAR,
    )
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    left = (size - resized_width) // 2
    top = (size - resized_height) // 2
    canvas[top : top + resized_height, left : left + resized_width] = resized
    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    tensor = rgb.astype(np.float32) / 255.0
    return np.ascontiguousarray(np.transpose(tensor, (2, 0, 1))[None])


def verify_and_benchmark_onnx(
    onnx_path: Path,
    images: Sequence[Path],
    image_size: int,
    limit: int,
) -> Dict[str, Any]:
    import onnx
    import onnxruntime as ort

    model = onnx.load(str(onnx_path))
    onnx.checker.check_model(model)
    available = ort.get_available_providers()
    providers = [
        provider
        for provider in (
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        )
        if provider in available
    ]
    session = ort.InferenceSession(str(onnx_path), providers=providers)
    input_name = session.get_inputs()[0].name
    durations = []
    output_shape = None
    selected = list(images[: max(1, limit)])
    warmed_up = False
    for path in selected:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            continue
        tensor = letterbox(image, image_size)
        if not warmed_up:
            session.run(None, {input_name: tensor})
            warmed_up = True
        started = time.perf_counter()
        outputs = session.run(None, {input_name: tensor})
        durations.append((time.perf_counter() - started) * 1000.0)
        output_shape = list(np.asarray(outputs[0]).shape)
    return {
        "providers": session.get_providers(),
        "images": len(durations),
        "mean_latency_ms": (
            sum(durations) / len(durations) if durations else None
        ),
        "output_shape": output_shape,
    }


def deploy_model(
    config: Dict[str, Any],
    best_pt: Path,
    onnx_path: Path,
    report: Dict[str, Any],
) -> None:
    deployment = config.get("deployment", {})
    target_pt = resolve_path(
        deployment.get("pt_path", "aeb/models/yolo26n.pt")
    )
    target_onnx = resolve_path(
        deployment.get("onnx_path", "aeb/models/yolo26n.onnx")
    )
    manifest_path = resolve_path(
        deployment.get(
            "manifest_path",
            "aeb/models/model_manifest.json",
        )
    )
    archive_root = resolve_path(
        deployment.get("archive_dir", "aeb/models/archive")
    )
    archive_dir = archive_root / datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir.mkdir(parents=True, exist_ok=True)

    for existing in (target_pt, target_onnx, manifest_path):
        if existing.is_file():
            shutil.copy2(str(existing), str(archive_dir / existing.name))
    atomic_copy(best_pt, target_pt)
    atomic_copy(onnx_path, target_onnx)
    manifest = {
        "deployed_at": datetime.now().isoformat(),
        "run_name": report["run_name"],
        "test_metrics": report["test_metrics"],
        "onnx_benchmark": report["onnx_benchmark"],
        "class_names": {0: "car"},
        "archive": str(archive_dir),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copy2(str(source), str(temporary))
    os.replace(str(temporary), str(destination))


def wait_until_ready(config: Dict[str, Any], poll_seconds: int) -> Dict[str, Any]:
    while True:
        report = audit_dataset(config)
        print_audit(report)
        gpu_ok, gpu_detail = gpu_ready(config)
        print(gpu_detail)
        if report["passed"] and gpu_ok:
            return report
        print("Chưa sẵn sàng; kiểm tra lại sau {} giây.\n".format(poll_seconds))
        time.sleep(poll_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--force-train", action="store_true")
    parser.add_argument("--no-deploy", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_yaml(args.config)
    if args.watch:
        poll_seconds = max(
            5,
            int(config.get("watch", {}).get("poll_seconds", 60)),
        )
        report = wait_until_ready(config, poll_seconds)
    else:
        report = audit_dataset(config)
        print_audit(report)

    if args.audit_only or args.dry_run:
        return 0 if report["passed"] else 2
    if not report["passed"] and not args.force_train:
        print("Không train vì dataset chưa đạt. Dùng --force-train chỉ để thử nghiệm.")
        return 2

    gpu_ok, gpu_detail = gpu_ready(config)
    print(gpu_detail)
    if not gpu_ok:
        print("Hãy tắt CARLA và các tiến trình dùng GPU trước khi train.")
        return 3

    result = train_and_test(config, report, args.no_deploy)
    print(
        "Test: P={precision:.3f} R={recall:.3f} "
        "mAP50={map50:.3f} mAP50-95={map50_95:.3f}".format(
            **result["test_metrics"]
        )
    )
    if result["deployed"]:
        print("Model đạt quality gate và đã được triển khai vào aeb/models/.")
        return 0
    print("Model chưa được triển khai; xem pipeline_report.json.")
    return 4 if not result["quality_passed"] else 0


if __name__ == "__main__":
    sys.exit(main())
