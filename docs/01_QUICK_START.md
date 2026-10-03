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
../venv/bin/python scripts/validate_v51_manuscript_claims.py
```

Mỗi validator in một dòng `PASS: ...` và trả exit code 0.

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

```bash
../venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --sensor-config configs/sensors_fusion_safe_fallback_batch_gpu.yaml \
  --scenario-config configs/scenarios/suites/smoke_basic.yaml \
  --control-mode physics
```

### Thư viện CUDA (`AEB_CUDA_LIBRARY_PATH`)

cuDNN hệ thống (`libcudnn8 8.9.7+cuda12.2`) cần `libcublasLt.so.12`, file này
chỉ có trong `/usr/local/cuda-11.7/lib64` và chỉ được `~/.bashrc` thêm vào
`LD_LIBRARY_PATH` ở shell tương tác. Vì vậy khi chạy qua ssh, `nohup` hoặc
launcher mở từ menu desktop, runner trước đây chết với SIGABRT.

Hiện tại `run_fusion_aeb_scenarios.py` (và `ui/fusion_view.py`,
`ui/yolo_view.py`, `ui/aeb_demo_view.py` — kể cả khi được
`scripts/record_scenario_videos.py` gọi — và
`scripts/campaign/smoke_yolo_fusion_full.py`) tự xử lý:

1. Tìm thư mục thư viện CUDA theo thứ tự: biến môi trường
   `AEB_CUDA_LIBRARY_PATH` (danh sách phân tách bằng `:`), khóa
   `model.cuda_library_path` trong sensor config, `/usr/local/cuda-11.7/lib64`,
   cuối cùng là `nvidia/*/lib` của venv (chỉ khi không có CUDA hệ thống, để
   không âm thầm đổi phiên bản cuDNN).
2. Nếu thư mục chưa có trong `LD_LIBRARY_PATH`, tự re-exec Python một lần với
   thư mục đó (glibc chỉ đọc `LD_LIBRARY_PATH` khi process khởi động).
3. Với config bắt buộc CUDA (`require_provider: CUDAExecutionProvider`), probe
   một CUDA session trong subprocess trước khi kết nối CARLA. Nếu lỗi: in
   `TECHNICAL HARD-STOP` kèm tên thư viện thiếu và cách sửa, exit code `3`,
   không tạo run directory. Exit code `1` vẫn chỉ có nghĩa là algorithm FAIL.

Ở máy khác, chỉ định thư mục chứa thư viện thiếu:

```bash
export AEB_CUDA_LIBRARY_PATH=/usr/local/cuda-11.7/lib64
../venv/bin/python -m infrastructure.cuda_runtime models/yolo26n_aeb_v7.onnx
```

Lệnh probe trên in `CUDA probe OK` (exit 0) hoặc thông báo hard-stop (exit 3).
`AEB_CUDA_NO_REEXEC=1` tắt cơ chế re-exec. Môi trường thực tế (phiên bản
onnxruntime, provider, thư mục CUDA và nguồn của nó, `LD_LIBRARY_PATH` lúc
khởi động, cuDNN/CUDA runtime, NVIDIA driver) được ghi vào khóa
`runtime_environment` của `run_metadata.json`.
