# Báo Cáo Mini: Xây Dựng Hệ Thống AEB Trên CARLA 0.9.11

> Bản mini dùng để đọc nhanh, duyệt bố cục và nội dung chính trước khi viết
> bản full theo mẫu báo cáo của trường. Nội dung được tổng hợp từ `docs/official/`,
> `docs/research/` và `docs/log/`.

## Chương 1. Mở Đầu

### 1.1. Lý Do Chọn Đề Tài

Hệ thống hỗ trợ lái nâng cao ADAS ngày càng phổ biến trên ô tô hiện đại. Trong
đó, AEB (Autonomous Emergency Braking) là chức năng an toàn chủ động quan trọng,
có nhiệm vụ cảnh báo và tự động phanh khi phát hiện nguy cơ va chạm phía trước.

Việc thử nghiệm AEB trên xe thật yêu cầu chi phí cao và có rủi ro an toàn. Vì
vậy, đề tài lựa chọn CARLA 0.9.11 để mô phỏng, xây dựng và kiểm thử một pipeline
AEB hoàn chỉnh trong môi trường có thể kiểm soát được.

### 1.2. Mục Tiêu Đề Tài

Mục tiêu của đề tài là xây dựng hệ thống AEB mô phỏng trên CARLA với xe ego
Tesla Model 3, sử dụng camera và radar phía trước để phát hiện nguy cơ va chạm
với ô tô phía trước. Hệ thống cần có khả năng:

- đọc dữ liệu từ radar và camera trong CARLA;
- xử lý radar thành object target thay vì phanh theo từng điểm đo đơn lẻ;
- dùng YOLO để nhận diện ô tô trong ảnh camera;
- kết hợp camera-radar fusion để xác nhận mục tiêu nguy hiểm;
- tính TTC, khoảng cách dừng và quyết định cảnh báo/phanh;
- kiểm thử bằng các kịch bản car-to-car trên cao tốc;
- lưu log, biểu đồ và video phục vụ đánh giá.

### 1.3. Phạm Vi Nghiên Cứu

Phạm vi hiện tại của project:

- Simulator: CARLA 0.9.11.
- Ego vehicle: `vehicle.tesla.model3`.
- Môi trường chính: cao tốc `Town04`.
- Đối tượng xét: ô tô phía trước, bài toán car-to-car.
- Thời tiết/môi trường: lý tưởng, chưa xét mưa, sương mù, đêm tối.
- Cảm biến: 1 camera RGB sau kính lái và 1 radar ở mũi xe.
- Dải vận tốc mục tiêu: ưu tiên 50-80 km/h, đồng thời test mở rộng để tìm giới
  hạn hệ thống.

## Chương 2. Cơ Sở Lý Thuyết Về ADAS Và AEB

### 2.1. Tổng Quan ADAS Và AEB

ADAS là nhóm hệ thống hỗ trợ người lái nhằm tăng an toàn và giảm tải thao tác.
AEB là một chức năng trong ADAS, có nhiệm vụ can thiệp khi hệ thống đánh giá
rằng xe đang có nguy cơ va chạm phía trước.

Một hệ thống AEB cơ bản cần trả lời ba câu hỏi:

1. Xe ego đang chuyển động như thế nào?
2. Vật thể phía trước ở đâu và có nằm trên quỹ đạo xe ego không?
3. Nếu tiếp tục di chuyển, sau bao lâu hoặc sau bao nhiêu mét sẽ va chạm?

### 2.2. Cảm Biến Trong AEB

Các cảm biến thường gặp trong ADAS/AEB gồm:

| Cảm biến | Vai trò chính | Nhận xét |
| --- | --- | --- |
| Camera | Nhận diện xe, làn đường, biển báo, người đi bộ | Mạnh về phân loại và hình dạng |
| Radar | Đo khoảng cách và vận tốc tương đối | Phù hợp bài toán car-to-car |
| LiDAR | Tạo point cloud 3D chính xác | Chi phí cao, thường gặp trong robot tự hành |
| Ultrasonic | Đo khoảng cách rất gần | Phù hợp parking |
| IMU/GNSS/wheel speed | Trạng thái chuyển động ego | Hỗ trợ dự đoán quỹ đạo |

Trong đề tài này, camera dùng để nhận diện ô tô, radar dùng để đo khoảng cách,
vận tốc tương đối và TTC.

### 2.3. TTC Và Khoảng Cách Dừng

TTC (Time To Collision) là thời gian còn lại trước va chạm nếu ego và target giữ
nguyên chuyển động tương đối:

```text
closing_speed = -relative_velocity
TTC = distance / closing_speed
```

TTC chỉ có ý nghĩa khi `closing_speed > 0`, tức target đang tiến lại gần ego theo
phương gây va chạm.

Ngoài TTC, AEB còn có thể dùng khoảng cách dừng yêu cầu:

```text
d_required =
  v_ego * t_response
  + v_ego^2 / (2 * a_ego)
  - v_target^2 / (2 * a_target)
  + safety_margin
```

Nếu khoảng cách hiện tại nhỏ hơn khoảng cách yêu cầu, hệ thống cần cảnh báo hoặc
phanh.

### 2.4. Repo Và Hệ Thống Tham Khảo

Project tham khảo tư duy thiết kế từ một số hệ thống mã nguồn mở:

| Nguồn | Ý tưởng chính | Bài học áp dụng |
| --- | --- | --- |
| Autoware | Predicted path, obstacle on path, stopping distance | Chỉ xét vật thể nằm trong hành lang/quỹ đạo dự kiến |
| openpilot | Radar track kết hợp lead từ vision | Radar tracking và camera xác nhận target |
| Apollo | Object-level perception và fusion | Chuẩn hóa object trước khi quyết định |

Điểm chung là không nên quyết định phanh từ một detection đơn lẻ. Hệ thống cần
có tầng trung gian:

```text
detection -> tracking/object -> risk assessment -> brake control
```

## Chương 3. Môi Trường Mô Phỏng Và Bài Toán Đề Xuất

### 3.1. CARLA 0.9.11

CARLA là simulator mã nguồn mở phục vụ nghiên cứu xe tự hành. CARLA cho phép
spawn xe, gắn cảm biến, tạo kịch bản giao thông và thu dữ liệu như camera, radar,
collision, vị trí actor.

Project đặt thư mục `aeb/` trực tiếp trong thư mục gốc CARLA:

```text
/home/mvhoang/CARLA_0.9.11/
├── CarlaUE4.sh
├── PythonAPI/
├── venv/
└── aeb/
```

Lệnh chạy CARLA ổn định trên máy hiện tại:

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Không dùng `-opengl` vì từng gây lỗi render Pygame/manual control.

### 3.2. Cấu Hình Máy Đã Test

| Thành phần | Cấu hình |
| --- | --- |
| OS | Ubuntu 22.04.5 LTS |
| CPU logical cores | 12 |
| RAM | 15 GiB |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU, 4 GiB VRAM |
| NVIDIA driver | 580.159.04 |
| Python CARLA | Python 3.7.17 |
| Python YOLO | Python 3.10 trong `.venv_yolo310` |

### 3.3. Bài Toán Mô Phỏng

Bài toán tập trung vào tình huống xe ego chạy trên cao tốc và gặp nguy cơ va
chạm với ô tô phía trước. Các kịch bản chính gồm:

- xe trước đứng yên;
- xe trước chạy chậm hơn;
- xe trước phanh gấp;
- xe làn bên nhập làn phía trước ego;
- đường trống để kiểm tra phanh nhầm;
- xe làn bên/decoy để kiểm tra chọn đúng target.

Các scenario lấy cảm hứng từ bài toán car-to-car của NCAP, nhưng project không
tuyên bố đây là bộ test chứng nhận NCAP chính thức.

### 3.4. Giới Hạn Của CARLA

CARLA radar không mô phỏng đầy đủ radar FMCW ngoài đời. Nó trả về các detection
point đã được engine mô phỏng sẵn, không có đầy đủ raw signal, Doppler map, CFAR
hay clutter như radar thật. Vì vậy project cần tự xây tầng clustering/tracking
để biến point thành object.

Ngoài ra, FPS video Pygame có thể dao động 17-18 FPS khi quay, nhưng khi chạy
synchronous mode với `fixed_delta_seconds = 0.05`, logic mô phỏng và log vẫn
được tính theo 20 Hz. Do đó kết quả đánh giá ưu tiên dựa trên log mô phỏng, không
dựa trên độ mượt video.

## Chương 4. Thiết Kế Hệ Thống AEB

### 4.1. Kiến Trúc Tổng Thể

Pipeline tổng thể:

```text
CARLA world
  -> ego vehicle + camera + radar
  -> radar processing / YOLO
  -> camera-radar fusion
  -> target selection
  -> TTC + stopping distance
  -> warning / brake decision
  -> CARLA VehicleControl override
  -> log + biểu đồ + video
```

Các module chính trong code:

| Thư mục | Vai trò |
| --- | --- |
| `configs/` | Cấu hình cảm biến, model, dataset, scenario |
| `control/` | Logic AEB và phanh |
| `core/` | Pipeline radar/AEB dùng chung |
| `perception/` | Xử lý cảm biến, radar object tracker |
| `scripts/` | Chạy batch, thu data, train, export, quay video |
| `ui/` | Giao diện camera, radar, YOLO, fusion, final demo |
| `tests/` | Unit test logic |

### 4.2. Cấu Hình Cảm Biến

Ego vehicle là `vehicle.tesla.model3`.

Camera:

| Thuộc tính | Giá trị |
| --- | --- |
| Loại | `sensor.camera.rgb` |
| Vị trí | Sau kính lái |
| Transform | `x=0.43`, `y=0.0`, `z=1.35` |
| FOV | 70 độ |
| Độ phân giải | 1280x720 |
| Sensor tick | 0.05 s, tương đương 20 FPS |

Radar:

| Thuộc tính | Giá trị |
| --- | --- |
| Loại | `sensor.other.radar` |
| Vị trí | Mũi xe |
| Transform | `x=2.53`, `y=0.0`, `z=0.48` |
| Range | 100 m |
| FOV ngang/dọc | 30 độ / 6 độ |
| Points per second | 2000 |
| Sensor tick | 0.05 s, tương đương 20 FPS |

Vị trí cảm biến được kiểm chứng bằng script `scripts/visualize_sensor_coverage.py`.
Các ảnh minh họa nằm trong `outputs/sensor_coverage/` nếu đã chạy script.

### 4.3. Xử Lý Radar

Ban đầu nếu tính TTC trực tiếp trên toàn bộ radar point, hệ thống dễ phanh nhầm
vì radar có thể thấy mặt đường, lan can, cây hoặc vật thể ngoài làn. Vì vậy
project chuyển sang hướng object-level:

```text
RadarMeasurement
  -> point trong hệ ego
  -> lọc range/độ cao/hành lang
  -> clustering theo vị trí và vận tốc
  -> tracking qua nhiều frame
  -> RadarObjectList
  -> chọn target nguy hiểm
```

Mỗi object radar có các thông tin chính:

- khoảng cách dọc;
- lệch ngang;
- vận tốc tương đối;
- TTC;
- số point trong cluster;
- trạng thái xác nhận qua nhiều frame.

Chỉ object đã xác nhận và nằm trong hành lang dự kiến của ego mới được dùng để
kích hoạt AEB.

### 4.4. Xử Lý Camera Và YOLO

Camera RGB đặt sau kính lái cung cấp ảnh cho YOLO. YOLO dùng để phát hiện class
`car` trong ảnh. Giai đoạn đầu project có thể dùng model YOLO26n có sẵn để kiểm
tra luồng camera/fusion. Sau đó, để model phù hợp hơn với góc nhìn CARLA, project
xây dựng dataset riêng và fine-tune YOLO26n cho một class `car`.

Model runtime hiện tại:

- `models/yolo26n_aeb_v7.pt`
- `models/yolo26n_aeb_v7.onnx`

YOLO không đo trực tiếp khoảng cách và vận tốc tương đối, nên trong hệ thống này
camera chủ yếu dùng để xác nhận target là ô tô, còn radar vẫn là nguồn chính cho
distance, relative velocity và TTC.

### 4.5. Camera-Radar Fusion

Fusion nhằm giảm nhược điểm của từng cảm biến:

- radar đo khoảng cách/vận tốc tốt nhưng point thưa và có thể nhiễu;
- camera nhận diện object tốt nhưng không đo trực tiếp vận tốc tương đối.

Project không dùng hàm CARLA có sẵn để biết điểm radar nằm ở pixel nào. Thay vào
đó, hệ thống dùng biến đổi hình học từ radar/ego/world/camera và ma trận nội tại
camera để chiếu radar object lên ảnh 2D. Nếu điểm chiếu của radar target nằm
trong YOLO bbox class `car`, target được xem là được camera xác nhận.

### 4.6. Logic AEB Và Phanh

State cơ bản:

| State | Ý nghĩa |
| --- | --- |
| `SAFE` / `NORMAL` | Không có nguy hiểm |
| `WARNING` | Có target nguy hiểm, hiển thị cảnh báo |
| `BRAKE` | Override throttle/brake |
| `RELEASE` | Nhả phanh khi an toàn hoặc hết nguy hiểm |

Project giữ nhiều chế độ phanh để so sánh:

| Chế độ | Mô tả |
| --- | --- |
| `binary` | Có nguy hiểm thì phanh 1.0 |
| `staged` | Chia tầng rủi ro, mỗi tầng có lực phanh cố định |
| `pid_v1` | PID điều khiển lực phanh |
| `pid_v2_comfort` | PID mềm hơn, giảm phanh nhầm |
| `staged_pid` | Chia tầng rủi ro kết hợp PID, bản chính hiện tại |

`staged_pid` được chọn làm bản chính tạm thời vì gần với tư duy AEB thực tế hơn:
cảnh báo trước, phanh nhẹ khi rủi ro tăng, phanh mạnh hoặc khẩn cấp khi nguy cơ
va chạm cao.

## Chương 5. Xây Dựng Dataset Và Kịch Bản Kiểm Thử

### 5.1. Dataset YOLO

Dataset được thu bằng ground truth CARLA:

```text
spawn ego + NPC
  -> camera RGB
  -> lấy bbox 3D actor từ CARLA
  -> chiếu bbox sang ảnh 2D
  -> lọc object không phù hợp
  -> ghi ảnh + label YOLO
```

Lý do dùng dataset riêng:

- góc nhìn camera sau kính lái trong CARLA khác dataset ngoài đời;
- cần model nhận diện tốt trong môi trường Town04;
- bài toán hiện tại chỉ cần class `car`.

Bộ dataset chính dùng cho train thử là `dataset_v7_same_lane`.

| Split | Ảnh | Box | Empty ratio | Session |
| --- | ---: | ---: | ---: | ---: |
| Train | 1505 | 1872 | 21.2% | 28 |
| Val | 300 | 379 | 16.3% | 6 |
| Test | 200 | 264 | 18.0% | 4 |

Dataset đạt quality gate trong script audit. Gallery kiểm tra label nằm ở
`outputs/dataset_v7_same_lane_box_check` nếu đã render.

### 5.2. Train Và Export YOLO

Luồng train tách thành các bước:

1. Audit dataset.
2. Train YOLO26n.
3. Export ONNX để dùng trong UI/runtime CARLA.

Các script chính:

```bash
.venv_yolo310/bin/python scripts/check_yolo_dataset.py
.venv_yolo310/bin/python scripts/train_yolo26n.py
.venv_yolo310/bin/python scripts/export_yolo26n_onnx.py
```

CARLA runtime dùng Python 3.7, còn YOLO/Ultralytics dùng Python 3.10 riêng để
tránh xung đột môi trường.

### 5.3. Kịch Bản Kiểm Thử

Scenario được chia thành các nhóm car-to-car:

| Nhóm | Ý nghĩa |
| --- | --- |
| `clear_road` | Đường trống, không được phanh nhầm |
| `ccrs` | Xe phía trước đứng yên |
| `ccrm` | Xe phía trước chạy chậm hơn |
| `ccrb` | Xe phía trước phanh gấp |
| `cut_in` | Xe làn bên nhập làn trước ego |
| `cut_out` | Xe phía trước rời làn |
| `adjacent_vehicle` | Xe làn bên, kiểm tra phanh nhầm |
| `curve_cases` | Đường cong, kiểm tra hành lang dự kiến |
| `multi_actor` | Nhiều xe, kiểm tra chọn đúng target |

Tiêu chí PASS/FAIL:

- Scenario nguy hiểm: PASS nếu AEB phanh và không va chạm.
- Scenario không nguy hiểm: PASS nếu không phanh sai.
- Với bài test giới hạn, FAIL được giữ lại để xác định dải hoạt động của hệ
  thống, không xóa để làm đẹp báo cáo.

### 5.4. Log, Biểu Đồ Và Video

Mỗi scenario có thể sinh:

- CSV log theo từng tick;
- summary CSV/JSON;
- biểu đồ brake profile;
- video demo Pygame 3 màn;
- thumbnail kiểm tra video không bị đen.

Log final hiện nằm ở:

```text
logs/final_evidence_staged_pid_20260628
```

Video final hiện nằm ở:

```text
outputs/scenario_videos/final_evidence_videos_20260628_internal
```

## Chương 6. Kết Quả Và Đánh Giá

### 6.1. Kết Quả Final Staged PID

Batch final dùng:

- perception/fusion: YOLO ONNX + radar object pipeline;
- phanh: `staged_pid`;
- scenario config: `configs/scenarios/suites/system_limit_extended_sweep.yaml`.

Kết quả tổng:

| Tổng case | PASS | FAIL | Missing | Pass rate |
| ---: | ---: | ---: | ---: | ---: |
| 66 | 63 | 3 | 0 | 95.45% |

Kết quả theo nhóm:

| Nhóm | Tổng case | PASS | FAIL |
| --- | ---: | ---: | ---: |
| `ccrm` | 24 | 24 | 0 |
| `ccrb` | 30 | 28 | 2 |
| `cutin` | 12 | 11 | 1 |

### 6.2. Các Case Fail Và Giới Hạn Hệ Thống

| Scenario | Collision | Min gap | Nhận xét |
| --- | ---: | ---: | --- |
| `ccrb_95_gap_20` | True | 0.0134 m | Xe trước phanh gấp, tốc độ cao, khoảng cách đầu nhỏ |
| `ccrb_110_gap_20` | True | 0.0806 m | Vượt dải vận tốc/khoảng cách an toàn của hệ thống |
| `cutin_100_60_gap_25` | True | 0.4763 m | Xe nhập làn ở tốc độ cao và gap nhỏ |

Các case fail này giúp xác định giới hạn hệ thống. Với mục tiêu hiện tại là cao
tốc, only-car, thời tiết lý tưởng, hệ thống hoạt động tốt hơn ở dải 50-80 km/h
và khoảng cách đủ lớn. Khi tốc độ tăng lên 95-110 km/h hoặc gap ban đầu quá nhỏ,
radar range 100 m và giới hạn điều khiển phanh khiến hệ thống không còn đảm bảo
tránh va chạm trong mọi trường hợp.

### 6.3. Video Demo

Các video demo đại diện:

| Scenario | Ý nghĩa | File |
| --- | --- | --- |
| `clear_road_50` | Đường trống, không phanh nhầm | `outputs/scenario_videos/final_evidence_videos_20260628_internal/clear_road_50.mp4` |
| `ccrs_80_gap_30` | Xe đứng yên phía trước, pass | `outputs/scenario_videos/final_evidence_videos_20260628_internal/ccrs_80_gap_30.mp4` |
| `ccrb_95_gap_20` | Xe trước phanh gấp, fail/giới hạn | `outputs/scenario_videos/final_evidence_videos_20260628_internal/ccrb_95_gap_20.mp4` |
| `cutin_80_50_gap_25` | Cut-in pass | `outputs/scenario_videos/final_evidence_videos_20260628_internal/cutin_80_50_gap_25.mp4` |
| `cutin_100_60_gap_25` | Cut-in fail/giới hạn | `outputs/scenario_videos/final_evidence_videos_20260628_internal/cutin_100_60_gap_25.mp4` |

Video được ghi trực tiếp từ frame Pygame bằng internal recorder, không dùng
x11grab, nên tránh lỗi video đen. Video dùng để minh họa, còn đánh giá định
lượng dựa trên log CSV.

### 6.4. Nhận Xét Về Độ Tin Cậy Kết Quả

Khi chạy synchronous mode:

- simulation backend dùng `fixed_delta_seconds = 0.05`, tương đương 20 Hz;
- Pygame/video frontend có thể chỉ hiển thị 17-18 FPS do render/record nặng;
- kết quả đánh giá lấy từ `sim_time_s`, `elapsed_s`, gap, TTC và collision trong
  log, không lấy từ FPS video.

Jerk trong log là `CARLA raw jerk`, tính từ gia tốc raw theo từng tick. Giá trị
này dùng để so sánh tương đối giữa các chế độ phanh trong cùng môi trường mô
phỏng, không coi là jerk tuyệt đối của xe thật.

## Chương 7. Kết Luận Và Hướng Phát Triển

### 7.1. Kết Quả Đạt Được

Project đã xây dựng được một pipeline AEB mô phỏng tương đối đầy đủ:

- cấu hình ego Tesla Model 3, camera và radar;
- xử lý radar từ point-level sang object-level;
- train model YOLO một class `car` cho môi trường CARLA;
- có camera-radar fusion để xác nhận target;
- có nhiều chế độ phanh và chọn `staged_pid` làm bản chính hiện tại;
- có scenario batch, log, biểu đồ và video evidence;
- chạy final 66 scenario với kết quả 63 PASS, 3 FAIL, pass rate 95.45%.

### 7.2. Hạn Chế

- CARLA radar chưa giống radar FMCW thật ngoài đời.
- Dải thử nghiệm còn tập trung vào cao tốc, ô tô, thời tiết lý tưởng.
- Radar range 100 m là giới hạn đáng kể ở tốc độ cao.
- YOLO mới train cho class `car`, chưa xét pedestrian, cyclist.
- Controller phanh vẫn là mô phỏng, chưa có đầy đủ actuator delay/ABS/tire model
  như xe thật.
- CARLA 0.9.11 có thể không ổn định khi chạy nhiều scenario liên tục, nên project
  đã bổ sung reload/restart world/server để tăng độ bền khi test.

### 7.3. Hướng Phát Triển

- Tối ưu staged PID để phanh mượt hơn và giảm jerk raw.
- Làm fusion chính thức hơn với `FusedTarget` ổn định qua thời gian.
- Mở rộng dataset cho nhiều map, ánh sáng, thời tiết và góc nhìn.
- Thêm pedestrian/cyclist nếu mở rộng ngoài bài toán car-to-car.
- Thêm mô hình phanh thực tế hơn, có delay và giới hạn jerk.
- Chuẩn hóa bộ test gần hơn với NCAP/ISO nếu cần đánh giá nghiêm ngặt hơn.

## Tài Liệu Và Artifact Tham Khảo Nội Bộ

- Tổng quan project: `docs/official/00_PROJECT_INTRODUCTION.md`
- Kiến trúc hệ thống: `docs/official/01_SYSTEM_ARCHITECTURE.md`
- Cấu hình cảm biến: `docs/official/02_SENSOR_CONFIGURATION.md`
- Xử lý radar: `docs/official/03_RADAR_PROCESSING.md`
- Camera/YOLO: `docs/official/04_CAMERA_YOLO_PROCESSING.md`
- Fusion: `docs/official/05_CAMERA_RADAR_FUSION.md`
- AEB và phanh: `docs/official/06_AEB_DECISION_AND_BRAKING.md`
- Scenario/validation: `docs/official/07_SCENARIOS_AND_VALIDATION.md`
- Dataset/training: `docs/official/08_DATASET_AND_TRAINING.md`
- Nền tảng ADAS/AEB: `docs/research/00_ADAS_AEB_BACKGROUND.md`
- So sánh repo: `docs/research/07_REPO_COMPARISON_SUMMARY.md`
- Evidence final: `docs/log/FINAL_EVIDENCE_PACK_20260628.md`
- Nhật ký thử nghiệm: `docs/log/EXPERIMENT_LOG.md`

