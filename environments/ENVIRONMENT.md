# Runtime Environment

Reference workstation on which the frozen v4–v5.2 evidence was produced, and
how to recreate its two Python environments. Captured 2026-10-03; the frozen
capture used by the papers is `docs/log/repeatability/environment_20260818/`
(that one was taken in a ROS 2 shell, so its pip lists also contain the ROS
packages on `PYTHONPATH`; the lock files here were generated with
`env -u PYTHONPATH` and list only the venvs' own packages).

| Item | Value on the reference machine |
|---|---|
| OS | Ubuntu 22.04.5 LTS, kernel 6.8.0-106-generic, x86_64 |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU, 4 GB |
| NVIDIA driver | 580.173.02 (`graphics-drivers` PPA) |
| CARLA | 0.9.11 binary release in `$CARLA_ROOT` (`CarlaUE4.sh`), PythonAPI egg `PythonAPI/carla/dist/carla-0.9.11-py3.7-linux-x86_64.egg` |
| CARLA client Python | 3.7.17 (deadsnakes PPA, `/usr/bin/python3.7`), venv `$CARLA_ROOT/venv` |
| Training/export Python | 3.10.12 (system), venv `$AEB_WORKSPACE_ROOT/environments/yolo310` |
| Launcher GUI Python | system `/usr/bin/python3` (3.10) with `python3-tk` and `python3-yaml` |
| CUDA libraries | CUDA 11.7 in `/usr/local/cuda-11.7` (`cuda-cudart-11-7` 11.7.99, `libcublas-11-7` 11.10.3.66, NVIDIA apt repo `cuda-ubuntu2204-x86_64`) |
| cuDNN | `libcudnn8` 8.9.7.29-1+**cuda12.2** (system apt, `/usr/lib/x86_64-linux-gnu/libcudnn.so.8.9.7`) |
| ONNX Runtime (runtime) | `onnxruntime-gpu` 1.14.1 (CUDA 11.x build) in the CARLA venv |

`$CARLA_ROOT` is the directory that contains the repository checkout
(`/home/mvhoang/CARLA_0.9.11` on the reference machine).

## Lock files

| File | Environment | Packages |
|---|---|---|
| `requirements-carla-py37.lock.txt` | CARLA client venv (runners, UI, validators, unit tests) | 44 |
| `requirements-yolo310.lock.txt` | YOLO training/ONNX export venv | 59 |
| `requirements-ci-py37.txt` | GitHub Actions job (subset; no CARLA/GPU) | 4 |

Both lock files are plain `pip freeze` output (no editable, local-path or VCS
entries) and were checked to resolve with `pip install --dry-run` on
2026-10-03.

## The cuDNN / `libcublasLt.so.12` situation

This machine runs a non-standard CUDA stack, and the validated evidence was
produced with it:

1. ONNX Runtime 1.14.1 is built for CUDA 11.x and loads the system cuDNN 8
   (`libcudnn.so.8`).
2. The installed cuDNN is the **CUDA 12.2 build** (8.9.7.29+cuda12.2). It
   `dlopen`s `libcublasLt.so.12`, which CUDA 11.7 does not ship.
3. A hand-made, root-owned symlink provides that name:
   `/usr/local/cuda-11.7/lib64/libcublasLt.so.12 -> /usr/local/cuda-11.7/lib64/libcublasLt.so.11`
   (the target's SONAME is `libcublasLt.so.11`, so the `.so.12` name is not in
   `ld.so.cache`).
4. The symlink is only found when `/usr/local/cuda-11.7/lib64` is on
   `LD_LIBRARY_PATH`. `~/.bashrc` adds it for interactive shells; ssh, `nohup`
   and desktop launches do not, and creating a CUDA session then aborts the
   interpreter with SIGABRT.

The repository handles this in `infrastructure/cuda_runtime.py`
(user-facing description in `docs/01_QUICK_START.md`, section "Thư viện CUDA"):

- CUDA library dirs are resolved in order: `AEB_CUDA_LIBRARY_PATH`
  (`:`-separated), the sensor config key `model.cuda_library_path`,
  `/usr/local/cuda-11.7/lib64`, and only if no system CUDA dir exists the
  venv's `nvidia/*/lib` wheels (so the validated system cuDNN is never
  silently replaced).
- CUDA entry points re-execute the interpreter once with those dirs prepended
  to `LD_LIBRARY_PATH` (glibc reads it only at process start).
  `AEB_CUDA_NO_REEXEC=1` disables this.
- Configs with `require_provider: CUDAExecutionProvider` probe a CUDA session
  in a subprocess first; failure is a technical hard-stop (exit code 3), never
  an algorithm FAIL (exit code 1).
- The resolved stack is recorded under `runtime_environment` in
  `run_metadata.json`.

Manual probe: `../venv/bin/python -m infrastructure.cuda_runtime
models/yolo26n_aeb_v7.onnx` (prints `CUDA probe OK`, exit 0, or a hard-stop
message, exit 3).

On a **new** machine do not copy the symlink trick. Install a cuDNN 8 build
for CUDA 11 (for example `libcudnn8=8.9.7.29-1+cuda11.8`) together with CUDA
11.x libraries, or point `AEB_CUDA_LIBRARY_PATH` at directories that contain a
consistent set (`libcudart.so.11.0`, `libcublas.so.11`, `libcublasLt.so.11`,
`libcudnn*.so.8`). Results from a different CUDA/cuDNN stack are a new
environment and must be recorded as such.

## Recreating the environments

CARLA client venv (`$CARLA_ROOT/venv`):

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get install python3.7 python3.7-venv python3.7-dev
cd $CARLA_ROOT
/usr/bin/python3.7 -m venv venv
venv/bin/python -m pip install "pip==24.0"
env -u PYTHONPATH venv/bin/python -m pip install -r aeb/environments/requirements-carla-py37.lock.txt
# onnxruntime (CPU) and onnxruntime-gpu share the "onnxruntime" import package;
# make sure the GPU build owns it:
venv/bin/python -m pip install --force-reinstall --no-deps onnxruntime-gpu==1.14.1
venv/bin/python -c "import onnxruntime as o; print(o.get_available_providers())"
```

The last line must list `CUDAExecutionProvider`. `carla` itself is not
installed with pip: the runtime adds the 0.9.11 egg from
`$CARLA_ROOT/PythonAPI/carla/dist/` to `sys.path` (PyPI has no 0.9.11 wheel).

YOLO training/export venv (`$AEB_WORKSPACE_ROOT/environments/yolo310`), from
the repository root:

```bash
/usr/bin/python3.10 -m venv $AEB_WORKSPACE_ROOT/environments/yolo310
$AEB_WORKSPACE_ROOT/environments/yolo310/bin/python -m pip install -U pip
env -u PYTHONPATH $AEB_WORKSPACE_ROOT/environments/yolo310/bin/python \
  -m pip install -r environments/requirements-yolo310.lock.txt
```

This venv carries its own CUDA 12.1 / cuDNN 9 user-space libraries as pip
`nvidia-*-cu12` wheels (torch 2.5.1+cu121, onnxruntime-gpu 1.23.2); it does not
use the system CUDA 11.7 stack. The launcher finds it via `AEB_YOLO_PYTHON` or
the workspace default.

Launcher GUI: `sudo apt-get install python3-tk python3-yaml`.

Then verify with the unit tests and the manuscript validators
(`docs/01_QUICK_START.md`, steps 1–2).
