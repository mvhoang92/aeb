# Báo Cáo Tối Ưu Radar-Only AEB - 2026-06-25

## Mục Tiêu

Kiểm tra lại radar-only AEB trên CARLA server đang chạy, đọc log tick-level và
xác định vì sao demo vẫn có cảm giác chưa mượt. Trọng tâm lần này là radar-only,
chưa đưa YOLO/fusion vào quyết định phanh.

## Môi Trường Chạy

- CARLA: 0.9.11.
- Map scenario: `Town04`.
- Client Python: `../venv/bin/python` Python 3.7.
- Scenario config: `configs/radar_only_validation.yaml`.
- Sensor/AEB config chính: `configs/sensors.yaml`.
- Control mode: `physics`.
- Fixed delta: `0.05 s`, tương đương 20 Hz.

Lúc chạy lần đầu CARLA server đang ở `Town03`, script báo cần `Town04`. Đã chạy
lại với `--load-map` để chuyển map.

## Lệnh Baseline Nhỏ

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id radar_only_opt_baseline_20260625 \
  --scenario clear_road_65 \
  --scenario ccrs_60_demo_150 \
  --scenario adjacent_stationary_65 \
  --scenario curve_clear_65 \
  --scenario curve_adjacent_stationary_65
```

Kết quả: 5/5 PASS.

## Lệnh Baseline Mở Rộng

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --run-id radar_only_opt_full_baseline_20260625 \
  --scenario clear_road_50 \
  --scenario clear_road_65 \
  --scenario clear_road_80 \
  --scenario ccrs_50 \
  --scenario ccrs_65 \
  --scenario ccrs_80 \
  --scenario ccrm_50_20 \
  --scenario ccrm_65_30 \
  --scenario ccrm_80_50 \
  --scenario adjacent_stationary_65 \
  --scenario curve_clear_65 \
  --scenario curve_adjacent_stationary_65 \
  --scenario curve_ccrs_65
```

Kết quả: 13/13 PASS.

Ghi chú: `Max jerk` là **CARLA raw jerk**, tính từ gia tốc dọc raw theo từng tick.
Metric này dùng để so sánh tương đối trong mô phỏng, không phải jerk tuyệt đối
của xe thật.

| Scenario | Status | Brake | Collision | Brake gap (m) | Min gap (m) | Max decel | Max jerk |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| clear_road_50 | PASS | False | False | | | 0.251 | 37.342 |
| clear_road_65 | PASS | False | False | | | 0.318 | 24.394 |
| clear_road_80 | PASS | False | False | | | 0.525 | 7.426 |
| ccrs_50 | PASS | True | False | 20.089 | 6.920 | 10.070 | 108.632 |
| ccrs_65 | PASS | True | False | 26.054 | 5.874 | 12.679 | 251.396 |
| ccrs_80 | PASS | True | False | 33.396 | 5.275 | 10.412 | 134.252 |
| ccrm_50_20 | PASS | True | False | 13.146 | 8.261 | 10.533 | 132.756 |
| ccrm_65_30 | PASS | True | False | 18.704 | 12.182 | 12.191 | 241.816 |
| ccrm_80_50 | PASS | True | False | 21.577 | 16.431 | 11.129 | 133.016 |
| adjacent_stationary_65 | PASS | False | False | | | 0.325 | 6.488 |
| curve_clear_65 | PASS | False | False | | | 0.348 | 29.842 |
| curve_adjacent_stationary_65 | PASS | False | False | | | 0.351 | 12.170 |
| curve_ccrs_65 | PASS | True | False | 25.517 | 5.899 | 11.410 | 228.040 |

## Phát Hiện Chính

1. Radar-only đang ổn về mặt safety trong batch hiện tại:
   - Không collision ở các tình huống car-to-car.
   - Không phanh nhầm ở clear road.
   - Không phanh nhầm với xe làn bên trong các case đã chạy.
   - Target radar khớp hazard actor 100% trong các case có target thẳng.

2. Cảm giác chưa mượt chủ yếu đến từ điều khiển phanh binary:
   - Khi vào trạng thái `BRAKE`, hệ thống command `brake=1.0`.
   - Max deceleration thường khoảng 10-12.7 m/s².
   - Max jerk trong các case phanh có thể vượt 100-250 m/s³.
   - Đây là đặc trưng của full-brake dạng bật/tắt, không phải lỗi target
     selection chính.

3. Log cũ có lệch 1 tick ở frame đầu phanh:
   - Frame đầu `aeb_state=BRAKE` đôi khi ghi `brake_cmd=0.0`.
   - Nguyên nhân: log đọc `ego.get_control()` ngay sau khi command, CARLA phản
     ánh control ở tick sau.
   - Đã sửa để log ghi command AEB dựa trên `system.decision.brake`.

## Kiểm Tra Sau Sửa Log

Lệnh:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --run-id radar_only_opt_after_logfix_20260625 \
  --scenario clear_road_65 \
  --scenario ccrs_60_demo_150 \
  --scenario adjacent_stationary_65 \
  --scenario curve_ccrs_65
```

Kết quả: 4/4 PASS.

Frame đầu phanh của `ccrs_60_demo_150` sau sửa:

| elapsed_s | speed_kph | bumper_gap_m | state | reason | brake_cmd | throttle_cmd | ttc_s |
| ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |
| 7.40 | 60.039 | 24.6305 | BRAKE | ttc_below_brake_threshold | 1.0 | 0.0 | 1.472 |

## Thử Giảm Full Brake Xuống 0.75

Đã tạo config tạm `/tmp/aeb_sensors_brake075.yaml` với:

```yaml
brake:
  full_brake: 0.75
```

Kết quả vẫn PASS nhưng không nên đưa vào config chính:

| Scenario | Min gap full=1.0 (m) | Min gap full=0.75 (m) | Nhận xét |
| --- | ---: | ---: | --- |
| ccrs_50 | 6.920 | 4.391 | Dừng sát hơn |
| ccrs_65 | 5.874 | 2.669 | Dừng sát hơn rõ |
| ccrs_80 | 5.275 | 1.265 | Biên an toàn thấp |
| curve_ccrs_65 | 5.899 | 1.714 | Biên an toàn thấp |

Một số case có jerk không giảm ổn định, thậm chí tăng. Vì vậy giảm hằng số
`full_brake` không phải hướng tối ưu tốt.

## Kết Luận

Radar-only hiện tại có thể dùng làm baseline kỹ thuật:

- Target selection đủ ổn cho các scenario đã chạy.
- Không thấy false brake trong clear road/adjacent/curve batch.
- Xe ego dừng an toàn trong các case cần phanh.

Nhưng radar-only chưa mượt vì bộ chấp hành phanh vẫn là binary full-brake. Nếu
muốn demo mượt hơn và gần xe thật hơn, bước tiếp theo nên là nâng cấp `control`
từ binary brake sang phanh nhiều tầng hoặc PID.

## Đề Xuất Bước Tiếp Theo

1. Giữ radar target selection hiện tại làm baseline.
2. Thêm controller phanh nhiều tầng:
   - `WARNING`: chỉ cảnh báo.
   - `SOFT_BRAKE`: phanh nhẹ khi margin bắt đầu thấp.
   - `MEDIUM_BRAKE`: phanh vừa khi TTC/required distance nguy hiểm.
   - `FULL_BRAKE`: chỉ dùng khi thật sự sắp va chạm.
3. Sau đó thay phần command bằng PID:
   - Input: desired deceleration hoặc desired speed.
   - Output: brake command 0-1.
   - Có rate limit để tránh jerk lớn.
4. Chạy lại chính các run trong báo cáo này để so sánh:
   - Collision phải vẫn bằng 0.
   - Min gap không quá thấp.
   - Max jerk phải giảm rõ.
   - Không tăng false brake.

## File Log Liên Quan

- `logs/radar_only_opt_baseline_20260625/`
- `logs/radar_only_opt_full_baseline_20260625/`
- `logs/radar_only_opt_after_logfix_20260625/`
- `logs/radar_only_opt_brake075_20260625/`
