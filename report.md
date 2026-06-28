# Xây Dựng Hệ Thống Phanh Khẩn Cấp Tự Động AEB Trên CARLA 0.9.11

> Bản thảo báo cáo full dạng Markdown. File này được viết để sau này chuyển sang
> `.docx` theo mẫu của Trường Cơ khí - Đại học Bách khoa Hà Nội. Công thức được
> viết bằng cú pháp LaTeX trong Markdown; tên hình và tên bảng được ghi sẵn để
> khi đưa sang Word có thể chuyển sang Caption tự động.

## Thông Tin Bìa Dự Kiến

- Trường: Đại học Bách khoa Hà Nội
- Đơn vị: Trường Cơ khí
- Trường Công nghệ Thông tin và Truyền thông
- Chuyên ngành: Kỹ thuật ô tô số
- Tên đề tài: Xây dựng hệ thống phanh khẩn cấp tự động AEB trên CARLA
- Sinh viên thực hiện: Mai Việt Hoàng
- Mã số sinh viên: 20241333E
- Giáo viên hướng dẫn: PGS. TS. Phạm Đức An
- Địa điểm, thời gian: Hà Nội, 2026

## Lời Cảm Ơn

Trong quá trình thực hiện đồ án, em xin gửi lời cảm ơn tới các thầy cô trong
Trường Cơ khí và Trường Công nghệ Thông tin và Truyền thông, Đại học Bách khoa Hà Nội đã trang bị kiến thức nền tảng về kỹ
thuật ô tô, hệ thống điều khiển và mô phỏng. Em cũng xin cảm ơn giảng viên
hướng dẫn đã định hướng nội dung nghiên cứu, góp ý trong quá trình xây dựng mô
phỏng và đánh giá hệ thống. Các kết quả trong đồ án được thực hiện trên nền tảng
CARLA 0.9.11, kết hợp với các công cụ Python, YOLO và các tài liệu tham khảo về
ADAS/AEB mã nguồn mở.

## Tóm Tắt Nội Dung Đồ Án

Đồ án xây dựng một hệ thống phanh khẩn cấp tự động AEB (Autonomous Emergency
Braking) trong môi trường mô phỏng CARLA 0.9.11. Xe ego được chọn là Tesla Model
3, di chuyển chủ yếu trên cao tốc Town04. Hệ thống sử dụng một camera RGB đặt
sau kính lái và một radar đặt ở mũi xe. Dữ liệu radar được xử lý ở mức đối tượng:
từ các điểm radar rời rạc, hệ thống lọc nhiễu, gom cụm, theo dõi qua nhiều khung hình
và chọn mục tiêu nguy hiểm. Camera kết hợp mô hình YOLO26n để phát hiện xe trong
ảnh. Hợp nhất dữ liệu camera-radar được dùng để xác nhận mục tiêu trước khi tính TTC,
khoảng cách dừng và quyết định cảnh báo/phanh.

Hệ thống được kiểm thử bằng các kịch bản car-to-car trên cao tốc như xe phía
trước chạy chậm hơn, xe phía trước phanh gấp và xe cắt làn. Bộ điều khiển phanh
cuối cùng sử dụng staged PID, tức chia rủi ro thành nhiều tầng và điều khiển lực
phanh liên tục trong từng tầng. Kết quả đánh giá cuối cùng trên 66 kịch bản cho
thấy hệ thống đạt 63 trường hợp, không đạt 3 trường hợp, tương đương 95,45%.
Các trường hợp không đạt được giữ lại để xác định giới hạn hoạt động của hệ
thống, tránh làm sai lệch nhận xét đánh giá.

## Mục Lục

> Khi chuyển sang Word, mục này nên được tạo lại bằng Table of Contents tự động
> của file mẫu.

- Chương 1. Tổng quan đề tài và bài toán AEB
- Chương 2. Cơ sở lý thuyết và thuật toán
- Chương 3. Thiết kế và triển khai hệ thống trên CARLA
- Chương 4. Thực nghiệm, bộ dữ liệu và đánh giá
- Chương 5. Kết luận và hướng phát triển
- Tài liệu tham khảo
- Phụ lục

## Danh Mục Hình Vẽ

> Khi chuyển sang Word, các dòng `Hình x.y` nên đổi sang Caption để Word tự tạo
> danh mục hình vẽ.

- Hình 1.1: Minh họa bài toán AEB car-to-car trên cao tốc.
- Hình 2.1: Nguyên lý radar ô tô FMCW ở mức khái niệm.
- Hình 2.2: Quy trình xử lý radar từ mức điểm đo đến mức đối tượng.
- Hình 2.3: Mô hình tính TTC giữa xe ego và xe mục tiêu.
- Hình 2.4: Nguyên lý hợp nhất dữ liệu camera-radar bằng chiếu hình học.
- Hình 2.5: Máy trạng thái AEB nhiều tầng.
- Hình 3.1: Kiến trúc tổng thể hệ thống AEB trong CARLA.
- Hình 3.2: Vị trí camera và radar trên Tesla Model 3 theo góc nhìn cạnh.
- Hình 3.3: Tầm phủ camera và radar theo góc nhìn từ trên xuống.
- Hình 3.4: Giao diện minh họa cuối cùng gồm 3 màn hình.
- Hình 4.1: Cấu trúc bộ dữ liệu YOLO v7 same-lane.
- Hình 4.2: Ví dụ ảnh bộ dữ liệu có bounding box.
- Hình 4.3: Kết quả huấn luyện YOLO26n.
- Hình 4.4: Biểu đồ phanh của trường hợp đạt.
- Hình 4.5: Biểu đồ phanh của trường hợp không đạt/giới hạn.
- Hình 4.6: Ảnh đại diện video minh họa cuối cùng.

## Danh Mục Bảng

- Bảng 1.1: Phạm vi và giả thiết của đồ án.
- Bảng 1.2: Các nguồn tham khảo chính cho hướng thiết kế AEB.
- Bảng 2.1: So sánh các cảm biến thường dùng trong ADAS/AEB.
- Bảng 2.2: Các biến trong công thức TTC và khoảng cách dừng.
- Bảng 2.3: So sánh các chế độ phanh trong đồ án.
- Bảng 3.1: Cấu hình máy và môi trường thực nghiệm.
- Bảng 3.2: Cấu hình camera trong project.
- Bảng 3.3: Cấu hình radar trong project.
- Bảng 3.4: Các module chính trong mã nguồn.
- Bảng 4.1: Thống kê bộ dữ liệu v7 same-lane.
- Bảng 4.2: Kết quả đánh giá cuối cùng của staged PID trên 66 kịch bản.
- Bảng 4.3: Heatmap kết quả CCRb.
- Bảng 4.4: Heatmap kết quả CCRm.
- Bảng 4.5: Heatmap kết quả cut-in.
- Bảng 4.6: Các trường hợp không đạt và giới hạn hệ thống.
- Bảng 4.7: Danh sách video minh họa cuối cùng.

# Chương 1. Tổng Quan Đề Tài Và Bài Toán AEB

## 1.1. Lý Do Chọn Đề Tài

Hệ thống hỗ trợ lái nâng cao ADAS (Advanced Driver Assistance Systems) ngày càng
phổ biến trên ô tô hiện đại. Các chức năng như cảnh báo lệch làn, ga tự động
thích ứng, cảnh báo va chạm phía trước và phanh khẩn cấp tự động giúp giảm tải
cho người lái và tăng an toàn giao thông. Trong nhóm chức năng này, AEB là một
hệ thống an toàn chủ động quan trọng vì nó có khả năng can thiệp trực tiếp vào
điều khiển xe khi phát hiện nguy cơ va chạm.

Thử nghiệm AEB trên xe thật có chi phí cao, cần bãi thử, mục tiêu giả, quy trình
an toàn và thiết bị đo chuyên dụng. Do đó, mô phỏng là bước phù hợp để nghiên
cứu thuật toán, xây dựng quy trình xử lý cảm biến, thử nhiều tình huống và tìm giới hạn
hệ thống trước khi nghĩ đến thử nghiệm thực tế.

CARLA là simulator mã nguồn mở được dùng phổ biến trong nghiên cứu xe tự hành.
Nó hỗ trợ tạo xe, gắn camera/radar, điều khiển các đối tượng trong mô phỏng,
tạo kịch bản, ghi nhật ký dữ liệu và thu bộ dữ liệu có nhãn chuẩn. Vì vậy, đồ án chọn CARLA 0.9.11 làm môi trường để
xây dựng hệ thống AEB ở mức mô phỏng.

![Minh họa bài toán AEB car-to-car](outputs/scenario_videos/final_evidence_videos_20260628_internal/thumbnails/ccrs_80_gap_30_5s.jpg)

**Hình 1.1: Minh họa bài toán AEB car-to-car trên cao tốc.**

## 1.2. Mục Tiêu Đề Tài

Mục tiêu của đồ án là xây dựng và đánh giá một quy trình xử lý AEB hoàn chỉnh trong
CARLA, gồm:

- cấu hình xe ego Tesla Model 3;
- gắn camera sau kính lái và radar ở mũi xe;
- xử lý radar từ các điểm đo rời rạc thành mục tiêu ở mức đối tượng;
- dùng YOLO để nhận diện xe trong ảnh camera;
- kết hợp dữ liệu camera-radar để xác nhận mục tiêu nguy hiểm;
- tính TTC, khoảng cách dừng và quyết định mức rủi ro;
- điều khiển phanh bằng nhiều chế độ, trong đó staged PID là phương án chính;
- xây dựng kịch bản kiểm thử, nhật ký dữ liệu, biểu đồ và video minh họa;
- xác định dải hoạt động tốt và các giới hạn của hệ thống.

## 1.3. Phạm Vi Và Giả Thiết

Đồ án tập trung vào bài toán nhỏ nhưng rõ ràng: AEB cho tình huống car-to-car
trên cao tốc trong môi trường lý tưởng.

**Bảng 1.1: Phạm vi và giả thiết của đồ án.**

| Thành phần | Phạm vi hiện tại |
|---|---|
| Simulator | CARLA 0.9.11 |
| Map chính | Town04, môi trường cao tốc |
| Ego vehicle | `vehicle.tesla.model3` |
| Đối tượng xét | Ô tô phía trước ego |
| Tình huống chính | Clear road, xe trước đứng yên, xe trước chạy chậm, xe trước phanh gấp, xe cắt làn |
| Thời tiết | Lý tưởng, chưa xét mưa/sương mù/đêm tối |
| Cảm biến | 1 camera RGB, 1 radar phía trước |
| Dải vận tốc ưu tiên | 50-80 km/h |
| Mục tiêu mở rộng | Sweep đến 100-110 km/h để tìm giới hạn |

Phạm vi này phù hợp với một đồ án mô phỏng: đủ để thể hiện quy trình xử lý ADAS/AEB
từ cảm biến đến điều khiển, nhưng vẫn kiểm soát được số biến gây nhiễu.

## 1.4. Nguồn Tham Khảo Và Hướng Tiếp Cận

Đồ án không sao chép trực tiếp thuật toán của một kho mã nguồn nào, nhưng tham khảo tư
duy thiết kế từ các hệ thống ADAS/tự hành như Autoware, openpilot, Apollo và
CARLA examples. Điểm chung của các hệ thống này là không quyết định phanh trực
tiếp từ một phát hiện đơn lẻ. Dữ liệu cảm biến thường đi qua các tầng trung gian:

```text
phát hiện -> gom cụm/theo dõi/đối tượng -> dự đoán rủi ro -> điều khiển
```

**Bảng 1.2: Các nguồn tham khảo chính cho hướng thiết kế AEB.**

| Nguồn | Ý tưởng chính | Cách áp dụng trong đồ án |
|---|---|---|
| Autoware | Xét vật cản nằm trên đường đi dự kiến, dùng khoảng cách dừng | Dùng hành lang dự kiến thay vì toàn bộ quạt radar |
| openpilot | Theo dõi radar kết hợp với đối tượng dẫn đường từ camera | Theo dõi radar và dùng camera để xác nhận mục tiêu |
| Apollo | Nhận thức môi trường và hợp nhất dữ liệu ở mức đối tượng | Chuẩn hóa `RadarObject`/`FusedTarget` trước khi ra quyết định |
| CARLA examples | Điều khiển thủ công, cảm biến, điều khiển actor | Mở rộng giao diện điều khiển thủ công và kịch bản trong CARLA |

Từ đó, hướng làm của đồ án là:

1. Làm radar-only ổn định trước.
2. Chuyển điểm đo radar thành danh sách đối tượng.
3. Huấn luyện YOLO cho môi trường CARLA.
4. Dùng hợp nhất dữ liệu để xác nhận mục tiêu.
5. Điều khiển phanh theo nhiều tầng thay vì chỉ phanh nhị phân.

# Chương 2. Cơ Sở Lý Thuyết Và Thuật Toán

## 2.1. Tổng Quan ADAS Và AEB

ADAS là nhóm hệ thống hỗ trợ người lái dựa trên cảm biến, xử lý tín hiệu và điều
khiển. AEB là chức năng can thiệp khi hệ thống dự đoán có nguy cơ va chạm phía
trước. Một hệ thống AEB cơ bản cần trả lời ba câu hỏi:

1. Ego đang chạy với vận tốc và gia tốc như thế nào?
2. Vật thể phía trước có nằm trên đường đi dự kiến của ego không?
3. Nếu giữ trạng thái hiện tại, còn bao lâu hoặc còn bao nhiêu mét trước khi va
   chạm?

Nếu câu trả lời cho thấy rủi ro tăng cao, hệ thống có thể cảnh báo, phanh nhẹ,
phanh mạnh hoặc phanh khẩn cấp.

## 2.2. Cảm Biến Trong ADAS/AEB

AEB thực tế thường dùng kết hợp nhiều cảm biến. Camera mạnh về nhận dạng hình
dạng và phân loại đối tượng; radar mạnh về khoảng cách và vận tốc tương đối;
LiDAR cho hình học 3D chính xác nhưng chi phí cao; ultrasonic phù hợp khoảng
cách gần; IMU/GNSS/wheel speed giúp xác định trạng thái chuyển động ego.

**Bảng 2.1: So sánh các cảm biến thường dùng trong ADAS/AEB.**

| Cảm biến | Đầu ra chính | Ưu điểm | Hạn chế |
|---|---|---|---|
| Camera | Ảnh RGB, lớp đối tượng, bounding box | Nhận dạng đối tượng tốt, giàu thông tin ngữ cảnh | Nhạy với ánh sáng, không đo trực tiếp vận tốc tương đối |
| Radar | Range, relative velocity, angle | Đo khoảng cách/vận tốc tốt, phù hợp car-to-car | Point thưa, khó phân loại hình dạng |
| LiDAR | Point cloud 3D | Hình học chính xác | Giá thành cao, dữ liệu nặng |
| Ultrasonic | Khoảng cách gần | Rẻ, tốt cho parking | Tầm rất ngắn |
| IMU/wheel speed | Vận tốc, gia tốc, yaw rate | Hỗ trợ dự đoán quỹ đạo ego | Không tự phát hiện vật thể |

Trong đồ án này, camera và radar được chọn vì đây là tổ hợp hợp lý cho bài toán
AEB car-to-car: radar đo khoảng cách/vận tốc, camera xác nhận vật thể là ô tô.

## 2.3. Nguyên Lý Radar Ô Tô Và Radar Trong CARLA

Radar ô tô thực tế thường là radar FMCW. Radar phát sóng điện từ, nhận tín hiệu
phản xạ từ vật thể, sau đó xử lý để suy ra khoảng cách, vận tốc tương đối và góc
của vật thể. Chuỗi xử lý radar thực tế có thể gồm FFT, phát hiện đỉnh, CFAR,
ước lượng góc, gom cụm, theo dõi và xuất danh sách đối tượng.

CARLA `sensor.other.radar` không trả tín hiệu radar thô như radar thật. Nó trả
các điểm phát hiện đã được mô phỏng sẵn. Mỗi điểm có độ sâu, góc phương vị, góc
cao và vận tốc tương đối. Vì vậy, radar trong CARLA gần với đầu ra ở mức điểm đo
hơn là tín hiệu FMCW thô. Để hệ thống gần với radar ô tô hơn, đồ án xây dựng
thêm tầng xử lý: lọc điểm đo, gom cụm, theo dõi và tạo danh sách đối tượng.

*Cần bổ sung hình minh họa: radar phát sóng, tín hiệu phản xạ từ xe phía trước và khối xử lý tạo khoảng cách/vận tốc/đối tượng.*

**Hình 2.1: Nguyên lý radar ô tô FMCW ở mức khái niệm.**

> Ghi chú: hình này cần vẽ lại trước khi đưa vào DOCX. Có thể vẽ dạng đơn giản:
> radar phát sóng, xe phía trước phản xạ, khối xử lý tạo range/velocity/object.

## 2.4. Xử Lý Radar Từ Mức Điểm Đo Đến Mức Đối Tượng

Nếu dùng trực tiếp toàn bộ điểm radar để tính TTC, hệ thống dễ phanh nhầm. Lý
do là radar có thể nhận điểm đo từ mặt đường, lan can, cây, biển báo hoặc xe ở làn
bên. Các điểm này có thể nằm trong quạt radar nhưng không nhất thiết nằm trên
đường đi của ego.

Do đó, đồ án chuyển từ xử lý ở mức điểm đo sang xử lý ở mức đối tượng:

```text
RadarMeasurement
  -> đổi điểm đo sang hệ tọa độ ego
  -> lọc theo range, độ cao, hành lang dự kiến
  -> gom cụm theo vị trí và vận tốc
  -> theo dõi qua nhiều khung hình
  -> RadarObjectList
  -> chọn mục tiêu AEB
```

*Cần bổ sung hình minh họa: quy trình lọc điểm radar, gom cụm, theo dõi và tạo danh sách đối tượng.*

**Hình 2.2: Quy trình xử lý radar từ mức điểm đo đến mức đối tượng.**

Các đại lượng chính của một điểm radar sau khi quy về hệ ego:

- `x_forward_m`: khoảng cách theo phương tiến của xe.
- `y_right_m`: lệch ngang, dương sang phải.
- `z_up_m`: độ cao tương đối.
- `relative_velocity_mps`: vận tốc tương đối theo hướng radar.

Một đối tượng radar sau gom cụm và theo dõi có thêm:

- khoảng cách dọc và lệch ngang;
- vận tốc tương đối trung bình;
- TTC;
- số điểm đo thuộc cụm;
- số khung hình được xác nhận;
- trạng thái mới/mất dấu;
- độ tin cậy nội bộ.

Việc yêu cầu đối tượng xuất hiện qua nhiều khung hình giúp loại điểm nhiễu thoáng qua.
Việc dùng hành lang dự kiến giúp giảm phanh nhầm khi xe đang cua hoặc khi radar
thấy vật thể bên ngoài làn.

## 2.5. Tính TTC

TTC (Time To Collision) là thời gian còn lại trước va chạm nếu hai xe giữ nguyên
chuyển động tương đối hiện tại. Trong đồ án, TTC được tính từ khoảng cách radar
và vận tốc đóng:

$$
v_{closing} = -v_{rel}
$$

$$
TTC = \frac{d}{v_{closing}}
$$

Trong đó:

- $d$ là khoảng cách từ ego đến mục tiêu theo phương chuyển động;
- $v_{rel}$ là vận tốc tương đối do bộ theo dõi đối tượng radar cung cấp;
- $v_{closing}$ là vận tốc đóng, chỉ dương khi mục tiêu đang tiến lại gần ego.

*Cần bổ sung hình minh họa: xe ego, xe mục tiêu, khoảng cách $d$ và vận tốc đóng $v_{closing}$.*

**Hình 2.3: Mô hình tính TTC giữa xe ego và xe mục tiêu.**

TTC chỉ có ý nghĩa khi:

$$
v_{closing} > 0
$$

Nếu mục tiêu đang rời xa ego hoặc không nằm trên hành lang dự kiến, TTC không được
dùng để kích hoạt phanh. Đây là điểm quan trọng để tránh tình huống cứ thấy vật
thể trong radar là phanh.

## 2.6. Khoảng Cách Dừng

TTC cho biết "còn bao lâu", nhưng AEB cũng cần biết "cần bao nhiêu mét để dừng
an toàn". Vì vậy, đồ án dùng thêm mô hình khoảng cách dừng:

$$
d_{ego} = v_{ego}t_{response} + \frac{v_{ego}^{2}}{2a_{ego}}
$$

$$
d_{target} = \frac{v_{target}^{2}}{2a_{target}}
$$

$$
d_{required} = d_{ego} - d_{target} + d_{offset}
$$

Trong đó:

- $v_{ego}$ là vận tốc ego;
- $v_{target}$ là vận tốc mục tiêu theo hướng ego;
- $t_{response}$ là thời gian phản ứng giả định của hệ thống;
- $a_{ego}$ là gia tốc hãm giả định của ego;
- $a_{target}$ là gia tốc hãm giả định của mục tiêu;
- $d_{offset}$ là khoảng cách dự phòng.

**Bảng 2.2: Các biến trong công thức TTC và khoảng cách dừng.**

| Ký hiệu | Ý nghĩa | Đơn vị |
|---|---|---|
| $d$ | Khoảng cách ego-mục tiêu | m |
| $v_{rel}$ | Vận tốc tương đối | m/s |
| $v_{closing}$ | Vận tốc đóng | m/s |
| $TTC$ | Thời gian tới va chạm | s |
| $v_{ego}$ | Vận tốc ego | m/s |
| $v_{target}$ | Vận tốc mục tiêu | m/s |
| $a_{ego}$ | Gia tốc hãm giả định của ego | m/s² |
| $a_{target}$ | Gia tốc hãm giả định của mục tiêu | m/s² |
| $d_{required}$ | Khoảng cách dừng yêu cầu | m |

Nếu khoảng cách hiện tại nhỏ hơn $d_{required}$, hệ thống có thể cảnh báo hoặc
phanh dù TTC chưa xuống ngưỡng rất thấp. Cách này giúp AEB phản ứng sớm hơn ở
tốc độ cao.

## 2.7. Xử Lý Camera Và YOLO

Camera đặt sau kính lái cung cấp ảnh RGB cho mô hình YOLO. YOLO trả về bounding
box, lớp đối tượng và độ tin cậy của các xe trong ảnh. Trong đồ án, mô hình được
huấn luyện tinh chỉnh cho một lớp `car`, vì phạm vi bài toán chỉ xét car-to-car
trên cao tốc.

YOLO không được dùng làm nguồn đo khoảng cách chính. Lý do là từ một ảnh RGB đơn
lẻ, việc suy ra khoảng cách và vận tốc tương đối không ổn định bằng radar. Vai
trò chính của YOLO là xác nhận rằng mục tiêu radar tương ứng với một ô tô trong
ảnh camera.

Trong quá trình thu bộ dữ liệu, bounding box được tạo từ nhãn chuẩn của CARLA.
Các bounding box bị che khuất quá nhiều hoặc không phù hợp được lọc bằng tỷ lệ
nhìn thấy (visible ratio). Khi YOLO vận hành, các bounding box trùng nhau được
xử lý theo NMS (Non-Maximum Suppression), tức giữ box có độ tin cậy tốt hơn và
loại các box chồng lấn quá nhiều.

## 2.8. Hợp Nhất Dữ Liệu Camera-Radar

Hợp nhất dữ liệu camera-radar trong đồ án được thực hiện bằng phép chiếu hình học.
Hệ thống không sử dụng thông tin nhãn trực tiếp từ CARLA để xác định trước một
điểm radar tương ứng với pixel nào trên ảnh. Thay vào đó, điểm/đối tượng radar
được biến đổi qua các hệ tọa độ và chiếu lên mặt phẳng ảnh camera.

Quy trình xử lý:

```text
RadarObject trong hệ ego
  -> biến đổi sang hệ world/camera
  -> chiếu qua ma trận nội tại camera
  -> lấy pixel 2D trên ảnh
  -> kiểm tra pixel nằm trong YOLO bbox lớp car
  -> tạo hoặc xác nhận FusedTarget
```

*Cần bổ sung hình minh họa: đối tượng radar trong hệ tọa độ 3D được chiếu lên ảnh camera và ghép với bounding box YOLO.*

**Hình 2.4: Nguyên lý hợp nhất dữ liệu camera-radar bằng chiếu hình học.**

Nếu đối tượng radar chiếu vào trong bbox YOLO, mục tiêu được camera xác nhận. Khi đó:

- khoảng cách, vận tốc tương đối và TTC lấy từ radar;
- lớp đối tượng và bbox lấy từ YOLO;
- mức tin cậy tăng vì hai cảm biến cùng thấy một mục tiêu.

Nếu YOLO mất phát hiện trong thời gian ngắn, radar-only vẫn có thể là nguồn dự phòng,
nhưng mức tin cậy thấp hơn. Ngược lại, nếu YOLO thấy xe nhưng radar không có
đối tượng hợp lệ, hệ thống không nên phanh mạnh vì thiếu khoảng cách/vận tốc đáng
tin cậy.

## 2.9. Chọn Target Và Xử Lý Trùng

Sau xử lý radar và hợp nhất dữ liệu, hệ thống có thể có nhiều ứng viên mục tiêu. Mục tiêu AEB
không nhất thiết là vật thể gần nhất tuyệt đối, mà là vật thể nguy hiểm nhất
trên đường đi dự kiến. Tiêu chí chọn mục tiêu gồm:

- nằm trong hành lang dự kiến của ego;
- đối tượng đã được xác nhận qua nhiều khung hình;
- có vận tốc đóng hợp lệ;
- TTC thấp hoặc khoảng cách hiện tại nhỏ hơn khoảng cách yêu cầu;
- nếu có hợp nhất dữ liệu, ưu tiên mục tiêu được YOLO xác nhận là `car`.

Với bounding box trùng YOLO, hệ thống dựa vào NMS của mô hình. Với đối tượng radar trùng,
bộ theo dõi ưu tiên hợp nhất hoặc chọn cụm ổn định hơn theo khoảng cách/vận tốc.
Nguyên tắc quan trọng là không để một nhiễu đơn lẻ kích hoạt AEB.

## 2.10. Logic Phanh Và Staged PID

Đồ án giữ nhiều chế độ phanh để so sánh:

**Bảng 2.3: So sánh các chế độ phanh trong đồ án.**

| Chế độ | Nguyên lý | Vai trò |
|---|---|---|
| `binary` | Có nguy hiểm thì phanh 1.0 | Mốc so sánh đơn giản |
| `staged` | Chia mức rủi ro, mỗi mức có lực phanh cố định | Kiểm tra logic nhiều tầng |
| `pid_v1` | PID theo sai số khoảng cách/TTC | Điều khiển liên tục |
| `pid_v2_comfort` | PID mềm hơn, giảm phanh nhầm | Tăng độ êm |
| `staged_pid` | Chia tầng rủi ro + PID trong từng tầng | Bản chính hiện tại |

Logic staged PID:

```text
SAFE      -> không phanh
WARNING   -> cảnh báo bằng icon, chưa hoặc phanh rất nhẹ
SOFT      -> PID trong giới hạn phanh nhẹ
HARD      -> PID trong giới hạn phanh mạnh
EMERGENCY -> cho phép phanh lớn nhất
RELEASE   -> nhả phanh khi mục tiêu không còn nguy hiểm
```

*Cần bổ sung hình minh họa: các trạng thái SAFE, WARNING, SOFT, HARD, EMERGENCY và RELEASE.*

**Hình 2.5: Máy trạng thái AEB nhiều tầng.**

PID không thay thế logic nhiều tầng, mà là phần điều khiển lực phanh bên trong
từng tầng. Tầng rủi ro quyết định "được phép phanh mạnh đến đâu", còn PID quyết
định "phanh bao nhiêu là đủ" dựa trên sai số.

Một dạng sai số điều khiển có thể viết:

$$
e(t) = d_{required}(t) - d_{current}(t)
$$

Nếu $e(t) > 0$, khoảng cách hiện tại đang thiếu so với khoảng cách an toàn, PID
tăng lệnh phanh. Nếu $e(t) \leq 0$, hệ thống có thể giảm phanh hoặc nhả phanh
theo logic nhả phanh.

Lệnh PID tổng quát:

$$
u(t) = K_p e(t) + K_i \int e(t)dt + K_d \frac{de(t)}{dt}
$$

Trong mô phỏng, lệnh $u(t)$ được giới hạn về khoảng:

$$
0 \leq brake \leq 1
$$

Đồ án cũng ghi lại jerk, nhưng jerk trong CARLA là giá trị jerk thô, tính từ
gia tốc mô phỏng theo từng tick. Giá trị này có thể rất cao và không nên xem là
jerk tuyệt đối của xe thật; nó chỉ phù hợp để so sánh tương đối giữa các chế độ
phanh trong cùng môi trường mô phỏng.

# Chương 3. Thiết Kế Và Triển Khai Hệ Thống Trên CARLA

## 3.1. Môi Trường Thực Nghiệm

Project được đặt trong thư mục gốc CARLA:

```text
/home/mvhoang/CARLA_0.9.11/
├── CarlaUE4.sh
├── PythonAPI/
├── venv/
└── aeb/
```

Lệnh chạy CARLA ổn định trên máy hiện tại:

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

Không dùng `-opengl` vì từng gây lỗi render Pygame/manual control.

**Bảng 3.1: Cấu hình máy và môi trường thực nghiệm.**

| Thành phần | Cấu hình |
|---|---|
| OS | Ubuntu 22.04.5 LTS |
| CPU | Intel Core i5-11400H, 6 nhân 12 luồng |
| RAM | 16 GiB |
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU, 4 GiB VRAM |
| NVIDIA driver | 580.159.04 |
| CARLA | 0.9.11 |
| Python CARLA | Python 3.7.17 |
| Python YOLO | Python 3.10 trong `.venv_yolo310` |

## 3.2. Kiến Trúc Tổng Thể

Quy trình xử lý tổng thể của hệ thống:

```text
CARLA world
  -> ego vehicle + camera + radar
  -> xử lý đối tượng radar
  -> phát hiện xe bằng YOLO
  -> hợp nhất dữ liệu camera-radar
  -> lựa chọn mục tiêu
  -> TTC + stopping distance
  -> AEB state + staged PID
  -> VehicleControl override
  -> nhật ký dữ liệu + biểu đồ + video
```

*Cần bổ sung hình minh họa: kiến trúc tổng thể từ CARLA, cảm biến, xử lý nhận thức, quyết định AEB đến điều khiển phanh.*

**Hình 3.1: Kiến trúc tổng thể hệ thống AEB trong CARLA.**

**Bảng 3.4: Các module chính trong mã nguồn.**

| Thư mục | Vai trò |
|---|---|
| `configs/` | Cấu hình cảm biến, bộ dữ liệu, mô hình, kịch bản |
| `control/` | Logic phanh, trạng thái AEB, PID/staged PID |
| `core/` | Các quy trình xử lý chính dùng chung |
| `perception/` | Xử lý radar, bộ theo dõi, hợp nhất dữ liệu cảm biến |
| `scripts/` | Thu bộ dữ liệu, huấn luyện, xuất ONNX, chạy kiểm thử hàng loạt, quay video |
| `ui/` | Giao diện camera, radar, hợp nhất dữ liệu, minh họa cuối cùng, giao diện khởi chạy |
| `tests/` | Kiểm thử đơn vị cho logic xử lý |

## 3.3. Cấu Hình Camera Và Radar

Ego vehicle là `vehicle.tesla.model3`. Camera đặt sau kính lái để mô phỏng góc
nhìn của camera ADAS phía trước. Radar đặt tại mũi xe để đo vật thể phía trước.
Vị trí cảm biến được kiểm tra bằng chương trình `scripts/visualize_sensor_coverage.py`.

![Vị trí cảm biến theo góc nhìn cạnh](outputs/sensor_coverage/near_side_view.png)

**Hình 3.2: Vị trí camera và radar trên Tesla Model 3 theo góc nhìn cạnh.**

![Tầm phủ cảm biến theo góc nhìn từ trên xuống](outputs/sensor_coverage/far_top_view.png)

**Hình 3.3: Tầm phủ camera và radar theo góc nhìn từ trên xuống.**

**Bảng 3.2: Cấu hình camera trong project.**

| Thuộc tính | Giá trị |
|---|---|
| Loại | `sensor.camera.rgb` |
| Vị trí | Sau kính lái |
| Transform | `x=0.43`, `y=0.0`, `z=1.35` |
| FOV | 70 độ |
| Độ phân giải | 1280x720 |
| Sensor tick | 0.05 s, tương đương 20 FPS |

**Bảng 3.3: Cấu hình radar trong project.**

| Thuộc tính | Giá trị |
|---|---|
| Loại | `sensor.other.radar` |
| Vị trí | Mũi xe |
| Transform | `x=2.53`, `y=0.0`, `z=0.48` |
| Range | 100 m |
| FOV ngang/dọc | 30 độ / 6 độ |
| Points per second | 2000 |
| Sensor tick | 0.05 s, tương đương 20 FPS |

## 3.4. Đồng Bộ Mô Phỏng

Khi chạy kiểm thử hàng loạt và ghi nhật ký dữ liệu, project ưu tiên chế độ đồng bộ với:

```text
fixed_delta_seconds = 0.05
```

Tức phần mô phỏng chạy logic ở 20 Hz. Phần hiển thị Pygame/video có thể chỉ đạt
17-18 FPS khi render nặng, nhưng nhật ký định lượng vẫn dựa trên thời gian mô phỏng
và tick cố định. Vì vậy, đánh giá đạt/không đạt dựa trên nhật ký dữ liệu, không
dựa trên độ mượt của video.

## 3.5. Giao Diện Và Launcher

Giao diện minh họa cuối cùng gồm ba vùng:

- màn camera + YOLO + hợp nhất dữ liệu ở phía trên trái;
- màn manual/chase camera phía dưới trái;
- màn radar bird-eye ở bên phải.

Thiết kế này giúp vừa thấy góc nhìn cảm biến, vừa thấy xe ego trong CARLA, vừa
quan sát được đối tượng radar, mục tiêu và trạng thái AEB.

![Giao diện minh họa cuối cùng gồm 3 màn hình](outputs/scenario_videos/final_evidence_videos_20260628_internal/thumbnails/cutin_80_50_gap_25_5s.jpg)

**Hình 3.4: Giao diện minh họa cuối cùng gồm 3 màn hình.**

Giao diện khởi chạy hỗ trợ chọn ứng dụng, file cấu hình kịch bản, kịch bản cụ
thể, chế độ điều khiển, loại phanh và chế độ sau khi AEB can thiệp. Đây là công
cụ thuận tiện để chạy minh họa thủ công mà không cần nhớ toàn bộ lệnh dòng lệnh.

# Chương 4. Thực Nghiệm, Bộ Dữ Liệu Và Đánh Giá

## 4.1. Thu Bộ Dữ Liệu YOLO

Bộ dữ liệu YOLO được tạo bằng nhãn chuẩn từ CARLA. Quy trình:

```text
khởi tạo ego + xe mục tiêu
  -> camera RGB
  -> lấy bounding box 3D từ actor CARLA
  -> chiếu bounding box sang ảnh 2D
  -> lọc đối tượng bị che khuất hoặc không phù hợp
  -> ghi ảnh + label YOLO
```

Ở giai đoạn đầu, bộ dữ liệu có nhiều xe ở làn bên và bounding box chồng nhau. Sau khi kiểm
tra ảnh xem trước, project chuyển sang bộ v7 same-lane: chỉ tạo xe cùng làn phía
trước ego, tăng khoảng cách giữa ảnh bằng nhịp lưu 40 khung hình, đa dạng mẫu xe và
lọc visible ratio.

![Ví dụ ảnh bộ dữ liệu có bounding box](outputs/dataset_v7_same_lane_box_check/train__town04_train_v7_same_lane_20260618_01_000000.jpg)

**Hình 4.1: Ví dụ ảnh bộ dữ liệu có bounding box.**

**Bảng 4.1: Thống kê bộ dữ liệu v7 same-lane.**

| Tập dữ liệu | Số ảnh | Số box | Ảnh có xe | Ảnh không xe | Tỷ lệ ảnh không xe | Số phiên thu | Số mẫu xe |
|---|---:|---:|---:|---:|---:|---:|---:|
| Train | 1505 | 1872 | 1186 | 319 | 21.2% | 28 | 21 |
| Validation | 300 | 379 | 251 | 49 | 16.3% | 6 | 14 |
| Test | 200 | 264 | 164 | 36 | 18.0% | 4 | 11 |

Tổng cộng bộ dữ liệu có 2005 ảnh và 2515 bounding box. Khoảng cách mục tiêu trải từ
khoảng 6,5 m đến 100 m, phù hợp với vùng quan tâm của hợp nhất dữ liệu radar-camera.

## 4.2. Huấn Luyện YOLO26n

Mô hình YOLO26n được huấn luyện tinh chỉnh cho một lớp `car`. Quá trình huấn luyện được tách thành:

```bash
.venv_yolo310/bin/python scripts/check_yolo_dataset.py
.venv_yolo310/bin/python scripts/train_yolo26n.py
.venv_yolo310/bin/python scripts/export_yolo26n_onnx.py
```

Môi trường huấn luyện dùng Python 3.10 để tương thích Ultralytics mới, trong khi
môi trường CARLA dùng Python 3.7. Mô hình sau huấn luyện được xuất sang ONNX để
chạy trong giao diện và các chương trình vận hành.

![Kết quả huấn luyện YOLO26n](training_runs/detect/yolo26n_aeb_20260619_011359/results.png)

**Hình 4.2: Kết quả huấn luyện YOLO26n.**

Mô hình sử dụng hiện tại:

- `models/yolo26n_aeb_v7.pt`
- `models/yolo26n_aeb_v7.onnx`

## 4.3. Kịch Bản Kiểm Thử

Kịch bản được chia theo nhóm car-to-car:

- `clear_road`: đường trống, kiểm tra phanh nhầm;
- `ccrs`: xe phía trước đứng yên;
- `ccrm`: xe phía trước chạy chậm hơn;
- `ccrb`: xe phía trước phanh gấp;
- `cut_in`: xe làn bên nhập làn trước ego;
- `cut_out`: xe phía trước rời làn;
- `adjacent_vehicle`: xe làn bên, kiểm tra chọn sai mục tiêu;
- `curve_cases`: đường cong, kiểm tra hành lang dự kiến;
- `multi_actor`: nhiều xe, kiểm tra chọn đúng mục tiêu.

Trong bộ đánh giá cuối cùng, phép quét tham số chính tập trung vào ba nhóm có ý nghĩa tìm giới hạn:
CCRm, CCRb và cut-in.

Tiêu chí đánh giá:

- Kịch bản nguy hiểm: đạt nếu AEB can thiệp và không va chạm.
- Kịch bản không nguy hiểm: đạt nếu không phanh nhầm.
- Trường hợp tốc độ/khoảng cách quá khó có thể không đạt; các trường hợp này được giữ lại để xác định
  giới hạn hệ thống.

## 4.4. Kết Quả Đánh Giá Cuối Cùng Với Staged PID

Bộ đánh giá cuối cùng dùng:

- nhận thức môi trường/hợp nhất dữ liệu: camera YOLO ONNX + quy trình xử lý đối tượng radar;
- phanh: `staged_pid`;
- cấu hình kịch bản: `configs/scenarios/suites/system_limit_extended_sweep.yaml`;
- nhật ký dữ liệu: `logs/final_evidence_staged_pid_20260628`;
- video: `outputs/scenario_videos/final_evidence_videos_20260628_internal`.

**Bảng 4.2: Kết quả đánh giá cuối cùng của staged PID trên 66 kịch bản.**

| Tổng số trường hợp | Đạt | Không đạt | Thiếu kết quả | Tỷ lệ đạt |
|---:|---:|---:|---:|---:|
| 66 | 63 | 3 | 0 | 95.45% |

## 4.5. Kết Quả Theo Nhóm Scenario

**Bảng 4.3: Heatmap kết quả CCRb - xe trước phanh gấp.**

| Speed \ Gap | 20 m | 30 m | 40 m | 50 m | 60 m | 80 m |
|---|---|---|---|---|---|---|
| 50 km/h | Đạt | Đạt | Đạt | Đạt | Đạt | Đạt |
| 65 km/h | Đạt | Đạt | Đạt | Đạt | Đạt | Đạt |
| 80 km/h | Đạt | Đạt | Đạt | Đạt | Đạt | Đạt |
| 95 km/h | Va chạm | Đạt | Đạt | Đạt | Đạt | Đạt |
| 110 km/h | Va chạm | Đạt | Đạt | Đạt | Đạt | Đạt |

**Bảng 4.4: Heatmap kết quả CCRm - xe trước chạy chậm hơn.**

| Ego/Target \ Gap | 20 m | 30 m | 40 m | 50 m | 60 m | 80 m |
|---|---|---|---|---|---|---|
| 60/30 km/h | Đạt | Đạt | Đạt | Đạt | Đạt | Đạt |
| 80/50 km/h | Đạt | Đạt | Đạt | Đạt | Đạt | Đạt |
| 100/70 km/h | Đạt | Đạt | Đạt | Đạt | Đạt | Đạt |
| 110/80 km/h | Đạt | Đạt | Đạt | Đạt | Đạt | Đạt |

**Bảng 4.5: Heatmap kết quả cut-in - xe cắt làn vào trước ego.**

| Ego/Target \ Gap | 25 m | 35 m | 45 m | 60 m |
|---|---|---|---|---|
| 60/40 km/h | Đạt | Đạt | Đạt | Đạt |
| 80/50 km/h | Đạt | Đạt | Đạt | Đạt |
| 100/60 km/h | Va chạm | Đạt | Đạt | Đạt |

## 4.6. Phân Tích Trường Hợp Không Đạt Và Giới Hạn

**Bảng 4.6: Các trường hợp không đạt và giới hạn hệ thống.**

| Kịch bản | Va chạm | Khoảng cách nhỏ nhất | Nhận xét |
|---|---:|---:|---|
| `ccrb_95_gap_20` | Có | 0.0134 m | Xe trước phanh gấp, tốc độ cao, khoảng cách đầu nhỏ |
| `ccrb_110_gap_20` | Có | 0.0806 m | Vượt dải vận tốc/khoảng cách an toàn của hệ thống |
| `cutin_100_60_gap_25` | Có | 0.4763 m | Xe nhập làn ở tốc độ cao và khoảng cách đầu nhỏ |

Các trường hợp không đạt này cho thấy staged PID hiện tại hoạt động tốt ở dải
50-80 km/h, và vẫn xử lý được nhiều trường hợp 95-110 km/h nếu khoảng cách ban
đầu đủ lớn. Tuy nhiên, ở tốc độ cao kèm khoảng cách đầu nhỏ, thời gian phản ứng
và quãng đường phanh không còn
đủ. Đây là giới hạn hợp lý của hệ thống, giống cách các hệ thống AEB thực tế
cũng chỉ đảm bảo trong một dải vận tốc/điều kiện nhất định.

![Biểu đồ phanh của trường hợp đạt](logs/final_evidence_staged_pid_20260628/plots/cutin_80_50_gap_25_brake_profile.png)

**Hình 4.3: Biểu đồ phanh của trường hợp đạt `cutin_80_50_gap_25`.**

![Biểu đồ phanh của trường hợp không đạt](logs/final_evidence_staged_pid_20260628/plots/cutin_100_60_gap_25_brake_profile.png)

**Hình 4.4: Biểu đồ phanh của trường hợp không đạt/giới hạn `cutin_100_60_gap_25`.**

## 4.7. Video Minh Họa Và Kết Quả Lưu Trữ

Video được ghi trực tiếp từ khung hình Pygame bằng bộ ghi nội bộ, tránh lỗi video
đen do quay màn hình ngoài. Mỗi video có ảnh đại diện để kiểm tra nhanh nội dung.

![Ảnh đại diện video cuối cùng](outputs/scenario_videos/final_evidence_videos_20260628_internal/thumbnails/cutin_100_60_gap_25_5s.jpg)

**Hình 4.5: Ảnh đại diện video minh họa cuối cùng.**

**Bảng 4.7: Danh sách video minh họa cuối cùng.**

| Kịch bản | Ý nghĩa | File |
|---|---|---|
| `clear_road_50` | Đường trống 50 km/h, không phanh nhầm | `outputs/scenario_videos/final_evidence_videos_20260628_internal/clear_road_50.mp4` |
| `ccrs_80_gap_30` | Xe đứng yên phía trước, phanh thành công | `outputs/scenario_videos/final_evidence_videos_20260628_internal/ccrs_80_gap_30.mp4` |
| `ccrb_95_gap_20` | Xe trước phanh gấp, trường hợp giới hạn/va chạm | `outputs/scenario_videos/final_evidence_videos_20260628_internal/ccrb_95_gap_20.mp4` |
| `cutin_80_50_gap_25` | Xe cắt làn, hệ thống xử lý thành công | `outputs/scenario_videos/final_evidence_videos_20260628_internal/cutin_80_50_gap_25.mp4` |
| `cutin_100_60_gap_25` | Xe cắt làn, trường hợp giới hạn/va chạm | `outputs/scenario_videos/final_evidence_videos_20260628_internal/cutin_100_60_gap_25.mp4` |

## 4.8. Nhận Xét Về Độ Tin Cậy Kết Quả

Kết quả đánh giá định lượng dựa trên nhật ký mô phỏng, gồm trạng thái va chạm,
khoảng cách nhỏ nhất, TTC, vận tốc tại thời điểm phanh, lệnh phanh và trạng thái AEB. Video chỉ
dùng để minh họa trực quan. Khi phần hiển thị Pygame chỉ đạt 17-18 FPS, phần mô phỏng
vẫn chạy theo tick 20 Hz nếu synchronous mode được bật.

CARLA server đôi khi không ổn định khi chạy nhiều kịch bản liên tục. Để giảm
ảnh hưởng này, project bổ sung reload/restart world/server giữa các lần chạy và
ưu tiên đọc nhật ký dữ liệu sau từng kịch bản. Đây là hạn chế thực nghiệm cần ghi rõ khi báo
cáo.

# Chương 5. Kết Luận Và Hướng Phát Triển

## 5.1. Kết Quả Đạt Được

Đồ án đã xây dựng được một hệ thống AEB mô phỏng tương đối đầy đủ:

- cấu hình ego Tesla Model 3, camera và radar trong CARLA;
- xây dựng quy trình xử lý radar từ mức điểm đo sang mức đối tượng;
- huấn luyện YOLO26n một lớp `car` bằng bộ dữ liệu tự thu từ CARLA;
- xây dựng hợp nhất dữ liệu camera-radar để xác nhận mục tiêu;
- xây dựng logic AEB với TTC, khoảng cách dừng và staged PID;
- có giao diện minh họa 3 màn, giao diện khởi chạy, nhật ký dữ liệu, biểu đồ và video minh họa;
- chạy đánh giá cuối cùng trên 66 kịch bản với 63 trường hợp đạt, 3 trường hợp không đạt, tỷ lệ đạt 95,45%;
- xác định được các tình huống giới hạn ở tốc độ cao/gap nhỏ.

## 5.2. Hạn Chế

Một số hạn chế chính:

- CARLA radar không phải mô phỏng đầy đủ radar FMCW ngoài đời.
- Bài toán mới xét ô tô trên cao tốc, chưa xét người đi bộ, xe máy, xe đạp.
- Môi trường chủ yếu là thời tiết lý tưởng.
- Radar range 100 m là giới hạn đáng kể ở vận tốc cao.
- YOLO mới được huấn luyện trong Town04, chưa kiểm tra nhiều map/thời tiết.
- Controller phanh vẫn là mô phỏng, chưa có mô hình actuator delay, ABS/tire
  model chi tiết như xe thật.
- Jerk trong CARLA chỉ nên xem là chỉ số tương đối.

## 5.3. Hướng Phát Triển

Các hướng phát triển tiếp theo:

- hoàn thiện hợp nhất dữ liệu thành `FusedTarget` ổn định qua nhiều khung hình;
- mở rộng bộ dữ liệu sang nhiều map, ánh sáng, thời tiết;
- thêm pedestrian/cyclist nếu mở rộng ngoài car-to-car;
- tối ưu staged PID để giảm jerk và tăng độ êm;
- thêm mô hình delay hệ thống phanh và giới hạn jerk;
- đánh giá theo cấu trúc gần Euro NCAP/ISO hơn;
- xuất báo cáo tự động từ nhật ký dữ liệu: bảng đạt/không đạt, biểu đồ, link video.

## 5.4. Kết Luận Chung

Với phạm vi cao tốc, only-car và thời tiết lý tưởng, hệ thống AEB mô phỏng đã
đạt mục tiêu chính: phát hiện nguy cơ va chạm, chọn mục tiêu hợp lý, kích hoạt
cảnh báo/phanh và tạo dữ liệu minh chứng kiểm thử. Kết quả đánh giá cuối cùng cho thấy staged PID là
hướng phù hợp hơn phanh nhị phân vì nó gần logic AEB thực tế: có cảnh báo, có
nhiều tầng phanh và có khả năng nhả phanh khi nguy cơ không còn.

Các trường hợp không đạt không phải lỗi cần che giấu mà là dữ liệu quan trọng để xác định
dải hoạt động của hệ thống. Đây cũng là cách đánh giá giống một sản phẩm kỹ thuật
thực tế: hệ thống cần có vùng hoạt động tốt, vùng giới hạn và các giả thiết rõ
ràng.

# Tài Liệu Tham Khảo

1. CARLA Simulator, tài liệu chính thức: https://carla.readthedocs.io/
2. CARLA 0.9.11 documentation: https://carla.readthedocs.io/en/0.9.11/
3. CARLA sensors reference: https://carla.readthedocs.io/en/0.9.11/ref_sensors/
4. Autoware Universe documentation: https://autowarefoundation.github.io/autoware.universe/
5. openpilot GitHub repository: https://github.com/commaai/openpilot
6. ApolloAuto GitHub repository: https://github.com/ApolloAuto/apollo
7. Ultralytics YOLO documentation: https://docs.ultralytics.com/
8. Euro NCAP official site: https://www.euroncap.com/
9. ISO 15623, Transport information and control systems - Forward vehicle collision warning systems.
10. Tài liệu nội bộ project: `docs/official/00_PROJECT_INTRODUCTION.md`.
11. Tài liệu nội bộ project: `docs/official/03_RADAR_PROCESSING.md`.
12. Tài liệu nội bộ project: `docs/official/05_CAMERA_RADAR_FUSION.md`.
13. Tài liệu nội bộ project: `docs/official/06_AEB_DECISION_AND_BRAKING.md`.
14. Tài liệu nội bộ project: `docs/log/FINAL_EVIDENCE_PACK_20260628.md`.

# Phụ Lục A. Lệnh Chạy Chính

## A.1. Chạy CARLA server

```bash
cd /home/mvhoang/CARLA_0.9.11
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./CarlaUE4.sh -quality-level=Low
```

## A.2. Chạy giao diện khởi chạy

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
python3 laucher.py
```

## A.3. Chạy minh họa cuối cùng bằng dòng lệnh

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python ui/aeb_demo_view.py \
  --res 1600x900 \
  --map-name Town04 \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --scenario cutin_80_50_gap_25 \
  --control-mode physics \
  --scenario-warmup-s 2
```

## A.4. Kiểm tra dataset YOLO

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
.venv_yolo310/bin/python scripts/check_yolo_dataset.py
```

## A.5. Train YOLO26n

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
.venv_yolo310/bin/python scripts/train_yolo26n.py
```

## A.6. Export ONNX

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
.venv_yolo310/bin/python scripts/export_yolo26n_onnx.py
```

# Phụ Lục B. Các Tệp Kết Quả Quan Trọng

| Loại | Đường dẫn |
|---|---|
| Summary CSV cuối cùng | `logs/final_evidence_staged_pid_20260628/summary.csv` |
| Summary JSON cuối cùng | `logs/final_evidence_staged_pid_20260628/summary.json` |
| Heatmap Markdown | `logs/final_evidence_staged_pid_20260628/system_limit_heatmap.md` |
| Biểu đồ phanh | `logs/final_evidence_staged_pid_20260628/plots/` |
| Video cuối cùng | `outputs/scenario_videos/final_evidence_videos_20260628_internal/` |
| Báo cáo bộ dữ liệu | `outputs/dataset_v7_same_lane_report.md` |
| Sensor coverage | `outputs/sensor_coverage/` |
| Kết quả huấn luyện YOLO | `training_runs/detect/yolo26n_aeb_20260619_011359/` |
