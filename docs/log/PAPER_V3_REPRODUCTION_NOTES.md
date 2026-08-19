# Paper V3 Reproduction Notes

Mục tiêu file này là ghi lại các thao tác chạy lại thí nghiệm phục vụ cải tiến `paper_v3`/chuẩn bị `paper_v4`. Nguyên tắc: chạy baseline hiện tại trước khi sửa thuật toán, giữ nguyên cả case PASS và FAIL, không chọn riêng run đẹp.

## 2026-08-18 — Chuẩn bị môi trường và smoke test

### Môi trường/code

- Working directory: `/home/mvhoang/CARLA_0.9.11/aeb`
- CARLA Python: `/home/mvhoang/CARLA_0.9.11/venv/bin/python`
- Launcher trực quan nên chạy bằng system Python vì venv CARLA không có `tkinter`:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/usr/bin/python3 laucher.py
```

- Đã sửa các script trong `venv/bin/` từng hard-code nhầm `carla_env` sang đúng path `venv`, để `source /home/mvhoang/CARLA_0.9.11/venv/bin/activate` trả về Python 3.7.17.
- Commit tại thời điểm ghi môi trường:

```text
f3065f2cfb6b3c471496a272bafc879b1c44acf5
```

- Working tree có file/thư mục chưa track:

```text
?? report/exports/
```

### Artifact môi trường đã lưu

```text
outputs/paper_v3_reproduction/environment/
```

Các file đã ghi:

- `uname.txt`
- `nvidia_smi.txt`
- `python_carla.txt`
- `python_yolo.txt`
- `git_commit.txt`
- `git_status.txt`
- `requirements_carla.txt`
- `requirements_yolo.txt`
- `model_sha256.txt`

Model hash:

```text
9665c77f9ca64d058fcd92955275de2bd7bed87700b53daf67e16cad5c8b1963  models/yolo26n_aeb_v7.pt
dc0a6ca1754a0c179357368b15bab5211bd95931c6373d721faeb86ae071c42a  models/yolo26n_aeb_v7.onnx
```

### Kiểm tra ban đầu

Unit test:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Kết quả:

```text
Ran 43 tests in 0.015s
OK
```

### CARLA server

CARLA được chạy bằng:

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 \
__GLX_VENDOR_LIBRARY_NAME=nvidia \
./CarlaUE4.sh -quality-level=Low
```

Trạng thái sau khi chạy: port `127.0.0.1:2000` mở.

### Smoke test fusion — PASS

Lệnh:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --scenario ccrm_60_30_gap_20 \
  --repeat 1 \
  --run-id paper_v3_cmd_smoke_fusion \
  --load-map \
  --scenario-cooldown-s 1.0 \
  --reload-world-wait-s 2.0
```

Kết quả:

```text
ccrm_60_30_gap_20: PASS, brake=True, collision=False, min_gap=14.17 m
```

Log:

```text
logs/paper_v3_cmd_smoke_fusion/
```

### Smoke test radar-only — PASS

Lệnh:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --scenario ccrm_60_30_gap_20 \
  --repeat 1 \
  --run-id paper_v3_cmd_smoke_radar_only \
  --load-map \
  --scenario-cooldown-s 1.0 \
  --reload-world-wait-s 2.0
```

Kết quả:

```text
ccrm_60_30_gap_20: PASS, brake=True, collision=False, min_gap=14.17 m
```

Log:

```text
logs/paper_v3_cmd_smoke_radar_only/
```

### Boundary sanity check fusion — tái hiện FAIL có phanh

Lệnh:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --scenario ccrb_95_gap_20 \
  --repeat 1 \
  --run-id paper_v3_cmd_boundary_fusion \
  --load-map \
  --scenario-cooldown-s 1.0 \
  --reload-world-wait-s 2.0
```

Kết quả:

```text
ccrb_95_gap_20: FAIL, brake=True, collision=True, min_gap=0.024 m
```

Log:

```text
logs/paper_v3_cmd_boundary_fusion/
```

Diễn giải cho paper: case này không phải không kích hoạt phanh; hệ thống có phanh nhưng khoảng cách/tốc độ nằm ngoài biên đủ để tránh va chạm.

## 2026-08-18 — Probe đề xuất tiếp theo

Trước khi chạy full `66 x repeat`, chạy probe 1 case x10 để kiểm tra độ ổn định lặp. Case ưu tiên:

```text
ccrb_95_gap_20
```

Lệnh dự kiến:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --scenario ccrb_95_gap_20 \
  --repeat 10 \
  --run-id paper_v3_probe_fusion_ccrb_95_gap_20_repeat10 \
  --load-map \
  --scenario-cooldown-s 1.0 \
  --reload-world-wait-s 2.0
```

Lưu ý: exit code có thể khác 0 vì case kỳ vọng không collision nhưng baseline đang collision. Khi đó cần đọc `summary.csv` và kiểm tra đủ 10 row, không coi riêng exit code 1 là crash.

### Kết quả probe `ccrb_95_gap_20` x10

Đã chạy lệnh trên với `run-id`:

```text
paper_v3_probe_fusion_ccrb_95_gap_20_repeat10
```

Log:

```text
logs/paper_v3_probe_fusion_ccrb_95_gap_20_repeat10/
```

Exit code:

```text
1
```

Diễn giải exit code: batch hoàn tất đủ 10 run nhưng trả 1 vì tất cả run đều FAIL theo PASS criteria, không phải CARLA/Python crash.

Tóm tắt từ `summary.csv`:

| Chỉ số | Giá trị |
|---|---:|
| Số run | 10 |
| PASS | 0 |
| FAIL | 10 |
| Brake activated | 10/10 |
| Collision | 10/10 |
| First brake time mean/std | 2.100 / 0.000 s |
| Brake gap mean/std | 18.5658 / 0.0124 m |
| Minimum bumper gap mean/std | 0.0170 / 0.0101 m |
| Minimum bumper gap min/max | -0.009 / 0.024 m |
| Target confirmed rate | 94.05% cho mọi run |
| Radar target--hazard match rate | 100% cho mọi run |

Per-run summary:

| Run | Status | Collision | First brake (s) | Brake gap (m) | Min bumper gap (m) |
|---:|---|---|---:|---:|---:|
| 1 | FAIL | True | 2.1 | 18.562 | 0.022 |
| 2 | FAIL | True | 2.1 | 18.562 | 0.024 |
| 3 | FAIL | True | 2.1 | 18.562 | 0.022 |
| 4 | FAIL | True | 2.1 | 18.603 | -0.009 |
| 5 | FAIL | True | 2.1 | 18.561 | 0.022 |
| 6 | FAIL | True | 2.1 | 18.562 | 0.023 |
| 7 | FAIL | True | 2.1 | 18.561 | 0.013 |
| 8 | FAIL | True | 2.1 | 18.562 | 0.007 |
| 9 | FAIL | True | 2.1 | 18.562 | 0.023 |
| 10 | FAIL | True | 2.1 | 18.561 | 0.023 |

Kết luận tạm thời cho paper: case stress `ccrb_95_gap_20` có hành vi rất ổn định qua 10 lần lặp. Hệ thống luôn chọn đúng target hazard, luôn kích hoạt phanh tại cùng thời điểm mô phỏng, nhưng vẫn va chạm với gap gần 0 m. Evidence này củng cố diễn giải ``insufficient-distance boundary'' thay vì perception miss.

### Probe PASS đối xứng `ccrb_80_gap_20` x10

Mục tiêu: chạy một case CCRb cùng gap 20 m nhưng trong dải mục tiêu/pass để so sánh với `ccrb_95_gap_20`.

Lần thử đầu dùng default `--reload-world-every 1` và `run-id`:

```text
paper_v3_probe_fusion_ccrb_80_gap_20_repeat10
```

Kết quả: chạy được 4/10 run đều PASS, sau đó CARLA timeout khi `reload_world()`:

```text
RuntimeError: time-out of 10000ms while waiting for the simulator
```

Diễn giải: đây là server/reload stability issue, không phải FAIL scenario. Thư mục partial có 4 CSV nhưng không có summary hoàn chỉnh vì script dừng trong `finally`.

Sau đó restart CARLA và chạy lại cùng case với `--reload-world-every 0`:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --scenario ccrb_80_gap_20 \
  --repeat 10 \
  --run-id paper_v3_probe_fusion_ccrb_80_gap_20_repeat10_noreload \
  --load-map \
  --scenario-cooldown-s 1.0 \
  --reload-world-every 0 \
  --reload-world-wait-s 2.0
```

Log hoàn chỉnh:

```text
logs/paper_v3_probe_fusion_ccrb_80_gap_20_repeat10_noreload/
```

Exit code:

```text
0
```

Tóm tắt từ `summary.csv`:

| Chỉ số | Giá trị |
|---|---:|
| Số run | 10 |
| PASS | 10 |
| FAIL | 0 |
| Brake activated | 10/10 |
| Collision | 0/10 |
| First brake time mean/std | 2.100 / 0.000 s |
| Brake gap mean/std | 18.5737 / 0.0188 m |
| Minimum bumper gap mean/std | 1.9655 / 0.0115 m |
| Minimum bumper gap min/max | 1.955 / 1.991 m |
| Target confirmed rate | 97.83% cho mọi run |
| Radar target--hazard match rate | 100% cho mọi run |

Per-run summary:

| Run | Status | Collision | First brake (s) | Brake gap (m) | Min bumper gap (m) |
|---:|---|---|---:|---:|---:|
| 1 | PASS | False | 2.1 | 18.556 | 1.956 |
| 2 | PASS | False | 2.1 | 18.598 | 1.978 |
| 3 | PASS | False | 2.1 | 18.556 | 1.956 |
| 4 | PASS | False | 2.1 | 18.600 | 1.991 |
| 5 | PASS | False | 2.1 | 18.579 | 1.963 |
| 6 | PASS | False | 2.1 | 18.557 | 1.958 |
| 7 | PASS | False | 2.1 | 18.556 | 1.955 |
| 8 | PASS | False | 2.1 | 18.580 | 1.963 |
| 9 | PASS | False | 2.1 | 18.599 | 1.976 |
| 10 | PASS | False | 2.1 | 18.556 | 1.959 |

Kết luận tạm thời cho paper: cặp `ccrb_80_gap_20` và `ccrb_95_gap_20` có thời điểm phanh gần như giống nhau, đều match đúng hazard 100%, nhưng khác outcome do biên động học/tốc độ. Đây là evidence tốt cho lập luận boundary stability: 80 km/h còn margin khoảng 1.96 m, 95 km/h collision sát 0 m.

Ghi chú vận hành: default `--reload-world-every 1` có thể gây timeout khi lặp nhiều lần. Với probe một scenario, `--reload-world-every 0` chạy ổn hơn. Nếu chạy full suite dài vẫn cần cân nhắc trade-off giữa reload để dọn actor và rủi ro timeout reload.

### Boundary probe mở rộng CCRb với chính sách no-reload

Sau khi thống nhất nên dùng cùng chính sách vận hành, các probe CCRb dưới đây đều chạy với:

```text
--control-mode physics
--repeat 10
--scenario-cooldown-s 1.0
--reload-world-every 0
```

Run directories:

```text
logs/paper_v3_probe_fusion_ccrb_80_gap_20_repeat10_noreload/
logs/paper_v3_probe_fusion_ccrb_95_gap_20_repeat10_noreload/
logs/paper_v3_probe_fusion_ccrb_95_gap_30_repeat10_noreload/
logs/paper_v3_probe_fusion_ccrb_110_gap_20_repeat10_noreload/
```

Tóm tắt aggregate từ các `summary.csv`:

| Scenario | Runs | PASS | FAIL | Collision | Brake | First brake mean/std (s) | Brake gap mean/std (m) | Min gap mean/std (m) | Min gap min/max (m) | Hazard match |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `ccrb_80_gap_20` | 10 | 10 | 0 | 0 | 10 | 2.100/0.000 | 18.574/0.019 | 1.966/0.011 | 1.955/1.991 | 100.0% |
| `ccrb_95_gap_20` | 10 | 0 | 10 | 10 | 10 | 2.100/0.000 | 18.568/0.014 | 0.019/0.009 | -0.007/0.025 | 100.0% |
| `ccrb_95_gap_30` | 10 | 10 | 0 | 0 | 10 | 2.300/0.000 | 27.024/0.000 | 3.885/0.001 | 3.884/3.888 | 100.0% |
| `ccrb_110_gap_20` | 10 | 0 | 10 | 10 | 10 | 2.100/0.000 | 18.563/0.001 | 0.074/0.022 | 0.007/0.084 | 100.0% |

Nhận xét kỹ thuật:

- Cả bốn probe đều đủ 10 run, không missing run khi dùng `--reload-world-every 0`.
- Tất cả run đều kích hoạt phanh và radar target--hazard match đạt 100%.
- Cặp cùng gap 20 m cho thấy biên theo tốc độ: 80 km/h PASS ổn định, 95 và 110 km/h collision ổn định.
- Cặp cùng 95 km/h cho thấy biên theo gap: gap 20 m FAIL ổn định, gap 30 m PASS ổn định.
- Đây là evidence tốt cho mục ``boundary stability'' của paper, nhưng vẫn chỉ là local probe quanh CCRb, chưa thay thế full-suite repeat, radar-only ablation, negative regression hoặc controller ablation.

## 2026-08-18 — Kế hoạch leo thang full-suite repeat

Không chạy ngay `66 x 10 = 660` run vì CARLA 0.9.11 từng timeout khi `reload_world()` và full suite rất tốn thời gian. Quy trình leo thang được chọn:

1. **Full fusion 66 case x3** để kiểm tra ổn định suite dài và phát hiện case đảo outcome.
2. Nếu x3 ổn, chạy **full fusion 66 case x5** để có evidence đủ mạnh hơn cho `paper_v4`.
3. Chỉ chạy **full fusion 66 case x10** nếu x5 ổn, còn thời gian/dung lượng, và cần bảng repeatability mạnh hơn.

Chính sách vận hành trước mắt:

```text
--control-mode physics
--load-map
--scenario-cooldown-s 1.0
--reload-world-every 0
```

Lý do dùng `--reload-world-every 0`: trong probe `ccrb_80_gap_20`, default reload từng scenario làm CARLA timeout ở run 5/10. No-reload đã chạy ổn các probe repeat10. Nếu full suite no-reload gặp actor/state leak, phương án fix là chia suite thành nhiều shard nhỏ hoặc sửa runner để checkpoint summary sau từng scenario và xử lý reload timeout mềm hơn.

### Lệnh full fusion 66 case x3

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --repeat 3 \
  --run-id paper_v3_fusion_full66_repeat3_noreload \
  --load-map \
  --scenario-cooldown-s 1.0 \
  --reload-world-every 0 \
  --reload-world-wait-s 2.0
```

### Lệnh dự kiến nếu x3 ổn: full fusion 66 case x5

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --repeat 5 \
  --run-id paper_v3_fusion_full66_repeat5_noreload \
  --load-map \
  --scenario-cooldown-s 1.0 \
  --reload-world-every 0 \
  --reload-world-wait-s 2.0
```

### Lệnh dự kiến nếu x5 vẫn ổn và cần x10

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --repeat 10 \
  --run-id paper_v3_fusion_full66_repeat10_noreload \
  --load-map \
  --scenario-cooldown-s 1.0 \
  --reload-world-every 0 \
  --reload-world-wait-s 2.0
```

### Kết quả full fusion 66 case x3

Run ID:

```text
paper_v3_fusion_full66_repeat3_noreload
```

Log:

```text
logs/paper_v3_fusion_full66_repeat3_noreload/
```

Exit code:

```text
1
```

Diễn giải exit code: batch hoàn tất đủ 198/198 run nhưng trả 1 vì có các scenario FAIL theo PASS criteria. Đây không phải crash.

Tổng quan:

| Chỉ số | Giá trị |
|---|---:|
| Scenario cấu hình | 66 |
| Repeat mỗi scenario | 3 |
| Tổng run | 198 |
| PASS run | 189 |
| FAIL run | 9 |
| Collision run | 9 |
| Brake activated | 198/198 |
| Scenario all-PASS | 63 |
| Scenario all-FAIL | 3 |
| Scenario mixed PASS/FAIL | 0 |
| Missing run | 0 |

Theo family:

| Family | Runs | PASS | FAIL | Collision |
|---|---:|---:|---:|---:|
| CCRm | 72 | 72 | 0 | 0 |
| CCRb | 90 | 84 | 6 | 6 |
| Cut-in | 36 | 33 | 3 | 3 |

Ba scenario all-FAIL, đúng với final evidence single-run:

| Scenario | Runs | Status | Collision | Brake | First brake | Brake gap | Min bumper gap |
|---|---:|---|---|---|---:|---:|---:|
| `ccrb_95_gap_20` | 3 | 3/3 FAIL | 3/3 | 3/3 | 2.1 s mọi run | 18.562--18.563 m | 0.009--0.023 m |
| `ccrb_110_gap_20` | 3 | 3/3 FAIL | 3/3 | 3/3 | 2.1 s mọi run | 18.564--18.608 m | 0.007--0.081 m |
| `cutin_100_60_gap_25` | 3 | 3/3 FAIL | 3/3 | 3/3 | 1.6 s mọi run | 7.257--7.303 m | 0.477--0.480 m |

Các scenario có dao động `minimum_bumper_gap_m` lớn nhất trong x3:

| Scenario | Mean min gap | Std | Range | Min--max |
|---|---:|---:|---:|---:|
| `cutin_100_60_gap_35` | 8.196 m | 0.724 m | 1.557 m | 7.662--9.219 m |
| `ccrb_95_gap_60` | 9.545 m | 0.284 m | 0.605 m | 9.143--9.748 m |
| `cutin_80_50_gap_35` | 14.235 m | 0.217 m | 0.531 m | 13.960--14.491 m |
| `ccrb_65_gap_80` | 7.427 m | 0.181 m | 0.385 m | 7.299--7.684 m |

Nhận xét:

- Full-suite x3 chạy xong không crash khi dùng `--reload-world-every 0`.
- Không có scenario nào đảo outcome giữa các lần lặp: 63 scenario luôn PASS, 3 scenario luôn FAIL.
- Ba FAIL vẫn là ba case đã công bố trong `paper_v3`, củng cố claim boundary thay vì random single-run artifact.
- Một số cut-in/gap lớn có dao động min-gap cỡ 0.5--1.6 m dù outcome vẫn PASS. Điều này nên được ghi trong paper như residual simulator/actor scheduling variability, không diễn giải thành reliability thống kê.
- Vì x3 ổn, có thể nâng lên x5 theo đúng kế hoạch. Tuy nhiên trước khi x5 nên cân nhắc sinh script aggregate tự động để tránh chép tay bảng kết quả.

### Script aggregate tự động

Đã thêm script:

```text
scripts/summarize_repeatability.py
```

Mục tiêu: đọc `summary.csv` của một run directory và sinh bảng repeatability theo family/scenario, tránh chép tay khi viết paper/report.

Lệnh đã chạy cho full66 x3:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/summarize_repeatability.py \
  logs/paper_v3_fusion_full66_repeat3_noreload \
  --output-dir outputs/paper_v3_reproduction/repeatability/paper_v3_fusion_full66_repeat3_noreload
```

Output:

```text
outputs/paper_v3_reproduction/repeatability/paper_v3_fusion_full66_repeat3_noreload/repeatability_summary.md
outputs/paper_v3_reproduction/repeatability/paper_v3_fusion_full66_repeat3_noreload/repeatability_summary.json
outputs/paper_v3_reproduction/repeatability/paper_v3_fusion_full66_repeat3_noreload/repeatability_by_family.csv
outputs/paper_v3_reproduction/repeatability/paper_v3_fusion_full66_repeat3_noreload/repeatability_by_scenario.csv
```

Khi chạy x5/x10, dùng cùng script với run directory tương ứng để sinh bảng tự động trước khi đưa vào paper.
