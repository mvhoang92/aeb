# 07. Scenario Và Validation

Validation dùng để trả lời hai câu hỏi: AEB có phanh khi cần không, và có tránh
phanh nhầm khi không nguy hiểm không.

## Liên Hệ Với NCAP

Các kịch bản trong đồ án lấy cảm hứng từ nhóm bài toán AEB car-to-car của NCAP,
đặc biệt là các tình huống:

- `CCRs`: Car-to-Car Rear stationary, xe mục tiêu đứng yên phía trước.
- `CCRm`: Car-to-Car Rear moving, xe mục tiêu chạy chậm hơn phía trước.
- `CCRb`: Car-to-Car Rear braking, xe mục tiêu phía trước đang chạy rồi phanh.

Đồ án không tuyên bố đây là bộ kiểm thử chứng nhận NCAP chính thức. Các điểm học
theo NCAP là cách chia nhóm tình huống car-to-car, cách thay đổi vận tốc/khoảng
cách ban đầu và cách quan sát kết quả có/không va chạm. Các bài cut-in, adjacent
lane, multi-actor và curve được thêm vào để đánh giá khả năng chọn target và tìm
giới hạn hệ thống trong mô phỏng.

## Nhóm Scenario

- `clear_road`: đường trống, không được phanh.
- `ccrs`: xe phía trước đứng yên, ego tiến đến.
- `ccrs_60_gap_200`: biến thể demo dài trên đoạn Town04 rộng/thẳng
  (`spawn_index=81`), target đứng yên cách 200 m, ego chạy 60 km/h; radar-only
  AEB chỉ bắt đầu thấy target khi xe vào trong range radar 100 m.
- `ccrs_60_demo_150`: bài demo trực quan trên cùng đoạn rộng/thẳng, target đứng
  yên cách 150 m để ego có đoạn chạy ổn định ở 60 km/h trước khi vào vùng radar
  và AEB can thiệp.
- `ccrm`: xe phía trước chạy chậm hơn.
- `ccrb`: xe phía trước phanh gấp.
- `adjacent_lane`: xe ở làn bên, không được phanh nhầm.
- `curve`: đường cong, kiểm tra hành lang dự đoán.
- `cut_in`: xe nhập làn phía trước ego.
- `cut_out`: xe phía trước rời làn.
- `multi_actor`: nhiều xe, cần chọn đúng target cùng làn/nguy hiểm nhất.

## Nhóm Đánh Giá

Khi viết báo cáo nên tách kết quả thành hai nhóm:

1. **Bộ test mục tiêu**: dải vận tốc/khoảng cách hệ thống được kỳ vọng hoạt động
   tốt, ưu tiên 50-80 km/h trên cao tốc, only-car, thời tiết lý tưởng. Nhóm này
   dùng để chứng minh hệ thống đạt mục tiêu thiết kế.
2. **Bộ test giới hạn**: mở rộng vận tốc, giảm khoảng cách đầu hoặc dùng cut-in
   khó hơn để tìm biên hoạt động của hệ thống. Nhóm này cho phép có trường hợp
   không đạt; mục tiêu là chỉ ra giới hạn, không phải làm đẹp tỷ lệ đạt.

## Tiêu Chí PASS/FAIL

- Scenario nguy hiểm: đạt nếu AEB phanh đúng lúc và không va chạm.
- Scenario không nguy hiểm: đạt nếu không phanh sai.
- Kiểm tra thêm:
  - `min_gap_m`: khoảng cách nhỏ nhất.
  - `first_brake_time_s`: thời điểm phanh đầu tiên.
  - `target_id`: target được chọn.
  - `collision`: có va chạm hay không.
  - `false_positive`: phanh khi không cần.
  - `maximum_abs_jerk_mps3`: jerk raw của CARLA, chỉ dùng để so sánh tương đối
    giữa các cấu hình phanh trong cùng bộ test; không coi là jerk tuyệt đối của
    xe thật.

## Chạy Batch

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --control-mode physics \
  --load-map
```

Log, ảnh và video nằm trong `logs/<run_id>/`. Nhật ký kết quả tổng hợp nằm ở
`docs/log/EXPERIMENT_LOG.md`.

## Kết Quả Final Evidence Hiện Tại

Bộ final evidence dùng staged PID, camera YOLO ONNX và radar object pipeline.
Kết quả tổng hợp:

| Tổng case | Đạt | Không đạt | Tỷ lệ đạt |
| ---: | ---: | ---: | ---: |
| 66 | 63 | 3 | 95,45% |

Các trường hợp không đạt:

| Scenario | Nhóm | Nhận xét |
| --- | --- | --- |
| `ccrb_95_gap_20` | CCRb giới hạn | Xe trước phanh gấp, tốc độ cao, khoảng cách đầu nhỏ |
| `ccrb_110_gap_20` | CCRb giới hạn | Vượt dải vận tốc/khoảng cách an toàn hiện tại |
| `cutin_100_60_gap_25` | Cut-in giới hạn | Xe nhập làn ở tốc độ cao và khoảng cách nhỏ |

Khi viết báo cáo, không nên gộp ba case này vào kết luận “hệ thống lỗi”, mà nên
giải thích đây là vùng giới hạn của hệ thống theo đúng tư duy đánh giá sản phẩm.
