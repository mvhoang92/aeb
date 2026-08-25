# Xây Dựng Và Đánh Giá Hệ Thống Phanh Khẩn Cấp Tự Động Sử Dụng Camera Và Radar Trong Môi Trường Mô Phỏng CARLA

> Bản v3: bổ sung camera gate có radar emergency fallback, chiến dịch GPU ba
> cấu hình gồm 2.461 lượt chạy, ablation/sensitivity, perturbation robustness,
> camera degradation và frozen hold-out. Kết quả hold-out không được dùng để
> hiệu chỉnh lại thuật toán.

> Bản thảo được soạn bằng Markdown để thuận tiện quản lý phiên bản và chuyển
> sang `.docx` theo mẫu của Trường Cơ khí - Đại học Bách khoa Hà Nội. Công thức
> dùng cú pháp LaTeX; các hình và bảng có caption để có thể tạo danh mục tự động
> trong Word.

## Thông Tin Bìa Dự Kiến

- Cơ sở đào tạo: Đại học Bách khoa Hà Nội
- Đơn vị: Trường Cơ khí; Trường Công nghệ Thông tin và Truyền thông
- Chuyên ngành: Kỹ thuật ô tô số
- Tên đề tài: Xây dựng và đánh giá hệ thống phanh khẩn cấp tự động sử dụng camera và radar trong môi trường mô phỏng CARLA
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

Đồ án xây dựng và đánh giá hệ thống phanh khẩn cấp tự động AEB (*Automatic
Emergency Braking*) trong CARLA 0.9.11. Xe ego Tesla Model 3 sử dụng radar phía
trước để lọc điểm đo, gom cụm, theo dõi đối tượng, chọn mục tiêu, tính TTC và
khoảng cách dừng; camera RGB và YOLO26n cung cấp bằng chứng phân loại xe. Hệ
thống dùng staged PID để điều khiển lực phanh theo mức rủi ro.

Nghiên cứu so sánh ba chính sách trên cùng harness: radar-only, hard camera gate
và camera gate có radar emergency fallback. Fallback chỉ cho phép một track
radar đã xác nhận, đủ số điểm, nằm gần quỹ đạo dự đoán và đồng thời vi phạm
ngưỡng TTC/khoảng cách dừng kích hoạt phanh; quyết định được latch đến khi radar
rời trạng thái BRAKE. Protocol được khóa trước hold-out, dùng simulation
synchronous fixed-step 0,05 s, CUDA inference và restart CARLA sau mỗi nhóm
scenario để tránh trạng thái tài nguyên tích lũy.

Chiến dịch cuối gồm 2.461 lượt chạy trong 639 phiên CARLA độc lập. Trên core
benchmark không tính synthetic fault injection, radar-only đạt
precision/recall 0,913/0,988; hard gate đạt 1,000/0,965; safe fallback đạt
1,000/0,988. Safe fallback phục hồi 10/10 lượt vật cản box/barrel giữa làn mà
hard gate va chạm, đồng thời vẫn chặn 40/40 props gần mép và 30/30 synthetic
fault bốn điểm. Tuy nhiên frozen hold-out cho kết quả kém hơn: safe fallback chỉ
đạt 35/70 lượt, phanh nhầm 20/25 high-support synthetic ghosts và cả ba chính
sách đều va chạm 15/15 lượt với ba loại physical prop mới do không tạo track
hoặc phát hiện quá muộn. Vì vậy, fallback cải thiện trade-off trên core suite
nhưng không giải quyết tổng quát bài toán radar ghost hay mọi vật cản chưa biết.

Toàn bộ kết quả được báo cáo ở cả run-level và named-scenario-level. Repeat dùng
để đánh giá tính nhất quán, không được diễn giải là các mẫu giao thông độc lập.
Kết quả không phải chứng nhận Euro NCAP, functional safety hoặc thử nghiệm xe
thật.

**Từ khóa:** AEB, ADAS, CARLA, radar, YOLO, camera-radar fusion, radar
emergency fallback, TTC, staged PID, precision-recall, hold-out, repeatability.

## Danh Mục Từ Viết Tắt

| Từ viết tắt | Diễn giải |
|---|---|
| AEB | Automatic Emergency Braking – phanh khẩn cấp tự động |
| ADAS | Advanced Driver Assistance Systems – hệ thống hỗ trợ lái xe nâng cao |
| TTC | Time To Collision – thời gian dự kiến đến va chạm |
| CCRs | Car-to-Car Rear Stationary – xe phía trước đứng yên |
| CCRm | Car-to-Car Rear Moving – xe phía trước chạy chậm hơn |
| CCRb | Car-to-Car Rear Braking – xe phía trước phanh |
| FOV | Field of View – trường nhìn của cảm biến |
| NMS | Non-Maximum Suppression – loại bỏ khung bao chồng lấn |
| ODD | Operational Design Domain – miền điều kiện vận hành |
| CUDA | Compute Unified Device Architecture – nền tảng tính toán GPU NVIDIA |
| FP/FN | False Positive/False Negative – dương tính giả/âm tính giả |
| TP/TN | True Positive/True Negative – dương tính đúng/âm tính đúng |

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

> Danh mục từ viết tắt, mục lục, danh mục hình và danh mục bảng sẽ được tạo tự
> động từ heading/caption khi chuyển sang Word.

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
- Hình 4.14: Precision-recall của ba chính sách trên core benchmark.
- Hình 4.15: PASS rate của các stress suite có chủ đích.
- Hình 4.16: Ablation radar emergency fallback.
- Hình 4.17: Kết quả PASS/FAIL trên frozen hold-out.
- Hình 4.18: Phân bố thời gian CUDA inference.

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
- Bảng 4.11: Kết quả tái lập full-suite 66 kịch bản với repeat x5.
- Bảng 4.12: Kết quả boundary probe với repeat x10.
- Bảng 4.13: Kết quả negative regression với repeat x5.
- Bảng 4.14: Ma trận nhầm lẫn radar-only vs camera-gated fusion.
- Bảng 4.15: Độ trễ kích hoạt phanh của fusion so với radar-only.
- Bảng 4.16: Kết quả false-positive vật lý (props gần mép đường) x5.
- Bảng 4.17: Kết quả limitation non-vehicle ngay giữa làn x5.
- Bảng 4.18: Ablation bộ điều khiển binary vs staged_pid.
- Bảng 4.19: Độ nhạy theo `confirmation_hold_s`.
- Bảng 4.20: Ma trận nhầm lẫn ba chính sách trên final GPU core benchmark.
- Bảng 4.21: Ablation và sensitivity của radar emergency fallback.
- Bảng 4.22: Perturbation robustness và camera degradation.
- Bảng 4.23: Kết quả frozen hold-out.
- Bảng 4.24: CUDA inference timing và tính toàn vẹn campaign.
- Bảng 5.1: Tổng hợp kết quả kiểm thử cuối cùng của hệ thống staged PID.
- Bảng 5.2: Hạn chế hiện tại và hướng xử lý dự kiến.
