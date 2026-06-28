# PID V2 Comfort Validation - 2026-06-27

## Mục Tiêu

PID v1 đã pass safety nhưng vẫn còn mục tiêu cải thiện:

- tăng khoảng cách dừng cuối, tránh các case dừng quá sát;
- giảm jerk trung bình;
- giữ pass rate trên full validation và limit validation;
- không làm tăng phanh nhầm ở các case cut-out, adjacent lane và đường cong.

## Ý Tưởng PID V2

PID v2 không chỉ tăng/giảm gain. Thay đổi chính là cho xe **phanh sớm hơn nhưng
nhẹ hơn**:

- `pid_target_margin_m`: tạo khoảng dư trước ngưỡng dừng bắt buộc.
- `pid_target_margin_max_lateral_m`: chỉ cho phanh sớm nếu target còn gần tâm
  hành lang dự kiến.
- Nếu target đã lệch ra mép hành lang, ví dụ xe đang cut-out, hệ thống không dùng
  phần phanh sớm comfort nữa, tránh phanh nhầm.

Nói ngắn gọn:

```text
PID v1: chờ gần thiếu khoảng cách rồi phanh.
PID v2: nếu target còn trong hành lang, phanh sớm nhẹ hơn để dừng xa và êm hơn.
```

## Cách Hiểu Metric Jerk Trong CARLA

Các bảng trong báo cáo này dùng `maximum_abs_jerk_mps3`, được tính từ gia tốc dọc
raw của CARLA theo từng tick:

```text
jerk = delta(longitudinal_acceleration) / delta_time
```

Metric này **không nên hiểu là jerk tuyệt đối của xe thật**. Trong mô phỏng hiện
tại, CARLA có thể tạo spike lớn khi bắt đầu phanh, khi brake command thay đổi
nhanh hoặc khi xe vừa dừng. Ngoài đời, hệ thống phanh, lốp, treo, ABS/ESC và ECU
sẽ làm trễ/lọc phản ứng này.

Vì vậy trong phạm vi dự án:

- jerk raw của CARLA được dùng chủ yếu để **so sánh tương đối** giữa các thuật
  toán trong cùng điều kiện test;
- không dùng giá trị này để kết luận trực tiếp rằng xe thật có jerk đúng bằng
  các con số trong bảng;
- khi viết báo cáo, các bảng có jerk nên ghi rõ đây là `CARLA raw jerk`;
- hướng nâng cấp sau là lọc gia tốc, tính jerk p95/RMS và mô phỏng actuator phanh.

## Config Chính

Trong `configs/sensors.yaml`:

```yaml
brake:
  brake_mode: pid_v2_comfort
  pid_kp: 0.12
  pid_ki: 0.01
  pid_kd: 0.0
  pid_ttc_kp: 0.12
  pid_min_brake: 0.25
  pid_hold_brake: 0.75
  pid_max_brake: 1.0
  pid_target_margin_m: 4.0
  pid_target_margin_max_lateral_m: 0.95
  pid_brake_rise_rate_per_s: 3.0
  pid_brake_fall_rate_per_s: 1.5
  pid_emergency_rise_rate_per_s: 12.0
  pid_emergency_distance_m: 16.0
  pid_emergency_margin_m: -5.0
  pid_emergency_ttc_s: 0.80
```

## Các Lần Tune Quan Trọng

### PID V2 Thử Nghiệm Ban Đầu

- Tăng `pid_target_margin_m` để phanh sớm hơn.
- Kết quả subset pass nhưng jerk tăng, chưa đạt mục tiêu comfort.

### Tune Quá Mềm

- Giảm emergency quá nhiều và giảm lực phanh tối đa.
- Kết quả fail ở các case biên như `short_gap_80_35` hoặc `short_gap_90_55`.
- Kết luận: ở short-gap 80-90 km/h vẫn cần khả năng phanh mạnh.

### Lateral Gate

- Vấn đề phát sinh: phanh sớm làm fail `cut_out_65_35` vì xe trước đang rời làn.
- Sửa bằng `pid_target_margin_max_lateral_m`.
- Nếu target lệch khỏi vùng lateral cho phép, PID v2 không dùng ngưỡng phanh sớm.
- Sau khi chạy lại tuần tự, không chạy song song trên cùng CARLA server:
  - `cut_out_65_35`: PASS, không phanh nhầm.
  - `cut_out_late_65_35`: PASS, vẫn phanh.
  - `short_gap_80_35`: PASS.
  - `braking_80_gap_40`: PASS.

## Lưu Ý Về Quy Trình Test

Không chạy hai batch scenario song song trên cùng một CARLA server. Hai runner sẽ
cùng spawn/điều khiển world và làm kết quả nhiễu. Một lần targeted test bị fail
giả do lỗi quy trình này, sau đó đã chạy lại tuần tự và pass.

## Kết Quả Unit Test

```text
39/39 PASS
```

Các test mới:

- PID target margin có thể kích hoạt phanh sớm.
- PID target margin bị chặn nếu target lateral lệch quá ngưỡng.

## Targeted Test Sau Lateral Gate

Run:

```text
logs/pid_v2_lateral_gate_cutout_seq_20260627_01
logs/pid_v2_lateral_gate_risk_seq_20260627_01
```

Kết quả:

| Scenario | Yêu Cầu | Kết Quả |
|---|---|---|
| cut_out_65_35 | Không phanh nhầm | PASS |
| cut_out_late_65_35 | Phải phanh | PASS |
| short_gap_80_35 | Không collision | PASS |
| braking_80_gap_40 | Không collision | PASS |

## Full Validation

Run:

```text
logs/pid_v2_comfort_validation_full_20260627_01
```

Kết quả: `29/29 PASS`.

Điểm đáng chú ý:

- Không collision.
- Không phanh nhầm ở clear road, adjacent stationary, curve clear, curve
  adjacent.
- `cut_out_65_35`: PASS, không phanh nhầm.
- `multi_two_leads_80`: PASS, min gap 2.12 m.
- Case sát nhất: `curve_ccrs_65`, min gap 1.33 m.

## Limit Validation

Run:

```text
logs/pid_v2_comfort_limit_full_20260627_01
```

Kết quả: `25/25 PASS`.

Điểm đáng chú ý:

- Pass nhóm operating range 40-100 km/h.
- Pass nhóm short-gap 60/80/90 km/h.
- Pass nhóm moving/braking target.
- Không phanh nhầm ở clear/adjacent/curve false-positive.
- Case sát nhất: `short_gap_80_35`, min gap 1.48 m.

## So Sánh PID V1 Và PID V2

### Full Validation 29 Case

Ghi chú: `Avg Max Jerk` và `Max Jerk` là **CARLA raw jerk**, dùng để so sánh
tương đối giữa PID v1 và PID v2 trong cùng bộ test.

| Mode | Pass | Avg Min Gap | Min Gap | Avg Max Decel | Avg Max Jerk | Max Jerk |
|---|---:|---:|---:|---:|---:|---:|
| PID v1 | 29/29 | 7.81 m | 0.95 m | 11.06 m/s2 | 169.22 m/s3 | 253.81 m/s3 |
| PID v2 comfort | 29/29 | 9.05 m | 1.33 m | 10.35 m/s2 | 148.56 m/s3 | 247.22 m/s3 |

### Limit Validation 25 Case

Ghi chú: `Avg Max Jerk` và `Max Jerk` là **CARLA raw jerk**, dùng để so sánh
tương đối giữa PID v1 và PID v2 trong cùng bộ test.

| Mode | Pass | Avg Min Gap | Min Gap | Avg Max Decel | Avg Max Jerk | Max Jerk |
|---|---:|---:|---:|---:|---:|---:|
| PID v1 | 25/25 | 5.94 m | 1.48 m | 10.87 m/s2 | 181.95 m/s3 | 278.33 m/s3 |
| PID v2 comfort | 25/25 | 6.57 m | 1.48 m | 10.47 m/s2 | 146.60 m/s3 | 239.52 m/s3 |

## Kết Luận

PID v2 comfort tốt hơn PID v1 theo đúng mục tiêu:

- Full validation vẫn `29/29 PASS`.
- Limit validation vẫn `25/25 PASS`.
- Avg min gap tăng.
- Avg max decel giảm.
- Avg max jerk giảm rõ rệt.
- Không làm tăng phanh nhầm nhờ lateral gate cho phần phanh sớm.

PID v2 comfort có thể dùng làm bản PID chính hiện tại. Bước tiếp theo là thiết kế
`staged PID`, tức là chia risk level thành nhiều tầng rồi dùng PID điều khiển lực
phanh trong từng tầng.
