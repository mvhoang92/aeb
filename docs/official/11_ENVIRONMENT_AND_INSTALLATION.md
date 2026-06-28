# 11. Môi Trường Và Cài Đặt

File này ghi cấu hình máy đã test, cách tải CARLA 0.9.11, cách đặt thư mục
`aeb/` vào CARLA và cách tạo môi trường Python để chạy project.

## Môi Trường Đã Test

Thông tin máy hiện tại:

- OS: Ubuntu 22.04.5 LTS.
- Kiến trúc: `x86_64`.
- CPU logical cores: 12.
- RAM: 15 GiB.
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU, 4 GiB VRAM.
- NVIDIA driver: `580.159.04`.
- Python trong `venv/`: Python 3.7.17.
- Một số package đã kiểm tra:
  - `pygame 2.6.1`
  - `numpy 1.21.6`
  - `PyYAML 6.0.1`
  - `opencv-python 4.13.0`

CARLA 0.9.11 dùng Python API phù hợp nhất với Python 3.7. Vì vậy project đang
ưu tiên chạy bằng `venv/bin/python` hoặc `python3.7`.

## Tải CARLA 0.9.11

CARLA có trang download chính thức liệt kê các bản phát hành, trong đó có
`CARLA 0.9.11`. Có thể tải bản Linux package từ trang này hoặc từ GitHub release
tương ứng.

Nguồn tham khảo:

- Trang download CARLA: `https://carla.readthedocs.io/en/latest/download/`
- Quick start CARLA 0.9.11: `https://carla.readthedocs.io/en/0.9.11/start_quickstart/`
- GitHub release CARLA: `https://github.com/carla-simulator/carla/releases`

Ví dụ cấu trúc sau khi tải và giải nén:

```text
/home/mvhoang/CARLA_0.9.11/
├── CarlaUE4.sh
├── PythonAPI/
├── Engine/
├── Import/
├── Tools/
└── ...
```

Nếu dùng thư mục khác, cần thay `/home/mvhoang/CARLA_0.9.11` trong các lệnh chạy.

## Đặt Thư Mục AEB Vào CARLA

Project `aeb` nên nằm trực tiếp trong thư mục gốc CARLA:

```text
/home/mvhoang/CARLA_0.9.11/
├── CarlaUE4.sh
├── PythonAPI/
├── aeb/
│   ├── configs/
│   ├── control/
│   ├── core/
│   ├── perception/
│   ├── scripts/
│   ├── ui/
│   └── README.md
└── ...
```

Cách clone:

```bash
cd /home/mvhoang/CARLA_0.9.11
git clone https://github.com/mvhoang92/aeb.git aeb
```

Nếu đã có thư mục `aeb/`, có thể cập nhật:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
git pull origin main
```

## Tạo Python Virtual Environment

Project hiện dùng `venv/` đặt ở thư mục gốc CARLA:

```text
/home/mvhoang/CARLA_0.9.11/venv/
```

Tạo môi trường:

```bash
cd /home/mvhoang/CARLA_0.9.11
python3.7 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Cài package cơ bản:

```bash
pip install numpy==1.21.6 pygame PyYAML opencv-python
```

Với YOLO/ONNX, cài thêm theo nhu cầu:

```bash
pip install ultralytics onnx onnxruntime-gpu
```

Ghi chú: nếu `onnxruntime-gpu` không khớp CUDA/driver trên máy, có thể dùng
`onnxruntime` CPU để debug trước, sau đó tối ưu CUDA sau.

## Kiểm Tra Python API CARLA

Từ thư mục gốc CARLA:

```bash
venv/bin/python PythonAPI/examples/manual_control.py
```

Nếu manual control chạy được, tiếp tục chạy app của project:

```bash
venv/bin/python aeb/ui/camera_view.py
```

Nếu Python không import được `carla`, cần kiểm tra lại:

- Đang chạy từ thư mục gốc CARLA hay chưa.
- `PythonAPI/carla/dist/` có file `.egg` phù hợp Python 3.7 hay không.
- Script đã thêm đúng CARLA egg vào `sys.path` hay chưa.

## Chạy CARLA Server

Lệnh đã test ổn trên máy hiện tại:

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Không thêm `-opengl` vì từng gây lỗi render pygame/manual control. Nếu chạy trên
máy desktop NVIDIA mặc định, có thể không cần hai biến `__NV_PRIME_RENDER_OFFLOAD`
và `__GLX_VENDOR_LIBRARY_NAME`.

## Kiểm Tra Project Sau Khi Cài

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Smoke test khi CARLA server đã bật:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --control-mode physics \
  --scenario clear_road_50 \
  --scenario ccrs_50 \
  --load-map
```

Nếu hai scenario này PASS, môi trường cơ bản đã đủ để tiếp tục làm radar-only
AEB.
