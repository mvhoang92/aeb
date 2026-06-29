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

Hệ thống được kiểm thử bằng các kịch bản car-to-car trên cao tốc, lấy cảm hứng
từ cấu trúc đánh giá AEB của NCAP như xe phía trước đứng yên, xe phía trước chạy
chậm hơn, xe phía trước phanh gấp và một số tình huống mở rộng như xe cắt làn.
Bộ điều khiển phanh cuối cùng sử dụng staged PID, tức chia rủi ro thành nhiều
tầng và điều khiển lực phanh liên tục trong từng tầng. Kết quả đánh giá được
tách thành hai lớp: dải thiết kế mong muốn và nhóm stress test tìm giới hạn. Hệ
thống đạt 38/38 trường hợp trong dải thiết kế; với nhóm stress test, hệ thống
đạt 25/28 trường hợp. Tổng cộng hệ thống đạt 63/66 kịch bản, tương đương
95,45%. Các trường hợp không đạt được giữ lại để xác định giới hạn hoạt động của
hệ thống, tránh làm sai lệch nhận xét đánh giá.

## Mục Lục

> Khi chuyển sang Word, mục này nên được tạo lại bằng Table of Contents tự động
> của file mẫu.

- Chương 1. Tổng quan đề tài và bài toán AEB
- Chương 2. Thiết lập môi trường mô phỏng
- Chương 3. Triển khai thuật toán AEB
- Chương 4. Kiểm thử và đánh giá
- Chương 5. Kết luận và hướng phát triển
- Tài liệu tham khảo
- Phụ lục

## Danh Mục Hình Vẽ

> Khi chuyển sang Word, các dòng `Hình x.y` nên đổi sang Caption để Word tự tạo
> danh mục hình vẽ.

- Hình 1.1: Minh họa bài toán AEB car-to-car trên cao tốc.
- Hình 1.2: Logo CARLA.
- Hình 2.1: Vị trí camera và radar trên Tesla Model 3 theo góc nhìn cạnh.
- Hình 2.2: Tầm phủ camera và radar theo góc nhìn từ trên xuống.
- Hình 2.3: Giao diện minh họa cuối cùng gồm 3 màn hình.
- Hình 3.1: Kiến trúc chức năng của hệ thống AEB.
- Hình 3.2: Nguyên lý radar ô tô FMCW ở mức khái niệm.
- Hình 3.3: Quy trình xử lý radar từ mức điểm đo đến mức đối tượng.
- Hình 3.4: Mô hình TTC và khoảng cách dừng giữa ego và mục tiêu.
- Hình 3.5: Ví dụ ảnh validation có nhãn bounding box trong quá trình huấn luyện YOLO26n.
- Hình 3.6: Kết quả huấn luyện YOLO26n.
- Hình 3.7: Nguyên lý hợp nhất dữ liệu camera-radar bằng phép chiếu hình học.
- Hình 3.8: Hành lang quỹ đạo dự đoán dùng để lọc mục tiêu radar.
- Hình 3.9: Máy trạng thái AEB nhiều tầng.
- Hình 4.1: Biểu đồ phanh PID của trường hợp xe đứng yên cùng làn.
- Hình 4.2: Biểu đồ phanh PID của trường hợp xe đứng yên từ xa.
- Hình 4.3: Biểu đồ phanh PID của trường hợp xe trước chạy chậm hơn.
- Hình 4.4: Biểu đồ phanh PID của stress test xe trước chạy chậm hơn.
- Hình 4.5: Biểu đồ phanh PID của trường hợp CCRb đạt.
- Hình 4.6: Biểu đồ phanh PID của trường hợp CCRb không đạt.
- Hình 4.7: Biểu đồ phanh PID của trường hợp cut-in đạt.
- Hình 4.8: Biểu đồ phanh PID của trường hợp cut-in không đạt.
- Hình 4.9: Biểu đồ phanh PID của trường hợp xe cùng làn trên đường cong.
- Hình 4.10: Biểu đồ phanh PID của trường hợp xe làn bên trên đường cong.
- Hình 4.11: Biểu đồ phanh PID của trường hợp nhiều xe có xe mồi làn bên.
- Hình 4.12: Biểu đồ phanh PID của trường hợp hai xe cùng làn.
- Hình 4.13: Ảnh đại diện video minh họa cuối cùng.

## Danh Mục Bảng

- Bảng 1.1: Lý do lựa chọn CARLA 0.9.11 cho đồ án.
- Bảng 1.2: Phạm vi và giả thiết của đồ án.
- Bảng 1.3: Các nguồn tham khảo chính cho hướng thiết kế AEB.
- Bảng 1.4: Liên hệ giữa nhóm kiểm thử của đồ án và nhóm tình huống NCAP.
- Bảng 2.1: Cấu hình máy và môi trường thực nghiệm.
- Bảng 2.2: So sánh các cảm biến thường dùng trong ADAS/AEB.
- Bảng 2.3: Một số cấu hình cảm biến tham khảo từ hệ thống ADAS/AEB thương mại.
- Bảng 2.4: So sánh thông số cảm biến tham khảo và cấu hình trong đồ án.
- Bảng 2.5: Cấu hình camera trong đồ án.
- Bảng 2.6: Cấu hình radar trong đồ án.
- Bảng 3.1: Quy trình phát triển hệ thống AEB trong đồ án.
- Bảng 3.2: Các module chính trong mã nguồn.
- Bảng 3.3: Các file mã nguồn và cấu hình chính.
- Bảng 3.4: Các hằng số chính trong xử lý dữ liệu radar.
- Bảng 3.5: Các biến và hằng số trong công thức TTC/khoảng cách dừng.
- Bảng 3.6: Thống kê bộ dữ liệu v7 same-lane.
- Bảng 3.7: Cấu hình fine-tune YOLO26n.
- Bảng 3.8: Kết quả đánh giá YOLO26n trong lần fine-tune cuối.
- Bảng 3.9: Các hằng số chính trong hợp nhất dữ liệu camera-radar.
- Bảng 3.10: Các hằng số chính trong dự đoán quỹ đạo ego.
- Bảng 3.11: So sánh các chế độ phanh trong đồ án.
- Bảng 3.12: Các hằng số chính của thuật toán staged PID.
- Bảng 4.1: Hai lớp kịch bản kiểm thử trong đồ án.
- Bảng 4.2: Kết quả tổng quan của staged PID trên 66 kịch bản.
- Bảng 4.3: Kết quả theo dải thiết kế và nhóm stress test.
- Bảng 4.4: Heatmap kết quả CCRb.
- Bảng 4.5: Heatmap kết quả CCRm.
- Bảng 4.6: Heatmap kết quả cut-in.
- Bảng 4.7: Một số trường hợp đại diện theo nhóm kiểm thử.
- Bảng 4.8: So sánh các phương án phanh trong quá trình phát triển.
- Bảng 4.9: Các trường hợp không đạt và giới hạn hệ thống.
- Bảng 4.10: Danh sách video minh họa cuối cùng.
- Bảng 5.1: Tổng hợp kết quả kiểm thử cuối cùng của hệ thống staged PID.
- Bảng 5.2: Hạn chế hiện tại và hướng xử lý dự kiến.
