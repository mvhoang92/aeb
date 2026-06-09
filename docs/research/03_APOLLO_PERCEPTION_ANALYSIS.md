# 03. Phân Tích Hướng Perception/Fusion Của Apollo

Apollo là stack tự hành lớn, có kiến trúc perception và fusion theo object-level
rõ ràng. Bài học chính cho dự án AEB là không nên đưa sensor raw trực tiếp vào
decision, mà cần trung gian object/track.

## Kiến Trúc Thường Gặp

```text
sensor raw data
  -> sensor-specific detection
  -> tracking
  -> object-level fusion
  -> prediction/planning/control
```

Ở cách tiếp cận này, mỗi object có vị trí, vận tốc, kích thước, class,
confidence và track id. Các module phía sau không cần biết chi tiết raw sensor
nữa.

## Bài Học Cho Project

- Radar point nên được chuyển thành `RadarObject`.
- Camera bbox nên được chuyển thành object detection có class/confidence.
- Fusion nên tạo `FusedTarget` thay vì rải logic ghép bbox/radar trong UI.
- AEB decision nên chỉ nhận target đã chuẩn hóa, không phụ thuộc trực tiếp vào
  chi tiết render hoặc pygame.

## Khác Biệt Với Project

Apollo là stack tự hành đầy đủ, có HD map, planning và nhiều cảm biến. Project
này có phạm vi nhỏ hơn: AEB trên cao tốc trong CARLA. Vì vậy chỉ cần học cấu
trúc object-level và tracking/fusion, không cần tái tạo toàn bộ stack.
