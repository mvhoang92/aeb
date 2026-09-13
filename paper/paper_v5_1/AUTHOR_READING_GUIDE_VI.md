# Bản tiếng Việt dễ đọc cho tác giả — Paper v5.1

> Đây là bản giải thích để tác giả đọc và trao đổi với thầy. Bản tiếng Anh
> `aeb_ieee_6page.tex` mới là bản dùng để gửi hội nghị. File
> `aeb_ieee_6page_vi.tex` là bản dịch kỹ thuật để đối chiếu bảng, công thức và
> thuật ngữ.

## 1. Bài báo muốn trả lời câu hỏi gì?

Khi radar cho rằng phía trước có nguy hiểm nhưng camera không xác nhận đó là
một chiếc xe, hệ thống nên xử lý thế nào?

Có ba cách thường gặp:

1. **Radar-only:** radar yêu cầu phanh thì phanh ngay.
2. **Camera gate cứng:** chỉ phanh khi radar yêu cầu và camera xác nhận có xe.
3. **Camera gate có radar emergency fallback:** bình thường vẫn cần camera,
   nhưng radar được phép bỏ qua camera trong tình huống rất khẩn cấp, nếu mục
tiêu radar đã ổn định và có đủ bằng chứng.

Bài báo không nói cách nào luôn tốt nhất. Mục tiêu là chỉ ra mỗi cách được gì,
mất gì và thất bại ở đâu.

## 2. Hệ thống được thử như thế nào?

Cả ba cách dùng chung mọi thành phần phía trước:

- radar để đo khoảng cách và vận tốc tương đối;
- camera RGB và YOLO26n để xác nhận xe;
- cùng cách lọc, gom nhóm và theo dõi điểm radar;
- cùng cách tính TTC và khoảng cách dừng;
- cùng bộ điều khiển staged PID;
- cùng bộ scenario và cùng cách chấm điểm.

Chỉ có **quy tắc cuối cùng cho phép hoặc không cho phép phanh** được thay đổi.
Nhờ vậy, khác biệt kết quả có thể quy về chính sách, không phải do đổi detector
hay đổi bộ điều khiển.

Fallback không phải radar-only. Nếu camera chưa xác nhận, fallback vẫn chưa
cho phanh ngay. Nó chỉ cho radar vượt qua camera khi đồng thời thỏa các điều
kiện chặt hơn: mục tiêu đã được theo dõi ổn định, có ít nhất sáu điểm, nằm gần
quỹ đạo xe, TTC không quá 1.10 s và khoảng cách đã thiếu ít nhất 2.0 m so với
khoảng cách dừng yêu cầu.

## 3. Dữ liệu và cách tính thống kê

Chiến dịch đã khóa có 2,461 lượt chạy trong 639 phiên CARLA. Hai chính sách có
camera chạy bằng CUDA; có 474 phiên và 74,928 lần suy luận, không có lỗi suy
luận.

Đơn vị thống kê chính không phải từng lượt chạy. Đơn vị chính là một **điều
kiện thử nghiệm được đặt tên**, ví dụ một tổ hợp tốc độ, khoảng cách, loại xe
hoặc loại vật cản. Có:

- 105 điều kiện trong bộ thử nghiệm chính;
- 14 điều kiện trong bộ kiểm tra bất lợi;
- mỗi điều kiện được lặp năm lần để kiểm tra tính ổn định.

Năm lần lặp không được coi là năm tình huống giao thông độc lập. Các điều kiện
được thiết kế có chủ đích nên precision/recall chỉ mô tả lưới thử nghiệm này,
không phải tỷ lệ ngoài đường thực tế.

Bộ kiểm tra bất lợi được khóa trước khi báo cáo nhưng được thiết kế để kiểm tra
các điểm yếu đã biết của fallback. Vì vậy, bài báo gọi chính xác đây là
**bộ kiểm tra cơ chế bất lợi đã khóa**, không gọi là mẫu giao thông ngẫu nhiên.
Các radar ghost trong bài là **synthetic fault injection** (chèn lỗi tổng hợp),
không phải phép đo tần suất radar ghost ngoài đời.

## 4. Kết quả chính

### Bộ thử nghiệm chính

| Chính sách | Precision | Recall | PASS |
|---|---:|---:|---:|
| Radar-only | 0.913 | 0.988 | 93/105 |
| Camera gate cứng | 1.000 | 0.965 | 99/105 |
| Camera gate + fallback | 1.000 | 0.988 | 101/105 |

Diễn giải đơn giản:

- Radar-only nhạy hơn nhưng phanh nhầm nhiều hơn.
- Camera gate cứng không có false positive trong lưới chính, nhưng bỏ sót một
  số vật cản không phải xe.
- Fallback lấy lại được hai tình huống vật cản giữa làn mà camera gate cứng
  bỏ sót, đồng thời vẫn chặn được tám nhóm phanh nhầm gần mép đường.

Đây là lợi ích trên bộ thử nghiệm chính, không phải bằng chứng fallback luôn
thắng.

### Bộ kiểm tra bất lợi

| Chính sách | Precision | Recall | PASS |
|---|---:|---:|---:|
| Radar-only | 0.545 | 0.857 | 6/14 |
| Camera gate cứng | 1.000 | 0.714 | 11/14 |
| Camera gate + fallback | 0.600 | 0.857 | 7/14 |

Kết quả đảo chiều. Bốn loại radar ghost tồn tại ổn định và có nhiều điểm đã
đủ giống mục tiêu thật để vượt qua luật fallback. Vì thế fallback phanh nhầm,
còn camera gate cứng chặn được chúng do camera không xác nhận lớp car.

## 5. Vì sao hệ thống thất bại?

Có bốn kiểu thất bại khác nhau:

### 5.1. Radar không tạo được mục tiêu

Xe đẩy hàng chỉ tạo được rất ít điểm radar, không tạo thành track đủ tin cậy.
Không có yêu cầu phanh từ radar thì fallback hay camera gate cũng không thể
khắc phục được. Cả ba xe đều va chạm mà không phanh, ở khoảng 49.96 km/h.

### 5.2. Camera chặn vật cản thật

Ghế dài tạo được track radar nhưng YOLO không nhận đó là xe. Radar-only phanh
từ 12.624 m và còn 32.57 km/h trước va chạm. Fallback chỉ đủ điều kiện ở
4.295 m và còn 54.93 km/h. Camera gate cứng không phanh và còn 59.95 km/h.

Điều này cho thấy fallback có phục hồi phanh, nhưng phanh quá muộn để dừng
kịp. Radar-only giảm tốc độ va chạm nhiều hơn trong trường hợp này, dù nó vẫn
không đạt tiêu chí PASS toàn bộ.

### 5.3. Đã phanh nhưng vẫn va chạm

Với vật thể cảnh báo giao thông, cả ba chính sách đều phanh từ 21.871 m nhưng
vẫn va chạm ở 7.82 km/h. Vì vậy ``đã phanh'' không đồng nghĩa với ``đã tránh
được va chạm''. Số va chạm nhị phân không cho biết hệ thống đã giảm hậu quả
được bao nhiêu.

### 5.4. Radar ghost đủ giống mục tiêu thật

Khi chèn sáu điểm radar vào giữa làn, tracker xác nhận mục tiêu rất sớm. Radar-
only và fallback đều phanh; camera gate cứng không phanh vì không có xác nhận
car. Trong 20 lần fallback phanh nhầm:

- xe đều dừng dưới 1 km/h;
- tốc độ khi bắt đầu phanh có trung vị 78.4 km/h;
- thời gian phanh là 3.60 s;
- giảm tốc cực đại là 9.02 m/s².

Đây là phanh nhầm nghiêm trọng trong mô phỏng, không phải một xung phanh ngắn.
Tuy nhiên, chưa có mô hình người ngồi trong xe hoặc xe chạy phía sau nên không
được chuyển các con số này thành kết luận về chấn thương.

## 6. Điểm mới của bài báo nằm ở đâu?

Không nên nói điểm mới là ``phát minh camera-radar fusion'', vì hướng đó đã có
nhiều nghiên cứu.

Điểm mạnh của bài này là cách đánh giá:

1. Giữ nguyên radar, detector, bộ điều khiển và scenario harness.
2. Chỉ thay quy tắc cuối cùng cho phép phanh.
3. So sánh cả radar-only, camera gate và fallback.
4. Dùng điều kiện thử nghiệm được đặt tên làm đơn vị chính.
5. Sau khi khóa luật, cố ý tạo radar ghost để kiểm tra đúng điểm yếu của luật.
6. Không chỉ đếm phanh và va chạm, mà còn đo thời điểm phanh, tốc độ trước va
   chạm, thời gian phanh nhầm và giảm tốc cực đại.

Nói ngắn gọn:

> Bài báo chỉ ra rằng camera gate có thể giảm phanh nhầm nhưng cũng có thể bỏ
> sót vật cản ngoài lớp car; fallback phục hồi một phần khả năng phanh nhưng
> không phân biệt được mọi radar ghost đủ thuyết phục.

## 7. Những gì bài báo chưa chứng minh

Bài báo không chứng minh:

- fusion luôn tốt hơn radar-only;
- fallback an toàn trong mọi tình huống;
- kết quả đại diện cho tỷ lệ giao thông ngoài đường;
- radar ghost trong mô phỏng có tần suất như radar thật;
- hệ thống chạy thời gian thực trên ECU;
- hệ thống đạt chứng nhận Euro NCAP hoặc functional safety;
- thuật toán đã được kiểm thử trên xe thật, HIL, nhiều map hoặc nhiều thời tiết.

Bài cũng chưa có baseline soft gate, xác minh camera không phụ thuộc lớp car
hoặc tracker xác suất. Nếu phát triển các baseline này, phải tạo protocol và
hold-out mới; không được chỉnh fallback theo hold-out đã xem.

## 8. Cách báo cáo ngắn với thầy

> Bài báo của em không tập trung đề xuất một detector fusion mới, mà đánh giá
> ba cách cấp quyền phanh khi radar và camera cho kết quả không thống nhất.
> Radar-only có recall cao nhưng dễ phanh nhầm; camera gate cứng giảm phanh
> nhầm nhưng có thể bỏ sót vật cản không phải xe; emergency fallback phục hồi
> một phần các trường hợp đó nhưng vẫn bị đánh lừa bởi radar ghost có nhiều
> điểm và tồn tại ổn định. Đóng góp chính là so sánh theo cùng một pipeline,
> phân tích theo cơ chế thất bại và bổ sung mức độ nghiêm trọng thay vì chỉ
> báo cáo precision/recall hoặc số va chạm.
