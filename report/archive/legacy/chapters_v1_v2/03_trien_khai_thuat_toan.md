# Chương 3. Triển Khai Thuật Toán AEB

Chương này trình bày pipeline thuật toán của hệ thống AEB: xử lý radar, xử lý
camera bằng YOLO, hợp nhất dữ liệu, chọn mục tiêu, tính TTC/khoảng cách dừng,
đánh giá mức nguy hiểm và điều khiển phanh bằng thuật toán PID. Phần thu dữ liệu v7 same-lane, huấn luyện và
đánh giá mô hình YOLO cũng được đưa vào chương này vì đây là một phần của thuật
toán nhận thức camera.

## 3.1. Quy Trình Phát Triển Và Lựa Chọn Phương Án Cuối

Hệ thống AEB trong đồ án không được xây dựng ngay từ phiên bản cuối cùng, mà
được phát triển theo từng bước để kiểm chứng từng khối chức năng. Cách làm này
giúp phát hiện lỗi sớm: trước khi đánh giá thuật toán phanh, cần chắc chắn giao
diện quan sát đúng; trước khi dùng fusion, cần kiểm tra radar và camera riêng;
trước khi dùng PID, cần có baseline phanh đơn giản để so sánh.

**Bảng 3.1: Quy trình phát triển hệ thống AEB trong đồ án.**

| Giai đoạn | Mục tiêu | Kết quả/Rút kinh nghiệm |
|---|---|---|
| Mở rộng `manual_control.py` | Giữ giao diện lái/quan sát gốc của CARLA, thêm cửa sổ phụ cho camera/radar | Tạo nền tảng debug trực quan, tránh mất khả năng quan sát như ví dụ gốc |
| Gắn camera và radar lên Tesla Model 3 | Kiểm tra vị trí camera sau kính lái và radar ở mũi xe | Phát hiện và chỉnh nhiều lần vị trí cảm biến bằng side view/top-down view |
| Chạy YOLO26n ban đầu | Kiểm tra khả năng nhận diện xe từ camera trước khi huấn luyện riêng | YOLO pretrained chạy được nhưng chưa tối ưu cho góc nhìn, môi trường và dữ liệu CARLA của dự án |
| Radar-only AEB | Xây dựng baseline chỉ dùng radar để tính mục tiêu, TTC và phanh | Phát hiện vấn đề phanh nhầm do điểm radar từ mặt đường, lan can, xe làn bên |
| Xử lý radar ở mức đối tượng | Lọc điểm, gom cụm, theo dõi và chọn mục tiêu ổn định | Giảm nhiễu radar, chuyển từ điểm đo rời rạc sang danh sách đối tượng |
| Thu bộ dữ liệu v7 và fine-tune YOLO26n | Tạo mô hình nhận diện `car` phù hợp với camera của dự án | YOLO sau fine-tuning dùng để xác nhận mục tiêu trong fusion |
| Fusion camera-radar | Ghép radar object với bounding box camera bằng chiếu hình học | Radar giữ vai trò đo khoảng cách/vận tốc, camera xác nhận mục tiêu là xe |
| Binary brake | Có nguy hiểm thì phanh 1.0 | Dễ kiểm chứng nhưng phanh gắt, chưa giống hành vi thực tế |
| PID v1/v2 | Điều khiển lực phanh liên tục theo sai số khoảng cách | Êm hơn binary nhưng cần tầng trạng thái để kiểm soát rủi ro và nhả phanh hợp lý |
| Staged PID cuối cùng | Kết hợp mức rủi ro SAFE/WARNING/SOFT/HARD/EMERGENCY với PID | Phương án chính dùng trong kiểm thử cuối cùng |

Qua các bước trên, thuật toán cuối cùng được chốt theo hướng: radar là nguồn đo
động học chính, camera/YOLO xác nhận mục tiêu, quỹ đạo ego dùng để loại vật thể
ngoài đường đi, TTC/khoảng cách dừng dùng để đánh giá nguy hiểm và staged PID
điều khiển lực phanh. Các bản phanh trước đó vẫn được giữ trong dự án để làm
mốc so sánh khi đánh giá. Các mục tiếp theo của chương này tập trung mô tả bản
thuật toán cuối cùng.

## 3.2. Kiến Trúc Thuật Toán Tổng Thể

Về bản chất, AEB là một hệ thống điều khiển an toàn theo vòng kín: cảm biến quan
sát môi trường, thuật toán nhận thức xác định mục tiêu, khối đánh giá rủi ro
tính khả năng va chạm, bộ điều khiển tạo lệnh phanh, sau đó trạng thái xe thay
đổi và hệ thống tiếp tục cập nhật ở chu kỳ tiếp theo.

Một hệ thống AEB cần trả lời ba câu hỏi chính:

1. Ego đang chạy với vận tốc và gia tốc như thế nào?
2. Vật thể phía trước có nằm trên đường đi dự kiến của ego không?
3. Nếu giữ trạng thái hiện tại, còn bao lâu hoặc còn bao nhiêu mét trước khi va
   chạm?

Trong đồ án, pipeline được tổ chức như sau:

```text
CARLA world
  -> ego vehicle + camera + radar
  -> xử lý đối tượng radar
  -> phát hiện xe bằng YOLO
  -> hợp nhất dữ liệu camera-radar
  -> lựa chọn mục tiêu
  -> TTC + stopping distance
  -> AEB state + staged PID
  -> VehicleControl override
  -> nhật ký dữ liệu + biểu đồ + video
```

![Kiến trúc chức năng của hệ thống AEB](../assets/aeb_functional_architecture.svg)

**Hình 3.1: Kiến trúc chức năng của hệ thống AEB.**

**Bảng 3.2: Các module chính trong mã nguồn.**

| Thư mục | Vai trò |
|---|---|
| `configs/` | Cấu hình cảm biến, bộ dữ liệu, mô hình, kịch bản |
| `control/` | Logic phanh, trạng thái AEB, PID/staged PID |
| `core/` | Các quy trình xử lý chính dùng chung |
| `perception/` | Xử lý radar, bộ theo dõi, hợp nhất dữ liệu cảm biến |
| `scripts/` | Thu bộ dữ liệu, huấn luyện, xuất ONNX, chạy kiểm thử hàng loạt, quay video |
| `ui/` | Giao diện camera, radar, hợp nhất dữ liệu, minh họa cuối cùng, launcher |
| `tests/` | Kiểm thử đơn vị cho logic xử lý |

Để thuận tiện cho việc đọc mã nguồn và bảo trì, dự án được tổ chức thành các
thư mục theo vai trò thay vì đặt toàn bộ script ở thư mục gốc. Cây thư mục rút
gọn của dự án như sau:

```text
aeb/
├── configs/                  # cấu hình cảm biến, dataset, model, scenario
│   ├── sensors.yaml           # ego, camera, radar, fusion, phanh
│   ├── model_training.yaml    # tham số train/evaluate/export YOLO
│   ├── dataset_collection*.yaml
│   └── scenarios/
│       ├── car_to_car/        # nhóm tình huống: CCRs, CCRm, CCRb, cut-in...
│       └── suites/            # bộ kiểm thử tổng hợp
├── control/
│   └── brake.py               # trạng thái AEB, TTC, stopping distance, PID
├── core/
│   ├── radar_aeb_pipeline.py  # pipeline radar/AEB dùng chung
│   ├── radar_object.py        # cấu trúc RadarObject
│   ├── target_selector.py     # chọn target AEB
│   └── ground_truth_labels.py # tạo nhãn từ ground truth CARLA
├── perception/
│   └── radar/
│       └── radar_object_tracker.py
├── scripts/
│   ├── collect_yolo_dataset.py
│   ├── check_yolo_dataset.py
│   ├── train_yolo26n.py
│   ├── export_yolo26n_onnx.py
│   ├── run_radar_aeb_scenarios.py
│   ├── run_fusion_aeb_scenarios.py
│   └── record_scenario_videos.py
├── ui/
│   ├── manual_control_common.py
│   ├── camera_view.py
│   ├── radar_view.py
│   ├── radar_aeb_view.py
│   ├── yolo_view.py
│   ├── fusion_view.py
│   └── aeb_demo_view.py
├── tests/
├── docs/
├── report/
└── laucher.py                 # giao diện khởi chạy dự án
```

**Bảng 3.3: Các file mã nguồn và cấu hình chính.**

| File/thư mục | Vai trò |
|---|---|
| `configs/sensors.yaml` | Cấu hình xe ego, camera, radar, fusion, target gate và các tham số phanh |
| `configs/scenarios/car_to_car/*.yaml` | Các nhóm kịch bản car-to-car như đường trống, CCRs, CCRm, CCRb, cut-in, cut-out |
| `configs/scenarios/suites/*.yaml` | Các bộ kiểm thử tổng hợp dùng cho kiểm tra nhanh, kiểm thử hồi quy và bộ minh chứng cuối cùng |
| `core/radar_aeb_pipeline.py` | Ghép các bước radar filtering, predicted path, chọn target và gọi logic phanh |
| `core/radar_object.py` | Định nghĩa đối tượng radar dùng trong pipeline |
| `core/target_selector.py` | Chọn mục tiêu AEB từ danh sách radar object |
| `perception/radar/radar_object_tracker.py` | Gom cụm, theo dõi và xác nhận radar object qua nhiều frame |
| `control/brake.py` | Tính TTC/khoảng cách dừng, máy trạng thái AEB, PID và override phanh |
| `scripts/collect_yolo_dataset.py` | Thu dataset YOLO bằng ground truth CARLA |
| `scripts/check_yolo_dataset.py` | Kiểm tra chất lượng bộ dữ liệu trước khi huấn luyện |
| `scripts/train_yolo26n.py` | Huấn luyện YOLO26n cho lớp `car` |
| `scripts/export_yolo26n_onnx.py` | Xuất mô hình sang ONNX để chạy trong pipeline online |
| `scripts/run_*_aeb_scenarios.py` | Chạy hàng loạt scenario, sinh log định lượng và summary |
| `scripts/record_scenario_videos.py` | Ghi video minh họa từ giao diện Pygame |
| `ui/aeb_demo_view.py` | Giao diện minh họa cuối cùng gồm camera/fusion, góc nhìn điều khiển và radar bird-eye |
| `laucher.py` | Giao diện chọn app, scenario, chế độ phanh và lệnh chạy |

Cách tách module này giúp thuật toán chính không bị phụ thuộc quá chặt vào giao
diện. Giao diện chỉ có nhiệm vụ hiển thị dữ liệu và gọi pipeline; thuật toán xử lý radar
nằm trong `core/` và `perception/`; quyết định phanh nằm trong `control/`; còn
script trong `scripts/` dùng để thu dữ liệu, huấn luyện mô hình, chạy kiểm thử hàng loạt
và ghi video.

## 3.3. Xử Lý Dữ Liệu Radar

Radar ô tô thực tế thường là radar FMCW. Radar phát sóng điện từ, nhận tín hiệu
phản xạ từ vật thể, sau đó xử lý để suy ra khoảng cách, vận tốc tương đối và góc
của vật thể. Chuỗi xử lý radar thực tế có thể gồm FFT, phát hiện đỉnh, CFAR,
ước lượng góc, gom cụm, theo dõi và xuất danh sách đối tượng.

![Nguyên lý radar ô tô FMCW](../assets/nguyenlyradar.webp)

**Hình 3.2: Nguyên lý radar ô tô FMCW ở mức khái niệm.**

CARLA `sensor.other.radar` không trả tín hiệu radar thô như radar thật. Nó trả
các điểm phát hiện đã được mô phỏng sẵn. Mỗi điểm có độ sâu, góc phương vị, góc
cao và vận tốc tương đối. Vì vậy, đồ án bắt đầu từ đầu ra radar mức điểm đo của
CARLA, sau đó xây dựng tầng xử lý gần với đầu ra radar ở mức đối tượng của xe thật.

Nếu dùng trực tiếp toàn bộ điểm radar để tính TTC, hệ thống dễ phanh nhầm do
radar có thể nhận điểm từ mặt đường, lan can, cây, biển báo hoặc xe ở làn bên.
Do đó, đồ án chuyển từ xử lý ở mức điểm đo sang xử lý ở mức đối tượng:

```text
RadarMeasurement
  -> đổi điểm đo sang hệ tọa độ ego
  -> lọc theo range, độ cao, hành lang dự kiến
  -> gom cụm theo vị trí và vận tốc
  -> theo dõi qua nhiều khung hình
  -> RadarObjectList
  -> chọn mục tiêu AEB
```

![Quy trình xử lý radar từ mức điểm đo đến mức đối tượng](../assets/radar_object_processing.svg)

**Hình 3.3: Quy trình xử lý radar từ mức điểm đo đến mức đối tượng.**

### 3.3.1. Đầu Vào Và Hệ Tọa Độ

Một điểm radar sau khi được quy đổi về hệ tọa độ ego có các đại lượng chính:

- `x_forward_m`: khoảng cách theo phương tiến của xe, đơn vị mét;
- `y_right_m`: độ lệch ngang, dương sang phải;
- `z_up_m`: độ cao tương đối;
- `relative_velocity_mps`: vận tốc tương đối theo hướng radar;
- `world_location`: vị trí trong hệ tọa độ thế giới CARLA, dùng khi cần so sánh
  với mặt đường để lọc điểm thấp.

Hệ trục này giúp thuật toán không phụ thuộc trực tiếp vào góc radar ban đầu.
Các bước phía sau chỉ cần làm việc với khoảng cách dọc, lệch ngang, độ cao và
vận tốc tương đối. Phần xử lý chính nằm trong các file:

- `core/radar_aeb_pipeline.py`: lọc điểm radar, cập nhật quỹ đạo dự đoán, gọi
  gom cụm và chọn target;
- `perception/radar/radar_object_tracker.py`: gom cụm điểm radar và theo dõi
  qua nhiều frame;
- `core/radar_object.py`: chuyển cluster thành `RadarObject`;
- `core/target_selector.py`: chọn target radar cho AEB.

### 3.3.2. Các Hằng Số Và Ngưỡng Xử Lý Radar

Các hằng số chính được đọc từ `configs/sensors.yaml`. Bảng dưới đây ghi lại các
tham số quan trọng nhất trong bản cuối của đồ án.

**Bảng 3.4: Các hằng số chính trong xử lý dữ liệu radar.**

| Nhóm | Tham số | Giá trị | Ý nghĩa |
|---|---|---:|---|
| Radar sensor | `range` | 100 m | Giới hạn xa nhất của radar CARLA |
| Radar sensor | `horizontal_fov` | 30 độ | Góc quét ngang, tập trung vào vùng trước xe |
| Radar sensor | `vertical_fov` | 6 độ | Góc quét dọc, giảm điểm không cần thiết theo phương cao |
| Radar sensor | `points_per_second` | 2000 | Mật độ điểm radar mô phỏng |
| Radar sensor | `sensor_tick` | 0.05 s | Chu kỳ radar, tương đương 20 Hz |
| Lọc vùng quan tâm | `min_radar_forward_distance_m` | 0.5 m | Bỏ điểm quá gần mũi xe |
| Lọc độ cao | `min_radar_z_up_m` / `max_radar_z_up_m` | -0.35 / 2.5 m | Giới hạn độ cao điểm dùng cho AEB |
| Lọc mặt đường | `min_height_above_road_m` | 0.20 m | Điểm thấp hơn ngưỡng này so với mặt đường bị coi là mặt đường |
| Hành lang AEB | `max_lateral_offset_m` | 1.25 m | Giới hạn lệch ngang quanh quỹ đạo dự đoán |
| Gom cụm | `tolerance_m` | 1.0 m | Khoảng cách phẳng tối đa để hai điểm thuộc cùng cụm |
| Gom cụm | `velocity_tolerance_mps` | 2.0 m/s | Chênh vận tốc tối đa trong cùng cụm |
| Gom cụm | `vertical_tolerance_m` | 1.5 m | Chênh độ cao tối đa trong cùng cụm |
| Gom cụm | `min_points` | 2 | Cụm phải có ít nhất 2 điểm radar |
| Tracking | `confirm_frames` | 3 frame | Cụm phải xuất hiện đủ 3 frame để được xác nhận |
| Tracking | `release_frames` | 4 frame | Mất dấu 4 frame thì xóa track |
| Tracking | `match_distance_m` | 2.5 m | Khoảng cách tối đa để match measurement với track cũ |
| Tracking | `match_velocity_mps` | 3.0 m/s | Chênh vận tốc tối đa để match track |
| Target gate | `selected_confirm_frames` | 5 frame | Target được chọn phải ổn định đủ 5 frame, trừ trường hợp khẩn cấp |

### 3.3.3. Lọc Điểm Radar

Hàm chính dùng để quyết định một điểm radar có được đưa vào xử lý AEB hay không
là `valid_path_target(point)` trong `core/radar_aeb_pipeline.py`. Một điểm radar
được giữ lại nếu thỏa mãn đồng thời các điều kiện:

$$
x_{forward} \geq x_{min}
$$

$$
x_{forward} \leq R_{radar}
$$

$$
z_{min} \leq z_{up} \leq z_{max}
$$

$$
d_{path}(point) \leq y_{limit}
$$

Trong đó $d_{path}(point)$ là khoảng cách từ điểm radar tới quỹ đạo dự đoán của
ego, còn $y_{limit}$ là giới hạn lệch ngang cho phép. Điều kiện này giúp loại
điểm nằm ngoài hành lang di chuyển của ego.

Ngoài ra, hệ thống lọc điểm mặt đường bằng hàm `is_ground_point(point)`. Nếu có
`world_location`, hệ thống lấy waypoint gần nhất trên map CARLA, tính độ cao
điểm radar so với mặt đường:

$$
h = z_{point} - z_{road}
$$

Nếu $h < 0.20\,m$, điểm đó bị coi là điểm mặt đường và không được dùng để tạo
mục tiêu AEB. Bộ lọc này rất quan trọng vì trong thử nghiệm radar CARLA có thể
trả nhiều điểm thấp ở mặt đường hoặc gần lan can.

### 3.3.4. Gom Cụm Điểm Radar

Sau khi lọc điểm, các điểm còn lại được đưa vào hàm `cluster_radar_points()`.
Thuật toán gom cụm dùng cách duyệt thành phần liên thông: bắt đầu từ một điểm,
tìm các điểm lân cận thỏa mãn điều kiện gần nhau, đưa vào cùng cụm, rồi tiếp tục
mở rộng cụm.

Hai điểm radar $p_i$ và $p_j$ được coi là lân cận nếu:

$$
\sqrt{(x_i-x_j)^2 + (y_i-y_j)^2} \leq d_{tol}
$$

$$
|z_i-z_j| \leq z_{tol}
$$

$$
|v_i-v_j| \leq v_{tol}
$$

Với cấu hình hiện tại: $d_{tol}=1.0\,m$, $z_{tol}=1.5\,m$ và
$v_{tol}=2.0\,m/s$. Cụm chỉ được giữ nếu có ít nhất `min_points=2` điểm và chiều
cao lớn nhất so với mặt đường đủ lớn. Điều này giúp loại các cụm quá nhỏ hoặc
chỉ là phản xạ sát mặt đường.

Một cụm radar được biểu diễn bằng các đại lượng:

- $x$: percentile 20% của các giá trị `x_forward_m`, nhằm lấy phần gần ego hơn
  của cụm thay vì trung bình toàn cụm;
- $y$: median của các giá trị lệch ngang;
- $z$: median của độ cao;
- $v_{rel}$: median của vận tốc tương đối;
- `point_count`: số điểm trong cụm;
- `world_location`: vị trí đại diện của cụm.

Việc dùng median và percentile giúp cụm ít bị ảnh hưởng bởi điểm ngoại lai hơn
so với dùng trung bình đơn giản.

### 3.3.5. Theo Dõi Cụm Qua Nhiều Frame

Sau khi tạo measurement từ cụm điểm, `RadarClusterTracker.update()` ghép measurement
mới với các track cũ. Nếu bật prediction, vị trí dọc của track cũ được dự đoán:

$$
\hat{x}_{t} = x_{t-1} + v_{rel}\Delta t
$$

$$
\hat{y}_{t} = y_{t-1}
$$

Trong đó $\Delta t$ bị giới hạn bởi `max_prediction_time_s=0.30s`. Một measurement
mới được ghép với track cũ nếu:

$$
\sqrt{(\hat{x}-x_m)^2 + (\hat{y}-y_m)^2} \leq 2.5\,m
$$

và:

$$
|v_{track}-v_m| \leq 3.0\,m/s
$$

Khi track được match liên tục, `hit_streak` tăng. Track chỉ được coi là
`confirmed=True` khi `hit_streak >= confirm_frames`, tức ít nhất 3 frame. Nếu
track bị mất dấu, `missed_frames` tăng; khi `missed_frames >= release_frames`,
track bị xóa. Nhờ đó, nhiễu radar xuất hiện thoáng qua không lập tức trở thành
target AEB.

### 3.3.6. Tạo RadarObjectList Và Độ Tin Cậy

Mỗi cluster/track được chuyển thành `RadarObject` bằng hàm
`radar_object_from_cluster()`. Đầu ra ở mức object gồm:

- `object_id`: id track;
- `longitudinal_m`: khoảng cách dọc;
- `lateral_m`: lệch ngang;
- `height_m`: độ cao;
- `relative_velocity_mps`: vận tốc tương đối;
- `point_count`: số điểm radar trong cụm;
- `confirmed`, `age_frames`, `hit_streak`, `missed_frames`;
- `confidence`: độ tin cậy nội bộ của dự án;
- `ttc_s`: TTC tính từ khoảng cách dọc và vận tốc tương đối.

CARLA radar không cung cấp trực tiếp các đại lượng như RCS, SNR hoặc xác suất tồn
tại đối tượng như radar thật. Vì vậy, độ tin cậy trong đồ án là một điểm số nội
bộ, không phải confidence vật lý của radar thương mại. Hàm
`cluster_confidence()` tính:

$$
score = 0.4\,score_{points} + 0.4\,score_{hits} + 0.2\,score_{fresh}
$$

Trong đó:

$$
score_{points} = \min(1, \frac{point\_count}{6})
$$

$$
score_{hits} = \min(1, \frac{hit\_streak}{3})
$$

`score_fresh = 1` nếu track không stale, ngược lại bằng 0. Nếu track chưa được
xác nhận, score bị nhân với `0.5`; nếu đã xác nhận, nhân với `1.0`. Điểm số này
giúp biểu diễn mức ổn định của track trong mô phỏng.

### 3.3.7. Chọn Target Radar Cho AEB

Danh sách `RadarObjectList` được đưa vào `select_aeb_target()`. Ở tầng radar-only,
target được chọn theo nguyên tắc:

1. chỉ xét object đã `confirmed=True`;
2. bỏ object stale;
3. ưu tiên object có TTC hữu hạn nhỏ nhất;
4. nếu TTC tương đương hoặc không hữu hạn, ưu tiên object có khoảng cách dọc nhỏ
   hơn.

TTC tại tầng radar được tính bằng:

$$
TTC = \frac{x_{forward}}{-v_{rel}}
$$

với điều kiện $v_{rel}<0$, tức mục tiêu đang tiến lại gần ego. Nếu $v_{rel} \geq 0$,
TTC được coi là vô hạn và object ít được ưu tiên hơn.

Sau bước chọn radar target, hệ thống còn đi qua target gate và fusion ở các tầng
sau. Vì vậy, một object radar được chọn ở bước này chưa chắc đã lập tức gây
phanh; nó còn phải nằm trong hành lang dự đoán, đủ ổn định qua nhiều frame, và
trong bản fusion cuối cùng nên được camera/YOLO xác nhận là xe.

## 3.4. Tính Thời Gian Va Chạm Và Khoảng Cách Dừng

Sau khi đã chọn được mục tiêu phía trước, hệ thống cần đánh giá mức nguy hiểm
theo hai nhóm đại lượng:

- thời gian còn lại trước va chạm nếu hai xe tiếp tục chuyển động như hiện tại;
- khoảng cách tối thiểu cần có để ego dừng lại hoặc giảm tốc đủ an toàn.

Trong mã nguồn, hai phép tính chính nằm trong `control/brake.py`:

- `compute_ttc(distance_m, relative_velocity_mps)`;
- `BinaryAEB.required_stopping_distance(ego_speed_mps, relative_velocity_mps)`.

Kết quả của hai phép tính này được ghi vào `AEBDecision` dưới dạng `ttc_s`,
`required_distance_m` và `distance_margin_m`, sau đó được bộ điều khiển phanh
sử dụng để chuyển trạng thái `NORMAL`, `WARNING`, `BRAKE` hoặc `RELEASE`.

### 3.4.1. Quy Ước Vận Tốc Tương Đối Và Vận Tốc Đóng

Trong dự án, vận tốc tương đối `relative_velocity_mps` được dùng theo quy ước:

- $v_{rel} < 0$: mục tiêu đang tiến lại gần ego, nguy cơ va chạm tăng;
- $v_{rel} = 0$: khoảng cách giữa ego và mục tiêu gần như không đổi;
- $v_{rel} > 0$: mục tiêu đang rời xa ego hoặc ego không còn bắt kịp mục tiêu.

Do đó vận tốc đóng được tính:

$$
v_{closing} = -v_{rel}
$$

Vận tốc đóng chỉ có ý nghĩa kích hoạt AEB khi:

$$
v_{closing} > 0
$$

Trong cấu hình hiện tại, hệ thống còn dùng ngưỡng `min_closing_speed_mps=0.2`.
Nếu vận tốc đóng nhỏ hơn ngưỡng này, target không được coi là đang tiến lại đủ
rõ ràng để kích hoạt phanh. Điều kiện này giúp tránh trường hợp radar nhiễu
vận tốc rất nhỏ nhưng AEB vẫn phản ứng.

### 3.4.2. Công Thức TTC

TTC (Time To Collision) là thời gian còn lại trước va chạm nếu khoảng cách và
vận tốc tương đối hiện tại được giữ nguyên. Đây là đại lượng thường dùng trong
các hệ thống cảnh báo va chạm phía trước và đánh giá AEB vì dễ diễn giải trực
tiếp: TTC càng nhỏ thì thời gian còn lại để người lái hoặc hệ thống phản ứng
càng ít [13]. Hàm `compute_ttc()` triển khai theo các trường hợp sau:

$$
TTC =
\begin{cases}
0, & d \leq 0 \\
\frac{d}{-v_{rel}}, & d > 0 \text{ và } v_{rel}<0 \\
\infty, & v_{rel} \geq 0
\end{cases}
$$

Trong đó:

- $d$ là khoảng cách dọc từ ego tới mục tiêu, lấy từ radar/fusion target;
- $v_{rel}$ là vận tốc tương đối của mục tiêu so với ego;
- $TTC=\infty$ nghĩa là chưa có nguy cơ va chạm theo mô hình vận tốc hiện tại.

Ví dụ, nếu target cách ego $30\,m$ và có $v_{rel}=-10\,m/s$, khi đó:

$$
TTC = \frac{30}{10} = 3\,s
$$

TTC dễ hiểu và rất hữu ích, nhưng không đủ để quyết định phanh trong mọi trường
hợp. Cùng một TTC là 3 giây, xe chạy 30 km/h và xe chạy 100 km/h có yêu cầu
quãng đường dừng khác nhau. Vì vậy đồ án dùng thêm mô hình khoảng cách dừng.

![Mô hình TTC và khoảng cách dừng](../assets/ttc_stopping_distance.svg)

**Hình 3.4: Mô hình TTC và khoảng cách dừng giữa ego và mục tiêu.**

### 3.4.3. Công Thức Khoảng Cách Dừng

Khoảng cách dừng của ego gồm hai phần:

- quãng đường xe vẫn tiếp tục đi trong thời gian phản ứng/tính toán;
- quãng đường hãm phanh sau khi hệ thống bắt đầu phanh.

Công thức này xuất phát từ mô hình động học giảm tốc đều và được kết hợp với
thời gian phản ứng của hệ thống. Việc so sánh khoảng cách hiện có với khoảng
cách cần thiết để dừng cũng cùng tinh thần với các thuật toán AEB trong hệ thống
mã nguồn mở như Autoware [6], [13].

Trong code, khoảng cách dừng của ego được tính:

$$
d_{ego} = v_{ego}t_{response} + \frac{v_{ego}^{2}}{2a_{ego}}
$$

Trong đó:

- $v_{ego}$ là vận tốc hiện tại của xe ego;
- $t_{response}$ là thời gian phản ứng giả định của hệ thống;
- $a_{ego}$ là gia tốc hãm giả định của ego.

Nếu target cũng đang chạy, target có thể tiếp tục đi thêm một đoạn trước khi
dừng. Vì vậy hệ thống ước lượng khoảng cách dừng của target:

$$
d_{target} = \frac{v_{target}^{2}}{2a_{target}}
$$

Vận tốc target được suy ra từ vận tốc ego và vận tốc tương đối:

$$
v_{target} = \max(0, v_{ego} + v_{rel})
$$

Khoảng cách yêu cầu giữa ego và target được tính:

$$
d_{required} = d_{ego} - d_{target} + d_{offset}
$$

Cuối cùng, hệ thống giới hạn giá trị nhỏ nhất:

$$
d_{required} = \max(d_{offset}, d_{required})
$$

Việc trừ $d_{target}$ có ý nghĩa: nếu xe phía trước cũng đang chạy và chưa dừng
ngay, ego có thêm không gian để giảm tốc. Ngược lại, với tình huống xe phía
trước đứng yên, $v_{target}=0$ nên $d_{target}=0$, yêu cầu phanh sẽ nghiêm ngặt
hơn.

### 3.4.4. Các Hằng Số Được Sử Dụng

Các tham số chính được lấy từ nhóm `brake` trong `configs/sensors.yaml`.

**Bảng 3.5: Các biến và hằng số trong công thức TTC/khoảng cách dừng.**

| Ký hiệu/tham số | Giá trị hiện tại | Ý nghĩa | Đơn vị |
|---|---:|---|---|
| $d$ | Từ target | Khoảng cách dọc ego-mục tiêu | m |
| $v_{rel}$ | Từ radar/fusion | Vận tốc tương đối | m/s |
| $v_{closing}$ | $-v_{rel}$ | Vận tốc đóng | m/s |
| $TTC$ | Tính toán | Thời gian tới va chạm | s |
| `warning_ttc_s` | 3.0 | Ngưỡng cảnh báo sớm | s |
| `brake_ttc_s` | 1.5 | Ngưỡng bắt đầu phanh theo TTC | s |
| `release_ttc_s` | 3.5 | Ngưỡng nhả phanh khi nguy cơ giảm | s |
| `response_time_s` | 0.20 | Thời gian phản ứng/tính toán giả định | s |
| `ego_emergency_decel_mps2` | 8.0 | Gia tốc hãm giả định của ego | m/s² |
| `target_emergency_decel_mps2` | 6.0 | Gia tốc hãm giả định của target | m/s² |
| `stopping_distance_offset_m` | 1.0 | Khoảng đệm an toàn tối thiểu | m |
| `min_closing_speed_mps` | 0.2 | Vận tốc đóng tối thiểu để target hợp lệ | m/s |
| `min_valid_distance_m` | 0.5 | Khoảng cách target nhỏ nhất được xét | m |
| `max_valid_distance_m` | 100.0 | Khoảng cách target lớn nhất được xét | m |

### 3.4.5. Biên An Toàn Khoảng Cách

Sau khi có $d_{required}$, hệ thống tính biên an toàn khoảng cách:

$$
d_{margin} = d - d_{required}
$$

Ý nghĩa của $d_{margin}$:

- $d_{margin} > 0$: khoảng cách hiện tại còn lớn hơn khoảng cách cần thiết;
- $d_{margin} = 0$: ego vừa đủ khoảng cách dừng theo mô hình;
- $d_{margin} < 0$: khoảng cách hiện tại đã nhỏ hơn khoảng cách yêu cầu, cần
  phanh mạnh hơn hoặc chuyển sang trạng thái khẩn cấp.

Trong code, biến này là `distance_margin_m`. Nếu `use_stopping_distance=true`
và `distance_margin_m` nhỏ hơn ngưỡng cho phép, hệ thống có thể chuyển sang
trạng thái phanh ngay cả khi TTC chưa xuống quá thấp. Đây là điểm khác với cách
dùng TTC đơn thuần.

### 3.4.6. Vai Trò Trong Logic AEB

TTC và khoảng cách dừng được dùng song song:

```text
target radar/fusion
  -> distance_m, relative_velocity_mps, ego_speed_mps
  -> compute_ttc()
  -> required_stopping_distance()
  -> distance_margin_m
  -> đánh giá mức nguy hiểm
  -> chọn trạng thái AEB và lực phanh
```

Logic tổng quát:

1. nếu không có target hợp lệ, AEB ở `NORMAL` hoặc `RELEASE`;
2. nếu $TTC \leq warning\_ttc$, hệ thống chuyển sang vùng cảnh báo;
3. nếu $TTC \leq brake\_ttc$, hệ thống bắt đầu phanh;
4. nếu $d_{margin}$ âm hoặc rất nhỏ, hệ thống phanh dù TTC chưa quá thấp;
5. nếu target mất nguy hiểm và không bật chế độ giữ phanh đến khi dừng, hệ
   thống có thể nhả phanh.

Như vậy, TTC trả lời câu hỏi “còn bao lâu thì va chạm nếu giữ nguyên vận tốc?”,
còn khoảng cách dừng trả lời câu hỏi “với tốc độ hiện tại, xe còn đủ đường để
dừng an toàn không?”. Việc kết hợp hai đại lượng này giúp hệ thống phản ứng hợp
lý hơn trên dải vận tốc 50-80 km/h mà đồ án đặt làm mục tiêu chính.

## 3.5. Thu Dữ Liệu Và Fine-Tune YOLO26n

Camera đặt sau kính lái cung cấp ảnh RGB cho mô hình nhận dạng đối tượng. Trong
bài toán AEB của đồ án, camera không phải nguồn chính để đo khoảng cách và vận
tốc tương đối; hai đại lượng này vẫn do radar đảm nhiệm. Vai trò chính của
camera và YOLO là xác nhận ngữ nghĩa: mục tiêu radar phía trước có phải ô tô hay
không.

Đầu ra mong muốn của nhánh camera là danh sách bounding box:

```text
Camera RGB
  -> YOLO26n
  -> bbox 2D, class, confidence
  -> lọc/NMS
  -> xác nhận target radar trong bước fusion
```

### 3.5.1. Lý Do Chọn YOLO26n

Đồ án chọn YOLO26n vì các lý do sau:

- YOLO là họ mô hình one-stage detector, tức ảnh đầu vào được đưa qua mạng một
  lần để dự đoán trực tiếp bounding box, class và confidence. Cách này phù hợp
  với bài toán thời gian thực hơn các detector hai giai đoạn.
- Bản `n` là bản nano/nhẹ nhất trong nhóm model đang dùng, phù hợp laptop có GPU
  khoảng 4 GB VRAM và vẫn còn phải chạy CARLA, pygame, radar UI và fusion.
- Bài toán chỉ có một class `car`, môi trường mô phỏng tương đối sạch, nên không
  cần dùng model lớn. Model lớn có thể tăng độ chính xác trên tập khó hơn nhưng
  làm giảm FPS và tăng tải GPU.
- YOLO26n hỗ trợ tốt luồng fine-tune bằng Ultralytics và export sang ONNX. Bản
  ONNX được dùng trong UI/fusion để chạy suy luận nhanh hơn và dễ triển khai
  runtime.

Về nguyên lý, YOLO chia ảnh thành các đặc trưng ở nhiều mức tỷ lệ, dự đoán hộp
bao quanh đối tượng và xác suất class trên các đặc trưng đó. Khi huấn luyện,
loss gồm ba thành phần chính:

- `box_loss`: sai số vị trí/kích thước bounding box;
- `cls_loss`: sai số phân loại class;
- `dfl_loss`: hỗ trợ mô hình học phân bố vị trí cạnh box chính xác hơn.

Sau suy luận, các box trùng lặp được xử lý bằng NMS (Non-Maximum Suppression).
Trong dự án, NMS đặc biệt quan trọng vì nếu YOLO trả nhiều box chồng nhau cho
cùng một xe, bước fusion có thể ghép sai hoặc tạo nhiều target ảo.

### 3.5.2. Nguyên Tắc Tạo Nhãn Từ CARLA

Bộ dữ liệu YOLO được tạo bằng nhãn chuẩn từ CARLA, không vẽ tay từng ảnh. Script
chính là `scripts/collect_yolo_dataset.py`, sử dụng các hàm trong
`core/ground_truth_labels.py` để chiếu bounding box 3D của actor xe sang ảnh
camera.

Quy trình tạo nhãn:

```text
spawn ego Tesla Model 3
  -> spawn xe phía trước theo kịch bản thu data
  -> camera RGB, depth camera, semantic camera
  -> lấy bounding box 3D của actor vehicle từ CARLA
  -> chiếu 8 đỉnh bbox 3D sang mặt phẳng ảnh 2D
  -> kiểm tra visible ratio bằng depth/semantic
  -> fit box theo phần xe thật sự nhìn thấy
  -> lọc box quá nhỏ, quá xa, bị che khuất nặng hoặc chồng nhau
  -> ghi ảnh .jpg và label YOLO một class `car`
```

Việc dùng ground truth của CARLA chỉ được dùng trong giai đoạn tạo dataset. Khi
chạy AEB/fusion, hệ thống không dùng ground truth actor để quyết định phanh.
Runtime chỉ dùng ảnh camera, kết quả YOLO, radar và trạng thái ego.

### 3.5.3. Kịch Bản Thu Dữ Liệu

Các bộ dữ liệu đầu tiên có nhiều xe ở làn bên, nhiều box chồng nhau và nhiều ảnh
các xe nối thành một hàng dài. Sau khi kiểm tra gallery, đồ án chuyển sang bộ
`v7_same_lane`, tập trung vào xe cùng làn phía trước ego. Lý do là bài toán AEB
cuối cùng chỉ xét car-to-car trên cao tốc trong môi trường lý tưởng, nên dataset
same-lane giúp YOLO học đúng miền ảnh cần cho fusion.

Cấu hình chính khi thu v7:

- map: `Town04`;
- ego: `vehicle.tesla.model3`;
- camera: 1280x720, FOV 70 độ, vị trí sau kính lái theo `configs/sensors.yaml`;
- số xe phía trước cùng làn: 4;
- khoảng cách ban đầu xấp xỉ 30 m, 65 m, 100 m và 135 m;
- nhịp lưu: 40 frame/ảnh, tương đương khoảng 2 giây/ảnh ở synchronous 20 FPS;
- class duy nhất: `0 = car`;
- lọc xe xa trong vùng khoảng 100 m phía trước;
- giữ một tỷ lệ ảnh không có xe để giảm false positive.

Các bộ v3-v6 được dùng để thử nghiệm và phát hiện vấn đề dữ liệu. Bộ v7 là bộ
được chọn để train vì ít nhiễu xe làn bên hơn, box sạch hơn và phù hợp trực tiếp
với mục tiêu fusion của đồ án.

![Ví dụ ảnh validation có nhãn bounding box trong quá trình huấn luyện YOLO26n](../assets/evidence/yolo_val_batch0_labels.jpg)

**Hình 3.5: Ví dụ ảnh validation có nhãn bounding box trong quá trình huấn luyện YOLO26n.**

### 3.5.4. Đánh Giá Bộ Dữ Liệu V7 Same-Lane

Bộ dữ liệu v7 được audit bằng `scripts/check_yolo_dataset.py` và báo cáo thống
kê `outputs/dataset_v7_same_lane_stats.json`. Các kiểm tra gồm: số lượng ảnh,
số instance, tỷ lệ ảnh empty, trùng lặp gần, label thiếu, label sai định dạng,
ảnh lỗi và trùng ảnh giữa các split.

**Bảng 3.6: Thống kê bộ dữ liệu v7 same-lane.**

| Tập dữ liệu | Số ảnh | Số box | Ảnh có xe | Ảnh không xe | Empty | Near-dup | Khoảng cách label | Số phiên | Số mẫu xe |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| Train | 1505 | 1872 | 1186 | 319 | 21.2% | 7.2% | 6.5-100.0 m | 28 | 21 |
| Validation | 300 | 379 | 251 | 49 | 16.3% | 10.4% | 6.8-100.0 m | 6 | 14 |
| Test | 200 | 264 | 164 | 36 | 18.0% | 8.5% | 6.9-99.2 m | 4 | 11 |

Nhận xét về dataset:

- Tỷ lệ ảnh empty 16-21% là cần thiết vì khi chạy thực tế không phải lúc nào
  phía trước xe cũng có target. Nếu dataset chỉ toàn ảnh có xe, model dễ sinh
  false positive.
- Near-duplicate dưới 11% cho thấy nhịp lưu 40 frame giúp ảnh thưa nhau hơn,
  giảm hiện tượng nhiều ảnh gần như giống hệt.
- Khoảng cách label trải từ khoảng 6-100 m, phù hợp với radar 100 m và bài toán
  cao tốc 50-80 km/h.
- Train có 21 mẫu xe khác nhau, giúp model không chỉ học một kiểu xe duy nhất.
- `visible_ratio` trung vị khoảng 0.54-0.55, nghĩa là phần lớn box còn đủ vùng
  xe nhìn thấy. Các xe bị che quá nặng đã được lọc bằng điều kiện visible pixels,
  fitted box area và suppress overlapping boxes.

Hạn chế của dataset:

- Dataset chủ yếu ở `Town04`, thời tiết và ánh sáng lý tưởng.
- Dataset tập trung vào xe cùng làn, chưa bao phủ đầy đủ xe cắt ngang, xe làn
  bên phức tạp hoặc nhiều điều kiện thời tiết.
- Metadata v7 chưa lưu màu xe đầy đủ, nên thống kê màu chưa dùng được trong báo
  cáo.

### 3.5.5. Quá Trình Fine-Tune YOLO26n

YOLO26n được fine-tune bằng môi trường Python 3.10 tách riêng, vì CARLA 0.9.11
dùng Python 3.7 còn phiên bản Ultralytics sử dụng trong đồ án cần Python mới
hơn. Quy trình gồm ba bước: kiểm tra chất lượng bộ dữ liệu, fine-tune mô hình
và xuất trọng số tốt nhất sang ONNX để suy luận thời gian chạy. Tên môi trường
và các lệnh tái lập được lưu trong README của dự án.

**Bảng 3.7: Cấu hình fine-tune YOLO26n.**

| Tham số | Giá trị | Ghi chú |
|---|---:|---|
| Base model | `models/yolo26n.pt` | Model pretrained trước khi fine-tune |
| Dataset | `dataset_v7_same_lane/dataset.yaml` | Một class `car` |
| Image size | 640 | Kích thước ảnh đưa vào mô hình khi huấn luyện |
| Epoch tối đa | 100 | Có `patience=20` để dừng sớm nếu metric không cải thiện |
| Batch size | 16 | Phù hợp GPU laptop 4 GB VRAM trong lần huấn luyện cuối |
| Optimizer | AdamW | Theo `configs/model_training.yaml` |
| Learning rate ban đầu | 0.001 | `lr0` |
| Mosaic | 0.5 | Tăng đa dạng bố cục trong quá trình huấn luyện |
| Mixup/copy-paste | 0.0 / 0.0 | Không dùng để tránh tạo ảnh quá xa miền CARLA thật |
| Seed | 2026 | Giúp kết quả lặp lại tốt hơn |
| Output run | `training_runs/detect/yolo26n_aeb_20260619_011359` | Lần huấn luyện cuối được dùng trong báo cáo |

Sau khi huấn luyện, bộ trọng số tốt nhất được export sang ONNX để dùng trong giao diện và fusion:

- `models/yolo26n_aeb_v7.pt`;
- `models/yolo26n_aeb_v7.onnx`.

### 3.5.6. Đánh Giá Mô Hình Sau Fine-Tune

Kết quả huấn luyện được ghi trong `results.csv` và minh họa bằng
`training_runs/detect/yolo26n_aeb_20260619_011359/results.png`.

![Kết quả huấn luyện YOLO26n](../assets/evidence/yolo_training_results.png)

**Hình 3.6: Kết quả huấn luyện YOLO26n.**

**Bảng 3.8: Kết quả đánh giá YOLO26n trong lần fine-tune cuối.**

| Mốc | Epoch | Precision | Recall | mAP50 | mAP50-95 | Train box loss | Val box loss |
|---|---:|---:|---:|---:|---:|---:|---:|
| Best theo mAP50-95 | 78 | 0.9919 | 0.9642 | 0.9940 | 0.9495 | 0.4179 | 0.3527 |
| Epoch cuối | 98 | 0.9837 | 0.9683 | 0.9933 | 0.9466 | 0.3357 | 0.3256 |

Nhận xét từ các biểu đồ:

- `train/box_loss`, `train/cls_loss` và `train/dfl_loss` giảm theo thời gian,
  cho thấy model học được vị trí box và class `car`.
- `val/box_loss` cũng giảm và không tăng mạnh ở cuối quá trình train, vì vậy
  chưa thấy dấu hiệu overfit nghiêm trọng trên validation.
- Precision xấp xỉ 0.98-0.99 nghĩa là phần lớn box model dự đoán là đúng xe.
- Recall xấp xỉ 0.96-0.97 nghĩa là model ít bỏ sót xe trong miền dữ liệu đã
  thu.
- mAP50 khoảng 0.993 và mAP50-95 khoảng 0.947-0.950 là đủ tốt cho vai trò xác
  nhận mục tiêu trong fusion.

Các file `BoxPR_curve.png`, `BoxF1_curve.png`, `confusion_matrix.png` và
`val_batch*_pred.jpg` trong cùng thư mục train được dùng để kiểm tra bổ sung.
Trong runtime AEB, YOLO vẫn không quyết định phanh một mình; model chỉ xác nhận
target radar là xe, còn khoảng cách, vận tốc tương đối, TTC và khoảng cách dừng
vẫn lấy từ radar/fusion.

## 3.6. Hợp Nhất Dữ Liệu Cảm Biến Camera-Radar

Hợp nhất dữ liệu cảm biến trong đồ án được thực hiện theo hướng radar-first:
radar cung cấp khoảng cách, vận tốc tương đối và TTC; camera/YOLO xác nhận mục
tiêu đó là ô tô trong ảnh. Cách này phù hợp với vai trò của từng cảm biến:
radar mạnh về đo động học, camera mạnh về nhận dạng ngữ nghĩa.

Điểm quan trọng là hệ thống không dùng nhãn actor hoặc ground truth của CARLA để
biết sẵn radar target nằm trong pixel nào. Runtime chỉ dùng dữ liệu cảm biến:

- `RadarObject` hoặc radar point đã có `world_location`;
- ảnh RGB và pose camera;
- bounding box YOLO;
- ma trận chiếu camera.

### 3.6.1. Đầu Vào Và Đầu Ra Của Fusion

Đầu vào của khối fusion gồm:

- danh sách radar object/point sau lọc radar;
- ảnh RGB mới nhất từ camera sau kính lái;
- danh sách detection từ YOLO26n: `x1`, `y1`, `x2`, `y2`, `confidence`,
  `class_name`;
- transform camera tại thời điểm ảnh được chụp;
- cấu hình ngưỡng từ `configs/sensors.yaml`.

Đầu ra của khối fusion trong dự án có hai dạng:

- trong giao diện kiểm tra: danh sách điểm radar đã chiếu lên ảnh và danh sách
  bounding box YOLO được ghép;
- trong kiểm thử AEB tự động: trạng thái mục tiêu đã được camera xác nhận hay
  chưa, kèm lý do bằng văn bản như "mục tiêu radar nằm trong bounding box YOLO"
  hoặc "chặn phanh vì mục tiêu radar không nằm trong bounding box YOLO".

Luồng xử lý tổng quát:

```text
Radar target/object
  -> lấy world_location
  -> biến đổi world -> camera
  -> chiếu 3D -> pixel 2D
  -> kiểm tra pixel nằm trong ảnh
  -> kiểm tra pixel nằm trong YOLO bbox class car
  -> fusion confirmed / fusion blocked
```

![Nguyên lý hợp nhất dữ liệu camera-radar bằng phép chiếu hình học](../assets/camera_radar_fusion_projection.svg)

**Hình 3.7: Nguyên lý hợp nhất dữ liệu camera-radar bằng phép chiếu hình học.**

### 3.6.2. Ma Trận Nội Tại Camera

Ma trận nội tại camera được tính trong hàm `camera_intrinsic()` của
`ui/manual_control_common.py`. Với ảnh có chiều rộng $W$, chiều cao $H$ và góc
nhìn ngang $FOV$, tiêu cự theo pixel được tính:

$$
f = \frac{W}{2\tan(FOV/2)}
$$

Ma trận nội tại:

$$
K =
\begin{bmatrix}
f & 0 & W/2 \\
0 & f & H/2 \\
0 & 0 & 1
\end{bmatrix}
$$

Với cấu hình hiện tại, camera có ảnh 1280x720 và FOV 70 độ. Ma trận này biến
tọa độ điểm trong hệ camera thành pixel trên ảnh.

### 3.6.3. Biến Đổi Hệ Tọa Độ World Sang Camera

Radar target được xử lý ở hệ ego/radar, nhưng để chiếu lên ảnh camera cần tọa độ
trong hệ world. Các radar point và radar object trong dự án giữ thêm
`world_location`, nên fusion có thể dùng trực tiếp vị trí 3D này.

Hàm `project_world_to_camera()` thực hiện các bước:

1. tạo vector đồng nhất của điểm world:

$$
P_w = [X_w, Y_w, Z_w, 1]^T
$$

2. nhân với ma trận nghịch đảo transform camera:

$$
P_{ue} = T_{cw}P_w
$$

Trong đó $T_{cw}$ là ma trận từ world sang hệ camera theo quy ước CARLA/Unreal.

3. đổi trục từ hệ Unreal sang hệ camera chuẩn dùng cho phép chiếu:

$$
P_c = [Y_{ue}, -Z_{ue}, X_{ue}]^T
$$

Trong đó $P_c=[X_c,Y_c,Z_c]^T$. Nếu $Z_c \leq 0$, điểm nằm sau camera nên bị bỏ.

4. chiếu sang pixel:

$$
\begin{bmatrix}
\tilde{u} \\
\tilde{v} \\
\tilde{w}
\end{bmatrix} = K \begin{bmatrix}
X_c \\
Y_c \\
Z_c
\end{bmatrix}
$$

$$
u = \frac{\tilde{u}}{\tilde{w}},\quad
v = \frac{\tilde{v}}{\tilde{w}}
$$

Điểm chỉ được giữ nếu:

$$
0 \leq u < W,\quad 0 \leq v < H
$$

### 3.6.4. Lọc Radar Trước Khi Chiếu

Không phải mọi radar point đều được chiếu lên ảnh để match. Trong UI/debug
`ui/fusion_view.py` và `ui/aeb_demo_view.py`, một điểm radar phải thỏa mãn:

$$
x_{forward} \geq x_{min}
$$

$$
x_{forward} \leq R_{radar}
$$

$$
|y_{right}| \leq y_{limit}
$$

$$
z_{min} \leq z_{up} \leq z_{max}
$$

Trong giao diện minh họa cuối cùng, nếu có `RadarAEBPipeline`, hàm `valid_path_target()` được ưu
tiên dùng lại để bảo đảm điểm radar cũng nằm trong hành lang quỹ đạo dự đoán.
Nhờ đó fusion không chỉ nhìn FOV camera, mà còn bám theo vùng di chuyển có khả
năng gây nguy hiểm cho ego.

**Bảng 3.9: Các hằng số chính trong hợp nhất dữ liệu camera-radar.**

| Nhóm | Tham số | Giá trị | Ý nghĩa |
|---|---|---:|---|
| YOLO | `model.confidence` | 0.25 | Ngưỡng confidence tối thiểu của bbox |
| YOLO | `model.nms_iou` | 0.50 | Ngưỡng NMS để loại bbox trùng |
| YOLO | `model.inference_interval_s` | 0.15 s | Chu kỳ suy luận YOLO trong UI |
| YOLO | `class_names[0]` | `car` | Class duy nhất dùng cho AEB |
| Fusion | `min_radar_forward_distance_m` | 0.5 m | Bỏ điểm radar quá gần |
| Fusion | `max_lateral_offset_m` | 2.4 m | Giới hạn lệch ngang khi chiếu/match debug |
| Fusion | `min_radar_z_up_m` / `max_radar_z_up_m` | -100 / 100 m | Không bó hẹp độ cao ở tầng fusion; radar pipeline đã lọc trước |
| Fusion gate | `confirmation_hold_s` | 0.35 s | Giữ xác nhận fusion ngắn hạn nếu camera/radar lệch frame |

### 3.6.5. Ghép Radar Với Bounding Box YOLO

Sau khi radar target được chiếu thành pixel $(u,v)$, hệ thống kiểm tra pixel đó
có nằm trong bbox YOLO class `car` hay không:

$$
x_1 \leq u \leq x_2
$$

$$
y_1 \leq v \leq y_2
$$

Nếu điều kiện đúng, radar target được camera xác nhận. Trong kiểm thử hàng loạt,
trạng thái này được ghi vào log dưới dạng mục tiêu radar đã nằm trong bounding
box YOLO của lớp `car`.

Nếu có nhiều điểm radar nằm trong cùng một bbox ở giao diện debug, hệ thống chọn
điểm có `x_forward_m` nhỏ nhất, tức điểm gần ego nhất trong bbox:

$$
p^* = \arg\min_{p \in bbox} x_{forward}(p)
$$

Cách chọn này phù hợp với AEB vì điểm gần nhất của xe phía trước thường quyết
định khoảng cách an toàn. Tuy nhiên trong pipeline phanh cuối, khoảng cách và
TTC vẫn lấy từ radar target/object đã chọn ở tầng radar, không lấy từ kích thước
bbox camera.

### 3.6.6. Fusion Gate Trong Quyết Định Phanh

Trong batch fusion AEB, radar vẫn tính quyết định phanh trước. Fusion gate chỉ
can thiệp khi radar muốn chuyển sang trạng thái phanh. Logic trong
`_fusion_gated_decision()` có thể mô tả:

```text
nếu radar_decision.state != BRAKE:
    giữ nguyên quyết định radar
ngược lại nếu fusion vừa xác nhận target:
    giữ nguyên quyết định phanh
ngược lại:
    chặn phanh, chuyển sang RELEASE với brake = 0
```

Nói cách khác, camera không tự tạo lệnh phanh. Camera chỉ có quyền xác nhận hoặc
chặn một lệnh phanh do radar đề xuất. Thiết kế này giảm nguy cơ phanh nhầm khi
radar nhìn thấy lan can, biển báo hoặc vật thể ngoài làn, nhưng vẫn giữ radar là
nguồn động học chính.

Để tránh mất xác nhận chỉ vì camera và radar lệch một vài frame, hệ thống dùng
`confirmation_hold_s=0.35s`. Nếu target vừa được xác nhận trong khoảng thời gian
ngắn này, fusion vẫn coi target là hợp lệ. Cách này phù hợp với hệ thống mô
phỏng 20 Hz, nơi radar/camera/YOLO không phải lúc nào cũng cập nhật đúng cùng
một tick.

### 3.6.7. Các Trường Hợp Không Xác Nhận Fusion

Fusion có thể không xác nhận target trong các trường hợp:

- không có mục tiêu radar hợp lệ;
- mục tiêu radar chưa có tọa độ 3D trong hệ world;
- camera chưa sẵn sàng hoặc chưa có ảnh mới;
- YOLO không phát hiện xe trong ảnh;
- mục tiêu radar nằm phía sau camera;
- điểm radar sau khi chiếu ra ngoài biên ảnh;
- điểm radar không nằm trong bounding box YOLO nào của lớp `car`.

Các lý do này được ghi vào log để phân tích lỗi. Ví dụ, nếu radar báo nguy hiểm
nhưng fusion chặn phanh vì điểm radar không nằm trong bounding box YOLO, có thể
mục tiêu radar là vật thể không phải xe, YOLO bỏ sót xe, hoặc sai số hiệu chỉnh
camera-radar làm điểm chiếu lệch khỏi bounding box.

### 3.6.8. Ưu Và Nhược Điểm Của Cách Fusion Này

Ưu điểm:

- không dùng ground truth trong runtime;
- giải thích được bằng hình học chiếu, dễ trình bày trong báo cáo;
- giảm phanh nhầm so với radar-only khi radar nhìn thấy vật thể không phải xe;
- tận dụng đúng vai trò của từng cảm biến: radar đo động học, camera xác nhận
  đối tượng.

Hạn chế:

- phụ thuộc vào độ chính xác vị trí gắn camera/radar và transform trong CARLA;
- nếu YOLO bỏ sót xe, fusion có thể chặn phanh dù radar đã thấy nguy hiểm;
- nếu bbox quá nhỏ hoặc target bị che khuất, điểm radar có thể không nằm trong
  bbox;
- thuật toán hiện mới là fusion hình học/gating, chưa phải tracking đa cảm biến
  đầy đủ kiểu Kalman filter hoặc hợp nhất xác suất ở mức đối tượng.

Với phạm vi đồ án hiện tại, cách fusion này đủ phù hợp vì bài toán chỉ xét ô tô
trên cao tốc, thời tiết lý tưởng và mục tiêu chính là giảm phanh nhầm của
radar-only mà vẫn giữ được khả năng tránh va chạm trong dải vận tốc mong muốn.

## 3.7. Dự Đoán Quỹ Đạo Di Chuyển

Trong bài toán AEB, radar có thể nhìn thấy nhiều vật thể phía trước: lan can,
biển báo, mặt đường, xe ở làn bên hoặc xe nằm trong vùng quét nhưng không nằm
trên hướng đi của ego. Nếu chỉ chọn vật thể gần nhất trong FOV radar, hệ thống
dễ phanh nhầm khi xe đang chạy sát mép đường hoặc vào cua. Vì vậy dự án tạo
một quỹ đạo dự đoán ngắn hạn của ego và chỉ giữ các radar object nằm gần quỹ đạo
này.

Phần này được triển khai trong `core/radar_aeb_pipeline.py`, chủ yếu ở các hàm:

- `update_predicted_path()`;
- `constant_curvature_path()`;
- `distance_to_predicted_path(point)`;
- `valid_path_target(point)`.

![Hành lang quỹ đạo dự đoán dùng để lọc mục tiêu radar](../assets/predicted_path_corridor.svg)

**Hình 3.8: Hành lang quỹ đạo dự đoán dùng để lọc mục tiêu radar.**

### 3.7.1. Đầu Vào Của Bước Dự Đoán Quỹ Đạo

Đầu vào không phải bản đồ HD, lane id hay ground truth của CARLA. Thuật toán chỉ
dùng trạng thái chuyển động hiện tại của ego:

- vận tốc ego $v_{ego}$ từ `ego.get_velocity()`;
- yaw rate $\omega_{yaw}$ từ `ego.get_angular_velocity().z`;
- lệnh lái hiện tại $\delta$ từ `ego.get_control().steer`;
- các hằng số cấu hình trong `configs/sensors.yaml`.

Điều này giúp thuật toán gần với tư duy xe thật hơn: xe tự dự đoán đường đi ngắn
hạn dựa trên chuyển động và góc lái của chính nó, không dựa vào thông tin “biết
sẵn” của simulator.

### 3.7.2. Ước Lượng Độ Cong Quỹ Đạo

Quỹ đạo được xấp xỉ bằng mô hình độ cong không đổi. Nếu ego đang chạy đủ nhanh
và yaw rate đủ rõ, độ cong từ yaw rate được tính:

$$
\kappa_{yaw} = \frac{\omega_{yaw}}{v_{ego}}
$$

Trong đó:

- $\kappa$ là độ cong, đơn vị $1/m$;
- $\omega_{yaw}$ là tốc độ quay thân xe quanh trục đứng, đơn vị rad/s;
- $v_{ego}$ là vận tốc ego, đơn vị m/s.

Song song, thuật toán ước lượng độ cong từ góc lái:

$$
\kappa_{steer} = k_{steer}\delta
$$

Với $\delta$ là lệnh lái chuẩn hóa trong CARLA và $k_{steer}$ là hệ số
`path_steer_curvature_per_unit`.

Trong code, nếu:

$$
v_{ego} \geq v_{min}
$$

và:

$$
|\omega_{yaw}| \geq \omega_{min}
$$

thì độ cong mong muốn được trộn từ yaw rate và góc lái:

$$
\kappa_{desired} = 0.75\kappa_{yaw} + 0.25\kappa_{steer}
$$

Nếu xe đi chậm hoặc yaw rate quá nhỏ, thuật toán dùng:

$$
\kappa_{desired} = \kappa_{steer}
$$

Cách trộn này giúp quỹ đạo bám theo chuyển động thật của xe khi đang cua, nhưng
vẫn có fallback từ lệnh lái khi yaw rate chưa đủ tin cậy.

### 3.7.3. Giới Hạn Và Làm Mượt Độ Cong

Độ cong mong muốn được giới hạn để tránh sinh quỹ đạo quá gắt:

$$
\kappa_{desired} =
\text{clip}(\kappa_{desired},-\kappa_{max},\kappa_{max})
$$

Sau đó thuật toán làm mượt theo thời gian:

$$
\kappa_t = \kappa_{t-1} + \alpha(\kappa_{desired}-\kappa_{t-1})
$$

Trong đó $\alpha$ là `path_curvature_smoothing`. Nếu $\alpha$ nhỏ, quỹ đạo đổi
chậm và ổn định hơn; nếu $\alpha$ lớn, quỹ đạo phản ứng nhanh hơn nhưng dễ rung
do nhiễu yaw rate/góc lái. Bản hiện tại dùng $\alpha=0.35$ để cân bằng hai yếu
tố này.

### 3.7.4. Sinh Các Điểm Quỹ Đạo Phía Trước

Sau khi có độ cong $\kappa_t$, hàm `constant_curvature_path()` sinh danh sách
điểm:

```text
(x_forward, y_right, heading)
```

theo từng bước khoảng cách $s$. Trong đó $s$ là chiều dài cung dọc theo quỹ đạo
dự đoán, tính từ vị trí hiện tại của ego về phía trước; $s=0$ tại vị trí hiện
tại của xe và tăng dần theo hướng xe dự kiến di chuyển. Với quỹ đạo cong:

$$
\theta(s) = \kappa s
$$

$$
x(s) = \frac{\sin(\theta)}{\kappa}
$$

$$
y(s) = \frac{1-\cos(\theta)}{\kappa}
$$

Khi $|\kappa|$ rất nhỏ, thuật toán coi ego đang đi thẳng:

$$
x(s)=s,\quad y(s)=0
$$

Để tránh quỹ đạo dự đoán kéo quá dài trong cua gắt, vòng lặp sinh điểm dừng nếu:

$$
|\theta(s)| > \theta_{max}
$$

hoặc:

$$
|y(s)| > y_{path,max}
$$

### 3.7.5. Tầm Dự Đoán

Tầm dự đoán phụ thuộc vào vận tốc ego:

$$
L = \min(R_{radar}, \max(L_{min}, v_{ego}T_{horizon}))
$$

Nếu ego chạy chậm, quỹ đạo vẫn có tối thiểu $L_{min}$ để lọc điểm gần phía
trước. Nếu ego chạy nhanh, quỹ đạo dài hơn nhưng không vượt quá tầm radar.

**Bảng 3.10: Các hằng số chính trong dự đoán quỹ đạo ego.**

| Tham số | Giá trị | Ý nghĩa |
|---|---:|---|
| `path_sample_step_m` | 1.0 m | Khoảng cách giữa hai điểm quỹ đạo liên tiếp |
| `path_horizon_time_s` | 2.5 s | Thời gian dự đoán phía trước theo vận tốc ego |
| `path_min_horizon_m` | 12.0 m | Tầm dự đoán tối thiểu |
| `path_max_lateral_deviation_m` | 6.0 m | Giới hạn lệch ngang tối đa của quỹ đạo |
| `path_min_speed_for_yaw_rate_mps` | 1.0 m/s | Vận tốc tối thiểu để tin yaw rate |
| `path_min_yaw_rate_deg_s` | 0.5 độ/s | Yaw rate tối thiểu để dùng công thức yaw |
| `path_steer_curvature_per_unit` | 0.06 1/m | Hệ số đổi lệnh lái sang độ cong |
| `path_max_abs_curvature_1pm` | 0.12 1/m | Giới hạn độ cong tuyệt đối |
| `path_curvature_smoothing` | 0.35 | Hệ số làm mượt độ cong |
| `path_max_heading_change_deg` | 75 độ | Giới hạn đổi hướng tối đa của path |

### 3.7.6. Tính Khoảng Cách Từ Radar Point Tới Quỹ Đạo

Sau khi có predicted path, hàm `distance_to_predicted_path(point)` tính khoảng
cách nhỏ nhất từ radar point tới các đoạn thẳng liên tiếp của quỹ đạo. Với một
đoạn path từ $A(x_a,y_a)$ tới $B(x_b,y_b)$ và radar point $P(x_p,y_p)$, hệ số
chiếu lên đoạn thẳng là:

$$
t =
\frac{(P-A)\cdot(B-A)}{\|B-A\|^2}
$$

Sau đó giới hạn:

$$
t = \text{clip}(t,0,1)
$$

Điểm gần nhất trên đoạn:

$$
Q = A + t(B-A)
$$

Khoảng cách tới đoạn:

$$
d_{path} = \sqrt{(x_p-x_q)^2+(y_p-y_q)^2}
$$

Thuật toán lấy giá trị nhỏ nhất qua toàn bộ các đoạn path. Radar point/object
chỉ được coi là ứng viên AEB nếu:

$$
d_{path} \leq y_{AEB}
$$

Trong đó $y_{AEB}$ lấy từ `max_lateral_offset_m=1.25m`. Đây là một trong các
bước quan trọng giúp loại xe làn bên và vật thể ngoài quỹ đạo.

### 3.7.7. Đầu Ra Và Vai Trò Trong Pipeline

Đầu ra của bước này gồm:

- `predicted_path`: danh sách điểm $(x_{forward}, y_{right}, heading)$;
- `path_curvature_1pm`: độ cong hiện tại;
- `path_horizon_m`: tầm dự đoán hiện tại;
- `path_description()`: mô tả debug như `straight`, `left R=...m`,
  `right R=...m`;
- kết quả lọc `valid_path_target(point)`.

Trong pipeline tổng thể:

```text
ego speed + yaw rate + steering
  -> update_predicted_path()
  -> predicted_path
  -> distance_to_predicted_path(point)
  -> valid_path_target(point)
  -> radar object candidates
```

Ưu điểm của cách này là giảm phanh nhầm so với chỉ dùng FOV radar. Hạn chế là
mô hình độ cong không đổi chỉ phù hợp dự đoán ngắn hạn. Nếu xe đánh lái đột ngột
hoặc gặp đường cong thay đổi nhanh, predicted path có thể lệch. Vì vậy đồ án chỉ
dùng path này như bộ lọc mục tiêu AEB trong vài giây phía trước xe, không dùng
như thuật toán lập kế hoạch chuyển động dài hạn.

## 3.8. Chọn Mục Tiêu, Đánh Giá Rủi Ro Va Chạm Và Điều Khiển Phanh PID

Sau khi đã có radar object, YOLO detection, fusion gate, TTC, khoảng cách dừng
và predicted path, hệ thống phải quyết định:

1. mục tiêu nào là mục tiêu AEB chính;
2. mức rủi ro hiện tại là gì;
3. có cần override lệnh điều khiển xe hay không;
4. nếu phanh thì phanh với lực bao nhiêu.

Luồng dữ liệu của khối quyết định/phanh có thể tóm tắt như sau:

```text
RadarObject đã xác nhận
  -> kiểm tra hành lang quỹ đạo dự đoán
  -> xác nhận bằng YOLO/fusion
  -> tính TTC và khoảng cách dừng
  -> đánh giá mức nguy hiểm
  -> staged PID giới hạn lực phanh theo tầng
  -> lệnh brake gửi tới xe ego
```

Phần này chủ yếu nằm trong:

- `core/target_selector.py::select_aeb_target`;
- `core/radar_aeb_pipeline.py::process`, `_target_ready_for_brake`;
- `control/brake.py::BinaryAEB.decide`;
- `control/brake.py::_desired_state`, `_apply_hysteresis`,
  `_pid_brake_command`, `_staged_pid_target`;
- `control/brake.py::make_brake_control`, `apply_brake_override`.

### 3.8.1. Chọn Mục Tiêu AEB

Sau radar clustering/tracking, hệ thống có thể có nhiều `RadarObject`. Mục tiêu
AEB không nhất thiết là object gần nhất tuyệt đối, mà là object có nguy cơ va
chạm cao nhất trên quỹ đạo dự đoán.

Hàm `select_aeb_target()` chọn mục tiêu theo thứ tự:

1. chỉ xét object đã `confirmed=True`;
2. bỏ object stale hoặc mất dấu;
3. tính TTC bằng `compute_ttc()`;
4. ưu tiên object có TTC hữu hạn nhỏ nhất;
5. nếu TTC không hữu hạn hoặc tương đương, ưu tiên object có khoảng cách dọc nhỏ
   hơn.

Có thể mô tả khóa ưu tiên bằng biến chỉ báo $q_i$:

$$
q_i =
\begin{cases}
0, & TTC_i < \infty \\
1, & TTC_i = \infty
\end{cases}
$$

$$
target = \arg\min_i \left(q_i,\ TTC_i,\ x_i\right)
$$

Trong đó phép tối thiểu được hiểu theo thứ tự từ điển: object có TTC hữu hạn
($q_i=0$) được ưu tiên; sau đó chọn TTC nhỏ nhất và cuối cùng là khoảng cách dọc
nhỏ nhất. Quy ước này khớp với hàm `select_aeb_target()` trong mã nguồn.

Ở bản có fusion, target radar còn phải được camera/YOLO xác nhận. Nếu radar
target không chiếu vào bbox `car`, fusion gate có thể chặn lệnh phanh để giảm
phanh nhầm.

### 3.8.2. Target Gate Trước Khi Phanh

Ngay cả khi radar đã chọn được target, hệ thống vẫn không phanh ngay lập tức
trong mọi trường hợp. `RadarAEBPipeline` có target gate để tránh object xuất
hiện thoáng qua gây phanh nhầm.

Target được coi là sẵn sàng phanh nếu một trong hai điều kiện đúng:

- target đã được chọn ổn định đủ `selected_confirm_frames=5` frame;
- tình huống đủ khẩn cấp để phanh ngay, ví dụ khoảng cách nhỏ hơn
  `immediate_brake_distance_m=22m` hoặc `distance_margin_m` thấp hơn ngưỡng
  `immediate_distance_margin_m=-4m`.

Như vậy hệ thống có hai lớp bảo vệ:

- radar object phải được tracking xác nhận qua nhiều frame;
- target đã chọn phải ổn định qua target gate, trừ trường hợp khẩn cấp.

### 3.8.3. Đánh Giá Trạng Thái Rủi Ro

Trong `control/brake.py`, máy trạng thái chính có bốn trạng thái logic:

- `NORMAL`: không có nguy cơ hợp lệ;
- `WARNING`: TTC thấp hơn ngưỡng cảnh báo nhưng chưa tới mức phanh;
- `BRAKE`: cần override phanh;
- `RELEASE`: nhả phanh sau khi nguy cơ giảm.

Hàm `_desired_state()` quyết định trạng thái mong muốn từ TTC:

$$
state =
\begin{cases}
BRAKE, & TTC \leq brake\_ttc \\
WARNING, & TTC \leq warning\_ttc \\
NORMAL, & TTC > warning\_ttc
\end{cases}
$$

Với cấu hình hiện tại:

- `warning_ttc_s = 3.0s`;
- `brake_ttc_s = 1.5s`;
- `release_ttc_s = 3.5s`.

Ngoài TTC, nếu `use_stopping_distance=true`, hệ thống cũng phanh khi:

$$
d_{margin} \leq d_{threshold}
$$

Trong đó $d_{margin}=d-d_{required}$ đã trình bày ở mục 3.4. Điều này giúp hệ
thống phản ứng sớm ở tốc độ cao, vì TTC đơn thuần có thể chưa phản ánh đủ quãng
đường cần để dừng.

### 3.8.4. Hysteresis Và Điều Kiện Nhả Phanh

Hệ thống dùng hysteresis để tránh trạng thái phanh nhấp nhả liên tục. Hàm
`_apply_hysteresis()` giữ trạng thái `BRAKE` nếu:

- thời gian giữ phanh tối thiểu chưa hết: `min_brake_hold_time_s=0.3s`;
- đang bật `hold_brake_until_stopped=true` và xe chưa dừng;
- TTC vẫn chưa vượt ngưỡng nhả `release_ttc_s`.

Nếu nguy cơ giảm và các điều kiện giữ phanh không còn đúng, trạng thái chuyển
sang `RELEASE`, lệnh phanh về 0. Tùy mục tiêu kiểm thử, dự án có thể chạy theo hai
kiểu:

- validation mode: giữ phanh đến khi xe dừng để đo khoảng cách cuối;
- driving-after-AEB mode: nhả phanh khi nguy cơ hết để mô phỏng xe thật tiếp tục
  chạy.

### 3.8.5. Các Chế Độ Phanh Đã Phát Triển

Đồ án giữ nhiều chế độ phanh để so sánh trong quá trình phát triển.

**Bảng 3.11: So sánh các chế độ phanh trong đồ án.**

| Chế độ | Nguyên lý | Vai trò |
|---|---|---|
| `binary` | Có nguy hiểm thì phanh 1.0 | Baseline đơn giản, dễ kiểm lỗi logic target |
| `staged` | Chia mức rủi ro, mỗi mức có lực phanh cố định | Kiểm tra máy trạng thái nhiều tầng |
| `pid_v1` | PID theo sai số khoảng cách/TTC | Bắt đầu điều khiển phanh liên tục |
| `pid_v2_comfort` | PID mềm hơn, có target margin và lateral gate | Giảm phanh nhầm, tăng độ êm |
| `staged_pid` | Chia tầng rủi ro + PID và giới hạn lực theo tầng | Bản chính hiện tại |

### 3.8.6. Công Thức PID

Trong chế độ PID, lệnh phanh không còn là 0 hoặc 1 tuyệt đối. Thuật toán tạo sai
số từ hai thành phần: thiếu khoảng cách an toàn và TTC thấp.

Sai số khoảng cách:

$$
e_d = \max(0,\ d_{threshold} - d_{margin} - d_{deadband})
$$

Sai số TTC:

$$
e_{ttc} = \max(0,\ brake\_ttc - TTC)
$$

Sai số tổng:

$$
e = e_d + k_{ttc}e_{ttc}
$$

Trong code, $k_{ttc}$ là `pid_ttc_kp`. Thành phần tích phân:

$$
I_t = \text{clip}(I_{t-1}+e\Delta t,\ -I_{max},\ I_{max})
$$

Thành phần đạo hàm chỉ lấy phần tăng sai số, không cho đạo hàm âm làm giảm
phanh quá nhanh:

$$
D_t = \max(0,\frac{e_t-e_{t-1}}{\Delta t})
$$

Lệnh phanh mục tiêu:

$$
b_{target} = b_{min} + K_p e + K_i I_t + K_d D_t
$$

Sau đó giới hạn:

$$
b_{target} = \text{clip}(b_{target}, b_{min}, b_{max})
$$

### 3.8.7. Staged PID

Staged PID là bản chính hiện tại. Ý tưởng là PID tính mức phanh liên tục, nhưng
mức phanh đó bị giới hạn bởi tầng rủi ro. Tầng rủi ro quyết định "được phép
phanh mạnh tới đâu", PID quyết định "trong giới hạn đó nên phanh bao nhiêu".

```text
SAFE/NORMAL -> không phanh
WARNING     -> cảnh báo, chưa override phanh
SOFT        -> PID bị giới hạn ở vùng phanh nhẹ
MEDIUM      -> PID được phép phanh trung bình
HARD        -> PID được phép phanh mạnh
EMERGENCY   -> cho phép phanh 1.0
RELEASE     -> nhả phanh khi nguy cơ giảm
```

![Máy trạng thái AEB nhiều tầng](../assets/aeb_staged_pid_state_machine.svg)

**Hình 3.9: Máy trạng thái AEB nhiều tầng.**

Trong code, `_staged_pid_target()` giới hạn phanh theo các điều kiện:

- nếu khoảng cách rất gần, $d \leq staged\_emergency\_distance$, phanh emergency;
- nếu $d_{margin} \leq staged\_emergency\_margin$, phanh emergency;
- nếu $TTC \leq staged\_emergency\_ttc$, phanh emergency;
- nếu $d_{margin} \leq staged\_hard\_margin$ hoặc
  $TTC \leq staged\_hard\_ttc$, cho phép vùng hard;
- nếu $d_{margin} \leq 0$ hoặc $TTC \leq brake\_ttc$, cho phép vùng medium;
- nếu chưa tới các ngưỡng trên, chỉ cho phép vùng soft.

**Bảng 3.12: Các hằng số chính của thuật toán staged PID.**

| Nhóm | Tham số | Giá trị | Ý nghĩa |
|---|---|---:|---|
| State | `warning_ttc_s` | 3.0 s | Bắt đầu cảnh báo |
| State | `brake_ttc_s` | 1.5 s | Bắt đầu phanh theo TTC |
| State | `release_ttc_s` | 3.5 s | Nhả phanh khi TTC phục hồi |
| Staged brake | `staged_soft_brake` | 0.55 | Trần/giá trị phanh vùng soft |
| Staged brake | `staged_medium_brake` | 0.75 | Trần/giá trị phanh vùng medium |
| Staged brake | `staged_hard_brake` | 0.90 | Trần/giá trị phanh vùng hard |
| Staged brake | `staged_emergency_brake` | 1.00 | Phanh khẩn cấp tối đa |
| Staged risk | `staged_hard_ttc_s` | 1.10 s | Ngưỡng hard theo TTC |
| Staged risk | `staged_emergency_ttc_s` | 0.80 s | Ngưỡng emergency theo TTC |
| Staged risk | `staged_hard_margin_m` | -2.0 m | Ngưỡng hard theo thiếu khoảng cách |
| Staged risk | `staged_emergency_margin_m` | -5.0 m | Ngưỡng emergency theo thiếu khoảng cách |
| PID | `pid_kp`, `pid_ki`, `pid_kd` | 0.12 / 0.01 / 0.0 | Hệ số PID |
| PID | `pid_ttc_kp` | 0.12 | Trọng số sai số TTC |
| PID | `pid_min_brake`, `pid_max_brake` | 0.25 / 1.0 | Biên lệnh phanh PID |
| PID | `pid_target_margin_m` | 4.0 m | Biên khoảng cách mong muốn cho PID |
| PID | `pid_target_margin_max_lateral_m` | 0.95 m | Chỉ cộng target margin khi target gần tâm làn ego |
| Rate limit | `pid_brake_rise_rate_per_s` | 3.0 /s | Tốc độ tăng phanh thường |
| Rate limit | `pid_brake_fall_rate_per_s` | 1.5 /s | Tốc độ giảm phanh |
| Rate limit | `pid_emergency_rise_rate_per_s` | 20.0 /s | Tốc độ tăng phanh khẩn cấp |

### 3.8.8. Giới Hạn Tốc Độ Tăng/Giảm Phanh

Sau khi có $b_{target}$, hệ thống không nhảy ngay tới giá trị đó trong điều kiện
thường. Hàm `_rate_limited_brake()` giới hạn tốc độ tăng/giảm lệnh phanh:

$$
b_t =
\min(b_{target}, b_{t-1}+r_{rise}\Delta t)
$$

khi target lớn hơn phanh hiện tại, và:

$$
b_t =
\max(b_{target}, b_{t-1}-r_{fall}\Delta t)
$$

khi target nhỏ hơn phanh hiện tại. Trong emergency, tốc độ tăng dùng
`pid_emergency_rise_rate_per_s=20.0/s`, cho phép phanh lên nhanh gần như tức
thời. Trong điều kiện thường, `pid_brake_rise_rate_per_s=3.0/s` giúp lệnh phanh
mượt hơn.

### 3.8.9. Override Lệnh Điều Khiển Xe

Khi `AEBDecision.state == BRAKE`, hàm `make_brake_control()` ghi đè lệnh điều
khiển:

```text
throttle = 0
brake    = decision.brake
hand_brake = false
```

Khi `state == RELEASE`, brake được trả về 0 để tài xế hoặc scenario controller
có thể tiếp tục điều khiển. Như vậy output cuối của thuật toán là:

- `state`: trạng thái AEB;
- `brake`: lệnh phanh 0-1;
- `throttle`: thường bằng 0 khi AEB can thiệp;
- `should_override`: có ghi đè điều khiển xe hay không;
- `reason`: lý do quyết định, dùng cho log và báo cáo;
- `ttc_s`, `required_distance_m`, `distance_margin_m`: các đại lượng đánh giá.

### 3.8.10. Nhận Xét Về Thuật Toán Cuối

Staged PID giống thực tế hơn binary brake vì có cảnh báo, phanh tăng dần và
phanh khẩn cấp. Tuy nhiên nó vẫn là mô hình điều khiển đơn giản trong mô phỏng:

- chưa mô phỏng sâu hệ thống thủy lực/phanh thật;
- jerk trong CARLA có spike và chỉ nên dùng để so sánh tương đối;
- chất lượng phụ thuộc vào target selection, radar object tracking và YOLO
  confirmation;
- ngoài dải vận tốc/khoảng cách thiết kế, hệ thống vẫn có thể không tránh được
  va chạm, đây chính là giới hạn cần báo cáo.

Trong phạm vi đồ án, staged PID được chọn làm bản cuối vì cân bằng giữa an toàn
và độ êm: đủ mạnh để tránh va chạm trong dải mục tiêu 50-80 km/h, nhưng giảm
được hiện tượng phanh nhầm/phanh gắt không cần thiết so với binary brake.
