# 05. Camera-Radar Fusion

Fusion nhằm giảm nhược điểm của từng cảm biến. Radar đo khoảng cách/vận tốc tốt
nhưng point thưa và dễ có nhiễu hình học. Camera nhận diện object tốt hơn về
hình dạng nhưng không đo vận tốc tương đối trực tiếp. Kết hợp hai nguồn giúp AEB
chỉ phanh khi target radar được camera xác nhận là xe phía trước.

## Ý Tưởng Chính

```text
YOLO bbox trên ảnh
Radar object / radar point trong hệ ego
  -> chiếu radar sang mặt phẳng ảnh camera
  -> kiểm tra point/object nằm trong bbox nào
  -> tạo fused target
```

CARLA không tự nói “điểm radar này thuộc pixel YOLO nào”. Project dùng toán học
hình học: transform từ radar sang ego/world/camera rồi dùng ma trận nội tại
camera để chiếu điểm 3D lên ảnh 2D.

## Association

Một radar object có thể được ghép với bbox nếu:

- Điểm chiếu nằm trong bbox hoặc gần tâm bbox.
- Khoảng cách radar hợp lý so với kích thước bbox.
- Bbox thuộc class `car`.
- Dữ liệu radar và camera không quá lệch timestamp.

## Đầu Ra Mong Muốn

`FusedTarget` nên có:

- `class_name`: ví dụ `car`.
- `bbox`: bbox trên ảnh.
- `distance_m`: từ radar.
- `relative_velocity_mps`: từ radar.
- `ttc_s`: từ radar.
- `confidence`: kết hợp confidence YOLO và radar track.

## Trạng Thái Hiện Tại

Fusion hiện đã có debug view để xem bbox và thông số radar. Bước tiếp theo là
biến fusion thành target chính thức cho AEB, đồng thời vẫn giữ radar-only làm
fallback khi camera/model mất detection.
