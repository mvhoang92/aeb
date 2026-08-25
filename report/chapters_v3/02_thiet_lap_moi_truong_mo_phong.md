# Chương 2. Thiết Lập Môi Trường Mô Phỏng

Chương này trình bày môi trường mô phỏng dùng trong đồ án, cơ sở lựa chọn cảm
biến và cách thiết lập xe ego, camera, radar trong CARLA. Mục tiêu của chương
không phải mô tả thuật toán AEB chi tiết, mà làm rõ hệ thống được đặt trong môi
trường nào, dữ liệu đầu vào đến từ đâu và các giả thiết mô phỏng được cấu hình
như thế nào. Các thuật toán xử lý radar, camera, hợp nhất dữ liệu, TTC và điều
khiển phanh được trình bày ở Chương 3.

## 2.1. Thiết Lập Môi Trường

CARLA là nền tảng mô phỏng mã nguồn mở phục vụ nghiên cứu xe tự hành và ADAS.
CARLA cung cấp môi trường 3D, bản đồ đô thị/cao tốc, phương tiện, người đi bộ,
đèn giao thông, cảm biến mô phỏng và API Python để điều khiển kịch bản. Đối với
đồ án này, CARLA cho phép kiểm thử AEB trong các tình huống nguy hiểm mà không
cần thử nghiệm trên xe thật.

Phiên bản được sử dụng là CARLA 0.9.11. Lý do chọn phiên bản này gồm:

- tương thích với môi trường Python 3.7 và các ví dụ mẫu của CARLA đang dùng;
- có sẵn `manual_control.py`, đây là nền tảng để mở rộng giao diện quan sát;
- hỗ trợ camera RGB, radar, collision sensor và API điều khiển actor;
- đủ ổn định cho mục tiêu mô phỏng car-to-car trên cao tốc.

Đồ án tập trung vào bản đồ Town04 vì bản đồ này có các đoạn đường rộng, nhiều
làn và phù hợp với bài toán cao tốc. Xe ego được chọn là Tesla Model 3
(`vehicle.tesla.model3`) để thống nhất cấu hình phương tiện trong toàn bộ dự án.

**Bảng 2.1: Cấu hình máy và môi trường thực nghiệm.**

| Thành phần | Cấu hình |
|---|---|
| OS | Ubuntu 22.04.5 LTS |
| CPU | Intel Core i5-11400H, 6 nhân 12 luồng |
| RAM | 16 GiB |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU, 4 GiB VRAM |
| NVIDIA driver | 580.159.04 |
| CARLA | 0.9.11 |
| Python CARLA | Python 3.7.17 |
| Python YOLO | Python 3.10 trong `.venv_yolo310` |

Dự án được đặt cạnh thư mục cài đặt CARLA để sử dụng thuận tiện Python API và
các ví dụ đi kèm. Cấu trúc triển khai tổng quát là:

```text
<CARLA_ROOT>/
├── CarlaUE4.sh
├── PythonAPI/
├── venv/
└── aeb/
```

CARLA được chạy với cấu hình đồ họa phù hợp GPU thử nghiệm; cờ `-opengl` không
được dùng vì từng gây mất ổn định khi hiển thị Pygame/manual control. Hướng dẫn
cài đặt và lệnh chạy chi tiết được tách sang `README.md` để báo cáo tập trung vào
thiết kế và kết quả kỹ thuật. Khi đưa lên GitHub, chỉ thư mục `aeb/` được quản
lý như một dự án riêng; dataset, video, log lớn và model archive được loại khỏi
Git bằng `.gitignore`.

## 2.2. Cấu Hình Xe Và Cảm Biến

AEB thực tế thường dùng kết hợp nhiều cảm biến. Camera mạnh về nhận dạng hình
dạng, làn đường và lớp đối tượng; radar mạnh về khoảng cách và vận tốc tương
đối; LiDAR cho hình học 3D chính xác nhưng chi phí cao; ultrasonic phù hợp
khoảng cách gần; IMU/wheel speed giúp xác định trạng thái chuyển động của ego.

Không có cảm biến nào hoàn hảo trong mọi điều kiện. Camera phụ thuộc vào ánh
sáng và không đo trực tiếp vận tốc tương đối. Radar ít phụ thuộc ánh sáng, đo
tốt khoảng cách/vận tốc, nhưng đầu ra thưa và khó phân loại hình dạng. Vì vậy,
nhiều hệ thống AEB thực tế dùng camera-radar fusion: radar cung cấp đại lượng
động học, camera xác nhận ngữ nghĩa của đối tượng.

**Bảng 2.2: So sánh các cảm biến thường dùng trong ADAS/AEB.**

| Cảm biến | Đầu ra chính | Ưu điểm | Hạn chế |
|---|---|---|---|
| Camera | Ảnh RGB, lớp đối tượng, bounding box | Nhận dạng đối tượng tốt, giàu thông tin ngữ cảnh | Nhạy với ánh sáng, không đo trực tiếp vận tốc tương đối |
| Radar | Range, relative velocity, angle | Đo khoảng cách/vận tốc tốt, phù hợp car-to-car | Point thưa, khó phân loại hình dạng |
| LiDAR | Point cloud 3D | Hình học chính xác | Giá thành cao, dữ liệu nặng |
| Ultrasonic | Khoảng cách gần | Rẻ, tốt cho parking | Tầm rất ngắn |
| IMU/wheel speed | Vận tốc, gia tốc, yaw rate | Hỗ trợ dự đoán quỹ đạo ego | Không tự phát hiện vật thể |

Ngoài đặc tính kỹ thuật riêng của từng cảm biến, cấu hình cảm biến trong đồ án
cũng được chọn dựa trên cách các hệ thống ADAS/AEB thương mại thường được triển
khai. Các hãng xe không luôn công bố đầy đủ thông số nội bộ của cảm biến, nhưng
tài liệu người dùng và tài liệu giới thiệu hệ thống cho thấy một số hướng cấu
hình phổ biến như sau.

**Bảng 2.3: Một số cấu hình cảm biến tham khảo từ hệ thống ADAS/AEB thương mại.**

| Hệ thống tham khảo | Cấu hình cảm biến được công bố ở mức khái niệm | Nhận xét cho đồ án |
|---|---|---|
| Toyota Safety Sense / Pre-Collision System | Camera phía trước kết hợp radar hoặc laser/radar tùy thế hệ [15] | Củng cố hướng dùng camera để nhận dạng và radar để hỗ trợ phát hiện va chạm phía trước |
| Honda Sensing / CMBS | Radar transmitter kết hợp forward-facing camera; radar đặt phía trước, camera đặt sau kính lái [16] | Gần với cấu hình mô phỏng của đồ án: camera sau kính lái và radar ở mũi xe |
| Subaru EyeSight | Hướng camera stereo, hỗ trợ cảnh báo và phanh trước va chạm [17] | Cho thấy camera có thể đảm nhiệm nhiều chức năng ADAS, nhưng việc đo động học chỉ bằng camera khó hơn radar |
| Mobileye Base ADAS | Một camera phía trước có thể hỗ trợ nhiều chức năng ADAS, gồm AEB [18] | Cho thấy camera-only là một hướng khả thi, nhưng trong đồ án vẫn dùng thêm radar để có khoảng cách/vận tốc trực tiếp |

Ở mức thông số, các cảm biến thương mại có thể có tầm đo và góc nhìn lớn hơn
đáng kể so với cấu hình mô phỏng của đồ án. Tuy nhiên, đồ án không đặt mục tiêu
mô phỏng đầy đủ phần cứng ADAS thương mại, mà cần một cấu hình đủ đại diện cho
bài toán cao tốc car-to-car, chạy ổn định trên máy cá nhân và giảm phanh nhầm
từ làn bên. Vì vậy, thông số cảm biến trong CARLA được chọn theo hướng tối giản
có kiểm soát.

**Bảng 2.4: So sánh thông số cảm biến tham khảo và cấu hình trong đồ án.**

| Nhóm cảm biến | Thông số tham khảo công bố công khai | Cấu hình trong đồ án | Lý do lựa chọn trong đồ án |
|---|---|---|---|
| Camera ADAS trước | ZF Smart Camera 4.8 dùng cảm biến 1,7 MP và FOV ngang tới 100 độ [19] | Camera RGB 1280x720, FOV 70 độ, 20 FPS | FOV 70 độ đủ bao phủ làn ego và vùng trước xe; giảm tải render/suy luận YOLO so với FOV rất rộng |
| Camera-first ADAS | Mobileye Base Driver Assist dùng một camera trước cho các chức năng ADAS cơ bản [18] | Một camera trước làm nguồn xác nhận `car` cho fusion | Giữ pipeline đơn giản: camera xác nhận mục tiêu, radar đo khoảng cách/vận tốc |
| Radar trước tầm trung | Bosch radar sensor công bố khoảng đo 0,23-160 m, FOV ngang ±75 độ và dọc ±15 độ [20] | Radar range 100 m, FOV ngang 30 độ, dọc 6 độ, 20 FPS | Tầm 100 m đủ cho dải mục tiêu 50-80 km/h; FOV hẹp tập trung vào làn trước để giảm nhiễu từ làn bên/lan can |
| Radar trước tầm xa | Continental long-range radar thế hệ mới có thể đạt tới 300 m và góc mở ±60 độ tùy cấu hình [21] | Không dùng radar tầm xa 300 m; giữ 100 m trong CARLA | Radar tầm xa phù hợp hệ thống thương mại/đa tình huống; đồ án chỉ kiểm thử cao tốc lý tưởng, car-to-car, nên ưu tiên ổn định và dễ đánh giá |

Trong phạm vi đồ án, hệ thống sử dụng một camera RGB phía trước, một radar phía
trước và trạng thái ego làm cảm biến phụ. Cấu hình này phù hợp với bài toán
car-to-car trên cao tốc: radar đo khoảng cách/vận tốc của xe phía trước, camera
xác nhận vật thể là ô tô, còn trạng thái ego hỗ trợ dự đoán hành lang di chuyển.
Như vậy, cấu hình của đồ án không cố gắng mô phỏng đầy đủ một xe thương mại cụ
thể, mà chọn cấu hình tối giản nhưng có cơ sở thực tế: một cảm biến thị giác để
nhận dạng mục tiêu, một radar phía trước để đo động học và trạng thái ego để
đánh giá mục tiêu có nằm trên đường đi dự kiến hay không.

Xe ego là Tesla Model 3. Camera được đặt sau kính lái để mô phỏng camera ADAS
phía trước. Radar được đặt ở mũi xe để đo vật thể phía trước. Vị trí cảm biến
được kiểm chứng bằng script `scripts/visualize_sensor_coverage.py`.

Vị trí cảm biến không được chọn tùy ý. Camera cần nằm gần vùng sau kính lái,
cao hơn mặt taplo và hướng về phía trước. Radar cần nằm gần mũi xe và trục giữa
thân xe để vùng quét đối xứng theo phương tiến. Trong quá trình phát triển,
camera/radar đã được kiểm tra bằng hình chiếu cạnh và góc nhìn từ trên xuống để
tránh lỗi radar bị thụt vào xe hoặc camera nhô quá xa khỏi kính lái.

![Vị trí cảm biến theo góc nhìn cạnh](assets/evidence/sensor_near_side_view.png)

**Hình 2.1: Vị trí camera và radar trên Tesla Model 3 theo góc nhìn cạnh.**

![Tầm phủ cảm biến theo góc nhìn từ trên xuống](assets/evidence/sensor_far_top_view.png)

**Hình 2.2: Tầm phủ camera và radar theo góc nhìn từ trên xuống.**

**Bảng 2.5: Cấu hình camera trong đồ án.**

| Thuộc tính | Giá trị |
|---|---|
| Loại | `sensor.camera.rgb` |
| Vị trí | Sau kính lái |
| Transform | `x=0.43`, `y=0.0`, `z=1.35` |
| FOV | 70 độ |
| Độ phân giải | 1280x720 |
| Sensor tick | 0.05 s, tương đương 20 FPS |

**Bảng 2.6: Cấu hình radar trong đồ án.**

| Thuộc tính | Giá trị |
|---|---|
| Loại | `sensor.other.radar` |
| Vị trí | Mũi xe |
| Transform | `x=2.53`, `y=0.0`, `z=0.48` |
| Range | 100 m |
| FOV ngang/dọc | 30 độ / 6 độ |
| Points per second | 2000 |
| Sensor tick | 0.05 s, tương đương 20 FPS |

Khi chạy kiểm thử hàng loạt và ghi nhật ký, dự án ưu tiên synchronous mode với:

```text
fixed_delta_seconds = 0.05
```

Tức phần mô phỏng chạy logic ở 20 Hz. Phần hiển thị Pygame/video có thể chỉ đạt
17-18 FPS khi render nặng, nhưng nhật ký định lượng vẫn dựa trên thời gian mô
phỏng và tick cố định. Vì vậy, đánh giá đạt/không đạt dựa trên log dữ liệu,
không dựa trên độ mượt của video.

Giao diện minh họa cuối cùng gồm ba vùng:

- màn camera + YOLO + hợp nhất dữ liệu ở phía trên trái;
- màn quan sát xe/góc nhìn điều khiển phía dưới trái;
- màn radar bird-eye ở bên phải.

![Giao diện minh họa cuối cùng gồm 3 màn hình](assets/evidence/final_demo_cutin_80_50_gap_25.jpg)

**Hình 2.3: Giao diện minh họa cuối cùng gồm 3 màn hình.**

Giao diện này giúp người xem thấy đồng thời ba lớp thông tin: ảnh camera/YOLO/fusion,
chuyển động xe trong CARLA và phân bố mục tiêu radar theo bird-eye view. Đây là
công cụ quan trọng để kiểm chứng trực quan các quyết định của AEB trước khi đưa
kết quả vào báo cáo.

## 2.3. Protocol GPU Và Cô Lập Tiến Trình

Final campaign được chạy tại commit `3be8ae4`, tag
`safe-fallback-eval-v1`. ONNX Runtime bắt buộc kích hoạt
`CUDAExecutionProvider`; nếu session rơi về CPU hoặc inference phát sinh lỗi,
master runner dừng kỹ thuật. Hard gate và safe fallback dùng cùng model hash,
input 640 px và cadence 0,15 s theo simulation timestamp. Radar-only không tạo
YOLO session.

CARLA 0.9.11 có thể tích lũy VRAM khi liên tục spawn/destroy camera. Vì vậy, thay
vì `reload_world()`, master runner khởi động một server Town04 mới cho mỗi named
scenario, chạy toàn bộ repeat của scenario đó, ghi checkpoint rồi dừng hẳn tiến
trình. Chiến dịch cuối gồm 639 server sessions. Nếu server lỗi, cùng run ID được
resume và các cặp `(scenario_id, run_index)` đã hoàn thành bị bỏ qua.

**Bảng 2.7: Kiểm soát khả năng tái lập của final campaign.**

| Thành phần | Kiểm soát |
|---|---|
| Vật lý | synchronous mode, fixed step 0,05 s |
| Random seed | 2026, lưu trong metadata |
| Thuật toán | commit/tag và config snapshot SHA-256 |
| Model | ONNX model SHA-256 và active provider |
| Tài nguyên | restart server sau mỗi named scenario |
| Lỗi kỹ thuật | retry tối đa 2 lần, checkpoint/resume |
| Lỗi thuật toán | không dừng campaign, giữ nguyên FAIL |
| Hold-out | chạy cuối, không tuning sau khi xem kết quả |

Cách này không biến năm repeat thành năm mẫu giao thông độc lập; nó chỉ hạn chế
carry-over tài nguyên và cho phép kiểm tra tính nhất quán trong cùng điều kiện.
