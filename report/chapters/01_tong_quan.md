# Chương 1. Tổng Quan Đề Tài Và Bài Toán AEB

## 1.1. Tổng Quan Về ADAS Và AEB

Trong nhiều năm, an toàn ô tô chủ yếu được nhìn nhận qua các hệ thống an toàn
bị động như khung hấp thụ lực, túi khí, dây đai an toàn và vùng biến dạng. Các
hệ thống này phát huy tác dụng sau khi va chạm đã xảy ra. Tuy nhiên, cùng với sự
phát triển của cảm biến, xử lý tín hiệu và điều khiển điện tử trên xe, xu hướng
an toàn hiện đại không chỉ dừng ở việc giảm hậu quả va chạm mà còn hướng tới
việc phát hiện sớm nguy cơ và chủ động tránh va chạm. Đây là cơ sở ra đời và
phát triển của ADAS (Advanced Driver Assistance Systems).

ADAS là nhóm hệ thống hỗ trợ người lái bằng cách quan sát môi trường xung quanh
xe, đánh giá rủi ro và đưa ra cảnh báo hoặc can thiệp điều khiển khi cần thiết.
Các chức năng thường gặp trong ADAS gồm cảnh báo va chạm phía trước, ga tự động
thích ứng, cảnh báo lệch làn, hỗ trợ giữ làn, giám sát điểm mù, nhận diện biển
báo và phanh khẩn cấp tự động. Trong đó, AEB (Autonomous/Automatic Emergency
Braking) là một trong những chức năng quan trọng nhất vì hệ thống không chỉ cảnh
báo cho người lái mà còn có thể trực tiếp tác động lên hệ thống phanh khi nhận
thấy va chạm sắp xảy ra.

![Minh họa bài toán AEB car-to-car](../assets/autonomous-emergency-braking-aeb-in-cars.png)

**Hình 1.1: Minh họa bài toán AEB car-to-car trên cao tốc.**

Về mặt thương mại, AEB không còn là một ý tưởng nghiên cứu xa rời thực tế. Nhiều
hãng xe lớn đã đưa AEB vào các gói hỗ trợ lái của mình, ví dụ như Toyota Safety
Sense, Honda Sensing, Mercedes-Benz Active Brake Assist, Volvo City Safety,
Nissan Safety Shield, Tesla Autopilot/Active Safety và các hệ thống tương tự của
Hyundai, Kia, BMW, Audi hoặc Volkswagen. Tên gọi và mức độ can thiệp có thể khác
nhau giữa các hãng, nhưng ý tưởng chung đều là dùng camera, radar hoặc tổ hợp
nhiều cảm biến để phát hiện xe phía trước, người đi bộ hoặc vật cản, sau đó cảnh
báo và phanh nếu người lái không phản ứng kịp. Điều này cho thấy AEB là một chủ
đề có tính ứng dụng cao, phù hợp để nghiên cứu trong đồ án về xe thông minh.

Tầm quan trọng của AEB cũng được thể hiện qua các chương trình đánh giá an toàn
và quy định kỹ thuật. Euro NCAP đưa các công nghệ an toàn chủ động như AEB vào
nhóm đánh giá Safety Assist, còn NHTSA tại Hoa Kỳ đã ban hành quy định yêu cầu
AEB trở thành trang bị tiêu chuẩn trên xe con và xe tải nhẹ trong lộ trình mới.
Nói cách khác, AEB đang chuyển dần từ một tính năng cao cấp thành một chức năng
an toàn cơ bản trên ô tô hiện đại. Vì vậy, việc hiểu nguyên lý hoạt động, xây
dựng pipeline cảm biến-quyết định-điều khiển và đánh giá giới hạn của AEB là một
nội dung có ý nghĩa cả về học thuật lẫn thực tiễn.

Trong bài toán car-to-car trên cao tốc, AEB phải giải quyết nhiều vấn đề liên
tiếp. Trước hết, hệ thống cần nhận biết có xe phía trước hay không. Tiếp theo,
hệ thống phải xác định xe đó có nằm trên đường đi dự kiến của ego hay chỉ là xe
ở làn bên, lan can, biển báo hoặc nhiễu từ môi trường. Sau đó, hệ thống cần ước
lượng khoảng cách, vận tốc tương đối, thời gian tới va chạm TTC và khoảng cách
dừng cần thiết. Cuối cùng, bộ điều khiển phải quyết định cảnh báo, phanh nhẹ,
phanh mạnh hay phanh khẩn cấp. Nếu phanh quá muộn, va chạm vẫn xảy ra; nếu phanh
quá nhạy, xe có thể phanh nhầm trong tình huống không nguy hiểm. Đây chính là
điểm khiến AEB trở thành một bài toán kỹ thuật thú vị: không chỉ cần nhận diện
đúng đối tượng, mà còn cần đánh giá đúng rủi ro và điều khiển phanh hợp lý.

Thử nghiệm AEB trực tiếp trên xe thật có nhiều rào cản. Một bài thử nghiêm túc
cần xe thử, bãi thử, mục tiêu giả có khả năng va chạm an toàn, thiết bị đo, quy
trình đảm bảo an toàn và nhân lực vận hành. Các thử nghiệm ở tốc độ cao hoặc cố
tình tạo tình huống gần va chạm cũng tiềm ẩn rủi ro lớn. Ngoài ra, để so sánh
các thuật toán, cần lặp lại cùng một kịch bản nhiều lần với điều kiện ban đầu
gần như giống nhau, điều này không dễ thực hiện ngoài đời. Vì vậy, mô phỏng là
bước phù hợp để nghiên cứu ban đầu: có thể tạo nhiều tình huống, thay đổi tham
số có kiểm soát, ghi lại dữ liệu chi tiết và tìm giới hạn hệ thống trước khi
nghĩ tới thử nghiệm thực tế.

## 1.2. Giới Thiệu Về CARLA

CARLA là một môi trường mô phỏng mã nguồn mở được phát triển cho nghiên cứu xe
tự hành và ADAS. Dự án CARLA được khởi nguồn từ Computer Vision Center (CVC) tại
Universitat Autònoma de Barcelona, với mục tiêu cung cấp một nền tảng mở cho
phát triển, huấn luyện và đánh giá hệ thống lái tự động. CARLA cho phép tạo thế
giới giao thông, sinh xe ego và xe mục tiêu, gắn cảm biến như camera/radar/LiDAR,
điều khiển actor, thiết lập bản đồ, thay đổi điều kiện môi trường, thu dữ liệu,
ghi log và tạo nhãn chuẩn từ simulator. Những khả năng này phù hợp với mục tiêu
của đồ án vì hệ thống cần vừa có cảm biến mô phỏng, vừa có kịch bản kiểm thử,
vừa có dữ liệu để huấn luyện YOLO và đánh giá thuật toán phanh.

![Minh họa môi trường CARLA](../assets/carla.jpg)

**Hình 1.2: Logo CARLA.**

CARLA được sử dụng rộng rãi trong cộng đồng nghiên cứu xe tự hành vì mã nguồn mở,
có Python API, có hệ sinh thái đi kèm như ScenarioRunner, ROS bridge, leaderboard
và nhiều ví dụ cảm biến/điều khiển. Với đồ án sinh viên, CARLA có ưu điểm quan
trọng là có thể chạy cục bộ, quan sát trực tiếp bằng giao diện đồ họa, tự viết
kịch bản và truy cập dữ liệu cảm biến mà không cần bãi thử thật. Đây là lý do
CARLA thường được dùng để thử nghiệm các thuật toán nhận thức môi trường, lập kế
hoạch chuyển động, điều khiển xe, thu dữ liệu huấn luyện và đánh giá ADAS.

Trong đồ án này, CARLA 0.9.11 được chọn vì đây là phiên bản đang được cài đặt và
vận hành ổn định trong môi trường thực nghiệm, tương thích với PythonAPI, ví dụ
`manual_control.py` và hệ sinh thái script hiện có. Việc sử dụng một phiên bản
ổn định giúp tập trung vào bài toán AEB thay vì mất thời gian xử lý khác biệt
API giữa các phiên bản CARLA mới hơn. Đồ án không đặt mục tiêu so sánh các phiên
bản simulator, mà tập trung xây dựng một pipeline AEB có thể quan sát, kiểm thử
và đánh giá được trong phạm vi mô phỏng.

Ở thời điểm thực hiện báo cáo, CARLA có các nhánh phát triển mới hơn, trong đó
nhánh 0.9.x vẫn được sử dụng cho các nghiên cứu dựa trên Unreal Engine 4; tài
liệu tải về chính thức hiện liệt kê 0.9.16 là bản phát hành mới của nhánh này.
Bên cạnh đó, CARLA 0.10.0 đã chuyển sang Unreal Engine 5.5 với chất lượng hình
ảnh và tài sản mô phỏng mới hơn. Tuy nhiên, việc nâng phiên bản simulator có thể
kéo theo thay đổi Python API, phiên bản Python, Unreal Engine, asset và cách
build/chạy server. Vì vậy, với đồ án này, chọn CARLA 0.9.11 là lựa chọn thực tế:
đủ chức năng camera/radar/vehicle control, chạy được trên máy hiện có và phù hợp
với mục tiêu xây dựng thuật toán AEB thay vì nghiên cứu hạ tầng simulator.

**Bảng 1.1: Lý do lựa chọn CARLA 0.9.11 cho đồ án.**

| Tiêu chí | Nhận xét |
|---|---|
| Tính ổn định | Đã cài đặt và chạy ổn định trên máy thực nghiệm |
| Tương thích code mẫu | Phù hợp với `PythonAPI/examples/manual_control.py`, nền tảng giao diện ban đầu của đồ án |
| Hỗ trợ cảm biến | Có camera RGB, radar, collision sensor và actor control |
| Đồng bộ mô phỏng | Có thể chạy bước thời gian cố định để ghi log và đánh giá kịch bản |
| Chi phí triển khai | Không cần build lại CARLA/Unreal Engine, tiết kiệm thời gian cho đồ án |
| Giới hạn | Không phải phiên bản mới nhất; chất lượng đồ họa và API không bằng các bản mới |

## 1.3. Mục Tiêu, Phạm Vi Và Giả Thiết

Mục tiêu tổng quát của đồ án là xây dựng một hệ thống AEB ở mức mô phỏng có đầy
đủ các khối chính của một pipeline ADAS: cảm biến, nhận thức môi trường, hợp
nhất dữ liệu, đánh giá rủi ro, điều khiển phanh và đánh giá kết quả. Hệ thống
không chỉ dừng ở việc viết một đoạn code phanh khi gặp vật cản, mà hướng tới một
quy trình có thể quan sát, kiểm thử, ghi log, so sánh và giải thích được.

Các mục tiêu cụ thể gồm:

- cấu hình xe ego Tesla Model 3;
- gắn camera sau kính lái và radar ở mũi xe;
- xử lý radar từ các điểm đo rời rạc thành mục tiêu ở mức đối tượng;
- dùng YOLO để nhận diện xe trong ảnh camera;
- kết hợp dữ liệu camera-radar để xác nhận mục tiêu nguy hiểm;
- tính TTC, khoảng cách dừng và quyết định mức rủi ro;
- điều khiển phanh bằng nhiều chế độ, trong đó staged PID là phương án chính;
- xây dựng kịch bản kiểm thử, nhật ký dữ liệu, biểu đồ và video minh họa;
- xác định dải hoạt động tốt và các giới hạn của hệ thống.

Về mặt học thuật, đồ án tập trung vào việc hiểu và triển khai các khái niệm cốt
lõi của AEB như TTC, khoảng cách dừng, xử lý nhiễu radar, chọn mục tiêu phía
trước, hợp nhất camera-radar và điều khiển phanh nhiều tầng. Về mặt kỹ thuật,
đồ án cần tạo ra một dự án có cấu trúc rõ ràng để có thể tiếp tục mở rộng sang
thu dữ liệu, huấn luyện mô hình, đánh giá nhiều kịch bản và cải tiến thuật toán
phanh trong tương lai.

Đồ án tập trung vào bài toán nhỏ nhưng rõ ràng: AEB cho tình huống car-to-car
trên cao tốc trong môi trường lý tưởng.

**Bảng 1.2: Phạm vi và giả thiết của đồ án.**

| Thành phần | Phạm vi hiện tại |
|---|---|
| Simulator | CARLA 0.9.11 |
| Map chính | Town04, môi trường cao tốc |
| Ego vehicle | `vehicle.tesla.model3` |
| Đối tượng xét | Ô tô phía trước ego |
| Tình huống chính | Clear road, xe trước đứng yên, xe trước chạy chậm, xe trước phanh gấp, xe cắt làn |
| Thời tiết | Lý tưởng, chưa xét mưa/sương mù/đêm tối |
| Cảm biến | 1 camera RGB, 1 radar phía trước; trạng thái ego/IMU dùng làm cảm biến phụ |
| Dải vận tốc ưu tiên | 50-80 km/h |
| Mục tiêu mở rộng | Sweep đến 100-110 km/h để tìm giới hạn |

Phạm vi này phù hợp với một đồ án mô phỏng: đủ để thể hiện quy trình xử lý ADAS/AEB
từ cảm biến đến điều khiển, nhưng vẫn kiểm soát được số biến gây nhiễu.

Việc giới hạn bài toán vào car-to-car trên cao tốc là có chủ đích. Nếu mở rộng
ngay sang người đi bộ, xe máy, đường đô thị, giao lộ, thời tiết xấu hoặc ánh sáng
ban đêm, số biến cần xử lý sẽ tăng rất nhanh và khó đánh giá nguyên nhân sai
lệch. Với bài toán hiện tại, hệ thống có thể tập trung vào các vấn đề nền tảng:
radar có chọn đúng xe phía trước không, camera có xác nhận đúng xe không, fusion
có ghép đúng mục tiêu không, TTC/khoảng cách dừng có phản ánh đúng rủi ro không
và bộ phanh có can thiệp hợp lý trong dải vận tốc mong muốn hay không.

Một điểm quan trọng khác là đồ án không đặt mục tiêu chứng minh hệ thống đạt mức
an toàn của xe thương mại. Các thử nghiệm trong CARLA chỉ giúp đánh giá thuật
toán trong môi trường mô phỏng, với giả thiết cảm biến, mô hình động học và điều
kiện đường tương đối lý tưởng. Do đó, kết quả cần được hiểu như bằng chứng kỹ
thuật trong phạm vi đồ án, không thay thế kiểm thử thực tế hoặc chứng nhận an
toàn chính thức.

## 1.4. Nguồn Tham Khảo Và Hướng Tiếp Cận

Đồ án không sao chép trực tiếp thuật toán của một kho mã nguồn nào, nhưng tham khảo tư
duy thiết kế từ các hệ thống ADAS/tự hành như Autoware, openpilot, Apollo và
CARLA examples. Điểm chung của các hệ thống này là không quyết định phanh trực
tiếp từ một phát hiện đơn lẻ. Dữ liệu cảm biến thường đi qua các tầng trung gian:

```text
phát hiện -> gom cụm/theo dõi/đối tượng -> dự đoán rủi ro -> điều khiển
```

**Bảng 1.3: Các nguồn tham khảo chính cho hướng thiết kế AEB.**

| Nguồn | Ý tưởng chính | Cách áp dụng trong đồ án |
|---|---|---|
| Autoware | Xét vật cản nằm trên đường đi dự kiến, dùng khoảng cách dừng | Dùng hành lang dự kiến thay vì toàn bộ quạt radar |
| openpilot | Theo dõi radar kết hợp với đối tượng dẫn đường từ camera | Theo dõi radar và dùng camera để xác nhận mục tiêu |
| Apollo | Nhận thức môi trường và hợp nhất dữ liệu ở mức đối tượng | Chuẩn hóa `RadarObject`/`FusedTarget` trước khi ra quyết định |
| CARLA examples | Điều khiển thủ công, cảm biến, điều khiển actor | Mở rộng giao diện điều khiển thủ công và kịch bản trong CARLA |

Autoware là một nền tảng phần mềm mã nguồn mở cho xe tự hành, trong đó nhiều
module an toàn không chỉ xét vật thể gần nhất mà xét vật thể có nằm trên đường
đi dự kiến của ego hay không. Đây là ý tưởng quan trọng đối với AEB, vì radar
phía trước có thể thấy cả lan can, xe làn bên hoặc vật thể ngoài quỹ đạo. Nếu chỉ
tính TTC từ mọi điểm radar, hệ thống sẽ dễ phanh nhầm. Vì vậy, đồ án học theo
tư duy "chỉ xét vật thể liên quan tới đường đi dự kiến".

openpilot và Apollo đại diện cho hướng hệ thống thực tế hơn: dữ liệu cảm biến
được đưa về các đối tượng có trạng thái, được theo dõi theo thời gian và sau đó
mới dùng cho lập kế hoạch/điều khiển. Điều này dẫn tới quyết định thiết kế của
đồ án: radar không chỉ là tập điểm rời rạc, YOLO không chỉ là các bounding box
độc lập, mà cả hai cần được đưa về mức `RadarObject` và `FusedTarget` trước khi
ra quyết định phanh.

CARLA examples, đặc biệt là `manual_control.py`, được dùng như nền tảng giao
diện và điều khiển ban đầu. Cách làm này giúp giữ nguyên cảm giác điều khiển xe
trong CARLA, sau đó mở rộng thêm màn hình camera, radar bird-eye, YOLO/fusion,
kịch bản tự động, log và video. Nhờ vậy, dự án vừa có thể minh họa trực quan,
vừa có thể chạy kiểm thử định lượng.

Từ đó, hướng làm của đồ án là:

1. Làm radar-only ổn định trước.
2. Chuyển điểm đo radar thành danh sách đối tượng.
3. Huấn luyện YOLO cho môi trường CARLA.
4. Dùng hợp nhất dữ liệu để xác nhận mục tiêu.
5. Điều khiển phanh theo nhiều tầng thay vì chỉ phanh nhị phân.

## 1.5. Liên Hệ Với Tiêu Chuẩn Đánh Giá NCAP

NCAP (New Car Assessment Programme) là nhóm các chương trình đánh giá an toàn
xe mới, trong đó Euro NCAP là một trong những hệ thống có ảnh hưởng lớn tại châu
Âu và được tham khảo rộng rãi trên thế giới. Khác với các yêu cầu pháp lý tối
thiểu, NCAP thường đưa ra các bài đánh giá bổ sung để so sánh mức độ an toàn giữa
các mẫu xe, bao gồm cả an toàn bị động và an toàn chủ động. Vì vậy, điểm số NCAP
có ảnh hưởng lớn tới hình ảnh thương mại của xe và thúc đẩy các hãng trang bị
nhiều công nghệ ADAS hơn [10].

Trong Euro NCAP, AEB thuộc nhóm Safety Assist và được đánh giá bằng các tình
huống có kiểm soát. Mục tiêu của các bài thử không chỉ là xem xe có phanh hay
không, mà còn xem hệ thống có tránh được va chạm hoặc giảm tốc độ va chạm trong
các điều kiện vận tốc/khoảng cách khác nhau hay không. Điều này rất phù hợp với
tư duy đánh giá trong đồ án: không chỉ chạy một vài minh họa trực quan, mà cần
chạy nhiều kịch bản để tìm dải hoạt động tốt và giới hạn hệ thống [10], [11].

Các kịch bản kiểm thử trong đồ án được xây dựng dựa trên tinh thần của các bài
đánh giá AEB car-to-car trong NCAP, đặc biệt là nhóm tình huống xe ego tiến tới
xe mục tiêu phía trước [11]. Các nhóm được học theo gồm:

- CCRs: xe mục tiêu phía trước đứng yên.
- CCRm: xe mục tiêu phía trước chạy chậm hơn.
- CCRb: xe mục tiêu phía trước đang chạy rồi phanh.

Đồ án không tuyên bố bộ kiểm thử là bài chứng nhận NCAP chính thức. Thay vào đó,
NCAP được sử dụng như một nguồn tham khảo để chia nhóm tình huống, chọn dải vận
tốc/khoảng cách và đánh giá có/không va chạm. Các tình huống xe cắt làn vào trước
ego, xe ở làn bên cạnh, nhiều xe xuất hiện đồng thời và đường cong được bổ sung
để tìm giới hạn của thuật toán trong môi trường mô phỏng CARLA.

**Bảng 1.4: Liên hệ giữa nhóm kiểm thử của đồ án và nhóm tình huống NCAP.**

| Nhóm trong đồ án | Ý nghĩa | Mức liên hệ với NCAP |
|---|---|---|
| `ccrs` | Ego tiến tới xe phía trước đứng yên | Học theo nhóm CCRs của AEB car-to-car |
| `ccrm` | Ego tiến tới xe phía trước chạy chậm hơn | Học theo nhóm CCRm |
| `ccrb` | Xe phía trước đang chạy rồi phanh gấp | Học theo nhóm CCRb |
| `cut_in` | Xe làn bên nhập làn trước ego | Bổ sung để tìm giới hạn hệ thống, không coi là bài NCAP chính thức |
| `clear_road`, `adjacent_vehicle`, `curve_cases` | Kiểm tra phanh nhầm và chọn sai mục tiêu | Bổ sung để kiểm tra độ ổn định thuật toán |

Tóm lại, Chương 1 xác định bài toán của đồ án là xây dựng và đánh giá một hệ
thống AEB mô phỏng trong phạm vi car-to-car trên cao tốc. Trên cơ sở đó, Chương
2 trình bày môi trường mô phỏng, cấu hình máy, xe ego và cảm biến được sử dụng
để triển khai các thuật toán ở các chương sau.
