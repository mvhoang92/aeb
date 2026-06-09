# Nghiên Cứu Lọc Nhiễu Radar Và Quyết Định Phanh AEB

Ngày tổng hợp: 05/06/2026.

Tài liệu này đối chiếu tài liệu chính thức của nhà cung cấp ô tô, hướng dẫn của
hãng xe và mã nguồn các dự án tự hành. Mục tiêu là chọn cách xử lý phù hợp cho
prototype AEB trên CARLA 0.9.11, không sao chép nguyên tham số của một hệ thống
thực tế sang mô phỏng.

## Kết Luận Ngắn

Một radar point có TTC thấp **không đủ** để kích hoạt phanh. Các hệ thống đáng
tin cậy thường đi qua chuỗi:

```text
Radar detection
  -> lọc vùng quan tâm và mặt đường
  -> gom điểm thành vật thể
  -> tracking nhiều frame
  -> kiểm tra động học và độ tin cậy
  -> kiểm tra vật thể có nằm trên quỹ đạo va chạm
  -> camera/map xác nhận khi có thể
  -> cảnh báo
  -> phanh một phần hoặc phanh khẩn cấp
```

Đối với dự án hiện tại, ba cải tiến có giá trị cao nhất là:

1. Làm mượt trạng thái track bằng bộ lọc alpha-beta hoặc Kalman, kèm loại
   velocity outlier theo lịch sử.
2. Tách `track đã tồn tại` khỏi `nguy hiểm đã được xác nhận`: chỉ phanh sau
   ít nhất 2 frame nguy hiểm liên tiếp, trừ tình huống cực kỳ khẩn cấp.
3. Chọn target theo độ thiếu khoảng cách dừng và quỹ đạo va chạm, không chỉ lấy
   TTC nhỏ nhất.

## CARLA 0.9.11 Đang Mô Phỏng Loại Radar Nào?

CARLA trả về danh sách `RadarDetection`, mỗi detection có:

- `depth`: khoảng cách.
- `azimuth`: góc ngang.
- `altitude`: góc dọc.
- `velocity`: vận tốc tương đối theo hướng tia radar.

Radar CARLA tạo vùng quét hình nón và raycast vào vật thể. Đây là dữ liệu
**sau phát hiện**, không phải tín hiệu FMCW thô, ADC sample, range-Doppler map
hay range-azimuth heatmap của radar thật.

Vì vậy dự án có thể nghiên cứu tốt:

- Lọc point sau phát hiện.
- Clustering, tracking và data association.
- Lọc mặt đường, vật thể ngoài làn và ghost point theo thời gian.
- Camera-radar fusion.
- TTC, khoảng cách dừng và logic AEB.

Dự án không thể tái hiện trung thực chỉ bằng sensor hiện tại:

- Range FFT, Doppler FFT và angle-of-arrival.
- CFAR trên range-Doppler/range-azimuth heatmap.
- Nhiễu tương hỗ giữa nhiều radar.
- Multipath và phản xạ điện từ theo vật liệu.
- Radar cross section, micro-Doppler và raw-signal interference mitigation.

Trong báo cáo sau này cần gọi đúng phạm vi là **lọc và tracking radar detection
trong CARLA**, không nên gọi là xử lý tín hiệu radar thô.

## Các Hãng Và Nhà Cung Cấp Xử Lý AEB Như Thế Nào?

Các hãng không công khai đầy đủ thuật toán production, threshold và calibration
vì đây là phần sở hữu trí tuệ và an toàn chức năng. Tuy nhiên tài liệu công khai
cho thấy các nguyên tắc chung sau.

### Bosch

Bosch mô tả AEB theo nhiều tầng:

1. Chuẩn bị hệ thống phanh khi khoảng cách trở nên nguy hiểm.
2. Cảnh báo bằng hình ảnh hoặc âm thanh.
3. Tạo một nhịp phanh để thu hút sự chú ý.
4. Phanh một phần, đồng thời hỗ trợ lực phanh nếu người lái phản ứng chưa đủ.
5. Chỉ tự động phanh toàn lực khi va chạm được đánh giá là không thể tránh.

Bosch cũng nêu việc dùng radar cùng camera để thu nhận, phân loại và tracking
vật thể tin cậy hơn. Ý nghĩa đối với dự án là không nên chuyển trực tiếp từ
`NORMAL` sang `brake = 1.0` chỉ bởi một measurement bất thường.

### Continental

Radar trước Continental ARS51x có chu kỳ cập nhật công bố là khoảng 55 ms,
tương đương xấp xỉ 18 Hz. Nó hỗ trợ Emergency Brake Assist, đo elevation,
blockage detection, auto-alignment và fusion với camera/navigation.

Radar cao cấp ARS540 công bố:

- Đo range, Doppler, azimuth và elevation.
- Multi-hypothesis tracking.
- Phân loại phương tiện giao thông và hạ tầng.
- Độ chính xác góc cao hơn và cập nhật khoảng 60 ms.

Điểm đáng chú ý là radar thực tế cung cấp **object track đã qua xử lý**, không
đơn thuần ném từng tia độc lập cho AEB. Tần số 20 Hz đang dùng trong
`sensors.yaml` là hợp lý cho prototype và gần chu kỳ một số radar thương mại.

### Volvo

Volvo công khai ba mức hỗ trợ của Collision Avoidance:

1. Cảnh báo va chạm.
2. Hỗ trợ phanh.
3. Tự động phanh.

Hệ thống được thiết kế can thiệp muộn nhất có thể nhưng vẫn đủ sớm để giảm hoặc
tránh va chạm. Triết lý này ưu tiên giảm false-positive và giữ quyền điều khiển
cho người lái.

### Tesla

Hướng dẫn Model 3 nêu rằng AEB có thể không phanh hoặc ngừng phanh khi:

- Người lái đánh lái mạnh.
- Người lái tác động phanh.
- Người lái tăng ga mạnh.
- Target không còn được phát hiện.

Tesla cũng cảnh báo AEB có thể phanh không phù hợp hoặc không đúng thời điểm.
Đây là bằng chứng thực tế cho việc cần driver override, target persistence và
logic hủy can thiệp, thay vì giữ phanh chỉ dựa trên TTC cũ.

### Mẫu Số Chung Từ Hãng

| Thành phần | Cách tiếp cận thường thấy |
|---|---|
| Nhận thức | Radar cung cấp range/relative speed; camera tăng khả năng phân loại |
| Tracking | Theo dõi vật thể qua thời gian, không quyết định từ một point |
| Relevance | Chỉ xét target nằm trên đường đi hoặc có khả năng cắt vào đường đi |
| HMI | Cảnh báo hình ảnh/âm thanh xuất hiện trước phanh mạnh |
| Phanh | Chuẩn bị phanh, phanh một phần, rồi mới phanh khẩn cấp |
| Hysteresis | Giữ/hủy trạng thái có điều kiện để tránh rung lắc quyết định |
| Người lái | Đánh lái, ga hoặc phanh chủ động có thể thay đổi/hủy can thiệp |
| Fusion | Camera/radar/map được dùng để tăng độ tin cậy và giảm vật cản giả |

## Các Repo Tự Hành Xử Lý Radar Như Thế Nào?

### Autoware

#### Autonomous Emergency Braking

Pipeline AEB của Autoware có cấu trúc rất gần bài toán hiện tại:

1. Sinh predicted path từ IMU hoặc quỹ đạo MPC.
2. Mở rộng footprint của ego thành vùng tìm kiếm.
3. Bỏ point cloud ngoài vùng dự đoán va chạm.
4. Gom cụm bằng Euclidean clustering.
5. Lọc cụm theo số point và chiều cao tối thiểu.
6. Tính vận tốc target từ lịch sử.
7. Chọn vật cản gần nhất có liên quan.
8. Dùng khoảng cách kiểu RSS để quyết định emergency stop.
9. Giữ trạng thái va chạm và lịch sử obstacle trong một khoảng thời gian.

Công thức RSS được Autoware dùng có dạng:

```text
d_safe =
    v_ego * t_response
    + v_ego^2 / (2 * a_ego)
    - sign(v_object) * v_object^2 / (2 * a_object)
    + offset
```

Điểm mạnh nhất cần học là AEB đánh giá vật thể trong **predicted footprint** và
dùng khoảng cách dừng vật lý. TTC chỉ là một chỉ báo, không phải toàn bộ logic.

Một số tham số Autoware như cluster tối thiểu 10 point phù hợp LiDAR/point cloud
dày, nhưng không phù hợp radar CARLA thưa. Không nên sao chép con số này vào
dự án.

#### Radar Object Tracker

Radar tracker của Autoware sử dụng:

- Global nearest-neighbor association.
- Cổng theo khoảng cách, diện tích, yaw, IoU và Mahalanobis distance.
- Track chỉ được publish sau đủ số measurement.
- Track bị xóa sau một khoảng lifetime nếu không có measurement mới.
- Lọc theo map: khoảng cách tới lane, chênh lệch hướng và lateral velocity.
- EKF cho các mô hình chuyển động khác nhau.

Module radar crossing-noise filter lưu ý rằng Doppler theo trục dọc radar đáng
tin hơn lateral velocity ước lượng. Object có lateral velocity quá lớn có thể
bị coi là nhiễu.

Áp dụng cho dự án:

- Không dùng thay đổi velocity của một frame làm sự thật tuyệt đối.
- Dùng innovation gate giữa prediction và measurement.
- Kiểm tra hướng/lateral motion trước khi coi target là vật cản cùng làn.

### openpilot

`radard.py` của openpilot thực hiện các ý chính:

- Mỗi radar track được làm mượt bằng Kalman filter 1D.
- Bù độ trễ radar bằng lịch sử vận tốc ego.
- Ghép camera lead và radar track bằng xác suất dựa trên sai khác khoảng cách,
  vị trí ngang và vận tốc.
- Có sanity check về khoảng cách và vận tốc trước khi chấp nhận match.
- Chỉ fusion khi xác suất lead từ vision đủ cao.
- Dùng low-pass bất đối xứng để giữ lead qua một khoảng bất định ngắn.
- Có ngoại lệ radar-only ở tốc độ thấp với vùng rất hẹp trước xe.
- Ghi chú trong code rằng stationary radar point có thể là false-positive và
  point quá gần có thể là radar glitch.

Điểm quan trọng: openpilot nhận **track ID từ radar của xe**, không nhận các
raycast point thô như CARLA. Dự án của mình phải tự làm bước clustering và
tracking trước khi áp dụng kiểu fusion này.

### Apollo

Radar pipeline của Apollo thể hiện các lớp phòng vệ:

- Bỏ measurement có timestamp bất thường.
- Hiệu chỉnh độ trễ radar.
- Match track ID trước, sau đó mới property matching.
- Dự đoán vị trí theo velocity và timestamp trước khi association.
- Hungarian assignment để ghép track và measurement một-một.
- Track chỉ được publish sau đủ số lần quan sát.
- Xóa track quá thời gian theo dõi.
- Hỗ trợ Adaptive Kalman Filter với state `x, y, vx, vy`.
- HD-map ROI filter loại object ngoài vùng đường hợp lệ.

Config hiện tại của Apollo có thể bật/tắt filter tùy pipeline, nên điều cần học
là kiến trúc nhiều tầng và lifecycle của track, không phải một giá trị tham số
cụ thể.

## So Sánh Với Code Hiện Tại

Code hiện tại đã có nền tảng đúng hướng:

| Thành phần | Trạng thái hiện tại |
|---|---|
| Predicted path theo yaw-rate/steer | Đã có |
| Hành lang target phía trước | Đã có |
| Lọc độ cao so với waypoint mặt đường | Đã có |
| Clustering theo khoảng cách và velocity | Đã có |
| Xác nhận track nhiều frame | Đã có, mặc định 3 frame |
| Track stale không được phanh | Đã có |
| TTC và khoảng cách dừng | Đã có |
| Cảnh báo tách khỏi phanh | Đã có |
| Tắt AEB khi lùi | Đã có |

Các khoảng trống gây phanh nhầm:

1. **Track chưa có state estimator.** Vị trí và velocity được thay trực tiếp
   bằng measurement mới, nên một spike có thể làm TTC tụt mạnh.
2. **Association còn greedy.** Gate cố định theo khoảng cách/velocity có thể
   đổi ID hoặc ghép nhầm khi nhiều vật thể gần nhau.
3. **Confirmation chỉ xác nhận sự tồn tại.** Sau khi track đã confirmed, một
   frame velocity nguy hiểm có thể kích hoạt phanh ngay.
4. **Chọn target bằng TTC nhỏ nhất.** Một target xa nhưng velocity nhiễu mạnh
   có thể thắng target hợp lý hơn.
5. **Chưa có uncertainty/confidence.** Track 2 point và track nhiều point ổn
   định đang có quyền kích hoạt gần tương đương nhau.
6. **Chưa dùng camera để chặn phanh radar-only ở tốc độ cao.**
7. **Phanh nhị phân tạo jerk lớn.** Đây là baseline hợp lệ, nhưng không giống
   staged braking của hệ thống thực tế.

## Kiến Trúc Đề Xuất Cho Dự Án

### Lớp 1: Point Validation

Giữ các bộ lọc hiện tại và bổ sung kiểm tra:

- Range, vertical height và predicted-path corridor.
- Bỏ point sau xe hoặc quá gần vị trí radar.
- Bỏ point có relative velocity/acceleration phi vật lý.
- Giữ raw point trên UI để debug, nhưng không đưa point bị loại vào AEB.

Không nên tăng `min_points` quá cao. Với CARLA radar 2.000 point/s và 20 Hz,
số tia lý thuyết là khoảng 100 mỗi frame nhưng chỉ tia raycast trúng bề mặt mới
trở thành detection. Cluster 2-3 point có thể hợp lệ.

### Lớp 2: Clustering

Tiếp tục gom theo:

- Khoảng cách không gian.
- Chênh lệch relative velocity.
- Chênh lệch chiều cao.

Distance của cluster nên lấy percentile thấp như hiện tại thay vì point gần
nhất tuyệt đối. Velocity nên dùng median để chống outlier.

### Lớp 3: Tracking Và Lọc Nhiễu Thời Gian

Mỗi track nên có:

```text
x, y, vx_relative, vy_estimated
covariance hoặc confidence
hit_count, miss_count, age
history 3-5 frame
```

Phiên bản đầu chưa cần EKF phức tạp. Có thể dùng:

- Alpha-beta filter cho `x` và relative velocity.
- Median/MAD của 3-5 measurement gần nhất.
- Reject measurement nếu innovation vượt ngưỡng.
- Giới hạn thay đổi acceleration hợp lý.

Sau đó mới cân nhắc Kalman `x, y, vx, vy` và Hungarian assignment.

### Lớp 4: Target Relevance

Một target chỉ có quyền phanh khi:

- Track mới và đã confirmed.
- Nằm trong swept path/footprint của ego.
- Có closing speed hợp lệ.
- Không phải ground point.
- Động học của track nhất quán.

Với đường cong, dùng predicted path thay vì trục radar thẳng. Với cut-in, cần
ước lượng lateral motion và giao cắt giữa quỹ đạo target với swept path ego.

### Lớp 5: Risk Score

Không xếp hạng chỉ bằng TTC. Đề xuất ưu tiên:

```text
distance_margin = measured_distance - required_stopping_distance
```

Thứ tự chọn target:

1. `distance_margin` âm nhiều nhất.
2. TTC thấp nhất.
3. Confidence cao hơn.
4. Khoảng cách gần hơn.

Một risk score mở rộng có thể dùng:

```text
risk =
    w_margin * normalized_negative_margin
    + w_ttc * normalized_inverse_ttc
    + w_path * path_overlap
    + w_conf * track_confidence
    + w_camera * camera_confirmation
```

Trong giai đoạn đầu nên giữ luật quyết định rõ ràng, chưa cần học máy.

### Lớp 6: Xác Nhận Nguy Hiểm

Tách hai bộ đếm:

- `track_confirm_frames`: vật thể có thật và được bám ổn định.
- `danger_confirm_frames`: rủi ro phanh tồn tại liên tiếp.

Baseline đề xuất để test, chưa phải tham số cuối:

```yaml
track_confirm_frames: 3
danger_confirm_frames: 2
critical_ttc_s: 0.8
critical_distance_margin_m: -2.0
```

Nếu nguy hiểm chưa tới mức critical, yêu cầu 2 frame liên tiếp. Nếu TTC hoặc
distance margin cực kỳ nguy hiểm, cho phép bypass để tránh trễ phanh.

### Lớp 7: Camera-Radar Fusion

Ở tốc độ trung bình/cao:

- Radar track phải chiếu được vào camera.
- Projected point/track phải nằm trong hoặc gần bbox phương tiện.
- Sai khác timestamp phải nằm trong cửa sổ cho phép.
- Camera class và radar động học phải phù hợp.

Nếu camera chưa xác nhận:

- Vẫn hiện FCW/radar debug.
- Chỉ cho radar-only full brake khi mức nguy hiểm critical hoặc tốc độ thấp.

Đây là cách cân bằng giữa missed detection của camera và false-positive của
radar, gần với triết lý fusion trong openpilot nhưng phù hợp dữ liệu CARLA hơn.

### Lớp 8: Phanh Và Driver Override

State machine nên tiến dần tới:

```text
NORMAL
  -> WARNING
  -> PREFILL/PARTIAL_BRAKE
  -> EMERGENCY_BRAKE
  -> RELEASE
```

Prototype hiện tại có thể tiếp tục binary brake để kiểm chứng perception. Sau
khi target ổn định mới thêm PID hoặc brake profile.

Nên bổ sung:

- Hủy/giảm can thiệp khi người lái đánh lái mạnh khỏi vật cản.
- Chính sách rõ khi người lái đạp ga mạnh.
- Không phanh tiến khi xe đang lùi.
- Release khi target mất xác nhận, trừ thời gian hold tối thiểu cần thiết.
- Log đầy đủ lý do chuyển state.

## Thứ Tự Triển Khai Khuyến Nghị

### Giai Đoạn 1: Giảm Phanh Nhầm Radar-Only

1. Thêm history và median/MAD velocity cho track.
2. Thêm alpha-beta filter hoặc Kalman 1D.
3. Thêm `danger_confirm_frames`.
4. Đổi target ranking sang distance margin trước TTC.
5. Log innovation, confidence, raw/smoothed velocity và lý do reject.

### Giai Đoạn 2: Fusion

1. Đồng bộ camera-radar theo timestamp/frame.
2. Ghép projected radar track với YOLO bbox.
3. Dùng camera confirmation cho phanh tốc độ cao.
4. Giữ radar-only fallback ở low-speed/critical risk.

### Giai Đoạn 3: Điều Khiển Phanh

1. Thêm partial brake hoặc brake ramp.
2. Thêm PID theo target deceleration hoặc distance margin.
3. Thêm driver override và release logic.
4. Đo jerk, stopping distance và residual impact speed.

### Giai Đoạn 4: Kiểm Thử Nhiễu

Vì CARLA không tạo raw radar interference, cần tự inject nhiễu ở tầng detection:

- Một-frame ghost point.
- Velocity spike.
- Range jump.
- Mất measurement 1-3 frame.
- Duplicate cluster.
- Timestamp delay/out-of-order.
- Ground point tăng bất thường.

Kịch bản hình học cần có:

- Đường cong cạnh tường/hộ lan.
- Cây hoặc cột sát lề.
- Xe ở làn bên cạnh.
- Xe cắt vào và cắt ra.
- Xe trước đứng yên, chạy chậm và phanh gấp.
- Dốc, đỉnh dốc và mặt đường gồ.
- Nhiều xe gần nhau gây đổi track ID.

Metric nên ghi:

- False brake per kilometer hoặc per scenario.
- Missed brake.
- Time-to-brake.
- TTC và distance margin tại thời điểm phanh.
- Khoảng cách dừng còn lại.
- Residual impact speed.
- Số lần đổi target/track ID.
- Jerk cực đại.

## Cấu Hình Hiện Tại Có Hợp Lý Không?

Các giá trị sau phù hợp để tiếp tục nghiên cứu:

- Radar 20 Hz (`sensor_tick: 0.05`).
- Camera 20 Hz.
- Radar range 100 m.
- Horizontal FOV 30 độ cho bài toán highway phía trước.
- Vertical FOV 6 độ để hạn chế mặt đường và vùng không liên quan.
- `confirm_frames: 3`.
- `min_points: 2` cho point cloud radar CARLA thưa.

Các giá trị chưa nên coi là hoàn chỉnh:

- `brake_ttc_s: 1.5`.
- `response_time_s: 0.20`.
- `ego_emergency_decel_mps2: 8.0`.
- `target_emergency_decel_mps2: 6.0`.
- `stopping_distance_offset_m: 1.0`.
- `full_brake: 1.0`.

Các tham số phanh phải được tune bằng scenario và log theo từng tốc độ. Vấn đề
"phanh nhạy" hiện tại có khả năng đến từ nhiễu velocity/target ranking và thiếu
xác nhận nguy hiểm, không nên chỉ chữa bằng cách hạ ngưỡng TTC.

## Nguồn Chính

### Hãng Và Nhà Cung Cấp

- [Bosch - Automatic emergency braking](https://www.bosch-mobility.com/en/solutions/assistance-systems/automatic-emergency-braking/)
- [Bosch - AEB for vulnerable road users](https://www.bosch-mobility.com/en/solutions/assistance-systems/automatic-emergency-braking-on-vulnerable-road-users/)
- [Continental - ARS51x](https://www.continental-automotive.com/en/components/radars/long-range-radars/advanced-radar-sensor-ars51x.html)
- [Continental - ARS540](https://www.continental-automotive.com/en/components/radars/long-range-radars/advanced-radar-sensor-ars540.html)
- [Volvo - Collision avoidance](https://www.volvocars.com/en-ca/support/car/s60/20w17/article/6f60b45ac7fdcfa0c0a81f6f2323236f_8018a9b070cea65bc0a801513d2a04f3/)
- [Tesla Model 3 - Collision Avoidance Assist](https://www.tesla.com/ownersmanual/model3/en_us/GUID-8EA7EF10-7D27-42AC-A31A-96BCE5BC0A85.html)

### Repo Và Tài Liệu Kỹ Thuật

- [CARLA 0.9.11 - Sensors reference](https://carla.readthedocs.io/en/0.9.11/ref_sensors/)
- [TI mmWave SDK - CFAR processing](https://software-dl.ti.com/ra-processors/esd/MMWAVE-L-SDK/05_04_00_01/exports/api_guide_xwrL64xx/CFARPROC_PAGE.html)
- [Autoware - Autonomous Emergency Braking](https://autowarefoundation.github.io/autoware_universe/main/control/autoware_autonomous_emergency_braking/)
- [Autoware - AEB source](https://github.com/autowarefoundation/autoware_universe/tree/main/control/autoware_autonomous_emergency_braking)
- [Autoware - Radar object tracker](https://github.com/autowarefoundation/autoware_universe/tree/main/perception/autoware_radar_object_tracker)
- [Autoware - Radar tracks noise filter](https://github.com/autowarefoundation/autoware_universe/tree/main/sensing/autoware_radar_tracks_noise_filter)
- [openpilot - radard.py](https://github.com/commaai/openpilot/blob/master/selfdrive/controls/radard.py)
- [Apollo - radar detection](https://github.com/ApolloAuto/apollo/tree/master/modules/perception/radar_detection)
- [Apollo - radar matcher](https://github.com/ApolloAuto/apollo/blob/master/modules/perception/radar_detection/lib/tracker/matcher/hm_matcher.cc)
- [Apollo - adaptive Kalman filter](https://github.com/ApolloAuto/apollo/blob/master/modules/perception/radar_detection/lib/tracker/filter/adaptive_kalman_filter.cc)

## Lưu Ý Khi Dùng Tài Liệu Này Trong Báo Cáo

- Phân biệt rõ thông tin hãng công khai với suy luận kiến trúc từ repo.
- Không tuyên bố thuật toán của Bosch, Volvo, Tesla hoặc Continental giống hệt
  Autoware/openpilot/Apollo.
- Không tuyên bố prototype đạt chuẩn Euro NCAP nếu chưa chạy đúng protocol,
  target, vận tốc, overlap và metric của phiên bản protocol tương ứng.
- Ghi rõ CARLA radar là raycast detection model, không phải mô phỏng toàn bộ
  chuỗi tín hiệu radar 77 GHz.
