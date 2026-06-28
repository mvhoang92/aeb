# System Limit Sweep - 2026-06-27

## Mục Tiêu

Tìm giới hạn hoạt động của controller chính hiện tại `staged_pid`, thay vì chỉ
tạo một bộ test toàn PASS. Sweep đầu tiên tập trung vào bài toán CCRs cơ bản:
xe mục tiêu đứng yên cùng làn, ego chạy trên cao tốc Town04.

## Cấu Hình

- Controller: `staged_pid`.
- Config scenario: `configs/system_limit_ccrs_sweep.yaml`.
- Runner: `scripts/run_radar_aeb_scenarios.py`.
- Log: `logs/system_limit_ccrs_sweep_20260627_01`.
- Heatmap sinh tự động:
  `logs/system_limit_ccrs_sweep_20260627_01/system_limit_heatmap.md`.

Lệnh chạy:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/system_limit_ccrs_sweep.yaml \
  --control-mode physics \
  --load-map \
  --run-id system_limit_ccrs_sweep_20260627_01 || true
```

Lệnh tạo heatmap:

```bash
../venv/bin/python scripts/summarize_system_limit_sweep.py \
  logs/system_limit_ccrs_sweep_20260627_01
```

`|| true` là có chủ ý vì sweep giới hạn được phép có FAIL/collision.

## Heatmap CCRs

| Speed \ Gap | 20 m | 30 m | 40 m | 50 m | 60 m | 80 m | 100 m |
|---|---|---|---|---|---|---|---|
| 40 km/h | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 50 km/h | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 60 km/h | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 70 km/h | COLLISION | PASS | PASS | PASS | PASS | PASS | PASS |
| 80 km/h | COLLISION | PASS | PASS | PASS | PASS | PASS | PASS |
| 90 km/h | COLLISION | COLLISION | PASS | PASS | PASS | PASS | PASS |
| 100 km/h | COLLISION | COLLISION | COLLISION | PASS | PASS | PASS | PASS |
| 110 km/h | COLLISION | COLLISION | COLLISION | COLLISION | PASS | PASS | PASS |

## Gap PASS Nhỏ Nhất Trong Sweep

| Speed | Min PASS gap |
|---:|---:|
| 40 km/h | 20 m |
| 50 km/h | 20 m |
| 60 km/h | 20 m |
| 70 km/h | 30 m |
| 80 km/h | 30 m |
| 90 km/h | 40 m |
| 100 km/h | 50 m |
| 110 km/h | 60 m |

## Case Fail

| Scenario | Collision | Min gap |
|---|---:|---:|
| `ccrs_70_gap_20` | True | 0.023 m |
| `ccrs_80_gap_20` | True | 0.100 m |
| `ccrs_90_gap_20` | True | -0.132 m |
| `ccrs_90_gap_30` | True | -0.083 m |
| `ccrs_100_gap_20` | True | 0.058 m |
| `ccrs_100_gap_30` | True | 0.042 m |
| `ccrs_100_gap_40` | True | -0.003 m |
| `ccrs_110_gap_20` | True | 0.065 m |
| `ccrs_110_gap_30` | True | 0.132 m |
| `ccrs_110_gap_40` | True | 0.075 m |
| `ccrs_110_gap_50` | True | -0.003 m |

## Nhận Xét

Kết quả này phù hợp với cách đánh giá như một sản phẩm thật:

- Không cố làm mọi scenario đều PASS.
- Có vùng hoạt động tốt rõ ràng.
- Có vùng ngoài giới hạn gây collision rõ ràng.
- Fail chủ yếu xuất hiện khi tốc độ cao và gap quá ngắn, tức là không đủ khoảng
  cách vật lý để dừng.

Dải hoạt động hợp lý hiện tại cho CCRs cùng làn, thời tiết lý tưởng, radar 100 m:

- 40-60 km/h: pass cả gap 20 m trong sweep này.
- 70-80 km/h: cần gap khoảng 30 m trở lên.
- 90 km/h: cần gap khoảng 40 m trở lên.
- 100 km/h: cần gap khoảng 50 m trở lên.
- 110 km/h: cần gap khoảng 60 m trở lên.

ODD đề xuất cho báo cáo giai đoạn này:

```text
Hệ thống AEB mô phỏng hoạt động ổn định nhất ở 50-80 km/h trên cao tốc,
target là ô tô cùng làn, thời tiết lý tưởng, radar nhìn thấy target trong tầm
100 m. Với 80 km/h, gap 30 m trở lên pass trong sweep CCRs hiện tại. Các tình
huống tốc độ cao hơn hoặc gap ngắn hơn được xem là vùng biên/ngoài ODD và có
thể collision.
```

## Bước Tiếp Theo

- Thêm sweep cho moving lead: ego nhanh hơn xe trước.
- Thêm sweep cho braking lead: xe trước phanh gấp ở nhiều gap.
- Thêm sweep cut-in sát/xa để xác định giới hạn khi target xuất hiện muộn.
- Sau khi có các sweep này, tổng hợp thành bảng ODD chính thức của project.
