# 06. Quyết Định AEB Và Phanh

AEB quyết định dựa trên target phía trước, TTC và khoảng cách dừng yêu cầu. Với
radar-only, target hiện là `RadarObject` đã qua clustering/tracking. Với fusion,
target tương lai sẽ là `FusedTarget` được camera xác nhận.

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

- `NORMAL`: không cảnh báo, không phanh.
- `WARNING`: target có nguy cơ, hiện icon cảnh báo.
- `BRAKE`: override throttle và brake.
- `RELEASE`: nhả phanh khi target không còn nguy hiểm hoặc xe đã an toàn.

Khi xe đang lùi, AEB phía trước không nên override phanh, vì radar trước có thể
vẫn thấy vật cản trong lúc người lái đang lùi ra khỏi tình huống.

## Phanh Hiện Tại

Baseline đang dùng binary brake:

```text
throttle = 0.0
brake = 1.0
```

Cách này dễ kiểm chứng nhưng không mượt. Khi radar-only đã ổn, nên thay bằng
PID hoặc brake profile theo TTC/khoảng cách để giảm phanh nhạy ở vận tốc thấp.

## Cảnh Báo

Icon `!` trong UI là tín hiệu cảnh báo mô phỏng. Khi báo cáo, có thể nói đây là
đầu ra ADAS trong mô phỏng; trên xe thật tín hiệu này có thể hiển thị trên màn
hình xe và phát âm thanh cảnh báo.
