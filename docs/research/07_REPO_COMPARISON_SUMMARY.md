# 07. Tổng Hợp So Sánh Repo Và Project

| Nguồn | Ý tưởng chính | Bài học áp dụng |
| --- | --- | --- |
| Autoware | Predicted path, obstacle on path, stopping distance | Dùng hành lang quỹ đạo thay vì toàn bộ quạt radar |
| openpilot | Radar track kết hợp lead từ vision | Tracking radar và dùng camera để xác nhận target |
| Apollo | Object-level perception/fusion | Chuẩn hóa `RadarObject`/`FusedTarget` trước khi decision |
| CARLA project | Radar point mô phỏng, camera RGB, ground truth label | Cần tự tạo object list và kiểm chứng false positive |

## Điểm Chung

Các repo tự hành nghiêm túc đều tránh quyết định trực tiếp từ một detection đơn
lẻ. Chúng thường có tầng trung gian:

```text
detection -> tracking/object -> prediction/risk -> control
```

## Hướng Phù Hợp Cho Project

Với phạm vi AEB CARLA:

1. Radar-only ổn định trước bằng object list.
2. Camera YOLO xác nhận target.
3. Fusion tạo target chung.
4. AEB decision dùng target đã chuẩn hóa.
5. Controller phanh chuyển từ binary sang PID/profile.

Đây là hướng vừa gần với Autoware/openpilot/Apollo ở mặt kiến trúc, vừa đủ gọn
để hoàn thành trong phạm vi một dự án mô phỏng.
