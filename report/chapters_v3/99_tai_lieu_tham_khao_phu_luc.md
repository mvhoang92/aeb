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

# Phụ Lục B. Khả Năng Tái Lập Kết Quả

Mã nguồn, cấu hình kịch bản, cấu hình cảm biến và hướng dẫn tái lập được quản
lý cùng dự án. Bộ dữ liệu, video và nhật ký đầy đủ có dung lượng lớn được cung
cấp qua liên kết tại Phụ lục A. Bảng dưới đây nêu các thành phần cần thiết để
kiểm tra lại các kết quả trong báo cáo; cú pháp lệnh chi tiết được duy trì trong
README để tránh phụ lục mang tính nhật ký vận hành.

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
| `ui/fusion_view.py` | Chiếu điểm radar sang ảnh, ghép với bounding box YOLO và hiển thị fusion. |
| `ui/aeb_demo_view.py` | Giao diện minh họa cuối cùng 3 màn. |
| `scripts/run_fusion_aeb_scenarios.py` | Chạy batch scenario cho AEB/fusion và sinh log. |
| `scripts/record_scenario_videos.py` | Quay video minh họa scenario. |
| `scripts/plot_brake_profile.py` | Sinh biểu đồ phanh, vận tốc, khoảng cách, TTC và dải trạng thái AEB. |

# Phụ Lục C. Ghi Chú Khi Chuyển Sang DOCX

- Các dòng bắt đầu bằng `Hình x.y:` nên được chuyển thành Caption hình trong
  Word để tạo danh mục hình tự động.
- Các dòng bắt đầu bằng `Bảng x.y:` nên được chuyển thành Caption bảng.
- Link Google Drive ở Phụ lục A chứa chung video, log chi tiết và biểu đồ đánh
  giá. Khi chuyển sang Word, có thể giữ một link chung này để tránh bảng phụ lục
  quá dài.
- Các thư mục dataset, training run và video có dung lượng lớn không nên nhúng
  trực tiếp vào repository nếu không cần thiết; chỉ cần giữ mã nguồn, cấu hình,
  log tóm tắt và link minh chứng.

# Phụ Lục D. Bằng Chứng Tái Lập Và So Sánh (Bản V2)

Phụ lục này liệt kê các artifact đã được đưa vào Git để tái lập các kết quả bổ
sung trong bản v2. Bảng summary và raw log nén nằm dưới `docs/log/repeatability/`;
hash được lưu trong `docs/log/repeatability/artifacts/SHA256SUMS.txt`.

| Nội dung | Vị trí |
|---|---|
| Full-suite fusion x5 | `docs/log/repeatability/paper_v3_fusion_full66_repeat5_noreload/` |
| Full-suite radar-only x5 | `docs/log/repeatability/paper_v3_radar_only_full66_repeat5_noreload/` |
| Negative regression x5 | `docs/log/repeatability/negative_regression_repeat5_comparison.md` |
| Ma trận nhầm lẫn + latency | `docs/log/repeatability/confusion_matrix_precision_recall.md` |
| False-positive vật lý | `docs/log/repeatability/physical_false_positive_v2_and_limitation_comparison.md` |
| Ablation bộ điều khiển | `docs/log/repeatability/controller_ablation_binary_vs_staged_pid.md` |
| Độ nhạy hold time | `docs/log/repeatability/fusion_hold_time_sensitivity.md` |
| Phân tích `cut_out_late_65_35` | `docs/log/cut_out_late_65_35_failure_analysis.md` |
| Bộ kịch bản false-positive | `configs/scenarios/suites/fusion_physical_false_positive_v2.yaml` |
| Bộ kịch bản limitation | `configs/scenarios/suites/fusion_nonvehicle_hazard_limitation.yaml` |
| Config ablation binary | `configs/sensors_binary.yaml` |
| Config hold-time sweep | `configs/sensors_fusion_hold_{0p10,0p35,0p70,1p00}.yaml` |

Các lệnh chạy chi tiết được ghi trong
`docs/log/PAPER_V3_REPRODUCTION_NOTES.md`. Khi cần kiểm tra lại, khôi phục raw
log bằng cách giải nén các file `*.tar.gz` trong `docs/log/repeatability/artifacts/`
vào `logs/`, sau đó chạy:

```bash
sha256sum -c docs/log/repeatability/artifacts/SHA256SUMS.txt
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/summarize_repeatability.py \
  logs/<run-id> --out docs/log/repeatability/<run-id>
```

# Phụ Lục E. Final GPU Campaign Và Hold-Out (Bản V3)

Protocol được khóa trong `docs/log/PAPER_V4_EVALUATION_PROTOCOL.md`; algorithm
commit/tag là `3be8ae4`/`safe-fallback-eval-v1`. Final campaign chạy bằng master
runner, restart CARLA sau mỗi named scenario:

```bash
/home/mvhoang/CARLA_0.9.11/venv/bin/python \
  scripts/run_v4_final_pipeline.py \
  --phase all \
  --campaign-id paper_v4_gpu_final_locked_20260825
```

| Artifact | Vị trí |
|---|---|
| Final narrative evidence | `docs/log/repeatability/paper_v4_gpu_final/FINAL_GPU_EVIDENCE.md` |
| Core confusion + Wilson CI | `docs/log/repeatability/paper_v4_gpu_final/core_confusion_metrics.csv` |
| Suite/hold-out metrics | `docs/log/repeatability/paper_v4_gpu_final/section_metrics.csv` |
| Named-scenario consistency | `docs/log/repeatability/paper_v4_gpu_final/scenario_consistency.csv` |
| Paired outcomes | `docs/log/repeatability/paper_v4_gpu_final/paired_outcomes.csv` |
| Ablation/sensitivity | `ablation_metrics.csv`, `sensitivity_metrics.csv` cùng thư mục |
| CUDA timing | `gpu_latency.csv` cùng thư mục |
| Reproducible analysis | `scripts/analyze_v4_final.py` |
| Raw logs + manifest | `docs/log/repeatability/artifacts/paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz` |
| Archive hash | file `.sha256` bên cạnh archive |

Sinh lại toàn bộ bảng và hình:

```bash
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/analyze_v4_final.py
```

CPU campaign trước đó chỉ là diagnostic evidence xử lý OOM và không được dùng
làm headline. Final metrics của bản v3 chỉ lấy từ campaign CUDA đã khóa.
