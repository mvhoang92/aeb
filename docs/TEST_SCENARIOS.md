# Kịch Bản Test Và Log AEB

Tài liệu này mô tả file test, mục tiêu từng kịch bản, cách chạy và cấu trúc log
của dự án AEB trên CARLA 0.9.11.

Các case có tên gần với CCRs, CCRm và CCRb chỉ là **NCAP-inspired** để phát
triển thuật toán. Đây chưa phải quy trình chứng nhận Euro NCAP chính thức.

## Danh Sách File Test

| File | Mục đích |
| --- | --- |
| `test_cam.py` | Kiểm tra camera sau kính lái và giao diện manual control. |
| `test_radar.py` | Kiểm tra toàn bộ radar point trên bird-eye view. |
| `test_model.py` | Kiểm tra camera và YOLO ONNX CUDA. |
| `test_fusion.py` | Kiểm tra phép chiếu radar lên bbox camera. |
| `test_brake_radar.py` | Test radar-only AEB, phanh nhị phân và icon cảnh báo FCW/AEB. |
| `run_radar_aeb_scenarios.py` | Tự spawn xe, chạy batch scenario và ghi log. |

Config của batch test nằm tại:

```text
aeb/configs/radar_aeb_scenarios.yaml
```

## Kịch Bản Tự Động

### `clear_road_50`

- Ego: Tesla Model 3, 50 km/h.
- Không có xe mục tiêu.
- Mục tiêu: kiểm tra point mặt đường hoặc nhiễu radar không gây phanh nhầm.
- Kỳ vọng: không phanh, không va chạm.

### `ccrs_30`

- Ego: 30 km/h.
- Xe mục tiêu: đứng yên cùng làn.
- Khoảng cách bumper ban đầu: 28 m.
- Mục tiêu: kiểm tra radar cluster, TTC và phanh với vật cản tĩnh.
- Kỳ vọng: AEB phanh và không va chạm.

### `ccrm_50_20`

- Ego: 50 km/h.
- Xe mục tiêu: chạy 20 km/h cùng làn.
- Khoảng cách bumper ban đầu: 32 m.
- Mục tiêu: kiểm tra vận tốc tương đối âm và TTC với xe chạy chậm.
- Kỳ vọng: AEB phanh và không va chạm.

### `ccrb_40_to_0`

- Ego và xe mục tiêu ban đầu cùng chạy 40 km/h.
- Khoảng cách bumper ban đầu: 22 m.
- Sau 1,5 giây, xe mục tiêu phanh `1.0`.
- Mục tiêu: kiểm tra AEB khi nguy cơ chỉ xuất hiện sau một sự kiện động.
- Kỳ vọng: AEB phanh và không va chạm.

### `adjacent_stationary_30`

- Ego: 30 km/h.
- Xe mục tiêu: đứng yên ở làn kế bên, phía trước 18 m.
- Mục tiêu: kiểm tra hành lang quỹ đạo loại vật thể ngoài làn ego.
- Kỳ vọng: không phanh nhầm, không va chạm.

## Cách Chạy

Khởi động CARLA:

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Chạy toàn bộ batch:

```bash
cd /home/mvhoang/CARLA_0.9.11
python3.7 aeb/run_radar_aeb_scenarios.py
```

Chỉ chạy một case:

```bash
python3.7 aeb/run_radar_aeb_scenarios.py --scenario ccrs_30
```

Chọn tên thư mục log cố định:

```bash
python3.7 aeb/run_radar_aeb_scenarios.py --run-id baseline_01
```

Lặp mỗi scenario nhiều lần:

```bash
python3.7 aeb/run_radar_aeb_scenarios.py --repeat 5
```

Chạy điều khiển vận tốc bằng throttle/brake vật lý:

```bash
python3.7 aeb/run_radar_aeb_scenarios.py --control-mode physics
```

`deterministic` là chế độ mặc định và dùng `set_target_velocity` trước khi AEB
can thiệp. `physics` dùng bộ giữ tốc độ đơn giản để đánh giá gần động lực học
thật hơn; cần hiệu chỉnh thêm trước khi dùng làm số liệu chuẩn.

Runner tự:

1. Kiểm tra CARLA đang ở `Town04`.
2. Chuyển world sang synchronous mode với bước thời gian `0.05 s`.
3. Spawn ego, radar, collision sensor và xe mục tiêu.
4. Giữ đúng vận tốc scenario cho tới khi AEB bắt đầu override; từ thời điểm
   phanh, xe chạy hoàn toàn theo động lực học và lệnh brake của CARLA.
5. Chạy cùng `RadarAEBPipeline` với `test_brake_radar.py`, không tạo cửa sổ
   pygame hoặc đối tượng manual control.
6. Xóa actor sau mỗi scenario.
7. Khôi phục world settings ban đầu kể cả khi script gặp lỗi.

Case nguy hiểm kết thúc thành công khi AEB đã kích hoạt và tốc độ ego xuống
dưới `0,30 m/s`. Runner không tự tăng tốc xe trở lại sau điểm này.

Không chạy `manual_control.py`, `spawn_npc.py` hoặc client điều khiển world khác
song song với batch test, vì nhiều client cùng tick synchronous world sẽ làm
kết quả không xác định.

## Cấu Trúc Log

Mỗi lần chạy tạo một thư mục:

```text
aeb/logs/YYYYMMDD_HHMMSS/
```

Bên trong gồm:

```text
run_metadata.json
summary.csv
summary.json
aggregate_summary.csv
aggregate_summary.json
clear_road_50.csv
ccrs_30.csv
ccrm_50_20.csv
ccrb_40_to_0.csv
adjacent_stationary_30.csv
```

### Log Theo Tick

Mỗi file scenario có một dòng cho mỗi tick CARLA. Các cột quan trọng:

| Cột | Ý nghĩa |
| --- | --- |
| `elapsed_s` | Thời gian từ đầu scenario. |
| `ego_speed_kph` | Vận tốc thực tế của ego. |
| `ego_acceleration_mps2` | Gia tốc dọc từ CARLA; âm là giảm tốc. |
| `ego_jerk_mps3` | Đạo hàm theo thời gian của gia tốc dọc. |
| `ego_x_m`, `ego_y_m`, `ego_lane_id` | Vị trí và lane ID ground-truth của ego. |
| `target_speed_kph` | Vận tốc thực tế của xe mục tiêu. |
| `target_x_m`, `target_y_m`, `target_lane_id` | Vị trí và lane ID của target. |
| `center_distance_m` | Khoảng cách Euclid giữa tâm hai actor. |
| `bumper_gap_m` | Ground-truth khoảng cách dọc từ bumper ego tới bumper target; có dấu. |
| `lateral_offset_m` | Độ lệch ngang ground-truth của target so với ego. |
| `raw_points` | Tổng radar point của frame. |
| `path_candidates` | Point còn lại sau bộ lọc hành lang và mặt đường. |
| `clusters` | Số radar cluster đang được theo dõi. |
| `confirmed_clusters` | Số cluster đủ số frame xác nhận. |
| `target_distance_m` | Khoảng cách radar của cluster được AEB chọn. |
| `target_relative_velocity_mps` | Vận tốc tương đối; âm nghĩa là đang khép khoảng cách. |
| `ttc_s` | TTC của target; để trống khi TTC vô hạn. |
| `required_distance_m` | Khoảng cách dừng yêu cầu theo vận tốc hai xe. |
| `distance_margin_m` | Khoảng cách radar trừ khoảng cách dừng yêu cầu. |
| `aeb_state` | `NORMAL`, `WARNING`, `BRAKE` hoặc `RELEASE`. |
| `brake_cmd` | Lệnh phanh thực tế gửi tới ego. |
| `aeb_override` | `1` khi AEB đang giành quyền điều khiển phanh. |
| `collision_count` | Số callback collision đã nhận. |
| `control_mode` | `deterministic` hoặc `physics`. |

Trong giao diện tương tác, trạng thái `WARNING` hiển thị icon `!` màu vàng;
trạng thái `BRAKE` hiển thị icon `!` màu đỏ. Đây là tín hiệu HMI mô phỏng,
chưa bao gồm âm thanh cảnh báo.

### Log Tổng Kết

`summary.csv` và `summary.json` chứa:

- Kết quả `PASS` hoặc `FAIL`.
- AEB có phanh hay không.
- Có va chạm hay không.
- Thời điểm cảnh báo và thời điểm phanh đầu tiên.
- Vận tốc và ground-truth gap khi bắt đầu phanh.
- Khoảng cách tâm nhỏ nhất.
- Bumper gap nhỏ nhất cho các case cùng làn.
- TTC nhỏ nhất.
- Khoảng cách dừng yêu cầu và margin tại thời điểm phanh.
- Giảm tốc cực đại, jerk cực đại và vận tốc cuối.
- Tỷ lệ tick có target radar đã xác nhận.
- Số radar point, candidate và cluster lớn nhất.

`aggregate_summary.csv/json` nhóm các lần lặp theo scenario và ghi số lần
PASS, pass rate, brake rate, gap nhỏ nhất và thời điểm phanh trung bình.

Tiêu chí hiện tại:

- Case nguy hiểm: phải có `aeb_override = 1` và không collision.
- Bumper gap nhỏ nhất phải lớn hơn `min_stop_gap_m`, mặc định `0,5 m`.
- Case an toàn: không được có `aeb_override = 1` và không collision.
- Gia tốc và jerk đã được log; `0,25 s` đầu được bỏ qua khi tính cực trị để
  tránh transient do khởi tạo scenario.

## Kết Quả Sau Khi Giảm Độ Nhạy Phanh

Bộ log đầy đủ:

```text
aeb/logs/less_sensitive_20260605/
```

CARLA chạy trên `Town04`, synchronous mode `0,05 s/tick`. Core AEB dùng chung
cho UI và runner, track stale không được kích hoạt phanh, đồng thời quyết định
kết hợp TTC và khoảng cách dừng. Cả 5 case đều PASS:

| Scenario | Kết quả | Phanh | Collision | Thời điểm phanh | Tốc độ khi phanh | Bumper gap khi phanh | Bumper gap nhỏ nhất |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `clear_road_50` | PASS | Không | Không | -- | -- | -- | -- |
| `ccrs_30` | PASS | Có | Không | 1,60 s | 29,98 km/h | 12,32 m | 7,70 m |
| `ccrm_50_20` | PASS | Có | Không | 1,95 s | 49,96 km/h | 13,13 m | 8,51 m |
| `ccrb_40_to_0` | PASS | Có | Không | 2,50 s | 39,97 km/h | 15,90 m | 7,98 m |
| `adjacent_stationary_30` | PASS | Không | Không | -- | -- | -- | -- |

Khoảng cách tâm nhỏ nhất của xe ở làn kế bên là `3,51 m`; AEB không tạo
cluster trong hành lang ego và không phanh nhầm.

Bộ tuning thay đổi:

- `brake_ttc_s`: `1,8 s` xuống `1,5 s`.
- `response_time_s`: `0,35 s` xuống `0,20 s`.
- `ego_emergency_decel_mps2`: `7,0` lên `8,0 m/s²`.
- `stopping_distance_offset_m`: `2,0 m` xuống `1,0 m`.

So với bộ `improved_core_20260605_v2`, CCRs phanh muộn hơn `0,55 s`, CCRm
muộn hơn `1,00 s` và CCRb muộn hơn `0,20 s`. Cả ba vẫn không va chạm và còn
bumper gap tối thiểu gần `8 m`.

Bài repeat chọn lọc:

```text
aeb/logs/less_sensitive_repeat_20260605/
```

Kết quả `6/6 PASS`: `clear_road_50`, `ccrs_30` và
`adjacent_stationary_30` đều chạy hai lần. CCRs có bumper gap nhỏ nhất
`7,70 m`; hai lần đường trống và hai lần xe làn bên cạnh đều không phanh.
Mẫu này còn nhỏ, chưa đủ làm kết luận thống kê trong báo cáo.

Các thư mục `smoke_*`, `baseline_20260605`, `baseline_20260605_v2` và
`baseline_20260605_final` là log trong quá trình debug. Chúng ghi lại hai lỗi
đã được phát hiện:

- AEB nhả phanh khi TTC tăng trong quá trình giảm tốc.
- Ego bị ép vận tốc theo transform `(0,0,0)` trước tick đầu tiên và nhảy sang
  làn kế bên.

## Quy Trình Đọc Lỗi

1. `raw_points = 0`: kiểm tra radar mount, FOV hoặc sensor callback.
2. Có raw point nhưng `path_candidates = 0`: kiểm tra ground filter và corridor.
3. Có candidate nhưng `clusters = 0`: chỉnh `min_points` hoặc cluster tolerance.
4. Có cluster nhưng `confirmed_clusters = 0`: kiểm tra tracking và
   `confirm_frames`.
5. Có confirmed cluster nhưng không phanh: kiểm tra relative velocity, TTC và
   state machine.
6. Có phanh nhưng vẫn collision: kiểm tra ngưỡng TTC, độ trễ xác nhận và khả
   năng giảm tốc thực tế.

Binary AEB hiện bật `hold_brake_until_stopped`, vì vậy sau khi phanh khẩn cấp
đã kích hoạt, lệnh phanh được giữ tới khi ego gần dừng hẳn. Nếu tắt tùy chọn
này, cần đặc biệt kiểm tra hiện tượng TTC tăng trong lúc giảm tốc làm AEB nhả
phanh quá sớm.
