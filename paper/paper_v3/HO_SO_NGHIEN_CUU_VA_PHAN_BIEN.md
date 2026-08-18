# Hồ Sơ Nghiên Cứu, Phản Biện Và Truy Vết Paper V3

**Ngày rà soát:** 18/08/2026

**Paper:** *A Sensor-to-Brake AEB Pipeline in CARLA with Object-Level Radar, Camera Verification, and Limit-Finding Evaluation*

Tài liệu này hợp nhất bốn nội dung:

1. khảo sát các nghiên cứu liên quan;
2. phản biện nội bộ qua nhiều vòng;
3. ánh xạ claim trong paper tới code, cấu hình và evidence;
4. ghi chú các thay đổi kỹ thuật của `paper_v3`.

Mục tiêu của hồ sơ không phải làm mọi chỉ số trông tốt hơn, mà là xác định chính
xác paper có thể tuyên bố điều gì từ evidence hiện có, đồng thời loại bỏ các claim
không đủ cơ sở.

---

## 1. Phạm Vi Và Phương Pháp Khảo Sát

Đây là một khảo sát tập trung nhằm định vị paper, không phải systematic review
đầy đủ. Các truy vấn chính gồm:

- `automatic emergency braking CARLA`;
- `AEB CARLA simulator`;
- `radar camera fusion automatic emergency braking`;
- `AEB target selection radar camera fusion`;
- `closed-loop automatic emergency braking simulation`.

Metadata và abstract được kiểm tra qua Crossref, OpenAlex và arXiv. Sau đó, các
claim dự kiến được đối chiếu với code, YAML và evidence đã check-in trong dự án.
`paper_v3` chỉ giữ các claim có nguồn nội bộ hoặc tài liệu tham khảo kiểm chứng
được.

---

## 2. Các Công Trình Gần Nhất Và Ảnh Hưởng Đến Claim Mới

| Công trình | Trọng tâm chính | Quan hệ với dự án | Hệ quả đối với `paper_v3` |
|---|---|---|---|
| Kim và Song, ICCAS 2013, *Vehicle Recognition Based on Radar and Vision Sensor Fusion for Automatic Emergency Braking* | Nhận dạng xe bằng radar và thị giác cho AEB | Chứng minh radar--vision AEB đã tồn tại từ trước | Không claim phát minh radar--camera AEB fusion |
| Hsu và cộng sự, SAE 2015, *Noise Filtering in Autonomous Emergency Braking Systems with Sensor Fusions* | Lọc nhiễu radar/camera và làm sạch mục tiêu AEB | Đã có xử lý nhiễu và kiểm tra nhất quán camera--radar | Trình bày filtering/tracking là đóng góp triển khai, không phải lý thuyết fusion mới |
| Bae và cộng sự, Sensors 2021, *Estimation of the Closest In-Path Vehicle by Low-Channel LiDAR and Camera Sensor Fusion* | Chiếu hình học, chọn xe gần nhất nằm trong quỹ đạo và kiểm thử AEB | Gần với path relevance và image association nhưng dùng LiDAR và xe thật | Nhấn mạnh tầng tạo radar object từ point CARLA và đánh giá biên vòng kín |
| Zhang và cộng sự, Electronics 2023, *Research on Automatic Emergency Braking System Based on Target Recognition and Fusion Control Strategy in Curved Road* | Chọn target trên đường cong, kết hợp TTC/khoảng cách an toàn và phanh phân tầng trong CarSim/Simulink | Trùng đáng kể với path-aware target selection và multi-stage control | Không claim path gate, TTC/distance fusion hoặc staged braking là mới riêng lẻ |
| Feng và cộng sự, WEVJ 2025, *Validating DVS Application in Autonomous Driving with Various AEB Scenarios in CARLA Simulator* | AEB trong CARLA với event camera | Chứng minh CARLA AEB kết hợp learned visual perception đã có | Phân biệt bằng RGB + radar object layer, late semantic gate và sweep car-to-car |
| Akula và cộng sự, arXiv 2026, *Radar-Guided Camera Verification for Automatic Emergency Braking: Rethinking Object Detection in Radar--Camera Fusion* | Radar-led camera verification bằng vùng mật độ cạnh, brake-by-wire trên xe thật | Rất gần triết lý radar-first/camera-verifier và có validation xe thật mạnh hơn | Bắt buộc trích dẫn; không claim radar-first camera verification là đầu tiên |
| Gómez-Huélamo và cộng sự, MTAP 2022 | Validation pipeline tự lái end-to-end trong CARLA bằng scenario lấy cảm hứng protocol | Chứng minh CARLA đã được dùng làm nền tảng validation pipeline | Định vị paper là baseline kỹ thuật có phạm vi hẹp, không phải phương pháp validation hoàn toàn mới |
| Yang và cộng sự, JAT 2022 | Tổng quan perception, decision, actuation và đánh giá AEB | Xác nhận AEB là chuỗi nhận thức--quyết định--chấp hành | Dùng để tạo động lực cho sensor-to-brake integration |
| Magosi và cộng sự, Sensors 2022 | Mô hình radar ô tô trong virtual validation | Chỉ ra các cấp fidelity và giới hạn radar ảo | Công khai radar CARLA không phải chuỗi FMCW raw |

### 2.1. Kết luận về tính mới

Khảo sát không hỗ trợ claim rằng một thành phần riêng lẻ trong dự án là hoàn toàn
mới. Đóng góp có thể bảo vệ được là cấu hình tích hợp cụ thể, có thể kiểm tra và
được đánh giá theo biên:

1. Chuyển radar detection point của CARLA thành object track đã xác nhận trước khi
   cho phép quyết định phanh, thay vì dùng actor ground truth hoặc point gần nhất.
2. Kết hợp liên quan quỹ đạo và rủi ro động học từ radar với cổng cho phép ngữ
   nghĩa YOLO ở tầng muộn; radar vẫn sở hữu khoảng cách và vận tốc tương đối.
3. Khép kín vòng điều khiển qua staged PID và `VehicleControl`, đồng thời ghi log
   theo fixed tick với điều kiện PASS rõ ràng.
4. Báo cáo outcome map 66 case, tách dải vận tốc mục tiêu với stress test và giữ
   nguyên cả ba collision.

Cách định vị phù hợp là:

> Một cấu hình kỹ thuật riêng biệt và baseline mô phỏng có thể truy vết, không
> phải thuật toán fusion đầu tiên hoặc hệ thống AEB sẵn sàng sản xuất.

---

## 3. Ánh Xạ Claim Tới Code, Cấu Hình Và Evidence

| Claim hoặc giá trị trong paper | Nguồn chính | Ghi chú kiểm tra |
|---|---|---|
| CARLA 0.9.11, Town04, Tesla Model 3 | `README.md`, `configs/sensors.yaml` | CARLA version là thông tin phạm vi cấp repository |
| Camera 1280x720, FOV 70 độ, tick 0.05 s | `configs/sensors.yaml` | YOLO inference được throttle riêng ở 0.15 s |
| Radar 100 m, FOV 30/6 độ, 2000 điểm/s, tick 0.05 s | `configs/sensors.yaml` | Đây là cấu hình simulator, không phải thông số radar thương mại |
| Lọc range, height, predicted path và ground | `core/radar_aeb_pipeline.py` | Ground rejection truy vấn độ cao waypoint CARLA; đã công khai là simulator privilege |
| Quỹ đạo độ cong không đổi và horizon 2.5 s | `core/radar_aeb_pipeline.py`, `configs/sensors.yaml` | Công thức và horizon khớp code |
| Cluster gate 1.0 m, vertical 1.5 m, velocity 2.0 m/s; range lấy percentile 20 | `perception/radar/radar_object_tracker.py`, `configs/sensors.yaml` | Gom cụm connected-component theo quy tắc tất định |
| Track xác nhận 3 frame, xóa sau 4 miss | Cùng tracker và config | Một miss làm track stale và unconfirmed ngay lập tức |
| Chọn target theo TTC hữu hạn rồi khoảng cách | `core/target_selector.py` | Chỉ dùng object confirmed và không stale |
| Target gate 5 lần chọn; bypass tại 22 m hoặc margin -4 m | `core/radar_aeb_pipeline.py`, `configs/sensors.yaml` | Việc đếm bắt đầu khi confirmed target có thể được chọn |
| Phép chiếu camera và cổng cho phép bbox YOLO | `scripts/run_fusion_aeb_scenarios.py` | Chỉ provisional `BRAKE` bị block; trạng thái radar khác đi qua |
| Camera hold 0.35 s dùng host monotonic time | `scripts/run_fusion_aeb_scenarios.py` | Giá trị mặc định nằm trong code, không ghi rõ trong `sensors.yaml`; đã đưa vào threats to validity |
| Actor ID và actor kinematics không tham gia quyết định phanh | Audit fusion runner và core pipeline | Exact transform và map height vẫn được dùng; actor matching chỉ có trong logger/evaluation |
| Dấu vận tốc và công thức TTC/khoảng cách dừng | `control/brake.py` | Relative velocity âm nghĩa là tiến gần; target speed được clamp tại 0 |
| Staged PID gain, bound và threshold | `control/brake.py`, `configs/sensors.yaml` | Supervisory states khác với các tầng giới hạn lệnh phanh |
| Brake latch trong pha dừng | `configs/sensors.yaml`, `control/brake.py` | `hold_brake_until_stopped: true`; trạng thái reset giữa các scenario |
| Dataset split, số box và empty ratio | `report/report.md`, `docs/official/08_DATASET_AND_TRAINING.md` | Dataset local không có trong checkout hiện tại |
| Chỉ số YOLO và training curve | `report/report.md`, `report/assets/evidence/yolo_training_results.png` | Training run và model artifact local không có; metric chỉ được dùng như evidence detector trong domain |
| Training config | `configs/model_training.yaml` | 640 px, 100 epoch, batch 16, AdamW, `lr0=0.001`, seed 2026 |
| Thành phần 66 case | `configs/scenarios/suites/system_limit_extended_sweep.yaml` | 24 moving-lead, 30 braking-lead, 12 cut-in |
| Phân chia intended/stress | Scenario YAML và quy tắc tốc độ ghi trong paper | Intended: các set không quá 80 km/h, 38 case; stress: set tốc độ cao hơn, 28 case |
| Điều kiện PASS | `scripts/run_radar_aeb_scenarios.py::summarize_scenario`, scenario YAML | Có phanh như kỳ vọng, không collision, min gap ít nhất 0.5 m, lane offset không quá 1.25 m |
| CCRb phanh mục tiêu tại 1.5 s với brake=1.0 | Final scenario YAML | Áp dụng cho toàn bộ tổ hợp CCRb |
| Cut-in bắt đầu chuyển làn tại 1.0 s | Final scenario YAML | Xe bắt đầu ở làn trái và chuyển sang phải |
| Tổng 63/66 và ba collision | `docs/log/FINAL_EVIDENCE_PACK_20260628.md` | CCRm 24/24, CCRb 28/30, cut-in 11/12 |
| Min gap của ba collision | Final evidence pack | 0.0134 m, 0.0806 m và 0.4763 m |
| First-brake và min-gap đại diện | `report/report.md`, các evidence figure | Raw final CSV không có; caption dẫn cả report và evidence summary |
| Diễn giải single-run | Tài liệu final run và không có repeat aggregate | Paper không claim confidence hoặc reliability |

### 3.1. Ranh giới sử dụng ground truth

Ground truth không được dùng để tạo lệnh phanh online, nhưng paper không tuyên
bố hệ thống hoàn toàn không dùng thông tin đặc quyền của simulator. Cụ thể:

- map waypoint height được dùng để loại ground point;
- exact sensor transform được dùng cho phép chiếu radar--camera;
- actor ID, actor role, actor gap và collision được dùng trong logger/evaluation;
- ground-truth 3-D box được dùng offline để sinh nhãn YOLO.

Việc công khai ranh giới này giúp phân biệt rõ sensor-based decision với
simulator-based scoring.

### 3.2. Artifact còn thiếu

- Final evidence pack dẫn tới CSV/JSON local nhưng các file không có trong
  checkout hiện tại.
- `models/yolo26n_aeb_v7.pt` và `.onnx` không có; thư mục `models/` chỉ giữ
  `.gitkeep`.
- Final aggregate 66 case không có case không nguy hiểm.
- Không có matched ablation hoặc nhiều lần lặp theo seed.
- Không có phân bố latency end-to-end được check-in.

Do đó paper chỉ báo cáo hành vi theo case cấu hình, không claim:

- reliability thống kê;
- fusion chắc chắn làm giảm false brake;
- PID vượt trội controller khác;
- chứng nhận NCAP;
- khả năng chuyển trực tiếp sang xe thật.

---

## 4. Phản Biện Nội Bộ Qua Các Vòng

## 4.1. Vòng 0: Chấm `paper_v2`

### Quyết định: major revision / weak reject

| Tiêu chí | Điểm | Nhận xét chính |
|---|---:|---|
| Mức độ quan trọng của bài toán | 8/10 | Tích hợp AEB sensor-to-brake phù hợp để nghiên cứu trong mô phỏng |
| Định vị tính mới | 4/10 | Related work còn mỏng; các thành phần chính đều có công trình gần |
| Độ chính xác kỹ thuật | 6/10 | Chưa công khai map-height, mô tả final suite rộng hơn evidence và thiếu điều kiện PASS |
| Độ chặt thực nghiệm | 4/10 | Mỗi case một lần chạy, không ablation, không confidence interval, final aggregate không có negative case |
| Truy vết evidence | 5/10 | Có summary nhưng thiếu raw final CSV/JSON và model file |
| Viết và bố cục | 7/10 | Dễ đọc nhưng hình gọi là architecture thực tế chỉ là sensor coverage; claim đóng góp còn mạnh |

### Các lỗi chặn chính

1. **Không chứng minh được firstness.** Đã có radar--vision AEB, geometric
   association, curved-road target selection, graded braking, CARLA AEB và
   radar-guided camera verifier.
2. **Dùng ODD chưa chính xác.** Nhóm scenario chia theo tốc độ không phải ODD.
   ODD phải mô tả môi trường, actor, thời tiết và cảm biến.
3. **Cần ghi đúng final suite.** Aggregate 66 case chỉ gồm 24 CCRm, 30 CCRb và
   12 cut-in.
4. **PASS mô tả chưa đủ.** Runner còn kiểm tra brake activation, min gap và lane
   offset.
5. **Claim không dùng ground truth quá mạnh.** Hệ thống có dùng map waypoint
   height và exact sensor transform.
6. **Ngôn ngữ nhân quả thiếu ablation.** Không thể kết luận fusion giảm false
   brake hoặc PID giảm jerk từ final evidence hiện tại.
7. **Ẩn giới hạn đồng bộ.** Camera hold dùng host monotonic time thay vì
   simulation time.
8. **Diễn giải 63/66 chưa an toàn.** Đây là coverage theo case cấu hình, không
   phải xác suất an toàn.

## 4.2. Vòng 1: Bản nháp đầu của `paper_v3`

### Các cải thiện được chấp nhận

- Bổ sung focused literature review và trích dẫn công trình gần nhất năm 2026.
- Đổi định vị từ thuật toán mới sang integration engineering contribution.
- Thay sensor-coverage figure bằng kiến trúc execution-order thật.
- Công khai map-height, calibration privilege và ranh giới evaluation ground
  truth.
- Định nghĩa chính xác suite, subset và PASS.
- Hạn chế kết luận về hành vi cấu hình tích hợp.
- Thêm threats to internal, construct, external và reproducibility validity.

### Các lỗi còn lại sau vòng 1

1. Quy đổi frame confirmation sang latency chưa chính xác. Với 20 Hz, mẫu thứ ba
   đến sau mẫu đầu 0.10 s; target đạt năm lần chọn ở mẫu thứ bảy, tức 0.30 s sau
   quan sát đầu nếu không bypass.
2. Mô tả release chưa xét `hold_brake_until_stopped`. Batch đánh giá giữ phanh
   qua pha dừng trừ khi camera permission chặn.
3. Bảng đại diện dẫn toàn bộ giá trị về short evidence summary trong khi một số
   first-brake value nằm trong checked-in report.
4. Bản sáu trang ban đầu để phần lớn trang cuối trống. Nội dung được phân bố lại
   bằng measurement semantics, traceability và validity analysis thay vì kéo giãn
   hình hoặc khoảng trắng.

## 4.3. Vòng 2: Chấm bản `paper_v3` cuối

### Quyết định: chấp nhận được như một paper mô phỏng/kỹ thuật có phạm vi rõ

| Tiêu chí | Điểm | Đánh giá cuối |
|---|---:|---|
| Mức độ quan trọng | 8.5/10 | Câu hỏi sensor-to-brake rõ ràng, phạm vi car-to-car hẹp |
| Định vị tính mới | 7/10 | Claim tích hợp trung thực và thảo luận trực tiếp prior art gần nhất |
| Độ chính xác kỹ thuật | 8.5/10 | Execution order, quyền sở hữu thông tin, temporal gate, brake latch, công thức và scoring khớp code/config |
| Độ chặt thực nghiệm | 6/10 | Sweep và failure analysis hữu ích nhưng single-run và thiếu ablation vẫn là điểm yếu không thể sửa bằng văn bản |
| Minh bạch evidence | 9/10 | Công khai failure, simulator privilege, artifact thiếu và wall-time synchronization |
| Viết và bố cục | 8.5/10 | Bản Anh đủ sáu trang IEEE, có architecture thật, result map rõ, không lỗi citation/layout |
| Khả năng tái lập | 6.5/10 | Mapping module/config tốt nhưng thiếu raw log và model làm giảm khả năng rebuild độc lập |

### Vì sao dừng phản biện tại đây

Các hạn chế còn lại không thể sửa bằng câu chữ nếu không tạo dữ liệu giả. Một
submission mạnh hơn cần chạy thí nghiệm mới:

- lặp theo controlled seed;
- so sánh radar-only, camera-gated và perfect-perception;
- đưa negative/adjacent-lane case vào cùng final matrix;
- dùng simulation-time cho camera synchronization;
- đo latency end-to-end;
- phát hành raw logs và model hash đầy đủ.

Trong phạm vi evidence đã check-in, manuscript cuối được đánh giá là nhất quán và
đủ bảo thủ. Claim mạnh hơn sẽ làm paper kém đáng tin hơn.

---

## 5. Các Thay Đổi Chính Của `paper_v3`

### 5.1. Định vị

`paper_v3` được viết lại sau focused literature search và audit claim theo
code/config. Tiêu đề và mạch nội dung nhấn mạnh:

- sensor-to-brake engineering baseline;
- object-level radar trong CARLA;
- late camera semantic permission;
- limit-finding evaluation.

Paper không tự nhận tạo ra TTC, YOLO, PID, path gate hoặc fusion primitive mới.

### 5.2. Sửa lỗi kỹ thuật và diễn giải

- Thay hình kiến trúc bằng
  `report/assets/aeb_closed_loop_architecture_en.png`.
- Tách ODD khỏi intended-range/stress subset.
- Ghi đúng 24 CCRm + 30 CCRb + 12 cut-in.
- Bổ sung đầy đủ PASS definition.
- Công khai map-height và exact calibration geometry.
- Làm rõ actor identity/kinematics không tham gia phanh nhưng được dùng chấm.
- Sửa timing của track/target gate theo sample thực tế.
- Công khai camera hold 0.35 s theo wall time.
- Công khai brake latch qua pha dừng.
- Loại claim nhân quả không có ablation.
- Đổi cách đọc 63/66 thành configured-case outcomes.
- Bổ sung threats to validity và artifact thiếu.

### 5.3. Các file đầu ra chính

- `aeb_ieee_6page.tex`: bản tiếng Anh chính.
- `aeb_ieee_6page.pdf`: PDF tiếng Anh 6 trang.
- `aeb_ieee_6page_vi.tex`: bản review tiếng Việt cùng claim/hình/bảng/reference.
- `aeb_ieee_6page_vi.pdf`: PDF review tiếng Việt.
- `references.bib`: tài liệu tham khảo dùng chung.
- `build.sh`: build song ngữ, kiểm tra citation/reference và bắt buộc bản Anh đúng
  sáu trang.
- `HO_SO_NGHIEN_CUU_VA_PHAN_BIEN.md`: tài liệu hiện tại, hợp nhất research,
  review, source map và revision notes.

---

## 6. Kết Quả Build Và Validation

Build bằng pdfLaTeX + BibTeX ngày 18/08/2026.

| Đầu ra | Số trang | Kết quả kiểm tra |
|---|---:|---|
| `aeb_ieee_6page.pdf` | 6 | Đúng page target, không citation/reference chưa resolve, không overfull box, font được nhúng |
| `aeb_ieee_6page_vi.pdf` | 6 | Bản review đầy đủ, không citation/reference chưa resolve, không overfull box, font được nhúng |

`build.sh` sẽ fail nếu:

- thiếu hoặc rỗng một trong hai PDF;
- có citation/reference chưa resolve;
- bản tiếng Anh không đúng sáu trang.

---

## 7. Kế Hoạch Hoàn Thiện Paper Trên Máy CARLA

Phần này là checklist thực nghiệm để tiếp tục nâng `paper_v3`. Nguyên tắc quan
trọng là **chạy lại baseline hiện tại trước khi sửa thuật toán**, sau đó mới thực
hiện ablation hoặc thay đổi đồng bộ. Nếu sửa code trước, kết quả mới sẽ không còn
so sánh trực tiếp được với evidence 63/66 đang dùng trong paper.

### 7.1. Đồng bộ repository và ghi lại môi trường

Trên máy có CARLA:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
git pull origin main
git rev-parse HEAD
```

Commit dùng để tạo một bộ evidence phải được lưu vào report của run. Trước khi
chạy, ghi lại môi trường:

```bash
mkdir -p outputs/paper_v3_reproduction/environment

uname -a \
  > outputs/paper_v3_reproduction/environment/uname.txt
nvidia-smi \
  > outputs/paper_v3_reproduction/environment/nvidia_smi.txt
../venv/bin/python --version \
  > outputs/paper_v3_reproduction/environment/python_carla.txt
.venv_yolo310/bin/python --version \
  > outputs/paper_v3_reproduction/environment/python_yolo.txt
git rev-parse HEAD \
  > outputs/paper_v3_reproduction/environment/git_commit.txt
git status --short \
  > outputs/paper_v3_reproduction/environment/git_status.txt
../venv/bin/pip freeze \
  > outputs/paper_v3_reproduction/environment/requirements_carla.txt
.venv_yolo310/bin/pip freeze \
  > outputs/paper_v3_reproduction/environment/requirements_yolo.txt
```

Kiểm tra model và lưu hash:

```bash
ls -lh models/yolo26n_aeb_v7.pt models/yolo26n_aeb_v7.onnx
sha256sum models/yolo26n_aeb_v7.pt models/yolo26n_aeb_v7.onnx \
  > outputs/paper_v3_reproduction/environment/model_sha256.txt
```

Nếu model không có, cần khôi phục đúng artifact đã tạo final evidence trước khi
chạy. Không nên train model mới rồi vẫn gọi kết quả là reproduction của baseline.
Model mới phải có version, hash và một nhóm kết quả riêng.

### 7.2. Kiểm tra trước khi chạy batch

Khởi động CARLA 0.9.11 bằng cấu hình ổn định của dự án:

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 \
__GLX_VENDOR_LIBRARY_NAME=nvidia \
./CarlaUE4.sh -quality-level=Low
```

Trong terminal khác:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
python3 laucher.py --check
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Chỉ chạy batch khi:

- CARLA server vào được Town04;
- model ONNX load thành công;
- unit test PASS;
- working tree và commit đã được ghi lại;
- còn đủ dung lượng cho log/video.

### 7.3. Thí nghiệm A -- lặp lại final fusion baseline

Đây là thí nghiệm ưu tiên cao nhất. Giữ nguyên:

- `configs/sensors.yaml`;
- YOLO ONNX hiện tại;
- `staged_pid`;
- physics control;
- final 66-case suite.

Chạy mỗi scenario ít nhất 5 lần:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb

../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --repeat 5 \
  --run-id paper_v3_fusion_repeat5 \
  --load-map
```

Runner trả exit code khác 0 nếu trong batch có bất kỳ case FAIL nào, kể cả khi
batch đã chạy xong. Vì final suite vốn có ba case fail, cần kiểm tra các file
summary thay vì coi exit code 1 là server crash. Phải phân biệt:

- batch hoàn tất nhưng có scenario FAIL;
- CARLA hoặc Python dừng giữa batch;
- scenario bị missing do server mất kết nối.

Kết quả mong muốn cần trả lời:

1. Ba case cũ có collision ở cả 5 lần không?
2. Có case PASS cũ nào trở thành FAIL không?
3. First-brake time, brake gap và minimum gap dao động bao nhiêu?
4. Có scenario nào thiếu run không?

Không ghi `63/66 = 95.45% reliability`. Sau khi lặp, nên báo cáo theo hai tầng:

- số scenario có kết quả ổn định qua toàn bộ lần chạy;
- phân bố outcome trên tổng số run, kèm số lần lặp và độ phân tán.

### 7.4. Thí nghiệm B -- radar-only đối xứng

Dùng cùng final 66 case, cùng staged PID và cùng số lần lặp, nhưng chạy pipeline
radar-only:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --repeat 5 \
  --run-id paper_v3_radar_only_repeat5 \
  --load-map
```

So sánh với Thí nghiệm A theo từng scenario, không chỉ so sánh tổng pass rate.
Các chỉ số tối thiểu:

- collision rate;
- false/missing brake;
- first-brake time;
- brake gap;
- minimum bumper gap;
- target-confirmed rate;
- target--hazard match rate nếu logger có dữ liệu;
- maximum deceleration và raw jerk chỉ dùng so sánh nội bộ.

Ablation này mới cho phép thảo luận camera permission đã thay đổi hành vi ở đâu.
Nếu final 66 case chỉ có hazard, chưa được kết luận camera làm giảm false brake.

### 7.5. Thí nghiệm C -- negative và target-selection regression

Dùng `fusion_regression.yaml` để bổ sung clear-road, adjacent-lane và curve case
vào cùng cấu hình camera-gated:

```bash
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/fusion_regression.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --repeat 5 \
  --run-id paper_v3_fusion_negative_repeat5 \
  --load-map
```

Suite này có các case không kỳ vọng phanh như:

- `false_clear_90`;
- `false_adjacent_90`;
- `false_curve_clear_90`;
- các `false_curve_adjacent_*`.

Ngoài ra, có thể chạy regression rộng hơn cho radar-only:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --repeat 5 \
  --run-id paper_v3_radar_regression_repeat5 \
  --load-map
```

Kết quả negative phải được báo cáo riêng:

```text
false-brake rate = số run phanh khi expected_brake=False
                   / tổng run expected_brake=False
```

Chỉ sau thí nghiệm này mới có thể thảo luận định lượng về unnecessary braking.

### 7.6. Thí nghiệm D -- controller ablation

Ưu tiên so sánh tối thiểu hai controller:

1. `binary`;
2. `staged_pid`.

Tạo các sensor config độc lập, ví dụ:

```text
configs/ablation/sensors_binary.yaml
configs/ablation/sensors_staged_pid.yaml
```

Mỗi file phải giữ nguyên sensor, radar tracker, target gate, YOLO và fusion;
chỉ thay `brake.brake_mode` cùng các tham số controller liên quan. Không sửa trực
tiếp `configs/sensors.yaml` giữa hai run vì rất khó truy vết.

Chạy cùng một scenario suite và cùng số lần lặp:

```bash
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/ablation/sensors_binary.yaml \
  --control-mode physics \
  --repeat 5 \
  --run-id paper_v3_binary_repeat5 \
  --load-map

../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/ablation/sensors_staged_pid.yaml \
  --control-mode physics \
  --repeat 5 \
  --run-id paper_v3_staged_pid_repeat5 \
  --load-map
```

Không nên kết luận staged PID ``êm hơn'' chỉ từ một giá trị jerk lớn nhất. Cần
so sánh ít nhất:

- collision;
- minimum gap;
- thời điểm bắt đầu phanh;
- profile lệnh phanh;
- maximum/mean deceleration;
- raw jerk distribution;
- số lần brake command đổi tầng;
- thời gian xe nằm ở emergency brake.

### 7.7. Sửa đồng bộ camera theo simulation time

Baseline hiện tại giữ camera confirmation 0.35 s bằng `time.monotonic()`. Tải GPU
hoặc tốc độ chạy batch có thể làm 0.35 s wall time tương ứng với số tick mô phỏng
khác nhau.

Thứ tự đúng:

1. hoàn thành và lưu Thí nghiệm A với code hiện tại;
2. tạo commit riêng sửa camera hold theo `sim_time_s` hoặc sensor timestamp;
3. thêm `fusion.confirmation_hold_s: 0.35` rõ ràng vào YAML;
4. viết unit/integration test cho thời điểm hết hold;
5. chạy lại cùng final suite với run ID mới;
6. không trộn kết quả trước và sau sửa đồng bộ trong cùng một bảng mà thiếu nhãn.

Run đề xuất sau khi sửa:

```text
paper_v3_fusion_simtime_repeat5
```

Nếu kết quả thay đổi, paper phải mô tả bản simulation-time là cấu hình mới, không
được dùng lại evidence cũ như thể thuật toán không đổi.

### 7.8. Controlled seed và tính lặp

Runner hiện chưa có tùy chọn `--seed`. Trước khi claim ``seed-controlled'', cần
bổ sung seed cho các thành phần có randomness:

- Python `random`;
- NumPy nếu được dùng;
- CARLA Traffic Manager nếu scenario dùng Traffic Manager;
- quá trình chọn blueprint/spawn nếu có ngẫu nhiên.

Seed phải được ghi vào từng summary. Nếu scenario hoàn toàn tất định, vẫn cần lặp
để đo dao động do physics/server/sensor scheduling, nhưng không được gọi đó là
random-seed study.

Một thiết kế gọn có thể dùng:

```text
seeds = 2026, 2027, 2028, 2029, 2030
```

Sau khi code hỗ trợ, mỗi result row phải chứa cả `scenario_id`, `run_index` và
`seed`.

### 7.9. Cấu trúc artifact cần giữ

Mỗi experiment nên có thư mục độc lập:

```text
logs/
├── paper_v3_fusion_repeat5/
├── paper_v3_radar_only_repeat5/
├── paper_v3_fusion_negative_repeat5/
├── paper_v3_radar_regression_repeat5/
├── paper_v3_binary_repeat5/
├── paper_v3_staged_pid_repeat5/
└── paper_v3_fusion_simtime_repeat5/
```

Mỗi thư mục tối thiểu phải giữ:

- per-tick CSV;
- per-case summary CSV/JSON;
- aggregate summary;
- scenario config snapshot;
- sensor config snapshot;
- git commit;
- model SHA-256;
- command đã chạy;
- timestamp bắt đầu/kết thúc;
- danh sách missing/crashed run;
- plot dùng trong paper.

Có thể nén evidence để chuyển máy hoặc upload release:

```bash
tar -czf outputs/paper_v3_reproduction_$(date +%Y%m%d).tar.gz \
  outputs/paper_v3_reproduction \
  logs/paper_v3_fusion_repeat5 \
  logs/paper_v3_radar_only_repeat5 \
  logs/paper_v3_fusion_negative_repeat5
```

Không nên commit hàng GB log/video trực tiếp vào Git. Có thể đưa file nén lên
GitHub Release hoặc Drive, sau đó ghi URL và SHA-256 vào repository.

### 7.10. Bảng kết quả cần tạo sau khi chạy

#### Bảng 1 -- Repeated final outcomes

| Family | Scenario | Runs | Pass | Collision | Mean min gap | Std min gap |
|---|---|---:|---:|---:|---:|---:|

#### Bảng 2 -- Radar-only so với camera-gated

| Config | Hazard collision rate | Missed-brake rate | Negative false-brake rate | Mean first-brake time |
|---|---:|---:|---:|---:|

#### Bảng 3 -- Controller ablation

| Controller | Pass/collision | Mean min gap | Max/mean deceleration | Raw jerk statistic |
|---|---:|---:|---:|---:|

#### Bảng 4 -- Boundary stability

| Scenario biên | Kết quả từng run | Brake gap range | Min gap range | Nhận xét |
|---|---|---:|---:|---|

Không gộp intended-range và stress thành một con số duy nhất nếu việc gộp làm mất
thông tin về vùng hoạt động.

### 7.11. Điều kiện cập nhật lại claim trong paper

Chỉ nâng claim khi có đúng evidence tương ứng:

| Claim muốn viết | Evidence bắt buộc |
|---|---|
| Camera gate giảm false brake | Matched radar-only/camera-gated trên cùng negative suite, nhiều lần lặp |
| Staged PID tốt hơn binary | Controller ablation giữ nguyên perception/scenario, có nhiều chỉ số và lặp |
| Hệ thống ổn định | Repeated runs, không missing, báo cáo phân bố và seed/config |
| Hoạt động real-time | Đo end-to-end latency và deadline miss, không dùng FPS video thay thế |
| Có khả năng tổng quát | Test map, thời tiết, ánh sáng, vehicle shape hoặc dataset ngoài domain |
| An toàn/đạt chuẩn | Quy trình tiêu chuẩn và validation xe thật; mô phỏng hiện tại không đủ |

Nếu kết quả lặp không giữ được 38/38 intended-range, phải sửa abstract, bảng kết
quả và conclusion theo dữ liệu mới; không được chọn riêng run đẹp nhất.

### 7.12. Checklist hoàn tất trước khi tạo `paper_v4`

- [ ] Baseline fusion hiện tại đã chạy lặp và không thiếu run.
- [ ] Radar-only chạy cùng final suite và cùng số lần lặp.
- [ ] Negative fusion regression đã có false-brake statistics.
- [ ] Binary và staged PID được so sánh đối xứng.
- [ ] Camera hold đã có baseline wall-time và bản simulation-time riêng.
- [ ] Seed hoặc nguồn không tất định được mô tả rõ.
- [ ] Raw CSV/JSON, config snapshot, command, commit và model hash được lưu.
- [ ] Bảng aggregate được sinh tự động, không chép tay.
- [ ] Case fail vẫn được giữ nguyên trong report.
- [ ] Claim mới có ablation hoặc evidence trực tiếp.
- [ ] `SOURCE_MAP`/hồ sơ truy vết được cập nhật theo artifact mới.
- [ ] Paper tiếng Anh build đúng 6 trang, bản Việt build thành công.
- [ ] Không có citation/reference chưa resolve hoặc overfull box.
- [ ] PDF và evidence archive có SHA-256.

Sau khi hoàn thành checklist, nên tạo `paper/paper_v4/` thay vì ghi đè
`paper_v3`. `paper_v3` phải tiếp tục đại diện đúng cho evidence single-run hiện
tại.

---

## 8. Kết Luận Hồ Sơ

`paper_v3` có thể bảo vệ tốt nhất khi được trình bày như một nghiên cứu tích hợp
hệ thống trong mô phỏng với phạm vi rõ, execution chain có thể truy vết và cách
đánh giá giữ nguyên case fail. Giá trị nổi bật không nằm ở từng công thức hoặc
module riêng lẻ, mà ở:

- việc bắt đầu từ simulated sensor outputs thay vì perfect lead state;
- chuyển radar point thành confirmed object trước khi phanh;
- phân chia rõ vai trò radar và camera;
- khép kín perception--decision--actuation;
- và báo cáo trung thực biên speed--gap--maneuver.

Paper hiện phù hợp với phạm vi đồ án hoặc workshop/conference thiên về engineering
simulation. Để hướng tới venue mạnh hơn, ưu tiên tiếp theo phải là thí nghiệm
ablation, lặp theo seed, negative-case matrix và phát hành artifact đầy đủ, không
phải tiếp tục tăng độ mạnh của claim trong phần viết.
