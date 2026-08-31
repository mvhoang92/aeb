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

## Project Launcher

Launcher có giao diện để bật CARLA, chạy các app UI và chạy từng nhóm kiểm thử:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/usr/bin/python3 launcher.py
```

Launcher dùng Python hệ thống vì môi trường `venv` CARLA/YOLO có thể không có
`tkinter`. Nếu gọi `python3 launcher.py` trong một venv thiếu Tkinter, launcher
tự khởi động lại bằng `/usr/bin/python3`. Các nút bên trong vẫn gọi đúng Python
riêng cho từng phần.

Giao diện trình bày theo bốn bước `CARLA → ứng dụng → kiểm thử → ghi video`,
có trạng thái kết nối theo màu, command preview và nhật ký tiến trình tập trung.

Các chức năng chính:

- Kiểm tra trạng thái CARLA qua host/port.
- Bật CARLA với NVIDIA PRIME offload và quality Low/Epic.
- Chạy/dừng final demo 3 màn, camera, radar, YOLO, fusion và Radar AEB.
- Chọn scenario config và scenario trực tiếp từ YAML.
- Chọn validation mode hoặc realistic mode `phanh xong chạy tiếp`.
- Chọn loại phanh khi chạy UI: `binary`, `pid`, `pid_v2_comfort`, `staged_pid`
  hoặc dùng mặc định trong `sensors.yaml`.
- Chạy radar/fusion batch, unit test hoặc kiểm tra dataset YOLO.
- Quay video bằng UI final, có run-id và report riêng.
- Hiển thị lệnh trước khi chạy và gom log của các tiến trình.

Kiểm tra dependency mà không mở cửa sổ:

```bash
/usr/bin/python3 launcher.py --check
```

## Scenario Config

Scenario YAML hiện chia theo hai tầng:

```text
configs/scenarios/
├── car_to_car/   # chia theo tình huống: CCRs, CCRm, CCRb, cut-in, cut-out...
└── suites/       # bộ gom để chạy: smoke, regression, sweep, report demo
```

Khi chạy thủ công, ưu tiên dùng các file trong `configs/scenarios/suites/`.
Khi muốn xem riêng một loại tình huống, dùng file trong
`configs/scenarios/car_to_car/`.

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

## Vẽ Tầm Camera Và Radar

Script này bắt buộc dùng `vehicle.tesla.model3`, đọc sensor từ
`configs/sensors.yaml`, vẽ FOV camera/radar trong CARLA rồi chụp 4 ảnh minh họa
góc nhìn trên xuống/ngang, gần/xa:

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python aeb/scripts/visualize_sensor_coverage.py \
  --config aeb/configs/sensors.yaml \
  --output-dir "$AEB_WORKSPACE_ROOT/runs/sensor_coverage/manual_capture" \
  --map-name Town06 \
  --spawn-index 0
```

`Town06` được dùng ở đây chỉ để lấy ảnh minh họa thoáng, đặc biệt cho góc nhìn
hình chiếu cạnh. Scenario AEB chính vẫn ưu tiên chạy trên `Town04`.

Kết quả:

```text
$AEB_WORKSPACE_ROOT/runs/sensor_coverage/manual_capture/
├── near_top_view.png
├── far_top_view.png
├── near_side_view.png
├── far_side_view.png
└── sensor_coverage_metadata.json
```

## Batch Radar-Only

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --control-mode physics \
  --load-map
```

Chạy một vài scenario cụ thể:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --control-mode physics \
  --scenario clear_road_50 \
  --scenario ccrs_50 \
  --load-map
```

## Xem Trực Tiếp Từng Scenario Radar-Only

Màn này mở giao diện `manual_control` bên trái và radar-only AEB bên phải, đồng
thời tự spawn/điều khiển một scenario để quan sát trực tiếp.

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python ui/radar_aeb_view.py \
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --control-mode physics \
  --scenario ccrs_60_demo_150
```

Khi chạy scenario trong UI, script tự chuyển camera trái sang `wide_chase`, dọn
actor scenario cũ, vẽ nhãn target và đường nối đỏ trong CARLA để dễ nhìn. Nếu
muốn giữ nguyên camera của `manual_control.py`, thêm:

```bash
--scenario-camera manual
```

Mặc định, khi AEB đã vào trạng thái `BRAKE`, scenario sẽ khóa ego ở chế độ dừng:
không đạp ga lại và giữ phanh để đo khoảng cách dừng cuối. Nếu muốn quay về hành
vi cũ, tức AEB nhả phanh thì controller lại bám tốc độ mục tiêu, thêm:

```bash
--keep-driving-after-aeb
```

Nếu máy bị lag khi chạy UI, giảm độ phân giải mỗi panel hoặc giảm tần suất debug
draw:

```bash
--res 960x540 --scenario-debug-interval-s 0.2
```

Live scenario có warm-up mặc định 1 giây sau khi spawn xe/đổi camera rồi mới cho
ego chạy và bắt đầu tính thời gian. Nếu máy bị khựng nhiều ở lúc xe vừa hiện,
tăng warm-up hoặc giữ camera manual để tránh respawn camera chase:

```bash
--scenario-warmup-s 2.0
--scenario-camera manual
```

Bài dài hơn cho báo cáo: xe trước đứng yên cách 200 m, ego chạy 60 km/h. Vì
radar hiện có range 100 m, giai đoạn đầu cố ý chưa thấy target cho đến khi ego
đi vào vùng radar. Scenario này dùng `spawn_index=81`, một đoạn Town04
rộng/thẳng hơn:

```bash
../venv/bin/python ui/radar_aeb_view.py \
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --control-mode physics \
  --scenario ccrs_60_gap_200
```

Muốn chạy bài khác thì tắt cửa sổ và đổi `--scenario`, ví dụ:

```bash
../venv/bin/python ui/radar_aeb_view.py \
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --control-mode physics \
  --scenario adjacent_stationary_65
```

Chế độ này dùng để nhìn trực quan. Nếu cần log khách quan, video evidence và
PASS/FAIL thì dùng batch runner ở mục trên.

## Dataset Và Train YOLO

Các bước kiểm tra dữ liệu, train và export ONNX được tách riêng. Dùng môi
trường Python 3.10 dành cho YOLO, không dùng Python 3.7 của CARLA.

Kiểm tra dataset:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
$AEB_WORKSPACE_ROOT/environments/yolo310/bin/python scripts/check_yolo_dataset.py
```

Train YOLO26n:

```bash
$AEB_WORKSPACE_ROOT/environments/yolo310/bin/python scripts/train_yolo26n.py
```

Weight tốt nhất nằm trong:

```text
$AEB_WORKSPACE_ROOT/training/detect/<run_name>/weights/best.pt
```

Export weight mới nhất sang ONNX:

```bash
$AEB_WORKSPACE_ROOT/environments/yolo310/bin/python scripts/export_yolo26n_onnx.py
```

Hoặc chỉ định rõ weight:

```bash
$AEB_WORKSPACE_ROOT/environments/yolo310/bin/python scripts/export_yolo26n_onnx.py \
  --weights "$AEB_WORKSPACE_ROOT/training/detect/<run_name>/weights/best.pt"
```

Có thể thêm `--dry-run` vào lệnh train hoặc export để chỉ kiểm tra đường dẫn và
khả năng load model.

## Unit Test

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

## Ghi Log

Các script batch ghi vào `$AEB_WORKSPACE_ROOT/runs/logs/<run_id>/`. Khi có kết quả quan trọng, chỉ cập
nhật tóm tắt vào `docs/log/EXPERIMENT_LOG.md`; không đưa toàn bộ log thô vào
tài liệu chính thức.
