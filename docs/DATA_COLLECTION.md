# Thu Thập Dataset Xe Bằng Ground Truth CARLA

Script `collect_ground_truth_data.py` tự động:

- Spawn ego `vehicle.tesla.model3`.
- Tự spawn traffic vehicle bằng Traffic Manager.
- Cho ego chạy bằng Traffic Manager.
- Chạy CARLA ở synchronous mode.
- Thu ảnh RGB từ camera sau kính lái.
- Thu depth và semantic segmentation đúng cùng simulation frame.
- Lấy bounding box 3D ground truth của các vehicle trong CARLA.
- Chiếu bounding box 3D lên ảnh thành bounding box 2D.
- Dùng semantic vehicle mask kết hợp depth target để loại ghost box.
- Siết bounding box hình học vào vùng pixel xe thực sự nhìn thấy.
- Lưu nhãn YOLO với một class duy nhất: `0 = car`.
- Lưu ảnh preview có box để kiểm tra bằng mắt.
- Lưu metadata về actor, khoảng cách, tốc độ, truncation và visibility.

## Vì Sao Chỉ Dùng Một Class `car`?

Giai đoạn hiện tại chỉ nghiên cứu AEB car-to-car trên Town04 trong điều kiện
tương đối lý tưởng. Một class giúp:

- Giảm độ phức tạp của model.
- Tập trung vào việc xác nhận có phương tiện phía trước.
- Giảm nhu cầu cân bằng nhiều class.
- Dễ đánh giá lỗi false-negative ảnh hưởng trực tiếp tới AEB.

Các vehicle bốn bánh của CARLA được gộp chung thành class `car`. Nếu sau này
mở rộng sang pedestrian, cyclist hoặc truck-specific AEB thì phải tách lại
class và thu thêm dataset tương ứng.

## Cấu Trúc File

```text
aeb/
├── collect_ground_truth_data.py
├── configs/
│   └── dataset_collection.yaml
├── core/
│   └── ground_truth_labels.py
└── dataset_v3/
    ├── dataset.yaml
    ├── images/
    │   ├── train/
    │   └── val/
    ├── labels/
    │   ├── train/
    │   └── val/
    ├── previews/
    │   ├── train/
    │   └── val/
    └── metadata/
        ├── train/
        └── val/
```

Ảnh trong `images/` là ảnh sạch dùng để train. Box chỉ được vẽ vào
`previews/`, không vẽ trực tiếp lên ảnh train.

Mỗi file label có dạng YOLO:

```text
class_id x_center y_center width height
```

Ví dụ:

```text
0 0.534602 0.513261 0.020110 0.029073
```

Tất cả tọa độ đều được chuẩn hóa về khoảng `[0, 1]`.

## Cách Chạy

### 1. Chạy CARLA

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Không thêm cờ `-opengl`.

### 2. Thu Dataset Train

Collector tự spawn ego và traffic. Không chạy `spawn_npc.py`, manual control,
ScenarioRunner hoặc client synchronous khác cùng lúc.

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python aeb/collect_ground_truth_data.py \
  --split train \
  --session-id town04_train_01 \
  --seed 2026 \
  --max-samples 2000
```

Nhấn `Q` hoặc `Esc` trong cửa sổ preview để dừng sớm.

Mỗi `session-id` là duy nhất. Khi thu một lượt mới, đổi tên session:

```bash
venv/bin/python aeb/collect_ground_truth_data.py \
  --split train \
  --session-id town04_train_02 \
  --max-samples 2000
```

Nếu lượt thu trước bị dừng giữa chừng và config chưa thay đổi, chạy tiếp bằng:

```bash
venv/bin/python aeb/collect_ground_truth_data.py \
  --split train \
  --session-id town04_train_01 \
  --max-samples 2000 \
  --resume
```

`--max-samples 2000` là tổng số mẫu mong muốn của session, không phải số mẫu
thu thêm. Collector kiểm tra metadata, ảnh, label và config trước khi nối tiếp.
Nếu config đã thay đổi, hãy tạo session mới để không trộn hai cấu hình gán nhãn.

Chạy không mở cửa sổ:

```bash
venv/bin/python aeb/collect_ground_truth_data.py \
  --split train \
  --session-id town04_train_01 \
  --max-samples 2000 \
  --no-window
```

### 3. Thu Dataset Validation

Đổi seed Traffic Manager trong config rồi thu một session riêng:

```yaml
traffic_manager:
  seed: 99
```

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python aeb/collect_ground_truth_data.py \
  --split val \
  --session-id town04_val_01 \
  --max-samples 500
```

Không nên random chia các frame liên tiếp của cùng một lượt chạy thành train
và val. Các ảnh trong cùng một chuỗi vẫn rất giống nhau, gây data leakage và
làm metric validation đẹp giả. Nên tách train/val theo session, traffic seed,
vị trí spawn và điều kiện mô phỏng.

Sau khi thu đủ train, val và test, pipeline tự động được mô tả tại
[`MODEL_TRAINING.md`](MODEL_TRAINING.md).

## Traffic Được Sinh Trong Collector

```yaml
traffic:
  spawn_vehicles: true
  number_of_vehicles: 30
  actor_filter: vehicle.*
  safe_blueprints: true
  same_lane_vehicles_ahead: 10
  same_lane_first_distance_m: 22.0
  same_lane_spacing_m: 20.0
  same_lane_following_distance_m: 8.0
```

Ego được spawn tại `spawn_index: 143`, là đoạn highway không nằm trong
junction của Town04. Collector lần theo `Waypoint.next()` từ lane của ego để
đặt tối đa 10 xe phía trước trên đúng tuyến lane. Nhóm này và ego đều tắt tự
đổi làn trong Traffic Manager. Các xe còn lại được spawn từ các spawn point
khác để dataset vẫn có xe ở làn bên cạnh và tình huống nền đa dạng.

Collector dùng cùng một client để bật synchronous mode, spawn ego và NPC, tick
simulation, thu sensor, sau đó trả world về trạng thái cũ và xóa actor đã tạo.
Cách này bám theo `spawn_npc.py`, `synchronous_mode.py` và
`sensor_synchronization.py` chính thức của CARLA, đồng thời tránh hai client
cùng gửi tick.

## Các Bộ Lọc Ground Truth

Config nằm tại:

```text
aeb/configs/dataset_collection.yaml
```

### Lọc Actor

```yaml
filter:
  actor_pattern: vehicle.*
  minimum_wheels: 4
  max_distance_m: 80.0
```

- Không gắn nhãn ego.
- Không gắn nhãn xe hai bánh.
- Bỏ vehicle ngoài khoảng cách tối đa.

### Lọc Bounding Box

```yaml
filter:
  min_box_width_px: 14
  min_box_height_px: 10
  min_box_area_px: 180
  max_truncation: 0.50
```

Box quá nhỏ không cung cấp đủ đặc trưng để train. Box bị cắt quá nhiều ở mép
ảnh cũng bị loại để giảm nhãn khó kiểm tra.

### Lọc Che Khuất Bằng Semantic Và Depth

```yaml
filter:
  use_depth_visibility: true
  use_semantic_visibility: true
  vehicle_semantic_tag: 10
  depth_tolerance_m: 1.5
  fit_box_to_visible_pixels: true
  visible_box_padding_px: 2
  min_visible_pixels: 50
  min_visible_ratio: 0.25
```

CARLA vẫn biết bounding box của xe ở sau một xe khác. Nếu chỉ chiếu hình học,
collector có thể tạo label cho xe nằm sau tường hoặc sau phương tiện khác.

Mask hợp lệ được tính như sau:

```text
visible_mask =
  semantic_pixel == Vehicles
  AND
  min_target_depth <= pixel_depth <= max_target_depth
```

Semantic segmentation loại pixel mặt đường, tường và cây. Depth loại vehicle
khác nằm trước hoặc sau target. Bounding box cuối được siết theo min/max pixel
của `visible_mask`, tương tự hướng tiếp cận của CarFree.

`min_visible_ratio: 0.25` nghĩa là ít nhất 25% vùng box chiếu hình học phải là
pixel vehicle ở đúng khoảng depth của target. Ngưỡng cũ 2% quá lỏng, nên một
phần rất nhỏ của xe vẫn đủ tạo label. Kết hợp ngưỡng này với tối thiểu 50 pixel,
box `14 x 10 px`, khoảng cách 80 m và truncation tối đa 50% giúp bỏ phần lớn xe
quá xa, quá nhỏ, bị che nhiều hoặc chỉ ló ra ở mép ảnh.

CARLA 0.9.11 chưa có instance segmentation camera như các bản mới. Hai xe cùng
class và gần như cùng depth vẫn có thể bị nhập mask trong trường hợp đặc biệt,
vì vậy vẫn cần xem ngẫu nhiên ảnh trong `previews/`.

## Đồng Bộ Sensor

Collector đăng ký bốn queue:

```text
WorldSnapshot
RGB
Depth
Semantic segmentation
```

Sau mỗi `world.tick()`, script chỉ xử lý khi cả bốn queue trả về đúng cùng
`frame`. Camera GPU có thể đến chậm theo thời gian thực, nhưng collector sẽ chờ
thay vì ghép ảnh mới với pose cũ.

Nếu CARLA đã ở synchronous mode trước khi collector chạy, script sẽ dừng và
báo lỗi rõ ràng. Trả server về async bằng:

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python PythonAPI/util/config.py --no-sync
```

## Tần Số Camera Và Tần Số Lưu

```yaml
world:
  fixed_delta_seconds: 0.05

camera:
  sensor_tick: 0.0

dataset:
  save_interval_frames_min: 5
  save_interval_frames_max: 10
```

- Simulation chạy 20 tick/s.
- `sensor_tick: 0.0` buộc camera phát ở mọi world tick.
- Collector chọn ngẫu nhiên khoảng cách 5-10 frame giữa hai lần lấy mẫu.
- Khoảng thời gian tương ứng là 0,25-0,5 giây, khoảng 2-4 ảnh mỗi giây mô phỏng.
- Khoảng lấy mẫu ngẫu nhiên giảm chuỗi frame gần như trùng nhau và tránh mẫu
  luôn rơi vào cùng một pha tuần hoàn.

Không đặt `sensor_tick: 0.05` cho collector trên CARLA 0.9.11. Qua kiểm tra
thực tế, camera có thể bỏ xen kẽ một số frame do sai số thời gian, làm RGB/depth
không còn khớp chính xác với world frame.

## Negative Sample

Ảnh không có xe là negative sample cần thiết để giảm false-positive:

```yaml
dataset:
  save_empty_images: true
  empty_frame_keep_ratio: 0.15
```

Không cần giữ toàn bộ frame rỗng vì chúng rất nhiều và dễ làm dataset mất cân
bằng. Baseline chỉ giữ ngẫu nhiên 15%.

Do cấu hình chính luôn đặt xe cùng làn phía trước, nên cần thu thêm một session
đường trống:

```bash
venv/bin/python aeb/collect_ground_truth_data.py \
  --split train \
  --session-id town04_train_clear_01 \
  --seed 5026 \
  --number-of-vehicles 0 \
  --same-lane-vehicles 0 \
  --max-samples 150
```

Pipeline train yêu cầu tỷ lệ negative sample tối thiểu 3% và tối đa 30%.

## Metadata

Mỗi session có file `.jsonl`. Mỗi dòng chứa:

- Camera frame và simulation timestamp.
- Pose camera và ego.
- Actor ID và blueprint của từng xe.
- Cờ `same_lane_seeded` cho biết xe thuộc nhóm được đặt cùng làn phía trước.
- Bounding box pixel.
- Khoảng cách và tốc độ vehicle.
- Tỷ lệ truncation.
- Số pixel và tỷ lệ visibility theo depth.

File `_summary.json` ghi tổng số:

- Ảnh positive/negative.
- Tổng box.
- Lý do các candidate bị loại.

Metadata này cần giữ lại để audit dataset và làm biểu đồ cho báo cáo.

## Cần Bao Nhiêu Ảnh Để Train YOLO26n?

`2000` ảnh không quá nhiều đối với object detection. Với bài toán một class,
một map và dùng trọng số COCO pretrained, đây là quy mô baseline vừa phải.
YOLO26n đã học class `car` từ COCO, nên ta đang fine-tune miền hình ảnh CARLA
thay vì train từ đầu.

Khuyến nghị cho giai đoạn đầu:

- Train: 1500-2000 ảnh sạch từ nhiều session và traffic seed.
- Validation: 300-500 ảnh từ session riêng.
- Test: 200-300 ảnh từ session riêng, không dùng để chỉnh model.
- Mục tiêu tối thiểu khoảng 5000 vehicle instance trong tập train sau lọc.

Không nên cố đủ 2000 bằng một lượt chạy dài. Tốt hơn là thu 4-5 session, mỗi
session 300-500 ảnh, thay đổi seed và điều kiện traffic. Đánh giá learning curve
ở các mốc 500, 1000, 1500 và 2000 ảnh; nếu metric và lỗi AEB không còn cải thiện
thì dừng thu thêm.

Tài liệu fine-tune chính thức của Ultralytics xem dataset dưới 1000 ảnh là
dataset nhỏ và đề xuất giảm augmentation, learning rate và số epoch. Với
1500-2000 ảnh đa dạng, có thể bắt đầu bằng pretrained `yolo26n.pt`, `imgsz=640`
và 100 epoch, sau đó dùng early stopping thay vì đoán số epoch cố định.

## Kiểm Tra Trước Khi Train

1. Xem ngẫu nhiên ít nhất 100 ảnh trong `previews/train`.
2. Kiểm tra xe bị che khuất có bị gắn box sai không.
3. Kiểm tra xe nhỏ ở xa có box quá nhiễu không.
4. Kiểm tra xe ở làn đối diện và làn bên cạnh.
5. Đếm phân bố kích thước box và khoảng cách.
6. Đảm bảo validation được thu từ session riêng.

Ground truth tự động giảm công gán nhãn, nhưng không loại bỏ bước kiểm tra chất
lượng dataset.

## Nguồn CARLA

- [CARLA - Bounding boxes](https://carla.readthedocs.io/en/latest/tuto_G_bounding_boxes/)
- [CARLA 0.9.11 - Synchronous mode](https://carla.readthedocs.io/en/0.9.11/adv_synchrony_timestep/)
- [CARLA 0.9.11 - Traffic Manager](https://carla.readthedocs.io/en/0.9.11/adv_traffic_manager/)
- [CARLA - Depth camera](https://carla.readthedocs.io/en/0.9.11/ref_sensors/)
- [CarFree - Automatic ground truth generation](https://github.com/AveesLab/CarFree)
- [Improving bounding box in CARLA](https://github.com/Mofeed-Chaar/Improving-bouning-box-in-Carla-simulator)
- [Ultralytics - YOLO26 training recipe](https://github.com/ultralytics/ultralytics/blob/main/docs/en/guides/yolo26-training-recipe.md)
- [Ultralytics - YOLO26](https://github.com/ultralytics/ultralytics/blob/main/docs/en/models/yolo26.md)

## So Sánh Với Collector Cũ

File `aeb_old/collect_dataset.py` có các ý đúng: camera RGB/depth cùng
transform, dùng snapshot actor, lọc box nhỏ và kiểm tra occlusion.

Phiên bản mới thay đổi:

- Không dùng `LifoQueue`, vì nó có thể bỏ frame cần ghép.
- Ghép snapshot, RGB, depth và semantic bằng frame tuyệt đối.
- Không chạy traffic ở client khác.
- Dùng semantic vehicle tag cùng depth thay vì chỉ depth.
- Sửa quy ước visibility thành `đủ pixel nhìn thấy thì giữ`; điều kiện giữa
  `check_occlusion()` và nơi gọi trong collector cũ đang bị đảo.
- Box train được siết vào pixel xe nhìn thấy thay vì giữ nguyên cuboid thô.
