# Quick Start

## 1. Kiểm tra repository và workspace

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
git status --short --branch
../venv/bin/python scripts/check_workspace.py
/usr/bin/python3 launcher.py --check
```

Workspace mặc định là `/home/mvhoang/CARLA_0.9.11/aeb_workspace`. Nếu đặt ở
máy khác:

```bash
export AEB_WORKSPACE_ROOT=/path/to/aeb_workspace
```

## 2. Chạy unit/claim gates

```bash
../venv/bin/python -m unittest discover -s tests -q
../venv/bin/python scripts/validate_v4_manuscript_claims.py
../venv/bin/python scripts/validate_v5_manuscript_claims.py
```

## 3. Khởi động CARLA

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia \
  ./CarlaUE4.sh -quality-level=Low
```

Không thêm `-opengl` trên máy đã kiểm chứng.

## 4. Chạy một scenario

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/smoke_basic.yaml \
  --scenario ccrs_30 --control-mode physics --load-map
```

Log mới được ghi vào `$AEB_WORKSPACE_ROOT/runs/logs/`.

## 5. Fusion/CUDA

Dùng `configs/sensors_fusion_hard_batch_gpu.yaml` hoặc
`configs/sensors_fusion_safe_fallback_batch_gpu.yaml`. Thiếu
`CUDAExecutionProvider` hoặc có inference error là technical hard-stop; không
được diễn giải thành algorithm FAIL.
