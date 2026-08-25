# AEB CARLA 0.9.11

Dự án mô phỏng hệ thống phanh khẩn cấp tự động AEB (Automatic Emergency
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
- Ba chính sách được đánh giá: radar-only, hard camera gate và camera gate có
  radar emergency fallback; bộ phanh dùng `staged_pid`.
- Final GPU campaign đã khóa trước hold-out gồm 2.461/2.461 runs trong 639 phiên
  CARLA; 474 CUDA sessions ghi 74.928 inference và không có inference error.
- Trên core benchmark không tính synthetic fault, precision/recall lần lượt là
  0,913/0,988; 1,000/0,965; và 1,000/0,988. Frozen hold-out cho kết quả PASS
  30/70, 55/70 và 35/70, thể hiện trade-off thay vì ưu thế tổng quát.
- Có launcher để bật CARLA, chạy UI, chạy kiểm thử và quay video.
- Báo cáo v3 và paper v5 song ngữ đã có source, PDF/DOCX, claim–evidence matrix,
  scenario-level/severity analysis và raw evidence kèm SHA-256.

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
├── report/               # báo cáo đồ án, source theo chương và export
│   ├── chapters_v3/      # source of truth của report v3
│   ├── assets/           # ảnh riêng và figures final evidence
│   ├── build_report_v3.py
│   ├── export_report_v3.py
│   └── report_v3.md      # bản full v3 đã ghép
├── paper/                # các phiên bản paper IEEE song ngữ
│   ├── README.md         # quy tắc build PDF Anh và Việt
│   ├── paper_v1..v4/     # manuscript và final-campaign revision lịch sử
│   └── paper_v5/         # reviewer-driven scenario/severity study
└── report_mini.md        # bản báo cáo ngắn để duyệt nhanh
```

Các thư mục sinh dữ liệu như `dataset*`, `logs/`, `outputs/`, `training_runs/`
và các model artifact `models/*.pt`, `models/*.onnx` được giữ local và đã đưa
vào `.gitignore`. Khi clone repo mới, cần train/export lại model hoặc đặt model
đúng đường dẫn trong `configs/sensors.yaml`.

## Thứ Tự Đọc Tài Liệu

1. `README.md`: tổng quan nhanh, cách chạy chính.
2. `report/report_v3.md`: báo cáo final đã ghép.
3. `report/chapters_v3/*.md`: nguồn chính để sửa report v3.
4. `paper/paper_v5/aeb_ieee_6page.pdf`: paper tiếng Anh sáu trang.
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
15. `docs/log/PAPER_V4_EVALUATION_PROTOCOL.md`: protocol khóa trước hold-out.
16. `docs/log/repeatability/paper_v4_gpu_final/FINAL_GPU_EVIDENCE.md`: kết quả final.
17. `paper/paper_v5/CLAIM_EVIDENCE_MATRIX.md`: mapping claim và artifact.
18. `docs/log/repeatability/artifacts/`: raw-log archive và SHA-256.

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

Headline evidence hiện nằm ở:

```text
outputs/paper_v4_final_pipeline/paper_v4_gpu_final_locked_20260825/
docs/log/repeatability/paper_v4_gpu_final/
docs/log/repeatability/artifacts/paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz
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

- `report/chapters_v3/*.md`: source of truth của report v3.
- `report/report_v3.md`: bản Markdown full đã ghép.
- `report/exports/aeb_report_v3.docx`: bản DOCX theo form cũ.
- `report/exports/aeb_report_v3.pdf`: bản PDF A4 để duyệt.

Sau khi sửa source, build và export lại bằng:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/usr/bin/python3 report/build_report_v3.py
/usr/bin/python3 report/export_report_v3.py
```

Khi hoàn thiện báo cáo, link GitHub và link Google Drive video sẽ được đưa vào
phụ lục thay vì liệt kê toàn bộ đường dẫn local trong nội dung chính.
