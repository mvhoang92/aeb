# 04. Xử Lý Camera Và YOLO

Camera dùng trong project là camera RGB đặt sau kính lái. Ảnh camera phục vụ hai
mục đích: debug góc nhìn giống xe thật và nhận diện xe phía trước bằng YOLO.

## Luồng Xử Lý

```text
CARLA RGB camera
  -> ảnh BGR/RGB
  -> YOLO detector
  -> bounding box class car
  -> vẽ bbox lên UI
  -> dùng bbox cho fusion với radar
```

## Model

Project hướng tới YOLO nhẹ, chạy ONNX CUDA để đủ mượt khi kết hợp với pygame và
CARLA. Model pretrained dùng để demo ban đầu; model chính nên được train lại từ
dataset CARLA để khớp góc nhìn, FOV, ánh sáng và môi trường Town04.

## Dataset Một Class

Với phạm vi hiện tại, một class `car` là hợp lý vì:

- Scenario chỉ tập trung car-to-car trên cao tốc.
- Không ưu tiên pedestrian, cyclist, intersection.
- Dữ liệu đơn giản hơn, dễ audit hơn.

Các object bị che quá nặng nên được lọc hoặc đánh dấu cẩn thận, vì label khó
nhìn có thể làm model học bbox không ổn định.

## Giới Hạn

Camera không trực tiếp đo vận tốc tương đối hoặc khoảng cách chính xác. Vì vậy
camera/YOLO nên dùng để xác nhận “có xe trong vùng nguy hiểm”, còn radar vẫn là
nguồn chính cho distance, relative velocity và TTC.
