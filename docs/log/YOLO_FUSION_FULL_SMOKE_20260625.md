# Báo Cáo Smoke Test YOLO, Fusion Và Full AEB - 2026-06-25

## Mục Tiêu

Kiểm tra nhanh ba lớp runtime sau khi đã có model YOLO mới:

1. YOLO ONNX có load và detect xe trong ảnh camera CARLA không.
2. Fusion có chiếu radar point vào bbox YOLO và match được không.
3. Full radar-only AEB scenario còn PASS không.

## Lệnh Chạy

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/smoke_yolo_fusion_full.py \
  --timeout 30 \
  --load-map \
  --target-gap-m 18 \
  --run-id smoke_full_after_nms_20260625 \
  --output logs/smoke_yolo_fusion_full_after_nms_20260625.json
```

## Kết Quả YOLO/Fusion

| Hạng mục | Kết quả |
| --- | --- |
| Status | PASS |
| Runtime | ONNX CUDA |
| Camera frame | 252045 |
| Radar frame | 252045 |
| Raw radar points | 60 |
| Projected radar points | 26 |
| YOLO detections | 1 |
| Matched boxes | 1 |
| Best class | car |
| Best confidence | 0.9821 |
| Actual bumper gap | 18.0 m |
| Radar matched distance | 17.92 m |
| Radar lateral | -0.039 m |

Ảnh debug:

```text
logs/smoke_debug/smoke_full_after_nms_20260625_yolo_fusion.png
```

Nhận xét:

- YOLO nhận đúng xe phía trước với confidence cao.
- Radar point được project vào vùng xe và match với bbox.
- Khoảng cách radar `17.92 m` khớp với bumper gap test `18.0 m`.

## Kết Quả Full Radar-AEB

Scenario:

```text
ccrs_60_demo_150
```

Kết quả:

| Hạng mục | Giá trị |
| --- | ---: |
| Status | PASS |
| Collision | False |
| Brake activated | True |
| First warning | 6.45 s |
| First brake | 7.40 s |
| Brake speed | 60.039 km/h |
| Brake gap | 24.631 m |
| Minimum bumper gap | 7.704 m |
| Radar target match hazard | 100% |

Log scenario:

```text
logs/smoke_full_after_nms_20260625/ccrs_60_demo_150.csv
```

## Lỗi Phát Hiện Và Đã Sửa

### 1. Smoke script spawn target sai nhánh đường

Triệu chứng:

- YOLO detect `0 object`.
- Camera không thấy xe target.
- Radar vẫn có point, nhưng point chủ yếu nằm trên mặt đường.

Nguyên nhân:

- Smoke script dùng `waypoint.next()` ở Town04. Ở một số spawn point, CARLA có
  thể chọn nhánh waypoint không nằm trong hướng nhìn camera.
- Ngoài ra, script lấy `ego.get_transform()` ngay sau `try_spawn_actor`, trước
  khi `world.tick()`, nên transform ego chưa ổn định.

Sửa:

- Sau khi spawn ego, tick world một lần rồi mới lấy transform.
- Spawn target tạm ở vị trí hợp lệ, tắt physics, sau đó teleport target tới vị
  trí trước mũi ego theo transform đã ổn định.
- Lưu ảnh debug để kiểm chứng bằng mắt.

File sửa:

```text
scripts/smoke_yolo_fusion_full.py
```

### 2. ONNX YOLO có thể trả bbox trùng

Triệu chứng:

- Một số ảnh dataset xuất hiện hai bbox gần như trùng nhau trên cùng một xe.

Sửa:

- Thêm NMS đơn giản sau bước parse ONNX output.
- Thêm config `model.nms_iou`.
- Thêm unit test cho NMS.

File sửa:

```text
ui/manual_control_common.py
configs/sensors.yaml
tests/test_onnx_model_names.py
```

## Verify Sau Sửa

```bash
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Kết quả:

```text
Ran 29 tests
OK
```

Launcher check:

```text
CARLA script       OK
CARLA Python       OK
YOLO Python        OK
Sensor config      OK
Scenario config    OK
Scenarios          29
```

## Kết Luận

- YOLO runtime với model `yolo26n_aeb_v7.onnx` chạy được trên ONNX CUDA.
- Fusion camera-radar hoạt động ở mức smoke test: bbox xe có radar point khớp.
- Full radar-only AEB scenario vẫn PASS sau các sửa.
- Bước tiếp theo nên là tích hợp fusion vào decision AEB hoặc tiếp tục nâng cấp
  bộ điều khiển phanh nhiều tầng/PID để giảm jerk.
