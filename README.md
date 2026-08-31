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
├── control/              # risk, state machine, staged/PID và actuation
├── core/                 # pipeline, target, fusion gate và policy interface
├── evaluation/           # schema, telemetry, scoring, severity và summary
├── infrastructure/       # external-workspace path resolver
├── perception/           # radar tracker và xử lý cảm biến
├── scripts/              # stable CLIs + categorized implementations
├── ui/                   # camera/radar/YOLO/fusion/final demo views
├── tests/                # unit, golden, compatibility và schema tests
├── models/               # deployment model/manifest local
├── docs/
│   ├── INDEX.md          # canonical reading map
│   ├── official/         # tài liệu kỹ thuật chi tiết
│   ├── research/         # hướng nghiên cứu, gồm PERG-AEB
│   ├── log/              # frozen evidence và experiment records
│   └── history/          # tài liệu legacy chỉ để tra cứu
├── report/
│   ├── report_v3.md      # frozen current report
│   ├── chapters_v3/
│   ├── exports/          # frozen PDF/DOCX v3
│   └── archive/          # report v1/v2, drafts và layout QA
└── paper/
    ├── CURRENT.md
    ├── VERSION_INDEX.md
    └── paper_v1/ ... paper_v5/
```

Dataset và generated artifacts được giữ ngoài Git tree tại workspace mặc định
`/home/mvhoang/CARLA_0.9.11/aeb_workspace`. Có thể đổi vị trí bằng biến
`AEB_WORKSPACE_ROOT`. Chạy `../venv/bin/python scripts/check_workspace.py` để
xem toàn bộ đường dẫn đã resolve. Các config lịch sử như
`aeb/dataset_v7_same_lane` được ánh xạ có kiểm soát sang workspace.

## Thứ Tự Đọc Tài Liệu

1. `docs/INDEX.md`: chọn lộ trình theo vai trò.
2. `docs/01_QUICK_START.md`: setup, workspace và smoke test.
3. `docs/02_SYSTEM_ARCHITECTURE.md`: kiến trúc source hiện hành.
4. `docs/03_BRAKE_POLICIES.md`: ba baseline và contract policy.
5. `docs/04_SCENARIO_AND_EVALUATION.md`: scoring, severity và failure handling.
6. `docs/05_WORKSPACE_AND_ARTIFACTS.md`: dữ liệu local, backup và checksum.
7. `docs/06_REPRODUCIBILITY.md`: protocol tái lập evidence.
8. `docs/07_EXTENDING_THE_SYSTEM.md`: thêm policy/scenario/metric.
9. `paper/CURRENT.md` và `report/README.md`: manuscript/report hiện hành.

Tài liệu chi tiết theo từng subsystem vẫn nằm trong `docs/official/`; historical
notes và frozen evidence được index nhưng không dùng làm quick-start.

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

Môi trường YOLO dùng Python 3.10 tại
`$AEB_WORKSPACE_ROOT/environments/yolo310`; có thể override launcher bằng
`AEB_YOLO_PYTHON`.

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
python3 launcher.py
```

Tên lịch sử `python3 laucher.py` vẫn được hỗ trợ qua compatibility wrapper.

Launcher có các tab chính:

- `CARLA Server`: bật/tắt CARLA với NVIDIA offload và quality Low.
- `Ứng dụng UI`: chạy final demo 3 màn, camera, radar, YOLO, fusion hoặc radar
  AEB live scenario.
- `Kiểm thử`: chạy scenario batch, unit test, audit dataset.
- `Quay video`: quay video từ giao diện final demo và sinh report video.

Kiểm tra dependency launcher:

```bash
python3 launcher.py --check
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
$AEB_WORKSPACE_ROOT/runs/campaigns/paper_v4_final_pipeline/
docs/log/repeatability/paper_v4_gpu_final/
docs/log/repeatability/artifacts/paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz
```

Đường dẫn workspace là local runtime storage; curated evidence trong `docs/`
và frozen Git tags vẫn là nguồn claim chính.

## Dataset Và Train YOLO

Kiểm tra dataset:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
${AEB_WORKSPACE_ROOT:-/home/mvhoang/CARLA_0.9.11/aeb_workspace}/environments/yolo310/bin/python scripts/check_yolo_dataset.py
```

Train YOLO26n:

```bash
${AEB_WORKSPACE_ROOT:-/home/mvhoang/CARLA_0.9.11/aeb_workspace}/environments/yolo310/bin/python scripts/train_yolo26n.py
```

Export ONNX:

```bash
${AEB_WORKSPACE_ROOT:-/home/mvhoang/CARLA_0.9.11/aeb_workspace}/environments/yolo310/bin/python scripts/export_yolo26n_onnx.py
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

- `report/chapters_v3/*.md`: frozen chapter source của report v3.
- `report/report_v3.md`: bản Markdown full đã khóa.
- `report/exports/aeb_report_v3.docx`: bản DOCX theo form cũ.
- `report/exports/aeb_report_v3.pdf`: bản PDF A4 để duyệt.

Để kiểm chứng khả năng build/export (không dùng để sửa đè report v3):

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/usr/bin/python3 report/build_report_v3.py
/usr/bin/python3 report/export_report_v3.py
```

Khi hoàn thiện báo cáo, link GitHub và link Google Drive video sẽ được đưa vào
phụ lục thay vì liệt kê toàn bộ đường dẫn local trong nội dung chính.
