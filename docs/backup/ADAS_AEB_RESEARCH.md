# Phần I - Cơ Sở Lý Thuyết Và Nghiên Cứu Liên Quan Về ADAS/AEB

Ngày cập nhật và kiểm tra nguồn: 06/06/2026.

## 1. Mục Tiêu Và Phạm Vi

Tài liệu này tổng hợp:

- Khái niệm và các nhóm chức năng của ADAS.
- Vai trò, ưu nhược điểm của camera, radar, LiDAR, siêu âm, IMU và bản đồ.
- Pipeline xử lý AEB từ nhận biết vật cản đến cảnh báo và điều khiển phanh.
- Các kiến trúc AEB từ đơn giản đến đa cảm biến.
- Cách tiếp cận được công khai bởi Toyota, Honda, Subaru, Tesla, Volvo,
  Mobileye, Bosch, Continental và ZF.
- Cách xử lý trong Autoware, openpilot, Apollo và Navigation2.
- Tiêu chuẩn, quy định và kịch bản kiểm thử AEB.

Tài liệu này chỉ trình bày cơ sở lý thuyết và nghiên cứu liên quan. Nền tảng mô
phỏng, thiết kế hệ thống, cấu hình, phương pháp triển khai và kết quả thực
nghiệm của đề tài sẽ được trình bày riêng trong Phần II.

Các hãng xe không công khai đầy đủ thuật toán production, threshold, trọng số
fusion và calibration. Vì vậy tài liệu chỉ mô tả những gì có nguồn chính thức;
phần kỹ thuật tổng quát được ghi dưới dạng kiến trúc tham khảo, không khẳng
định là thuật toán nội bộ của một hãng cụ thể.

## 2. ADAS Là Gì?

ADAS, viết tắt của `Advanced Driver Assistance Systems`, là tập hợp các hệ
thống hỗ trợ người lái bằng cách:

1. Quan sát môi trường và trạng thái xe.
2. Phát hiện nguy cơ.
3. Cảnh báo người lái.
4. Can thiệp tức thời vào phanh, ga hoặc lái khi cần.
5. Hỗ trợ điều khiển liên tục trong một phạm vi vận hành xác định.

Theo cách phân loại được NHTSA trình bày:

- AEB, FCW và cảnh báo lệch làn là hỗ trợ tức thời ở SAE Level 0.
- ACC hoặc hỗ trợ giữ làn riêng lẻ thuộc Level 1.
- Điều khiển đồng thời lái và ga/phanh trong khi người lái vẫn giám sát thuộc
  Level 2.

AEB không biến xe thành xe tự lái. Đây là một chức năng can thiệp an toàn trong
thời gian ngắn; người lái vẫn chịu trách nhiệm theo dõi và điều khiển xe.

Nguồn: [NHTSA - Driver Assistance Technologies](https://www.nhtsa.gov/vehicle-safety/driver-assistance-technologies).

## 3. Các Nhóm Chức Năng ADAS Phổ Biến

### 3.1 Cảnh Báo

| Chức năng | Mục đích |
|---|---|
| FCW | Cảnh báo nguy cơ va chạm phía trước |
| LDW | Cảnh báo xe rời làn ngoài ý muốn |
| BSW | Cảnh báo xe trong điểm mù |
| RCTW | Cảnh báo phương tiện cắt ngang khi lùi |
| TSR | Nhận dạng biển báo giao thông |
| DMS | Theo dõi mức độ chú ý, buồn ngủ hoặc mất tập trung của người lái |

### 3.2 Can Thiệp Tránh Va Chạm

| Chức năng | Mục đích |
|---|---|
| AEB | Tự động phanh khi va chạm phía trước sắp xảy ra |
| PAEB | AEB dành cho người đi bộ |
| Cyclist AEB | AEB dành cho người đi xe đạp |
| Rear AEB | Phanh tự động khi lùi |
| Blind Spot Intervention | Phanh hoặc hỗ trợ lái khi đổi làn không an toàn |
| ESS/AES | Hỗ trợ hoặc tự động đánh lái tránh vật cản |

### 3.3 Hỗ Trợ Điều Khiển

| Chức năng | Mục đích |
|---|---|
| ACC | Giữ tốc độ và khoảng cách với xe phía trước |
| LKA | Can thiệp để không rời làn |
| LCA | Điều khiển liên tục để giữ xe giữa làn |
| TJA | Hỗ trợ điều khiển trong ùn tắc |
| ISA | Hỗ trợ tuân thủ giới hạn tốc độ |

### 3.4 Hỗ Trợ Đỗ Xe Và Tốc Độ Thấp

- Camera lùi và camera toàn cảnh.
- Cảm biến siêu âm.
- Cảnh báo cắt ngang phía sau.
- Phanh khẩn cấp khi lùi.
- Ngăn tăng tốc nhầm ở tốc độ thấp.
- Hỗ trợ hoặc tự động đỗ xe.

## 4. AEB Là Gì?

AEB, `Automatic Emergency Braking` hoặc `Autonomous Emergency Braking`, tự động
tạo lực phanh khi hệ thống đánh giá rằng:

- Có một đối tượng nằm trên đường va chạm.
- Khoảng cách và vận tốc tương đối đang trở nên nguy hiểm.
- Người lái chưa phản ứng hoặc phản ứng không đủ.
- Phanh tự động có thể tránh va chạm hoặc giảm tốc độ va chạm.

NHTSA phân biệt hai cơ chế:

- `Dynamic Brake Support`: người lái đã phanh nhưng chưa đủ lực; hệ thống tăng
  lực phanh.
- `Crash Imminent Braking`: người lái chưa phanh; hệ thống tự động phanh.

AEB có thể được chia theo đối tượng và tình huống:

- Car-to-car rear: xe trước đứng yên, chạy chậm hoặc phanh.
- Pedestrian AEB.
- Cyclist AEB.
- Crossing AEB tại giao lộ.
- Turn-across-path với xe đối diện.
- Head-on AEB.
- Rear AEB khi lùi.
- Multi-collision braking sau va chạm đầu tiên.

## 5. Chuỗi Xử Lý AEB Tổng Quát

```text
Sensor acquisition
  -> hiệu chuẩn và đồng bộ
  -> phát hiện điểm hoặc vật thể
  -> lọc nhiễu và vùng quan tâm
  -> fusion và tracking
  -> dự đoán quỹ đạo ego và target
  -> chọn target liên quan
  -> đánh giá nguy cơ
  -> state machine cảnh báo/phanh
  -> điều khiển cơ cấu phanh
  -> giám sát lỗi và ghi log
```

### 5.1 Thu Nhận Và Đồng Bộ

Mỗi sensor có tần số, timestamp, độ trễ và hệ tọa độ riêng. Hệ thống cần:

- Hiệu chuẩn nội tại camera.
- Hiệu chuẩn ngoại tại giữa camera, radar và thân xe.
- Chuyển dữ liệu về cùng hệ tọa độ.
- Bù độ trễ theo timestamp.
- Không ghép camera frame mới với radar frame quá cũ.

Sai số đồng bộ có thể khiến box camera được ghép với radar point thuộc vị trí
cũ của vật thể, đặc biệt khi xe đang chạy nhanh hoặc chuyển làn.

### 5.2 Nhận Biết Đối Tượng

Camera thường đảm nhiệm:

- Phân loại xe, người đi bộ, xe đạp.
- Phát hiện làn đường, đèn và biển báo.
- Ước lượng vùng trống và hình dạng vật thể.

Radar thường đảm nhiệm:

- Đo khoảng cách.
- Đo vận tốc tương đối trực tiếp qua Doppler.
- Hoạt động tốt hơn camera trong đêm hoặc một số điều kiện thời tiết xấu.

LiDAR thường đảm nhiệm:

- Đo hình học 3D có độ phân giải góc cao.
- Tách vật thể và free space.
- Tạo lớp dự phòng hình học cho hệ thống tự hành cao cấp.

### 5.3 Lọc Vùng Liên Quan

Không phải mọi vật thể phía trước sensor đều là nguy cơ. AEB cần loại:

- Vật thể ngoài predicted path.
- Xe ở làn bên cạnh hoặc làn đối diện không cắt vào đường đi.
- Mặt đường, lan can, biển báo, cây và công trình.
- Detection quá thấp, quá cao hoặc ngoài tầm vận hành.
- Track có vận tốc hoặc vị trí nhảy bất thường.

Một cách phổ biến là mở rộng footprint của ego dọc theo quỹ đạo dự đoán thành
một `collision corridor`. Chỉ target giao với corridor mới được đánh giá sâu.

### 5.4 Tracking

Một detection đơn lẻ không nên trực tiếp kích hoạt phanh. Tracking thường:

- Ghép measurement mới với track cũ.
- Dự đoán trạng thái giữa hai chu kỳ sensor.
- Làm mượt khoảng cách và vận tốc.
- Xác nhận track sau nhiều frame.
- Xóa hoặc đánh dấu stale khi mất measurement.
- Cung cấp covariance hoặc confidence.

Các bộ lọc thường gặp:

- Low-pass hoặc exponential smoothing.
- Alpha-beta filter.
- Kalman Filter.
- Extended/Unscented Kalman Filter.
- Multiple-model tracker cho nhiều kiểu chuyển động.

### 5.5 Dự Đoán Quỹ Đạo

Đường đi của ego có thể được dự đoán từ:

- Vận tốc và yaw-rate từ IMU.
- Góc lái và mô hình bicycle.
- Quỹ đạo planner hoặc MPC.
- Tâm làn từ camera hoặc HD map.

Target có thể được dự đoán bằng:

- Constant velocity.
- Constant acceleration.
- Constant turn rate and velocity.
- Quỹ đạo từ perception predictor.

Quỹ đạo MPC chính xác hơn trong chuyển làn hoặc đường cong thay đổi; quỹ đạo
IMU đơn giản hơn và là fallback khi planner không có dữ liệu.

### 5.6 Chỉ Số Nguy Cơ

#### TTC

Với quy ước vận tốc đóng dương:

```text
TTC = distance / closing_speed
```

TTC dễ tính nhưng có hạn chế:

- Không phản ánh khả năng phanh thực tế.
- Nhạy với nhiễu vận tốc khi closing speed gần 0.
- Không mô hình hóa độ bám, dốc, tải xe và độ trễ cơ cấu.
- Không đủ để quyết định target có nằm trên đường va chạm hay không.

#### Time Headway

```text
THW = distance / ego_speed
```

THW phù hợp đánh giá khoảng cách bám xe nhưng không thay thế TTC.

#### Khoảng Cách Dừng

Mô hình đơn giản:

```text
d_required =
    v_ego * t_response
    + v_ego^2 / (2 * a_ego)
    - v_target^2 / (2 * a_target)
    + safety_margin
```

Trong đó:

- `t_response`: tổng thời gian nhận biết, quyết định và build-up phanh.
- `a_ego`: giảm tốc khả dụng của ego.
- `a_target`: giả định giảm tốc của target.
- `safety_margin`: biên do sai số sensor và mô hình.

Production AEB thường kết hợp TTC, khoảng cách dừng, predicted path, confidence
và khả năng tránh va chạm, thay vì chỉ dùng một threshold TTC.

#### Khoảng Cách An Toàn Theo RSS

Responsibility-Sensitive Safety, `RSS`, mô hình hóa khoảng cách dọc tối thiểu
dựa trên giả định về thời gian phản ứng và khả năng tăng/giảm tốc của hai xe.
Một dạng công thức cho xe sau `r` và xe trước `f` là:

```text
v_rho = v_r + rho * a_max_accel

d_min = max(
    0,
    v_r * rho
    + 0.5 * a_max_accel * rho^2
    + v_rho^2 / (2 * a_min_brake)
    - v_f^2 / (2 * a_max_brake_front)
)
```

Trong đó:

- `rho`: thời gian phản ứng.
- `a_max_accel`: mức xe sau vẫn có thể tăng tốc trong thời gian phản ứng.
- `a_min_brake`: mức giảm tốc tối thiểu xe sau phải thực hiện.
- `a_max_brake_front`: mức phanh cực đại giả định của xe trước.

RSS không phải một sensor hay một bộ điều khiển phanh. Đây là safety model xác
định khi khoảng cách trở nên không an toàn và “proper response” cần áp dụng.
Kết quả phụ thuộc mạnh vào các giả định gia tốc, giảm tốc và response time.

### 5.7 State Machine

Một state machine tham khảo:

```text
NORMAL
  -> INFORMATION
  -> WARNING
  -> BRAKE_PREPARE
  -> PARTIAL_BRAKE
  -> EMERGENCY_BRAKE
  -> HOLD
  -> RELEASE
```

Các tầng có thể gồm:

1. Hiển thị cảnh báo.
2. Cảnh báo âm thanh hoặc rung.
3. Pre-fill hoặc pre-charge hệ thống phanh.
4. Brake jerk để thu hút người lái.
5. Hỗ trợ lực phanh nếu người lái đã đạp phanh.
6. Phanh một phần.
7. Phanh khẩn cấp toàn lực.

Hysteresis và số frame xác nhận giúp tránh trạng thái phanh bật/tắt liên tục.

### 5.8 Điều Kiện Override Và Release

Hệ thống cần định nghĩa rõ khi nào:

- Người lái đánh lái mạnh.
- Người lái đạp ga mạnh.
- Người lái chủ động phanh.
- Target rời predicted path.
- Sensor bị che hoặc mất dữ liệu.
- Xe về số lùi.
- ABS/ESC đang can thiệp.

Tesla công khai rằng AEB có thể không phanh hoặc dừng phanh khi người lái đánh
lái mạnh, tăng ga mạnh hoặc target không còn được phát hiện. Điều này minh họa
vai trò của driver override và điều kiện release.

### 5.9 Điều Khiển Phanh

Khối đánh giá nguy cơ nên tạo ra yêu cầu ở mức vật lý, ví dụ giảm tốc mong muốn
`a_des`, thay vì gắn trực tiếp mọi mức nguy cơ với một giá trị pedal phanh.

Ba cách điều khiển thường gặp:

1. `Binary brake`: đóng/mở phanh theo ngưỡng. Dễ kiểm tra logic nhưng tạo jerk
   lớn và khó điều chỉnh mức can thiệp.
2. `Brake profile`: chọn trước đường giảm tốc theo thời gian hoặc theo trạng
   thái warning, partial brake và emergency brake.
3. `Closed-loop control`: điều chỉnh lệnh phanh theo sai số giữa giảm tốc mong
   muốn và giảm tốc đo được.

Một bộ PID tổng quát có dạng:

```text
e(t) = a_des(t) - a_measured(t)

u(t) =
    Kp * e(t)
    + Ki * integral(e(t) dt)
    + Kd * de(t)/dt
```

Trong đó:

- `u`: lệnh cơ cấu phanh.
- `Kp`: phản ứng theo sai số hiện tại.
- `Ki`: loại sai lệch tĩnh nhưng có nguy cơ integral windup.
- `Kd`: giảm dao động nhưng nhạy với nhiễu.

Với AEB, bộ điều khiển còn cần:

- Saturation giới hạn lệnh phanh.
- Anti-windup.
- Lọc thành phần đạo hàm.
- Rate limiter hoặc jerk limit.
- Chuyển trạng thái êm giữa phanh một phần và phanh khẩn cấp.
- Phối hợp với ABS/ESC và driver override.

PID không tự quyết định có nguy hiểm hay không. Risk assessment tạo
`a_des`; controller chỉ cố gắng thực hiện yêu cầu giảm tốc đó. Việc tách hai
lớp giúp đánh giá riêng lỗi nhận thức/quyết định và lỗi bám điều khiển.

## 6. Vai Trò Và Hạn Chế Của Từng Sensor

| Sensor | Thông tin mạnh | Hạn chế chính | Vai trò điển hình trong AEB |
|---|---|---|---|
| Mono camera | Class, làn, hình dạng, ngữ cảnh | Depth gián tiếp; nhạy ánh sáng/thời tiết | Phát hiện và phân loại |
| Stereo camera | Class và depth từ disparity | Cần texture; nhạy ánh sáng, calibration | AEB camera-centric |
| Radar | Range, Doppler, hoạt động đêm | Phân loại và độ phân giải góc hạn chế | Range/velocity, tracking |
| Imaging radar | Range/Doppler và góc tốt hơn | Giá và xử lý phức tạp | Perception 4D, redundancy |
| LiDAR | Hình học 3D chính xác | Chi phí, thời tiết, tích hợp | Free space và object 3D |
| Ultrasonic | Vật cản rất gần, giá thấp | Tầm ngắn, độ phân giải thấp | Rear/parking AEB |
| IMU/wheel speed | Ego motion, yaw-rate | Drift và không thấy vật cản | Predicted path, compensation |
| GNSS/map | Vị trí và cấu trúc đường | Không đủ chính xác một mình | Context, lane/road ROI |
| Driver camera | Hướng nhìn và chú ý | Không đo nguy cơ bên ngoài | Điều chỉnh cảnh báo/can thiệp |

Không tồn tại sensor hoàn hảo. Sensor fusion nhằm tạo tính bổ sung và dự phòng,
không chỉ tăng số lượng sensor.

### 6.1 Các Thông Số Cần Đọc Khi Chọn Sensor

Không nên đánh giá sensor chỉ bằng tầm đo xa nhất. Với AEB, các thông số cần
được xem đồng thời gồm:

| Nhóm thông số | Ý nghĩa đối với AEB |
|---|---|
| Range | Khoảng cách nhỏ nhất và lớn nhất có thể đo |
| Horizontal/vertical FOV | Phạm vi góc quan sát ngang và dọc |
| Angular resolution | Khả năng tách hai vật thể gần nhau theo góc |
| Range resolution | Khả năng tách hai vật thể gần nhau theo khoảng cách |
| Accuracy | Sai số của range, velocity, angle hoặc pixel |
| Update rate | Số lần tạo measurement trong một giây |
| Latency | Thời gian từ lúc thu tín hiệu đến lúc dữ liệu tới thuật toán |
| Timestamp jitter | Độ dao động của timestamp và chu kỳ dữ liệu |
| Detection probability | Xác suất phát hiện đúng target trong ODD |
| False-alarm rate | Mức tạo detection không phải vật cản thật |
| Dynamic range/HDR | Khả năng xử lý đồng thời vùng rất sáng và rất tối |
| Environmental rating | Khả năng hoạt động khi mưa, bụi, rung và nhiệt độ cao |
| Output level | Raw signal, point/location, object track hay quyết định chức năng |

Hai sensor cùng ghi “100 m” có thể cho hiệu năng AEB rất khác nhau nếu một
sensor có góc phân giải thấp, độ trễ lớn hoặc chỉ phát hiện tốt target có độ
phản xạ cao.

### 6.2 Camera

#### Nguyên Lý

Camera biến ánh sáng qua thấu kính thành ảnh trên cảm biến CMOS. Với mô hình
pinhole, điểm 3D trong hệ camera được chiếu lên pixel theo:

```text
u = fx * X / Z + cx
v = fy * Y / Z + cy
```

Trong đó:

- `fx`, `fy`: tiêu cự tính theo pixel.
- `cx`, `cy`: principal point.
- `X, Y, Z`: tọa độ điểm trong hệ camera.
- `u, v`: tọa độ pixel.

Đây cũng là cơ sở toán học để chiếu radar point lên ảnh camera trong sensor
fusion. Hệ thống phải dùng extrinsic transform radar-camera, camera intrinsic
và phép chiếu; sensor không tự cung cấp quan hệ giữa point và bounding box.

Mono camera không đo trực tiếp chiều sâu. Khoảng cách có thể được suy ra từ:

- Kích thước vật thể đã biết.
- Chuyển động qua nhiều frame.
- Mạng monocular depth.
- Ground-plane assumption.
- Radar hoặc LiDAR đi kèm.

Stereo camera dùng disparity giữa hai ảnh:

```text
Z = f * B / disparity
```

Với `B` là baseline hai camera. Disparity càng nhỏ khi vật thể càng xa, do đó
sai số depth thường tăng theo khoảng cách.

#### Thông Số Quan Trọng

- Resolution: ảnh lớn tăng chi tiết nhưng tăng băng thông và thời gian inference.
- Horizontal FOV: FOV hẹp nhìn xa tốt hơn; FOV rộng thấy cut-in/crossing sớm hơn.
- Frame rate: thường phải cân bằng với compute và latency toàn pipeline.
- Exposure và HDR: ảnh hưởng trực tiếp khi đi từ vùng tối ra vùng sáng.
- Rolling/global shutter: rolling shutter có thể làm méo vật thể khi chuyển
  động nhanh.
- Lens distortion: cần hiệu chuẩn để projection chính xác.
- Mounting pose: sai số vài độ có thể làm radar-camera association lệch rõ ở xa.

Ví dụ công khai:

- ZF S-Cam4 dùng cảm biến HDR 1,7 megapixel và FOV ngang 100 độ.
- ZF Smart Camera 6 công bố độ phân giải 8 megapixel và FOV 120 độ.
- Camera cự ly gần của Bosch có cấu hình 1 hoặc 2 megapixel, FOV ngang trên
  190 độ cho bài toán quan sát quanh xe.

Các số này minh họa trade-off theo chức năng, không phải một cấu hình bắt buộc
cho mọi AEB.

### 6.3 Radar Ô Tô

#### Nguyên Lý Radar FMCW Thật

Radar ô tô hiện đại thường phát sóng liên tục điều tần, `FMCW`. Mỗi chirp tăng
hoặc giảm tần số theo thời gian. Tín hiệu phản xạ được trộn với tín hiệu phát để
tạo beat frequency.

Với trường hợp đơn giản:

```text
R = c * f_beat / (2 * slope)
```

Trong đó:

- `R`: khoảng cách.
- `c`: tốc độ ánh sáng.
- `f_beat`: beat frequency.
- `slope`: tốc độ quét tần số của chirp.

Vận tốc tương đối được suy ra từ thay đổi pha/Doppler giữa nhiều chirp:

```text
v = wavelength * f_doppler / 2
```

Góc tới được ước lượng từ chênh lệch pha giữa nhiều anten thu. Chuỗi xử lý điển
hình gồm:

```text
ADC samples
  -> range FFT
  -> Doppler FFT
  -> angle estimation
  -> CFAR detection
  -> clustering
  -> object tracking
```

Radar 4D bổ sung khả năng đo hoặc ước lượng tốt hơn theo bốn chiều:
`range`, `Doppler`, `azimuth`, `elevation`.

#### Nguồn Nhiễu Và Sai Số

- Multipath từ mặt đường, gầm xe và lan can.
- Ground reflection.
- Ghost target.
- Interference từ radar xe khác.
- Vật có radar cross section nhỏ.
- Angle ambiguity hoặc độ phân giải góc thấp.
- Stationary infrastructure bị nhầm thành vật cản.
- Track bị split/merge khi nhiều xe gần nhau.

Vì vậy radar production thường không đưa từng reflection trực tiếp vào AEB.
Nó có thể xuất `locations`, object tracks hoặc raw/processed signal cho ECU
fusion.

#### Ví Dụ Thông Số Công Khai

| Sensor công khai | Tần số | Tầm đo | FOV | Chu kỳ cập nhật |
|---|---:|---:|---:|---:|
| Continental ARS540 | 76-77 GHz | 300 m | ±60 độ | 60 ms, khoảng 16,7 Hz |
| Bosch front/corner radar và radar premium | 76-81 GHz | đến 500/700 m tùy biến thể | Trang sản phẩm chỉ công bố FOV rộng | Không công bố |
| ZF short-range radar | 77 GHz | 0,3-80 m | ngang 170 độ | Không công bố tại trang sản phẩm |

Tầm đo thực tế phụ thuộc kích thước, vật liệu, góc và radar cross section của
target. “300 m” không có nghĩa mọi người đi bộ hoặc vật nhỏ đều được phát hiện
ổn định ở 300 m.

### 6.4 LiDAR

LiDAR phát xung hoặc mẫu ánh sáng laser và đo thời gian photon quay về:

```text
R = c * delta_t / 2
```

Kết hợp range với hướng tia tạo point cloud 3D. Một số hệ quay cơ khí, một số
dùng MEMS, flash hoặc solid-state scanning.

Thông số chính:

- Số channel/beam.
- Points per second.
- Rotation hoặc scan frequency.
- Horizontal/vertical FOV.
- Range theo reflectivity của target.
- Minimum range.
- Range/angular accuracy.
- Intensity và multi-return.

Ví dụ Ouster OS1 công bố tối đa 128 channel, 10,4 triệu point/s, FOV dọc 45 độ,
range danh định 90 m tại reflectivity 10% và maximum range 250 m.

LiDAR giúp kiểm tra hình học, chiều cao và free space tốt hơn radar độ phân giải
thấp. Đổi lại, point cloud dày cần compute lớn; hiệu năng còn phụ thuộc mưa,
sương, vật liệu target và tình trạng cửa sổ sensor.

### 6.5 Siêu Âm

Sensor siêu âm phát xung âm tần số cao rồi đo thời gian echo:

```text
R = speed_of_sound * delta_t / 2
```

Nó phù hợp vật cản rất gần và phanh khi đỗ xe, không phù hợp AEB cao tốc vì tầm
ngắn và update rate thấp hơn yêu cầu highway.

Bosch công bố sensor siêu âm có:

- Tầm phát hiện đến 5,5 m.
- Khoảng cách đo chính xác tối thiểu 15 cm.
- Vùng phát hiện sự hiện diện 3-15 cm.

Continental CUS320 công bố tần số 52 kHz, tầm 16-550 cm và FOV
`120 x 60` độ.

### 6.6 IMU, Wheel Speed, Steering Và GNSS

IMU thường gồm:

- Accelerometer ba trục.
- Gyroscope ba trục.

Gyroscope cho yaw-rate trực tiếp; accelerometer cho gia tốc riêng. Việc tích
phân acceleration và angular velocity tạo vận tốc/tư thế nhưng sẽ tích lũy bias
và drift. Vì vậy hệ thống thường fusion IMU với wheel speed, steering, GNSS,
camera hoặc LiDAR localization.

Với mô hình bicycle đơn giản:

```text
curvature = tan(steering_angle) / wheelbase
yaw_rate = ego_speed * curvature
```

Các tín hiệu này rất quan trọng cho AEB vì chúng tạo predicted path. Chỉ dùng
trục thẳng của radar sẽ dễ nhận tường, lan can hoặc xe làn bên cạnh khi ego
đang cua.

GNSS cung cấp vị trí toàn cục nhưng không đủ cho AEB cự ly ngắn nếu dùng một
mình. Map và localization chủ yếu cung cấp lane topology, curvature, direction
và context cho target filtering.

### 6.7 Tần Số Sensor Và Đồng Bộ

Camera, radar, LiDAR và vehicle-state bus thường có tần số và độ trễ khác
nhau. Ví dụ, camera có thể tạo ảnh ở 20-30 Hz trong khi radar tạo object list
ở một chu kỳ khác. Khác biệt tần số không tự gây sai fusion nếu dữ liệu có
timestamp đáng tin cậy và pipeline xử lý đúng thời gian.

Fusion cần:

1. Ghép measurement gần timestamp nhất.
2. Đặt giới hạn tuổi dữ liệu tối đa.
3. Bù chuyển động ego trong khoảng lệch thời gian.
4. Không dùng lại radar hoặc camera frame cũ vô thời hạn.

Các chiến lược đồng bộ phổ biến:

- `Nearest-neighbor timestamp`: chọn measurement gần nhất trong cửa sổ thời
  gian cho phép.
- `Interpolation`: nội suy ego pose hoặc vehicle state đến timestamp sensor.
- `Prediction to common time`: dự đoán track đến cùng một thời điểm fusion.
- `Buffering`: trì hoãn sensor nhanh để chờ sensor chậm, đổi lại tăng latency.

Không có một tần số camera hoặc radar tối ưu cho mọi hệ thống. End-to-end
latency, độ ổn định timestamp và khả năng bù chuyển động quan trọng hơn việc
chỉ tăng frame rate.

Nguồn:

- [OpenCV - Camera calibration và mô hình pinhole](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
- [TI - mmWave fundamentals: range, velocity and angle](https://www.ti.com/document-viewer/lit/html/sszt906)
- [Bosch - Radar sensor](https://www.bosch-mobility.com/en/solutions/sensors/radar-sensor/)
- [Continental - ARS540](https://www.continental-automotive.com/en/components/radars/long-range-radars/advanced-radar-sensor-ars540.html)
- [ZF - Sensor Power](https://press.zf.com/press/en/releases/release_3394.html)
- [ZF - Smart Camera 6](https://press.zf.com/press/en/releases/release_88128.html)
- [Ouster - OS1 LiDAR](https://ouster.com/products/hardware/os1-lidar-sensor)
- [Bosch - Ultrasonic sensor](https://www.bosch-mobility.com/en/solutions/sensors/ultrasonic-sensor/)
- [Continental - CUS320](https://www.continental-automotive.com/en/components/sensors/parking-sensors/ultrasonic-parking-sensor.html)
- [Bosch Sensortec - IMU overview](https://www.bosch-sensortec.com/products/motion-sensors/imus/)

## 7. Các Kiến Trúc AEB Từ Đơn Giản Đến Phức Tạp

### 7.1 Radar Đơn

Pipeline tối giản:

```text
radar detection
  -> lọc góc/range
  -> chọn target gần trục xe
  -> TTC hoặc stopping distance
  -> cảnh báo/phanh
```

Ưu điểm:

- Đo range và vận tốc tương đối trực tiếp.
- Hoạt động ngày đêm.
- Chi phí tính toán thấp.
- Phù hợp AEB car-to-car cơ bản.

Hạn chế:

- Khó phân biệt xe, cây, biển báo và kết cấu đường.
- Khó xử lý stationary object mà không tăng false-positive.
- Khó nhận biết người đi bộ và xe đạp bằng radar độ phân giải thấp.
- Dễ phanh nhầm nếu chỉ dùng góc ngang cố định và TTC của từng point.

Toyota công bố hệ Pre-crash Safety năm 2002 dùng radar milimet để đo vật cản,
vị trí, tốc độ và hướng chuyển động. Honda CMS năm 2003 cũng dùng radar
milimet, kết hợp yaw-rate, góc lái, wheel speed và brake pressure để tính đường
dự kiến của ego.

Đây là ví dụ lịch sử cho thấy radar-only vẫn cần vehicle dynamics và predicted
path, không chỉ dùng khoảng cách thẳng trước xe.

### 7.2 Một Camera Phía Trước

Pipeline:

```text
camera
  -> neural-network perception
  -> object/lane/free-space estimation
  -> monocular depth hoặc motion estimation
  -> collision prediction
  -> AEB
```

Mobileye công khai Base ADAS có thể dùng một camera trước để cung cấp AEB, ACC,
ISA, LKA và highway assist.

Ưu điểm:

- Giá và phần cứng thấp.
- Phân loại đối tượng tốt.
- Dùng chung sensor cho làn, biển báo và AEB.

Hạn chế:

- Khoảng cách và vận tốc phải suy ra từ hình ảnh.
- Dễ giảm chất lượng khi lóa, tối, mưa, sương hoặc camera bẩn.
- Cần calibration và mô hình perception có độ tin cậy cao.

Camera-only không đồng nghĩa với thuật toán đơn giản. Nó giảm sensor vật lý
nhưng chuyển độ phức tạp sang mạng neural, estimation và validation dữ liệu.

### 7.3 Stereo Camera

Stereo camera dùng hai góc nhìn để tính disparity và ước lượng depth.

Subaru EyeSight công khai sử dụng hai camera stereo; một số cấu hình mới có thể
bổ sung camera mono góc rộng. Hệ thống cung cấp Pre-Collision Braking cùng các
chức năng hỗ trợ lái khác.

Ưu điểm:

- Có depth hình học mà không cần radar.
- Phân loại và hình dạng tốt.
- Cùng sensor hỗ trợ làn và vật thể.

Hạn chế:

- Depth giảm chất lượng ở vùng ít texture hoặc khoảng cách xa.
- Cần baseline và calibration stereo ổn định.
- Hai camera vẫn có các hạn chế quang học tương tự nhau.

### 7.4 Camera Và Radar

Đây là cấu hình phổ biến cho AEB hiện đại:

```text
radar tracks: range + relative velocity
camera objects: class + bbox + lane context
             \ /
        association/fusion
              |
      fused object tracks
              |
       risk assessment
```

Có ba mức fusion:

- `Late fusion`: radar và camera quyết định riêng; logic cuối kết hợp kết quả.
- `Track-to-track fusion`: ghép object track từ mỗi sensor.
- `Measurement/feature fusion`: kết hợp dữ liệu sớm hơn trong mạng hoặc tracker.

Ưu điểm:

- Radar bù nhược điểm depth của camera.
- Camera bù nhược điểm phân loại và góc của radar.
- Stationary target có thể được camera xác nhận.
- Tăng khả năng xử lý pedestrian/cyclist.

Hạn chế:

- Association sai khi nhiều vật thể gần nhau.
- Cần đồng bộ và calibration chính xác.
- Hai sensor có thể bất đồng; hệ thống phải định nghĩa confidence và fallback.

### 7.5 Multi-Camera, Multi-Radar, LiDAR Và Map

Hệ cao cấp có thể gồm:

- Camera trước tele/wide và camera surround.
- Radar trước tầm xa và radar góc.
- Imaging radar.
- LiDAR.
- Ultrasonic.
- IMU/GNSS và HD map.
- Driver monitoring camera.

ZF mô tả kiến trúc có thể mở rộng từ camera đơn đến nhiều camera, radar,
ultrasonic và LiDAR. Mobileye Surround ADAS dùng camera surround và radar.

Ưu điểm:

- Trường nhìn rộng và khả năng xử lý giao lộ/cắt ngang.
- Redundancy giữa các modality.
- Hỗ trợ AEB khi rẽ, head-on và evasive steering.
- Free-space và topology tốt hơn.

Hạn chế:

- Giá, năng lượng và băng thông cao.
- Calibration và data association phức tạp.
- Validation state space tăng rất mạnh.
- Nhiều sensor không tự động đồng nghĩa với an toàn nếu fusion không tốt.

## 8. Cách Tiếp Cận Công Khai Của Các Hãng Và Nhà Cung Cấp

### 8.1 Toyota

#### Quá Trình Phát Triển Công Khai

- Năm 2002, Toyota công bố Pre-crash Safety dùng radar milimet để đo vật cản,
  vị trí, tốc độ và đường đi; ECU đánh giá khả năng va chạm.
- Hệ thống liên kết Brake Assist và pre-crash seatbelt.
- Các thế hệ sau kết hợp radar milimet với camera.
- Toyota Safety Sense C từng dùng camera và laser radar.
- Toyota Safety Sense P dùng camera và radar milimet.
- Các thế hệ gần đây tiếp tục mở rộng camera-radar perception và tình huống
  giao lộ.

#### Ý Nghĩa Kỹ Thuật

Toyota thể hiện quá trình tiến hóa:

```text
radar + vehicle dynamics
  -> radar + camera fusion
  -> nhận biết nhiều đối tượng và nhiều tình huống hơn
  -> liên kết perception, phanh, dây đai và driver monitoring
```

Nguồn:

- [Toyota - Pre-crash Safety 2002](https://global.toyota/en/detail/211112)
- [Toyota - Driver-monitoring Pre-crash Safety](https://global.toyota/en/detail/248128)
- [Toyota Safety Sense](https://pressroom.toyota.com/the-evolution-of-safety-at-toyota-part-2-toyota-safety-sense-for-all/)

### 8.2 Honda

Honda CMS năm 2003 công khai một kiến trúc có:

- Radar milimet khoảng 100 m.
- Khoảng cách và vận tốc tương đối.
- Yaw-rate, góc lái, tốc độ bánh xe và áp suất phanh.
- Predicted path của ego.
- Cảnh báo hình ảnh/âm thanh.
- Phanh và pre-tensioner dây đai.

Honda SENSING hiện mô tả front wide-view camera, sonar trước/sau; tùy đời xe và
model có thể có camera trước cùng radar milimet. CMBS thực hiện:

1. Cảnh báo âm thanh và hình ảnh.
2. Phanh nhẹ khi nguy cơ tăng.
3. Phanh mạnh khi va chạm được đánh giá là sắp xảy ra.

Nguồn:

- [Honda CMS 2003](https://global.honda/en/newsroom/news/2003/4030520-eng.html)
- [Honda SENSING](https://global.honda/en/tech/Safety_and_driver_assistive_technologies_Honda_SENSING/)

### 8.3 Subaru EyeSight

Subaru EyeSight là ví dụ điển hình cho kiến trúc stereo-camera-centric:

- Hai camera stereo quan sát phía trước.
- Một số cấu hình bổ sung camera mono góc rộng.
- Pre-Collision Braking, ACC và lane support dùng chung perception.

Điểm đáng chú ý là stereo vision cung cấp cả thông tin ngữ nghĩa và depth, cho
phép AEB không bắt buộc phải có radar trong cấu hình cơ bản.

Nguồn:

- [Subaru EyeSight Getting Started Guide](https://techinfo.subaru.com/stis/doc/ownerManual/MSA5B2304A_2nd.pdf)

### 8.4 Tesla

Tài liệu Model 3 hiện tại mô tả:

- Nhiều camera quan sát phía trước, bên và sau.
- Camera phải được hiệu chuẩn trước khi một số chức năng, bao gồm AEB, hoạt
  động đầy đủ.
- FCW cung cấp cảnh báo hình ảnh và âm thanh.
- AEB phanh khi hệ thống đánh giá va chạm là không thể tránh.
- AEB có thể không phanh hoặc dừng phanh khi đánh lái mạnh, phanh/nhả phanh,
  tăng ga mạnh hoặc target không còn được phát hiện.

Đây là kiến trúc camera-centric đa góc nhìn. Tài liệu người dùng không công
bố chi tiết mạng neural, thuật toán depth, threshold TTC hay logic fusion của
từng phiên bản phần cứng; không nên tự suy diễn các tham số đó.

Nguồn:

- [Tesla Model 3 - Cameras](https://www.tesla.com/ownersmanual/model3/en_us/GUID-682FF4A7-D083-4C95-925A-5EE3752F4865.html)
- [Tesla Model 3 - Collision Avoidance Assist](https://www.tesla.com/ownersmanual/model3/en_us/GUID-8EA7EF10-7D27-42AC-A31A-96BCE5BC0A85.html)

### 8.5 Volvo

Volvo công khai rõ vai trò sensor trong hệ camera-radar:

- Radar phát hiện vật thể và đo khoảng cách.
- Camera phân loại loại vật thể.
- Control unit đánh giá tình huống giao thông.
- Các hệ đầu tiên yêu cầu radar và camera cùng xác nhận trước khi tự phanh.
- Trình tự gồm cảnh báo âm thanh/hình ảnh, pre-charge phanh và full braking nếu
  người lái không phản ứng.

Volvo cũng cho biết camera giúp nhận biết stationary vehicle trong khi giữ
false alarm thấp hơn so với hệ radar-only trước đó.

Nguồn:

- [Volvo - Collision Warning with Auto Brake](https://www.media.volvocars.com/global/en-gb/media/pressreleases/13830/)
- [Volvo - Pedestrian Detection with Full Auto Brake](https://www.media.volvocars.com/global/en-gb/media/pressreleases/31773)

### 8.6 Mobileye

Mobileye minh họa kiến trúc có khả năng mở rộng:

- Base ADAS: một camera trước, hỗ trợ AEB và nhiều chức năng khác.
- Cloud-Enhanced ADAS: thêm dữ liệu bản đồ cộng đồng mà không cần thêm sensor
  vật lý trên xe.
- Surround ADAS: camera surround và radar, dùng compute EyeQ cao hơn.

Điểm chính là kiến trúc ADAS có thể scale theo cost:

```text
single camera
  -> single camera + map
  -> surround camera + radar fusion
```

Nguồn:

- [Mobileye ADAS Platforms](https://www.mobileye.com/solutions/adas/)

### 8.7 Bosch

Bosch mô tả pipeline AEB nhiều tầng:

1. Chuẩn bị hệ thống phanh.
2. Cảnh báo âm thanh/hình ảnh.
3. Brake jerk.
4. Partial braking.
5. Dynamic brake support nếu người lái phanh chưa đủ.
6. Full braking khi va chạm được đánh giá là không thể tránh.

Bosch công khai radar là sensor chính cho range và tình huống crossing; camera
bổ sung giúp tăng availability, phân loại và tracking thông qua sensor fusion.

Bosch cũng mở rộng AEB thành:

- Rear-end AEB.
- Crossing AEB.
- Turn-across-path.
- Reverse AEB.

Nguồn:

- [Bosch - Automatic Emergency Braking](https://www.bosch-mobility.com/en/solutions/assistance-systems/automatic-emergency-braking/)

### 8.8 Continental

Continental cung cấp platform camera có machine learning, free-space detection,
Emergency Brake Assist và trường nhìn rộng. MFC527 công khai độ phân giải
`1820 x 940`, FOV `110 x 46` độ và khả năng hoạt động trong điều kiện ánh sáng
yếu.

Điều này cho thấy ECU camera hiện đại không chỉ xuất bounding box. Nó có thể
cung cấp:

- Object detection.
- Lane và road model.
- Free space.
- Input cho Emergency Brake Assist.

Nguồn:

- [Continental - Multi Function Mono Camera MFC527](https://www.continental-automotive.com/en/components/cameras/multi-function-mono-camera-mfc527.html)

### 8.9 ZF

ZF công khai nhiều mức hệ thống:

- Radar 77 GHz hỗ trợ ACC, cảnh báo va chạm và AEB.
- OnGuardMAX kết hợp radar, camera và image processing.
- AEB khi rẽ dùng hai radar góc trước, camera trước và hệ thống phanh.
- Kiến trúc cao hơn có camera, radar và LiDAR để tăng redundancy.
- Integrated Brake Control có thời gian apply phanh AEB công bố dưới 150 ms.

ZF cũng trình diễn automated collision avoidance: nếu không đủ khoảng cách
phanh và làn bên cạnh an toàn, hệ thống có thể kết hợp phanh và steering.

Nguồn:

- [ZF - OnGuardMAX](https://www.zf.com/products/en/cv/products_76928.html)
- [ZF - Automated Driving Functions](https://press.zf.com/press/en/releases/release_2986.html)
- [ZF - ADAS Sensors](https://press.zf.com/press/en/releases/release_34432.html)
- [ZF - Integrated Brake Control](https://www.zf.com/products/en/cars/products_77568.html)

## 9. Cách Xử Lý Trong Các Repo Mã Nguồn Mở

Mã nguồn mở hữu ích vì cho thấy data flow, state, filter và tham số cụ thể.
Tuy nhiên, repo nghiên cứu không phải bằng chứng rằng thuật toán đã đạt yêu cầu
homologation hoặc tương đương hệ thống production của hãng.

### 9.1 Autoware Universe

Autoware có module `autoware_autonomous_emergency_braking` riêng. Vai trò của
module là phát hiện vật cản nằm trên quỹ đạo dự đoán và gửi tín hiệu emergency
qua diagnostics.

Pipeline:

```text
ego velocity + yaw-rate             MPC predicted trajectory
              \                      /
               IMU path + MPC path
                        |
point cloud hoặc predicted objects
                        |
rough path-corridor filtering
  -> voxel/noise filtering
  -> Euclidean clustering
  -> cluster height check
  -> 2D convex hull
  -> footprint/path intersection
                        |
select closest relevant obstacle
  -> estimate obstacle velocity
  -> median velocity history
  -> braking-distance check
  -> emergency diagnostic
```

#### Predicted Path

IMU path dùng vận tốc dọc `v` và angular velocity `omega`:

```text
x(k+1)     = x(k) + v * cos(theta(k)) * dt
y(k+1)     = y(k) + v * sin(theta(k)) * dt
theta(k+1) = theta(k) + omega * dt
```

MPC path lấy trực tiếp predicted trajectory từ controller. Hai path có thể được
dùng cùng lúc:

- MPC phản ánh steering/planning intent tốt hơn.
- IMU path độc lập với planner, có thể đóng vai trò fallback khi trajectory
  planner hoặc odometry sai.

Autoware cũng chỉ rõ nhược điểm của IMU path: giữ nguyên yaw-rate hiện tại quá
lâu có thể làm path cong ra khỏi làn và gây phanh nhầm. Biện pháp là giới hạn
time horizon, tổng chiều dài và lateral deviation.

#### Chọn Vật Cản

Autoware không kiểm tra toàn bộ point cloud bằng TTC. Module:

1. Cắt point ngoài vùng lân cận predicted footprint.
2. Downsample point cloud.
3. Gom cụm Euclidean.
4. Bỏ cụm quá thấp hoặc quá ít point.
5. Tạo convex hull.
6. Chỉ giữ point/hull có khả năng giao với footprint ego trên path.
7. Chọn target liên quan gần nhất theo path.

Với predicted object, module kiểm tra giao giữa polygon/bounding box của object
và swept footprint của ego, thay vì chỉ kiểm tra tâm object.

#### Ước Lượng Vận Tốc Và Nguy Cơ

Nếu input là point cloud chưa có vận tốc object, Autoware ước lượng từ vị trí
target qua thời gian, bù ego motion và lấy median của lịch sử để giảm nhiễu.
Nếu input là predicted object, module dùng vận tốc object do perception cung cấp.

Khoảng cách phanh có dạng:

```text
d_braking =
    v_ego * t_response
    + v_ego^2 / (2 * |a_ego_min|)
    - sign(v_obj) * v_obj^2 / (2 * |a_obj_min|)
    + offset
```

Emergency được yêu cầu khi khoảng cách thật nhỏ hơn `d_braking`. Đây là logic
gần với stopping-distance/RSS, không chỉ là threshold TTC.

#### Một Số Default Đáng Chú Ý

Theo schema của nhánh `main` được đọc ngày 06/06/2026:

| Tham số | Default | Ý nghĩa |
|---|---:|---|
| `aeb_hz` | 10 Hz | Tần số chạy module |
| `imu_prediction_time_horizon` | 1,5 s | Horizon IMU path |
| `imu_prediction_time_interval` | 0,1 s | Bước lấy mẫu IMU path |
| `max_generated_imu_path_length` | 10 m | Chiều dài IMU path tối đa |
| `imu_path_lat_dev_threshold` | 1,75 m | Giới hạn lệch ngang |
| `mpc_prediction_time_horizon` | 4,5 s | Horizon MPC path |
| `mpc_prediction_time_interval` | 0,1 s | Bước lấy mẫu MPC path |
| `cluster_tolerance` | 0,15 m | Khoảng nối point trong cluster |
| `minimum_cluster_size` | 10 | Số point tối thiểu |
| `cluster_minimum_height` | 0,1 m | Chiều cao tối thiểu của cluster |
| `t_response` | 1,0 s | Response time trong khoảng cách phanh |
| `a_ego_min` | -3,0 m/s² | Giảm tốc ego giả định |
| `a_obj_min` | -1,0 m/s² | Giảm tốc object giả định |
| `collision_keeping_sec` | 3,0 s | Thời gian giữ trạng thái collision |

Không nên sao chép trực tiếp các số này sang một hệ sensor khác. Autoware mặc
định xử lý point cloud tương đối dày; `minimum_cluster_size: 10` có thể không
phù hợp với radar point cloud thưa hoặc object list đã qua xử lý.

Điểm nên học:

- Predicted path có hai nguồn độc lập.
- Collision check dùng swept footprint.
- Clustering trước khi quyết định.
- Median history để giảm velocity spike.
- Phân tách phát hiện nguy cơ và emergency-stop operator.

Nguồn:

- [Autoware - Autonomous Emergency Braking](https://autowarefoundation.github.io/autoware_universe/main/control/autoware_autonomous_emergency_braking/)
- [Autoware - AEB source và schema](https://github.com/autowarefoundation/autoware_universe/tree/main/control/autoware_autonomous_emergency_braking)
- [Autoware - MPC lateral controller](https://autowarefoundation.github.io/autoware_universe/main/control/autoware_mpc_lateral_controller/)

### 9.2 openpilot

openpilot là hệ ACC và lane centering, không phải repo AEB độc lập tương đương
module Autoware. Tương tác với AEB/FCW nguyên bản còn phụ thuộc từng xe; tài
liệu danh sách xe thậm chí cảnh báo rằng bật openpilot longitudinal trên một số
cấu hình sẽ vô hiệu hóa AEB/FCW nguyên bản. Phần có giá trị nghiên cứu trực
tiếp ở đây là cơ chế fusion lead vehicle trong `radard.py`.

Pipeline `radard.py`:

```text
vehicle radar tracks             vision lead hypotheses
        |                                  |
track ID + dRel/yRel/vRel       x/y/v + uncertainty + probability
        |                                  |
1D Kalman filter                   temporal probability filter
        +---------------+------------------+
                        |
probabilistic association by distance/lateral/velocity
                        |
sanity gates
                        |
fused lead or vision-only fallback
                        |
low-speed narrow radar fallback
```

Các chi tiết đáng chú ý trong snapshot nhánh `master` ngày 06/06/2026:

- Mỗi radar track giữ `dRel`, `yRel`, `vRel`, filtered lead velocity và lead
  acceleration.
- Kalman filter 1D làm mượt vận tốc/gia tốc lead.
- Ego speed history được dùng để bù radar delay.
- Association camera-radar dùng xác suất Laplace theo sai khác distance,
  lateral position và velocity.
- Match phải vượt distance/velocity sanity gate.
- Nếu vision đủ confidence nhưng không có radar match hợp lệ, pipeline có thể
  xuất vision-only lead.
- Radar-only fallback chỉ dùng ở tốc độ ego dưới `4 m/s`, `|yRel| < 1 m` và
  `0,75 < dRel < 25 m`.
- Code ghi rõ stationary radar point có thể là false-positive và point quá gần
  có thể là radar glitch.

Các threshold trên là implementation detail của openpilot cho hardware/vehicle
được hỗ trợ, không phải chuẩn AEB. Các nguyên tắc có thể khái quát gồm:

- Dùng uncertainty của camera khi association.
- Bù độ trễ sensor.
- Có sanity gate trước khi nhận match.
- Cho phép vision-only/radar-only fallback nhưng giới hạn ODD.
- Radar-only fallback nên hẹp hơn khi confidence thấp.

Nguồn:

- [openpilot - `radard.py`](https://github.com/commaai/openpilot/blob/master/selfdrive/controls/radard.py)
- [openpilot - Supported cars và ghi chú AEB](https://github.com/commaai/openpilot/blob/master/docs/CARS.md)
- [openpilot - Safety](https://docs.comma.ai/concepts/safety/)

### 9.3 Apollo

Apollo là full autonomous-driving stack. Nó không tổ chức AEB thành một file
TTC độc lập; chức năng tránh va chạm được chia qua perception, prediction,
planning và control.

#### Perception Và Fusion

```text
LiDAR detection/tracking
Camera tracking
Radar detection/re-tracking
        |
PrefusedObjects
        |
probabilistic multi-sensor fusion
        |
PerceptionObstacles
```

Radar module nhận object đã được radar driver phát hiện và track, nhưng Apollo
vẫn re-track trước khi gửi tới fusion. Điều này phản ánh thực tế rằng object
list của sensor chưa nhất thiết đủ ổn định cho planning.

Multi-sensor fusion là post-processing probabilistic fusion của LiDAR, camera
và radar. Output là object thống nhất cho downstream module, thay vì để mỗi
sensor tự kích hoạt phanh.

#### Prediction Và Planning

Prediction nhận position, heading, velocity và acceleration của object rồi tạo
nhiều predicted trajectory kèm xác suất. Repo phân biệt:

- `Ignore`: object đủ xa hoặc không liên quan.
- `Caution`: có khả năng tương tác cao với ego.
- `Normal`: các object còn lại.

Prediction chỉ dự đoán target; planning tạo trajectory ego. Như vậy collision
check có thể xét cả tương lai ego và target, cần thiết cho cut-in, giao lộ và
đổi làn.

Điểm nên học:

- Sensor-specific tracking trước fusion.
- Unified object model sau fusion.
- Target prediction nhiều giả thuyết.
- Tách object prediction khỏi ego planning.
- Risk không chỉ dựa trên target gần nhất tại thời điểm hiện tại.

Một hệ AEB car-to-car không nhất thiết phải sao chép toàn bộ Apollo. Biểu diễn
fused track tối thiểu có thể gồm:

```text
position + velocity + class + confidence + age + source mask
```

Sau đó dùng constant-velocity prediction ngắn hạn trước khi cân nhắc mô hình
phức tạp hơn.

Nguồn:

- [Apollo - Radar detection](https://github.com/ApolloAuto/apollo/tree/master/modules/perception/radar_detection)
- [Apollo - Multi-sensor fusion](https://github.com/ApolloAuto/apollo/tree/master/modules/perception/multi_sensor_fusion)
- [Apollo - Prediction](https://github.com/ApolloAuto/apollo/tree/master/modules/prediction)
- [Apollo - Repository](https://github.com/ApolloAuto/apollo)

### 9.4 ROS 2 Navigation2 Collision Monitor

Nav2 không phải hệ ô tô, nhưng `nav2_collision_monitor` là ví dụ rõ về lớp an
toàn độc lập trên robot tự hành. Node nhận LaserScan, PointCloud2, Range hoặc
costmap rồi lọc lệnh vận tốc trước khi gửi đến robot.

Các model:

- `Stop`: đủ số point trong safety zone thì dừng.
- `Slowdown`: đủ số point thì giảm lệnh vận tốc theo tỷ lệ.
- `Limit`: giới hạn vận tốc.
- `Approach`: chiếu chuyển động hiện tại và giữ time-to-collision lớn hơn
  ngưỡng đặt trước.

Zone có thể là polygon, circle, footprint hoặc `VelocityPolygon`. Zone thay đổi
theo tốc độ là bài học quan trọng: xe chạy nhanh cần hành lang nhìn xa hơn xe
chạy chậm.

Khi nhiều zone cùng kích hoạt, hành động mạnh nhất thắng. Repo còn có:

- `trigger_consecutive_points`.
- `release_consecutive_points`.

Đây chính là debounce/hysteresis theo số chu kỳ để giảm trạng thái nhấp nháy do
nhiễu sensor.

Điểm chuyển sang AEB ô tô:

- Có lớp safety độc lập với planner.
- Dùng vùng cảnh báo, vùng giảm tốc và vùng dừng khác nhau.
- Safety zone phụ thuộc vận tốc.
- Tách trigger và release confirmation.
- Có thể chạy logic cảnh báo riêng mà không tác động control.

Nguồn:

- [Nav2 - Collision Monitor source](https://github.com/ros-navigation/navigation2/tree/main/nav2_collision_monitor)
- [Nav2 - Collision Monitor configuration](https://docs.nav2.org/configuration/packages/collision_monitor/configuring-collision-monitor-node.html)

### 9.5 So Sánh Các Repo

| Repo | Input chính | Biểu diễn nguy cơ | Output | Bài học phù hợp |
|---|---|---|---|---|
| Autoware AEB | Point cloud, predicted object, IMU/MPC path | Swept footprint + braking distance | Emergency diagnostic | AEB decision độc lập |
| openpilot | Vision lead + radar object tracks + car state | Fused lead, sanity gates | Lead state cho longitudinal/FCW | Association và fallback |
| Apollo | LiDAR/camera/radar objects, map, localization | Predicted trajectories + planning | Trajectory/control | Kiến trúc full stack |
| Nav2 Collision Monitor | Scan/point cloud/range + velocity command | Safety zone hoặc TTC | Stop/slow/limit command | Safety layer, debounce |

Nhận xét tổng hợp:

1. Autoware minh họa rõ một module AEB độc lập dựa trên predicted path và
   khoảng cách phanh.
2. openpilot minh họa camera-radar association, uncertainty gate và fallback.
3. Apollo minh họa tracking, fusion và prediction trong một full stack.
4. Nav2 minh họa lớp safety độc lập, vùng hành động và debounce theo thời gian.

## 10. Bảng So Sánh Các Hướng Kiến Trúc

| Hướng | Ví dụ công khai | Điểm mạnh | Rủi ro chính |
|---|---|---|---|
| Radar + vehicle dynamics | Toyota/Honda đời đầu | Range, Doppler, ngày đêm | Phân loại và stationary target |
| Một camera | Mobileye Base ADAS | Giá thấp, semantic tốt | Depth và điều kiện quang học |
| Stereo camera | Subaru EyeSight | Semantic + depth hình học | Texture, ánh sáng, calibration |
| Multi-camera vision | Tesla | FOV rộng, học từ dữ liệu camera | Phụ thuộc vision và calibration |
| Camera + radar | Volvo, Toyota, Honda, Bosch | Bổ sung range/class, robust hơn | Association và đồng bộ |
| Multi-camera + multi-radar | Mobileye Surround, ZF | Giao lộ, crossing, redundancy | Cost và validation phức tạp |
| Camera + radar + LiDAR | Kiến trúc AD cao cấp | Hình học và redundancy mạnh | Giá, compute, integration |

Không nên kết luận kiến trúc nhiều sensor luôn tốt hơn. Một hệ ít sensor nhưng
được calibration và validation tốt có thể ổn định hơn một hệ nhiều sensor có
association yếu.

## 11. Tiêu Chuẩn Và Quy Định

### 11.1 ISO 22839

ISO 22839:2013 quy định khái niệm vận hành, chức năng tối thiểu, yêu cầu hệ
thống và phương pháp kiểm thử cho Forward Vehicle Collision Mitigation Systems.
Tiêu chuẩn được ISO xác nhận lại năm 2024 và vẫn còn hiệu lực.

Nguồn:

- [ISO 22839:2013](https://www.iso.org/standard/45339.html)

### 11.2 UNECE Regulation No. 152

UN Regulation No. 152 quy định Advanced Emergency Braking System cho xe hạng
nhẹ trong hệ thống type approval UNECE. Tài liệu bao gồm yêu cầu hệ thống,
cảnh báo, can thiệp, kiểm tra lỗi và thử nghiệm hiệu năng.

Nguồn:

- [UNECE - UN Regulation No. 152 Rev.2](https://unece.org/transport/documents/2023/06/standards/un-regulation-no-152-rev2)

### 11.3 NHTSA FMVSS No. 127

Ngày 29/04/2024, NHTSA công bố final rule FMVSS No. 127. Quy định yêu cầu AEB,
bao gồm pedestrian AEB, trở thành trang bị tiêu chuẩn trên hầu hết xe con và
light truck mới tại Mỹ trước tháng 09/2029.

Các điểm chính được NHTSA công bố:

- Xe phải tránh va chạm với lead vehicle trong các bài test đến khoảng
  100 km/h.
- Hệ thống phải tự động áp phanh khi va chạm với lead vehicle sắp xảy ra trong
  phạm vi yêu cầu đến khoảng 145 km/h.
- Pedestrian AEB hoạt động trong phạm vi yêu cầu đến khoảng 73 km/h.
- Cảnh báo gồm tín hiệu âm thanh và hình ảnh.
- Hệ thống phải phát hiện lỗi, bao gồm suy giảm chỉ do sensor bị che, và báo
  trạng thái cho người lái.

Tiêu chuẩn đặt yêu cầu hiệu năng, không bắt buộc hãng phải dùng radar, camera
hay một kiến trúc fusion cụ thể.

Nguồn:

- [NHTSA - AEB Final Rule](https://www.nhtsa.gov/press-releases/nhtsa-fmvss-127-automatic-emergency-braking-reduce-crashes)
- [NHTSA - FMVSS No. 127 Full Text](https://www.nhtsa.gov/sites/nhtsa.gov/files/2024-04/final-rule-automatic-emergency-braking-systems-light-vehicles_web-version.pdf)

### 11.4 Euro NCAP

Euro NCAP AEB Car-to-Car Test Protocol v4.3.1 định nghĩa bảy nhóm:

- `CCRs`: target phía trước đứng yên.
- `CCRm`: target phía trước chạy đều.
- `CCRb`: target phía trước phanh.
- `CCFtap`: ego rẽ cắt ngang xe đối diện.
- `CCCscp`: hai xe đi thẳng cắt ngang tại giao lộ.
- `CCFhos`: head-on do xe đối diện lệch làn.
- `CCFhol`: head-on do xe đối diện đổi làn để vượt.

Global Vehicle Target được thiết kế để tái tạo thuộc tính camera, radar 24/77
GHz và LiDAR. Điều này tiếp tục cho thấy protocol đánh giá hiệu năng hệ thống,
không ưu tiên một modality duy nhất.

Euro NCAP còn yêu cầu OEM mô tả cho một số bài test:

- Kiến trúc sensor và fusion.
- TTC cảnh báo và AEB activation.
- ODD và giới hạn vận hành.
- Điều kiện override.
- Validation SiL, HiL, ViL và physical test.
- Bằng chứng giảm false-positive ngoài thực tế.

Nguồn:

- [Euro NCAP - AEB Car-to-Car v4.3.1](https://cdn.euroncap.com/cars/assets/euro_ncap_aeb_c2c_test_protocol_v431_532926aad1.pdf)
- [Euro NCAP - Safety Assist Protocols](https://www.euroncap.com/safety-assist/)

#### Cập Nhật Giao Thức Euro NCAP 2026

Từ năm 2026, Euro NCAP tổ chức rating theo bốn giai đoạn:

1. Safe Driving.
2. Crash Avoidance.
3. Crash Protection.
4. Post-Crash Safety.

AEB và các can thiệp tránh va chạm được đặt trong nhóm Crash Avoidance, gồm
các protocol riêng cho frontal collision, lane-departure collision và
low-speed collision. Vì vậy `AEB Car-to-Car v4.3.1` vẫn hữu ích để mô tả chi
tiết các kịch bản C2C cũ, nhưng không đại diện toàn bộ khung chấm điểm 2026.

Nguồn:

- [Euro NCAP - 2026 Protocols](https://www.euroncap.com/en/for-engineers/protocols/2026-protocols/)
- [Euro NCAP - Thay đổi giao thức 2026](https://www.euroncap.com/press-media/euro-ncap-announces-2026-protocol-changes-to-tackle-modern-driving-risks/)

### 11.5 NHTSA NCAP ADAS 2026

Ngày 07/05/2026, NHTSA công bố các bài đánh giá pass/fail ADAS mới trong NCAP.
Bốn bài mới gồm:

- Pedestrian AEB.
- Lane Keeping Assistance.
- Blind Spot Warning.
- Blind Spot Intervention.

Bốn tiêu chí ADAS trước đó gồm:

- Forward Collision Warning.
- Crash Imminent Braking.
- Dynamic Brake Support.
- Lane Departure Warning.

Đây là chương trình đánh giá người tiêu dùng, khác với yêu cầu pháp lý tối thiểu
của FMVSS No. 127.

Nguồn:

- [NHTSA - New ADAS tests in NCAP, 07/05/2026](https://www.nhtsa.gov/press-releases/tesla-model-y-first-vehicle-pass-nhtsa-new-advanced-driver-assistance-system-tests)

## 12. Các Tình Huống Khó Và Cách Xử Lý

### 12.1 Stationary Object

Vấn đề:

- Radar có thể thấy cầu, biển, lan can hoặc mặt đường.
- Bỏ toàn bộ stationary object sẽ bỏ sót xe dừng.

Biện pháp:

- Camera xác nhận class.
- Map/lane ROI.
- Kiểm tra object nằm trên predicted path.
- Persistence nhiều frame.
- Kiểm tra chiều cao và kích thước cluster.
- Threshold khác nhau theo tốc độ và confidence.

### 12.2 Đường Cong Và Chuyển Làn

Vấn đề:

- Corridor thẳng nhận tường hoặc xe làn bên cạnh.
- Yaw-rate hiện tại có thể không phản ánh ý định chuyển làn sắp tới.

Biện pháp:

- Predicted path từ IMU/steering.
- Ưu tiên trajectory planner/MPC khi hợp lệ.
- Camera lane hoặc map ROI.
- Giới hạn lateral deviation của path.
- Driver steering override.

### 12.3 Cut-in

Vấn đề:

- Target ban đầu ở ngoài hành lang nhưng đang cắt vào.
- TTC dọc có thể chưa phản ánh lateral collision.

Biện pháp:

- Track `x, y, vx, vy`.
- Dự đoán polygon giao với ego corridor.
- Camera xác nhận indicator, orientation hoặc lane crossing.
- Confidence tăng theo nhiều frame.

### 12.4 Che Khuất

Vấn đề:

- Camera chỉ thấy một phần target.
- Radar point có thể bị gán nhầm sang box phía trước hoặc phía sau.

Biện pháp:

- Fusion có depth/range gate.
- Track persistence qua mất dấu ngắn.
- Multi-hypothesis association khi hai target gần nhau.
- Không dùng một radar point làm đại diện toàn bộ vật thể.

### 12.5 Mưa, Sương, Đêm Và Lóa

Biện pháp:

- Radar hỗ trợ camera.
- Sensor blockage detection.
- Giảm ODD hoặc báo unavailable.
- Điều chỉnh confidence và ngưỡng can thiệp.
- Test theo nhiều điều kiện môi trường.

### 12.6 Mặt Đường Và Vật Thể Thấp

Biện pháp:

- So sánh point với mặt đường từ map hoặc ground-plane estimate.
- Lọc theo chiều cao tương đối.
- Cluster geometry.
- Camera/free-space xác nhận.
- Không chỉ lọc theo altitude radar cố định vì đường có dốc.

## 13. An Toàn Chức Năng Và SOTIF

AEB liên quan trực tiếp đến điều khiển phanh nên cần xem xét:

- Sensor hoặc ECU hỏng.
- Timestamp sai hoặc mất frame.
- Calibration sai.
- Sensor bị che.
- Model nhận diện sai trong điều kiện vẫn hoạt động bình thường.
- False-positive gây phanh không mong muốn.
- False-negative gây bỏ lỡ va chạm.

Hai nhóm vấn đề khác nhau:

- `Functional safety`: lỗi phần cứng/phần mềm, thường liên quan ISO 26262.
- `SOTIF`: chức năng không đủ an toàn dù hệ thống không bị hỏng, thường liên
  quan ISO 21448.

Một prototype hoặc repo nghiên cứu không mặc nhiên chứng minh đạt ISO 26262 hay
ISO 21448. Khi chưa có quy trình safety case và bằng chứng validation đầy đủ,
chỉ nên nói rằng thiết kế có tham khảo các nguyên tắc:

- Diagnostic.
- Degraded mode.
- Confidence.
- Redundancy.
- Traceability.
- Scenario-based verification.

## 14. Chỉ Số Đánh Giá

### 14.1 Perception

- Precision, recall, mAP của camera detector.
- Range/velocity error của radar track.
- Association accuracy.
- Track confirmation time.
- Track loss rate.
- False target rate.

### 14.2 Risk Assessment

- TTC error.
- Target selection accuracy.
- False-positive brake events.
- Missed brake events.
- Warning timing.
- AEB activation timing.

### 14.3 Vehicle Response

- Initial speed.
- Target speed.
- Relative speed.
- Brake onset time.
- Peak and average deceleration.
- Jerk.
- Stopping distance.
- Impact speed hoặc avoided collision.
- Distance margin tại thời điểm dừng.

### 14.4 Robustness

- Đường thẳng và đường cong.
- Làn bên cạnh có xe.
- Lan can, tường, cây và mặt đường.
- Target đứng yên, chạy đều, phanh.
- Cut-in và cut-out.
- Sensor noise, dropout và latency.
- Camera tối, lóa hoặc bị che.
- Radar point thưa hoặc ghost detection.

## 15. Kết Luận

Các hệ AEB phát triển theo hai hướng song song:

1. Giảm chi phí bằng perception camera mạnh hơn.
2. Tăng robustness bằng camera-radar hoặc fusion đa cảm biến.

Radar-only phù hợp bài toán car-to-car cơ bản nhưng cần predicted path,
clustering, tracking và stationary-object handling. Camera-only có lợi thế về
phân loại nhưng phải giải bài toán depth và điều kiện quang học. Camera-radar
là điểm cân bằng phổ biến vì radar cung cấp range/Doppler còn camera cung cấp
class và ngữ cảnh. Multi-sensor mở rộng ODD và redundancy nhưng làm calibration,
fusion và validation phức tạp hơn.

Điểm chung giữa các hãng không phải là một threshold TTC cụ thể, mà là:

- Chỉ chọn target liên quan đến đường đi.
- Theo dõi qua thời gian.
- Kết hợp nhiều chỉ số nguy cơ.
- Cảnh báo trước khi can thiệp mạnh khi còn thời gian.
- Hỗ trợ người lái phanh.
- Phanh tự động khi nguy cơ đủ chắc chắn.
- Có hysteresis, override, diagnostics và giới hạn vận hành.
- Kiểm thử bằng scenario có thể lặp lại và dữ liệu thực tế.

Các công bố của hãng và repo mã nguồn mở cho thấy không tồn tại một công thức
TTC hay một kiến trúc sensor duy nhất phù hợp mọi ODD. Một hệ AEB có cơ sở khoa
học cần tách rõ perception, tracking, target relevance, risk assessment và
brake control; đồng thời phải được đánh giá bằng kịch bản có thể lặp lại.

## 16. Danh Sách Nguồn Chính

### Tiêu Chuẩn Và Cơ Quan Đánh Giá

1. [NHTSA - Driver Assistance Technologies](https://www.nhtsa.gov/vehicle-safety/driver-assistance-technologies)
2. [NHTSA - FMVSS No. 127 AEB Final Rule](https://www.nhtsa.gov/press-releases/nhtsa-fmvss-127-automatic-emergency-braking-reduce-crashes)
3. [NHTSA - FMVSS No. 127 Full Text](https://www.nhtsa.gov/sites/nhtsa.gov/files/2024-04/final-rule-automatic-emergency-braking-systems-light-vehicles_web-version.pdf)
4. [Euro NCAP - AEB Car-to-Car Test Protocol v4.3.1](https://cdn.euroncap.com/cars/assets/euro_ncap_aeb_c2c_test_protocol_v431_532926aad1.pdf)
5. [Euro NCAP - Safety Assist Protocols](https://www.euroncap.com/safety-assist/)
6. [UNECE - UN Regulation No. 152 Rev.2](https://unece.org/transport/documents/2023/06/standards/un-regulation-no-152-rev2)
7. [ISO 22839:2013](https://www.iso.org/standard/45339.html)
8. [SAE J3016 Levels of Driving Automation](https://www.sae.org/binaries/content/assets/cm/content/blog/sae-j3016-visual-chart_5.3.21.pdf)
9. [NHTSA - New ADAS tests in NCAP, 07/05/2026](https://www.nhtsa.gov/press-releases/tesla-model-y-first-vehicle-pass-nhtsa-new-advanced-driver-assistance-system-tests)
10. [Euro NCAP - 2026 Protocols](https://www.euroncap.com/en/for-engineers/protocols/2026-protocols/)
11. [Euro NCAP - Thay đổi giao thức 2026](https://www.euroncap.com/press-media/euro-ncap-announces-2026-protocol-changes-to-tackle-modern-driving-risks/)
12. [Mobileye - Responsibility-Sensitive Safety](https://www.mobileye.com/technology/responsibility-sensitive-safety/)

### Hãng Xe Và Nhà Cung Cấp

13. [Toyota - Pre-crash Safety 2002](https://global.toyota/en/detail/211112)
14. [Toyota - Safety Sense Evolution](https://pressroom.toyota.com/the-evolution-of-safety-at-toyota-part-2-toyota-safety-sense-for-all/)
15. [Honda - CMS 2003](https://global.honda/en/newsroom/news/2003/4030520-eng.html)
16. [Honda SENSING](https://global.honda/en/tech/Safety_and_driver_assistive_technologies_Honda_SENSING/)
17. [Subaru EyeSight Guide](https://techinfo.subaru.com/stis/doc/ownerManual/MSA5B2304A_2nd.pdf)
18. [Tesla Model 3 - Cameras](https://www.tesla.com/ownersmanual/model3/en_us/GUID-682FF4A7-D083-4C95-925A-5EE3752F4865.html)
19. [Tesla Model 3 - Collision Avoidance Assist](https://www.tesla.com/ownersmanual/model3/en_us/GUID-8EA7EF10-7D27-42AC-A31A-96BCE5BC0A85.html)
20. [Volvo - Collision Warning with Auto Brake](https://www.media.volvocars.com/global/en-gb/media/pressreleases/13830/)
21. [Volvo - Pedestrian Detection with Full Auto Brake](https://www.media.volvocars.com/global/en-gb/media/pressreleases/31773)
22. [Mobileye ADAS Platforms](https://www.mobileye.com/solutions/adas/)
23. [Bosch - Automatic Emergency Braking](https://www.bosch-mobility.com/en/solutions/assistance-systems/automatic-emergency-braking/)
24. [Continental - MFC527 Camera Platform](https://www.continental-automotive.com/en/components/cameras/multi-function-mono-camera-mfc527.html)
25. [ZF - OnGuardMAX](https://www.zf.com/products/en/cv/products_76928.html)
26. [ZF - Automated Driving Functions](https://press.zf.com/press/en/releases/release_2986.html)

### Nguyên Lý Và Thông Số Sensor

27. [OpenCV - Camera calibration và mô hình pinhole](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html)
28. [TI - mmWave fundamentals: range, velocity and angle](https://www.ti.com/document-viewer/lit/html/sszt906)
29. [Bosch - Radar sensor](https://www.bosch-mobility.com/en/solutions/sensors/radar-sensor/)
30. [Continental - ARS540](https://www.continental-automotive.com/en/components/radars/long-range-radars/advanced-radar-sensor-ars540.html)
31. [ZF - Sensor Power](https://press.zf.com/press/en/releases/release_3394.html)
32. [ZF - Smart Camera 6](https://press.zf.com/press/en/releases/release_88128.html)
33. [Ouster - OS1 LiDAR](https://ouster.com/products/hardware/os1-lidar-sensor)
34. [Bosch - Ultrasonic sensor](https://www.bosch-mobility.com/en/solutions/sensors/ultrasonic-sensor/)
35. [Continental - CUS320](https://www.continental-automotive.com/en/components/sensors/parking-sensors/ultrasonic-parking-sensor.html)
36. [Bosch Sensortec - IMU overview](https://www.bosch-sensortec.com/products/motion-sensors/imus/)

### Phần Mềm Tự Hành Tham Khảo

37. [Autoware - Autonomous Emergency Braking](https://autowarefoundation.github.io/autoware_universe/main/control/autoware_autonomous_emergency_braking/)
38. [Autoware - AEB source](https://github.com/autowarefoundation/autoware_universe/tree/main/control/autoware_autonomous_emergency_braking)
39. [Autoware - MPC lateral controller](https://autowarefoundation.github.io/autoware_universe/main/control/autoware_mpc_lateral_controller/)
40. [openpilot - `radard.py`](https://github.com/commaai/openpilot/blob/master/selfdrive/controls/radard.py)
41. [openpilot - Supported cars](https://github.com/commaai/openpilot/blob/master/docs/CARS.md)
42. [openpilot - Safety](https://docs.comma.ai/concepts/safety/)
43. [Apollo - Radar detection](https://github.com/ApolloAuto/apollo/tree/master/modules/perception/radar_detection)
44. [Apollo - Multi-sensor fusion](https://github.com/ApolloAuto/apollo/tree/master/modules/perception/multi_sensor_fusion)
45. [Apollo - Prediction](https://github.com/ApolloAuto/apollo/tree/master/modules/prediction)
46. [Apollo - Repository](https://github.com/ApolloAuto/apollo)
47. [Nav2 - Collision Monitor](https://github.com/ros-navigation/navigation2/tree/main/nav2_collision_monitor)
48. [Nav2 - Collision Monitor configuration](https://docs.nav2.org/configuration/packages/collision_monitor/configuring-collision-monitor-node.html)
