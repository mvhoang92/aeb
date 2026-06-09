# 02. Phân Tích Hướng Radar/Vision Của openpilot

openpilot là hệ thống hỗ trợ lái mã nguồn mở tập trung nhiều vào camera và radar
trên một số nền tảng xe. Với bài toán giữ khoảng cách và cảnh báo/phanh, hướng
tư duy đáng chú ý là kết hợp track radar với lead vehicle từ vision.

## Ý Tưởng Quan Trọng

- Radar cung cấp track có khoảng cách và vận tốc tương đối.
- Vision/model dự đoán lead vehicle và xác suất object phía trước.
- Association giữa radar track và lead từ camera giúp giảm nhiễu.
- Hệ thống không tin tuyệt đối vào một frame đơn lẻ; tracking và temporal
  consistency rất quan trọng.

## Bài Học Cho Project

Với AEB CARLA:

- Radar-only nên có tracking trước khi phanh.
- Camera/YOLO nên dùng để xác nhận target radar nằm trong bbox xe.
- Không nên phanh theo detection một frame nếu không có bằng chứng đủ ổn định.
- Radar fallback vẫn cần tồn tại khi camera mất detection tạm thời.

## Khác Biệt Với Project

openpilot làm trên xe thật, có dữ liệu radar/vision thực và controller xe thật.
Project này chạy trong CARLA, radar là detection point mô phỏng, nên phần
clustering/tracking và kiểm soát false positive phải tự thiết kế phù hợp với dữ
liệu CARLA.
