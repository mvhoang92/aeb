# 01. Phân Tích Hướng AEB Của Autoware

Autoware là một stack tự hành mã nguồn mở, trong đó AEB được thiết kế theo tư
duy an toàn: chỉ xét vật cản có khả năng nằm trên quỹ đạo dự đoán của ego, sau
đó đánh giá khoảng cách dừng và nguy cơ va chạm.

## Ý Tưởng Quan Trọng

- Sinh predicted path của ego từ trạng thái xe, steering/IMU hoặc quỹ đạo điều
  khiển.
- Chỉ xét obstacle nằm gần predicted path.
- Dùng footprint/hành lang an toàn thay vì toàn bộ vùng cảm biến.
- Lọc obstacle theo chiều cao, vị trí, độ tin cậy.
- Quyết định phanh dựa trên khoảng cách dừng, thời gian phản ứng và biên an toàn.

## Bài Học Cho Radar AEB

Điểm đáng học nhất không phải là bê nguyên code, mà là cấu trúc quyết định:

```text
sensor data
  -> obstacle/object extraction
  -> predicted ego path
  -> obstacle on path
  -> stopping distance / collision check
  -> AEB command
```

Cách này giảm phanh nhầm khi:

- Xe đi qua vật thể ở làn bên.
- Xe cua và radar vẫn nhìn thấy tường/cây phía trước theo góc quét.
- Mặt đường hoặc vật thể tĩnh sinh point không liên quan đến quỹ đạo ego.

## Khác Biệt Với Project

Autoware thường làm việc với obstacle/object từ LiDAR, camera, radar hoặc
fusion ở tầng nhận thức cao hơn. Project CARLA hiện dùng radar point sparse, nên
cần thêm tầng clustering/tracking để tạo object list trước khi áp dụng tư duy
Autoware.
