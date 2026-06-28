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
- Transform hiện tại so với gốc ego: `x=0.43 m`, `y=0.0 m`, `z=1.35 m`,
  `pitch=yaw=roll=0 deg`.
- FOV ngang: `70 deg`.
- Độ phân giải: `1280x720`.
- Sensor tick: `0.05 s`, tương đương khoảng `20 FPS`.
- Vai trò:
  - Hiển thị góc nhìn tài xế/AEB camera.
  - Cấp ảnh cho YOLO.
  - Dùng để xác nhận radar target trong fusion.
- Độ phân giải lấy theo config hiện tại. Khi thu dataset, ảnh và label YOLO phải
  dùng đúng cùng camera config để tránh lệch hình học.

## Radar

- Loại CARLA: `sensor.other.radar`.
- Vị trí: mũi xe, gần tâm ngang của xe.
- Transform hiện tại so với gốc ego: `x=2.53 m`, `y=0.0 m`, `z=0.48 m`,
  `pitch=yaw=roll=0 deg`.
- Range: `100 m`.
- FOV ngang/dọc: `30 deg` / `6 deg`.
- Points per second: `2000`.
- Sensor tick: `0.05 s`, tương đương khoảng `20 FPS`.
- Vai trò:
  - Cung cấp điểm đo phía trước.
  - Mỗi điểm có khoảng cách, góc, độ cao tương đối và vận tốc tương đối.
  - Sau xử lý sẽ tạo object list để tính TTC/khoảng cách dừng.

CARLA radar không phải radar FMCW đầy đủ ngoài đời. Nó trả về detection point đã
được engine mô phỏng sẵn, gần với “point-level output” hơn là tín hiệu raw. Vì
vậy project cần tự xây tầng clustering/tracking để biến point thành object.

## Kiểm Chứng Vị Trí Và Tầm Sensor

Script `scripts/visualize_sensor_coverage.py` dùng đúng `configs/sensors.yaml`,
bắt buộc ego là `vehicle.tesla.model3`, vẽ FOV camera/radar trong CARLA và chụp
4 ảnh minh họa:

- `near_top_view.png`: nhìn từ trên xuống gần xe, kiểm tra sensor có nằm đúng vị
  trí trên Tesla Model 3 không.
- `far_top_view.png`: nhìn từ trên xuống xa, kiểm tra tầm radar tối đa và FOV
  ngang.
- `near_side_view.png`: nhìn ngang gần xe, kiểm tra cao độ camera/radar.
- `far_side_view.png`: nhìn ngang xa theo kiểu hình chiếu cạnh, kiểm tra FOV
  dọc và range.

Camera được vẽ màu xanh dương, radar màu đỏ/cam. Radar dùng đúng range trong
config; camera dùng range minh họa để thấy FOV vì camera RGB không có max range
vật lý cố định như radar.

Camera được tinh chỉnh theo `near_side_view.png` để nằm sát mặt trong kính lái,
gần vùng phía trên kính nhưng không nổi ra ngoài nóc xe.

Radar được tinh chỉnh để hơi nhô khỏi mặt cản trước của Tesla Model 3 trong
CARLA. Bbox xe báo mũi xe xấp xỉ `x=2.425 m`; config hiện tại đặt radar tại
`x=2.53 m`, tức nhô trước bbox khoảng `10.5 cm`. Mục tiêu là giảm sai số khi xe
áp sát vật cản phía trước/lan can trong bài test radar gần.

Ảnh minh họa nên chụp trên `Town06` để nền thoáng và góc cạnh ít bị tường/cây
che. Điều này không đổi ODD chính của project; radar-only AEB vẫn ưu tiên test
trên `Town04`.

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
