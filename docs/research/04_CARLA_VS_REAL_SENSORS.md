# 04. CARLA Sensor So Với Cảm Biến Thực Tế

CARLA rất hữu ích để mô phỏng và tạo dữ liệu có ground truth, nhưng không nên
đồng nhất cảm biến CARLA với cảm biến thật.

## Radar Thực Tế

Radar ô tô thường là FMCW radar. Nó phát sóng điện từ, nhận tín hiệu phản xạ,
sau đó xử lý để suy ra:

- Range: khoảng cách.
- Doppler: vận tốc tương đối.
- Angle: góc phương vị, đôi khi có cả góc cao.
- RCS/strength: cường độ phản xạ.

Chuỗi xử lý có thể gồm FFT, CFAR detection, angle estimation, clustering,
tracking và object list.

## Radar CARLA

CARLA `sensor.other.radar` trả về detection point đã mô phỏng sẵn. Mỗi point có
độ sâu/góc/vận tốc tương đối. Nó không trả raw ADC, range-Doppler map hay nhiễu
FMCW đầy đủ. Vì vậy:

- CARLA radar giống output point-level hơn là raw radar.
- Muốn giống radar thật hơn cần tự thêm tầng cluster/track/object list.
- Số point phụ thuộc vật thể trong scene và `points_per_second`.

## Camera CARLA

Camera CARLA tạo ảnh RGB sạch, có thể điều chỉnh FOV/độ phân giải. Nó thiếu
nhiều yếu tố khó của camera thật như motion blur phức tạp, lens flare, bụi,
mưa, noise sensor, exposure và sai khác lens. Tuy vậy nó rất mạnh để tạo label
ground truth.

## Kết Luận

Project nên nói rõ: cảm biến CARLA dùng để mô phỏng pipeline và kiểm chứng logic,
không phải mô phỏng vật lý radar/camera đầy đủ như xe thật.
