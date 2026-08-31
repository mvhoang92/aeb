# 15. Quy Trình Tham Gia Và Giao Task

Tài liệu này dành cho người mới hoặc một công cụ AI khác nhảy vào dự án AEB
trên CARLA. Mục tiêu là giúp người/AI mới hiểu đủ nhanh để làm việc ngay, không
phụ thuộc vào lịch sử chat trước đó.

## 1. Nguyên Tắc Nguồn Sự Thật

Không dùng lịch sử chat làm nguồn chính. Khi có mâu thuẫn, ưu tiên theo thứ tự:

1. Code hiện tại trong repo.
2. File cấu hình trong `configs/`.
3. Tài liệu chính thức trong `docs/official/`.
4. Nhật ký thử nghiệm trong `docs/log/EXPERIMENT_LOG.md`.
5. Tài liệu research trong `docs/research/`.
6. Tài liệu cũ trong `docs/history/legacy_docs/` chỉ để tham khảo.

Nếu code và tài liệu khác nhau, phải kiểm tra code trước, sau đó cập nhật tài
liệu nếu thay đổi đã được xác nhận.

## 2. Đọc Nhanh Trong 15 Phút

Một người/AI mới nên đọc theo thứ tự này:

1. `README.md`: trạng thái nhanh, cách chạy, cấu trúc thư mục.
2. `docs/official/00_PROJECT_INTRODUCTION.md`: mục tiêu và phạm vi.
3. `docs/official/13_PROJECT_PROGRESS_REPORT.md`: đã làm, đang làm, sẽ làm.
4. `docs/official/10_CODE_STRUCTURE.md`: file nào phụ trách phần nào.
5. `docs/official/01_SYSTEM_ARCHITECTURE.md`: pipeline tổng thể.
6. `docs/official/03_RADAR_PROCESSING.md`: radar-only pipeline.
7. `docs/official/06_AEB_DECISION_AND_BRAKING.md`: TTC, stopping distance, phanh.
8. `docs/official/07_SCENARIOS_AND_VALIDATION.md`: scenario và log.
9. `docs/official/09_RUN_GUIDE.md`: lệnh chạy.
10. `docs/official/12_AI_WORKFLOW.md`: quy ước làm việc với AI.

Sau khi đọc, cần nắm được:

- Dự án hiện ưu tiên radar-only AEB trước.
- Fusion hiện mới là debug, chưa là nhánh quyết định phanh chính.
- Cấu hình sensor/scenario nằm trong `configs/`.
- Logic dùng chung không nên viết trực tiếp vào UI.

## 3. Trạng Thái Dự Án Hiện Tại

Tóm tắt kỹ thuật:

- Simulator: CARLA 0.9.11.
- Ego vehicle: `vehicle.tesla.model3`.
- Sensor:
  - Camera RGB sau kính lái.
  - Radar tại mũi xe.
- Nhánh ổn định nhất: radar-only AEB.
- Dải vận tốc mục tiêu hiện tại: 50-80 km/h.
- Pipeline radar-only:

```text
CARLA RadarMeasurement
  -> radar points trong hệ ego
  -> lọc range / độ cao / ground / predicted corridor
  -> clustering + tracking
  -> RadarObjectList
  -> chọn target
  -> TTC + stopping distance
  -> AEB state machine
  -> brake override
  -> stop latch để đo final gap
```

Các phần đang/dự kiến:

- Chạy validation radar-only đầy đủ và ghi evidence.
- Thu dataset camera từ CARLA ground truth.
- Train YOLO một class `car`.
- Nâng fusion từ debug sang `FusedTarget`.
- Nâng phanh binary sang PID hoặc brake profile.

## 4. Bản Đồ Module

### 4.1. UI

- `ui/camera_view.py`: test camera.
- `ui/radar_view.py`: radar bird-eye/debug.
- `ui/radar_aeb_view.py`: live radar-only AEB và scenario trực quan.
- `ui/yolo_view.py`: camera + YOLO bbox.
- `ui/fusion_view.py`: camera + YOLO + projected radar debug.
- `ui/manual_control_common.py`: helper dùng chung cho các app hai panel.

Quy tắc: UI chỉ nên gọi pipeline và vẽ kết quả. Không nhồi thuật toán AEB lớn
vào UI nếu có thể đặt ở `core/`, `perception/` hoặc `control/`.

### 4.2. Core

- `core/radar_aeb_pipeline.py`: pipeline radar-only chính.
- `core/radar_object.py`: object-level radar data.
- `core/target_selector.py`: chọn target AEB.
- `core/ground_truth_labels.py`: helper ground truth label cho dataset.

Quy tắc: logic dùng chung cho UI và batch nên đặt ở `core/`.

### 4.3. Perception

- `perception/radar/radar_object_tracker.py`: clustering, tracking, confirmation
  radar object.

Quy tắc: thuật toán xử lý cảm biến nên đặt ở `perception/`.

### 4.4. Control

- `control/brake.py`: TTC, stopping distance, AEB state machine, brake override.

Quy tắc: quyết định phanh và điều khiển phanh đặt ở `control/`. Không để code
spawn actor/scenario trong module này.

### 4.5. Scripts

- `scripts/run_radar_aeb_scenarios.py`: batch validation.
- `scripts/collect_yolo_dataset.py`: thu dataset.
- `scripts/check_yolo_dataset.py`: audit dataset trước khi train.
- `scripts/train_yolo26n.py`: train YOLO26n.
- `scripts/export_yolo26n_onnx.py`: export model sang ONNX.
- `scripts/visualize_sensor_coverage.py`: vẽ vùng phủ sensor.

Quy tắc: script là entry point để chạy việc, không nên chứa thuật toán dùng
chung nếu thuật toán đó còn được UI gọi lại.

### 4.6. Configs

- `configs/sensors.yaml`: ego, camera, radar, model, fusion, brake.
- `configs/scenarios/suites/radar_only_regression.yaml`: scenario validation/live demo.
- `configs/dataset_collection.yaml`: thu dataset.
- `configs/model_training.yaml`: train/evaluate/export YOLO.

Quy tắc: thông số sensor, threshold, scenario phải đọc từ config khi hợp lý.
Tránh hard-code nếu giá trị có thể cần tune.

## 5. Quy Trình Nhận Một Task

Trước khi sửa code, người/AI mới cần xác định:

- Mục tiêu của task là gì?
- Đây là task code, config, docs, test hay research?
- File nào liên quan?
- Có cần CARLA server đang bật không?
- Cần chạy unit test, smoke test hay batch scenario nào?
- Kết quả mong đợi là gì?
- Có phải cập nhật docs/log không?

Mẫu task tốt:

```text
Task: Giảm phanh nhầm radar-only khi xe đi qua vật thể làn bên.

Mục tiêu:
- Ego không phanh với target ở adjacent lane.
- Không làm hỏng CCRs cùng làn.

File liên quan:
- core/radar_aeb_pipeline.py
- perception/radar/radar_object_tracker.py
- configs/sensors.yaml
- configs/scenarios/suites/radar_only_regression.yaml

Test cần chạy:
- unit test
- adjacent_stationary_65
- ccrs_65
- clear_road_65

Docs cần cập nhật:
- docs/log/EXPERIMENT_LOG.md
- docs/official/03_RADAR_PROCESSING.md nếu logic được chốt
```

## 6. Quy Trình Sửa Code

1. Chạy `git status --short` để xem workspace có thay đổi không.
2. Đọc file liên quan trước khi sửa.
3. Tìm pattern hiện có bằng `rg`.
4. Sửa nhỏ, đúng phạm vi task.
5. Không revert/xóa thay đổi của người khác nếu chưa được yêu cầu.
6. Không đổi tên file/thư mục lớn nếu chưa có quyết định rõ ràng.
7. Chạy test phù hợp.
8. Cập nhật tài liệu nếu behavior hoặc command thay đổi.
9. Báo lại rõ file đã sửa, test đã chạy, phần còn cần người kiểm tra.

## 7. Quy Tắc Khi Nhiều Người Hoặc Nhiều AI Cùng Làm

- Mỗi task nên có phạm vi file rõ ràng.
- Nếu phải sửa chung một file, đọc diff hiện tại trước.
- Không format toàn bộ file nếu chỉ sửa vài dòng.
- Không refactor ngoài phạm vi task.
- Không tự ý đổi sensor position, radar range, threshold phanh hoặc scenario
  chính nếu task không yêu cầu.
- Nếu phát hiện thay đổi của người khác làm task không thể tiếp tục, ghi rõ:
  - file nào,
  - dòng/khối nào,
  - mâu thuẫn logic là gì,
  - đề xuất hợp nhất.

## 8. Quy Tắc Cập Nhật Tài Liệu

Chỉ cập nhật đúng nơi:

| Trường hợp | File cần cập nhật |
|---|---|
| Lệnh chạy mới/thay đổi command | `docs/official/09_RUN_GUIDE.md` |
| Thay đổi cấu trúc file/module | `docs/official/10_CODE_STRUCTURE.md` |
| Thay đổi sensor/config đã chốt | `docs/official/02_SENSOR_CONFIGURATION.md` |
| Thay đổi radar pipeline | `docs/official/03_RADAR_PROCESSING.md` |
| Thay đổi AEB/phanh | `docs/official/06_AEB_DECISION_AND_BRAKING.md` |
| Thay đổi scenario/evaluation | `docs/official/07_SCENARIOS_AND_VALIDATION.md` |
| Thay đổi dataset/train | `docs/official/08_DATASET_AND_TRAINING.md` |
| Lỗi, thử nghiệm, smoke test, kết quả mới | `docs/log/EXPERIMENT_LOG.md` |
| Research hoặc so sánh repo/cảm biến | `docs/research/` |
| Tiến độ tổng hợp | `docs/official/13_PROJECT_PROGRESS_REPORT.md` |

Không biến tài liệu chính thức thành nhật ký. Nhật ký nằm ở
`docs/log/EXPERIMENT_LOG.md`; tài liệu chính thức chỉ ghi kết luận/thiết kế đã
tương đối chốt.

## 9. Quy Ước UI Demo/Test

Khi làm UI demo có pygame, ưu tiên bố cục vừa màn Full HD theo chiều dọc. Preset
mặc định nên dùng khoảng `1600x900`.

Layout khuyến nghị:

```text
+---------------------------+---------------------------+
| Camera + YOLO/Fusion      |                           |
|                           | Radar bird-eye + path     |
+---------------------------+ target, TTC, brake info   |
| Manual / ego view         |                           |
|                           |                           |
+---------------------------+---------------------------+
```

- Cột trái khoảng 60% chiều ngang, chia hai hàng:
  - trên: camera sau kính lái, YOLO bbox, fusion target;
  - dưới: manual/chase view, HUD, ego vehicle, collision.
- Cột phải dùng toàn bộ chiều cao cho radar bird-eye, predicted path, object list
  và trạng thái AEB.
- Không dùng layout ba panel ngang cho demo chính vì dễ tràn màn và khó nhìn.
- Batch validation nên chạy không UI hoặc UI tối giản; layout ba vùng chủ yếu
  phục vụ demo, debug trực quan và quay video báo cáo.

Quay video evidence:

- Script hiện có: `scripts/record_scenario_videos.py`.
- Cách làm: chạy UI scenario trên Xvfb, quay bằng `ffmpeg`/NVENC, lưu video vào
  `$AEB_WORKSPACE_ROOT/runs/videos/scenario_videos/`.
- Batch số liệu và quay video nên tách nhau:
  - batch validation ưu tiên ổn định, log `.csv/.json/.md`;
  - video dùng để minh họa một vài scenario tiêu biểu trong báo cáo.
- Khi đổi layout UI, phải cập nhật `--screen-size`, `--capture-size` và preset
  cửa sổ của script quay video để khớp với UI mới.

## 9. Quy Tắc Test

### 9.1. Unit Test Mặc Định

Chạy sau khi sửa logic Python:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

### 9.2. Py Compile

Chạy cho file vừa sửa nếu muốn bắt lỗi syntax nhanh:

```bash
../venv/bin/python -m py_compile path/to/file.py
```

### 9.3. Smoke Test Live UI

Khi CARLA server đã bật:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python ui/radar_aeb_view.py \
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --control-mode physics \
  --scenario ccrs_60_demo_150 \
  --res 960x540 \
  --scenario-warmup-s 2.0 \
  --scenario-debug-interval-s 0.2
```

### 9.4. Batch Radar-Only

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --control-mode physics \
  --scenario clear_road_50 \
  --scenario ccrs_50 \
  --load-map
```

### 9.5. Test Theo Loại Thay Đổi

| Loại thay đổi | Test tối thiểu |
|---|---|
| Sửa `control/brake.py` | unit test + ít nhất một CCRs |
| Sửa radar pipeline | unit test + clear road + CCRs + adjacent lane |
| Sửa live UI | py_compile + chạy một scenario UI |
| Sửa scenario config | load YAML + chạy scenario liên quan |
| Sửa dataset collector | unit test helper + chạy collect nhỏ |
| Sửa train/model | unit test model + audit-only |
| Sửa docs | kiểm tra link/tên file/lệnh chạy |

## 10. Quy Tắc Với CARLA

- CARLA server thường chạy từ thư mục gốc:

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

- Không dùng `-opengl` trên máy hiện tại nếu không có lý do rõ ràng, vì từng làm
  pygame/manual control render lỗi.
- Nếu CARLA server tắt, các smoke test UI/batch sẽ fail hoặc treo.
- Với test cần cảm giác UI, người dùng cần tự nhìn và xác nhận.

## 11. Quy Tắc Với Data, Log Và Model

Không commit mặc định:

- `$AEB_WORKSPACE_ROOT/runs/`
- `$AEB_WORKSPACE_ROOT/datasets/`
- `$AEB_WORKSPACE_ROOT/training/`
- video/ảnh evidence nặng
- model `.pt`, `.onnx`, `.engine`

Nếu cần đưa model hoặc ảnh minh họa vào repo, phải ghi rõ lý do và cân nhắc dung
lượng.

## 12. Checklist Trước Khi Bàn Giao Task

Trước khi báo hoàn thành:

- [ ] Đã đọc đúng file liên quan.
- [ ] Không sửa lan man ngoài phạm vi.
- [ ] Không revert thay đổi người khác.
- [ ] Đã chạy test phù hợp hoặc ghi rõ vì sao chưa chạy.
- [ ] Đã cập nhật docs/log nếu behavior thay đổi.
- [ ] Đã nêu file sửa và ý nghĩa thay đổi.
- [ ] Đã nêu rủi ro còn lại hoặc phần cần người dùng kiểm tra bằng mắt.

Mẫu báo cáo bàn giao:

```text
Đã sửa:
- file A: ...
- file B: ...

Logic chính:
- ...

Đã kiểm tra:
- py_compile: PASS
- unit test: 28/28 PASS
- smoke scenario ...: PASS/không chạy được vì ...

Cần người dùng kiểm tra:
- cảm giác phanh/UI/final gap trong CARLA.
```

## 13. Prompt Mẫu Cho AI Khác

Khi giao task cho một AI khác, có thể dùng mẫu này:

```text
Bạn đang làm trong repo /home/mvhoang/CARLA_0.9.11/aeb.

Trước khi sửa, đọc:
- README.md
- docs/official/15_CONTRIBUTING_AND_TASK_WORKFLOW.md
- docs/official/10_CODE_STRUCTURE.md
- các file liên quan đến task.

Task:
<mô tả task>

Phạm vi:
- Được sửa: <file/thư mục>
- Không được sửa: <file/thư mục nếu có>

Kết quả mong muốn:
- <behavior/test/result>

Test cần chạy:
- <unit/smoke/batch>

Docs cần cập nhật:
- <file docs/log nếu cần>

Quy tắc:
- Không revert thay đổi người khác.
- Không refactor ngoài phạm vi.
- Nếu không chạy được CARLA/test, báo rõ lý do.
```

## 14. Các Sai Lầm Cần Tránh

- Tính AEB trực tiếp từ toàn bộ radar point mà bỏ qua object/tracking.
- Đưa logic phanh vào UI thay vì `control/` hoặc `core/`.
- Đổi sensor config mà không cập nhật tài liệu sensor.
- Sửa scenario nhưng không kiểm tra target spawn/gap/lateral.
- Thay đổi threshold phanh rồi không ghi lại kết quả test.
- Ghi kết luận nghiên cứu vào tài liệu chính thức khi chưa kiểm chứng.
- Đưa dataset/log/model nặng lên repo.

## 15. Mục Tiêu Của Quy Trình Này

Sau khi đọc file này, một người hoặc AI khác phải có thể:

- Hiểu dự án đang ở giai đoạn nào.
- Biết file nào cần đọc/sửa cho từng nhóm task.
- Biết cách chạy test tối thiểu.
- Biết tài liệu nào cần cập nhật.
- Làm việc cùng người/AI khác mà không phá thay đổi hiện có.

Nếu một task không thể mô tả rõ theo các mục trên, nên làm rõ task trước khi
sửa code.
