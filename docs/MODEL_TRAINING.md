# Pipeline Tự Động Train Và Test YOLO26n

File `aeb/model_pipeline.py` thực hiện tuần tự:

1. Audit dataset train, validation và test.
2. Chờ dataset đạt quality gate nếu chạy với `--watch`.
3. Kiểm tra CUDA và dung lượng VRAM còn trống.
4. Fine-tune `yolo26n.pt` bằng Python 3.10.
5. Đánh giá model tốt nhất trên test split độc lập.
6. Export ONNX và kiểm tra bằng ONNX Runtime CUDA.
7. Chỉ triển khai model nếu precision, recall và mAP đạt ngưỡng.
8. Archive model cũ trước khi thay file đang dùng bởi CARLA.

CARLA và collector vẫn chạy bằng Python 3.7. Train model phải dùng `python3`
của hệ thống vì môi trường này có PyTorch, Ultralytics và CUDA mới.

## Dataset Cần Thu

Quality gate mặc định trong `aeb/configs/model_training.yaml`:

```yaml
minimum_images:
  train: 1500
  val: 300
  test: 200
minimum_sessions:
  train: 3
  val: 1
  test: 1
minimum_train_instances: 3000
minimum_empty_ratio: 0.03
```

Nên thu nhiều session với seed khác nhau:

```bash
venv/bin/python aeb/collect_ground_truth_data.py \
  --split train --session-id town04_train_01 --seed 2026 --max-samples 500

venv/bin/python aeb/collect_ground_truth_data.py \
  --split train --session-id town04_train_02 --seed 2027 --max-samples 500

venv/bin/python aeb/collect_ground_truth_data.py \
  --split train --session-id town04_train_03 --seed 2028 --max-samples 500

venv/bin/python aeb/collect_ground_truth_data.py \
  --split val --session-id town04_val_01 --seed 3026 --max-samples 300

venv/bin/python aeb/collect_ground_truth_data.py \
  --split test --session-id town04_test_01 --seed 4026 --max-samples 200
```

Thu thêm negative sample đường trống cho từng split. Ví dụ:

```bash
venv/bin/python aeb/collect_ground_truth_data.py \
  --split train \
  --session-id town04_train_clear_01 \
  --seed 5026 \
  --number-of-vehicles 0 \
  --same-lane-vehicles 0 \
  --max-samples 150
```

Validation và test cũng cần negative session riêng, khoảng 30 ảnh val và 20 ảnh
test. Pipeline yêu cầu tỷ lệ ảnh rỗng từ 3% đến 30%.

Không dùng cùng seed cho train, val và test. Collector lưu tất cả vào
`aeb/dataset_v3` nhưng tách thư mục theo split.

## Chạy Audit

```bash
cd /home/mvhoang/CARLA_0.9.11
python3 aeb/model_pipeline.py --audit-only
```

Report được lưu tại:

```text
aeb/training_runs/dataset_audit.json
```

Audit kiểm tra:

- Đủ số ảnh, số session và số vehicle instance.
- Ảnh và label có đủ cặp.
- Tọa độ YOLO hợp lệ và chỉ dùng class `0 = car`.
- Ảnh có đọc được hay không.
- Tỷ lệ negative sample.
- Tỷ lệ frame gần trùng nhau bằng difference hash.
- Ảnh trùng tuyệt đối giữa train, val và test.

## Chạy Tự Động

Có thể bật watcher trước hoặc sau khi thu data:

```bash
cd /home/mvhoang/CARLA_0.9.11
python3 aeb/model_pipeline.py --watch
```

Watcher kiểm tra lại mỗi 60 giây. Khi dataset đạt và GPU còn tối thiểu 3000 MiB,
script tự train, test, export và triển khai. Sau khi thu data xong cần tắt CARLA
để trả VRAM cho quá trình train. Watcher sẽ chờ nếu CARLA vẫn chiếm GPU.

Chạy một lần, không chờ:

```bash
python3 aeb/model_pipeline.py
```

Không nên dùng `--force-train` cho model chính thức. Cờ này chỉ phục vụ smoke
test khi dataset chưa đạt quality gate.

## Cấu Hình Train

Baseline dành cho RTX 3050 Laptop 4 GB:

```yaml
training:
  imgsz: 640
  epochs: 100
  patience: 20
  batch: 4
  workers: 4
  amp: true
  optimizer: AdamW
  lr0: 0.001
  mosaic: 0.5
  mixup: 0.0
  copy_paste: 0.0
```

Model dùng pretrained `aeb/models/yolo26n.pt`, không train từ đầu. Early
stopping có thể kết thúc trước 100 epoch nếu validation không cải thiện.

## Quality Gate Của Model

```yaml
quality_gate:
  minimum_precision: 0.75
  minimum_recall: 0.75
  minimum_map50: 0.80
  minimum_map50_95: 0.50
```

Model không đạt ngưỡng vẫn được giữ trong `aeb/training_runs/detect`, nhưng
không ghi đè model dùng cho demo.

Nếu đạt, pipeline cập nhật:

```text
aeb/models/yolo26n.pt
aeb/models/yolo26n.onnx
aeb/models/model_manifest.json
```

Model cũ được lưu tại:

```text
aeb/models/archive/<timestamp>/
```

ONNX chứa metadata tên class. Runtime đọc metadata này để hiểu model AEB có
`class 0 = car`, thay vì dùng nhầm bảng class COCO.

## Test Sau Khi Train

Pipeline tự chạy `model.val(split="test")`, lưu confusion matrix, PR curve,
metric và `pipeline_report.json`. Sau đó ONNX được kiểm tra cấu trúc và benchmark
trên `CUDAExecutionProvider`.

Sau kiểm thử offline, chạy lại trên CARLA:

```bash
venv/bin/python aeb/test_model.py
venv/bin/python aeb/test_fusion.py
```

Hai file này tự dùng `aeb/models/yolo26n.onnx` mới nếu model đã qua quality gate.

## Nguồn

- [Ultralytics - YOLO26 training recipe](https://github.com/ultralytics/ultralytics/blob/main/docs/en/guides/yolo26-training-recipe.md)
- [Ultralytics - Train mode](https://github.com/ultralytics/ultralytics/blob/main/docs/en/modes/train.md)
- [Ultralytics - YOLO26](https://github.com/ultralytics/ultralytics/blob/main/docs/en/models/yolo26.md)
