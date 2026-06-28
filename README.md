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
2. `docs/official/13_PROJECT_PROGRESS_REPORT.md`: báo cáo tiến độ tổng hợp,
   gồm giới thiệu dự án, research đã tham khảo, pipeline dự kiến/hiện tại và
   checklist đã làm/đang làm/sẽ làm.
3. `docs/official/11_ENVIRONMENT_AND_INSTALLATION.md`: cấu hình máy, tải CARLA,
   đặt thư mục `aeb/` và tạo môi trường Python.
4. `docs/official/01_SYSTEM_ARCHITECTURE.md`: kiến trúc pipeline tổng thể.
5. `docs/official/02_SENSOR_CONFIGURATION.md`: cấu hình camera/radar/ego car.
6. `docs/official/03_RADAR_PROCESSING.md`: xử lý radar, object list và chọn target.
7. `docs/official/06_AEB_DECISION_AND_BRAKING.md`: TTC, khoảng cách dừng và phanh.
8. `docs/official/07_SCENARIOS_AND_VALIDATION.md`: scenario và cách đọc log.
9. `docs/official/08_DATASET_AND_TRAINING.md`: thu data và train YOLO.
10. `docs/research/00_ADAS_AEB_BACKGROUND.md`: nền tảng ADAS/AEB cho báo cáo.
11. `docs/research/07_REPO_COMPARISON_SUMMARY.md`: so sánh Autoware, openpilot,
   Apollo và hướng đang dùng trong project.
12. `docs/official/12_AI_WORKFLOW.md`: quy trình giao việc cho AI, test, cập
   nhật tài liệu và push GitHub.
13. `docs/official/15_CONTRIBUTING_AND_TASK_WORKFLOW.md`: onboarding cho người
   mới hoặc AI khác, gồm cách nhận task, sửa code, test và bàn giao.
14. `docs/log/EXPERIMENT_LOG.md`: nhật ký thử nghiệm, kết quả và bằng chứng.

## Cài Đặt Nhanh

CARLA 0.9.11 cần được tải và giải nén trước. Sau đó clone project `aeb` trực
tiếp vào thư mục gốc CARLA:

```bash
cd /home/mvhoang/CARLA_0.9.11
git clone https://github.com/mvhoang92/aeb.git aeb
```

Project hiện dùng Python 3.7 và `venv/` ở thư mục gốc CARLA:

```bash
cd /home/mvhoang/CARLA_0.9.11
python3.7 -m venv venv
source venv/bin/activate
pip install numpy==1.21.6 pygame PyYAML opencv-python
```

Xem đầy đủ tại `docs/official/11_ENVIRONMENT_AND_INSTALLATION.md`.

## Chạy CARLA

Từ thư mục gốc CARLA:

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Không dùng thêm `-opengl` trên máy hiện tại, vì cờ này từng làm pygame/manual
control render lỗi.

## Launcher Giao Diện

Launcher tập trung việc bật/tắt CARLA, chạy các app debug và chạy kiểm thử:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
python3 laucher.py
```

Launcher dùng `python3` hệ thống vì `venv` CARLA/YOLO trên máy hiện tại không có
`tkinter`. Bên trong launcher vẫn tự gọi đúng `venv/bin/python` cho CARLA và
`.venv_yolo310/bin/python` cho YOLO khi cần.

Launcher có bốn tab:

- `CARLA Server`: chọn quality, bật NVIDIA offload, bật/dừng server.
- `Ứng dụng UI`: chạy final demo 3 màn, camera, radar, YOLO, fusion hoặc Radar
  AEB live scenario. Có lựa chọn validation mode hoặc realistic mode
  `phanh xong chạy tiếp`, và chọn loại phanh `binary`, `pid`, `pid_v2_comfort`
  hoặc `staged_pid`.
- `Kiểm thử`: chạy radar/fusion scenario batch, unit test hoặc audit dataset
  YOLO.
- `Quay video`: gọi script quay video UI final và sinh report video.

Có thể kiểm tra dependency của launcher mà không mở cửa sổ:

```bash
python3 laucher.py --check
```

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
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --control-mode physics \
  --load-map
```

Log sẽ được ghi vào `logs/<run_id>/`. Xem thêm
`docs/official/07_SCENARIOS_AND_VALIDATION.md`.

## Cấu Trúc Scenario Config

Các scenario YAML được chia lại theo hai tầng:

- `configs/scenarios/car_to_car/`: thư viện tình huống gốc, chia theo bản chất
  bài test như CCRs xe trước đứng yên, CCRm xe trước chạy chậm, CCRb xe trước
  phanh gấp, cut-in, cut-out, adjacent, curve và multi-actor.
- `configs/scenarios/suites/`: bộ gom để chạy theo mục tiêu như smoke test,
  radar-only regression, fusion regression, system-limit sweep và report demo.

Launcher ưu tiên hiển thị các tên này thay vì bắt người dùng nhớ file YAML cũ.

## Thu Dataset Và Train YOLO

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
.venv_yolo310/bin/python scripts/check_yolo_dataset.py
.venv_yolo310/bin/python scripts/train_yolo26n.py
.venv_yolo310/bin/python scripts/export_yolo26n_onnx.py
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
# documents
