# 03. Xử Lý Radar

Mục tiêu của tầng radar là biến các point rời rạc của CARLA thành object target
có thể dùng cho AEB. Đây là điểm quan trọng vì phanh trực tiếp theo từng point
dễ bị nhiễu bởi mặt đường, tường, cây, vật thể ngoài làn hoặc point xuất hiện
thoáng qua.

## Dữ Liệu Đầu Vào

Mỗi radar point được quy về hệ ego:

- `x_forward_m`: khoảng cách theo phương tiến.
- `y_right_m`: lệch ngang, dương sang phải.
- `z_up_m`: độ cao tương đối.
- `relative_velocity_mps`: vận tốc tương đối theo hướng radar. Giá trị âm
  thường nghĩa là vật thể đang tiến lại gần ego.

TTC point-level:

```text
TTC = distance / closing_speed
closing_speed = -relative_velocity_mps
```

TTC chỉ có ý nghĩa khi `closing_speed > 0`.

## Lọc Point

Các bước lọc chính:

1. Giới hạn theo tầm radar.
2. Bỏ point quá thấp/quá giống mặt đường.
3. Giữ point trong hành lang dự đoán của ego, thay vì dùng toàn bộ quạt radar.
4. Có thể nới hành lang ở xa và siết hành lang ở gần để giảm phanh nhầm khi cua.

Ý tưởng hành lang dự đoán tương tự hướng của Autoware: chỉ vật thể giao với quỹ
đạo dự đoán của xe mới nên được xét cho AEB.

## Clustering Và Tracking

CARLA radar point được gom cụm theo:

- Khoảng cách dọc/ngang gần nhau.
- Vận tốc tương đối gần nhau.
- Cùng vùng không gian phía trước ego.

Sau đó tracker giữ cụm qua nhiều frame. Object chỉ được xác nhận khi xuất hiện
đủ số frame liên tiếp. Nếu mất point, track bị đánh stale hoặc mất quyền kích
hoạt AEB.

Đầu ra là `RadarObjectList`, trong đó mỗi object có:

- Vị trí dọc/ngang.
- Khoảng cách target.
- Vận tốc tương đối.
- TTC.
- Số point trong cluster.
- Số frame đã được xác nhận.
- Confidence nội bộ.

## Chọn Target AEB

Target được chọn từ object đã xác nhận, không stale và nằm trong vùng có khả năng
va chạm. Tiêu chí ưu tiên hiện tại là TTC thấp và khoảng cách gần trong hành
lang ego. Nhờ vậy, một point nhiễu đơn lẻ không còn đủ để làm xe phanh.

## Kết Luận Thiết Kế

Pipeline radar hiện tại là bản thích nghi giữa CARLA và tư duy radar thật:
CARLA cấp detection point, project tự tạo object list rồi mới đưa sang AEB. Đây
là hướng phù hợp hơn so với tính TTC trên toàn bộ point radar.
