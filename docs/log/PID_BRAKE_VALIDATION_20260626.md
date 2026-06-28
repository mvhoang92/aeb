# PID Brake Validation - 2026-06-26

## Mục Tiêu

Chuyển bộ điều khiển phanh AEB từ `binary`/`staged` sang `pid` để phanh có mức
điều khiển liên tục hơn, vẫn giữ nguyên điều kiện an toàn:

- Không collision trong các kịch bản có nguy hiểm.
- Không phanh nhầm trong các kịch bản đường trống, xe làn bên, đường cong.
- Xe dừng lại sau khi AEB can thiệp để đo được khoảng cách cuối.
- Log đủ thông tin để so sánh với binary/staged: khoảng cách dừng, gia tốc âm,
  jerk và trạng thái AEB.

## Lưu Ý Về Jerk Trong CARLA

`maximum_abs_jerk_mps3` trong báo cáo này là **CARLA raw jerk**, được tính từ
gia tốc dọc raw theo từng tick. Con số này có thể có spike lớn khi brake command
thay đổi nhanh hoặc khi xe gần dừng, nên chỉ dùng để so sánh tương đối giữa các
mode phanh trong cùng môi trường test. Không nên hiểu đây là jerk tuyệt đối của
xe thật.

## Thay Đổi Code

- `control/brake.py`
  - Thêm `brake_mode: pid`.
  - Thêm các tham số PID: `pid_kp`, `pid_ki`, `pid_kd`, `pid_ttc_kp`,
    `pid_min_brake`, `pid_hold_brake`, `pid_max_brake`.
  - Thêm giới hạn tốc độ tăng/giảm phanh:
    `pid_brake_rise_rate_per_s`, `pid_brake_fall_rate_per_s`,
    `pid_emergency_rise_rate_per_s`.
  - Thêm điều kiện emergency dựa trên TTC, khoảng cách và distance margin.
  - Sửa `dt` để PID/rate limit dùng đúng chu kỳ điều khiển.
  - Đạo hàm PID chỉ dùng để tăng phanh khi rủi ro tăng, không dùng để nhả phanh
    khi xe chưa dừng.

- `configs/sensors.yaml`
  - Chuyển `brake.brake_mode` sang `pid`.
  - Giữ nguyên tham số `staged_*` để rollback hoặc so sánh.
  - PID v1 sau tune:
    - `pid_min_brake: 0.45`
    - `pid_hold_brake: 0.75`
    - `pid_brake_rise_rate_per_s: 10.0`
    - `pid_brake_fall_rate_per_s: 3.0`
    - `pid_emergency_distance_m: 18.0`
    - `pid_emergency_margin_m: -5.0`
    - `pid_emergency_ttc_s: 0.80`

- `tests/test_radar_aeb_logic.py`
  - Thêm test PID ramp phanh ở rủi ro vừa.
  - Thêm test PID lên full brake ở tình huống emergency.
  - Thêm test PID giữ phanh khi xe chưa dừng.

## Quy Trình Test

Chiến lược test không chạy full ngay từ đầu:

1. Chạy unit test để kiểm tra logic không lỗi.
2. Chạy subset các case đại diện:
   - short-gap 60/80/90 km/h.
   - moving lead 80/50 km/h.
   - lead vehicle phanh gấp.
   - false-positive trên đường cong có xe làn bên.
3. Nếu subset fail hoặc dừng quá sát thì tune PID.
4. Chạy full validation 29 case.
5. Chạy limit validation 25 case để tìm biên hoạt động.

## Kết Quả Unit Test

```text
36/36 PASS
```

## Subset Ban Đầu

Run:

```text
logs/pid_brake_risk_subset_20260626_01
```

Kết quả: `7/7 PASS`.

| Scenario | Kết Quả | Min Gap |
|---|---:|---:|
| short_gap_60_25 | PASS | 4.10 m |
| short_gap_80_35 | PASS | 1.48 m |
| short_gap_90_55 | PASS | 3.37 m |
| moving_80_50_gap_35 | PASS | 13.92 m |
| braking_65_gap_28 | PASS | 2.51 m |
| braking_80_gap_40 | PASS | 4.37 m |
| false_curve_adjacent_80 | PASS | -- |

Nhận xét: subset pass nhưng `short_gap_80_35` còn khá sát, cần xem thêm full
validation.

## Full Validation Lần 1

Run:

```text
logs/pid_brake_validation_full_20260626_01
```

Kết quả: `28/29 PASS`.

Case fail:

| Scenario | Lỗi | Min Gap |
|---|---|---:|
| multi_two_leads_80 | Không collision nhưng dừng quá sát, dưới ngưỡng 0.5 m | 0.05 m |

Nguyên nhân:

- PID bắt đầu phanh khi `distance_margin_m` vừa chạm 0.
- Lệnh phanh đầu chỉ khoảng 0.35.
- Thành phần đạo hàm âm làm phanh tụt khi sai số giảm nhẹ, trong khi xe vẫn
  chưa dừng.

## Tune PID

Các chỉnh sửa sau fail:

- `pid_min_brake`: 0.35 -> 0.45.
- `pid_brake_rise_rate_per_s`: 8.0 -> 10.0.
- `pid_brake_fall_rate_per_s`: 6.0 -> 3.0.
- Đạo hàm PID chỉ lấy phần dương để không tự kéo phanh xuống trong vùng nguy hiểm.

Retest riêng case fail:

```text
logs/pid_brake_multi_tune_20260626_01
```

Kết quả:

| Scenario | Trước Tune | Sau Tune |
|---|---:|---:|
| multi_two_leads_80 | FAIL, min gap 0.05 m | PASS, min gap 0.94 m |

## Full Validation Sau Tune

Run:

```text
logs/pid_brake_validation_full_20260626_02
```

Kết quả: `29/29 PASS`.

Các điểm chính:

- Không collision.
- Không false brake ở clear road, adjacent stationary, curve clear, curve
  adjacent.
- Case sát nhất: `multi_two_leads_80`, min gap 0.94 m.

## Limit Validation Sau Tune

Run:

```text
logs/pid_brake_limit_full_20260626_01
```

Kết quả: `25/25 PASS`.

Các điểm chính:

- Pass nhóm stationary lead từ 40 đến 100 km/h với gap cấu hình.
- Pass nhóm short-gap 60/80/90 km/h.
- Pass nhóm moving/braking target.
- Không phanh nhầm ở nhóm false-positive 90 km/h và đường cong 65-80 km/h.
- Case sát nhất trong limit: `short_gap_80_35`, min gap 1.48 m.

## So Sánh Binary, Staged Và PID

### Full Validation 29 Case

Ghi chú: các cột jerk là **CARLA raw jerk**, dùng để so sánh tương đối.

| Mode | Pass | Avg Min Gap | Min Gap | Avg Max Decel | Avg Max Jerk |
|---|---:|---:|---:|---:|---:|
| Binary + target gate | 29/29 | 8.58 m | 4.09 m | 11.14 m/s2 | 172.96 m/s3 |
| Staged v1 | 29/29 | 8.04 m | 2.13 m | 11.29 m/s2 | 177.10 m/s3 |
| PID v1 tuned | 29/29 | 7.81 m | 0.94 m | 11.06 m/s2 | 169.22 m/s3 |

### Limit Validation 25 Case

Ghi chú: các cột jerk là **CARLA raw jerk**, dùng để so sánh tương đối.

| Mode | Pass | Avg Min Gap | Min Gap | Avg Max Decel | Avg Max Jerk |
|---|---:|---:|---:|---:|---:|
| Binary + target gate | 25/25 | 7.14 m | 1.48 m | 11.10 m/s2 | 163.12 m/s3 |
| Staged v1 | 25/25 | 6.09 m | 1.48 m | 10.66 m/s2 | 177.21 m/s3 |
| PID v1 tuned | 25/25 | 5.94 m | 1.48 m | 10.87 m/s2 | 181.95 m/s3 |

## Kết Luận

PID v1 tuned đã đạt yêu cầu an toàn trên bộ test hiện tại:

- Full validation: `29/29 PASS`.
- Limit validation: `25/25 PASS`.
- Không collision.
- Không false-positive ở các case đã test.

Tuy nhiên PID v1 chưa phải nghiệm tối ưu về độ êm:

- Ở full validation, jerk trung bình thấp hơn binary một chút.
- Ở limit validation, jerk trung bình cao hơn binary/staged.
- Khoảng cách dừng trung bình thấp hơn binary, tức là PID đang phanh muộn/mềm hơn
  nhưng vẫn đủ an toàn trong bộ test hiện tại.

Hướng tiếp theo nếu muốn tối ưu:

1. Tune PID v2 theo mục tiêu kép: min gap >= 1.0-2.0 m và giảm jerk.
2. Thử tăng `stopping_distance_offset_m` riêng cho PID lên 1.5-2.0 m.
3. Thêm metric comfort rõ hơn: jerk trung bình, jerk cực đại, thời gian từ first
   brake đến xe dừng.
4. Chạy thêm scenario giới hạn ở 80-100 km/h với gap nhỏ hơn để xác định biên
   fail thật sự.
