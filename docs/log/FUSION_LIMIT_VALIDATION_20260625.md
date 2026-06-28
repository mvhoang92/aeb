# Limit Validation Cho Fusion-AEB Binary - 2026-06-25

## Mục Tiêu

Tạo bộ test stress/limit để tìm biên hoạt động của hệ thống hiện tại trước khi
nâng cấp phanh PID hoặc multi-stage brake.

Khác với bộ validation ổn định, bộ này cố tình thêm các tình huống khó:

- tốc độ cao hơn dải mục tiêu,
- khoảng cách ban đầu ngắn,
- xe trước phanh gấp ở gap nhỏ,
- xe làn bên trên đường cong để kiểm tra phanh nhầm,
- log thêm `maximum_deceleration_mps2` và `maximum_abs_jerk_mps3` để sau này so
  sánh với PID.

## File Và Lệnh Chạy

Config mới:

```text
configs/fusion_limit_validation.yaml
```

Full batch đầu tiên:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/fusion_limit_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id fusion_limit_binary_20260625_01
```

Sweep bổ sung cho case đường cong + xe làn bên:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/fusion_limit_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id fusion_limit_curve_adjacent_sweep_20260625_01 \
  --scenario false_curve_adjacent_65 \
  --scenario false_curve_adjacent_70 \
  --scenario false_curve_adjacent_75 \
  --scenario false_curve_adjacent_80
```

Log:

```text
logs/fusion_limit_binary_20260625_01
logs/fusion_limit_curve_adjacent_sweep_20260625_01
```

## Tiêu Chí Đánh Giá

- Case nguy hiểm phải phanh và không collision.
- Case không nguy hiểm không được phanh nhầm.
- `minimum_bumper_gap_m` phải lớn hơn `min_stop_gap_m` nếu scenario có đặt.
- Lane-follow không vượt `max_lane_offset_m`.
- `maximum_deceleration_mps2` và `maximum_abs_jerk_mps3` được ghi để đánh giá
  độ gắt của phanh, chưa dùng làm điều kiện fail chính.
- `maximum_abs_jerk_mps3` là **CARLA raw jerk**, dùng để so sánh tương đối giữa
  các thuật toán/cấu hình trong cùng mô phỏng, không phải jerk tuyệt đối của xe
  thật.

## Kết Quả Full Batch Đầu Tiên

Full batch đầu tiên có 22 scenario:

- PASS: 21
- FAIL: 1
- Fail duy nhất: `false_curve_adjacent_80`

| Scenario | Nhóm | Status | Brake | Collision | First brake (s) | Min gap (m) | Max decel | Max jerk |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| limit_ccrs_40_gap_40 | CCRs operating | PASS | Yes | No | 2.00 | 7.11 | 9.56 | 144.17 |
| limit_ccrs_50_gap_45 | CCRs operating | PASS | Yes | No | 1.65 | 6.68 | 11.07 | 141.60 |
| limit_ccrs_60_gap_55 | CCRs operating | PASS | Yes | No | 1.70 | 6.35 | 10.33 | 206.40 |
| limit_ccrs_70_gap_65 | CCRs operating | PASS | Yes | No | 1.75 | 5.53 | 11.90 | 237.84 |
| limit_ccrs_80_gap_75 | CCRs operating | PASS | Yes | No | 1.75 | 4.95 | 10.48 | 141.73 |
| limit_ccrs_90_gap_90 | CCRs operating | PASS | Yes | No | 1.80 | 8.15 | 11.35 | 226.92 |
| limit_ccrs_100_gap_105 | CCRs stress | PASS | Yes | No | 1.85 | 11.00 | 11.31 | 140.15 |
| short_gap_60_25 | Short gap | PASS | Yes | No | 0.05 | 4.89 | 9.93 | 127.41 |
| short_gap_60_30 | Short gap | PASS | Yes | No | 0.15 | 7.49 | 12.56 | 249.07 |
| short_gap_80_35 | Short gap | PASS | Yes | No | 0.05 | 1.48 | 10.39 | 108.21 |
| short_gap_80_45 | Short gap | PASS | Yes | No | 0.25 | 6.25 | 10.04 | 135.31 |
| short_gap_90_55 | Short gap | PASS | Yes | No | 0.30 | 6.60 | 12.76 | 253.08 |
| short_gap_90_65 | Short gap | PASS | Yes | No | 0.70 | 7.57 | 13.32 | 264.20 |
| moving_80_50_gap_35 | Moving lead | PASS | Yes | No | 1.85 | 13.66 | 13.07 | 215.07 |
| moving_90_60_gap_45 | Moving lead | PASS | Yes | No | 2.70 | 16.07 | 11.24 | 73.85 |
| braking_65_gap_28 | Braking lead | PASS | Yes | No | 2.70 | 2.51 | 10.45 | 146.92 |
| braking_80_gap_40 | Braking lead | PASS | Yes | No | 2.85 | 4.38 | 11.00 | 218.82 |
| braking_90_gap_55 | Braking lead | PASS | Yes | No | 3.15 | 6.89 | 11.34 | 119.16 |
| false_clear_90 | False positive | PASS | No | No | - | - | 1.30 | 9.79 |
| false_adjacent_90 | False positive | PASS | No | No | - | - | 2.11 | 18.35 |
| false_curve_clear_90 | False positive | PASS | No | No | - | - | 0.94 | 8.99 |
| false_curve_adjacent_80 | False positive curve | FAIL | Yes | Yes | 0.60 | - | 17.19 | 338.60 |

## Sweep Đường Cong + Xe Làn Bên

Sau fail ở `false_curve_adjacent_80`, đã thêm sweep 65/70/75/80 km/h để tìm ngưỡng.

| Scenario | Ego speed | Expected | Result | First brake | Collision | Max lane offset | Max jerk | Nhận xét |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| false_curve_adjacent_65 | 65 km/h | Không phanh | PASS | - | No | trong giới hạn | 12.17 | Ổn |
| false_curve_adjacent_70 | 70 km/h | Không phanh | FAIL | 0.60 s | No | trong giới hạn | 86.13 | Phanh nhầm |
| false_curve_adjacent_75 | 75 km/h | Không phanh | FAIL | 0.60 s | Yes | 3.38 m | 593.46 | Phanh nhầm và collision |
| false_curve_adjacent_80 | 80 km/h | Không phanh | FAIL | 0.60 s | Yes | 3.34 m | 617.88 | Phanh nhầm và collision |

Chi tiết tại thời điểm phanh đầu tiên:

- 70 km/h: target làn bên được fusion xác nhận, `reason=distance_and_ttc_brake|fusion_confirmed`.
- 75-80 km/h: hiện tượng tương tự, sau đó ego lệch khỏi lane và collision.

## Nhận Xét Kỹ Thuật

### Điểm Mạnh Hiện Tại

- Cùng làn, xe đứng yên: pass từ 40 đến 100 km/h nếu gap đủ lớn.
- Short-gap cùng làn: vẫn pass trong các case đã thử, nhưng `short_gap_80_35`
  chỉ còn `1.48 m`, nên đây gần biên hơn các case khác.
- Xe trước phanh gấp: pass ở 65/80/90 km/h với gap đã chọn.
- Clear road 90 km/h và adjacent straight 90 km/h không phanh nhầm.

### Điểm Yếu Hiện Tại

Điểm yếu rõ nhất là:

```text
đường cong + xe đứng yên làn bên + tốc độ >= 70 km/h
```

Nguyên nhân gần nhất theo log:

- radar target nằm trong hành lang nguy hiểm theo predicted path hiện tại,
- target radar chiếu vào bbox YOLO nên fusion xác nhận,
- hệ thống cho BRAKE dù scenario kỳ vọng không phanh,
- ở 75-80 km/h, ego lane-follow lệch nhiều và collision.

Nói cách khác, lỗi không nằm ở YOLO phát hiện sai; lỗi là target association/lane
gating trên đường cong chưa đủ chặt cho xe làn bên.

### Jerk

Binary brake tạo jerk lớn rõ rệt:

- nhiều case phanh có jerk khoảng `100-260 m/s^3`,
- case lỗi đường cong 75-80 km/h có jerk vượt `590 m/s^3`.

Điều này củng cố hướng làm PID/multi-stage brake sau này. Tuy nhiên, trước khi
PID, cần xử lý false-positive trên đường cong, vì PID chỉ làm phanh mượt hơn chứ
không tự sửa quyết định target sai.

## Dải Hoạt Động Tạm Thời

Dựa trên lần test này:

- Dải tốt cho scenario cùng làn, rõ ràng: `50-80 km/h`, có thể mở rộng đến
  `90-100 km/h` nếu gap đủ và target trong radar range.
- Dải ổn cho false-positive đường cong + xe làn bên: đến khoảng `65 km/h`.
- Từ `70 km/h` trở lên ở đường cong có xe làn bên, thuật toán hiện tại có nguy
  cơ phanh nhầm.

Do đó, khi báo cáo nên nói:

```text
Hệ thống hiện tại hoạt động tốt trong các kịch bản cùng làn rõ ràng ở 50-80 km/h.
Biên yếu hiện tại là các tình huống đường cong tốc độ cao có vật thể ở làn bên,
do target radar có thể bị đưa vào hành lang nguy hiểm và được camera xác nhận.
```

## Việc Nên Làm Tiếp

1. Cải thiện target association trên đường cong:
   - siết `distance_to_predicted_path`,
   - dùng lane waypoint của target/cluster khi có thể,
   - kiểm tra lateral offset theo quỹ đạo cong thay vì theo trục radar thẳng.

2. Thêm log fusion chi tiết hơn:
   - số bbox YOLO,
   - pixel chiếu target radar,
   - bbox nào match,
   - lane id/waypoint gần target radar.

3. Sau khi giảm false-positive, mới nâng phanh:
   - multi-stage brake,
   - PID brake,
   - giới hạn jerk hoặc rate limit brake command.

4. Chạy lại cùng bộ `fusion_limit_validation.yaml` để so sánh:
   - binary hiện tại,
   - binary sau sửa target gating,
   - PID/multi-stage sau này.
