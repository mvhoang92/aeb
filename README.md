# AEB CARLA 0.9.11

Dự án AEB mới cho CARLA 0.9.11. Bản cũ đã được chuyển sang `aeb_old2/`.

Mục tiêu của bản mới là xây dựng hệ thống AEB có giao diện giống
`PythonAPI/examples/manual_control.py`, sau đó mở rộng thêm camera, radar,
sensor fusion, TTC và điều khiển phanh.

## Yêu Cầu Thiết Kế

- Ego vehicle: `vehicle.tesla.model3`.
- Môi trường chính: cao tốc trên `Town04`.
- Đối tượng test: chỉ ô tô, chưa ưu tiên pedestrian/intersection.
- Sensor:
  - 1 camera RGB đặt sau kính lái.
  - 1 radar đặt ở mũi xe.
- Sensor fusion:
  - Camera dùng để xác nhận xe/vật cản phía trước.
  - Radar cung cấp distance và relative velocity.
  - Fusion target được dùng để tính TTC.
- TTC/AEB:
  - TTC thấp thì cảnh báo/phanh.
  - Ban đầu phanh nhị phân: `brake = 1.0` hoặc `brake = 0.0`.
  - Sau khi baseline ổn định sẽ thay bằng PID brake controller.
- Giao diện:
  - Bên trái giữ nguyên manual control của CARLA.
  - Bên phải là góc nhìn camera AEB sau kính lái.
  - Code nên coi như extend từ `manual_control.py`, không viết lại manual UI từ đầu.
- Test:
  - Chạy các case inspired by NCAP, không tuyên bố đạt/chứng nhận NCAP chính thức.
  - Các case cần có sau này: CCRs, CCRm, CCRb, adjacent lane, cut-in.

## Trạng Thái Hiện Tại

Đã có:

- `configs/camera.yaml`: config ego, display và camera sau kính lái.
- `configs/sensors.yaml`: config chung cho camera, radar, model và fusion.
- `test_cam.py`: mở rộng `manual_control.py` thành cửa sổ 2 panel:
  - Trái: manual control gốc của CARLA.
  - Phải: camera AEB sau kính lái.
- `test_radar.py`: bên trái manual control, bên phải bird-eye view hiển thị tầm quét radar.
- `test_brake_radar.py`: test phanh radar-only bằng TTC và binary brake `0/1`.
- `test_model.py`: bên trái manual control, bên phải camera AEB + YOLO bbox.
- `test_fusion.py`: bên trái manual control, bên phải camera AEB + bbox + thông số radar.
- `two_panel_common.py`: helper dùng chung để các script bên trên giữ nguyên manual control ở nửa trái.
- `control/brake.py`: logic TTC, BinaryAEB và helper override phanh CARLA.
- `core/radar_aeb_pipeline.py`: pipeline dùng chung cho UI và batch test,
  gồm lọc point, predicted path, clustering, tracking và chọn target.
- `radar_cluster.py`: gom radar point thành cụm, theo dõi cụm qua nhiều frame
  và chỉ xác nhận target ổn định cho AEB.
- `run_radar_aeb_scenarios.py`: tự chạy batch scenario radar AEB và sinh log.
- `collect_ground_truth_data.py`: tự thu ảnh camera, chiếu bounding box 3D
  ground truth của CARLA và tạo nhãn YOLO một class `car`.
- `docs/TEST_SCENARIOS.md`: mô tả toàn bộ file test, kịch bản và cấu trúc log.
- `docs/RADAR_AEB_RESEARCH.md`: tổng hợp cách hãng xe, nhà cung cấp và các repo
  tự hành xử lý nhiễu radar, tracking target và quyết định phanh AEB.
- `docs/ADAS_AEB_RESEARCH.md`: Phần I của báo cáo, gồm cơ sở lý thuyết
  ADAS/AEB, cảm biến, thuật toán đánh giá nguy cơ và điều khiển phanh, cách tiếp
  cận công khai của các hãng, Autoware/Apollo/openpilot/Nav2 và tiêu chuẩn.
- `docs/ADAS_AEB_SLIDE_PROMPT.md`: prompt tạo bộ slide báo cáo ADAS/AEB 17
  trang, speaker notes và prompt tạo các ảnh minh họa phù hợp.
- `docs/DATA_COLLECTION.md`: hướng dẫn thu dataset train/val, cấu trúc label,
  đồng bộ RGB/depth/semantic và traffic được collector tự sinh.
- `docs/MODEL_TRAINING.md`: audit dataset, tự train/test YOLO26n, export ONNX
  CUDA và quality gate trước khi thay model demo.

Chưa có trong bản mới:

- Phanh PID.
- AEB dùng target đã được camera-radar fusion xác nhận.
- Model YOLO được train lại bằng dataset ground truth riêng của dự án.
- Bộ scenario rộng hơn để thống kê false-positive/missed detection ở nhiều
  tốc độ, đường cong, cut-in và điều kiện che khuất.
- Quy trình scenario và metric bám sát tiêu chuẩn NCAP chính thức.

## Cách Chạy CARLA

Từ thư mục gốc CARLA:

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Lệnh trên dùng NVIDIA offload và mức chất lượng Low để giảm tải GPU.
`-quality-level=Low` đã chạy ổn với cửa sổ pygame/manual control trên máy hiện
tại. Không thêm cờ `-opengl`, vì cờ này mới là nguyên nhân làm cửa sổ pygame,
manual control hoặc camera render lỗi.

## Cách Chạy Test Camera

Mở terminal thứ hai sau khi CARLA server đã load xong:

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python aeb/test_cam.py
```

Bật autopilot ngay từ đầu:

```bash
venv/bin/python aeb/test_cam.py -a
```

Cửa sổ mặc định gồm 2 panel, mỗi panel `1280x720` giống `manual_control.py`.
Nếu máy nặng hoặc cửa sổ quá rộng, có thể giảm kích thước:

```bash
venv/bin/python aeb/test_cam.py --res 960x540
```

Chọn map khác nếu cần:

```bash
venv/bin/python aeb/test_cam.py --map-name Town04
```

## Cách Chạy Test Radar

Panel bên trái vẫn là `manual_control.py`. Panel bên phải là bird-eye view:
ego ở phía dưới, quạt radar hướng lên trước, radar point đổi màu theo mức nguy
hiểm TTC.

Quy ước màu: đỏ là `TTC <= brake_ttc_s`, xanh dương là
`TTC <= warning_ttc_s`, xanh lá là an toàn hoặc TTC vô hạn. TTC chỉ hữu hạn khi
vận tốc tương đối âm.

```bash
venv/bin/python aeb/test_radar.py
```

Nếu cần giảm kích thước cửa sổ:

```bash
venv/bin/python aeb/test_radar.py --res 960x540
```

## Cách Chạy Test Phanh Radar-Only

Script này dùng radar target phía trước để tính TTC. Target phanh không còn là
một radar point đơn lẻ. Pipeline hiện tại:

1. Lọc point theo tầm radar, độ cao so với mặt đường và hành lang quỹ đạo ego.
2. Gom các point gần nhau và có vận tốc tương đối gần nhau thành cluster.
3. Theo dõi cluster giữa các frame radar.
4. Chỉ cluster có ít nhất `min_points` và xuất hiện liên tiếp đủ
   `confirm_frames` mới được xác nhận.
5. Track bị mất point dù chỉ một frame sẽ mất quyền kích hoạt AEB; khi xuất
   hiện lại phải xác nhận đủ `confirm_frames`.
6. Chọn cluster mới, đã xác nhận và có TTC thấp nhất làm target AEB.
7. Phanh khi TTC thấp hơn `brake_ttc_s` hoặc khoảng cách thực tế nhỏ hơn
   khoảng cách dừng yêu cầu.
8. Khi phanh, AEB tạm thời override xe:

```text
throttle = 0.0
brake = 1.0
```

Chạy với autopilot để ego tự chạy, AEB chỉ can thiệp khi nguy hiểm:

```bash
venv/bin/python aeb/test_brake_radar.py -a
```

Ngưỡng phanh nằm trong `configs/sensors.yaml`:

```yaml
brake:
  warning_ttc_s: 3.0
  brake_ttc_s: 1.5
  release_ttc_s: 3.5
  max_lateral_offset_m: 1.25
  min_radar_z_up_m: -0.35
  max_radar_z_up_m: 2.5
  min_height_above_road_m: 0.20
  path_horizon_time_s: 2.5
  path_min_horizon_m: 12.0
  path_max_lateral_deviation_m: 6.0
  hold_brake_until_stopped: true
  release_speed_mps: 0.3
  use_stopping_distance: true
  response_time_s: 0.20
  ego_emergency_decel_mps2: 8.0
  target_emergency_decel_mps2: 6.0
  stopping_distance_offset_m: 1.0
  full_brake: 1.0
```

Config gom cụm và xác nhận radar:

```yaml
radar_cluster:
  tolerance_m: 1.0
  velocity_tolerance_mps: 2.0
  vertical_tolerance_m: 1.5
  min_points: 2
  confirm_frames: 3
  release_frames: 4
  match_distance_m: 2.5
  match_velocity_mps: 3.0
  distance_percentile: 0.20
  min_max_height_above_road_m: 0.25
  prediction_enabled: true
  max_prediction_time_s: 0.30
```

Ý nghĩa chính:

- `tolerance_m`: khoảng cách tối đa để hai point được nối vào cùng một cluster.
- `velocity_tolerance_mps`: chênh lệch vận tốc tương đối tối đa trong cluster.
- `min_points`: số point tối thiểu của một cluster. CARLA radar khá thưa nên
  baseline đặt là `2`.
- `confirm_frames`: cluster phải được nhận liên tiếp bao nhiêu frame trước khi
  có quyền kích hoạt AEB.
- `release_frames`: số frame mất dấu trước khi xóa track đã có.
- Track mất dấu được giữ lại ngắn hạn để ghép lại, nhưng bị đánh dấu stale và
  không được chọn làm target AEB. Sau khi ghép lại, track phải xác nhận lại.
- `prediction_enabled`: dự đoán vị trí dọc ngắn hạn bằng vận tốc tương đối để
  ghép cluster ổn định hơn giữa hai frame radar.
- `distance_percentile`: lấy percentile thấp của khoảng cách point làm khoảng
  cách vật cản, ổn định hơn lấy đúng point gần nhất nhưng vẫn thiên về mặt gần
  ego của vật thể.
- `min_max_height_above_road_m`: cluster phải có ít nhất một point đủ cao hơn
  mặt đường để giảm cluster do mặt đường sinh ra.

Trong `test_brake_radar.py`, hai đường màu vàng biểu diễn hành lang va chạm
phía trước ego. Hành lang này cong theo quỹ đạo dự đoán từ vận tốc, yaw-rate và
lệnh đánh lái của ego. Chiều dài hành lang được giới hạn theo vận tốc
`speed * path_horizon_time_s`, đồng thời bị chặn bởi tầm radar và độ lệch ngang
tối đa. Point có TTC thấp nhưng nằm ngoài hành lang chỉ được hiển thị để debug
và không được chọn làm target phanh. Bộ lọc độ cao riêng trong
`brake` loại point mặt đường khỏi quyết định phanh nhưng không ẩn chúng trên UI.
Các point bị nhận diện là mặt đường được vẽ màu xám trong
`test_brake_radar.py`. Giá trị `min_height_above_road_m` được tính từ tọa độ
world của radar point đến độ cao waypoint làn đường gần nhất, nên vẫn hoạt động
khi đường lên hoặc xuống dốc.

Trên bird-eye của `test_brake_radar.py`:

- Dot nhỏ: radar point thô.
- Point xám: point mặt đường bị AEB bỏ qua.
- Vòng vàng: cluster đang chờ xác nhận đủ frame.
- Tâm có màu TTC và viền sáng: cluster đã xác nhận.
- Vòng trắng lớn: cluster đang được chọn làm target AEB.
- Icon `!` vàng: hệ thống phát tín hiệu cảnh báo va chạm trước FCW.
- Icon `!` đỏ: AEB đã chuyển sang trạng thái phanh khẩn cấp.

Icon này là HMI mô phỏng trong CARLA. Khi triển khai trên xe, cùng tín hiệu
trạng thái có thể được đưa lên màn hình cụm đồng hồ hoặc màn hình trung tâm và
kết hợp cảnh báo âm thanh; phần âm thanh chưa nằm trong phạm vi prototype này.

FCW và phanh dùng hai ngưỡng khác nhau: icon vàng bắt đầu ở
`warning_ttc_s = 3,0 s`, còn AEB chỉ phanh ở `brake_ttc_s = 1,5 s` hoặc khi
không còn đủ khoảng cách dừng. Cách tách này cho phép cảnh báo sớm nhưng tránh
để xe phanh quá nhạy.

Đây vẫn là phanh nhị phân, nhưng quyết định đã kết hợp TTC và khoảng cách dừng:

```text
d_required =
  v_ego * response_time
  + v_ego^2 / (2 * a_ego)
  - v_target^2 / (2 * a_target)
  + safety_offset
```

`distance_margin = target_distance - d_required`. Margin nhỏ hơn hoặc bằng
không sẽ kích hoạt phanh ngay cả khi TTC chưa chạm ngưỡng. Đây là baseline
stopping-distance đơn giản, chưa phải triển khai RSS đầy đủ.

Với `hold_brake_until_stopped: true`, sau khi AEB đã vào trạng thái `BRAKE`,
binary brake được giữ cho tới khi tốc độ ego nhỏ hơn `release_speed_mps`. Điều
này tránh trường hợp TTC tăng trong lúc giảm tốc làm AEB nhả phanh rồi xe tăng
tốc trở lại trước vật cản.

## Cơ Sở Thiết Kế Radar AEB

Thiết kế hiện tại tham khảo cách các hệ thống mã nguồn mở xử lý point cloud và
radar, sau đó giảm quy mô cho phù hợp với radar thưa của CARLA 0.9.11:

- [Autoware AEB](https://autowarefoundation.github.io/autoware_universe/main/control/autoware_autonomous_emergency_braking/):
  tạo predicted path, crop point theo footprint ego, Euclidean clustering, lọc
  chiều cao cluster, giữ lịch sử obstacle và so sánh với khoảng cách phanh.
- [openpilot radard.py](https://github.com/commaai/openpilot/blob/master/selfdrive/controls/radard.py):
  duy trì radar track, lọc trạng thái vận tốc và ghép radar-camera theo khoảng
  cách, lateral position và vận tốc; code cũng ghi rõ stationary radar point có
  thể là false positive.
- [CARLA issue #4974](https://github.com/carla-simulator/carla/issues/4974):
  ghi nhận radar có thể trả về ground hit hoặc vận tốc/range không nhất quán.
- [CARLA issue #6674](https://github.com/carla-simulator/carla/issues/6674):
  thảo luận giới hạn của radar CARLA dựa trên các raycast phân bố ngẫu nhiên.

Các giá trị `min_points: 2` và `tolerance_m: 1.0` không sao chép trực tiếp từ
Autoware. Đây là baseline riêng cho CARLA vì mỗi vật thể thường chỉ có ít radar
point. Khi có log scenario thực tế, cần đánh giá lại precision, false brake và
missed detection trước khi chốt tham số cho báo cáo.

## Cách Chạy Test Model YOLO

Panel bên phải là camera sau kính lái và bbox từ YOLO26n. Runtime mặc định dùng
ONNX Runtime với `CUDAExecutionProvider`.

```bash
venv/bin/python aeb/test_model.py
```

Model đã được tải và export sẵn:

```text
aeb/models/yolo26n.pt
aeb/models/yolo26n.onnx
```

Trong CARLA runtime, script dùng file ONNX:

```text
aeb/models/yolo26n.onnx
```

File `.pt` giữ lại để export lại khi cần. Vì CARLA 0.9.11 dùng Python 3.7,
runtime ưu tiên ONNX thay vì gọi trực tiếp Ultralytics/PyTorch.

## Thu Dataset Ground Truth Cho YOLO

Dataset giai đoạn đầu dùng một class:

```text
0 = car
```

Collector tự spawn traffic, chạy synchronous mode, lưu ảnh RGB sạch, label
YOLO, preview có box và metadata. Bounding box 3D được chiếu lên ảnh, sau đó
semantic segmentation và depth cùng frame được dùng để bỏ ghost box và siết
box vào pixel xe nhìn thấy. Cấu hình hiện ưu tiên 10 xe cùng làn phía trước,
lọc xe bị che nhiều và lấy mẫu cách ngẫu nhiên 5-10 simulation frame.

Thu train:

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python aeb/collect_ground_truth_data.py \
  --split train \
  --session-id town04_train_01 \
  --seed 2026 \
  --max-samples 2000
```

Mỗi session dùng một tên riêng. Nếu session bị dừng giữa chừng và config không
đổi, thêm `--resume`; nếu muốn thu lượt mới, đổi sang `town04_train_02`.

Chi tiết về config, validation split, visibility và cấu trúc dataset nằm tại
[`docs/DATA_COLLECTION.md`](docs/DATA_COLLECTION.md).

Khi đã thu đủ train/val/test, chạy watcher để tự audit, train, test và export:

```bash
python3 aeb/model_pipeline.py --watch
```

Chi tiết quality gate và quy trình triển khai model nằm tại
[`docs/MODEL_TRAINING.md`](docs/MODEL_TRAINING.md).

## Cách Chạy Test Fusion

Panel bên phải là camera sau kính lái, bbox từ YOLO và thông số radar. Khi radar
point project vào trong bbox, label sẽ có thêm:

```text
d=<distance>m rv=<relative_velocity>m/s ttc=<ttc>s
```

Chạy:

```bash
venv/bin/python aeb/test_fusion.py
```

Nếu chưa có YOLO, script vẫn hiển thị camera và các điểm radar project lên ảnh,
nhưng chưa có bbox từ model.

## Phím Điều Khiển

Panel bên trái dùng phím của `manual_control.py`:

- `W`/mũi tên lên: ga.
- `S`/mũi tên xuống: phanh.
- `A`/mũi tên trái: rẽ trái.
- `D`/mũi tên phải: rẽ phải.
- `P`: bật/tắt autopilot.
- `TAB`: đổi vị trí camera manual-control bên trái.
- `` ` `` hoặc `N`: đổi sensor manual-control bên trái.
- `F1`: bật/tắt HUD.
- `H` hoặc `?`: help.
- `ESC`: thoát.

## Config Camera

File config camera riêng cho `test_cam.py`:

```text
aeb/configs/camera.yaml
```

File config chung cho `test_radar.py`, `test_model.py` và `test_fusion.py`:

```text
aeb/configs/sensors.yaml
```

Camera sau kính lái hiện đặt tại:

```yaml
image_size_x: 1280
image_size_y: 720
location:
  x: 0.8
  y: 0.0
  z: 1.55
rotation:
  pitch: 0.0
  yaw: 0.0
  roll: 0.0
fov: 70
sensor_tick: 0.05
```

Nếu góc nhìn cam chưa đúng ý, ưu tiên chỉnh các tham số `x`, `z`, `pitch`,
và `fov` trong `driver_camera`.

## Hướng Làm Tiếp Theo

1. Mở rộng batch repeat sang đường cong, cut-in, nhiều xe và nhiều mức tốc độ.
2. Chạy các case nguy hiểm bằng `physics` mode và hiệu chỉnh bộ giữ tốc độ.
3. Dùng camera/YOLO xác nhận class và vùng ảnh trước khi cho target radar kích
   hoạt AEB ở tốc độ cao.
4. Sau khi target selection ổn định, thay binary brake bằng PID.
5. Bổ sung quy trình và metric bám sát tài liệu NCAP chính thức.

## Batch Test Và Log

Chạy toàn bộ kịch bản radar AEB tự động:

```bash
python3.7 aeb/run_radar_aeb_scenarios.py
```

Chạy lặp mỗi scenario:

```bash
python3.7 aeb/run_radar_aeb_scenarios.py --repeat 5
```

Chạy bằng throttle/brake vật lý thay vì ép vận tốc:

```bash
python3.7 aeb/run_radar_aeb_scenarios.py --control-mode physics
```

Kết quả được ghi vào `aeb/logs/<run_id>/`. Xem mô tả từng scenario, tiêu chí
PASS/FAIL và ý nghĩa từng cột log tại
[`docs/TEST_SCENARIOS.md`](docs/TEST_SCENARIOS.md).

Bộ kiểm tra sau khi giảm độ nhạy phanh nằm tại:

```text
aeb/logs/less_sensitive_20260605/
```

Kết quả là `5/5 PASS`. Bài repeat chọn lọc tại
`aeb/logs/less_sensitive_repeat_20260605/` đạt `6/6 PASS`: hai lần đường trống, hai
lần CCRs và hai lần xe đứng ở làn bên cạnh. Đây vẫn chưa phải chứng nhận NCAP.
