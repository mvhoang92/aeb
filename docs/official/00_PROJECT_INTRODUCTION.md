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

Radar-only hiện là nhánh ổn định nhất. Pipeline không còn dùng một radar point
đơn lẻ để phanh, mà gom point thành object, tracking qua nhiều frame rồi mới
chọn target AEB. Cách này gần với tư duy của radar thật hơn: radar cấp thấp tạo
điểm đo, tầng xử lý tạo track/object, tầng AEB quyết định phanh.

Camera, YOLO và fusion đã có app debug và khung xử lý, nhưng chưa phải nhánh AEB
chính. Dataset collector và training pipeline đã có, cần thu data tốt hơn để
train model riêng cho môi trường CARLA.

## Mốc Kết Quả

- Unit test logic sau refactor: `28/28 PASS`.
- Smoke test CARLA sau refactor cấu trúc:
  - `clear_road_50`: PASS, không phanh sai.
  - `ccrs_50`: PASS, có phanh và không va chạm.
- Radar-only regression trước đó đã chạy qua các nhóm scenario 50-80 km/h gồm
  đường thẳng, đường cong, adjacent lane, cut-in, cut-out và nhiều xe.

## Giới Hạn

- CARLA radar không mô phỏng đầy đủ sóng FMCW, Doppler map, CFAR hay clutter như
  radar thật.
- Binary brake `0/1` còn gắt, cần PID hoặc profile phanh theo khoảng cách/TTC.
- Fusion camera-radar mới ở mức debug/hiển thị, chưa là cơ chế quyết định chính.
- Dataset YOLO cần audit kỹ để tránh label xe bị che khuất quá nặng.

## Lộ Trình

1. Chốt radar-only AEB hoạt động ổn ở 50-80 km/h.
2. Thu dataset camera bằng ground truth CARLA.
3. Train YOLO một class `car`, export ONNX CUDA.
4. Dùng fusion để xác nhận target AEB.
5. Làm phanh mượt bằng PID hoặc controller theo profile.
