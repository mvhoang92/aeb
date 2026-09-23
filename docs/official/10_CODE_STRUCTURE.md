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
- `core/headless_aeb_runtime.py`: thứ tự runtime dùng chung pipeline → policy → actuation.
- `core/brake_permission_policy.py`: interface radar-only, hard camera gate và emergency fallback.
- `core/fusion_brake_gate.py`: cơ chế gate/fallback đã được kiểm chứng và giữ nguyên.
- `core/radar_object.py`: cấu trúc dữ liệu `RadarObject` và object list.
- `core/target_selector.py`: chọn target AEB từ radar object list.

## Perception

- `perception/radar/radar_object_tracker.py`: clustering, tracking và tạo radar
  object từ point.

## Control

- `control/brake.py`: compatibility facade giữ nguyên import lịch sử.
- `control/risk_model.py`: TTC và stopping distance.
- `control/controller.py`: orchestration `BinaryAEB`.
- `control/staged_pid.py`: binary/staged/PID brake command.
- `control/state_machine.py`: validation, hysteresis và transition.
- `control/actuation.py`: helper override `carla.VehicleControl`.

## Scripts

- `scripts/run_radar_aeb_scenarios.py` và `run_fusion_aeb_scenarios.py`: stable
  scenario CLI và sinh log.
- `scripts/campaign/`: campaign orchestration và final pipeline.
- `scripts/analysis/`: analysis, repeatability summary và manuscript validators.
- `scripts/dataset/`: thu thập/audit/cleanup dataset.
- `scripts/training/`: training và ONNX export.
- `scripts/maintenance/`: công cụ bảo trì/visualization.
- Các file cùng tên ở `scripts/` là compatibility wrapper cho command lịch sử.

## Tests

- `tests/test_radar_aeb_logic.py`: logic radar/AEB.
- `tests/test_brake_permission_policy.py`: golden output ba policy.
- `tests/test_headless_aeb_runtime.py`: runtime policy injection.
- `tests/test_evaluation_modules.py`: schema/scoring/severity/summary compatibility.
- `tests/test_control_modules.py`: facade và control decomposition.
- `tests/test_script_compatibility.py`: wrapper script lịch sử.
- Các test dataset/model/ONNX tiếp tục bảo vệ pipeline train/model.

## Quy Ước Sửa Code

- Logic dùng chung đặt trong `core/`, `perception/` hoặc `control/`.
- UI chỉ nên render và gọi pipeline, không nhồi thêm thuật toán AEB phức tạp.
- Batch script chỉ nên dựng scenario, gọi pipeline và ghi log.
- Khi thay logic radar/AEB, chạy unit test trước rồi smoke test CARLA.
