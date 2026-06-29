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
camera để chiếu điểm 3D lên ảnh 2D. Đây không phải là sử dụng ground truth để
ra quyết định, vì pipeline online chỉ dùng dữ liệu từ radar, camera, transform
cảm biến và kết quả YOLO.

## Phép Chiếu Hình Học

Ý tưởng toán học:

```text
p_radar = [x, y, z, 1]^T
p_world = T_world_ego * T_ego_radar * p_radar
p_camera = T_camera_world * p_world
```

Sau đó chiếu điểm 3D trong hệ camera lên mặt phẳng ảnh:

```text
u = fx * X / Z + cx
v = fy * Y / Z + cy
```

Trong đó:

- `(X, Y, Z)` là tọa độ điểm trong hệ camera.
- `(u, v)` là pixel trên ảnh.
- `fx, fy, cx, cy` là tham số nội tại camera.

Nếu `Z <= 0`, điểm nằm sau camera và bị loại. Nếu `(u, v)` nằm ngoài ảnh, điểm
không được dùng để ghép với YOLO.

## Association

Một radar object có thể được ghép với bbox nếu:

- Điểm chiếu nằm trong bbox hoặc gần tâm bbox.
- Khoảng cách radar hợp lý so với kích thước bbox.
- Bbox thuộc class `car`.
- Dữ liệu radar và camera không quá lệch timestamp.
- Nếu nhiều bbox thỏa mãn, ưu tiên bbox có tâm gần điểm chiếu hơn hoặc có độ tin
  cậy cao hơn.
- Nếu nhiều radar object nằm trong cùng bbox, ưu tiên object có TTC thấp hơn và
  đã được tracker xác nhận ổn định hơn.

## Đầu Ra Mong Muốn

`FusedTarget` nên có:

- `class_name`: ví dụ `car`.
- `bbox`: bbox trên ảnh.
- `distance_m`: từ radar.
- `relative_velocity_mps`: từ radar.
- `ttc_s`: từ radar.
- `confidence`: kết hợp confidence YOLO và radar track.

## Vai Trò Của Từng Cảm Biến

- Radar là nguồn chính cho khoảng cách, vận tốc tương đối và TTC.
- Camera/YOLO là nguồn chính để xác nhận vật thể là xe.
- Fusion giúp giảm phanh nhầm với lan can, cây, mặt đường hoặc xe ngoài hành
  lang dự kiến.
- Khi camera mất detection ngắn hạn, radar object đã tracking vẫn có thể làm
  fallback nhưng mức tin cậy thấp hơn.
- Khi YOLO thấy xe nhưng radar không có object hợp lệ, hệ thống không nên phanh
  mạnh vì thiếu thông tin khoảng cách/vận tốc đáng tin cậy.

## Trạng Thái Hiện Tại

Fusion đã được đưa vào final demo và smoke/final evidence. Radar-only vẫn được
giữ làm baseline/fallback, nhưng bản đánh giá cuối cùng dùng camera YOLO ONNX
kết hợp radar object pipeline để ra quyết định AEB.
