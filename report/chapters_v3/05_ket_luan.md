# Chương 5. Kết Luận Và Hướng Phát Triển

## 5.1. Kết Quả Đạt Được

Đồ án đã xây dựng pipeline AEB mô phỏng từ sensor đến brake gồm radar object
processing, YOLO26n, camera-radar projection, predicted-path target selection,
TTC/stopping-distance risk và staged PID. Bản v3 bổ sung radar emergency
fallback, master campaign có checkpoint/resume, CUDA provider verification,
CARLA process isolation và bộ evidence tái lập.

Ba chính sách được đánh giá trên cùng scenario definitions:

1. radar-only;
2. hard camera gate;
3. camera gate có radar emergency fallback.

**Bảng 5.1: Kết quả chính của final GPU core benchmark.**

| Chính sách | Core PASS/555 | Precision* | Recall* | Collision* |
|---|---:|---:|---:|---:|
| Radar-only | 465 | 0,913 | 0,988 | 15 |
| Hard camera gate | 525 | 1,000 | 0,965 | 25 |
| Safe fallback | 535 | 1,000 | 0,988 | 15 |

\* Precision/recall/collision dùng 525 core runs không tính synthetic fault;
PASS/555 bao gồm cả 30 labelled synthetic faults.

Trên core suite, safe fallback đạt mục tiêu thiết kế: phục hồi non-vehicle core
recall của radar-only và giữ false-brake suppression của hard gate. Ablation cho
thấy central-path constraint, minimum point threshold và latch đều có tác động
quan sát được. Perturbation và camera degradation cho thấy fallback cải thiện
nhưng không loại bỏ mọi collision.

Đóng góp quan trọng nhất không phải một con số F1 duy nhất, mà là chuỗi evidence
có thể truy nguyên: protocol khóa trước hold-out, 2.461 runs, 639 server
sessions, config/model hash, tick logs, run-level/scenario-level summaries,
ablation, sensitivity, degradation, hold-out và artifact SHA-256.

## 5.2. Trả Lời Câu Hỏi Nghiên Cứu

- **RQ1:** Radar-only có recall cao nhưng phanh nhầm edge props; hard gate tăng
  precision lên 1,000 trên core benchmark nhưng bỏ 10/10 non-vehicle in-path và
  tăng collision từ 15 lên 25.
- **RQ2:** Emergency fallback phục hồi 10/10 core non-vehicle runs, giảm
  collision core về 15 và không tạo FP trên weak four-point synthetic suite.
- **RQ3:** Lợi ích chỉ giữ một phần ngoài core. Safe fallback đạt 54/60
  perturbation và 24/30 camera-off runs, nhưng frozen hold-out chỉ 35/70.
- **RQ4:** Central-path, point threshold và latch có ablation effect rõ.
  Stability/risk-conjunction không phân biệt trên focused suite; sensitivity
  chỉ ra việc nới point threshold hoặc siết TTC/stability đều đổi outcome.

Kết quả vì vậy ủng hộ một nhận định có điều kiện: radar emergency fallback có
thể dịch chuyển trade-off precision/recall thuận lợi trên suite đã biết, nhưng
không tạo ra dominance tổng quát.

## 5.3. Hạn Chế Và Threats To Validity

**Bảng 5.2: Hạn chế quan trọng sau frozen hold-out.**

| Hạn chế | Bằng chứng | Hệ quả |
|---|---|---|
| High-support radar ghost | Safe fallback FP 20/25 ghost hold-out | Rule-based quality/risk không chứng minh vật thể là thật |
| Physical prop detectability | Cả ba chính sách collision 15/15 props mới | Radar track có thể không hình thành hoặc hình thành quá muộn |
| Camera mất hoàn toàn | Safe fallback collision 6/18 positive camera-off runs | Emergency override có thể quá muộn so với normal camera confirmation |
| Local perturbation | Safe fallback fail box gap 19/21 m nhưng đạt 20 m | Physical radar geometry có biên không đơn điệu |
| Một map/ego và synthetic imagery | Town04, Tesla Model 3, YOLO cùng miền | Chưa chứng minh cross-domain generalization |
| Radar CARLA mức point | Không có signal-level multipath/ghost physics | Synthetic injection chỉ là fault model có nhãn |
| Repeat có tương quan | x3/x5 cùng named condition | Không coi run là mẫu traffic độc lập |
| Synchronous processing | Simulator chờ inference | CUDA timing không chứng minh ECU deadline |
| Không HIL/xe thật | Chỉ có CARLA | Không claim functional safety hay road readiness |

Aggregate precision/F1 còn phụ thuộc tỷ lệ positive/negative do người thiết kế
suite chọn. Wilson interval run-level được cung cấp nhưng không khắc phục hoàn
toàn pseudo-replication; named-scenario consistency mới là đơn vị diễn giải
chính. Các scenario CCRs/CCRm/CCRb chỉ “lấy cảm hứng từ NCAP”, không phải bài
chứng nhận Euro NCAP.

## 5.4. Hướng Phát Triển

Các bước tiếp theo nên ưu tiên giải quyết failure mode thay vì tiếp tục tăng
repeat giống hệt:

- bổ sung probabilistic multi-target tracking và explicit radar ghost model;
- dùng objectness/free-space hoặc segmentation đa lớp thay vì camera `car` veto;
- hiệu chỉnh fallback theo uncertainty, impact-speed reduction và available
  stopping margin, không chỉ threshold nhị phân;
- kiểm thử đa map, weather, illumination, vehicle/prop blueprint và sensor noise;
- mô phỏng camera dropout/stale frame theo thời gian thay vì chỉ tắt detector;
- bổ sung actuator/communication delay, tire-road friction và brake dynamics;
- đánh giá trên recorded sensor data, software/hardware-in-the-loop trước khi
  cân nhắc thử nghiệm xe thật có kiểm soát;
- thiết kế scenario sampling theo distribution mục tiêu nếu muốn diễn giải tỷ
  lệ ngoài benchmark.

Video minh họa nên quay sau khi khóa thuật toán, gồm vehicle hazard, edge-prop
suppression, core non-vehicle recovery và hold-out ghost/prop limitation. Video
không thay thế CSV/tick log trong evidence.

## 5.5. Kết Luận Chung

Hệ thống hoàn thành mục tiêu xây dựng và đánh giá AEB camera-radar trong CARLA,
đồng thời làm rõ vì sao “fusion tốt hơn” là một kết luận quá đơn giản. Radar-only,
hard gate và emergency fallback chiếm các vị trí khác nhau trên trade-off
precision/recall. Safe fallback đạt kết quả tốt nhất trên core benchmark đã biết,
nhưng frozen hold-out cho thấy hard gate đạt nhiều PASS hơn do fallback phản ứng
với radar ghost mạnh, trong khi cả ba chính sách vẫn thất bại với một số props
mới.

Do đó, kết luận phù hợp nhất là: camera gating có hiệu quả như cơ chế giảm
false-positive; radar emergency fallback có thể phục hồi một phần obstacle
recall nhưng cần uncertainty-aware sensing và đánh giá rộng hơn. Bản v3 không
coi fallback là bảo đảm fail-safe, mà coi đây là một thiết kế trung gian có ưu,
nhược điểm và failure evidence được công bố đầy đủ.
