# Nhật Ký Thử Nghiệm

File này chỉ ghi tóm tắt các lần thử nghiệm quan trọng, lỗi đã gặp và quyết định
sửa chính. Log thô, ảnh và video vẫn nằm trong `logs/`. Tài liệu cũ được giữ ở
`docs/history/legacy_docs/RADAR_ONLY_EXPERIMENT_LOG.md`.

## Quy Ước Về Jerk Trong CARLA

Các giá trị jerk trong log, ví dụ `ego_jerk_mps3` và
`maximum_abs_jerk_mps3`, là **CARLA raw jerk**. Chúng được tính từ gia tốc dọc raw
theo từng tick mô phỏng:

```text
jerk = delta(longitudinal_acceleration) / delta_time
```

Con số này có thể có spike lớn khi brake command thay đổi nhanh, khi xe bắt đầu
phanh hoặc vừa dừng. Vì vậy:

- dùng jerk raw chủ yếu để so sánh tương đối giữa các thuật toán trong cùng bộ
  test;
- không coi giá trị jerk raw này là jerk tuyệt đối của xe thật;
- khi đưa bảng so sánh vào báo cáo, cần ghi chú rõ là **CARLA raw jerk**;
- hướng nâng cấp sau là lọc gia tốc, tính thêm p95/RMS jerk và mô phỏng actuator
  phanh.

## 2026-06-17 - Bổ Sung Lọc Xe Bị Che Khuất Khi Thu YOLO Dataset

Quan sát:

- Một số frame preview có xe bị che khuất nhiều nhưng vẫn được gán label do bộ
  lọc v6 đã nới rất thoáng để bắt được xe xa trong tầm 100 m.
- Nếu chỉ tăng `min_visible_ratio` sẽ dễ mất xe xa/nhỏ nhưng nhìn rõ.

Sửa:

- Giữ `min_visible_ratio` thấp để không bỏ sót xe xa.
- Thêm luật lọc che khuất mạnh:
  - Nếu `visible_ratio < 0.15`, label chỉ được giữ khi phần nhìn thấy vẫn đủ lớn.
  - Điều kiện đủ lớn hiện tại: `visible_pixels >= 300` hoặc fitted box của phần
    nhìn thấy có diện tích `>= 1000 px`.
- File train thủ công: `scripts/train_yolo_v6.sh`.
- Thêm khử box chồng nhau trước khi ghi YOLO label:
  - Giữ box gần camera hơn.
  - Loại box phía sau nếu `IoU >= 0.55` hoặc nếu một box nằm trong box còn lại
    với tỷ lệ `>= 0.75`.

Ý nghĩa:

- Xe chỉ lộ một mẩu nhỏ sau vật cản sẽ bị bỏ khỏi label.
- Xe gần bị che một phần nhưng phần nhìn thấy vẫn lớn vẫn được giữ.
- Xe xa/nhỏ nhưng không bị che nhiều vẫn được giữ nhờ `visible_ratio` đủ tốt.

## 2026-06-17 - Thu Dataset V7 Same-Lane

Mục tiêu:

- Giảm nhiễu từ xe làn bên khi train YOLO giai đoạn đầu.
- Scene chỉ spawn xe cùng làn phía trước ego, không spawn NPC random ngoài làn.
- Label vẫn là `car`, nhưng vì scene sạch nên gần như toàn bộ label là xe cùng
  làn.

Config chính:

- File: `configs/dataset_collection_v7_same_lane.yaml`.
- Dataset root: `dataset_v7_same_lane`.
- `number_of_vehicles = same_lane_vehicles_ahead = 4`.
- Khoảng cách xe cùng làn ban đầu: 30 m, 65 m, 100 m, 135 m.
- Nhịp lưu: 40 frame/ảnh.
- Vẫn dùng filter che khuất và khử box chồng nhau đã bổ sung cho v6.

Kinh nghiệm khi thu:

- Session dài 60 ảnh tạo nhiều frame empty ở đoạn cuối vì xe phía trước đi khỏi
  vùng nhìn thấy.
- Chốt cách thu tốt hơn: nhiều session ngắn, khoảng 50 ảnh/session.
- Đã thêm `scripts/collect_v7_same_lane_batch.sh` để tự động chạy nhiều session
  ngắn.

Kết quả hiện tại:

| Split | Ảnh | Box | Positive | Empty | Empty ratio | Session | Same-lane box |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 764 | 887 | 576 | 188 | 24.6% | 13 | 887 |
| val | 200 | 257 | 169 | 31 | 15.5% | 4 | 257 |
| test | 150 | 201 | 123 | 27 | 18.0% | 3 | 201 |

Phân bố khoảng cách:

- Train: 6.5-100.0 m, median 29.6 m.
- Val: 6.8-100.0 m, median 29.8 m.
- Test: 6.9-99.2 m, median 29.5 m.

Gallery kiểm label:

- `outputs/dataset_v7_same_lane_box_check`.
- Tổng 1114 ảnh, 1345 box.

Nhận xét nhanh:

- Toàn bộ box hiện tại là xe same-lane do script spawn chủ động.
- Ảnh sạch hơn v6 natural, ít nhiễu xe làn bên.
- Đây là bộ v7 mini/medium để kiểm chất lượng và train thử. Nếu dùng làm bộ
  chính thức, nên thu bù lên khoảng train/val/test = 1500/300/200 ảnh.

## 2026-06-17 - Hoàn Thành Dataset V7 Same-Lane Full

Sau khi kiểm thủ công bản mini/medium đạt yêu cầu, đã thu bù thêm để đạt bộ full
cho train thử YOLO:

| Split | Ảnh | Box | Positive | Empty | Empty ratio | Session | Same-lane box |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 1505 | 1872 | 1186 | 319 | 21.2% | 28 | 1872 |
| val | 300 | 379 | 251 | 49 | 16.3% | 6 | 379 |
| test | 200 | 264 | 164 | 36 | 18.0% | 4 | 264 |

Audit:

- Lệnh: `../venv/bin/python scripts/train_yolo_pipeline.py --config configs/model_training.yaml --audit-only`.
- Kết quả: `Data đạt toàn bộ quality gate`.
- Gallery kiểm label: `outputs/dataset_v7_same_lane_box_check`.
- Thống kê metadata: `outputs/dataset_v7_same_lane_stats.json`.

Đa dạng xe:

- Train có 21 blueprint xe khác nhau.
- Val có 14 blueprint xe khác nhau.
- Test có 11 blueprint xe khác nhau.
- Metadata cũ của v7 chưa lưu `color`, nên chưa thống kê màu chính xác từ file
  metadata được. Collector đã được cập nhật để các lần thu sau lưu thêm trường
  `color`.

## 2026-06-10 - Thêm Tool Minh Họa Sensor Coverage

Đã thêm `scripts/visualize_sensor_coverage.py` để vẽ tầm camera/radar trên đúng
`vehicle.tesla.model3` theo `configs/sensors.yaml`.

Output dự kiến:

- `outputs/sensor_coverage/near_top_view.png`
- `outputs/sensor_coverage/far_top_view.png`
- `outputs/sensor_coverage/near_side_view.png`
- `outputs/sensor_coverage/far_side_view.png`
- `outputs/sensor_coverage/sensor_coverage_metadata.json`

Mục đích: kiểm chứng vị trí gắn camera sau kính lái, radar ở mũi xe và tạo hình
minh họa cho báo cáo.

Cập nhật sau khi kiểm tra hình chiếu cạnh:

- Camera chỉnh về `x=0.43 m`, `z=1.35 m` để lùi vào sát mặt trong kính lái hơn,
  theo kiểm tra từ `near_side_view.png`.
- Radar chỉnh về `x=2.53 m`, `z=0.48 m` để nhô trước bbox mũi xe khoảng
  `10.5 cm`. Trước đó `x=2.45 m` chỉ nhô khoảng `2.5 cm`, khi xe áp sát/collision
  nhẹ với lan can vẫn có thể còn báo khoảng `8-9 cm`.
- Ảnh minh họa coverage khuyến nghị chụp trên `Town06 --spawn-index 0` để góc
  cạnh thoáng hơn, không bị tường/cây che như một số vị trí trên `Town04`.

## 2026-06-10 - Smoke Test Sau Refactor Cấu Trúc Code

Lệnh chạy:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/radar_only_validation.yaml \
  --control-mode physics \
  --scenario clear_road_50 \
  --scenario ccrs_50 \
  --run-id structure_refactor_smoke_20260610 \
  --load-map
```

Kết quả:

- `clear_road_50`: PASS, không phanh sai.
- `ccrs_50`: PASS, có phanh, không va chạm, `min_gap=6.943 m`.
- Log: `logs/structure_refactor_smoke_20260610`.

Ý nghĩa: refactor thư mục code không làm vỡ pipeline radar-only cơ bản.

## Radar-Only Regression Trước Refactor

Các nhóm đã từng chạy:

- Đường trống.
- CCRs, CCRm, CCRb.
- Adjacent lane.
- Đường cong.
- Cut-in, cut-out.
- Nhiều xe target.

Kết quả đã đạt trong mô phỏng có kiểm soát:

- Baseline 27 scenario 50-80 km/h: `27/27 PASS`.
- Nhóm động/nhiều xe chạy lặp ba lần: `21/21 PASS`.
- Unit test logic sau refactor: `28/28 PASS`.

Các kết quả này là bằng chứng nội bộ cho project, không phải chứng nhận NCAP.

## Các Lỗi Thiết Kế Đã Gặp

- Tính TTC trên toàn bộ radar point gây phanh nhầm khi lùi hoặc khi radar nhìn
  thấy mặt đường/tường/cây.
- Point đơn lẻ gây phanh nhạy quá mức.
- Radar quét rộng trong lúc cua khiến vật thể ngoài quỹ đạo bị coi là nguy hiểm.
- `-opengl` làm cửa sổ pygame/manual control render lỗi trên máy hiện tại.

## Các Sửa Chính

- Không phanh khi xe đang lùi với AEB phía trước.
- Thêm lọc độ cao và hành lang dự đoán.
- Chuyển từ point-level TTC sang radar object list.
- Thêm clustering/tracking và yêu cầu object được xác nhận qua nhiều frame.
- Tách code theo `ui/`, `scripts/`, `core/`, `perception/`, `control/`.

## 2026-06-10 - Sửa Live Scenario Trong UI Radar-Only

Vấn đề:

- Khi chạy `ui/radar_aeb_view.py --scenario ...`, target có thể không xuất hiện
  đúng trước ego dù terminal báo đã spawn.
- Nguyên nhân là UI dùng lại ego do `manual_control.py` spawn ngẫu nhiên, sau đó
  `set_transform()` ego sang spawn scenario nhưng chưa đợi CARLA cập nhật frame.
  Vì vậy target được tính theo vị trí ego cũ, còn khi đo lại thì ego đã ở vị trí
  mới, làm gap/lateral sai.

Sửa:

- Sau khi reset ego, spawn target và dọn actor scenario cũ đều sync thêm một
  frame CARLA.
- Thêm `ccrs_60_demo_150` để demo trực quan: target đứng yên cách khoảng 150 m,
  cùng làn, ego có đoạn chạy ổn định 60 km/h trước khi vào vùng radar.
- Khi chạy live scenario, UI tự chuyển camera trái sang `wide_chase`, vẽ nhãn
  target và đường nối đỏ trong CARLA. Có thể dùng `--scenario-camera manual` nếu
  muốn giữ nguyên camera manual_control.

Smoke test:

- `ccrs_60_demo_150`: dùng cho demo quan sát trực tiếp trên đoạn Town04 rộng.
- `ccrs_65`: `initial bumper_gap=59.7 m`, `lateral=-0.0 m`.
- `ccrs_60_gap_200`: `initial bumper_gap=200.2 m`, `lateral=0.0 m`.
- `py_compile`: PASS.
- Unit test: `28/28 PASS`.

## 2026-06-10 - Khóa Ego Dừng Sau Khi AEB Phanh Trong UI Scenario

Vấn đề:

- Trong live scenario, ego được controller giữ tốc độ mục tiêu, ví dụ 60 km/h.
- Sau khi AEB phanh và state machine nhả phanh, controller lại đạp ga để quay về
  tốc độ mục tiêu, làm xe nhấp nhả phanh/ga và khó đo khoảng cách dừng cuối.

Sửa:

- Mặc định, khi AEB vào trạng thái `BRAKE`, live scenario sẽ latch ego sang chế
  độ dừng: throttle bằng 0, giữ brake bằng 1.0 cho tới khi xe dừng.
- UI hiển thị `Stop latch` và `Final gap` để phục vụ đánh giá thủ công.
- Có thể quay về hành vi cũ bằng `--keep-driving-after-aeb`.

Smoke test sau sửa:

- `ccrs_65`: latch tại `reason=ttc_below_brake_threshold`.
- `ccrs_65`: `AEB final stop: gap=1.98 m`, `lateral=-0.01 m`.

## 2026-06-10 - Giảm Khựng Đầu Live Scenario

Quan sát:

- Lag chủ yếu xảy ra lúc đầu khi xe ego/target vừa hiện ra.
- Khi bắt đầu phanh thì lại mượt hơn, nên nguyên nhân chính không nằm ở thuật
  toán AEB mà ở thao tác setup live scenario: reset ego, spawn target, sync frame
  CARLA và respawn camera chase của `manual_control`.

Sửa:

- Thêm warm-up mặc định 1 giây sau khi spawn xe/đổi camera; ego vẫn giữ phanh
  trong thời gian này.
- Sau warm-up mới set vận tốc ego/target và bắt đầu tính `elapsed_s` của scenario.
- Có thể chỉnh bằng `--scenario-warmup-s`, hoặc dùng `--scenario-camera manual`
  để tránh respawn camera chase nếu máy bị lag.

## 2026-06-15 - Thu Bộ Dataset YOLO Ground Truth Đầu Tiên

Mục tiêu:

- Thu bộ dữ liệu camera theo cấu hình cảm biến hiện tại để train model YOLO nhỏ
  cho bài toán car-to-car trên Town04.
- Ưu tiên xe cùng làn phía trước ego, có khoảng cách 6-80 m.
- Có thêm một tỷ lệ nhỏ ảnh empty trong `train`, `val`, `test` để model không
  học rằng ảnh nào cũng phải có xe.

Các session đã thu:

| Split | Session | Số ảnh | Số box | Ghi chú |
| --- | --- | ---: | ---: | --- |
| train | `town04_train_20260615_01` | 500 | 1336 | nhiều xe cùng làn |
| train | `town04_train_20260615_02` | 500 | 1353 | nhiều xe cùng làn |
| train | `town04_train_20260615_03` | 500 | 1389 | có thêm negative tự nhiên |
| val | `town04_val_20260615_01` | 100 | 324 | positive |
| val | `town04_val_20260615_02` | 180 | 933 | positive |
| val | `town04_val_empty_20260615_01` | 20 | 0 | empty |
| test | `town04_test_20260615_01` | 100 | 346 | positive |
| test | `town04_test_20260615_02` | 90 | 271 | positive |
| test | `town04_test_empty_20260615_01` | 10 | 0 | empty |

Kết quả tổng:

| Split | Ảnh | Box | Positive | Negative | Session | Empty ratio | Near-dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 1500 | 4078 | 1363 | 137 | 3 | 9.1% | 9.2% |
| val | 300 | 1257 | 280 | 20 | 3 | 6.7% | 5.0% |
| test | 200 | 617 | 190 | 10 | 3 | 5.0% | 1.0% |

Phân bố khoảng cách:

- Train: 6.2-80.0 m, median 36.4 m, 3218 box cùng làn.
- Val: 6.6-79.9 m, median 41.1 m, 1122 box cùng làn.
- Test: 6.8-79.9 m, median 38.6 m, 583 box cùng làn.

Audit:

- Lệnh: `../venv/bin/python scripts/train_yolo_pipeline.py --audit-only`.
- Kết quả: `Data đạt toàn bộ quality gate`.
- Dataset nằm tại: `dataset_v3`.
- Dung lượng hiện tại: khoảng 1.7 GB.

Kiểm tra thủ công:

- Đã mở nhanh preview train/val/test và một ảnh empty.
- Box bám xe đúng theo ground truth CARLA.
- Có artifact chấm đen trên vùng trời từ render CARLA, nhưng không nằm trên nhãn
  xe; cần theo dõi thêm khi train nếu model học nhiễu nền.

## 2026-06-15 - Pilot Dataset V4 Sau Khi Giảm Xe Cùng Làn

Lý do:

- Bộ `dataset_v3` có nhiều ảnh các xe nối thành một hàng dài, dễ làm dữ liệu
  bị thiên lệch.
- Ảnh liên tiếp vẫn hơi giống nhau dù trước đó đã lưu cách 5-10 frame.

Thay đổi config:

- `dataset.root`: `aeb/dataset_v4`.
- `same_lane_vehicles_ahead`: giảm từ 10 xuống 4.
- `same_lane_first_distance_m`: 30 m.
- `same_lane_spacing_m`: 35 m.
- `same_lane_following_distance_m`: 12 m.
- `save_interval_frames_min/max`: 20/20 frame.

Pilot đã chạy:

- Lệnh: `../venv/bin/python -u scripts/collect_yolo_dataset.py --split train --session-id town04_train_v4_pilot_20260615_01 --max-samples 120 --seed 20261520 --no-window`.
- Kết quả: 120 ảnh, 280 box, 117 positive, 3 negative.
- Trung bình: 2.33 box/ảnh.
- Khoảng cách: 6.5-79.8 m, median 35.8 m.
- Box từ xe cùng làn được spawn chủ động: 112/280.

Nhận xét nhanh:

- Preview không còn kiểu đoàn 7-10 xe nối đuôi trong hầu hết frame.
- Có nhiều bố cục hơn: xe cùng làn, xe làn bên, xe ở xa, một ít negative.
- Nhịp 20 frame làm ảnh khác nhau rõ hơn nhưng thời gian thu lâu hơn.
- Artifact chấm đen trên trời vẫn còn, cần cân nhắc nếu ảnh hưởng training.

Cập nhật sau pilot:

- Vì CARLA dataset collector đang chạy synchronous với `fixed_delta_seconds=0.05`
  tương đương 20 FPS, nhịp 2 giây/ảnh tương ứng 40 frame/ảnh.
- Config thu full `dataset_v4` được đổi sang `save_interval_frames_min/max` =
  `40/40` để ảnh thưa nhau hơn pilot.

## 2026-06-16 - Thu Full Dataset V5

Lý do:

- Muốn giữ `dataset_v4` làm pilot và tạo bộ mới sạch hơn là `dataset_v5`.
- Ảnh cần thưa hơn nữa: 2 giây/ảnh, tương ứng 40 frame/ảnh ở synchronous 20 FPS.
- Giảm hiện tượng xe nối đuôi thành một hàng dài như `dataset_v3`.

Cấu hình chính:

- `dataset.root`: `aeb/dataset_v5`.
- `same_lane_vehicles_ahead`: 4 mặc định; có thêm session 2 xe cùng làn và
  session traffic tự nhiên không ép xe cùng làn.
- `same_lane_first_distance_m`: 30 m.
- `same_lane_spacing_m`: 35 m.
- `save_interval_frames_min/max`: `40/40`.

Các nhóm session:

- Train: pilot, same-lane 4 xe, same-lane 2 xe, natural traffic, empty và các
  session bù instance.
- Val: same-lane 4 xe, same-lane 2 xe, empty.
- Test: same-lane 4 xe, same-lane 2 xe, empty.

Kết quả tổng:

| Split | Ảnh | Box | Positive | Negative | Session | Empty ratio | Near-dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 2300 | 3051 | 1861 | 439 | 8 | 19.1% | 2.2% |
| val | 300 | 355 | 227 | 73 | 3 | 24.3% | 3.7% |
| test | 200 | 295 | 162 | 38 | 3 | 19.0% | 4.0% |

Phân bố khoảng cách:

- Train: 6.1-80.0 m, median 43.5 m, 930 box từ xe cùng làn được spawn chủ động.
- Val: 6.6-80.0 m, median 38.3 m, 134 box cùng làn.
- Test: 6.0-79.7 m, median 39.3 m, 103 box cùng làn.

Audit:

- Lệnh audit dùng root `aeb/dataset_v5`.
- Kết quả: `Data đạt toàn bộ quality gate`.
- `dataset_v5/dataset.yaml` đã được tạo.
- Dung lượng: khoảng 2.2 GB.
- Preview: 2800 ảnh.

Nhận xét nhanh:

- Bộ v5 thưa hơn rõ so với v3/v4, near-duplicate thấp.
- Không còn quá nhiều ảnh đoàn xe dài nối đuôi nhau.
- Có nhiều cảnh 1-3 xe, xe làn bên, xe xa và empty.
- Artifact chấm đen vẫn chủ yếu nằm ở bầu trời, được xem như nhiễu nền camera.

## 2026-06-16 - Thu Dataset V6 Với Filter Label Thoáng Hơn

Lý do:

- Khi kiểm `dataset_v5`, một số xe nhìn thấy được trong ảnh chưa có label vì
  filter visible/box còn chặt.
- Mục tiêu v6 là ưu tiên không bỏ sót xe trong vùng quan tâm của radar-camera
  fusion, khoảng 100 m phía trước, có buffer lên 110 m.

Thay đổi config so với v5:

- `dataset.root`: `aeb/dataset_v6`.
- `max_distance_m`: 110.0.
- `min_box_width_px`: 5.
- `min_box_height_px`: 4.
- `min_box_area_px`: 25.
- `max_truncation`: 0.85.
- `depth_tolerance_m`: 2.5.
- `min_visible_pixels`: 8.
- `min_visible_ratio`: 0.03.
- Giữ nhịp lưu 40 frame/ảnh và cấu hình traffic/spacing như v5.

Pilot:

- `town04_train_v6_pilot_20260616_01`: 120 ảnh, 264 box.
- Khoảng cách label đạt 6.1-98.9 m, median 46.1 m.
- Preview không thấy box rác rõ ràng; xe xa/làn bên được giữ tốt hơn v5.

Kết quả full:

| Split | Ảnh | Box | Positive | Negative | Session | Empty ratio | Near-dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 1500 | 3236 | 1288 | 212 | 5 | 14.1% | 1.3% |
| val | 300 | 671 | 233 | 67 | 3 | 22.3% | 2.3% |
| test | 200 | 435 | 172 | 28 | 3 | 14.0% | 1.5% |

Phân bố khoảng cách:

- Train: 5.7-99.9 m, median 54.5 m, 1338 box từ xe cùng làn được spawn chủ động.
- Val: 6.2-99.5 m, median 42.2 m, 222 box cùng làn.
- Test: 6.4-99.5 m, median 47.2 m, 188 box cùng làn.

Audit:

- Lệnh audit dùng root `aeb/dataset_v6`.
- Kết quả: `Data đạt toàn bộ quality gate`.
- `dataset_v6/dataset.yaml` đã được tạo.
- Dung lượng dataset: khoảng 1.8 GB.
- Gallery kiểm label: `outputs/dataset_v6_box_check`, 2000 ảnh, khoảng 717 MB.

Nhận xét nhanh:

- V6 bắt thêm nhiều xe xa/nhỏ hơn v5 và vẫn giữ near-duplicate thấp.
- Tổng box train vượt ngưỡng mà không cần session bù.
- Cần kiểm gallery thủ công thêm để chắc việc nới filter không tạo nhiều label
  quá nhỏ hoặc label khó học.

## 2026-06-25 - Kiểm Tra Và Tối Ưu Radar-Only AEB

- CARLA server đang chạy được dùng để chạy lại radar-only validation ở `Town04`.
- Batch baseline nhỏ: 5/5 PASS.
- Batch baseline mở rộng: 13/13 PASS, không collision và không false brake trong
  các case clear road/adjacent/curve đã chọn.
- Đã sửa log runner để frame đầu `AEB BRAKE` ghi đúng `brake_cmd=1.0`, tránh lệch
  1 tick giữa command AEB và `ego.get_control()`.
- Thử config tạm `full_brake=0.75`: vẫn PASS nhưng dừng sát hơn nhiều, không đưa
  vào config chính.
- Kết luận: radar-only hiện đủ ổn làm baseline safety, nhưng chưa mượt vì phanh
  vẫn là binary full-brake. Bước tiếp theo nên là phanh nhiều tầng hoặc PID.
- Báo cáo chi tiết: `docs/log/RADAR_ONLY_OPTIMIZATION_20260625.md`.

## 2026-06-25 - Smoke Test YOLO, Fusion Và Full AEB

- Tạo script `scripts/smoke_yolo_fusion_full.py` để test tự động YOLO ONNX,
  camera-radar fusion và một scenario full radar-AEB.
- Phát hiện smoke script spawn target sai nhánh đường ở Town04; đã sửa bằng cách
  tick ego trước khi lấy transform và teleport target trực tiếp trước mũi ego.
- Phát hiện ONNX YOLO có thể trả bbox trùng; đã thêm NMS và test tương ứng.
- Kết quả sau sửa:
  - YOLO/Fusion: PASS, detect `car` confidence khoảng 0.982, radar distance
    khoảng 17.92 m với target gap 18.0 m.
  - Full radar-AEB `ccrs_60_demo_150`: PASS, không collision, dừng còn khoảng
    7.704 m.
- Báo cáo chi tiết: `docs/log/YOLO_FUSION_FULL_SMOKE_20260625.md`.

## 2026-06-25 - Test Binary Brake Với Fusion Camera-Radar

- Tạo script `scripts/run_fusion_aeb_scenarios.py` để chạy scenario batch với
  fusion gate: radar chọn target và tính TTC/stopping distance, YOLO camera xác
  nhận target trước khi cho lệnh `BRAKE` đi qua.
- Thêm hook `_make_system()` vào `scripts/run_radar_aeb_scenarios.py` để tái sử
  dụng runner mà không phá radar-only baseline.
- Unit test: 29/29 PASS.
- Full validation trên `configs/radar_only_validation.yaml`, control mode
  `physics`: 29/29 PASS, không collision, không false brake ở các case clear
  road/adjacent/curve clear.
- Log full validation: `logs/fusion_aeb_binary_full_20260625_01`.
- Báo cáo chi tiết: `docs/log/FUSION_AEB_BINARY_TEST_20260625.md`.

## 2026-06-25 - Limit Validation Cho Fusion-AEB Binary

- Tạo `configs/fusion_limit_validation.yaml` để tìm biên hoạt động trước khi làm
  PID/multi-stage brake.
- Full batch đầu tiên: 21/22 PASS.
- Cùng làn/stationary pass từ 40 đến 100 km/h với gap được chọn; short-gap 80
  km/h ở 35 m còn pass nhưng min gap chỉ khoảng 1.48 m.
- Fail chính: đường cong + xe đứng yên làn bên ở 80 km/h bị phanh nhầm và
  collision.
- Sweep bổ sung đường cong + xe làn bên:
  - 65 km/h: PASS.
  - 70 km/h: FAIL do phanh nhầm.
  - 75-80 km/h: FAIL do phanh nhầm và collision.
- Nhận xét: điểm yếu hiện tại là target association/lane gating trên đường cong
  tốc độ cao, không phải YOLO detect sai.
- Báo cáo chi tiết: `docs/log/FUSION_LIMIT_VALIDATION_20260625.md`.

## 2026-06-26 - Target Gate Không Dùng CARLA Map

- Thêm `target_gate` vào `configs/sensors.yaml`.
- Sửa `core/radar_aeb_pipeline.py` để target radar mới xuất hiện phải ổn định
  đủ frame trước khi được đưa vào AEB, trừ khi quá sát hoặc khoảng cách dừng
  thiếu nghiêm trọng.
- Không dùng `CARLA map`, `lane_id` hoặc ground truth để quyết định phanh.
- Unit test: 31/31 PASS.
- Sweep lại lỗi cũ `false_curve_adjacent_65/70/75/80`: 4/4 PASS.
- Full validation chuẩn: 29/29 PASS tại
  `logs/fusion_aeb_binary_gate_full_20260626_01`.
- Full limit validation: 25/25 PASS tại
  `logs/fusion_limit_gate_full_20260626_01`.
- Báo cáo chi tiết: `docs/log/TARGET_GATE_VALIDATION_20260626.md`.

## 2026-06-26 - Thử Staged Brake

- Thêm `brake_mode: staged` trong `control/brake.py` và `configs/sensors.yaml`.
- Unit test: 33/33 PASS.
- Subset nguy hiểm: 7/7 PASS tại `logs/staged_brake_risk_subset_20260626_01`.
- Full validation chuẩn: 29/29 PASS tại
  `logs/staged_brake_validation_full_20260626_01`.
- Full limit validation: 25/25 PASS tại
  `logs/staged_brake_limit_full_20260626_01`.
- Kết luận: staged v1 vẫn an toàn trên bộ test hiện tại nhưng chưa giảm jerk ổn
  định; min gap trung bình giảm so với binary. Đây là bản thử nghiệm trung gian,
  chưa phải nghiệm tối ưu.
- Báo cáo chi tiết: `docs/log/STAGED_BRAKE_VALIDATION_20260626.md`.

## 2026-06-26 - PID Brake V1

- Thêm `brake_mode: pid` trong `control/brake.py` và chuyển config chính sang
  PID trong `configs/sensors.yaml`.
- Unit test: 36/36 PASS.
- Subset nguy hiểm/false-positive: 7/7 PASS tại
  `logs/pid_brake_risk_subset_20260626_01`.
- Full validation lần đầu: 28/29 PASS, fail ở `multi_two_leads_80` vì không
  collision nhưng min gap chỉ 0.05 m, dưới ngưỡng 0.5 m.
- Tune PID:
  - `pid_min_brake`: 0.35 -> 0.45.
  - `pid_brake_rise_rate_per_s`: 8.0 -> 10.0.
  - `pid_brake_fall_rate_per_s`: 6.0 -> 3.0.
  - Đạo hàm PID chỉ dùng phần dương để không kéo phanh xuống khi xe chưa dừng.
- Retest `multi_two_leads_80`: PASS, min gap 0.94 m tại
  `logs/pid_brake_multi_tune_20260626_01`.
- Full validation sau tune: 29/29 PASS tại
  `logs/pid_brake_validation_full_20260626_02`.
- Full limit validation: 25/25 PASS tại
  `logs/pid_brake_limit_full_20260626_01`.
- Kết luận: PID v1 đạt an toàn trên bộ test hiện tại, nhưng chưa tối ưu độ êm.
  Full validation có jerk trung bình thấp hơn binary một chút; limit validation
  có jerk trung bình cao hơn binary/staged. Cần PID v2 nếu muốn tối ưu comfort.
- Báo cáo chi tiết: `docs/log/PID_BRAKE_VALIDATION_20260626.md`.

## Roadmap Sau PID V2

- Giữ nhiều chiến lược phanh để so sánh và trình diễn:
  - `binary`
  - `staged`
  - `pid_v1`
  - `pid_v2_comfort`
  - `staged_pid`
  - các bản PID khác nếu cần tìm giới hạn hệ thống.
- Sau khi PID v2 có kết quả ổn, làm lại UI để chọn brake mode trực tiếp khi demo.
- Bổ sung xuất log hai tầng sau mỗi batch test:
  - log kỹ thuật chi tiết từng frame `.csv`;
  - báo cáo dễ đọc cho người xem: pass/fail, có collision không, xe dừng cách
    bao nhiêu mét, thời điểm bắt đầu phanh, max decel, max jerk và nhận xét.
- Thiết kế UI demo/test cho màn Full HD:
  - ưu tiên vừa theo chiều dọc, mặc định khoảng `1600x900`;
  - cột trái chiếm khoảng 60% chiều ngang, chia làm hai hàng:
    - trên: camera sau kính lái + YOLO/fusion;
    - dưới: manual/chase view để thấy ego, HUD, collision;
  - cột phải chiếm toàn bộ chiều cao, dùng cho radar bird-eye, predicted path,
    target AEB và thông số TTC/distance/relative velocity/brake command;
  - batch validation vẫn nên chạy không UI hoặc UI tối giản để log ổn định, UI
    ba vùng dùng cho demo và quay video báo cáo.
- Quay video evidence:
  - đã có script `scripts/record_scenario_videos.py` để quay UI scenario tự động
    bằng Xvfb + ffmpeg/NVENC;
  - output mặc định nằm trong `outputs/scenario_videos/`, log quay nằm trong
    `outputs/scenario_videos/logs/`;
  - sau khi làm UI demo ba vùng, cần cập nhật script quay video cho đúng kích
    thước cửa sổ/capture size mới, ví dụ preset Full HD `1600x900`.

## 2026-06-27 - PID V2 Comfort

- Thêm `pid_v2_comfort` theo hướng phanh sớm hơn nhưng nhẹ hơn.
- Thêm `pid_target_margin_m` để tạo khoảng dư trước ngưỡng dừng bắt buộc.
- Thêm `pid_target_margin_max_lateral_m` để chỉ dùng phanh sớm khi target còn
  gần tâm hành lang; cách này tránh phanh nhầm ở `cut_out_65_35`.
- Unit test: 39/39 PASS.
- Lưu ý quy trình: không chạy hai batch scenario song song trên cùng CARLA
  server, vì hai runner sẽ cùng điều khiển world và làm kết quả nhiễu.
- Targeted test sau lateral gate:
  - `cut_out_65_35`: PASS, không phanh nhầm.
  - `cut_out_late_65_35`: PASS, vẫn phanh.
  - `short_gap_80_35`: PASS.
  - `braking_80_gap_40`: PASS.
- Full validation: 29/29 PASS tại
  `logs/pid_v2_comfort_validation_full_20260627_01`.
- Limit validation: 25/25 PASS tại
  `logs/pid_v2_comfort_limit_full_20260627_01`.
- So với PID v1:
  - Full validation avg min gap tăng 7.81 m -> 9.05 m.
  - Full validation avg max jerk giảm 169.22 -> 148.56 m/s3.
  - Limit validation avg min gap tăng 5.94 m -> 6.57 m.
  - Limit validation avg max jerk giảm 181.95 -> 146.60 m/s3.
- Kết luận: PID v2 comfort đạt mục tiêu và có thể dùng làm bản PID chính hiện tại.
  Bước tiếp theo là `staged PID`: chia risk level thành nhiều tầng rồi dùng PID
  điều khiển lực phanh trong từng tầng.
- Báo cáo chi tiết: `docs/log/PID_V2_COMFORT_VALIDATION_20260627.md`.

## 2026-06-27 - Staged PID Bản Đầu

- Thêm `brake_mode: staged_pid` trong `control/brake.py`.
- Ý tưởng: dùng PID v2 comfort làm nền, nhưng target brake được đưa qua các tầng
  rủi ro:
  - soft: phanh sớm/nhẹ, target được giới hạn bởi `staged_soft_brake`;
  - medium: TTC hoặc khoảng cách dừng đã vào vùng phanh chính;
  - hard: TTC thấp hơn hoặc thiếu khoảng cách rõ hơn;
  - emergency: quá sát/quá nguy hiểm, cho phép phanh tối đa.
- `configs/sensors.yaml` đã chuyển `brake_mode` sang `staged_pid` để các lần
  test tiếp theo chạy bản này.
- Unit test logic: 27/27 PASS.
- Sau đó phát hiện lỗi runner: trong `settle_ticks`, ego đã chạy trước thời điểm
  bắt đầu log, làm một số case có khoảng cách thực tế nhỏ hơn config và làm PID
  có state trước khi scenario bắt đầu.
- Sửa runner để warm-up sensor khi xe đứng yên, rồi reset state phanh/PID trước
  khi bắt đầu scenario.
- Tune `pid_emergency_rise_rate_per_s` lên `20.0` để emergency stage lên full
  brake ngay tick đầu.
- Unit test sau sửa: 42/42 PASS.
- Targeted subset sau sửa runner: 4/4 PASS.
- Full validation: 29/29 PASS tại
  `logs/staged_pid_validation_full_20260627_02`.
- Limit validation: 25/25 PASS tại `logs/staged_pid_limit_full_20260627_02`.
- Kết luận: `staged_pid` pass toàn bộ test hiện tại. Cần chạy lại script so sánh
  nhiều brake mode trên runner đã sửa để so sánh công bằng với `pid_v2_comfort`.
- Báo cáo chi tiết: `docs/log/STAGED_PID_VALIDATION_20260627.md`.

## 2026-06-27 - Sweep Tìm Giới Hạn Hệ Thống CCRs

- Chốt hướng đánh giá kiểu sản phẩm thật: không cố làm mọi case đều pass, mà tìm
  rõ dải vận tốc/khoảng cách hệ thống chạy tốt và các vùng chắc chắn vượt giới
  hạn.
- Thêm `configs/system_limit_ccrs_sweep.yaml` gồm 56 case CCRs:
  - xe trước đứng yên cùng làn;
  - ego chạy 40, 50, 60, 70, 80, 90, 100, 110 km/h;
  - khoảng cách ban đầu 20, 30, 40, 50, 60, 80, 100 m.
- Thêm `scripts/summarize_system_limit_sweep.py` để tạo bảng heatmap pass/fail từ
  `summary.csv`.
- Chạy full sweep tại `logs/system_limit_ccrs_sweep_20260627_01`.
- Kết quả biên pass nhỏ nhất theo vận tốc:
  - 40 km/h: pass từ 20 m.
  - 50 km/h: pass từ 20 m.
  - 60 km/h: pass từ 20 m.
  - 70 km/h: pass từ 30 m.
  - 80 km/h: pass từ 30 m.
  - 90 km/h: pass từ 40 m.
  - 100 km/h: pass từ 50 m.
  - 110 km/h: pass từ 60 m.
- Các case fail là collision ở vùng vận tốc cao/khoảng cách ngắn, đúng mục tiêu
  dùng để xác định giới hạn thay vì che kết quả.
- Kết luận tạm thời: ODD hợp lý để báo cáo hiện tại là cao tốc, thời tiết lý
  tưởng, chỉ xe ô tô, target cùng làn; dải nên tập trung tối ưu là 50-80 km/h.
  Với CCRs 80 km/h, hệ thống hiện pass từ khoảng 30 m trở lên.
- Báo cáo chi tiết: `docs/log/SYSTEM_LIMIT_SWEEP_20260627.md`.
- Heatmap tự sinh: `logs/system_limit_ccrs_sweep_20260627_01/system_limit_heatmap.md`.

## 2026-06-27 - Sweep Mở Rộng Tìm Giới Hạn Hệ Thống

- Thêm `scripts/build_system_limit_extended_sweep_config.py` để sinh config dài
  có kiểm soát, tránh viết tay nhiều scenario dễ sai.
- Thêm `configs/system_limit_extended_sweep.yaml` gồm 66 case:
  - CCRm: xe trước chạy chậm hơn ego.
  - CCRb: xe trước đang chạy rồi phanh gấp.
  - Cut-in: xe từ làn trái cắt vào trước ego.
- Mở rộng `scripts/summarize_system_limit_sweep.py` để tạo heatmap cho nhiều
  nhóm test, không chỉ CCRs.
- Smoke test 3 case đại diện: 3/3 PASS.
- Full extended sweep tại `logs/system_limit_extended_sweep_20260627_01`:
  - 66 case.
  - 64 PASS.
  - 2 FAIL/collision có chủ ý để xác định giới hạn.
- Hai case fail:
  - `ccrb_110_gap_20`: xe trước phanh gấp, cả hai 110 km/h, gap 20 m.
  - `cutin_100_60_gap_25`: ego 100 km/h, xe 60 km/h cắt làn vào khi gap 25 m.
- Kết luận: các case fail nằm đúng vùng ngoài ODD hợp lý: tốc độ cao, khoảng cách
  ngắn, target xuất hiện/phanh quá gấp.
- Báo cáo chi tiết: `docs/log/SYSTEM_LIMIT_EXTENDED_SWEEP_20260627.md`.
- Heatmap: `logs/system_limit_extended_sweep_20260627_01/system_limit_heatmap.md`.

## 2026-06-27 - UI Final Và Script Quay Video

- Thêm `ui/aeb_demo_view.py` làm UI demo final 3 vùng:
  - trên trái: camera sau kính lái + YOLO + radar/fusion overlay;
  - dưới trái: manual/chase view để thấy ego, target, HUD và collision;
  - bên phải: radar bird-eye, predicted path, target, TTC, state và brake command.
- Cập nhật `scripts/record_scenario_videos.py`:
  - mặc định quay bằng UI final `ui/aeb_demo_view.py`;
  - default capture đổi sang `1600x900`;
  - thêm `--run-id`, `--ui-script`, `--encoder`, `--skip-existing`, `--dry-run`;
  - tự sinh `video_report.md` để sau này điền link Google Drive.
- Compile check:
  - `../venv/bin/python -m py_compile ui/aeb_demo_view.py scripts/record_scenario_videos.py`
- Dry-run một scenario thành công:
  - `cutin_80_50_gap_25`

## 2026-06-27 - Tách Chế Độ Dừng Để Đánh Giá Và Chế Độ Demo Real

- Phát hiện `--keep-driving-after-aeb` trước đó mới tắt stop latch của live
  scenario, nhưng logic AEB vẫn đọc `hold_brake_until_stopped: true` nên có thể
  tiếp tục giữ phanh với reason `brake_held_until_stopped`.
- Sửa `ui/aeb_demo_view.py`: khi chạy `--keep-driving-after-aeb`, UI dùng bản
  config runtime riêng với `brake.hold_brake_until_stopped = false`.
- Ý nghĩa:
  - Không truyền `--keep-driving-after-aeb`: chế độ validation/report, phanh rồi
    dừng hẳn để đo final gap.
  - Có `--keep-driving-after-aeb`: chế độ demo giống xe thật hơn, AEB có thể
    nhả phanh khi hết nguy hiểm và scenario controller tiếp tục lái.
- Unit test bổ sung:
  - `test_brake_can_release_before_stop_when_hold_disabled`.
  - Kết quả: `PYTHONPATH=aeb venv/bin/python -m unittest aeb.tests.test_radar_aeb_logic`
    đạt 28/28 PASS.

## 2026-06-27 - Chuyển UI Final Sang Cửa Sổ Tự Fit Màn Hình

- Không dùng `--fullscreen` làm luồng demo chính vì fullscreen thật không ổn trên
  máy hiện tại và khó thao tác khi vừa xem vừa điều khiển CARLA/terminal.
- `ui/aeb_demo_view.py` mặc định mở cửa sổ thường và tự fit theo desktop hiện tại
  nếu không truyền `--res`.
- Thêm:
  - `--fit-screen`: mặc định bật.
  - `--no-fit-screen`: tắt tự fit, dùng đúng `--res` hoặc config.
  - `--fit-margin-x`, `--fit-margin-y`: chỉnh khoảng trừ cho dock/top bar.
- `scripts/record_scenario_videos.py` vẫn truyền `--res` và `--no-fit-screen`
  khi quay bằng UI final để video có kích thước cố định, tránh lệch vùng capture.

## 2026-06-27 - Nâng Cấp Project Launcher

- Nâng cấp `laucher.py` theo hướng tool nội bộ đầy đủ, không cần đẹp:
  - tab bật/tắt CARLA server;
  - tab chạy UI, mặc định là final demo 3 màn;
  - tab chạy radar/fusion scenario batch, unit test, audit dataset;
  - tab quay video scenario bằng UI final.
- Thêm chọn scenario config từ YAML:
  - `system_limit_extended_sweep.yaml`;
  - `system_limit_ccrs_sweep.yaml`;
  - `radar_only_validation.yaml`;
  - `radar_aeb_scenarios.yaml`;
  - `fusion_limit_validation.yaml`.
- Thêm lựa chọn hành vi AEB:
  - validation: phanh rồi dừng để đo final gap;
  - realistic: hết nguy hiểm thì nhả phanh và chạy tiếp
    (`--keep-driving-after-aeb`).
- Launcher chạy bằng `python3 laucher.py` vì `venv` CARLA/YOLO trên
  máy hiện tại không có `tkinter`; các nút bên trong vẫn gọi đúng Python riêng.

## 2026-06-27 - Refactor Scenario Config Và Chọn Loại Phanh Trong UI

- Chia lại scenario config theo tình huống car-to-car:
  - `configs/scenarios/car_to_car/ccrs_stationary_lead.yaml`;
  - `configs/scenarios/car_to_car/ccrm_moving_lead.yaml`;
  - `configs/scenarios/car_to_car/ccrb_braking_lead.yaml`;
  - `configs/scenarios/car_to_car/cut_in.yaml`;
  - `configs/scenarios/car_to_car/cut_out.yaml`;
  - `configs/scenarios/car_to_car/adjacent_vehicle.yaml`;
  - `configs/scenarios/car_to_car/curve_cases.yaml`;
  - `configs/scenarios/car_to_car/multi_actor.yaml`;
  - `configs/scenarios/car_to_car/clear_road.yaml`.
- Thêm các suite để chạy theo mục tiêu:
  - `configs/scenarios/suites/smoke_basic.yaml`;
  - `configs/scenarios/suites/radar_only_regression.yaml`;
  - `configs/scenarios/suites/fusion_regression.yaml`;
  - `configs/scenarios/suites/system_limit_ccrs_sweep.yaml`;
  - `configs/scenarios/suites/system_limit_extended_sweep.yaml`;
  - `configs/scenarios/suites/report_demo.yaml`.
- Các YAML scenario cũ được chuyển vào `configs/legacy/` để tham chiếu lịch sử,
  nhưng launcher/script mặc định dùng đường dẫn mới.
- Thêm `--brake-mode` vào UI runtime config override. Launcher có dropdown chọn
  loại phanh khi chạy demo/quay video: `binary`, `staged`, `pid`, `pid_v1`,
  `pid_v2`, `pid_v2_comfort`, `staged_pid` hoặc dùng mặc định trong
  `sensors.yaml`.

## 2026-06-28 - Ổn Định CARLA Server Khi Chạy Launcher

- Giữ lệnh bật CARLA mặc định giống cách chạy ổn định bằng terminal:
  `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low`.
- Thêm tùy chọn `Stable mode` trong launcher, chỉ dùng khi cần debug server:
  thêm `-carla-rpc-port`, `-nosound`, `-windowed`, `-ResX=1280`, `-ResY=720`.
- Thêm nút `Dọn CARLA treo` để xử lý trường hợp port CARLA offline nhưng process
  `CarlaUE4` vẫn còn chạy ngầm sau khi UE4 bị văng.
- Các UI Pygame thoát sạch hơn khi mất kết nối CARLA, thay vì in traceback dài.
- Khi chạy batch/video nhiều scenario, CARLA 0.9.11 có thể crash sau 2-3 bài
  dù không OOM (`bIsOOM=0` trong crash log). Thêm cơ chế chạy bền:
  `--scenario-cooldown-s` để nghỉ/tick giữa scenario và
  `--reload-world-every` để reload world sau mỗi N bài nếu cần.
- Launcher hiển thị thêm `Cooldown` và `Reload world mỗi N bài/video`. Quay video
  mặc định reload mỗi 2 video để giảm rủi ro UE4 văng khi spawn/destroy UI/sensor
  liên tục.
- Chốt hướng benchmark: mỗi kịch bản nên bắt đầu từ world sạch. Batch radar/fusion
  và quay video mặc định `--reload-world-every 1`. UI demo có thêm tùy chọn
  `Reload world khi mở scenario`, tương ứng `--reload-world-on-start`.
- Sửa tính tái lập của UI live scenario: warmup, cut-in timing, duration, auto-exit
  và debug overlay chuyển sang dùng thời gian mô phỏng CARLA
  (`world.get_snapshot().timestamp.elapsed_seconds`) thay vì thời gian thật của
  máy (`time.monotonic`). Nhờ vậy kịch bản như `cutin_100_60_gap_25` không còn
  phụ thuộc FPS/render lag để quyết định thời điểm xe bắt đầu cắt làn.
- Khi set tốc độ ban đầu cho ego/target, nhả control phanh ngay sau
  `set_target_velocity` để tránh tick đầu vẫn còn lệnh phanh từ warmup.
- Với `control-mode physics`, thêm `physics_velocity_lock` mặc định bật cho
  giai đoạn chạy kịch bản trước khi AEB can thiệp. Controller vẫn đạp ga/phanh
  bằng physics, nhưng mỗi tick đồng thời giữ vector vận tốc theo giá trị scenario
  để tránh ego bị thấp hơn cấu hình khoảng 10% trong các bài như
  `cutin_100_60_gap_25` và `cutin_80_50_gap_25`. Khi AEB bắt đầu phanh, ego không
  còn được khóa vận tốc nữa nên kết quả dừng vẫn phản ánh thuật toán phanh.
- Sửa UI demo live: khi scenario kết thúc bình thường, ví dụ `clear_road_50`,
  không tự áp `brake=1.0` nữa. Chỉ giữ xe dừng khi AEB thật sự đã latch phanh;
  trường hợp đường trống kết thúc bài thì nhả ga/phanh để tránh hiểu nhầm là
  AEB phanh nhầm.
- Bổ sung log chi tiết cho đánh giá phanh: tick-level CSV có thêm cột
  `brake_stage` (`SAFE`, `WARNING`, `SOFT_BRAKE`, `MEDIUM_BRAKE`, `HARD_BRAKE`,
  `EMERGENCY`, `HOLD_STOP`, `RELEASE`). Thêm script
  `scripts/plot_brake_profile.py` để xuất biểu đồ PNG gồm lực phanh, tốc độ ego,
  khoảng cách bumper gap và TTC theo thời gian. Script đọc được cả log cũ chưa có
  `brake_stage` bằng cách suy ra stage từ `aeb_state`, `aeb_reason` và
  `brake_cmd`.
- Bổ sung lớp ổn định mới cho lỗi CARLA văng sau nhiều scenario:
  - batch runner tự quét và dọn mọi actor có `role_name` bắt đầu bằng
    `aeb_scenario_` trước scenario mới và sau `reload_world`;
  - thêm `--reload-world-wait-s` để đợi world ổn định trước khi spawn tiếp;
  - launcher có tùy chọn `Restart CARLA trước scenario`, dùng cho cách chạy
    từng scenario trong UI: dừng process CARLA cũ, bật lại server theo cấu hình
    hiện tại, chờ port online rồi mới mở Pygame demo.
