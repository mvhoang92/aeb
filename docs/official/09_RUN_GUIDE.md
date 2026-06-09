# 09. Hướng Dẫn Chạy

Trước khi chạy, cần cài CARLA 0.9.11, đặt thư mục `aeb/` trong thư mục gốc
CARLA và tạo `venv/`. Xem chi tiết ở
`docs/official/11_ENVIRONMENT_AND_INSTALLATION.md`.

## Khởi Động CARLA

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Không thêm `-opengl` trên cấu hình máy hiện tại.

## App UI

```bash
venv/bin/python aeb/ui/camera_view.py
venv/bin/python aeb/ui/radar_view.py
venv/bin/python aeb/ui/radar_aeb_view.py -a
venv/bin/python aeb/ui/yolo_view.py
venv/bin/python aeb/ui/fusion_view.py
```

Giảm kích thước cửa sổ:

```bash
venv/bin/python aeb/ui/radar_view.py --res 960x540
```

Chọn map:

```bash
venv/bin/python aeb/ui/camera_view.py --map-name Town04
```

## Batch Radar-Only

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --load-map
```

Chạy một vài scenario cụ thể:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --scenario clear_road_50 \
  --scenario ccrs_50 \
  --load-map
```

## Dataset Và Model

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python aeb/scripts/collect_yolo_dataset.py \
  --split train \
  --session-id town04_train_01 \
  --max-samples 500

venv/bin/python aeb/scripts/train_yolo_pipeline.py --audit-only
```

## Unit Test

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

## Ghi Log

Các script batch ghi vào `logs/<run_id>/`. Khi có kết quả quan trọng, chỉ cập
nhật tóm tắt vào `docs/log/EXPERIMENT_LOG.md`; không đưa toàn bộ log thô vào
tài liệu chính thức.
