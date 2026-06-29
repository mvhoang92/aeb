# Tài Liệu Tham Khảo

1. CARLA Simulator, trang chính thức: https://carla.org/
2. CARLA documentation: https://carla.readthedocs.io/
3. CARLA 0.9.11 release: https://github.com/carla-simulator/carla/releases/tag/0.9.11
4. CARLA sensors reference: https://carla.readthedocs.io/en/0.9.11/ref_sensors/
5. Dosovitskiy et al., CARLA: An Open Urban Driving Simulator: https://arxiv.org/abs/1711.03938
6. Autoware Universe documentation: https://autowarefoundation.github.io/autoware.universe/
7. openpilot GitHub repository: https://github.com/commaai/openpilot
8. ApolloAuto GitHub repository: https://github.com/ApolloAuto/apollo
9. Ultralytics YOLO documentation: https://docs.ultralytics.com/
10. Euro NCAP protocols: https://www.euroncap.com/safety-assist/
11. Euro NCAP AEB Car-to-Car Test Protocol v4.2.
12. NHTSA Automatic Emergency Braking final rule: https://www.nhtsa.gov/press-releases/nhtsa-fmvss-127-automatic-emergency-braking-reduce-crashes
13. ISO 15623, Transport information and control systems - Forward vehicle collision warning systems.
14. GitHub repository của đồ án: https://github.com/mvhoang92/aeb
15. Toyota Safety Sense: https://www.toyota.com/safety-sense/
16. Honda Sensing - Collision Mitigation Braking System: https://automobiles.honda.com/sensing
17. Subaru EyeSight Driver Assist Technology: https://www.subaru.com/eyesight.html
18. Mobileye ADAS: https://www.mobileye.com/solutions/adas/
19. ZF Smart Camera 4.8: https://www.zf.com/products/en/cars/products_64256.html
20. Bosch Mobility radar sensor: https://www.bosch-mobility.com/en/solutions/sensors/radar-sensor/
21. Continental long-range radar information: https://www.continental-automotive.com/en/components/radars/long-range-radars/
22. CARLA releases page: https://github.com/carla-simulator/carla/releases
23. CARLA download page: https://carla.org/download/

# Phụ Lục A. Liên Kết Mã Nguồn Và Kết Quả Minh Họa

Phụ lục này gom các liên kết bên ngoài dùng khi chuyển báo cáo sang bản `.docx`
cuối cùng. Các video, log chi tiết và biểu đồ dung lượng lớn không nên đưa trực
tiếp vào repository, mà được lưu trong một thư mục Google Drive chung.

| Nội dung | Liên kết/Ghi chú |
|---|---|
| Mã nguồn đồ án | https://github.com/mvhoang92/aeb |
| Video, log và biểu đồ đánh giá | https://drive.google.com/drive/folders/12cPKJKFeiSwI8vx67RviL3VIx_lmOstq?usp=drive_link |
| File báo cáo `.docx` sau khi chuyển từ Markdown | Cập nhật đường dẫn trong bản nộp cuối |

# Phụ Lục B. Các Thư Mục Minh Chứng Chính Trong Dự Án

Các thư mục dưới đây là nơi lưu dữ liệu minh chứng đã dùng để viết Chương 4.
Khi kiểm tra lại kết quả, nên ưu tiên các thư mục cuối cùng thay vì các log thử
nghiệm trung gian.

| Thành phần | Đường dẫn trong dự án | Nội dung |
|---|---|---|
| Log đánh giá staged PID cuối cùng | `logs/final_evidence_staged_pid_20260628/` | File CSV từng scenario, `summary.csv`, `aggregate_summary.json`, heatmap và biểu đồ phanh. |
| Biểu đồ phanh PID | `logs/final_evidence_staged_pid_20260628/plots/` | Biểu đồ lực phanh, vận tốc, khoảng cách, TTC và dải màu trạng thái AEB. |
| Log so sánh PID/staged PID trước đó | `logs/staged_pid_validation_full_20260627_02/` | Dữ liệu trung gian dùng để so sánh quá trình tune phanh. |
| Video minh họa cuối cùng | `outputs/scenario_videos/final_evidence_videos_20260628_internal/` | Video màn hình 3 vùng và ảnh đại diện một số scenario tiêu biểu. |
| Ảnh và sơ đồ dùng trong báo cáo | `report/assets/` | Hình minh họa AEB, CARLA, radar, fusion, quỹ đạo dự đoán. |
| Bộ dữ liệu v7 same-lane cho YOLO | `dataset_v7_same_lane/` | Ảnh, nhãn và file `dataset.yaml` dùng fine-tune YOLO26n. |
| Kết quả huấn luyện YOLO | `training_runs/detect/yolo26n_aeb_20260619_011359/` | Trọng số, biểu đồ huấn luyện và kết quả đánh giá mô hình. |

# Phụ Lục C. Lệnh Chạy Chính

## C.1. Chạy CARLA server

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Lệnh trên dùng GPU NVIDIA offload và quality Low. Trong quá trình thử nghiệm,
cờ `-opengl` đã được bỏ vì có thể làm cửa sổ Pygame/manual control hiển thị
không ổn định trên máy dùng Ubuntu.

## C.2. Chạy giao diện khởi chạy

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
python3 laucher.py
```

Launcher dùng để chọn nhóm kịch bản, scenario cụ thể, chế độ điều khiển, loại
phanh và mở nhanh giao diện minh họa hoặc chạy test.

## C.3. Chạy minh họa cuối cùng bằng dòng lệnh

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

Giao diện minh họa cuối cùng gồm ba vùng: camera + YOLO/fusion, góc nhìn manual
control và bird-eye radar. Giao diện này dùng để quan sát trực quan trạng thái
AEB, target được chọn, lực phanh và các điểm radar trong thời gian chạy.

## C.4. Kiểm tra dataset YOLO

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
.venv_yolo310/bin/python scripts/check_yolo_dataset.py
```

## C.5. Fine-tune YOLO26n

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
.venv_yolo310/bin/python scripts/train_yolo26n.py
```

## C.6. Export YOLO26n sang ONNX

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
.venv_yolo310/bin/python scripts/export_yolo26n_onnx.py
```

## C.7. Tạo lại biểu đồ phanh PID

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
python3 scripts/plot_brake_profile.py \
  --run-dir logs/final_evidence_staged_pid_20260628 \
  --output-dir logs/final_evidence_staged_pid_20260628/plots
```

## C.8. Build lại báo cáo Markdown tổng

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb/report
python3 build_report.py
```

Lệnh này ghép các file trong `report/chapters/` thành `report/report.md`.

# Phụ Lục D. Các File Cấu Hình Và Mã Nguồn Quan Trọng

| File/Thư mục | Vai trò |
|---|---|
| `configs/sensors.yaml` | Cấu hình vị trí, độ phân giải, FOV và tần số của camera/radar. |
| `configs/model_training.yaml` | Cấu hình fine-tune và export YOLO26n. |
| `configs/dataset_collection_v7_same_lane.yaml` | Cấu hình thu bộ dữ liệu v7 same-lane cho YOLO26n. |
| `configs/scenarios/car_to_car/` | Các nhóm kịch bản theo tình huống: clear road, CCRs, CCRm, CCRb, cut-in, cut-out, curve, multi-actor. |
| `configs/scenarios/suites/system_limit_extended_sweep.yaml` | Bộ kịch bản stress test dùng tìm giới hạn hệ thống. |
| `control/brake.py` | Các thuật toán phanh: binary, PID v1/v2 và staged PID. |
| `core/radar_aeb_pipeline.py` | Pipeline AEB từ radar/object/fusion tới trạng thái phanh. |
| `perception/radar/` | Các module xử lý radar, gom cụm, theo dõi và chọn mục tiêu. |
| `perception/fusion/` | Hợp nhất camera-radar và tạo mục tiêu hợp nhất. |
| `ui/aeb_demo_view.py` | Giao diện minh họa cuối cùng 3 màn. |
| `scripts/run_fusion_aeb_scenarios.py` | Chạy batch scenario cho AEB/fusion và sinh log. |
| `scripts/record_scenario_videos.py` | Quay video minh họa scenario. |
| `scripts/plot_brake_profile.py` | Sinh biểu đồ phanh, vận tốc, khoảng cách, TTC và dải trạng thái AEB. |

# Phụ Lục E. Ghi Chú Khi Chuyển Sang DOCX

- Các dòng bắt đầu bằng `Hình x.y:` nên được chuyển thành Caption hình trong
  Word để tạo danh mục hình tự động.
- Các dòng bắt đầu bằng `Bảng x.y:` nên được chuyển thành Caption bảng.
- Link Google Drive ở Phụ lục A chứa chung video, log chi tiết và biểu đồ đánh
  giá. Khi chuyển sang Word, có thể giữ một link chung này để tránh bảng phụ lục
  quá dài.
- Các thư mục dataset, training run và video có dung lượng lớn không nên nhúng
  trực tiếp vào repository nếu không cần thiết; chỉ cần giữ mã nguồn, cấu hình,
  log tóm tắt và link minh chứng.
