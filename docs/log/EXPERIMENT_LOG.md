# Nhật Ký Thử Nghiệm

File này chỉ ghi tóm tắt các lần thử nghiệm quan trọng, lỗi đã gặp và quyết định
sửa chính. Log thô, ảnh và video vẫn nằm trong `logs/`. Tài liệu cũ được giữ ở
`docs/backup/RADAR_ONLY_EXPERIMENT_LOG.md`.

## 2026-06-10 - Smoke Test Sau Refactor Cấu Trúc Code

Lệnh chạy:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --scenario clear_road_50 \
  --scenario ccrs_50 \
  --run-id structure_refactor_smoke_20260610 \
  --load-map
```

Kết quả:

- `clear_road_50`: PASS, không phanh sai.
- `ccrs_50`: PASS, có phanh, không va chạm, `min_gap=6.943 m`.
- Log: `logs/structure_refactor_smoke_20260610`.

Ý nghĩa: refactor thư mục code không làm vỡ pipeline radar-only cơ bản.

## Radar-Only Regression Trước Refactor

Các nhóm đã từng chạy:

- Đường trống.
- CCRs, CCRm, CCRb.
- Adjacent lane.
- Đường cong.
- Cut-in, cut-out.
- Nhiều xe target.

Kết quả đã đạt trong mô phỏng có kiểm soát:

- Baseline 27 scenario 50-80 km/h: `27/27 PASS`.
- Nhóm động/nhiều xe chạy lặp ba lần: `21/21 PASS`.
- Unit test logic sau refactor: `28/28 PASS`.

Các kết quả này là bằng chứng nội bộ cho project, không phải chứng nhận NCAP.

## Các Lỗi Thiết Kế Đã Gặp

- Tính TTC trên toàn bộ radar point gây phanh nhầm khi lùi hoặc khi radar nhìn
  thấy mặt đường/tường/cây.
- Point đơn lẻ gây phanh nhạy quá mức.
- Radar quét rộng trong lúc cua khiến vật thể ngoài quỹ đạo bị coi là nguy hiểm.
- `-opengl` làm cửa sổ pygame/manual control render lỗi trên máy hiện tại.

## Các Sửa Chính

- Không phanh khi xe đang lùi với AEB phía trước.
- Thêm lọc độ cao và hành lang dự đoán.
- Chuyển từ point-level TTC sang radar object list.
- Thêm clustering/tracking và yêu cầu object được xác nhận qua nhiều frame.
- Tách code theo `ui/`, `scripts/`, `core/`, `perception/`, `control/`.
