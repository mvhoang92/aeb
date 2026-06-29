# Chương 5. Kết Luận Và Hướng Phát Triển

## 5.1. Kết Quả Đạt Được

Đồ án đã xây dựng được một hệ thống phanh khẩn cấp tự động AEB trong môi trường
mô phỏng CARLA theo hướng tương đối hoàn chỉnh, từ thiết lập cảm biến, xử lý dữ
liệu, hợp nhất camera-radar, điều khiển phanh đến kiểm thử và ghi nhận kết quả.
Các kết quả chính gồm:

- thiết lập môi trường CARLA 0.9.11 với ego Tesla Model 3, camera RGB phía sau
  kính lái, radar phía trước xe và các kịch bản cao tốc trên Town04;
- xây dựng quy trình xử lý radar từ điểm đo rời rạc sang mức đối tượng, gồm lọc
  nhiễu, lọc theo hành lang quỹ đạo, gom cụm, theo dõi qua nhiều khung hình và
  chọn mục tiêu nguy hiểm;
- thu dữ liệu từ CARLA, xây dựng bộ dữ liệu v7 same-lane và fine-tune YOLO26n
  cho bài toán phát hiện một lớp `car`;
- xây dựng hợp nhất dữ liệu camera-radar bằng phép chiếu hình học, ghép điểm
  radar/object radar với bounding box YOLO để tăng độ tin cậy mục tiêu;
- xây dựng logic đánh giá nguy hiểm dựa trên TTC, khoảng cách dừng, trạng thái
  mục tiêu và hành lang di chuyển dự kiến của xe ego;
- triển khai nhiều phiên bản điều khiển phanh để so sánh: phanh nhị phân, PID
  v1, PID v2 và staged PID;
- xây dựng giao diện minh họa 3 màn, launcher, hệ thống log chi tiết, biểu đồ
  phanh PID và video minh họa phục vụ kiểm chứng và báo cáo.

Kết quả kiểm thử cuối cùng không chỉ được nhìn theo một con số tổng, mà được
tách thành hai lớp: dải thiết kế mong muốn và nhóm stress test tìm giới hạn.
Cách tách này phù hợp hơn với tư duy đánh giá một hệ thống kỹ thuật thực tế: hệ
thống cần có vùng hoạt động tốt, đồng thời phải chỉ ra vùng bắt đầu mất hiệu quả.

**Bảng 5.1: Tổng hợp kết quả kiểm thử cuối cùng của hệ thống staged PID.**

| Nhóm kiểm thử | Mục đích | Kết quả | Nhận xét |
|---|---:|---:|---|
| Dải thiết kế | Đánh giá vùng hoạt động mong muốn của đồ án | 38/38 PASS | Hệ thống hoạt động ổn định trong các tình huống cao tốc, only-car, thời tiết lý tưởng, vận tốc chủ yếu 50-80 km/h. |
| Stress test/tìm giới hạn | Mở rộng tốc độ, khoảng cách và tình huống khó hơn | 25/28 PASS | Ba trường hợp không đạt dùng để xác định giới hạn hiện tại của hệ thống. |
| Tổng toàn bộ | Đánh giá chung trên 66 kịch bản | 63/66 PASS | Tỷ lệ đạt 95,45%, nhưng kết luận chính vẫn dựa trên dải thiết kế và phân tích giới hạn. |

Ba trường hợp không đạt trong stress test gồm các tình huống tốc độ cao, khoảng
cách ban đầu nhỏ hoặc xe cắt làn khó. Đây không nên xem là lỗi cần che giấu, mà
là bằng chứng giúp xác định biên hoạt động của hệ thống AEB trong phạm vi mô
phỏng.

## 5.2. Nhận Xét Về Phạm Vi Hoạt Động

Trong phạm vi đã đặt ra, hệ thống đạt được mục tiêu của đồ án: phát hiện nguy cơ
va chạm, chọn đúng mục tiêu chính, kích hoạt cảnh báo/phanh nhiều tầng và sinh
dữ liệu đánh giá có thể kiểm tra lại. Phạm vi hoạt động tốt nhất hiện tại có thể
tóm tắt như sau:

- môi trường cao tốc trong CARLA Town04;
- đối tượng tham gia là ô tô, chưa xét người đi bộ, xe máy hoặc xe đạp;
- thời tiết và ánh sáng lý tưởng;
- vận tốc ego chủ yếu trong khoảng 50-80 km/h;
- radar có tầm đo khoảng 100 m, camera dùng YOLO26n fine-tune trên dữ liệu cùng
  miền mô phỏng;
- bộ điều khiển phanh cuối cùng là staged PID, có các trạng thái SAFE, WARNING,
  SOFT_BRAKE, HARD_BRAKE, EMERGENCY và HOLD_STOP/nhả phanh tùy chế độ chạy.

Ở ngoài dải trên, hệ thống vẫn có thể hoạt động trong nhiều trường hợp, nhưng
không nên khẳng định là đạt tuyệt đối. Các bài stress test cho thấy khi vận tốc
tăng cao, gap nhỏ hoặc xe mục tiêu xuất hiện muộn do cắt làn, thời gian còn lại
để nhận biết và phanh giảm mạnh. Đây là giới hạn hợp lý của một cấu hình cảm
biến và thuật toán còn ở mức mô phỏng đồ án môn học.

## 5.3. Hạn Chế

Các hạn chế chính của đồ án được tổng hợp trong Bảng 5.2.

**Bảng 5.2: Hạn chế hiện tại và hướng xử lý dự kiến.**

| Hạn chế | Ảnh hưởng | Hướng xử lý |
|---|---|---|
| CARLA radar trả về điểm đo đã mô phỏng sẵn, không mô phỏng đầy đủ chuỗi tín hiệu FMCW thô | Thuật toán chưa đánh giá được các bước xử lý tín hiệu radar thấp như beat signal, FFT, Doppler map | Khi mở rộng nghiên cứu, bổ sung mô phỏng radar signal-level hoặc dùng dataset radar thực tế. |
| Bài toán mới xét car-to-car trên cao tốc | Chưa bao phủ người đi bộ, xe máy, xe đạp, đô thị phức tạp | Mở rộng ODD và thêm lớp đối tượng trong dataset/model. |
| Dataset YOLO chủ yếu ở Town04 và điều kiện lý tưởng | Model có thể giảm chất lượng khi đổi map, ánh sáng hoặc thời tiết | Thu thêm dữ liệu đa map, đa thời tiết, ban đêm/mưa/sương. |
| Fusion đang dùng chiếu hình học và điều kiện ghép ngưỡng | Chưa phải bộ theo dõi đa mục tiêu xác suất như hệ thống thương mại | Bổ sung Kalman filter, xác suất liên kết dữ liệu, quản lý track mất/hiện lại. |
| Controller phanh chưa mô hình hóa đầy đủ actuator delay, ABS, tire model và mặt đường | Giá trị jerk/gia tốc trong CARLA chỉ nên dùng để so sánh tương đối | Thêm mô hình trễ phanh, giới hạn jerk và điều kiện bám đường khi nghiên cứu sâu hơn. |
| Một số lỗi kỹ thuật của môi trường mô phỏng như artifact camera, FPS hiển thị hoặc CARLA server không ổn định khi chạy nhiều scenario liên tiếp | Có thể ảnh hưởng video minh họa hoặc thời gian chạy batch dài | Chạy synchronous mode, reset world giữa scenario, ghi log phần mô phỏng 20 Hz và tách riêng FPS hiển thị. |

Một điểm cần nhấn mạnh là jerk trong đồ án không được xem như giá trị đại diện
tuyệt đối cho độ êm của xe thật. CARLA cho phép lấy vận tốc/gia tốc và tính jerk
từ sai phân theo thời gian, nhưng mô hình lốp, mặt đường, ABS và cơ cấu phanh
không đầy đủ như xe thực. Vì vậy, jerk phù hợp để so sánh tương đối giữa các
phiên bản phanh trong cùng môi trường mô phỏng hơn là để kết luận trực tiếp về
độ êm tuyệt đối ngoài đời.

## 5.4. Hướng Phát Triển

Từ kết quả hiện tại, các hướng phát triển tiếp theo gồm:

- mở rộng bộ kịch bản theo cấu trúc gần Euro NCAP/ISO hơn, có lặp lại nhiều lần
  cho cùng một scenario để đánh giá độ ổn định thống kê;
- mở rộng dataset và fine-tune model trên nhiều map, thời tiết, thời điểm trong
  ngày và nhiều loại xe hơn;
- nâng cấp fusion từ ghép ngưỡng hình học sang theo dõi đa mục tiêu có độ tin
  cậy, ví dụ Kalman filter hoặc bộ lọc xác suất tương đương;
- bổ sung mô hình trễ hệ thống phanh, giới hạn jerk và điều kiện mặt đường để
  điều khiển staged PID sát thực tế hơn;
- thêm chế độ đánh giá tự động sinh báo cáo: bảng pass/fail, biểu đồ phanh,
  ảnh đại diện, video và nhận xét ngắn cho từng scenario;
- mở rộng bài toán từ car-to-car sang pedestrian/cyclist nếu phạm vi đồ án tiếp
  theo yêu cầu đánh giá AEB trong đô thị;
- kiểm tra khả năng triển khai model YOLO ONNX/TensorRT và tối ưu tốc độ xử lý
  nếu muốn đưa pipeline gần bài toán thời gian thực hơn.

## 5.5. Kết Luận Chung

Với phạm vi cao tốc, only-car và thời tiết lý tưởng, hệ thống AEB mô phỏng đã
đạt mục tiêu chính của đồ án. Pipeline cuối cùng có đầy đủ các khối quan trọng:
cảm biến camera-radar, xử lý radar object-level, YOLO26n, hợp nhất dữ liệu, dự
đoán quỹ đạo, tính TTC/khoảng cách dừng và phanh staged PID. Kết quả kiểm thử
cho thấy hệ thống đạt toàn bộ dải thiết kế mong muốn và xác định được một số
giới hạn khi tăng độ khó của kịch bản.

So với phanh nhị phân, staged PID là hướng phù hợp hơn vì nó gần logic AEB thực
tế: có cảnh báo, có nhiều tầng can thiệp, lực phanh thay đổi theo mức nguy hiểm
và có thể nhả phanh khi nguy cơ không còn trong chế độ chạy thực tế. Các trường
hợp fail trong stress test được giữ lại như một phần của kết quả kỹ thuật, giúp
báo cáo không chỉ trình bày hệ thống "chạy được", mà còn chỉ ra hệ thống chạy tốt
trong điều kiện nào và bắt đầu giới hạn ở đâu.
