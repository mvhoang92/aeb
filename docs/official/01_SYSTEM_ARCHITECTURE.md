# 01. Kiến Trúc Hệ Thống

Pipeline tổng thể:

```text
CARLA world
  -> ego vehicle + camera + radar
  -> perception
     -> radar object list
     -> camera YOLO boxes
  -> target selection / fusion
  -> TTC + stopping distance
  -> warning / brake decision
  -> CARLA VehicleControl override
  -> log + ảnh + video kiểm chứng
```

## Các Tầng Code

- `ui/`: các app debug 2 panel. Bên trái giữ logic `manual_control.py`, bên
  phải vẽ camera, radar, YOLO hoặc fusion.
- `scripts/`: các script chạy batch, thu dataset và train model.
- `core/`: logic dùng chung, gồm pipeline AEB, radar object, target selector.
- `perception/radar/`: xử lý radar point thành cluster/track/object.
- `control/`: logic phanh, TTC, state và override điều khiển xe.
- `configs/`: cấu hình sensor, model, dataset và scenario.
- `tests/`: unit test cho helper và logic quyết định.

## Luồng Radar-Only

```text
RadarMeasurement
  -> đổi sang điểm trong hệ ego
  -> lọc range / độ cao / hành lang dự đoán
  -> cluster theo vị trí và vận tốc
  -> tracking qua frame
  -> RadarObjectList
  -> chọn target có nguy cơ cao nhất
  -> AEB decision
```

## Luồng Camera/Fusion

Camera RGB tạo ảnh từ góc sau kính lái. YOLO nhận ảnh này và vẽ bounding box
cho class `car`. Radar point/object được chiếu sang ảnh camera bằng quan hệ hình
học giữa camera, radar và ego. Fusion hiện dùng để debug target radar nằm trong
bbox nào; hướng tiếp theo là tạo `FusedTarget` ổn định để thay hoặc xác nhận
target radar-only.

## Đồng Bộ Mô Phỏng

Khi chạy scenario batch, nên dùng synchronous mode để mỗi tick CARLA tạo dữ liệu
cảm biến nhất quán. Khi debug manual UI, có thể chạy asynchronous để thao tác
mượt hơn. Nếu camera có fps thấp hơn server fps, dữ liệu camera sẽ cập nhật thưa
hơn; radar và AEB cần timestamp/frame id để tránh lấy nhầm dữ liệu quá cũ.
