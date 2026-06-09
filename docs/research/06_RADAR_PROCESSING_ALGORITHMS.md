# 06. Thuật Toán Xử Lý Radar Cho AEB

Các thuật toán radar AEB thường không dừng ở việc tính TTC cho từng điểm đo. Hệ
thống cần biến dữ liệu cảm biến thành target ổn định, rồi mới quyết định phanh.

## Pipeline Khuyến Nghị

```text
radar point
  -> coordinate transform
  -> range/height/path filtering
  -> clustering
  -> tracking
  -> object list
  -> target selection
  -> TTC + stopping distance
  -> warning/brake state
```

## Lọc Nhiễu

- Ground filtering: bỏ point quá gần mặt đường.
- Path filtering: chỉ giữ point trong hành lang dự đoán.
- Lateral gating: bỏ object lệch làn.
- Temporal filtering: yêu cầu object tồn tại nhiều frame.
- Stale handling: không phanh theo object đã mất detection mới.

## Clustering

Clustering gom các point gần nhau thành candidate object. Trong project nhỏ, có
thể dùng rule theo khoảng cách và vận tốc. Trong hệ thống lớn hơn, có thể dùng
DBSCAN hoặc tracker đa mục tiêu.

## Tracking

Tracking giúp:

- Giữ `track_id`.
- Ước lượng target ổn định hơn.
- Giảm phanh nhầm bởi point một frame.
- Biết object mất detection hay vẫn tồn tại.

## Target Selection

Target AEB nên ưu tiên:

- Nằm trên quỹ đạo ego.
- Được xác nhận qua nhiều frame.
- Có closing speed dương.
- TTC thấp hoặc khoảng cách dừng không đủ.

Không nên chọn target chỉ vì nó gần nhất nếu nó lệch làn hoặc không có nguy cơ
va chạm.
