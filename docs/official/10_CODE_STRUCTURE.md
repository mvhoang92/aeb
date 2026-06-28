# 10. Cấu Trúc Code

Tài liệu này mô tả nơi nên đọc/sửa code sau khi dự án đã tách khỏi kiểu đặt mọi
script ở root.

## UI

- `ui/manual_control_common.py`: helper dùng chung để giữ manual control gốc ở
  panel trái.
- `ui/camera_view.py`: test camera sau kính lái.
- `ui/radar_view.py`: bird-eye radar point/object debug.
- `ui/radar_aeb_view.py`: radar-only AEB + override phanh.
- `ui/yolo_view.py`: camera + YOLO bbox.
- `ui/fusion_view.py`: camera + bbox + thông số radar.

## Core

- `core/radar_aeb_pipeline.py`: pipeline radar-only dùng chung cho UI và batch.
- `core/radar_object.py`: cấu trúc dữ liệu `RadarObject` và object list.
- `core/target_selector.py`: chọn target AEB từ radar object list.

## Perception

- `perception/radar/radar_object_tracker.py`: clustering, tracking và tạo radar
  object từ point.

## Control

- `control/brake.py`: TTC, quyết định phanh, binary brake và helper override
  `carla.VehicleControl`.

## Scripts

- `scripts/run_radar_aeb_scenarios.py`: chạy batch scenario và sinh log.
- `scripts/collect_yolo_dataset.py`: thu dataset YOLO bằng ground truth CARLA.
- `scripts/check_yolo_dataset.py`: audit dataset YOLO trước khi train.
- `scripts/train_yolo26n.py`: train YOLO26n trên dataset đã cấu hình.
- `scripts/export_yolo26n_onnx.py`: export `best.pt` sang ONNX cho runtime.
- `scripts/train_yolo_pipeline.py`: pipeline tổng hợp đời cũ, chỉ giữ để tham
  khảo hoặc chạy lại log cũ.

## Tests

- `tests/test_radar_aeb_logic.py`: logic radar/AEB.
- `tests/test_dataset_collector_helpers.py`: helper dataset.
- `tests/test_model_pipeline.py`: pipeline train/model.
- `tests/test_onnx_model_names.py`: kiểm tra tên model ONNX.

## Quy Ước Sửa Code

- Logic dùng chung đặt trong `core/`, `perception/` hoặc `control/`.
- UI chỉ nên render và gọi pipeline, không nhồi thêm thuật toán AEB phức tạp.
- Batch script chỉ nên dựng scenario, gọi pipeline và ghi log.
- Khi thay logic radar/AEB, chạy unit test trước rồi smoke test CARLA.
