# AEB CARLA 0.9.11

Dự án mô phỏng hệ thống Autonomous Emergency Braking trên CARLA 0.9.11. Ego
vehicle là `vehicle.tesla.model3`, chạy chủ yếu trên cao tốc `Town04`, dùng 1
camera RGB sau kính lái và 1 radar ở mũi xe. Hướng phát triển là radar-only AEB
ổn định trước, sau đó bổ sung YOLO, camera-radar fusion và điều khiển phanh PID.

## Trạng Thái Hiện Tại

- Đã có giao diện 2 panel dựa trên `manual_control.py`: bên trái giữ manual
  control, bên phải là camera/radar/model/fusion debug view.
- Đã refactor code theo nhóm `ui/`, `scripts/`, `core/`, `perception/`,
  `control/`, `configs/`, `tests/`.
- Radar-only AEB đã chuyển từ chọn point đơn lẻ sang object list:
  radar point -> lọc -> clustering/tracking -> `RadarObjectList` -> chọn target
  -> TTC/khoảng cách dừng -> phanh.
- Batch scenario radar-only đã có log, ảnh, video và test tự động.
- Dataset collector YOLO một class `car` và pipeline train/export ONNX đã có
  khung chạy, cần tiếp tục thu data, audit và train model riêng.

## Cấu Trúc Chính

```text
aeb/
├── configs/              # cấu hình sensor, model, dataset, scenario
├── control/              # logic phanh và AEB controller
├── core/                 # pipeline, target selector, dữ liệu radar object
├── perception/           # xử lý cảm biến, hiện có radar object tracker
├── scripts/              # batch scenario, thu dataset, train model
├── ui/                   # các app 2 panel dùng manual_control.py
├── tests/                # unit test cho logic core và pipeline
├── docs/
│   ├── official/         # tài liệu kỹ thuật chính thức của dự án
│   ├── research/         # tài liệu nghiên cứu, so sánh repo/cảm biến/thực tế
│   ├── log/              # nhật ký thử nghiệm và các lần làm-sai-sửa
│   └── backup/           # tài liệu cũ được giữ lại để tra cứu
└── logs/                 # log, ảnh, video sinh ra khi chạy scenario
```

## Thứ Tự Đọc Tài Liệu

1. `docs/official/00_PROJECT_INTRODUCTION.md`: mục tiêu, phạm vi và trạng thái.
2. `docs/official/01_SYSTEM_ARCHITECTURE.md`: kiến trúc pipeline tổng thể.
3. `docs/official/02_SENSOR_CONFIGURATION.md`: cấu hình camera/radar/ego car.
4. `docs/official/03_RADAR_PROCESSING.md`: xử lý radar, object list và chọn target.
5. `docs/official/06_AEB_DECISION_AND_BRAKING.md`: TTC, khoảng cách dừng và phanh.
6. `docs/official/07_SCENARIOS_AND_VALIDATION.md`: scenario và cách đọc log.
7. `docs/official/08_DATASET_AND_TRAINING.md`: thu data và train YOLO.
8. `docs/research/00_ADAS_AEB_BACKGROUND.md`: nền tảng ADAS/AEB cho báo cáo.
9. `docs/research/07_REPO_COMPARISON_SUMMARY.md`: so sánh Autoware, openpilot,
   Apollo và hướng đang dùng trong project.
10. `docs/log/EXPERIMENT_LOG.md`: nhật ký thử nghiệm, kết quả và bằng chứng.

## Chạy CARLA

Từ thư mục gốc CARLA:

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Không dùng thêm `-opengl` trên máy hiện tại, vì cờ này từng làm pygame/manual
control render lỗi.

## Chạy Các App Debug

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python aeb/ui/camera_view.py
venv/bin/python aeb/ui/radar_view.py
venv/bin/python aeb/ui/radar_aeb_view.py -a
venv/bin/python aeb/ui/yolo_view.py
venv/bin/python aeb/ui/fusion_view.py
```

Nếu cửa sổ quá lớn:

```bash
venv/bin/python aeb/ui/radar_view.py --res 960x540
```

## Chạy Radar-Only Scenario

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --load-map
```

Log sẽ được ghi vào `logs/<run_id>/`. Xem thêm
`docs/official/07_SCENARIOS_AND_VALIDATION.md`.

## Thu Dataset Và Train YOLO

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python aeb/scripts/collect_yolo_dataset.py \
  --split train \
  --session-id town04_train_01 \
  --max-samples 500

venv/bin/python aeb/scripts/train_yolo_pipeline.py --audit-only
```

Chi tiết nằm ở `docs/official/08_DATASET_AND_TRAINING.md`.

## Kiểm Tra Nhanh

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Sau refactor cấu trúc code, unit test đã chạy qua `28/28 PASS` và smoke test
CARLA radar-only với `clear_road_50`, `ccrs_50` đã đạt `2/2 PASS`.

## Hướng Phát Triển

- Chốt radar-only AEB ở dải 50-80 km/h với false positive thấp.
- Thu và audit dataset camera, ưu tiên xe cùng làn và các case car-to-car.
- Train YOLO model riêng, export ONNX CUDA.
- Hoàn thiện fusion camera-radar để xác nhận target trước khi phanh.
- Thay binary brake bằng PID hoặc brake profile mượt hơn.
