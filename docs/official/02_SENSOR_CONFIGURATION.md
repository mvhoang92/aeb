# 02. Cấu Hình Cảm Biến

Cấu hình chính nằm trong `configs/sensors.yaml` và `configs/camera.yaml`. Mục
tiêu là bám hình dung xe thật ở mức mô phỏng: camera đặt sau kính lái, radar đặt
ở giữa mũi xe, cùng hướng với trục tiến của ego vehicle.

## Ego Vehicle

- Blueprint: `vehicle.tesla.model3`.
- Vai trò: ego car.
- Môi trường ưu tiên: `Town04`, đường cao tốc, chủ yếu car-to-car.

## Camera

- Loại: `sensor.camera.rgb`.
- Vị trí: sau kính lái, nhìn theo hướng tiến của xe.
- Vai trò:
  - Hiển thị góc nhìn tài xế/AEB camera.
  - Cấp ảnh cho YOLO.
  - Dùng để xác nhận radar target trong fusion.
- Độ phân giải lấy theo config hiện tại. Khi thu dataset, ảnh và label YOLO phải
  dùng đúng cùng camera config để tránh lệch hình học.

## Radar

- Loại CARLA: `sensor.other.radar`.
- Vị trí: mũi xe, gần tâm ngang của xe.
- Vai trò:
  - Cung cấp điểm đo phía trước.
  - Mỗi điểm có khoảng cách, góc, độ cao tương đối và vận tốc tương đối.
  - Sau xử lý sẽ tạo object list để tính TTC/khoảng cách dừng.

CARLA radar không phải radar FMCW đầy đủ ngoài đời. Nó trả về detection point đã
được engine mô phỏng sẵn, gần với “point-level output” hơn là tín hiệu raw. Vì
vậy project cần tự xây tầng clustering/tracking để biến point thành object.

## Tần Số Và FPS

Camera có thể giới hạn 20-30 FPS để nhẹ hơn. Với AEB, radar và logic phanh nên
được đồng bộ theo tick mô phỏng khi chạy batch. Nếu server dao động 30-40 FPS mà
camera chạy 20 FPS, fusion cần kiểm tra tuổi dữ liệu camera/radar trước khi kết
hợp.

## Ghi Chú Chạy CARLA

Lệnh ổn định trên máy hiện tại:

```bash
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Không dùng `-opengl` vì từng gây lỗi render pygame/manual control.
