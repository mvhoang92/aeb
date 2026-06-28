# 14. Script Tạo Slide Báo Cáo Tiến Độ

File này là prompt/script để đưa cho một AI khác tạo slide báo cáo tiến độ dự án
AEB trên CARLA. Mục tiêu là tạo một bộ slide rõ ràng, khoa học, dễ trình bày
trước giảng viên. Không cần đi quá sâu vào code, nhưng phải thể hiện được dự án
đã nghiên cứu gì, đã làm gì, đang làm gì và sẽ làm gì.

## Prompt Chính

Bạn là một chuyên gia thiết kế slide kỹ thuật và hỗ trợ viết báo cáo nghiên cứu
về ADAS/AEB. Hãy tạo một bộ slide báo cáo tiến độ cho dự án:

**"Xây dựng hệ thống phanh khẩn cấp tự động AEB trên CARLA 0.9.11"**

Yêu cầu chung:

- Ngôn ngữ: tiếng Việt có dấu.
- Số slide: khoảng 12-14 slide.
- Phong cách: kỹ thuật, rõ ràng, hiện đại, phù hợp báo cáo đại học.
- Không làm slide quá nhiều chữ.
- Mỗi slide có tiêu đề ngắn, 3-5 ý chính.
- Có thể thêm speaker notes ngắn cho từng slide.
- Ưu tiên sơ đồ pipeline, bảng tiến độ, hình minh họa cảm biến, hình minh họa
  AEB hơn là đoạn văn dài.
- Không bịa kết quả chưa có. Những phần chưa hoàn thành phải ghi là "dự kiến"
  hoặc "đang thực hiện".
- Dùng thuật ngữ nhất quán: ADAS, AEB, TTC, stopping distance, radar-only,
  YOLO, sensor fusion, CARLA.

Thông tin dự án:

- Môi trường mô phỏng: CARLA 0.9.11.
- Xe ego: Tesla Model 3 (`vehicle.tesla.model3`).
- Map chính: Town04, môi trường cao tốc.
- Bài toán chính: car-to-car AEB.
- Cảm biến:
  - Camera RGB đặt sau kính lái.
  - Radar đặt tại mũi xe.
- Dải vận tốc mục tiêu hiện tại: 50-80 km/h.
- Radar range hiện tại: 100 m.
- Nhánh ưu tiên hiện tại: radar-only AEB.
- Nhánh dự kiến: camera YOLO, camera-radar fusion, PID brake.

## Nội Dung Slide Đề Xuất

### Slide 1 - Tiêu Đề

Tiêu đề:

**Báo Cáo Tiến Độ Dự Án AEB Trên CARLA**

Nội dung:

- Mô phỏng hệ thống phanh khẩn cấp tự động.
- Ego vehicle: Tesla Model 3.
- Cảm biến: camera trước + radar trước.
- Trọng tâm hiện tại: radar-only AEB baseline.

Gợi ý hình:

- Ảnh hoặc render xe Tesla Model 3 trong CARLA trên đường cao tốc.
- Có overlay vùng quét radar/camera phía trước.

Speaker notes:

> Dự án hướng tới xây dựng một pipeline AEB có thể giải thích, kiểm thử và mở
> rộng trong CARLA. Giai đoạn hiện tại tập trung làm radar-only thật ổn định
> trước khi chuyển sang camera và fusion.

### Slide 2 - Bối Cảnh Và Động Lực

Nội dung:

- ADAS là nhóm công nghệ hỗ trợ lái an toàn trên ô tô hiện đại.
- AEB giúp cảnh báo và phanh tự động khi có nguy cơ va chạm phía trước.
- Thử nghiệm AEB thật tốn kém và nguy hiểm.
- CARLA giúp mô phỏng, kiểm thử và ghi log trong môi trường kiểm soát được.

Gợi ý hình:

- Sơ đồ một xe ego đang tiến tới xe phía trước, có vùng cảnh báo/phanh.

Speaker notes:

> AEB là một chức năng an toàn chủ động quan trọng. Với CARLA, ta có thể tạo các
> tình huống nguy hiểm lặp lại nhiều lần mà không cần thử trên xe thật.

### Slide 3 - Mục Tiêu Dự Án

Nội dung:

- Xây dựng AEB mô phỏng trên CARLA 0.9.11.
- Cấu hình Tesla Model 3 với camera và radar phía trước.
- Làm radar-only AEB baseline ở dải 50-80 km/h.
- Thu dataset và train YOLO nhận diện xe.
- Phát triển sensor fusion và phanh PID ở giai đoạn sau.

Gợi ý trình bày:

- Dùng checklist 5 mục.

Speaker notes:

> Mục tiêu không phải chứng nhận NCAP chính thức, mà là xây dựng pipeline nghiên
> cứu rõ ràng: từ cảm biến, nhận thức, chọn target, đánh giá nguy cơ đến điều
> khiển phanh.

### Slide 4 - Hệ Thống Và Công Cụ

Nội dung:

- Simulator: CARLA 0.9.11.
- Ngôn ngữ: Python 3.7.
- UI dựa trên `manual_control.py`.
- Cấu trúc project gồm `configs/`, `ui/`, `core/`, `perception/`, `control/`,
  `scripts/`, `docs/`.
- Có unit test cho logic xử lý: hiện tại `28/28 PASS`.

Gợi ý hình:

- Sơ đồ folder/module đơn giản.

Speaker notes:

> Project được tách module để sau này dễ mở rộng: UI chỉ để quan sát, core xử lý
> pipeline, perception xử lý radar/camera, control xử lý phanh.

### Slide 5 - Cấu Hình Cảm Biến

Nội dung:

- Camera RGB đặt sau kính lái, nhìn về phía trước.
- Radar đặt tại mũi xe.
- Radar hiện tại: range 100 m, HFOV 30 độ, VFOV 6 độ.
- Đã có script visualize sensor coverage để kiểm tra vị trí và vùng phủ.

Gợi ý hình:

- Hình top-down xe với vùng quét radar và camera.
- Hình side-view cho thấy camera sau kính lái và radar ở mũi xe.

Speaker notes:

> Việc đặt sensor được kiểm chứng bằng hình chiếu cạnh và top-down. Điều này
> quan trọng vì nếu sensor lệch, radar/camera sẽ tạo dữ liệu sai so với giả định
> thuật toán.

### Slide 6 - Research Đã Tham Khảo

Nội dung:

- ADAS/AEB: warning, TTC, stopping distance, emergency braking.
- Radar thực tế: FMCW, Doppler, clustering, tracking, object list.
- CARLA radar: trả về detection point, cần tự xử lý lên object-level.
- Repo tham khảo:
  - Autoware: predicted path, obstacle checking, stopping distance.
  - openpilot: radar track + vision lead.
  - Apollo: object-level perception/fusion trước decision.

Gợi ý trình bày:

- Bảng 3 cột: Nguồn tham khảo, Ý tưởng chính, Cách áp dụng vào project.

Speaker notes:

> Bài học quan trọng là không nên phanh trực tiếp từ một radar point đơn lẻ.
> Project chuyển sang object-level: clustering, tracking, chọn target trong hành
> lang dự đoán rồi mới tính nguy cơ.

### Slide 7 - Pipeline Dự Kiến Hoàn Chỉnh

Nội dung:

```text
CARLA World
  -> Tesla Model 3 + Camera + Radar
  -> Camera branch: RGB -> YOLO -> bounding boxes
  -> Radar branch: detections -> filtering -> clustering/tracking -> object list
  -> Fusion: match radar object với YOLO bbox -> fused target
  -> AEB: target selection -> TTC/stopping distance -> warning/brake
  -> Brake control: binary brake -> PID/brake profile
```

Gợi ý hình:

- Sơ đồ pipeline ngang từ trái sang phải.
- Dùng màu khác nhau cho camera, radar, fusion, AEB, brake.

Speaker notes:

> Đây là hướng hoàn chỉnh của dự án. Radar cung cấp động học, camera cung cấp
> nhận dạng, fusion tạo target đáng tin cậy hơn cho AEB.

### Slide 8 - Pipeline Hiện Tại: Radar-Only AEB

Nội dung:

```text
CARLA RadarMeasurement
  -> radar points trong hệ ego
  -> lọc range/độ cao/mặt đường
  -> clustering theo vị trí và vận tốc
  -> tracking qua nhiều frame
  -> RadarObjectList
  -> chọn target trong predicted corridor
  -> TTC + stopping distance
  -> AEB state machine
  -> brake override + stop latch
```

Gợi ý hình:

- Sơ đồ radar-only pipeline.
- Có thể minh họa bird-eye view: quạt radar, object target, hành lang nguy hiểm.

Speaker notes:

> Pipeline hiện tại đã đi từ radar point lên object list. Đây là bước quan trọng
> để giảm phanh nhầm do điểm nhiễu, mặt đường hoặc vật ngoài làn.

### Slide 9 - Thuật Toán AEB Hiện Tại

Nội dung:

- Target selection:
  - object ở phía trước xe.
  - nằm trong predicted path corridor.
  - có vận tốc tương đối nguy hiểm.
- Risk estimation:
  - TTC.
  - stopping distance.
- State machine:
  - NORMAL.
  - WARNING.
  - BRAKE.
  - RELEASE.
- Live scenario có stop latch để đo final gap.

Gợi ý hình:

- State machine 4 trạng thái.
- Công thức TTC đơn giản:

```text
TTC = distance / closing_speed
```

Speaker notes:

> TTC cho biết còn bao lâu sẽ va chạm nếu vận tốc tương đối giữ nguyên. Stopping
> distance bổ sung góc nhìn vật lý: với vận tốc hiện tại, xe cần bao xa để dừng.

### Slide 10 - Giao Diện Và Scenario Kiểm Thử

Nội dung:

- UI 2 panel:
  - bên trái: manual_control/CARLA view.
  - bên phải: radar bird-eye, target, TTC, brake state.
- Scenario chính:
  - clear road.
  - CCRs: xe trước đứng yên.
  - CCRm: xe trước chạy chậm.
  - CCRb: xe trước phanh gấp.
  - adjacent lane.
  - curve/cut-in/cut-out.
- Demo hiện tại: `ccrs_60_demo_150`.

Gợi ý hình:

- Screenshot UI radar-only nếu có.
- Nếu chưa có ảnh, dùng mock diagram: xe ego, target, bird-eye radar.

Speaker notes:

> Scenario live giúp quan sát trực tiếp. Batch runner dùng để log khách quan và
> tổng hợp PASS/FAIL.

### Slide 11 - Tiến Độ Đã Hoàn Thành

Nội dung dạng checklist:

- [x] Tạo project AEB riêng và refactor cấu trúc.
- [x] Cấu hình Tesla Model 3, camera, radar.
- [x] Tạo các màn test camera/radar/model/fusion.
- [x] Xây dựng radar-only AEB.
- [x] Clustering/tracking radar object.
- [x] Predicted corridor, TTC, stopping distance.
- [x] Live scenario, stop latch, final gap.
- [x] Unit test logic: `28/28 PASS`.

Gợi ý trình bày:

- Bảng "Đã làm" với icon check.

Speaker notes:

> Phần đã hoàn thành quan trọng nhất là radar-only baseline: xe ego có thể chạy
> đều, gặp target nguy hiểm thì AEB can thiệp phanh và dừng để đo khoảng cách
> cuối.

### Slide 12 - Vấn Đề Đã Gặp Và Cách Xử Lý

Nội dung:

| Vấn đề | Nguyên nhân | Cách xử lý |
|---|---|---|
| Radar phanh nhầm | point mặt đường/vật ngoài làn | lọc ground, corridor, clustering |
| Target spawn sai | CARLA chưa sync frame sau reset ego | sync frame sau reset/spawn |
| Phanh nhấp nhả | controller đạp ga lại sau khi AEB nhả | stop latch |
| Lag đầu scenario | spawn actor, respawn camera, sync frame | warm-up, giảm debug draw |

Speaker notes:

> Các lỗi này giúp định hình pipeline hiện tại. Đặc biệt, phanh từ point đơn lẻ
> là không ổn, cần object-level và hành lang dự đoán.

### Slide 13 - Đang Làm Và Kế Hoạch Tiếp Theo

Nội dung:

Đang làm:

- Chạy radar-only thủ công từng scenario.
- Tinh chỉnh threshold ở 50-80 km/h.
- Ghi log/video/screenshot cho báo cáo.

Sẽ làm:

- Thu dataset camera từ CARLA ground truth.
- Train YOLO một class `car`.
- Test YOLO trong CARLA.
- Làm camera-radar fusion.
- Làm PID/brake profile.
- So sánh radar-only, fusion và PID.

Gợi ý trình bày:

- Roadmap 3 giai đoạn:
  1. Radar-only baseline.
  2. YOLO + fusion.
  3. PID + đánh giá tổng hợp.

Speaker notes:

> Lộ trình hiện tại là chốt radar-only trước. Khi baseline ổn định, camera và
> fusion sẽ được thêm để giảm phanh nhầm và tăng độ tin cậy.

### Slide 14 - Kết Luận Tạm Thời

Nội dung:

- Dự án đã có nền tảng mô phỏng AEB hoàn chỉnh trên CARLA.
- Radar-only pipeline đã chuyển từ point-level sang object-level.
- Các lỗi quan trọng trong live scenario đã được xử lý.
- Hướng tiếp theo là đánh giá radar-only có hệ thống, sau đó mở rộng sang YOLO,
  fusion và PID brake.

Speaker notes:

> Kết luận tạm thời là dự án đang đi đúng hướng. Phần radar-only đã đủ để làm
> baseline nghiên cứu; các phần tiếp theo sẽ giúp hệ thống gần với AEB thực tế
> hơn.

## Prompt Tạo Hình Minh Họa

Nếu cần tạo ảnh minh họa bằng AI image generator, dùng các prompt sau.

### Ảnh 1 - Hero Slide

```text
Technical presentation illustration of an autonomous emergency braking simulation
in CARLA, Tesla Model 3 ego vehicle on a clean highway, front radar cone and
windshield camera field of view overlay, another vehicle ahead, realistic but
clean academic style, 16:9, no text, no logos.
```

### Ảnh 2 - Sensor Coverage

```text
Top-down technical diagram of a Tesla Model 3 with a front radar cone and a
windshield camera field of view, radar in red, camera in cyan, clean engineering
visual style, white or dark neutral background, 16:9, no text.
```

### Ảnh 3 - Radar-Only Pipeline

```text
Clean technical diagram showing radar detections becoming clusters, tracked
objects, target selection corridor, TTC estimation and emergency braking,
minimal engineering infographic style, 16:9, no text.
```

### Ảnh 4 - AEB Scenario

```text
Autonomous emergency braking test scenario on a highway: ego car approaching a
stationary lead car, bird-eye inset showing radar fan, target object, TTC warning
zone, professional simulation report style, 16:9, no text.
```

## Quy Tắc Thiết Kế Slide

- Mỗi slide chỉ nên có một thông điệp chính.
- Không copy nguyên code vào slide.
- Công thức chỉ đưa TTC và stopping distance ở mức dễ hiểu.
- Các phần chưa làm phải dùng màu/xưng hô là "dự kiến", không trình bày như kết
  quả đã hoàn thành.
- Nếu có bảng tiến độ, dùng 3 trạng thái:
  - Hoàn thành.
  - Đang làm.
  - Dự kiến.
- Nên dùng các màu nhất quán:
  - Radar: đỏ/cam.
  - Camera: xanh cyan.
  - Fusion: tím hoặc xanh lá.
  - Brake/AEB: đỏ.
  - Completed: xanh lá.
  - In progress: vàng.
  - Planned: xám.

## Nội Dung Cần Nhấn Mạnh Khi Trình Bày

- Project không chỉ là chạy CARLA, mà là xây dựng pipeline AEB có cấu trúc.
- Radar-only là baseline, không phải đích cuối.
- Việc chuyển từ radar point sang object list là quyết định kỹ thuật quan trọng.
- Tham khảo Autoware/openpilot/Apollo giúp project gần với tư duy hệ tự hành hơn.
- Các lỗi đã gặp như phanh nhầm, spawn sai, nhấp nhả phanh đều đã được xử lý có
  cơ sở.
- Tiến độ tiếp theo rõ ràng: radar-only validation -> dataset -> YOLO -> fusion
  -> PID -> báo cáo cuối.
