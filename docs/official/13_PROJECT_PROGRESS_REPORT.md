# 13. Báo Cáo Tiến Độ Dự Án

Tài liệu này dùng để theo dõi tiến độ tổng thể của dự án AEB trên CARLA. Khác
với các file kỹ thuật chi tiết, file này tập trung trả lời bốn câu hỏi:

- Dự án đang làm gì?
- Đã nghiên cứu những hướng nào?
- Pipeline dự kiến và pipeline hiện tại khác nhau ra sao?
- Đã làm, đang làm và sẽ làm những phần nào?

## 1. Giới Thiệu Dự Án

Dự án xây dựng hệ thống phanh khẩn cấp tự động AEB mô phỏng trên CARLA 0.9.11.
Ego vehicle là `vehicle.tesla.model3`, chạy chủ yếu trên môi trường cao tốc
`Town04`. Bài toán chính là car-to-car AEB: xe ego phát hiện nguy cơ va chạm với
ô tô phía trước, cảnh báo và phanh khẩn cấp nếu cần.

Hệ thống dự kiến dùng hai cảm biến phía trước:

- Camera RGB đặt sau kính lái.
- Radar đặt tại mũi xe.

Lộ trình phát triển là làm radar-only AEB ổn định trước, sau đó thêm camera
YOLO, sensor fusion camera-radar và điều khiển phanh mượt hơn bằng PID hoặc
brake profile.

## 2. Mục Tiêu Kỹ Thuật

- Cấu hình xe ego Tesla Model 3 và cảm biến trong CARLA.
- Xây dựng giao diện kiểm thử trực quan dựa trên `manual_control.py`.
- Xây dựng radar-only AEB baseline ở dải 50-80 km/h.
- Tạo scenario kiểm thử car-to-car và ghi log/evidence.
- Thu dataset camera từ CARLA ground truth.
- Train YOLO một class `car` cho môi trường mô phỏng.
- Xây dựng fusion camera-radar để xác nhận target nguy hiểm.
- So sánh radar-only, fusion AEB và điều khiển phanh PID.

## 3. Research Đã Nghiên Cứu

### 3.1. ADAS Và AEB

Đã nghiên cứu tổng quan ADAS và vị trí của AEB trong ADAS. Các chức năng liên
quan gồm Forward Collision Warning, Adaptive Cruise Control, Lane Keeping Assist
và Autonomous Emergency Braking.

Với AEB, các khối quan trọng là:

- Nhận biết vật thể phía trước.
- Ước lượng khoảng cách và vận tốc tương đối.
- Chọn target nguy hiểm.
- Tính TTC.
- Tính khoảng cách dừng.
- Cảnh báo.
- Can thiệp phanh khi nguy cơ đủ cao.

### 3.2. Cảm Biến Thực Tế

Đã nghiên cứu các loại cảm biến thường dùng trong ADAS:

- Radar trước xe: đo khoảng cách và vận tốc tương đối tốt, ít phụ thuộc ánh sáng.
- Camera trước: nhận dạng class, lane, biển báo và ngữ cảnh.
- Lidar: tạo point cloud dày, thường dùng trong hệ tự hành nghiên cứu/cao cấp.
- Ultrasonic: tầm gần, thường dùng cho đỗ xe.
- IMU/GNSS/CAN: cung cấp trạng thái ego như vận tốc, yaw rate, gia tốc.

Nhận xét chính: radar và camera bổ sung cho nhau. Radar mạnh ở đo động học, camera
mạnh ở phân loại và ngữ cảnh. Vì vậy sensor fusion là hướng phù hợp cho AEB.

### 3.3. CARLA Radar So Với Radar Thực Tế

CARLA radar trả về các detection point gồm khoảng cách/góc/vận tốc tương đối.
Radar thực tế có pipeline xử lý tín hiệu phức tạp hơn như FMCW, Doppler, CFAR,
clustering và tracking. Vì vậy trong dự án này không nên phanh trực tiếp từ một
radar point đơn lẻ. Cần tạo tầng object-level trung gian:

```text
radar detections -> filtering -> clustering -> tracking -> object list
```

Đây là hướng hiện tại của radar-only AEB.

### 3.4. Repo Và Hệ Thống Tham Khảo

Đã tham khảo các hướng kiến trúc từ Autoware, openpilot và Apollo:

- Autoware: predicted path, obstacle on path, stopping distance.
- openpilot: radar track kết hợp lead từ vision.
- Apollo: perception/fusion ở object-level trước khi decision/control.

Bài học áp dụng cho project:

- Không quyết định phanh từ point đơn lẻ.
- Chỉ xét object nằm trong hành lang nguy hiểm phía trước ego.
- Dùng tracking/confirmation qua nhiều frame để giảm nhiễu.
- Chuẩn hóa dữ liệu thành `RadarObject` hoặc `FusedTarget` trước khi AEB decision.
- Tách rõ perception, target selection, risk estimation và brake control.

## 4. Pipeline Dự Kiến

Pipeline hoàn chỉnh dự kiến của dự án:

```text
CARLA World
  -> Ego Tesla Model 3
  -> Camera + Radar

Camera branch:
  -> RGB image
  -> YOLO car detection
  -> bounding boxes + confidence

Radar branch:
  -> radar detections
  -> filtering
  -> clustering/tracking
  -> object list: distance, lateral, relative velocity

Fusion branch:
  -> project radar object to image
  -> match radar object with YOLO bbox
  -> fused target

AEB branch:
  -> target selection
  -> TTC
  -> stopping distance
  -> warning/brake state
  -> brake override/PID
  -> log final gap
```

## 5. Pipeline Hiện Tại

Pipeline đang chạy ổn nhất là radar-only:

```text
CARLA RadarMeasurement
  -> radar point trong hệ ego
  -> lọc range/độ cao/mặt đường
  -> clustering theo vị trí và vận tốc
  -> tracking qua nhiều frame
  -> RadarObjectList
  -> chọn target trong predicted path corridor
  -> tính TTC + stopping distance
  -> AEB state machine
  -> VehicleControl brake override
  -> stop latch để đo final gap
```

Camera, YOLO và fusion đã có app debug/khung xử lý, nhưng chưa phải nhánh quyết
định phanh chính.

## 6. Thuật Toán Đã Làm

### 6.1. Radar Processing

- Đọc raw radar detection từ CARLA.
- Đổi dữ liệu radar sang hệ tọa độ ego.
- Lọc điểm theo range, độ cao và vùng quan tâm.
- Gom cụm radar point thành object.
- Tracking object qua nhiều frame.
- Yêu cầu object được xác nhận trước khi dùng cho AEB.

### 6.2. Target Selection

- Không xét toàn bộ quạt radar như nguy cơ trực tiếp.
- Sinh predicted path/corridor theo hướng xe ego.
- Chỉ chọn object nằm trong hành lang nguy hiểm.
- Ưu tiên object gần, đang closing và có TTC/khoảng cách dừng nguy hiểm.

### 6.3. AEB Decision

- Tính TTC từ khoảng cách và vận tốc tương đối.
- Tính stopping distance dựa trên vận tốc ego và giả thiết giảm tốc.
- State machine gồm `NORMAL`, `WARNING`, `BRAKE`, `RELEASE`.
- Có hysteresis/release threshold để giảm nhấp nhả.
- Không phanh khi xe đang lùi.

### 6.4. Brake Control Hiện Tại

- Giai đoạn hiện tại dùng binary brake: phanh 0 hoặc full brake.
- Khi live scenario đã vào `BRAKE`, ego được latch dừng để đo khoảng cách cuối.
- Terminal/UI hiển thị final gap phục vụ đánh giá thủ công.

## 7. Thuật Toán Dự Kiến Làm Tiếp

- YOLO detector một class `car` train bằng dữ liệu CARLA.
- Fusion radar-camera bằng cách project radar object lên ảnh camera.
- Xác nhận target radar bằng bounding box camera.
- Tạo `FusedTarget` gồm class, distance, relative velocity và confidence.
- PID hoặc brake profile để phanh mượt hơn binary brake.
- Biểu đồ tốc độ, khoảng cách, TTC, brake command theo thời gian.

## 8. Tiến Độ Theo Module

### 8.1. Môi Trường Và Cấu Trúc Project

- [x] Tạo project `aeb/` riêng trong thư mục CARLA.
- [x] Đổi bản cũ thành `aeb_old2`.
- [x] Refactor code theo `ui/`, `scripts/`, `core/`, `perception/`, `control/`.
- [x] Tạo tài liệu cài đặt môi trường và cách đặt folder `aeb/`.
- [ ] Dọn các file tạm và chuẩn hóa toàn bộ command cuối cùng.

### 8.2. Cảm Biến

- [x] Chọn ego vehicle là Tesla Model 3.
- [x] Cấu hình camera sau kính lái.
- [x] Cấu hình radar ở mũi xe.
- [x] Viết script visualize sensor coverage.
- [x] Kiểm tra sensor bằng top-down và side view.
- [ ] Chốt thông số sensor cuối cùng cho báo cáo.

### 8.3. Radar-Only AEB

- [x] Hiển thị radar bird-eye view.
- [x] Hiển thị toàn bộ radar points để debug.
- [x] Chuyển từ point-level sang object-level.
- [x] Clustering và tracking radar object.
- [x] Predicted path/corridor.
- [x] TTC và stopping distance.
- [x] AEB warning/brake state.
- [x] Brake override trong CARLA.
- [x] Stop latch sau khi AEB phanh.
- [ ] Chạy validation đầy đủ ở 50-80 km/h.
- [ ] Chốt threshold radar-only.

### 8.4. Camera Và YOLO

- [x] Tạo camera debug view.
- [x] Tạo YOLO/model debug view.
- [x] Có cấu hình training pipeline.
- [ ] Thu dataset CARLA ground truth.
- [ ] Audit label và chia train/val/test.
- [ ] Train YOLO một class `car`.
- [ ] Export ONNX/CUDA.
- [ ] Test model mới trong CARLA.

### 8.5. Fusion

- [x] Tạo fusion debug view.
- [x] Có logic project radar lên ảnh camera ở mức debug.
- [ ] Match radar object với YOLO bbox ổn định.
- [ ] Tạo fused target chính thức.
- [ ] Dùng fusion target cho AEB decision.
- [ ] So sánh radar-only và fusion AEB.

### 8.6. Brake Control

- [x] Binary full brake.
- [x] Hold brake until stopped trong logic AEB.
- [x] Stop latch trong live scenario.
- [ ] Thiết kế PID brake.
- [ ] Tune PID theo final gap/độ mượt.
- [ ] So sánh binary brake và PID brake.

### 8.7. Test Và Evidence

- [x] Unit test logic hiện tại: `28/28 PASS`.
- [x] Smoke test radar-only sau refactor.
- [x] Live scenario `ccrs_60_demo_150`.
- [x] Final gap in ra terminal/UI.
- [ ] Batch validation đầy đủ.
- [ ] Lưu log, ảnh, video từng scenario.
- [ ] Bảng tổng hợp PASS/FAIL.
- [ ] Biểu đồ kết quả cho báo cáo.

## 9. Đã Làm, Đang Làm, Sẽ Làm

### Đã Làm

- Dựng project AEB trên CARLA 0.9.11.
- Cấu hình Tesla Model 3, camera và radar.
- Tạo các app debug camera/radar/model/fusion/AEB.
- Xây dựng radar-only AEB object-level.
- Tạo live scenario có target, ego chạy tốc độ mục tiêu và AEB can thiệp.
- Sửa các lỗi lớn: target spawn lệch, phanh nhấp nhả, lag đầu scenario.
- Viết bộ tài liệu official/research/log.

### Đang Làm

- Chạy thử thủ công radar-only trên các scenario chính.
- Tinh chỉnh trải nghiệm live scenario để quan sát và ghi evidence.
- Chuẩn bị chốt radar-only baseline ở dải 50-80 km/h.

### Sẽ Làm

- Chạy batch validation đầy đủ cho radar-only.
- Thu dataset camera từ CARLA ground truth.
- Train YOLO một class `car`.
- Hoàn thiện camera-radar fusion.
- Làm PID/brake profile.
- Tổng hợp kết quả và viết báo cáo cuối kỳ.

## 10. Kết Quả Hiện Tại

Kết quả kỹ thuật đã xác nhận:

- Unit test logic: `28/28 PASS`.
- Radar-only smoke test sau refactor chạy được.
- Live scenario đã spawn đúng target cùng làn.
- Ego có thể chạy đều ở vận tốc mục tiêu trước khi AEB can thiệp.
- Khi AEB phanh, ego dừng hẳn và giữ phanh để đo final gap.
- Warm-up live scenario giúp tách lag setup khỏi pha chạy/đánh giá.

Các kết quả này là bằng chứng nội bộ cho tiến độ dự án, chưa phải chứng nhận
NCAP hay đánh giá an toàn chính thức.

## 11. Việc Ưu Tiên Ngắn Hạn

1. Chạy `ccrs_60_demo_150` và ghi lại video/final gap.
2. Chạy nhóm clear road để kiểm tra false positive.
3. Chạy nhóm adjacent lane để kiểm tra phanh nhầm.
4. Chạy CCRs/CCRm/CCRb ở 50-80 km/h.
5. Lưu bảng kết quả radar-only baseline.
6. Sau khi radar-only ổn, chuyển sang thu dataset camera.

## 12. Quy Ước Cập Nhật Tiến Độ

- File này dùng để tick tiến độ tổng thể.
- Mỗi thay đổi kỹ thuật quan trọng ghi thêm vào `docs/log/EXPERIMENT_LOG.md`.
- Các file `docs/official/03...06...` chỉ nên cập nhật khi đã chốt hướng kỹ
  thuật, không ghi kiểu nhật ký.
- Các tài liệu research nằm trong `docs/research/` để giải thích nguồn tham khảo,
  repo ngoài và khác biệt giữa project với hệ thống thực tế.
