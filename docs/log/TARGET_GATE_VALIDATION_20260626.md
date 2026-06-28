# Target Gate Validation - 2026-06-26

## Mục Tiêu

Giảm lỗi phanh nhầm trong tình huống:

```text
đường cong + xe đứng yên ở làn bên + ego chạy 70-80 km/h
```

Không dùng `CARLA map` hoặc `lane_id` làm input quyết định phanh để tránh
"hack" ground truth của simulator.

## Ý Tưởng Sửa

Trước khi cho target radar đi vào AEB, thêm một lớp kiểm tra ổn định:

- Target mới xuất hiện phải được chọn liên tục đủ số frame mới được phanh.
- Nếu tình huống quá khẩn cấp thì vẫn cho phanh ngay:
  - target rất gần,
  - hoặc khoảng cách hiện tại nhỏ hơn nhiều so với khoảng cách cần để dừng.

Nói đơn giản:

```text
Target bình thường: cần thấy ổn định vài frame rồi mới phanh.
Target quá sát/quá nguy hiểm: phanh ngay.
```

Mục tiêu là chặn các target "lóe lên" ngắn hạn do xe làn bên trên đường cong,
nhưng không làm trễ các tình huống nguy hiểm thật.

## Code Thay Đổi

File chính:

- `core/radar_aeb_pipeline.py`

Config:

```yaml
target_gate:
  enabled: true
  selected_confirm_frames: 5
  immediate_brake_distance_m: 22.0
  immediate_distance_margin_m: -4.0
```

Unit test:

- `tests/test_radar_aeb_logic.py`
  - Target chưa đủ ổn định bị chặn.
  - Target quá gần vẫn được cho phanh ngay.

## Lệnh Test

Unit test:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Sweep lại các case fail cũ:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/fusion_limit_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id fusion_limit_curve_adjacent_gate_20260626_01 \
  --scenario false_curve_adjacent_65 \
  --scenario false_curve_adjacent_70 \
  --scenario false_curve_adjacent_75 \
  --scenario false_curve_adjacent_80
```

Full validation chuẩn:

```bash
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id fusion_aeb_binary_gate_full_20260626_01
```

Full limit validation:

```bash
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/fusion_limit_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id fusion_limit_gate_full_20260626_01
```

## Kết Quả

### Unit Test

```text
31/31 PASS
```

### Sweep Case Fail Cũ

Log:

```text
logs/fusion_limit_curve_adjacent_gate_20260626_01
```

| Scenario | Trước khi sửa | Sau khi sửa |
| --- | --- | --- |
| false_curve_adjacent_65 | PASS | PASS |
| false_curve_adjacent_70 | FAIL - phanh nhầm | PASS |
| false_curve_adjacent_75 | FAIL - phanh nhầm + collision | PASS |
| false_curve_adjacent_80 | FAIL - phanh nhầm + collision | PASS |

### Full Validation Chuẩn

Log:

```text
logs/fusion_aeb_binary_gate_full_20260626_01
```

Kết quả:

```text
29/29 PASS
```

Điểm cần chú ý:

Ghi chú: `Max jerk` là **CARLA raw jerk**, dùng để so sánh tương đối trong mô
phỏng, không phải jerk tuyệt đối của xe thật.

| Scenario | Status | Brake | Collision | Min gap | Max jerk |
| --- | --- | ---: | ---: | ---: | ---: |
| curve_ccrs_65 | PASS | Yes | No | 4.089 m | 225.194 |

Case đường cong cùng làn vẫn phanh được sau khi thêm target gate.

### Full Limit Validation

Log:

```text
logs/fusion_limit_gate_full_20260626_01
```

Kết quả:

```text
25/25 PASS
```

Một số case quan trọng:

Ghi chú: `Max jerk` là **CARLA raw jerk**, dùng để so sánh tương đối trong mô
phỏng, không phải jerk tuyệt đối của xe thật.

| Scenario | Status | Brake | Collision | Min gap | Max jerk |
| --- | --- | ---: | ---: | ---: | ---: |
| short_gap_80_35 | PASS | Yes | No | 1.478 m | 108.208 |
| false_curve_adjacent_70 | PASS | No | No | - | 8.914 |
| false_curve_adjacent_75 | PASS | No | No | - | 8.746 |
| false_curve_adjacent_80 | PASS | No | No | - | 9.900 |

## Nhận Xét

Target gate đã xử lý được lỗi phanh nhầm trên đường cong tốc độ cao mà không làm
hỏng các case nguy hiểm trong bộ test hiện tại.

Điểm cần theo dõi tiếp:

- `short_gap_80_35` vẫn là case sát biên vì min gap chỉ còn khoảng `1.48 m`.
- Target gate có thể làm phanh muộn hơn trong một số cut-in cực gấp, nên cần giữ
  các test cut-in khi phát triển tiếp.
- Jerk vẫn cao vì phanh vẫn là binary full-brake; PID/multi-stage brake là bước
  tiếp theo hợp lý sau khi target selection đã sạch hơn.

## Kết Luận

Sau target gate:

```text
validation chuẩn: 29/29 PASS
limit validation: 25/25 PASS
```

Đây là mốc tốt để bắt đầu làm phanh PID hoặc multi-stage brake.
