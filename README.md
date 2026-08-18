# AEB CARLA 0.9.11

Dự án mô phỏng hệ thống phanh khẩn cấp tự động AEB (Autonomous Emergency
Braking) trên CARLA 0.9.11. Xe ego là `vehicle.tesla.model3`, chạy chủ yếu trên
cao tốc `Town04`, dùng một camera RGB đặt sau kính lái và một radar đặt ở mũi
xe.

Mục tiêu của dự án là xây dựng một pipeline AEB đủ rõ ràng để phục vụ đồ án:
cảm biến, xử lý radar, YOLO, hợp nhất dữ liệu camera-radar, chọn mục tiêu, tính
TTC/khoảng cách dừng, điều khiển phanh và đánh giá bằng log/biểu đồ/video.

Repository: https://github.com/mvhoang92/aeb

## Trạng Thái Hiện Tại

- Đã refactor mã nguồn theo nhóm `configs/`, `control/`, `core/`,
  `perception/`, `scripts/`, `ui/`, `tests/`.
- Radar đã chuyển từ phanh theo điểm đo đơn lẻ sang xử lý mức đối tượng:
  điểm đo -> lọc -> gom cụm -> theo dõi -> `RadarObjectList` -> chọn mục tiêu.
- YOLO26n đã được train lại cho bài toán một lớp `car` bằng dataset
  `dataset_v7_same_lane`.
- Camera-radar fusion đã được tích hợp vào giao diện và pipeline kiểm thử.
- Bộ phanh chính hiện tại là `staged_pid`, có nhiều tầng cảnh báo/phanh và có
  PID trong từng tầng.
- Final evidence hiện có 66 kịch bản system-limit, kết quả 63 đạt, 3 không đạt,
  tỷ lệ đạt 95,45%.
- Có launcher để bật CARLA, chạy UI, chạy kiểm thử và quay video.
- Có `report_mini.md`, thư mục `report/` chứa bản thảo full tách theo chương
  và hướng dẫn form/caption cho báo cáo đồ án.

## Cấu Trúc Thư Mục

```text
aeb/
├── configs/              # sensor, model, dataset, scenario YAML
│   └── scenarios/
│       ├── car_to_car/   # tình huống gốc: CCRs, CCRm, CCRb, cut-in...
│       └── suites/       # bộ gom để chạy smoke/regression/sweep/report demo
├── control/              # logic phanh, AEB state, PID/staged PID
├── core/                 # pipeline AEB, target selector, radar object data
├── perception/           # radar tracker và xử lý cảm biến
├── scripts/              # thu dataset, train/export model, chạy batch, video
├── ui/                   # camera/radar/YOLO/fusion/final demo/launcher views
├── tests/                # unit test cho logic core
├── docs/
│   ├── official/         # tài liệu kỹ thuật chính thức
│   ├── research/         # tài liệu tham khảo và so sánh repo/cảm biến
│   ├── log/              # nhật ký thí nghiệm, kết quả, quyết định kỹ thuật
│   └── backup/           # tài liệu cũ để tra cứu
├── report/               # bản thảo báo cáo full, tách theo chương
│   ├── chapters/         # từng chương để sửa cuốn chiếu
│   ├── assets/           # ảnh riêng cho báo cáo
│   ├── build_report.py   # ghép chương thành report/report.md
│   └── report.md         # bản full đã ghép để chuyển sang DOCX
├── paper/                # các phiên bản paper IEEE song ngữ
│   ├── README.md         # quy tắc bắt buộc build PDF Anh và Việt
│   ├── paper_v1/         # manuscript song ngữ đầu tiên
│   ├── paper_v2/         # bản nhấn mạnh đóng góp tích hợp hệ thống
│   └── paper_v3/         # bản hiện tại: research-audited, có hồ sơ phản biện
└── report_mini.md        # bản báo cáo ngắn để duyệt nhanh
```

Các thư mục sinh dữ liệu như `dataset*`, `logs/`, `outputs/`, `training_runs/`
và các model artifact `models/*.pt`, `models/*.onnx` được giữ local và đã đưa
vào `.gitignore`. Khi clone repo mới, cần train/export lại model hoặc đặt model
đúng đường dẫn trong `configs/sensors.yaml`.

## Thứ Tự Đọc Tài Liệu

1. `README.md`: tổng quan nhanh, cách chạy chính.
2. `report_mini.md`: bản tóm tắt nội dung đồ án.
3. `report/report.md`: bản thảo báo cáo full đã ghép.
4. `report/chapters/*.md`: nguồn sửa từng chương của báo cáo.
5. `docs/official/16_REPORT_FORMAT_AND_CAPTIONS.md`: quy ước form báo cáo,
   tên hình và tên bảng.
6. `docs/official/00_PROJECT_INTRODUCTION.md`: mục tiêu, phạm vi, kết quả hiện
   tại.
7. `docs/official/01_SYSTEM_ARCHITECTURE.md`: kiến trúc hệ thống.
8. `docs/official/02_SENSOR_CONFIGURATION.md`: cấu hình ego, camera, radar.
9. `docs/official/03_RADAR_PROCESSING.md`: xử lý radar từ điểm đo đến đối tượng.
10. `docs/official/04_CAMERA_YOLO_PROCESSING.md`: camera và YOLO.
11. `docs/official/05_CAMERA_RADAR_FUSION.md`: hợp nhất dữ liệu camera-radar.
12. `docs/official/06_AEB_DECISION_AND_BRAKING.md`: TTC, khoảng cách dừng,
    staged PID.
13. `docs/official/07_SCENARIOS_AND_VALIDATION.md`: kịch bản kiểm thử và cách
    đánh giá.
14. `docs/official/08_DATASET_AND_TRAINING.md`: dataset v7 same-lane và train
    YOLO26n.
15. `docs/log/FINAL_EVIDENCE_PACK_20260628.md`: kết quả final evidence.
16. `docs/log/REPORT_REWORK_TASKS.md`: task list cho lần viết lại báo cáo.

## Cài Đặt Nhanh

CARLA 0.9.11 cần được tải và giải nén trước. Sau đó clone project `aeb` trực
tiếp vào thư mục gốc CARLA:

```bash
cd /home/mvhoang/CARLA_0.9.11
git clone https://github.com/mvhoang92/aeb.git aeb
```

Môi trường CARLA dùng Python 3.7 ở thư mục gốc CARLA:

```bash
cd /home/mvhoang/CARLA_0.9.11
python3.7 -m venv venv
source venv/bin/activate
pip install numpy==1.21.6 pygame PyYAML opencv-python
```

Môi trường YOLO dùng Python 3.10 riêng trong `aeb/.venv_yolo310`.

## Chạy CARLA

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Không dùng thêm `-opengl` trên máy hiện tại vì từng gây lỗi render Pygame/manual
control.

## Chạy Launcher

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
python3 laucher.py
```

Launcher có các tab chính:

- `CARLA Server`: bật/tắt CARLA với NVIDIA offload và quality Low.
- `Ứng dụng UI`: chạy final demo 3 màn, camera, radar, YOLO, fusion hoặc radar
  AEB live scenario.
- `Kiểm thử`: chạy scenario batch, unit test, audit dataset.
- `Quay video`: quay video từ giao diện final demo và sinh report video.

Kiểm tra dependency launcher:

```bash
python3 laucher.py --check
```

## Chạy Final Demo 3 Màn

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python ui/aeb_demo_view.py \
  --res 1600x900 \
  --map-name Town04 \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --scenario cutin_80_50_gap_25 \
  --control-mode physics \
  --scenario-warmup-s 2
```

Giao diện gồm:

- camera + YOLO + fusion;
- manual/chase view;
- radar bird-eye, target, TTC, trạng thái AEB và lệnh phanh.

## Chạy Batch Final Evidence

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --control-mode physics \
  --load-map
```

Kết quả quan trọng hiện nằm ở:

```text
logs/final_evidence_staged_pid_20260628/
outputs/scenario_videos/final_evidence_videos_20260628_internal/
```

## Dataset Và Train YOLO

Kiểm tra dataset:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
.venv_yolo310/bin/python scripts/check_yolo_dataset.py
```

Train YOLO26n:

```bash
.venv_yolo310/bin/python scripts/train_yolo26n.py
```

Export ONNX:

```bash
.venv_yolo310/bin/python scripts/export_yolo26n_onnx.py
```

Model đang dùng:

```text
models/yolo26n_aeb_v7.pt
models/yolo26n_aeb_v7.onnx
```

## Unit Test

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

## Báo Cáo

- `report_mini.md`: bản đọc nhanh.
- `report/chapters/*.md`: nguồn sửa từng chương, dùng để làm cuốn chiếu.
- `report/report.md`: bản thảo full đã ghép, dùng để đọc tổng thể hoặc chuyển
  sang `.docx`.
- `report/build_report.py`: script ghép các chương sau khi chỉnh sửa.
- `docs/official/16_REPORT_FORMAT_AND_CAPTIONS.md`: quy ước tên hình/bảng để
  chuyển sang `.docx`.

Sau khi sửa một chương, ghép lại bản full bằng:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb/report
python3 build_report.py
```

Khi hoàn thiện báo cáo, link GitHub và link Google Drive video sẽ được đưa vào
phụ lục thay vì liệt kê toàn bộ đường dẫn local trong nội dung chính.
