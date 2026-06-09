# 05. So Sánh Cấu Hình Cảm Biến

File này đặt cấu hình dự án cạnh cấu hình thường gặp để biết điểm nào hợp lý và
điểm nào là giới hạn mô phỏng.

## Radar Trước

Cấu hình dự án hiện hướng tới:

- Range: khoảng 100 m.
- FOV ngang: khoảng 30 độ.
- Vị trí: giữa mũi xe.
- Output: detection point CARLA, sau đó project tự cluster/track.

Radar ô tô thật có thể có tầm xa hơn, thường dùng radar trước tầm trung/tầm xa
để hỗ trợ ACC/AEB. Output cuối của radar thương mại thường là object/track list,
không chỉ là point rời rạc.

## Camera Trước

Cấu hình dự án:

- Camera RGB sau kính lái.
- FOV và độ phân giải cố định theo config.
- Dùng cho YOLO và fusion.

Camera thật thường có calibration nghiêm ngặt, lens/distortion riêng, exposure
và xử lý ảnh riêng. Trong CARLA, camera sạch hơn và dễ label hơn.

## Tần Số

Với mô phỏng:

- Radar/AEB nên chạy theo tick mô phỏng khi batch.
- Camera 20-30 FPS là hợp lý để giảm tải.
- Fusion cần kiểm tra timestamp khi hai cảm biến khác tần số.

## Khuyến Nghị

- Giữ radar 100 m cho giai đoạn 50-80 km/h, vì đủ cho scenario hiện tại.
- Nếu muốn chạy tốc độ cao hơn hoặc phanh sớm hơn, cần tăng range và kiểm tra
  lại false positive.
- Có thể tăng `points_per_second` để radar point dày hơn, nhưng không nên dùng
  mật độ point để che lỗi thuật toán. Tracking và target selection vẫn là phần
  chính.
