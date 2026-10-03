# Bản tiếng Việt dễ đọc cho tác giả — Paper v5.2

> Đây là bản giải thích để tác giả đọc và trao đổi với thầy. Bản tiếng Anh
> `aeb_ieee_6page.tex` mới là bản dùng để gửi hội nghị. File
> `aeb_ieee_6page_vi.tex` là bản dịch kỹ thuật để đối chiếu bảng, công thức và
> thuật ngữ. Nội dung dưới đây theo bản v5.2 sau bước sửa văn bản (tóm tắt,
> giới hạn, từ ngữ) ghi trong `CHANGELOG.md`.

## 0. v5.2 khác v5.1 ở đâu?

Không có lượt chạy CARLA nào được thêm, bớt hay chỉnh lại. Mọi số liệu mới đều
do script đã commit tính lại từ bằng chứng đã khóa.

1. **Bảng III có thêm cột $p$** (kiểm định McNemar chính xác), xem mục 4.3.
2. **Hai hình mới:** Hình 1 là sơ đồ pipeline, Hình 2 là log theo thời gian của
   hai lượt chạy tiêu biểu (xem mục 6). Hình trade-off cũ của v5 bị bỏ vì chỉ
   lặp lại số liệu của bảng kết quả chính.
3. **31 tài liệu tham khảo** (v5.1 có 19), tài liệu nào cũng đã được đối chiếu
   DOI hoặc trang chính thức (`SOURCE_MAP.md`).
4. **Bản tiếng Anh build bằng pdfLaTeX** (font Times, tiêu đề mục có small caps
   đúng chuẩn IEEE). Bản tiếng Việt vẫn dùng XeLaTeX, không giới hạn số trang.
5. **Macro `\artifactdoi`**: chỗ điền DOI Zenodo; hiện ghi "DOI to be assigned
   (Zenodo)". Khi có DOI chỉ cần sửa macro ở hai file `.tex`.
6. **Validator v5.2** (`scripts/validate_v52_manuscript_claims.py`) kiểm tra
   bảng với CSV đã khóa, tính lại cột McNemar và kiểm tra hai bản ngôn ngữ khớp
   nhau.
7. **Sửa văn bản:** tóm tắt rút còn 178 từ, chỉ giữ các con số chính của câu
   chuyện; precision/recall của bộ chính chuyển vào Bảng II. Chữ "late" chỉ vị
   trí cuối pipeline, không chỉ thời gian; khi nói về thời gian, bài dùng
   "delayed permission" (cấp quyền chậm). Lần lặp được mô tả là đo **tính tất
   định**. Mục Limits mở đầu bằng câu: kết luận dựa trên cơ chế, không dựa trên
   ý nghĩa thống kê.

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

"Late brake permission" trong bài nghĩa là bước cấp quyền phanh nằm **ở cuối
pipeline**, sau khi radar đã yêu cầu phanh. Chữ "late" không có nghĩa là phanh
muộn.

## 2. Hệ thống được thử như thế nào?

Cả ba cách dùng chung mọi thành phần phía trước:

- radar để đo khoảng cách và vận tốc tương đối;
- camera RGB và YOLO26n chỉ nhận lớp **car** để xác nhận xe;
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
quỹ đạo xe, TTC không quá 1.10 s **và** khoảng cách đã thiếu ít nhất 2.0 m so
với khoảng cách dừng yêu cầu. Cả hai điều kiện TTC và khoảng cách phải cùng
thỏa.

## 3. Dữ liệu và cách tính thống kê

Chiến dịch đã khóa có 2,461 lượt chạy trong 639 phiên CARLA. Hai chính sách có
camera chạy bằng CUDA; có 474 phiên và 74,928 lần suy luận, không có lỗi suy
luận.

Đơn vị thống kê chính không phải từng lượt chạy. Đơn vị chính là một **điều
kiện thử nghiệm được đặt tên**, ví dụ một tổ hợp tốc độ, khoảng cách, loại xe
hoặc loại vật cản. Có:

- 105 điều kiện trong bộ thử nghiệm chính;
- 14 điều kiện trong bộ kiểm tra bất lợi;
- mỗi điều kiện được lặp năm lần.

Không điều kiện nào có lần PASS lẫn lần FAIL: năm lần lặp luôn cho cùng kết
quả. Vì vậy v5.2 nói rõ lần lặp chỉ đo **tính tất định** của pipeline mô
phỏng, không đo dao động giữa các lần chạy và không phải năm tình huống giao
thông độc lập. Nhiễu cảm biến và thay đổi seed là việc của nghiên cứu sau. Các
điều kiện được thiết kế có chủ đích nên precision/recall chỉ mô tả lưới thử
nghiệm này, không phải tỷ lệ ngoài đường thực tế.

Bộ kiểm tra bất lợi được khóa trước khi báo cáo nhưng được thiết kế để kiểm tra
các điểm yếu đã biết của fallback. Vì vậy, bài báo gọi chính xác đây là
**bộ kiểm tra cơ chế bất lợi đã khóa**, không gọi là mẫu giao thông ngẫu nhiên.
Các radar ghost trong bài là **synthetic fault injection** (chèn lỗi tổng hợp),
không phải phép đo tần suất radar ghost ngoài đời.

## 4. Kết quả chính

### 4.1. Bộ thử nghiệm chính (Bảng II)

| Chính sách | Precision | Recall | PASS |
|---|---:|---:|---:|
| Radar-only | 0.913 | 0.988 | 93/105 |
| Camera gate cứng | 1.000 | 0.965 | 99/105 |
| Camera gate + fallback | 1.000 | 0.988 | 101/105 |

Diễn giải đơn giản:

- Radar-only nhạy hơn nhưng phanh nhầm nhiều hơn.
- Camera gate cứng không có false positive trong lưới chính, nhưng bỏ sót hai
  vật cản giữa làn không phải xe (hộp và thùng phuy).
- Fallback lấy lại được hai tình huống đó, đồng thời vẫn chặn được tám điều
  kiện phanh nhầm gần mép đường.
- Cả ba cùng bỏ sót một tình huống cut-out muộn: điểm radar của xe phía trước
  rời khỏi hành lang quỹ đạo dự đoán rộng ±1.25 m trước khi đạt ngưỡng phanh.
  Đây là giới hạn của bước dự đoán quỹ đạo, không phải do camera chặn.

Đây là lợi ích trên bộ thử nghiệm chính, không phải bằng chứng fallback luôn
thắng.

### 4.2. Bộ kiểm tra bất lợi (Bảng II)

| Chính sách | Precision | Recall | PASS |
|---|---:|---:|---:|
| Radar-only | 0.545 | 0.857 | 6/14 |
| Camera gate cứng | 1.000 | 0.714 | 11/14 |
| Camera gate + fallback | 0.600 | 0.857 | 7/14 |

Kết quả đảo chiều. Bốn trong năm cấu hình radar ghost tồn tại ổn định, có
nhiều điểm và đủ giống mục tiêu thật để vượt qua luật fallback. Vì thế fallback
phanh nhầm, còn camera gate cứng chặn được chúng do camera không xác nhận lớp
car.

### 4.3. Bảng III và cột McNemar, giải thích bằng lời thường

Bảng III so sánh **từng cặp** chính sách (A và B) trên **cùng một** điều kiện
có tên. Mỗi điều kiện rơi vào đúng một trong bốn ô:

- **Both PASS:** cả A và B đều đạt;
- **A only:** chỉ A đạt;
- **B only:** chỉ B đạt;
- **Both FAIL:** cả hai đều trượt.

Hai ô "Both" không cho biết chính sách nào tốt hơn. Chỉ những điều kiện **bất
đồng** (A only hoặc B only) mới cho thông tin. Kiểm định McNemar chính xác hỏi
một câu đơn giản: *nếu hai chính sách thật ra ngang nhau, mỗi điều kiện bất
đồng giống như một lần tung đồng xu, nghiêng về A hay B với xác suất 1/2. Khi
đó, khả năng thấy một sự lệch ít nhất bằng mức đang thấy là bao nhiêu?* Con số
đó là $p$ (hai phía, tức tính cả trường hợp lệch về A và lệch về B).

| Phạm vi | A / B | A only | B only | $p$ | Đọc thế nào |
|---|---|---:|---:|---:|---|
| Chính | Radar / Cứng | 2 | 8 | 0.1094 | Gate cứng hơn ở 8 điều kiện, kém ở 2; lệch nhưng chưa đủ rõ với 10 điều kiện |
| Chính | Radar / Fallback | 0 | 8 | 0.0078 | Cả 8 điều kiện bất đồng đều nghiêng về fallback: $2 \times (1/2)^8 = 2/256$ |
| Chính | Cứng / Fallback | 0 | 2 | 0.5000 | Chỉ có 2 điều kiện bất đồng, quá ít để nói gì |
| Bất lợi | Radar / Cứng | 0 | 5 | 0.0625 | 5/5 nghiêng về gate cứng, nhưng 5 điều kiện vẫn ít: $2/32$ |
| Bất lợi | Radar / Fallback | 0 | 1 | 1.0000 | Chỉ 1 điều kiện bất đồng |
| Bất lợi | Cứng / Fallback | 4 | 0 | 0.1250 | 4/4 nghiêng về gate cứng (bốn ghost): $2/16$ |

Những điều cần nhớ khi trình bày:

- Chỉ **1 trong 6** cặp có $p<0.05$ (radar-only so với fallback trên bộ chính,
  0 so với 8). Vì vậy bài viết rõ: **kết luận dựa trên các cơ chế đã xác định,
  không dựa trên ý nghĩa thống kê**.
- $p$ ở đây chỉ **mô tả** mức lệch trên lưới điều kiện tự xây dựng, không suy
  ra tỷ lệ ngoài đường thật. Không hiệu chỉnh cho việc so sánh nhiều cặp.
- Kiểm định chính xác này hơi "bảo thủ" khi số điều kiện bất đồng nhỏ
  (Fagerland và cộng sự đề xuất mid-p); bài vẫn dùng bản chính xác và ghi rõ
  điều đó.
- Kiểm định dùng **điều kiện có tên**, không dùng từng lượt lặp, vì lần lặp
  không độc lập.

Số liệu được tính bởi `scripts/analysis/analyze_v52_paired_tests.py` từ bằng
chứng đã khóa và lưu ở
`docs/log/repeatability/paper_v5_2_derived/paired_exact_mcnemar.csv`.

## 5. Vì sao hệ thống thất bại?

Có bốn kiểu thất bại khác nhau:

### 5.1. Radar không tạo được mục tiêu

Với xe đẩy hàng, mỗi frame chỉ có tối đa hai điểm radar lọt qua bộ lọc khoảng
cách, độ cao và quỹ đạo dự đoán, nên không hình thành cluster nào. Không có yêu cầu
phanh từ radar thì fallback hay camera gate cũng không thể khắc phục được. Cả
ba chính sách đều va chạm mà không phanh, với trung vị khoảng 49.96 km/h.

### 5.2. Camera chặn vật cản thật (cấp quyền chậm)

Ghế dài tạo được track radar nhưng YOLO không nhận đó là xe. Radar-only phanh
từ 12.624 m và còn 32.57 km/h trước va chạm. Fallback chỉ đủ điều kiện ở
4.295 m và còn 54.93 km/h. Camera gate cứng không phanh và còn 59.95 km/h.

Fallback có phục hồi được phanh (TP), nhưng quyền phanh đến quá chậm để dừng
kịp. Radar-only giảm tốc độ va chạm nhiều hơn trong trường hợp này, dù vẫn
không đạt tiêu chí PASS.

### 5.3. Đã phanh nhưng vẫn va chạm

Với vật thể cảnh báo giao thông, cả ba chính sách đều phanh từ 21.871 m nhưng
vẫn va chạm ở 7.82 km/h. Vì vậy "đã phanh" không đồng nghĩa với "đã tránh
được va chạm". Số va chạm nhị phân không cho biết hệ thống đã giảm hậu quả
được bao nhiêu.

### 5.4. Radar ghost đủ giống mục tiêu thật

Khi chèn sáu điểm radar vào giữa làn, tracker xác nhận mục tiêu rất sớm. Radar-
only và fallback đều phanh; camera gate cứng không phanh vì không có xác nhận
car. Cả 20 lần fallback phanh nhầm đều kết thúc bằng việc xe dừng dưới 1 km/h,
với các trung vị (Bảng IV):

- tốc độ khi bắt đầu phanh: 78.4 km/h;
- thời gian phanh: 3.60 s;
- giảm tốc cực đại: 9.02 m/s².

Đây là phanh nhầm nghiêm trọng trong mô phỏng, không phải một xung phanh ngắn.
Tuy nhiên, chưa có mô hình người ngồi trong xe hoặc xe chạy phía sau nên không
được chuyển các con số này thành kết luận về chấn thương.

## 6. Hai hình mới, đọc thế nào?

### Hình 1 — Sơ đồ pipeline và ba quy tắc cấp quyền

Hình đi từ trái sang phải: điểm radar được lọc, gom nhóm và theo dõi thành
track; bước rủi ro tính TTC và khoảng cách dừng và đưa ra **yêu cầu phanh
radar $B_r$**. Song song, camera và YOLO chỉ xác nhận lớp car ($C$, và giữ xác
nhận thêm 0.35 s là $H$). Ở cuối pipeline là ba quy tắc:

- radar-only: có $B_r$ là phanh;
- gate cứng: cần $B_r$ **và** có box car tại điểm radar chiếu lên ảnh;
- fallback: như gate cứng, **hoặc** điều kiện khẩn cấp $E_r$ thỏa.

Sau đó cả ba dùng cùng bộ staged PID. Ý chính của hình: ba chính sách giống hệt
nhau ở mọi bước, chỉ khác ô cấp quyền cuối cùng. Nhãn trong hình giữ tiếng Anh
để khớp với bản nộp.

### Hình 2 — Log theo thời gian của hai lượt chạy

Hai cột, mỗi cột là một lượt chạy thật lấy từ log đã khóa. Các hàng là tốc độ
xe, TTC đo bằng radar và lệnh phanh theo thời gian. **Nền xám** là lúc radar
đang yêu cầu phanh ($B_r$ có mặt). **Nét đứt** là thời điểm va chạm.

- **(a) Fallback, ghost tổng hợp sáu điểm giữa làn:** không có vật cản thật,
  nhưng fallback cấp quyền khẩn cấp ở 0.15 s và xe phanh tới khi dừng hẳn. Đây
  là cái giá của fallback.
- **(b) Gate cứng, ghế dài trong bộ bất lợi:** có vật cản thật, radar yêu cầu
  phanh (nền xám) nhưng gate cứng chặn suốt đến lúc va chạm. Đây là cái giá của
  gate cứng.

Lượt chạy không được chọn tùy ý. Quy tắc: chọn lượt có các đại lượng severity
bằng trung vị của chính sách đó; nếu nhiều lượt bằng nhau thì lấy mã kịch
bản/lượt nhỏ nhất. Vì pipeline tất định, 15/20 lượt ghost và 5/5 lượt ghế dài
có giá trị bằng nhau. Hình minh họa **cơ chế**, không minh họa độ dao động.
Lựa chọn được ghi trong
`docs/log/repeatability/paper_v5_2_derived/figures/timeseries_selection.json`.

## 7. Điểm mới của bài báo nằm ở đâu?

Không nên nói điểm mới là "phát minh camera-radar fusion", vì hướng đó đã có
nhiều nghiên cứu.

Điểm mạnh của bài này là cách đánh giá:

1. Giữ nguyên radar, detector, bộ điều khiển và scenario harness.
2. Chỉ thay quy tắc cuối cùng cho phép phanh.
3. So sánh cả radar-only, camera gate và fallback.
4. Dùng điều kiện thử nghiệm được đặt tên làm đơn vị chính, kể cả cho kiểm
   định McNemar.
5. Sau khi khóa luật, cố ý tạo radar ghost để kiểm tra đúng điểm yếu của luật.
6. Không chỉ đếm phanh và va chạm, mà còn đo thời điểm phanh, tốc độ trước va
   chạm, thời gian phanh nhầm và giảm tốc cực đại.

Nói ngắn gọn:

> Bài báo chỉ ra rằng camera gate có thể giảm phanh nhầm nhưng cũng có thể bỏ
> sót vật cản ngoài lớp car; fallback phục hồi một phần khả năng phanh nhưng
> không phân biệt được mọi radar ghost đủ thuyết phục.

## 8. Những gì bài báo chưa chứng minh

Bài báo không chứng minh:

- fusion luôn tốt hơn radar-only;
- fallback an toàn trong mọi tình huống;
- khác biệt giữa các chính sách có ý nghĩa thống kê (chỉ 1/6 cặp có $p<0.05$);
- kết quả đại diện cho tỷ lệ giao thông ngoài đường;
- độ dao động giữa các lần chạy (lần lặp là tất định);
- radar ghost trong mô phỏng có tần suất như radar thật;
- hệ thống chạy thời gian thực trên ECU;
- hệ thống đạt chứng nhận Euro NCAP, UN R152, ISO hoặc functional safety/SOTIF;
- thuật toán đã được kiểm thử trên xe thật, HIL, nhiều map hoặc nhiều thời tiết.

Bài cũng chưa có baseline soft gate, xác minh camera không phụ thuộc lớp car
hoặc tracker xác suất. Nếu phát triển các baseline này, phải tạo protocol và
hold-out mới; không được chỉnh fallback theo hold-out đã xem.

## 9. Việc tác giả cần làm trước khi nộp

- Điền DOI Zenodo vào macro `\artifactdoi` ở cả hai file `.tex`.
- Kiểm tra lại trạng thái preprint của Akula và cộng sự.
- Quyết định có gắn tag v5.2 là phiên bản đóng băng hay không.
- Nhờ thầy đọc lại tiêu đề, đoạn novelty và cách viết về McNemar.

## 10. Cách báo cáo ngắn với thầy

> Bài báo của em không tập trung đề xuất một detector fusion mới, mà đánh giá
> ba cách cấp quyền phanh khi radar và camera cho kết quả không thống nhất.
> Radar-only có recall cao nhưng dễ phanh nhầm; camera gate cứng giảm phanh
> nhầm nhưng có thể bỏ sót vật cản không phải xe; emergency fallback phục hồi
> một phần các trường hợp đó nhưng vẫn bị đánh lừa bởi radar ghost có nhiều
> điểm và tồn tại ổn định. Đóng góp chính là so sánh theo cùng một pipeline,
> phân tích theo cơ chế thất bại và bổ sung mức độ nghiêm trọng thay vì chỉ
> báo cáo precision/recall hoặc số va chạm. Kiểm định McNemar chỉ dùng để mô
> tả; kết luận của bài dựa trên cơ chế chứ không dựa trên giá trị $p$.
