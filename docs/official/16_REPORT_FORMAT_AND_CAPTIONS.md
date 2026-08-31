# 16. Hướng Dẫn Cấu Trúc Báo Cáo Và Đặt Tên Hình/Bảng

Tài liệu này dùng để chuẩn hóa bản báo cáo đồ án AEB trước khi chuyển sang file `.docx`. Cấu trúc được rút ra từ báo cáo đồ án kỳ trước của sinh viên và điều chỉnh lại cho phù hợp với đề tài hiện tại: mô phỏng hệ thống AEB trên CARLA 0.9.11.

Mục tiêu chính:

- Giữ báo cáo theo phong cách đồ án kỹ thuật: có chương lớn, mục nhỏ, hình/bảng được đánh số rõ ràng.
- Không viết theo nhật ký làm việc, mà trình bày theo luồng khoa học: tổng quan, lý thuyết, thiết kế, thực nghiệm, kết luận.
- Khi viết Markdown, luôn ghi sẵn tên hình và tên bảng để sau này chuyển sang Word không mất công dò lại.

## 16.1. Cấu Trúc Báo Cáo Cũ Được Tham Khảo

Báo cáo cũ có cấu trúc tổng quát như sau:

1. Trang bìa
2. Lời cảm ơn
3. Tóm tắt nội dung đồ án
4. Mục lục
5. Danh mục hình vẽ
6. Danh mục bảng
7. Chương 1: Tổng quan hệ thống
8. Chương 2: Huấn luyện mô hình AI
9. Chương 3: Xây dựng ứng dụng/phần mềm
10. Chương 4: Triển khai và tích hợp hệ thống
11. Chương 5: Kết luận
12. Tài liệu tham khảo
13. Phụ lục

Điểm nên giữ lại cho báo cáo AEB:

- Có phần tóm tắt trước mục lục.
- Mỗi chương bắt đầu bằng mục tiêu của chương và kết thúc bằng đoạn tổng kết ngắn.
- Hình được ghi theo dạng `Hình x.y: Tên hình`.
- Bảng được ghi theo dạng `Bảng x.y: Tên bảng`.
- Các phần thuật toán cần có công thức, giải thích biến và liên hệ với cách triển khai trong code.

## 16.2. Cấu Trúc Đề Xuất Cho Báo Cáo AEB

Nên gom báo cáo thành 5 chương lớn để mạch đọc gọn hơn, không bị giống danh sách công việc đã làm.

### Phần đầu báo cáo

- Trang bìa
- Lời cảm ơn
- Tóm tắt nội dung đồ án
- Mục lục
- Danh mục hình vẽ
- Danh mục bảng
- Danh mục từ viết tắt, nếu cần

### Chương 1: Tổng Quan Đề Tài Và Bài Toán AEB

Nội dung nên có:

- Lý do chọn đề tài.
- Giới thiệu ADAS và AEB.
- Bài toán AEB trong phạm vi đồ án: cao tốc, chỉ xét ô tô, thời tiết lý tưởng, xe ego Tesla Model 3.
- Mục tiêu đồ án.
- Phạm vi và giới hạn của hệ thống.
- Các hướng tiếp cận trong thực tế và repo tham khảo.

### Chương 2: Thiết Lập Môi Trường Mô Phỏng

Đây là chương làm rõ đồ án được dựng trên môi trường nào, dùng cảm biến nào và
cảm biến được cấu hình ra sao trong CARLA.

Nội dung nên có:

- CARLA 0.9.11, Town04 và lý do chọn môi trường mô phỏng.
- Cấu hình máy, môi trường Python/CARLA.
- Cơ sở lựa chọn cảm biến trong ADAS/AEB: camera, radar, LiDAR, ultrasonic, IMU/wheel speed.
- Cấu hình xe ego Tesla Model 3.
- Cấu hình camera sau kính lái.
- Cấu hình radar ở mũi xe.
- Synchronous mode 20 Hz.
- UI quan sát 3 màn và launcher.

### Chương 3: Triển Khai Thuật Toán AEB

Nội dung nên có:

- Kiến trúc thư mục mã nguồn.
- Kiến trúc thuật toán AEB.
- Nguyên lý radar ô tô ngoài đời và radar trong CARLA.
- Xử lý tín hiệu radar: lọc điểm, gom cụm, theo dõi, tạo object list.
- Tính TTC và khoảng cách dừng.
- Xử lý camera, YOLO, NMS và bounding box.
- Quy trình tạo dataset bằng ground truth CARLA.
- Dataset v7 same-lane.
- Huấn luyện, đánh giá và export YOLO26n ONNX.
- Fusion camera-radar.
- Chọn target, xử lý trùng.
- Logic cảnh báo/phanh nhiều tầng và staged PID.

### Chương 4: Kiểm Thử Và Đánh Giá

Nội dung nên có:

- Các nhóm kịch bản kiểm thử: đường trống, car-to-car đứng yên, xe phía trước chạy chậm, xe cắt làn, nhiều xe gây nhiễu.
- Điều kiện pass/fail.
- Kết quả kiểm thử từng nhóm.
- Log chi tiết và biểu đồ phanh.
- Video minh họa.
- Phân tích các trường hợp fail để xác định giới hạn hoạt động.

### Chương 5: Kết Luận Và Hướng Phát Triển

Nội dung nên có:

- Kết quả đạt được.
- Các hạn chế còn tồn tại.
- Dải hoạt động tốt nhất của hệ thống.
- Hướng phát triển: đồng bộ hóa tốt hơn, PID nâng cao, sensor fusion mạnh hơn, đánh giá theo chuẩn Euro NCAP/ISO, mở rộng thời tiết và loại đối tượng.

### Phần cuối báo cáo

- Tài liệu tham khảo
- Phụ lục A: Lệnh chạy
- Phụ lục B: Bảng scenario đầy đủ
- Phụ lục C: Link video demo
- Phụ lục D: Cấu hình YAML quan trọng

## 16.3. Quy Ước Đặt Caption Trong Markdown

Khi chèn hình, dùng dạng:

```markdown
![Mô tả ngắn](relative/path/to/image.png)

**Hình 3.2: Vị trí camera và radar trên Tesla Model 3 theo góc nhìn cạnh và từ trên xuống.**
```

Khi chèn bảng, dùng dạng:

```markdown
**Bảng 4.3: Điều kiện pass/fail cho các kịch bản kiểm thử AEB.**

| Tiêu chí | Điều kiện pass | Ghi chú |
|---|---|---|
| Va chạm | Không xảy ra collision | Dựa trên log CARLA |
```

Lưu ý:

- Đánh số theo chương: hình ở chương 3 là `Hình 3.1`, `Hình 3.2`, ...
- Không dùng nhiều tên khác nhau cho cùng một hình.
- Mỗi hình/bảng phải được nhắc đến trong nội dung, ví dụ: "Kiến trúc tổng thể được minh họa ở Hình 3.1".
- Nếu sau này chuyển sang Word, có thể đổi các dòng `Hình x.y` và `Bảng x.y` sang style Caption.

## 16.4. Danh Sách Hình Dự Kiến

Danh sách này là khung ban đầu, có thể chỉnh khi viết báo cáo full.

| Mã hình | Tên hình dự kiến | Nguồn |
|---|---|---|
| Hình 1.1 | Minh họa hệ thống AEB trên cao tốc | Tự vẽ hoặc ảnh mô phỏng |
| Hình 1.2 | Các cấp chức năng ADAS liên quan đến AEB | Tự vẽ |
| Hình 2.1 | Nguyên lý hoạt động radar ô tô FMCW | Tự vẽ |
| Hình 2.2 | So sánh radar ngoài đời và radar trong CARLA | Tự vẽ |
| Hình 2.3 | Mô hình tính TTC giữa xe ego và xe mục tiêu | Tự vẽ |
| Hình 2.4 | Mô hình khoảng cách dừng của ego và target | Tự vẽ |
| Hình 2.5 | Pipeline xử lý radar từ raw point đến object list | Từ thiết kế project |
| Hình 2.6 | Pipeline xử lý camera và YOLO | Từ thiết kế project |
| Hình 2.7 | Nguyên lý fusion camera-radar bằng chiếu hình học | Từ thiết kế project |
| Hình 2.8 | Máy trạng thái AEB: Safe, Warning, Soft Brake, Emergency Brake, Release | Tự vẽ |
| Hình 3.1 | Kiến trúc tổng thể hệ thống AEB trong CARLA | Từ code/project |
| Hình 3.2 | Cấu trúc thư mục mã nguồn AEB | Screenshot hoặc sơ đồ |
| Hình 3.3 | Vị trí camera và radar trên Tesla Model 3 | `$AEB_WORKSPACE_ROOT/runs/sensor_coverage` |
| Hình 3.4 | Tầm phủ camera và radar theo góc nhìn từ trên xuống | `$AEB_WORKSPACE_ROOT/runs/sensor_coverage` |
| Hình 3.5 | Giao diện kiểm thử 3 màn của hệ thống | Screenshot UI |
| Hình 3.6 | Launcher dùng để chạy demo, test và quay video | Screenshot launcher |
| Hình 4.1 | Ví dụ dữ liệu phiên bản v7 same-lane cho huấn luyện YOLO26n | Screenshot ảnh preview dataset |
| Hình 4.2 | Ví dụ ảnh dataset có bounding box | `$AEB_WORKSPACE_ROOT/datasets/active/v7_same_lane/previews` |
| Hình 4.3 | Biểu đồ thống kê số ảnh và số nhãn trong dataset | Tạo từ script thống kê |
| Hình 4.4 | Kết quả huấn luyện YOLO26n | `$AEB_WORKSPACE_ROOT/training/.../results.png` |
| Hình 4.5 | Ma trận nhầm lẫn hoặc biểu đồ precision-recall của YOLO | `$AEB_WORKSPACE_ROOT/training/...` |
| Hình 4.6 | Nhóm kịch bản car-to-car đứng yên | Tự vẽ hoặc screenshot |
| Hình 4.7 | Nhóm kịch bản cut-in | Tự vẽ hoặc screenshot |
| Hình 4.8 | Biểu đồ phanh của một case pass | Từ log final |
| Hình 4.9 | Biểu đồ phanh của một case fail/giới hạn | Từ log final |
| Hình 4.10 | Heatmap hoặc bảng màu kết quả system limit sweep | Từ script tổng hợp |

## 16.5. Danh Sách Bảng Dự Kiến

| Mã bảng | Tên bảng dự kiến | Ghi chú |
|---|---|---|
| Bảng 1.1 | Phạm vi và giả thiết của đồ án | Cao tốc, ô tô, thời tiết lý tưởng |
| Bảng 1.2 | Một số repo/hệ thống tham khảo cho AEB/ADAS | Autoware, openpilot, Apollo, CARLA examples |
| Bảng 2.1 | So sánh các cảm biến dùng trong ADAS/AEB | Camera, radar, lidar, ultrasonic |
| Bảng 2.2 | Các tham số chính của radar trong project | Range, FOV, FPS, vị trí lắp |
| Bảng 2.3 | Các tham số chính của camera trong project | Độ phân giải, FOV, FPS, vị trí lắp |
| Bảng 2.4 | Định nghĩa các biến trong công thức TTC và khoảng cách dừng | Dùng khi trình bày thuật toán |
| Bảng 2.5 | So sánh các chế độ phanh | Binary, PID v1, PID v2, staged PID |
| Bảng 3.1 | Cấu hình môi trường thực nghiệm | OS, GPU, Python, CARLA |
| Bảng 3.2 | Các module chính trong mã nguồn | `sensors`, `perception`, `control`, `ui`, `scripts` |
| Bảng 3.3 | Các file cấu hình YAML chính | Sensor, scenario, training |
| Bảng 3.4 | Các trạng thái AEB trong hệ thống | Safe, warning, brake, release |
| Bảng 4.1 | Thống kê dataset v7 same-lane | Train/val/test, số ảnh, số box |
| Bảng 4.2 | Cấu hình huấn luyện YOLO26n | Epoch, imgsz, batch, model |
| Bảng 4.3 | Kết quả đánh giá YOLO26n | Precision, recall, mAP |
| Bảng 4.4 | Nhóm kịch bản kiểm thử AEB | Clear road, CCRs, CCRm, cut-in, multi-actor |
| Bảng 4.5 | Điều kiện pass/fail cho kiểm thử AEB | Collision, stop gap, false brake |
| Bảng 4.6 | Kết quả kiểm thử staged PID theo từng nhóm | Pass/fail/tỉ lệ |
| Bảng 4.7 | Các trường hợp fail và nguyên nhân | Dùng để xác định giới hạn hệ thống |
| Bảng 4.8 | Danh sách video demo và link Drive | Bổ sung sau khi upload |
| Bảng 5.1 | Tổng kết kết quả đạt được, hạn chế và hướng phát triển | Dùng ở chương kết luận |

## 16.6. Các Phần Thuật Toán Cần Viết Kỹ

Khi viết bản full, các phần dưới đây không nên chỉ mô tả bằng lời. Cần có công thức, sơ đồ hoặc pseudo-code.

### Xử lý radar

Cần trình bày:

- Radar CARLA trả về các điểm đo gồm khoảng cách, góc, vận tốc tương đối.
- Các điểm bị nhiễu bởi mặt đường hoặc vật thể bên ngoài hướng di chuyển được lọc bằng vùng quan tâm.
- Các điểm còn lại được gom cụm để tạo object list gần giống đầu ra radar ô tô thực tế.
- Target AEB được chọn theo khoảng cách, vận tốc đóng và vị trí so với đường đi dự kiến.

### Tính TTC

Cần trình bày:

- TTC là thời gian còn lại trước va chạm nếu hai xe giữ nguyên vận tốc tương đối hiện tại.
- Chỉ tính TTC khi khoảng cách đang giảm.
- Nếu vật thể không tiến gần ego thì TTC được xem là vô cùng hoặc không nguy hiểm.

### Khoảng cách dừng

Cần trình bày công thức:

```text
ego_stop_distance =
  ego_speed * response_time
  + ego_speed^2 / (2 * ego_deceleration)

target_stop_distance =
  target_speed^2 / (2 * target_deceleration)

required_distance =
  ego_stop_distance - target_stop_distance + offset
```

Sau công thức cần giải thích từng biến và vì sao công thức này giúp AEB quyết định phanh sớm hơn TTC thuần.

### Camera và YOLO

Cần trình bày:

- YOLO dùng để phát hiện xe trong ảnh camera.
- Dataset được tạo từ CARLA ground truth, sau đó train YOLO26n cho bài toán một class `car`.
- YOLO không trực tiếp đo khoảng cách chính xác như radar, nhưng giúp xác nhận vật thể phía trước có phải xe hay không.

### Fusion camera-radar

Cần trình bày:

- Radar cho khoảng cách và vận tốc tương đối tốt hơn.
- Camera/YOLO cho nhận dạng đối tượng và bounding box.
- Fusion được thực hiện bằng cách chiếu điểm radar sang mặt phẳng ảnh, sau đó ghép với bounding box YOLO.
- Target được xác nhận mạnh hơn nếu vừa có radar object vừa nằm trong vùng box camera.

### Xử lý box trùng và object trùng

Cần trình bày:

- Nếu nhiều box hoặc nhiều cụm radar đại diện cho cùng một xe, hệ thống cần chọn/ghép theo độ gần không gian.
- Với YOLO, các box trùng thường được xử lý bằng NMS.
- Với radar, các cụm gần nhau có thể được hợp nhất hoặc chọn cụm có nguy cơ cao hơn.

### Phanh PID và staged PID

Cần trình bày:

- Binary brake là baseline: thấy nguy hiểm thì phanh mạnh ngay.
- PID tạo lệnh phanh liên tục dựa trên sai lệch giữa khoảng cách hiện tại và khoảng cách an toàn.
- Staged PID gần thực tế hơn vì có nhiều tầng: cảnh báo, phanh nhẹ, phanh mạnh, nhả phanh khi hết nguy hiểm.
- Jerk trong CARLA có thể cao do mô phỏng và cách lấy mẫu, nên chỉ dùng để so sánh tương đối giữa các thuật toán, không nên xem là giá trị tuyệt đối ngoài đời.

## 16.7. Quy Ước Khi Viết Bản Full

- Không cập nhật kết quả thử nghiệm rải rác vào nhiều file chính thức. Kết quả mới nên vào `docs/log/EXPERIMENT_LOG.md`, sau đó chọn lọc đưa vào báo cáo.
- Báo cáo full nên ưu tiên phần thuật toán và phân tích kết quả, không sa đà vào lịch sử chỉnh sửa.
- Các file official hiện tại là nguồn tham khảo chính:
  - `00_PROJECT_INTRODUCTION.md`
  - `01_SYSTEM_ARCHITECTURE.md`
  - `02_SENSOR_CONFIGURATION.md`
  - `03_RADAR_PROCESSING.md`
  - `04_CAMERA_YOLO_PROCESSING.md`
  - `05_CAMERA_RADAR_FUSION.md`
  - `06_AEB_DECISION_AND_BRAKING.md`
  - `07_SCENARIOS_AND_VALIDATION.md`
  - `08_DATASET_AND_TRAINING.md`
  - `11_ENVIRONMENT_AND_INSTALLATION.md`
- Khi có hình/video/log mới, cập nhật danh sách hình/bảng trong tài liệu này hoặc đưa trực tiếp vào chương tương ứng trong `report/chapters_v3/`.
