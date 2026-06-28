# Staged Brake Validation - 2026-06-26

## Mục Tiêu

Thử thay phanh nhị phân:

```text
nguy hiểm -> brake = 1.0
```

bằng phanh nhiều tầng:

```text
nguy hiểm vừa -> brake thấp hơn
nguy hiểm cao -> brake mạnh hơn
khẩn cấp -> brake = 1.0
```

Mục tiêu dài hạn là giảm jerk và làm xe phanh giống hệ thống thật hơn.

## Lưu Ý Về Jerk Trong CARLA

Các giá trị jerk trong báo cáo này là **CARLA raw jerk**, tính từ gia tốc dọc raw
theo từng tick. Giá trị này có thể xuất hiện spike lớn do physics mô phỏng và do
brake command thay đổi trực tiếp. Vì vậy jerk ở đây dùng để so sánh tương đối
giữa binary/staged trong cùng điều kiện test, không phải jerk tuyệt đối của xe
thật.

## Code Thay Đổi

File chính:

- `control/brake.py`

Config trong `configs/sensors.yaml`:

```yaml
brake:
  brake_mode: staged
  staged_soft_brake: 0.55
  staged_medium_brake: 0.75
  staged_hard_brake: 0.90
  staged_emergency_brake: 1.0
  staged_hard_ttc_s: 1.10
  staged_emergency_ttc_s: 0.80
  staged_hard_margin_m: -2.0
  staged_emergency_margin_m: -5.0
  staged_emergency_distance_m: 18.0
```

Ý nghĩa:

- Nếu tình huống vừa nguy hiểm: phanh khoảng `0.75`.
- Nếu nguy hiểm hơn: phanh khoảng `0.90`.
- Nếu quá sát hoặc thiếu khoảng dừng nghiêm trọng: phanh `1.0`.

Binary baseline vẫn còn trong code. Có thể quay lại bằng:

```yaml
brake:
  brake_mode: binary
```

## Unit Test

```text
33/33 PASS
```

Test mới:

- Staged brake dùng lệnh phanh thấp hơn trong tình huống vừa nguy hiểm.
- Staged brake vẫn giữ full brake trong tình huống khẩn cấp.

## Lệnh Test CARLA

Subset nguy hiểm:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/fusion_limit_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id staged_brake_risk_subset_20260626_01 \
  --scenario short_gap_60_25 \
  --scenario short_gap_80_35 \
  --scenario short_gap_90_55 \
  --scenario braking_65_gap_28 \
  --scenario braking_80_gap_40 \
  --scenario moving_80_50_gap_35 \
  --scenario false_curve_adjacent_80
```

Full validation chuẩn:

```bash
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id staged_brake_validation_full_20260626_01
```

Full limit validation:

```bash
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/fusion_limit_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id staged_brake_limit_full_20260626_01
```

## Kết Quả

### Subset Nguy Hiểm

```text
7/7 PASS
```

| Scenario | Status | Min gap |
| --- | --- | ---: |
| short_gap_60_25 | PASS | 4.41 m |
| short_gap_80_35 | PASS | 1.48 m |
| short_gap_90_55 | PASS | 2.23 m |
| moving_80_50_gap_35 | PASS | 14.40 m |
| braking_65_gap_28 | PASS | 2.48 m |
| braking_80_gap_40 | PASS | 4.29 m |
| false_curve_adjacent_80 | PASS | - |

### Full Validation Chuẩn

```text
29/29 PASS
```

Log:

```text
logs/staged_brake_validation_full_20260626_01
```

Case đáng chú ý:

| Scenario | Status | Min gap |
| --- | --- | ---: |
| curve_ccrs_65 | PASS | 3.28 m |
| multi_two_leads_80 | PASS | 2.13 m |

### Full Limit Validation

```text
25/25 PASS
```

Log:

```text
logs/staged_brake_limit_full_20260626_01
```

Case đáng chú ý:

| Scenario | Status | Min gap |
| --- | --- | ---: |
| short_gap_80_35 | PASS | 1.48 m |
| short_gap_90_55 | PASS | 2.23 m |
| short_gap_90_65 | PASS | 4.47 m |
| false_curve_adjacent_70 | PASS | - |
| false_curve_adjacent_75 | PASS | - |
| false_curve_adjacent_80 | PASS | - |

## So Sánh Với Binary + Target Gate

Ghi chú: các giá trị jerk bên dưới là **CARLA raw jerk**.

Baseline binary + target gate:

- Validation chuẩn: `logs/fusion_aeb_binary_gate_full_20260626_01`
- Limit validation: `logs/fusion_limit_gate_full_20260626_01`

### Validation Chuẩn

Trên các case có phanh:

| Metric | Binary | Staged | Nhận xét |
| --- | ---: | ---: | --- |
| Min gap trung bình | 8.583 m | 8.039 m | Staged dừng sát hơn |
| Max decel trung bình | 11.135 | 11.288 | Gần như không cải thiện |
| Max jerk trung bình | 172.962 | 177.099 | Chưa giảm |

### Limit Validation

Trên các case có phanh:

| Metric | Binary | Staged | Nhận xét |
| --- | ---: | ---: | --- |
| Min gap trung bình | 7.141 m | 6.088 m | Staged dừng sát hơn |
| Max decel trung bình | 11.097 | 10.655 | Có giảm nhẹ |
| Max jerk trung bình | 163.115 | 177.210 | Chưa giảm |

Một số case staged làm min gap giảm khá rõ:

| Scenario | Binary gap | Staged gap |
| --- | ---: | ---: |
| multi_two_leads_80 | 6.384 m | 2.134 m |
| short_gap_90_55 | 6.603 m | 2.235 m |
| short_gap_90_65 | 7.574 m | 4.470 m |

## Nhận Xét

Staged brake v1 đã đạt mục tiêu an toàn tối thiểu:

```text
validation chuẩn: 29/29 PASS
limit validation: 25/25 PASS
```

Tuy nhiên staged v1 **chưa đạt mục tiêu giảm jerk một cách ổn định**. Một số
case jerk giảm, nhưng trung bình không giảm. Lý do có thể là:

- phanh nhẹ hơn ở đầu làm xe dừng muộn hơn,
- sau đó hệ thống phải tăng phanh mạnh hơn,
- gia tốc trong mô phỏng có nhiễu nên jerk cực đại không chỉ phụ thuộc vào giá
  trị `brake_cmd`.

## Kết Luận

Staged brake v1 là một bản chạy được và an toàn trên bộ test hiện tại, nhưng
chưa nên coi là nghiệm tối ưu.

Hướng tiếp theo nên là:

1. Giữ target gate vì đã xử lý lỗi phanh nhầm.
2. Làm PID hoặc staged có rate limit rõ ràng hơn.
3. Đặt thêm điều kiện chất lượng:
   - không collision,
   - min gap không quá sát,
   - max jerk phải giảm so với binary.

Nếu mục tiêu là báo cáo tiến độ, staged v1 có thể được trình bày như một thử
nghiệm trung gian: **an toàn vẫn pass, nhưng chưa cải thiện jerk đủ tốt**, từ đó
dẫn sang nhu cầu PID.
