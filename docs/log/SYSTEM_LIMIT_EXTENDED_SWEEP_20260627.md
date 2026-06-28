# System Limit Extended Sweep - 2026-06-27

## Mục Tiêu

Mở rộng bài test giới hạn hệ thống sau CCRs đứng yên. Mục tiêu không phải làm
mọi trường hợp đều pass, mà tìm rõ vùng hoạt động tốt và vùng bắt đầu vượt quá
khả năng phanh hiện tại của controller `staged_pid`.

## Cấu Hình

- Controller: `staged_pid`.
- Config scenario: `configs/system_limit_extended_sweep.yaml`.
- Runner: `scripts/run_radar_aeb_scenarios.py`.
- Log: `logs/system_limit_extended_sweep_20260627_01`.
- Heatmap:
  `logs/system_limit_extended_sweep_20260627_01/system_limit_heatmap.md`.
- Tổng số case: 66.
- Kết quả: 64 PASS, 2 FAIL.

Lệnh chạy:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/system_limit_extended_sweep.yaml \
  --control-mode physics \
  --load-map \
  --run-id system_limit_extended_sweep_20260627_01 || true
```

Lệnh tạo heatmap:

```bash
../venv/bin/python scripts/summarize_system_limit_sweep.py \
  logs/system_limit_extended_sweep_20260627_01
```

`|| true` là có chủ ý vì bài test giới hạn được phép có FAIL/collision.

## Heatmap Tóm Tắt

### CCRm - Xe Trước Chạy Chậm Hơn

| Ego/Target | 20 m | 30 m | 40 m | 50 m | 60 m | 80 m |
|---|---|---|---|---|---|---|
| 60/30 km/h | PASS | PASS | PASS | PASS | PASS | PASS |
| 80/50 km/h | PASS | PASS | PASS | PASS | PASS | PASS |
| 100/70 km/h | PASS | PASS | PASS | PASS | PASS | PASS |
| 110/80 km/h | PASS | PASS | PASS | PASS | PASS | PASS |

Nhận xét: nhóm này pass toàn bộ vì vận tốc tương đối chỉ khoảng 30 km/h. Đây là
kiểu tình huống cao tốc khá thực tế: xe trước vẫn đang chạy, ego chỉ cần giảm
tốc/phanh để giữ khoảng cách.

### CCRb - Xe Trước Phanh Gấp

| Speed | 20 m | 30 m | 40 m | 50 m | 60 m | 80 m |
|---|---|---|---|---|---|---|
| 50 km/h | PASS | PASS | PASS | PASS | PASS | PASS |
| 65 km/h | PASS | PASS | PASS | PASS | PASS | PASS |
| 80 km/h | PASS | PASS | PASS | PASS | PASS | PASS |
| 95 km/h | PASS | PASS | PASS | PASS | PASS | PASS |
| 110 km/h | COLLISION | PASS | PASS | PASS | PASS | PASS |

Nhận xét: case biên rõ nhất là `110 km/h, gap 20 m`. Dưới mức này hoặc ở gap lớn
hơn, controller hiện tại vẫn tránh va chạm được trong mô phỏng.

### Cut-in - Xe Cắt Làn Vào Trước Ego

| Ego/Cut-in | 25 m | 35 m | 45 m | 60 m |
|---|---|---|---|---|
| 60/40 km/h | PASS | PASS | PASS | PASS |
| 80/50 km/h | PASS | PASS | PASS | PASS |
| 100/60 km/h | COLLISION | PASS | PASS | PASS |

Nhận xét: case `100/60 km/h, gap 25 m` bị collision. Đây là giới hạn hợp lý vì
target xuất hiện muộn trong hành lang ego, vận tốc tương đối lớn và khoảng cách
còn lại quá ngắn.

## Case Fail

| Scenario | Nhóm | Collision | Min gap |
|---|---|---:|---:|
| `ccrb_110_gap_20` | Xe trước phanh gấp | True | 0.054 m |
| `cutin_100_60_gap_25` | Cut-in | True | 0.274 m |

## Kết Luận ODD Tạm Thời

Kết hợp với sweep CCRs đứng yên trước đó:

- Dải mục tiêu 50-80 km/h là hợp lý và đang ổn.
- Với target đứng yên cùng làn, 80 km/h cần khoảng 30 m trở lên.
- Với xe trước còn chạy chậm hơn ego, hệ thống ổn hơn vì vận tốc tương đối nhỏ.
- Với xe trước phanh gấp, hệ thống vẫn ổn tới 95 km/h ở gap 20 m trong sweep này,
  nhưng 110 km/h gap 20 m là ngoài giới hạn.
- Với cut-in, hệ thống ổn ở 60-80 km/h trong các gap đã thử; ở 100 km/h, cut-in
  chỉ cách 25 m là ngoài giới hạn.

ODD nên dùng cho báo cáo giai đoạn hiện tại:

```text
Hệ thống AEB mô phỏng hoạt động tốt nhất trên cao tốc, thời tiết lý tưởng, chỉ
ô tô, target cùng làn hoặc cắt làn rõ ràng, tốc độ ego khoảng 50-80 km/h. Các
tình huống trên 100 km/h với gap ngắn, target đứng yên hoặc cut-in muộn được xem
là vùng biên/ngoài ODD và có thể collision.
```

## Bước Tiếp Theo

- Gom kết quả CCRs + extended sweep thành một bảng ODD chính thức.
- Tạo script batch so sánh nhiều brake mode nếu cần đối chiếu lịch sử.
- Làm UI demo ba vùng và log dễ đọc/video evidence cho các case đại diện:
  - một case pass đẹp trong ODD;
  - một case fail ngoài ODD;
  - một case cut-in pass;
  - một case braking-lead sát biên.
