# Final Evidence Pack - AEB Staged PID

## Tổng Quan

- Thuật toán phanh: `staged_pid` trong `configs/sensors.yaml`.
- Perception/fusion: camera YOLO ONNX + radar object pipeline.
- Scenario config: `configs/scenarios/suites/system_limit_extended_sweep.yaml`.
- Log final: `/home/mvhoang/CARLA_0.9.11/aeb/logs/final_evidence_staged_pid_20260628`.
- Video final: `/home/mvhoang/CARLA_0.9.11/aeb/outputs/scenario_videos/final_evidence_videos_20260628_internal`.

## Kết Quả Batch

| Tổng case | PASS | FAIL | Missing | Pass rate |
|---:|---:|---:|---:|---:|
| 66 | 63 | 3 | 0 | 95.45% |

## Case Fail / Giới Hạn Hệ Thống

| Scenario | Collision | Min gap | Lý do |
|---|---:|---:|---|
| `ccrb_95_gap_20` | True | 0.0134 m | expected_collision=False actual=True; collision |
| `ccrb_110_gap_20` | True | 0.0806 m | expected_collision=False actual=True; collision |
| `cutin_100_60_gap_25` | True | 0.4763 m | expected_collision=False actual=True; collision |

## Artifact Chính

- Summary CSV: `/home/mvhoang/CARLA_0.9.11/aeb/logs/final_evidence_staged_pid_20260628/summary.csv`
- Summary JSON: `/home/mvhoang/CARLA_0.9.11/aeb/logs/final_evidence_staged_pid_20260628/summary.json`
- Aggregate: `/home/mvhoang/CARLA_0.9.11/aeb/logs/final_evidence_staged_pid_20260628/aggregate_summary.json`
- Heatmap Markdown: `/home/mvhoang/CARLA_0.9.11/aeb/logs/final_evidence_staged_pid_20260628/system_limit_heatmap.md`
- Biểu đồ phanh: `/home/mvhoang/CARLA_0.9.11/aeb/logs/final_evidence_staged_pid_20260628/plots`
- Video report: `/home/mvhoang/CARLA_0.9.11/aeb/outputs/scenario_videos/final_evidence_videos_20260628_internal/video_report.md`
- Video thumbnails kiểm tra không đen: `/home/mvhoang/CARLA_0.9.11/aeb/outputs/scenario_videos/final_evidence_videos_20260628_internal/thumbnails`

## Video Demo

| Scenario | Ý nghĩa | File |
|---|---|---|
| `clear_road_50` | Đường trống 50 km/h, không phanh nhầm | `/home/mvhoang/CARLA_0.9.11/aeb/outputs/scenario_videos/final_evidence_videos_20260628_internal/clear_road_50.mp4` |
| `ccrs_80_gap_30` | Xe đứng yên phía trước, hệ thống phanh thành công | `/home/mvhoang/CARLA_0.9.11/aeb/outputs/scenario_videos/final_evidence_videos_20260628_internal/ccrs_80_gap_30.mp4` |
| `ccrb_95_gap_20` | Xe trước phanh gấp, case giới hạn/collision | `/home/mvhoang/CARLA_0.9.11/aeb/outputs/scenario_videos/final_evidence_videos_20260628_internal/ccrb_95_gap_20.mp4` |
| `cutin_80_50_gap_25` | Cut-in pass | `/home/mvhoang/CARLA_0.9.11/aeb/outputs/scenario_videos/final_evidence_videos_20260628_internal/cutin_80_50_gap_25.mp4` |
| `cutin_100_60_gap_25` | Cut-in fail giới hạn/collision | `/home/mvhoang/CARLA_0.9.11/aeb/outputs/scenario_videos/final_evidence_videos_20260628_internal/cutin_100_60_gap_25.mp4` |

## Ghi Chú

- Video được ghi trực tiếp từ frame Pygame bằng `--record-video-path`, không dùng x11grab nên tránh lỗi video đen.
- Các thumbnail ở giây 1/5/9 đã được trích ra để kiểm tra hình ảnh.
- Jerk trong log là CARLA raw jerk, dùng để so sánh tương đối trong mô phỏng.
