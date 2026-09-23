# 00. Giới Thiệu Dự Án

Dự án này xây dựng một hệ thống AEB mô phỏng trên CARLA 0.9.11. Mục tiêu không
phải chứng nhận NCAP chính thức, mà là tạo một pipeline nghiên cứu đủ rõ ràng để
giải thích, thử nghiệm và mở rộng: cảm biến -> nhận thức -> chọn mục tiêu nguy
hiểm -> tính nguy cơ va chạm -> cảnh báo/phanh.

## Phạm Vi

- Ego vehicle: `vehicle.tesla.model3`.
- Môi trường chính: cao tốc `Town04`.
- Đối tượng chính: ô tô phía trước và ô tô cùng làn.
- Cảm biến:
  - Camera RGB sau kính lái.
  - Radar phía trước mũi xe.
- Dải mục tiêu hiện tại: 50-80 km/h trong các scenario car-to-car đơn giản và
  bán phức tạp.

## Trạng Thái Kỹ Thuật

Pipeline hiện tại đã đi qua đủ các bước chính của đồ án: radar object-level,
YOLO một class `car`, camera-radar fusion, chọn target, tính TTC/khoảng cách
dừng và phanh staged PID. Radar-only vẫn được giữ làm nhánh tham chiếu, nhưng
bản đánh giá cuối cùng dùng camera YOLO ONNX kết hợp radar object pipeline.

Radar không còn dùng một điểm đo đơn lẻ để phanh, mà gom điểm thành object,
tracking qua nhiều frame rồi mới chọn target AEB. Cách này gần với tư duy radar
thật hơn: radar cấp thấp tạo điểm đo, tầng xử lý tạo track/object, tầng AEB quyết
định cảnh báo/phanh.

Camera dùng YOLO26n đã train lại trên `dataset_v7_same_lane`. Fusion dùng phép
chiếu hình học để ghép radar object với bounding box YOLO, qua đó xác nhận target
là xe phía trước.

Phanh chính hiện tại là `staged_pid`: chia rủi ro thành nhiều tầng, dùng PID
trong từng tầng và có logic nhả phanh khi nguy cơ không còn.

## Mốc Kết Quả

- Unit test logic sau refactor: `28/28 PASS`.
- Dataset chính: `dataset_v7_same_lane`, gồm 2005 ảnh và 2515 bounding box.
- Model chính: `models/yolo26n_aeb_v7.pt` và `models/yolo26n_aeb_v7.onnx`.
- Final evidence staged PID:
  - 66 kịch bản.
  - 63 đạt, 3 không đạt.
  - Tỷ lệ đạt 95,45%.
- Các trường hợp không đạt được giữ lại để xác định giới hạn hệ thống, đặc biệt
  ở vận tốc cao và khoảng cách đầu nhỏ.

## Giới Hạn

- CARLA radar không mô phỏng đầy đủ sóng FMCW, Doppler map, CFAR hay clutter như
  radar thật.
- Bộ test hiện lấy cảm hứng từ NCAP car-to-car nhưng chưa phải bài chứng nhận
  NCAP chính thức.
- Dataset YOLO hiện tập trung vào xe cùng làn trong Town04, chưa bao phủ nhiều
  map/thời tiết.
- Controller phanh là mô phỏng, chưa có đầy đủ actuator delay, ABS/tire model
  như xe thật.
- Jerk trong CARLA chỉ dùng để so sánh tương đối, không xem là giá trị tuyệt đối
  của xe thật.
- CARLA 0.9.11 có thể không ổn định khi chạy nhiều kịch bản liên tục.

## Lộ Trình

1. Giữ `report/report_v3.md` làm báo cáo frozen; thuật toán mới phải tạo report generation mới.
2. Bổ sung phần NCAP/Euro NCAP và mapping scenario của đồ án.
3. Bổ sung so sánh các bộ phanh: binary, PID v1, PID v2, staged PID.
4. Tạo/thu thập hình minh họa còn thiếu cho báo cáo.
5. Đưa link GitHub và link Drive video vào phụ lục trước khi chuyển `.docx`.
