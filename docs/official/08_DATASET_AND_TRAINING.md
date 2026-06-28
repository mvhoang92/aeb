# 08. Dataset Và Training YOLO

Mục tiêu dataset là train YOLO một class `car` cho góc nhìn camera sau kính lái
trong CARLA. Dataset nên ưu tiên xe cùng làn, nhiều khoảng cách, nhiều vận tốc
và các tình huống car-to-car mà AEB cần xử lý.

## Thu Dataset

Collector dùng ground truth CARLA để tạo bbox:

```text
spawn ego + NPC
  -> camera RGB
  -> lấy bounding box 3D actor từ CARLA
  -> chiếu bbox 3D sang ảnh 2D
  -> lọc object không phù hợp
  -> ghi ảnh + label YOLO
```

Chạy mẫu:

```bash
cd /home/mvhoang/CARLA_0.9.11
venv/bin/python aeb/scripts/collect_yolo_dataset.py \
  --split train \
  --session-id town04_train_01 \
  --max-samples 500
```

Nếu session đã tồn tại, nên dùng session id mới hoặc chế độ overwrite khi thật
sự muốn ghi đè.

## Số Lượng Ảnh Khuyến Nghị

Cho bài toán một class trong môi trường mô phỏng tương đối sạch:

- Train: khoảng 1500 ảnh tốt.
- Val: khoảng 300 ảnh.
- Test: khoảng 200 ảnh.
- Negative/empty: 10-20% để giảm false positive.

Không nên chỉ tăng số ảnh. Quan trọng hơn là độ đa dạng: khoảng cách gần/xa,
xe cùng làn, xe làn bên, che khuất nhẹ, đường cong, ánh sáng khác nhau. Nên
chụp cách 5-10 frame để tránh ảnh quá giống nhau.

## Audit Data

Cần kiểm tra:

- Bbox có bám xe không.
- Xe bị che quá nặng có nên giữ label không.
- Xe làn bên có bị label sai mục tiêu không.
- Ảnh train/val/test có bị trùng gần như y hệt không.
- File label YOLO có đúng class id `0` cho `car` không.

## Train Và Export

Luồng train hiện tại tách thành ba bước để dễ theo dõi và dễ debug:

1. Audit dataset.
2. Train YOLO26n.
3. Export ONNX để dùng trong UI/runtime CARLA.

Các lệnh train/export dùng môi trường Python 3.10 `.venv_yolo310`, vì runtime
CARLA 0.9.11 vẫn dùng Python 3.7 nhưng Ultralytics YOLO mới cần Python mới hơn.

Audit dataset:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
.venv_yolo310/bin/python scripts/check_yolo_dataset.py
```

Train YOLO26n:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
.venv_yolo310/bin/python scripts/train_yolo26n.py
```

Export ONNX từ run mới nhất:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
.venv_yolo310/bin/python scripts/export_yolo26n_onnx.py
```

Model runtime hiện tại:

- `models/yolo26n_aeb_v7.pt`: weight PyTorch sau khi train.
- `models/yolo26n_aeb_v7.onnx`: model ONNX dùng cho UI YOLO/fusion.

Model chỉ nên thay vào UI demo/fusion khi đạt quality gate trên test split riêng.
