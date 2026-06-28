# Test Binary Brake Với Fusion Camera-Radar - 2026-06-25

## Mục Tiêu

Kiểm tra bước tiếp theo sau radar-only: dùng camera YOLO để xác nhận target radar
trước khi cho binary AEB can thiệp phanh.

Trong lần test này, fusion chưa thay thế radar. Radar vẫn là cảm biến chính để
tính khoảng cách, vận tốc tương đối, TTC và stopping distance. Camera YOLO đóng
vai trò confirmation gate:

- Nếu radar chọn target nguy hiểm và target đó chiếu vào bbox YOLO `car`, lệnh
  `BRAKE` được cho qua.
- Nếu radar báo nguy hiểm nhưng target không được YOLO xác nhận, lệnh phanh bị
  chặn ở tầng fusion.

## Thay Đổi Code

File mới:

- `scripts/run_fusion_aeb_scenarios.py`

File được chỉnh nhỏ để tái sử dụng runner scenario:

- `scripts/run_radar_aeb_scenarios.py`
  - Thêm hook `_make_system()` để runner radar-only có thể được kế thừa.
  - Giữ nguyên hành vi radar-only mặc định.

## Môi Trường Test

- CARLA client/server: `0.9.11`
- Map: `Town04`
- Mode mô phỏng: synchronous mode
- `fixed_delta_seconds`: `0.05 s`, tương đương 20 FPS mô phỏng
- Control mode: `physics`
- Sensor config: `configs/sensors.yaml`
- Scenario config: `configs/radar_only_validation.yaml`
- Model YOLO runtime: ONNX theo config hiện tại

## Lệnh Chạy

Kiểm tra cú pháp:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m py_compile \
  scripts/run_radar_aeb_scenarios.py \
  scripts/run_fusion_aeb_scenarios.py
```

Unit test:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Smoke batch nhỏ:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id fusion_aeb_binary_smoke_20260625_01 \
  --scenario clear_road_65 \
  --scenario ccrs_60_demo_150 \
  --scenario adjacent_stationary_65
```

Full validation:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --load-map \
  --run-id fusion_aeb_binary_full_20260625_01
```

## Tiêu Chí Pass

- Scenario nguy hiểm phải có phanh AEB.
- Scenario không nguy hiểm không được phanh nhầm.
- Không collision nếu scenario kỳ vọng không collision.
- Ego vẫn giữ được lane trong các scenario yêu cầu lane-follow.
- Với các scenario có target cụ thể, actor được chọn để phanh phải đúng với
  kỳ vọng trong config.

## Kết Quả Tổng Quan

Log full validation:

```text
logs/fusion_aeb_binary_full_20260625_01
```

Kết quả:

- Tổng scenario: 29
- PASS: 29
- FAIL: 0
- Collision: 0
- False brake ở clear/adjacent/curve clear: 0
- Unit test: 29/29 PASS

## Bảng Kết Quả Full Validation

| Scenario | Kỳ vọng phanh | Kết quả phanh | Collision | First brake (s) | Min gap (m) | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| clear_road_50 | No | No | No | - | - | PASS |
| clear_road_65 | No | No | No | - | - | PASS |
| clear_road_80 | No | No | No | - | - | PASS |
| ccrs_50 | Yes | Yes | No | 1.60 | 6.98 | PASS |
| ccrs_60_gap_200 | Yes | Yes | No | 10.40 | 7.69 | PASS |
| ccrs_60_demo_150 | Yes | Yes | No | 7.40 | 7.70 | PASS |
| ccrs_65 | Yes | Yes | No | 1.70 | 5.88 | PASS |
| ccrs_80 | Yes | Yes | No | 1.70 | 5.28 | PASS |
| ccrm_50_20 | Yes | Yes | No | 3.05 | 8.26 | PASS |
| ccrm_65_30 | Yes | Yes | No | 3.05 | 12.17 | PASS |
| ccrm_80_50 | Yes | Yes | No | 3.75 | 16.43 | PASS |
| ccrb_50_to_0 | Yes | Yes | No | 2.85 | 5.98 | PASS |
| ccrb_65_to_0 | Yes | Yes | No | 3.10 | 4.43 | PASS |
| ccrb_80_to_0 | Yes | Yes | No | 3.15 | 6.35 | PASS |
| adjacent_stationary_50 | No | No | No | - | - | PASS |
| adjacent_stationary_65 | No | No | No | - | - | PASS |
| adjacent_stationary_80 | No | No | No | - | - | PASS |
| non_closing_60_80 | No | No | No | - | 31.12 | PASS |
| curve_clear_65 | No | No | No | - | - | PASS |
| curve_clear_80 | No | No | No | - | - | PASS |
| curve_adjacent_stationary_65 | No | No | No | - | - | PASS |
| curve_ccrs_65 | Yes | Yes | No | 1.10 | 5.90 | PASS |
| cut_in_65_45 | Yes | Yes | No | 4.05 | 10.24 | PASS |
| cut_in_80_50 | Yes | Yes | No | 3.10 | 14.28 | PASS |
| cut_out_65_35 | No | No | No | - | - | PASS |
| cut_out_late_65_35 | Yes | Yes | No | 2.25 | 12.18 | PASS |
| cut_out_80_50 | No | No | No | - | - | PASS |
| multi_adjacent_decoy_65 | Yes | Yes | No | 2.90 | 11.73 | PASS |
| multi_two_leads_80 | Yes | Yes | No | 1.30 | 6.38 | PASS |

## Kiểm Tra Fusion Trong Tick Log

Một số scenario được kiểm tra thủ công trong tick-level CSV:

| Scenario | Rows có fusion confirmed | Rows bị fusion chặn phanh | Rows phanh | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| ccrs_60_demo_150 | 61 | 0 | 38 | Target cùng làn được xác nhận trước khi phanh |
| ccrs_80 | 72 | 0 | 50 | Vẫn phanh kịp ở 80 km/h |
| curve_ccrs_65 | 50 | 0 | 44 | Đường cong vẫn xác nhận được target |
| cut_in_65_45 | 67 | 0 | 41 | Cut-in được xác nhận khi vào hành lang nguy hiểm |
| cut_out_65_35 | 31 | 0 | 0 | Có nhìn thấy xe nhưng không phanh vì target rời hành lang |
| multi_adjacent_decoy_65 | 90 | 0 | 41 | Không chọn nhầm decoy làn bên |

Ví dụ `ccrs_60_demo_150`:

```text
first_brake t=7.40 s
ego_speed=60.039 km/h
bumper_gap=24.6305 m
reason=ttc_below_brake_threshold|fusion_confirmed
```

## Nhận Xét

Fusion-AEB binary đã chạy ổn trên bộ validation hiện tại. Điểm quan trọng là
camera chưa dùng để tính khoảng cách hoặc TTC; camera chỉ xác nhận target radar
bằng phép chiếu hình học radar-to-camera và bbox YOLO.

Kết quả 29/29 PASS cho thấy có thể dùng fusion gate làm nền cho bước tiếp theo:

- đưa logic này vào UI full/demo,
- log thêm số bbox, pixel chiếu radar và trạng thái fusion vào CSV,
- nâng cấp từ phanh binary sang phanh nhiều tầng hoặc PID,
- test thêm repeat nhiều lần để đánh giá độ ổn định thống kê.

## Hạn Chế Của Lần Test

- Chưa ghi video evidence cho full batch để tiết kiệm thời gian.
- Chưa test trong điều kiện nhiều loại thời tiết/ánh sáng.
- Fusion gate hiện dựa trên target radar chiếu vào bbox YOLO. Nếu bbox YOLO mất
  trong thời gian dài, BRAKE sẽ bị chặn. Hiện có `confirmation_hold_s = 0.35 s`
  để giảm nhấp nhả ngắn hạn.
- Các scenario vẫn là môi trường mô phỏng có kiểm soát, chưa đại diện đầy đủ cho
  giao thông thật.

## Kết Luận

Binary brake với fusion camera-radar đã đạt mức smoke/full validation đầu tiên.
Radar-only vẫn là baseline safety tốt; fusion đã sẵn sàng để đưa vào nhánh demo
và làm nền cho bài test phanh nhiều tầng/PID.
