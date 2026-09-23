# Nhật Ký Thử Nghiệm Radar-Only AEB

## 1. Mục Đích

Tài liệu này lưu lại quá trình kiểm tra, phát hiện lỗi, sửa lỗi và chạy hồi quy
cho hệ thống radar-only AEB trên CARLA 0.9.11.

Mục tiêu thử nghiệm hiện tại:

- Dải vận tốc thiết kế chính: `50-80 km/h`.
- Đối tượng: ô tô chạy cùng chiều hoặc đứng yên.
- Môi trường: Town04, đường khô, tầm nhìn tốt, không có người đi bộ.
- Radar trước: tầm quét `100 m`, ngang `30°`, dọc `6°`, `2000 point/s`,
  chu kỳ `0,05 s`.
- Quyết định phanh: radar clustering, tracking, hành lang quỹ đạo, TTC và
  khoảng cách dừng.
- Điều khiển AEB: phanh nhị phân `0/1`; chưa dùng PID.

Đây là thử nghiệm phát triển, không phải kết quả chứng nhận Euro NCAP.

## 2. File Và Dữ Liệu

Các file chính:

```text
aeb/scripts/run_radar_aeb_scenarios.py
aeb/configs/radar_only_validation.yaml
aeb/configs/sensors.yaml
aeb/core/radar_aeb_pipeline.py
aeb/core/radar_object.py
aeb/core/target_selector.py
aeb/control/brake.py
```

Log đầy đủ được lưu cục bộ trong:

```text
aeb/logs/<run_id>/
```

Mỗi run mới gồm:

```text
config_snapshot/
run_metadata.json
summary.csv
summary.json
aggregate_summary.csv
aggregate_summary.json
<scenario>.csv
evidence/                  # chỉ có khi dùng --record-evidence
```

Thư mục `logs/` bị loại khỏi Git để tránh đẩy video và log lớn. Các kết luận
quan trọng được ghi lại trong tài liệu này.

## 3. Tiêu Chí PASS/FAIL

Case nguy hiểm:

- AEB phải kích hoạt.
- Không có collision.
- Khoảng cách bumper nhỏ nhất phải từ `0,5 m` trở lên.

Case an toàn:

- Không được kích hoạt AEB.
- Không có collision.

Case đường cong:

- Thỏa các điều kiện tương ứng ở trên.
- Độ lệch tâm làn tuyệt đối không vượt `1,25 m`.

Các case đường cong dùng bộ lane-follow của test runner để xe đi đúng quỹ đạo.
Bộ lane-follow không tham gia vào quyết định phanh AEB.

## 4. Quá Trình Làm - Sai - Sửa

### 4.1. Baseline Ban Đầu

Run:

```text
radar_only_baseline_det_20260606
radar_only_baseline_physics_20260606
```

Kết quả:

- Deterministic: `15/15 PASS`.
- Physics: `15/15 PASS`.

Vấn đề phát hiện khi đọc log:

- Xe mục tiêu của case đang chạy bắt đầu gần như đứng yên.
- Case `ccrb_40_to_0` kích hoạt AEB ở `0,5 s`, trước thời điểm target được yêu
  cầu phanh ở `1,5 s`.
- Ego đặt 50 km/h nhưng chỉ duy trì khoảng 45 km/h.

Kết luận: kết quả PASS chưa hợp lệ để đánh giá AEB vì test runner khởi tạo vận
tốc sai.

### 4.2. Sửa Khởi Tạo Vận Tốc

Thay đổi:

- Spawn ego và target trước.
- Đặt vận tốc ban đầu cho cả hai xe trong cùng giai đoạn khởi tạo.
- Đặt lại vận tốc ngay trước mốc `t=0`.

Kết quả kiểm tra:

- `ccrb_40_to_0` cảnh báo ở khoảng `2,1 s`.
- AEB phanh ở khoảng `2,7 s`.
- AEB không còn kích hoạt trước sự kiện target phanh.

### 4.3. Mở Rộng Lên 50-80 km/h

Run đầu:

```text
radar_only_validation_det_v1_20260606
```

Kết quả: `9/16 PASS`, có 7 case collision.

Quan sát quan trọng:

- AEB đã phanh đúng và giảm tốc với khoảng `8,7-9,0 m/s²`.
- Trước lần dừng đầu tiên, xe còn khoảng hở `6-9 m`.
- Sau khi AEB chuyển sang `RELEASE`, runner lại ép xe trở về vận tốc scenario.
- Ego tăng tốc lần hai và đâm target.

Nguyên nhân: lỗi test harness, không phải lỗi radar hoặc logic AEB.

### 4.4. Khóa Bộ Giữ Tốc Sau Khi AEB Kích Hoạt

Thay đổi:

- Biến `brake_activated` được chốt sau lần AEB đầu tiên.
- Bộ giữ tốc không được phép tăng tốc ego trở lại trong phần còn lại của
  scenario.
- Scenario kết thúc sau khi ego giữ trạng thái dừng đủ số tick yêu cầu.

Run lại:

```text
radar_only_validation_det_v2_20260606
```

Kết quả: `16/16 PASS`, không đổi ngưỡng TTC hoặc khoảng cách dừng.

### 4.5. Hiệu Chỉnh Test Bench Physics

Vấn đề:

- Throttle bị giới hạn ở `0,7`.
- Case 80 km/h thực tế giảm xuống khoảng 60-77 km/h.
- Controller chuyển ga/phanh liên tục khi vận tốc dao động sát setpoint.

Thay đổi:

- PI nhỏ cho bộ giữ vận tốc của runner.
- Feedforward phụ thuộc vận tốc.
- Throttle tối đa `1,0`.
- Deadband vận tốc `0,5 m/s`; trong deadband chỉ giảm ga, không phanh.

Kết quả kiểm tra đường trống:

| Setpoint | Vận tốc trung bình ổn định |
| ---: | ---: |
| 50 km/h | 49,7 km/h |
| 65 km/h | 64,1 km/h |
| 80 km/h | 78,2 km/h |

Đây là controller của test bench, không phải PID phanh AEB.

### 4.6. Ghi Ảnh Và Video

Lỗi đầu tiên:

- Simulation chạy nhanh hơn callback ghi ảnh.
- Video 4,35 giây chỉ có 5 frame.

Thay đổi:

- Khi bật `--record-evidence`, runner đợi camera hoàn thành đúng world frame.
- Camera ghi `960x540`, `20 FPS`.
- Sau khi tạo MP4, chỉ giữ video và ảnh sự kiện; frame trung gian được xóa.

Ảnh được lưu tại:

- `first_warning.png`
- `first_brake.png`
- `minimum_gap.png`

`events.json` liên kết ảnh với frame, thời gian, vận tốc, gap, TTC và trạng
thái AEB.

### 4.7. Kiểm Tra Đường Cong

Đoạn thử:

- Town04, `spawn_index: 208`.
- Đường cao tốc nhiều làn, thay đổi hướng khoảng `22°` trong 60 m đầu.

Bốn scenario:

- Đường cong trống ở 65 km/h.
- Đường cong trống ở 80 km/h.
- Xe đứng yên làn kế bên trên đường cong.
- Xe đứng yên cùng làn trên đường cong.

Kết quả ban đầu:

- `4/4 PASS`.
- Lệch tâm làn tối đa `0,40 m`.
- Sai lệch hướng tối đa dưới `4°`.
- Xe làn bên không gây cảnh báo hoặc phanh.
- Xe cùng làn được phanh, khoảng hở nhỏ nhất `5,86 m`.

### 4.8. Cut-In, Cut-Out Và Nhiều Xe

Runner được mở rộng từ một target cố định sang danh sách actor có role:

- Mỗi actor có vị trí làn, vận tốc, trạng thái hazard và sự kiện chuyển làn.
- Radar cluster được ghép với actor ground truth gần nhất trong cổng `6 m`.
- Log ghi actor được radar chọn và kiểm tra actor tại thời điểm phanh.
- Scenario có thể yêu cầu hazard ban đầu/cuối cùng cùng hoặc khác làn ego.
- Pipeline được tách nhẹ theo hướng object-list: CARLA radar point được lọc,
  gom cụm và tracking thành `RadarObjectList`, sau đó target selector mới chọn
  object AEB. Hành vi chọn target giữ nguyên so với baseline: object confirmed,
  không stale, TTC hữu hạn thấp nhất, rồi tới khoảng cách gần nhất.

Baseline đầu tiên có một case cut-out 65/35 km/h bị đánh dấu FAIL vì AEB vẫn
phanh. Khi đọc log tại tick phanh:

- Tâm target đã lệch ngang khoảng `2,10 m`.
- Điểm đại diện radar vẫn chỉ lệch khoảng `0,98 m`.
- Hành lang phanh rộng `1,25 m`.
- Mép trong của thân xe vẫn còn chồng lấn hành lang va chạm.

Đây không phải track cũ hoặc radar point ma. Kỳ vọng “không phanh” ban đầu là
không an toàn. Không giảm độ nhạy của AEB; thay vào đó tách thành:

- Cut-out sớm: xe rời hành lang trước khi nguy hiểm, không được phanh.
- Cut-out muộn: thân xe còn lấn hành lang, phải phanh.

Một lỗi trình bày bằng chứng cũng được phát hiện: ảnh `minimum_gap` của
cut-out sớm lấy khoảng cách dọc âm sau khi ego đã đi qua xe ở làn khác. Bộ ghi
bằng chứng hiện tuân theo `report_minimum_gap: false`, nên không còn lưu ảnh
hoặc event này cho case không còn cùng làn.

## 5. Regression Cuối Ngày 6/6/2026

### 5.1. Đoạn Thẳng

Run:

```text
radar_only_regression_det_3x_20260606
radar_only_regression_physics_3x_20260606
```

Kết quả:

- Deterministic: `48/48 PASS`.
- Physics: `48/48 PASS`.
- Collision: `0`.
- Phanh nhầm trong case an toàn: `0`.
- Khoảng hở nhỏ nhất deterministic: `4,92 m`.
- Khoảng hở nhỏ nhất physics: `4,69 m`.

Kết quả physics theo nhóm:

| Nhóm scenario | Số lượt | Kết quả | Khoảng hở nhỏ nhất |
| --- | ---: | ---: | ---: |
| Đường trống 50/65/80 | 9 | 9 PASS, không phanh | Không áp dụng |
| Xe đứng yên cùng làn | 9 | 9 PASS | 5,07 m |
| Xe trước chạy chậm | 9 | 9 PASS | 8,30 m |
| Xe trước phanh gấp | 9 | 9 PASS | 4,69 m |
| Xe đứng yên làn bên | 9 | 9 PASS, không phanh | Không áp dụng |
| Xe trước chạy nhanh hơn | 3 | 3 PASS, không phanh | 31,11 m |

### 5.2. Đường Cong

Run:

```text
radar_only_curve_regression_3x_20260606
```

Kết quả:

- `12/12 PASS`.
- Không collision.
- Không phanh nhầm ở đường cong trống hoặc xe làn bên.
- `curve_ccrs_65`: khoảng hở nhỏ nhất `5,865 m`.
- Lệch tâm làn tối đa trong các lượt kiểm tra khoảng `0,40 m`.

### 5.3. Tổng Hợp

Tổng regression dùng để kết luận:

```text
108/108 PASS
0 collision
0 false brake trong các case an toàn đã định nghĩa
```

Không dùng các run debug trước khi sửa test harness để tính pass rate cuối.

Sau khi tích hợp lane-follow, config snapshot và metadata, toàn bộ 20 scenario
physics được chạy lại bằng đúng mã cuối tại:

```text
aeb/logs/radar_only_final_all20_20260607/
```

Kết quả tích hợp: `20/20 PASS`, không collision, không false brake và khoảng
hở nhỏ nhất `4,69 m`.

### 5.4. Regression Động Và Nhiều Xe Ngày 07/06/2026

Run lặp:

```text
aeb/logs/radar_only_dynamic_regression_3x_20260607/
```

Kết quả:

| Scenario | Số lượt | Phanh | Khoảng hở nhỏ nhất |
| --- | ---: | ---: | ---: |
| `cut_in_65_45` | 3/3 PASS | 100% | 10,478 m |
| `cut_in_80_50` | 3/3 PASS | 100% | 12,872 m |
| `cut_out_65_35` | 3/3 PASS | 0% | Không áp dụng |
| `cut_out_late_65_35` | 3/3 PASS | 100% | 11,838 m |
| `cut_out_80_50` | 3/3 PASS | 0% | Không áp dụng |
| `multi_adjacent_decoy_65` | 3/3 PASS | 100% | 11,526 m |
| `multi_two_leads_80` | 3/3 PASS | 100% | 5,267 m |

Tổng nhóm này: `21/21 PASS`, `0 collision`. Radar target ghép đúng hazard
`100%` trong các tick có target của bảy scenario; hai case nhiều xe đều chọn
đúng actor tại thời điểm phanh.

Toàn bộ 27 scenario physics được chạy lại một lượt bằng đúng mã cuối tại:

```text
aeb/logs/radar_only_final_all27_20260607/
```

Kết quả tích hợp: `27/27 PASS`, `0 collision`, không phanh nhầm trong các case
an toàn đã định nghĩa. Run metadata xác nhận CARLA client/server `0.9.11`,
map `Town04`, synchronous step `0,05 s`.

## 6. Bằng Chứng Hình Ảnh

Đoạn thẳng:

```text
aeb/logs/radar_only_evidence_final_20260606/
```

Video:

- `ccrs_80`: 4,30 giây, 86 frame.
- `ccrb_80_to_0`: 5,70 giây, 114 frame.
- `adjacent_stationary_80`: 5,95 giây, 119 frame.

Đường cong:

```text
aeb/logs/radar_only_curve_evidence_final_20260606/
```

Video:

- `curve_ccrs_65`: 3,40 giây, 68 frame.
- `curve_adjacent_stationary_65`: 4,95 giây, 99 frame.

Cut-in, cut-out và nhiều xe:

```text
aeb/logs/radar_only_dynamic_evidence_v2_20260607/
```

Video:

- `cut_in_80_50`: 5,75 giây; có ảnh cảnh báo, phanh và khoảng hở nhỏ nhất.
- `cut_out_65_35`: 6,95 giây; có cảnh báo nhưng không phanh, không lưu gap dọc
  sau khi target đã sang làn khác.
- `cut_out_late_65_35`: 4,40 giây; phanh ở khoảng `2,30 s`.
- `multi_adjacent_decoy_65`: 5,05 giây; phanh theo actor `lead`, không chọn xe
  mồi ở làn trái.

## 7. Cách Chạy Lại

Regression deterministic:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode deterministic \
  --repeat 3 \
  --run-id radar_only_det_repeat
```

Regression physics, gồm cả case đường cong:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --repeat 3 \
  --run-id radar_only_physics_repeat
```

Ghi video một scenario:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --scenario ccrs_80 \
  --record-evidence \
  --run-id ccrs_80_video
```

## 8. Phạm Vi Kết Luận

Kết quả hiện tại cho phép kết luận:

> Radar-only AEB đã hoạt động ổn định trong bộ scenario có kiểm soát ở
> 50-80 km/h trên đoạn thẳng và một đoạn cong của Town04, gồm một xe mục tiêu,
> cut-in/cut-out và hai cấu hình nhiều xe, trong thời tiết tốt và cảm biến
> không bị lỗi.

Chưa được phép suy rộng kết luận này sang:

- Mật độ giao thông cao, mục tiêu bị che khuất hoặc nhiều xe chuyển làn đồng
  thời.
- Cut-in/cut-out với quỹ đạo, góc nhập làn và vận tốc ngoài các case đã định
  nghĩa.
- Đường cong gắt hơn, dốc lớn hoặc giao lộ.
- Hộ lan, tường và vật thể tĩnh có hình học phức tạp ở nhiều vị trí.
- Mưa, sương mù, mặt đường trơn.
- Nhiễu, mất frame hoặc sai số radar có chủ đích.
- Vận tốc trên 80 km/h.

## 9. Bước Tiếp Theo

Trước khi chuyển hẳn sang fusion:

1. Thêm nhiều vị trí guardrail, tường và dốc trên Town04.
2. Mở rộng cut-in/cut-out theo nhiều gap, góc nhập làn và vận tốc.
3. Thêm che khuất và ba xe trở lên để kiểm tra đổi target.
4. Mô phỏng mất point, mất frame và nhiễu vận tốc radar.
5. Chạy tối thiểu 20 lần cho các case biên gần ngưỡng phanh.

Sau khi các nhóm trên ổn định, giữ radar-only làm baseline và bắt đầu
camera-radar fusion.
