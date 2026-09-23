# Hướng Dẫn Cấu Trúc File Code

Tài liệu này giúp đọc nhanh codebase AEB sau khi đã tách lại theo vai trò
module. Các script chính không còn nằm ở root `aeb/`.

## 1. UI Và Demo Tương Tác

Các file trong `ui/` là công cụ xem trực tiếp bằng pygame/manual control, không
phải unit test:

| File | Vai trò |
| --- | --- |
| `ui/camera_view.py` | Manual control bên trái, camera sau kính lái bên phải. |
| `ui/radar_view.py` | Manual control bên trái, bird-eye radar bên phải. |
| `ui/radar_aeb_view.py` | Radar-only AEB tương tác, có FCW/AEB và override phanh. |
| `ui/yolo_view.py` | Camera + YOLO bbox. |
| `ui/fusion_view.py` | Camera + YOLO bbox + radar projection/debug fusion. |
| `ui/manual_control_common.py` | Helper chung: CARLA sensor, hai panel, YOLO runtime, vẽ UI. |

Ví dụ chạy:

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python aeb/ui/radar_aeb_view.py -a
```

## 2. Script Batch, Dataset Và Training

Các file trong `scripts/` là script chạy batch hoặc pipeline dữ liệu:

| File | Vai trò |
| --- | --- |
| `scripts/run_radar_aeb_scenarios.py` | Tự spawn scenario radar-only AEB, chạy regression, ghi log/evidence. |
| `scripts/collect_yolo_dataset.py` | Thu ảnh RGB và nhãn YOLO từ ground truth CARLA. |
| `scripts/train_yolo_pipeline.py` | Audit dataset, train/test YOLO26n, export ONNX và deploy model. |

Ví dụ chạy:

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python aeb/scripts/collect_yolo_dataset.py --split train --session-id town04_train_01
python3 aeb/scripts/train_yolo_pipeline.py --audit-only
```

## 3. Core AEB

Các file trong `core/` là logic dùng chung cho UI và batch test:

| File | Vai trò |
| --- | --- |
| `core/radar_aeb_pipeline.py` | Pipeline radar-only: lọc point, cập nhật object list, chọn target và gọi AEB decision. |
| `core/radar_object.py` | Biểu diễn `RadarObject`/object-list từ track radar CARLA. |
| `core/target_selector.py` | Chọn object nguy hiểm nhất cho AEB. |
| `core/ground_truth_labels.py` | Chiếu bounding box 3D CARLA lên ảnh và hỗ trợ tạo label YOLO. |

## 4. Perception Và Control

| File | Vai trò |
| --- | --- |
| `perception/radar/radar_object_tracker.py` | Gom radar point thành cluster, tracking qua frame, xác nhận object. |
| `control/brake.py` | State machine FCW/AEB, TTC, khoảng cách dừng và helper override phanh CARLA. |

## 5. Tests

Unit test thật nằm trong `tests/`, không nằm trong `ui/`.

Chạy test:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Nhóm test chính:

- `test_radar_aeb_logic.py`: radar object/tracker, target selector, BinaryAEB,
  evidence event và scenario helper.
- `test_ground_truth_labels.py`: chiếu box và xử lý label ground truth.
- `test_dataset_collector_helpers.py`: helper thu dataset.
- `test_model_pipeline.py`: audit dataset và pipeline train model.
- `test_onnx_model_names.py`: đọc tên class từ ONNX/YOLO helper.

## 6. Nguyên Tắc Sửa Code

- Sửa giao diện/debug trực tiếp trong `ui/`.
- Sửa batch scenario/log trong `scripts/run_radar_aeb_scenarios.py`.
- Sửa thu dataset trong `scripts/collect_yolo_dataset.py` và
  `core/ground_truth_labels.py`.
- Sửa train/export model trong `scripts/train_yolo_pipeline.py`.
- Sửa thuật toán radar-only AEB trong `core/`, `perception/radar/` và
  `control/`.
- Sau mỗi thay đổi logic, chạy unit test và nếu CARLA đang bật thì chạy một
  scenario smoke.
