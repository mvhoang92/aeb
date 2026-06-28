# Staged PID Validation - 2026-06-27

## Mục Tiêu

Kiểm tra bản `staged_pid`: chia rủi ro AEB thành nhiều tầng nhưng vẫn dùng PID
để điều khiển lực phanh trong từng tầng.

Ý tưởng:

```text
soft risk      -> PID trong khung phanh nhẹ
medium risk    -> PID trong khung phanh vừa
hard risk      -> PID trong khung phanh mạnh
emergency risk -> cho phép phanh tối đa
```

Mục tiêu kỳ vọng:

- giữ pass rate như `pid_v2_comfort`;
- tránh phanh nhầm ở cut-out/adjacent/curve;
- tăng khoảng cách dừng ở các case sát biên;
- nếu có thể, không làm CARLA raw jerk tăng quá nhiều.

## Config Chính

Trong `configs/sensors.yaml`:

```yaml
brake:
  brake_mode: staged_pid
  staged_soft_brake: 0.55
  staged_medium_brake: 0.75
  staged_hard_brake: 0.90
  staged_emergency_brake: 1.0
  staged_hard_ttc_s: 1.10
  staged_emergency_ttc_s: 0.80
  staged_hard_margin_m: -2.0
  staged_emergency_margin_m: -5.0
  staged_emergency_distance_m: 18.0
  pid_kp: 0.12
  pid_ki: 0.01
  pid_kd: 0.0
  pid_ttc_kp: 0.12
  pid_min_brake: 0.25
  pid_target_margin_m: 4.0
  pid_target_margin_max_lateral_m: 0.95
```

`staged_pid` kế thừa lateral gate của PID v2 comfort: chỉ phanh sớm nếu target còn
gần tâm hành lang dự kiến. Nếu target lệch ra ngoài ngưỡng lateral, hệ thống
không dùng phần phanh sớm comfort.

## Unit Test

Lệnh:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m unittest discover -s tests
```

Kết quả:

```text
42/42 PASS
```

Các test mới kiểm tra:

- soft stage không vượt quá `staged_soft_brake`;
- hard stage cho phép lực phanh mạnh hơn soft/medium;
- lateral gate của PID v2 vẫn hoạt động trong `staged_pid`.

## Targeted Test

Lưu ý: các run `_01` ban đầu bị thay thế bởi run `_02` sau khi phát hiện runner
cho ego chạy trong `settle_ticks` trước thời điểm bắt đầu log. Runner đã được sửa
để warm-up sensor khi xe đứng yên, sau đó mới reset state phanh/PID và bắt đầu
scenario.

### Cut-Out Và Case Nguy Hiểm

Lệnh:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id staged_pid_targeted_radar_20260627_02 \
  --scenario cut_out_65_35 \
  --scenario cut_out_late_65_35
```

Kết quả:

| Scenario | Kỳ vọng | Kết quả | Min gap |
| --- | --- | --- | ---: |
| `cut_out_65_35` | Không phanh nhầm | PASS, không phanh | -- |
| `cut_out_late_65_35` | Có phanh | PASS, không collision | 14.35 m |

Lệnh limit targeted:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/fusion_limit_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id staged_pid_targeted_limit_20260627_02 \
  --scenario short_gap_80_35 \
  --scenario braking_80_gap_40
```

Kết quả:

| Scenario | Kỳ vọng | Kết quả | Min gap |
| --- | --- | --- | ---: |
| `short_gap_80_35` | Có phanh, không collision | PASS | 1.79 m |
| `braking_80_gap_40` | Có phanh, không collision | PASS | 6.61 m |

## Full Validation

Lệnh:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id staged_pid_validation_full_20260627_02
```

Kết quả:

- PASS: `29/29`.
- Không collision.
- Không phanh nhầm ở clear road, adjacent lane, curve clear và cut-out sớm.
- Min gap nhỏ nhất: `4.07 m`.
- Log: `logs/staged_pid_validation_full_20260627_02`.

## Limit Validation

Lệnh:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/fusion_limit_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id staged_pid_limit_full_20260627_02
```

Kết quả:

- PASS: `25/25`.
- Không collision.
- Không phanh nhầm ở false-positive set.
- Min gap nhỏ nhất: `1.94 m`.
- Log: `logs/staged_pid_limit_full_20260627_02`.

## Kết Quả Tổng Hợp

Ghi chú: `Avg Max Jerk` và `Max Jerk` là **CARLA raw jerk**, chỉ dùng để so sánh
tương đối trong cùng môi trường mô phỏng.

### Full Validation

Các giá trị jerk/decel trung bình chỉ tính trên các scenario có phanh.

| Pass | Avg Min Gap | Min Gap | Avg Max Decel | Max Decel | Avg Max Jerk | Max Jerk |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 29/29 | 10.93 m | 4.07 m | 10.80 m/s2 | 12.79 m/s2 | 168.38 m/s3 | 253.66 m/s3 |

### Limit Validation

Các giá trị jerk/decel trung bình chỉ tính trên các scenario có phanh.

| Pass | Avg Min Gap | Min Gap | Avg Max Decel | Max Decel | Avg Max Jerk | Max Jerk |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 25/25 | 7.32 m | 1.94 m | 10.75 m/s2 | 12.48 m/s2 | 167.19 m/s3 | 247.39 m/s3 |

## Nhận Xét

Staged PID đạt mục tiêu an toàn:

- full validation pass toàn bộ;
- limit validation pass toàn bộ;
- cut-out sớm không bị phanh nhầm;
- cut-out muộn vẫn phanh;
- các case sát biên trong limit set vẫn giữ khoảng cách dừng tối thiểu trên
  ngưỡng pass 0.5 m.

Nhược điểm hiện tại:

- `staged_pid` đang thiên về an toàn/dừng xa hơn là comfort.
- Chưa so sánh công bằng lại với `pid_v2_comfort` sau khi sửa runner warm-up.
  Các bảng PID v2 cũ dùng runner trước khi sửa nên chỉ nên xem là tham khảo.

Kết luận tạm thời:

- `staged_pid` pass toàn bộ bộ test hiện tại sau khi sửa runner warm-up.
- Nếu ưu tiên demo “phanh nhiều nấc giống thực tế”, có thể dùng `staged_pid`.
- Bước tiếp theo nên viết script so sánh nhiều brake mode trên cùng runner đã
  sửa để có bảng công bằng giữa `binary`, `staged`, `pid_v2_comfort` và
  `staged_pid`.
- Nếu muốn tăng comfort, có thể tune giảm độ gắt của stage:
  - giảm `staged_soft_brake`/`staged_medium_brake`;
  - lùi ngưỡng emergency;
  - hoặc để stage chỉ giới hạn trần, không ép sàn phanh quá cao ở medium/hard.
