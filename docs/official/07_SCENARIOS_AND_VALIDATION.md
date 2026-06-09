# 07. Scenario Và Validation

Validation dùng để trả lời hai câu hỏi: AEB có phanh khi cần không, và có tránh
phanh nhầm khi không nguy hiểm không.

## Nhóm Scenario

- `clear_road`: đường trống, không được phanh.
- `ccrs`: xe phía trước đứng yên, ego tiến đến.
- `ccrm`: xe phía trước chạy chậm hơn.
- `ccrb`: xe phía trước phanh gấp.
- `adjacent_lane`: xe ở làn bên, không được phanh nhầm.
- `curve`: đường cong, kiểm tra hành lang dự đoán.
- `cut_in`: xe nhập làn phía trước ego.
- `cut_out`: xe phía trước rời làn.
- `multi_actor`: nhiều xe, cần chọn đúng target cùng làn/nguy hiểm nhất.

Các tên lấy cảm hứng từ bài toán NCAP car-to-car, không tuyên bố là bài test
NCAP chính thức.

## Tiêu Chí PASS/FAIL

- Scenario nguy hiểm: PASS nếu AEB phanh đúng lúc và không va chạm.
- Scenario không nguy hiểm: PASS nếu không phanh sai.
- Kiểm tra thêm:
  - `min_gap_m`: khoảng cách nhỏ nhất.
  - `first_brake_time_s`: thời điểm phanh đầu tiên.
  - `target_id`: target được chọn.
  - `collision`: có va chạm hay không.
  - `false_positive`: phanh khi không cần.

## Chạy Batch

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --load-map
```

Log, ảnh và video nằm trong `logs/<run_id>/`. Nhật ký kết quả tổng hợp nằm ở
`docs/log/EXPERIMENT_LOG.md`.

## Kết Quả Gần Nhất

Sau refactor cấu trúc code, smoke test trên CARLA đã chạy:

- `clear_road_50`: PASS, không phanh sai.
- `ccrs_50`: PASS, AEB phanh và không va chạm.

Đây là smoke test để xác nhận refactor không làm vỡ pipeline, chưa thay thế cho
regression đầy đủ.
