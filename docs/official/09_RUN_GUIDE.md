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

Giao diện trình bày theo bốn bước `CARLA → ứng dụng → kiểm thử → ghi video`
ở thanh điều hướng bên trái, có trạng thái kết nối theo màu (góc trên bên phải),
command preview kèm nút sao chép luôn hiển thị ở cuối mỗi trang, và nhật ký tiến
trình tập trung có thể kéo giãn. Trang dài tự cuộn; kích thước chữ và cửa sổ tự
co giãn theo DPI màn hình (`Xft.dpi`). Mở thẳng một trang hoặc đặt kích thước:

```bash
/usr/bin/python3 launcher.py --page tests          # carla | apps | tests | video
/usr/bin/python3 launcher.py --geometry 1280x800
```

Mã nguồn giao diện nằm trong `ui/launcher/` (`launcher.py` chỉ là entry point);
các lệnh được dựng bởi hàm thuần trong `ui/launcher/commands.py` và được khóa
bằng `tests/test_launcher_commands.py`.

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

## AEB Test Bench v2 (`launcher_v2.py`)

Test Bench v2 là launcher thứ hai, độc lập hoàn toàn với `launcher.py` (mã
nguồn riêng trong `ui/testbench/`, không import `ui/launcher/`). Nó chỉ dựng
lệnh cho hai runner có sẵn và chỉ đọc YAML kịch bản/log, không ghi config hay
bằng chứng.

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/usr/bin/python3 launcher_v2.py            # mở cửa sổ "AEB Test Bench v2"
/usr/bin/python3 launcher_v2.py --check    # kiểm tra điều kiện, không mở cửa sổ
```

Màn **Thí nghiệm** đi theo thứ tự định nghĩa một thí nghiệm:

1. **Kịch bản**: cây file suite → nhóm tình huống (CCRs, CCRm, CCRb, cut-in,
   đường trống, xe làn bên, vật ven đường, radar ma…) → kịch bản, ô chọn ba
   trạng thái, tìm kiếm, lọc theo kỳ vọng (phải phanh / không được phanh / va
   chạm chấp nhận được) và bảng chi tiết bằng tiếng Việt.
2. **Hệ thống được kiểm tra**: Radar-only (`configs/sensors.yaml`), Camera hard
   gate (`sensors_fusion_hard_batch_{gpu,cpu}.yaml`), Gate + radar emergency
   fallback (`sensors_fusion_safe_fallback_batch_{gpu,cpu}.yaml`); chọn nhiều
   để so sánh cặp. Thiết bị CUDA/CPU và chế độ physics/deterministic.
3. **Thiết kế thí nghiệm**: số lần lặp, seed, cooldown, reload world, load map,
   ghi video, `--resume`, run-id (mẫu `tb_<mẫu|custom>_{policy}[_{suite}]_<thời gian>`).
4. **Kế hoạch chạy**: mỗi dòng là một lệnh = một thư mục log, kèm số lượt chạy,
   thời gian ước lượng và lệnh chính xác (sao chép được).
5. **Chạy**: hàng đợi tuần tự, tiến độ, log trực tiếp, dừng lệnh/hàng đợi.
   Exit 1 = có FAIL thuật toán (bằng chứng, hàng đợi chạy tiếp); exit 3 =
   HARD-STOP kỹ thuật thiếu CUDA; traceback/CARLA crash = lỗi kỹ thuật. Hai loại
   kỹ thuật được hiển thị khác màu và mặc định dừng hàng đợi.

Cách dựng lệnh: một lệnh cho mỗi cặp (file suite × hệ thống). Chọn cả suite thì
không truyền `--scenario` (giống chiến dịch của paper); chọn một phần thì
truyền nhiều `--scenario` trong cùng lệnh (runner hỗ trợ `action="append"`), nên
mỗi cặp vẫn chỉ có một thư mục log. Không sinh YAML tạm, vì SHA-256 của file
suite thật được ghi vào `run_metadata.json`. Lệnh được xếp theo từng suite (mọi
hệ thống của suite này rồi mới tới suite sau) để hàng đợi bị ngắt vẫn để lại
các cặp so sánh hoàn chỉnh.

Mẫu một chạm: **Smoke nhanh** (`smoke_basic.yaml`, radar-only, 1 lần),
**Hồi quy core** (4 suite phạm vi core của paper × 3 hệ thống, CUDA, physics)
và **Hold-out** (`fusion_fallback_holdout.yaml` × 3 hệ thống). Giao thức paper
dùng 5 lần lặp; hai mẫu sau mặc định 1 lần và có nút chuyển sang 5 lần kèm thời
gian ước lượng.

Màn **Kết quả** liệt kê thư mục log (mới nhất trước) với hệ thống/suite/PASS
từ `run_metadata.json`; chọn một run để xem từng lượt chạy (kỳ vọng và thực tế
phanh/va chạm, gap nhỏ nhất, PASS/FAIL) cùng TP/FP/TN/FN, precision, recall; giữ
Ctrl chọn run thứ hai để xem bảng cặp theo điều kiện có tên (cả hai PASS / chỉ
A / chỉ B / cả hai FAIL / lặp không nhất quán) — cùng logic bảng McNemar của
paper, chỉ mô tả, không tính p-value.

Cờ tự động hóa (dùng cho kiểm thử end-to-end):

```bash
/usr/bin/python3 launcher_v2.py --preset smoke --autostart --exit-when-done
/usr/bin/python3 launcher_v2.py --scenario configs/scenarios/suites/smoke_basic.yaml:ccrs_30 \
  --policy fallback --device cuda --autostart --exit-when-done
/usr/bin/python3 launcher_v2.py --page results --select-run <run-id> --select-run <run-id>
```

Trạng thái CARLA được đọc từ bảng socket của kernel (`/proc/net/tcp`), không mở
kết nối tới cổng RPC, và tạm ngưng khi hàng đợi đang chạy. Kiểm thử:
`tests/test_testbench_plan.py`, `tests/test_testbench_results.py`,
`tests/test_testbench_gui.py`.

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
