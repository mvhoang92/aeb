# Prompt Tạo Slide Báo Cáo ADAS Và AEB

Ngày tạo: 06/06/2026.

## Cách Sử Dụng

Sao chép toàn bộ phần **Prompt Chính** vào Gamma, Canva, PowerPoint Copilot
hoặc công cụ tạo slide. Nếu công cụ không đọc được file trong máy, nội dung
quan trọng đã được mô tả trực tiếp trong prompt.

Các hình mang tính kỹ thuật như pipeline, sensor fusion và state machine nên
được vẽ bằng shape/vector trong slide. Không dùng ảnh AI thay cho sơ đồ cần độ
chính xác.

## Prompt Chính

```text
Hãy tạo một bộ slide thuyết trình bằng tiếng Việt có dấu với chủ đề:

"NGHIÊN CỨU HỆ THỐNG ADAS VÀ XÂY DỰNG PHANH KHẨN CẤP TỰ ĐỘNG AEB
TRÊN CARLA 0.9.11"

Đối tượng nghe là giảng viên kỹ thuật. Mục tiêu của bài trình bày:

1. Giải thích ADAS và vai trò của AEB.
2. Trình bày nguyên lý camera, radar và sensor fusion.
3. So sánh các kiến trúc AEB từ đơn giản đến đa cảm biến.
4. Phân tích cách tiếp cận công khai của hãng xe và repo mã nguồn mở.
5. Trình bày kiến trúc dự án AEB đang xây dựng trên CARLA 0.9.11.
6. Nêu rõ giới hạn hiện tại và lộ trình phát triển tiếp theo.

YÊU CẦU CHUNG

- Tạo 17 slide, tỷ lệ 16:9, phù hợp bài nói 15-18 phút.
- Ngôn ngữ: tiếng Việt có dấu, giọng văn học thuật nhưng dễ trình bày.
- Mỗi slide tối đa 5 ý chính, mỗi ý không quá 15 từ nếu có thể.
- Không tạo đoạn văn dài trên slide.
- Mỗi slide phải có speaker notes từ 80-140 từ để người trình bày giải thích.
- Các thuật ngữ lần đầu xuất hiện phải ghi cả tên đầy đủ và viết tắt.
- Giữ các từ kỹ thuật cần thiết như TTC, FCW, AEB, radar, tracking, fusion.
- Không tuyên bố dự án đạt Euro NCAP, ISO 26262 hoặc tiêu chuẩn production.
- Phân biệt rõ dữ liệu công khai, kiến trúc tham khảo và suy luận kỹ thuật.
- Trích nguồn ngắn ở chân slide, ví dụ: NHTSA, Euro NCAP, Autoware, CARLA.
- Slide cuối có danh sách nguồn chính và đường dẫn rút gọn dễ đọc.

PHONG CÁCH THIẾT KẾ

- Phong cách kỹ thuật ô tô hiện đại, rõ ràng, không giống trang quảng cáo.
- Nền sáng trắng hoặc xám rất nhạt.
- Màu chính: xanh navy, xanh cyan; dùng vàng cho cảnh báo và đỏ cho phanh.
- Chữ màu đen/xám đậm, độ tương phản cao.
- Không dùng nền gradient, hiệu ứng 3D chữ hoặc quá nhiều card.
- Dùng icon nét đơn cho camera, radar, phanh, cảnh báo và ô tô.
- Dùng cùng một quy ước màu trong toàn bộ bài:
  + Xanh lá: an toàn.
  + Xanh dương: theo dõi hoặc cảnh báo sớm.
  + Vàng: nguy cơ.
  + Đỏ: phanh khẩn cấp.
- Ưu tiên sơ đồ vector, bảng so sánh và biểu đồ kỹ thuật.
- Không dùng logo hãng xe nếu không cần thiết.

CẤU TRÚC TỪNG SLIDE

SLIDE 1 - TRANG BÌA

Tiêu đề:
"Nghiên cứu hệ thống ADAS và xây dựng AEB trên CARLA 0.9.11"

Phụ đề:
"Camera, radar, sensor fusion và đánh giá nguy cơ va chạm"

Để chỗ cho:
- Họ tên sinh viên.
- Giảng viên hướng dẫn.
- Lớp và ngày báo cáo.

Hình nền nên là Tesla Model 3 đang chạy trên cao tốc mô phỏng, có camera sau
kính lái và radar trước xe được minh họa bằng lớp phủ kỹ thuật.

SLIDE 2 - BÀI TOÁN VÀ MỤC TIÊU

Trình bày:
- Tai nạn phía trước thường liên quan phản ứng chậm hoặc thiếu quan sát.
- AEB cảnh báo và tự phanh khi va chạm trở nên khó tránh.
- Dự án tập trung car-to-car trên cao tốc.
- Ego vehicle là Tesla Model 3 trong Town04.
- Mục tiêu cuối là camera-radar fusion và điều khiển phanh ổn định.

Dùng sơ đồ: nhận biết -> đánh giá nguy cơ -> cảnh báo -> phanh.

SLIDE 3 - ADAS LÀ GÌ?

Chia ADAS thành bốn nhóm:
- Cảnh báo: FCW, LDW, BSW.
- Can thiệp tránh va chạm: AEB, rear AEB, blind-spot intervention.
- Hỗ trợ điều khiển: ACC, LKA, lane centering.
- Hỗ trợ đỗ xe: camera, siêu âm, automatic parking.

Nhấn mạnh:
- AEB là can thiệp tức thời, không phải xe tự lái.
- Người lái vẫn chịu trách nhiệm giám sát.

Dùng sơ đồ phân nhóm, không dùng đoạn văn.

SLIDE 4 - NGUYÊN LÝ HOẠT ĐỘNG CỦA AEB

Vẽ pipeline ngang:

Sensor
-> hiệu chuẩn và đồng bộ
-> phát hiện vật thể
-> lọc và tracking
-> dự đoán quỹ đạo
-> chọn target
-> đánh giá nguy cơ
-> cảnh báo/phanh

Giải thích ngắn:
- Detection đơn lẻ không nên trực tiếp kích hoạt phanh.
- Target phải nằm trên predicted path.
- Quyết định cần xét độ tin cậy và dữ liệu nhiều frame.

SLIDE 5 - HỆ THỐNG CẢM BIẾN ADAS

Tạo bảng so sánh:

Camera:
- Mạnh về class, làn đường và ngữ cảnh.
- Yếu về depth và điều kiện quang học.

Radar:
- Mạnh về range, Doppler và hoạt động ngày đêm.
- Yếu về phân loại và độ phân giải góc.

LiDAR:
- Hình học 3D chính xác.
- Chi phí và xử lý cao.

Siêu âm:
- Phù hợp vật cản gần và đỗ xe.
- Không phù hợp AEB cao tốc.

IMU/wheel speed:
- Cung cấp ego motion và predicted path.
- Không tự nhìn thấy vật cản.

SLIDE 6 - CAMERA: NGUYÊN LÝ VÀ THÔNG SỐ

Trình bày mô hình pinhole:

u = fx.X/Z + cx
v = fy.Y/Z + cy

Nêu ý nghĩa:
- Intrinsic xác định phép chiếu lên pixel.
- Extrinsic xác định quan hệ giữa camera và thân xe.
- Mono camera không đo trực tiếp chiều sâu.
- Stereo camera dùng disparity: Z = f.B/disparity.

Thông số quan trọng:
- Resolution.
- FOV.
- Frame rate.
- Exposure/HDR.
- Latency và calibration.

Đặt hình minh họa camera nhìn đường và mặt phẳng ảnh.

SLIDE 7 - RADAR: NGUYÊN LÝ VÀ THÔNG SỐ

Trình bày radar FMCW:
- Range từ beat frequency.
- Velocity từ Doppler.
- Angle từ chênh lệch pha giữa anten.

Vẽ chuỗi:

Chirp
-> phản xạ
-> range FFT
-> Doppler FFT
-> angle estimation
-> CFAR
-> clustering/tracking

Nêu nguồn nhiễu:
- Multipath.
- Ground reflection.
- Ghost target.
- Radar interference.
- Stationary infrastructure.

Nhấn mạnh:
Radar CARLA là ray-cast detection-level, không mô phỏng toàn bộ FMCW.

SLIDE 8 - SENSOR FUSION CAMERA VÀ RADAR

Vẽ hai nhánh:

Camera:
class + bounding box + lane context

Radar:
distance + relative velocity + angle

Hợp nhất thành:
fused object track

Track cần có:
- Position.
- Velocity.
- Class.
- Confidence.
- Track age.
- Sensor source.

Giải thích ba mức fusion:
- Late fusion.
- Track-to-track fusion.
- Measurement/feature fusion.

Nhấn mạnh CARLA không tự biết radar point thuộc YOLO box; chương trình phải
calibration, transform và project bằng toán học.

SLIDE 9 - ĐÁNH GIÁ NGUY CƠ

Trình bày ba chỉ số:

TTC = distance / closing_speed

THW = distance / ego_speed

d_required =
v_ego.t_response
+ v_ego²/(2.a_ego)
- v_target²/(2.a_target)
+ safety_margin

Nêu giới hạn:
- TTC không phản ánh toàn bộ khả năng phanh.
- Closing speed gần 0 làm TTC nhạy nhiễu.
- Target ngoài quỹ đạo không phải nguy cơ trực tiếp.

Kết luận:
Nên kết hợp TTC, stopping distance, predicted path và confidence.

SLIDE 10 - STATE MACHINE CẢNH BÁO VÀ PHANH

Vẽ state machine:

NORMAL
-> INFORMATION
-> WARNING
-> BRAKE PREPARE
-> PARTIAL BRAKE
-> EMERGENCY BRAKE
-> HOLD
-> RELEASE

Nêu:
- Hysteresis tránh bật/tắt liên tục.
- Xác nhận nhiều frame giảm nhiễu.
- Có điều kiện driver override.
- Binary brake phù hợp baseline, không phải giải pháp cuối.
- PID/profile deceleration dùng để điều khiển phanh mượt hơn.

SLIDE 11 - CÁC KIẾN TRÚC AEB TRONG THỰC TẾ

Tạo bảng từ đơn giản đến phức tạp:

1. Radar + vehicle dynamics:
Toyota/Honda đời đầu.

2. Một camera:
Mobileye Base ADAS.

3. Stereo camera:
Subaru EyeSight.

4. Multi-camera vision:
Tesla.

5. Camera + radar:
Toyota, Honda, Volvo, Bosch.

6. Camera + radar + LiDAR:
Kiến trúc tự hành cao cấp.

Kết luận:
Nhiều sensor chỉ có giá trị khi calibration, fusion và validation tốt.

SLIDE 12 - BÀI HỌC TỪ AUTOWARE

Trình bày pipeline Autoware AEB:
- Predicted path từ IMU và MPC.
- Lọc point cloud theo swept footprint.
- Clustering, height check và convex hull.
- Chọn vật cản liên quan gần nhất.
- Ước lượng vận tốc qua lịch sử.
- Quyết định bằng braking distance.

Thông số tham khảo:
- AEB 10 Hz.
- IMU horizon 1,5 s.
- MPC horizon 4,5 s.
- Response time 1,0 s.

Ghi chú rõ:
Không sao chép trực tiếp cluster size của LiDAR sang radar CARLA thưa.

SLIDE 13 - BÀI HỌC TỪ CÁC REPO KHÁC

Tạo bảng bốn hàng:

openpilot:
- Ghép vision lead với radar track.
- Kalman filter, delay compensation, sanity gate.

Apollo:
- Tracking riêng từng sensor.
- Probabilistic multi-sensor fusion.
- Prediction nhiều quỹ đạo.

Nav2 Collision Monitor:
- Stop/slowdown/approach zone.
- Trigger và release debounce.

CARLA RSS:
- Tạo giới hạn gia tốc an toàn từ ground truth.
- Chỉ phù hợp làm oracle/baseline, không thay perception.

SLIDE 14 - KIẾN TRÚC DỰ ÁN CARLA

Vẽ sơ đồ:

RGB camera -> YOLO car detection --------\
                                          -> fusion/tracking
Front radar -> filter/cluster/tracking ---/

Ego speed + yaw-rate + steer
-> predicted path/collision corridor

Fusion track + predicted path
-> target selection
-> TTC + stopping distance
-> warning
-> brake controller
-> CARLA VehicleControl

Nêu:
- Ego: Tesla Model 3.
- Map: Town04.
- Bài toán hiện tại: highway car-to-car.

SLIDE 15 - CẤU HÌNH CẢM BIẾN HIỆN TẠI

Tạo bảng:

Camera:
- Vị trí: (0,8; 0; 1,55) m.
- Resolution: 1280 x 720.
- FOV ngang: 70 độ.
- Sensor tick: 0,05 s, tương đương 20 Hz.

Radar:
- Vị trí: (2,35; 0; 0,55) m.
- Range: 100 m.
- FOV ngang: 30 độ.
- FOV dọc: 6 độ.
- 2.000 point/s.
- Sensor tick: 0,05 s.
- Khoảng 100 ray danh định mỗi chu kỳ.

Nhận xét:
- Radar FOV hẹp phù hợp baseline cùng làn.
- Camera/radar 20 Hz vẫn đồng bộ được bằng frame và timestamp.
- Cần synchronous mode cho benchmark có thể lặp lại.

SLIDE 16 - KIỂM THỬ, GIỚI HẠN VÀ LỘ TRÌNH

Chia slide thành ba cột:

Kịch bản:
- CCRs: xe trước đứng yên.
- CCRm: xe trước chạy đều.
- CCRb: xe trước phanh.
- Adjacent lane.
- Curved road.
- Cut-in/cut-out.

Giới hạn:
- Radar CARLA không phải raw FMCW.
- Model camera hiện tập trung class car.
- Fusion tracker chưa hoàn chỉnh.
- Phanh hiện là binary.
- Chưa chứng nhận NCAP.

Lộ trình:
- Hoàn thiện camera-radar association.
- Fused object tracker.
- State machine nhiều tầng.
- PID/profile deceleration.
- Scenario batch và thống kê.

SLIDE 17 - KẾT LUẬN VÀ NGUỒN

Kết luận:
- Radar-only cần predicted path, clustering và tracking.
- Camera bổ sung phân loại và lane context.
- Camera-radar là cấu hình cân bằng cho AEB car-to-car.
- TTC phải kết hợp stopping distance và target relevance.
- Autoware là tham chiếu gần nhất cho AEB decision.
- Mục tiêu của dự án là pipeline giải thích được và đo lường được.

Nguồn chính:
- NHTSA Driver Assistance Technologies và FMVSS 127.
- Euro NCAP 2026 Protocols.
- UNECE Regulation No. 152.
- Autoware Autonomous Emergency Braking.
- openpilot radard.py.
- Apollo multi-sensor fusion.
- CARLA 0.9.11 Sensors Reference.

Kết thúc bằng câu:
"Xin cảm ơn thầy/cô đã lắng nghe."

YÊU CẦU SPEAKER NOTES

Trong speaker notes:
- Giải thích thuật ngữ bằng ví dụ trực quan.
- Chỉ rõ phần nào là nghiên cứu và phần nào đã có trong dự án.
- Với công thức, giải thích ý nghĩa vật lý thay vì chỉ đọc ký hiệu.
- Với kiến trúc hãng, chỉ nói "cách tiếp cận được công khai".
- Với repo, nêu rõ điểm có thể học và điểm không nên sao chép trực tiếp.
- Với thông số CARLA, giải thích đây là cấu hình mô phỏng đang sử dụng.
- Gợi ý câu chuyển tiếp tự nhiên giữa các slide.

Hãy tạo toàn bộ nội dung slide và speaker notes ngay, không chỉ tạo dàn ý.
```

## Prompt Tạo Ảnh

### Ảnh Bìa

```text
Photorealistic engineering visualization of a red Tesla Model 3 driving on a
modern multi-lane highway, viewed from a low front three-quarter angle. A
subtle transparent technical overlay shows one windshield camera field of view
and one front bumper radar cone detecting a vehicle ahead. Clear daytime,
realistic road and vehicles, clean automotive safety research aesthetic,
accurate proportions, wide 16:9 composition, open negative space in the upper
left for a presentation title. No text, no logos, no UI, no gradients, no
futuristic city, no autonomous taxi equipment.
```

### Ảnh Minh Họa Camera Và Radar

```text
Technical automotive sensor visualization, side-front view of a modern sedan
on a highway. Show a transparent blue camera viewing frustum originating
behind the windshield and a cyan radar detection cone originating at the
center of the front bumper. A passenger car is detected directly ahead while
cars in adjacent lanes remain outside the collision corridor. Precise,
realistic, educational engineering style, light neutral background, wide
16:9 composition. No labels, no text, no logos, no decorative effects.
```

### Ảnh Minh Họa Radar FMCW

```text
Clean scientific illustration of an automotive FMCW radar mounted in the
center of a car front bumper. Electromagnetic waves travel toward a vehicle
ahead and reflections return to a receiving antenna array. Show several
parallel antenna elements and subtle wave fronts, realistic scale, dark
components on a white technical background, cyan and red accents only, wide
16:9. No equations, no labels, no text, no science-fiction effects.
```

### Ảnh Minh Họa Sensor Fusion

```text
Automotive perception fusion visualization from the driver's perspective on a
highway. The same lead car is represented by a camera bounding region and a
small set of radar detection points, converging into one stable tracked object
with a projected collision path ahead of the ego vehicle. Clean technical
research aesthetic, realistic road scene, restrained blue, green, yellow and
red safety colors, wide 16:9. No text, no numerical labels, no dashboard UI,
no logos.
```

### Ảnh Kịch Bản AEB

```text
Realistic controlled automotive AEB test on a closed highway test track. A
modern sedan approaches a soft passenger-car target directly ahead in the same
lane. Show visible braking posture and a long clear stopping corridor, with
adjacent lanes empty. Daylight, safety research environment, camera mounted
behind windshield and radar hidden in front bumper, wide 16:9 composition.
No collision, no people, no text, no logos, no dramatic smoke.
```

## Lưu Ý Khi Dùng Ảnh

- Chỉ dùng ảnh AI ở slide bìa hoặc slide chuyển phần.
- Pipeline và state machine phải vẽ bằng shape để đúng logic.
- Không để ảnh AI tự tạo chữ, công thức hoặc bounding box có số liệu.
- Không dùng hình sensor đặt sai vị trí: camera sau kính lái, radar giữa mũi xe.
- Chú thích dưới ảnh: `Hình minh họa, không phải sơ đồ phần cứng của một hãng`.
