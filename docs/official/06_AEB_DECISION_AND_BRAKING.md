# 06. Quyết Định AEB Và Phanh

AEB quyết định dựa trên target phía trước, TTC và khoảng cách dừng yêu cầu. Với
radar-only, target là `RadarObject` đã qua clustering/tracking. Với fusion,
target là `FusedTarget` được camera/YOLO xác nhận.

## TTC

```text
closing_speed = -relative_velocity_mps
TTC = distance_m / closing_speed
```

TTC chỉ hữu hạn khi `closing_speed > 0`. Nếu target đang rời xa hoặc đứng yên
tương đối theo hướng không gây va chạm, TTC không nên kích hoạt phanh.

## Khoảng Cách Dừng

Một công thức thực dụng:

```text
d_required =
  v_ego * t_response
  + v_ego^2 / (2 * a_ego)
  - v_target^2 / (2 * a_target)
  + safety_margin
```

Trong đó:

- `v_ego`: vận tốc ego.
- `v_target`: vận tốc target theo hướng ego.
- `t_response`: thời gian phản ứng hệ thống.
- `a_ego`: gia tốc hãm giả định của ego.
- `a_target`: gia tốc hãm giả định của target.
- `safety_margin`: khoảng cách dự phòng.

Nếu `distance_m <= d_required`, AEB có thể phanh dù TTC chưa quá thấp.

## State Cơ Bản

- `NORMAL` hoặc `SAFE`: không cảnh báo, không phanh.
- `WARNING`: target có nguy cơ, hiện icon cảnh báo.
- `SOFT`: phanh nhẹ.
- `HARD`: phanh mạnh hơn.
- `EMERGENCY`: phanh khẩn cấp.
- `RELEASE`: nhả phanh khi target không còn nguy hiểm hoặc xe đã an toàn.

Khi xe đang lùi, AEB phía trước không nên override phanh, vì radar trước có thể
vẫn thấy vật cản trong lúc người lái đang lùi ra khỏi tình huống.

## Các Chế Độ Phanh

Project giữ nhiều chế độ phanh để so sánh:

- `binary`: baseline đơn giản, có nguy hiểm thì `brake = 1.0`.
- `staged`: chia tầng rủi ro và gán lực phanh cố định cho từng tầng.
- `pid_v1`: PID điều khiển lực phanh theo sai số khoảng cách/TTC.
- `pid_v2_comfort`: PID phanh sớm hơn nhưng nhẹ hơn, có lateral gate để tránh
  phanh nhầm khi target đang lệch khỏi hành lang dự kiến.
- `staged_pid`: bản chính hiện tại, chia tầng rủi ro như `staged` nhưng lực
  phanh trong từng tầng do PID và rate limiter điều khiển.

Ý tưởng của `staged_pid`:

```text
soft risk      -> PID trong khung phanh nhẹ
medium risk    -> PID trong khung phanh vừa
hard risk      -> PID trong khung phanh mạnh
emergency risk -> cho phép phanh tối đa
```

Như vậy hệ thống vẫn có phản ứng nhiều nấc giống AEB thực tế hơn, nhưng không bị
giật như binary full-brake ngay từ đầu. Kết quả jerk trong CARLA vẫn chỉ nên xem
là `CARLA raw jerk` để so sánh tương đối giữa các chế độ.

## So Sánh Các Bộ Phanh

| Chế độ | Ưu điểm | Hạn chế | Vai trò trong đồ án |
| --- | --- | --- | --- |
| `binary` | Đơn giản, dễ kiểm chứng AEB có can thiệp hay không | Phanh gắt, không êm, dễ tạo jerk lớn | Baseline ban đầu |
| `staged` | Có nhiều mức phanh, dễ giải thích | Lực phanh cố định, chưa mượt | Bước trung gian |
| `pid_v1` | Điều khiển liên tục theo sai số | Cần tuning, có thể nhạy | So sánh với binary/staged |
| `pid_v2_comfort` | Êm hơn, giảm phanh nhầm nhờ lateral gate | Có thể phản ứng chậm hơn ở case gắt | Bản comfort |
| `staged_pid` | Kết hợp tầng rủi ro và PID, gần logic AEB thực tế hơn | Vẫn cần tuning sâu nếu mở rộng điều kiện | Bản chính hiện tại |

Khi viết báo cáo, nên trình bày `binary` và `pid_v1/pid_v2` như các mốc so sánh,
còn `staged_pid` là phương án cuối cùng được dùng trong final evidence.

## Đánh Giá Theo Hai Nhóm

Không nên chỉ báo cáo một tỷ lệ pass/fail chung. Kết quả nên chia thành:

1. **Bộ test mục tiêu**: dải tốc độ/khoảng cách mà hệ thống được thiết kế để hoạt
   động tốt, ưu tiên 50-80 km/h.
2. **Bộ test giới hạn**: các case tốc độ cao hơn, khoảng cách nhỏ hơn hoặc cut-in
   khó hơn để tìm giới hạn của hệ thống.

Việc giữ lại case không đạt là cần thiết để thể hiện dải hoạt động thật của hệ
thống, thay vì chỉ chọn các bài dễ để báo cáo đẹp.

## Cảnh Báo

Icon `!` trong UI là tín hiệu cảnh báo mô phỏng. Khi báo cáo, có thể nói đây là
đầu ra ADAS trong mô phỏng; trên xe thật tín hiệu này có thể hiển thị trên màn
hình xe và phát âm thanh cảnh báo.
