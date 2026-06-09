# 00. Nền Tảng ADAS Và AEB

ADAS là nhóm hệ thống hỗ trợ người lái nhằm tăng an toàn, giảm tải thao tác và
cảnh báo sớm rủi ro. AEB là một chức năng ADAS quan trọng: khi hệ thống dự đoán
có nguy cơ va chạm phía trước, xe sẽ cảnh báo và có thể tự phanh nếu người lái
không phản ứng đủ nhanh.

## Cảm Biến Thường Gặp

- Camera: nhận diện làn đường, xe, người đi bộ, biển báo; mạnh về phân loại và
  hình dạng.
- Radar trước: đo khoảng cách và vận tốc tương đối; mạnh trong bài toán car-to-
  car và điều kiện ánh sáng xấu.
- LiDAR: tạo point cloud 3D chính xác; phổ biến trong robot tự hành hơn xe phổ
  thông vì chi phí.
- Ultrasonic: tầm gần, thường dùng cho parking.
- IMU/GNSS/wheel speed: trạng thái chuyển động của ego vehicle.

## Nguyên Lý AEB

AEB cần ba nhóm thông tin:

1. Ego đang đi như thế nào: vận tốc, gia tốc, hướng lái.
2. Target phía trước ở đâu: khoảng cách dọc, lệch ngang, cùng làn hay không.
3. Target đang chuyển động như thế nào: vận tốc tương đối, TTC, khả năng va chạm.

Các đại lượng hay dùng:

```text
closing_speed = v_ego - v_target
TTC = distance / closing_speed
```

Và khoảng cách dừng:

```text
d_stop = v * t_response + v^2 / (2a)
```

Trong hệ thống thực tế, AEB không chỉ dùng một ngưỡng TTC cứng. Nó thường kết
hợp TTC, khoảng cách dừng, dự đoán quỹ đạo, phân loại object, độ tin cậy cảm
biến và trạng thái người lái.

## Các Tầng Thuật Toán

- Detection: phát hiện object hoặc radar point.
- Tracking: duy trì object qua thời gian.
- Prediction: dự đoán quỹ đạo ego và target.
- Risk assessment: đánh giá TTC, khoảng cách dừng, khả năng giao cắt quỹ đạo.
- Decision: cảnh báo, chuẩn bị phanh, phanh một phần hoặc phanh khẩn cấp.
- Control: chuyển quyết định thành lệnh phanh thực tế.

## Ghi Chú Báo Cáo

Khi trình bày, nên tách rõ “nguyên lý chung của AEB” và “phiên bản mô phỏng
trong CARLA”. Phần nguyên lý có thể nói về xe thật, còn phần CARLA cần nêu rõ
giới hạn mô phỏng.
