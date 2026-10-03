# Bản dịch tiếng Việt của paper v5.2 (chỉ để đọc)

Thư mục này chứa bản dịch **trung thành, từng câu** của bản tiếng Anh
`../aeb_ieee_6page.tex` tại commit `fc501b6` (nội dung `.tex` tiếng Anh không
đổi từ commit đó đến nay). Bản dịch chỉ để đọc hiểu; **bản tiếng Anh là bản
chính thức** để nộp và trích dẫn. Khi hai bản khác nhau, theo bản tiếng Anh.

| File | Nội dung |
|---|---|
| `aeb_v5_2_vi_doc_hieu.tex` / `.pdf` | Bản đọc hiểu một cột, A4 (nguồn nội dung duy nhất của bản dịch) |
| `aeb_v5_2_vi_ieee.tex` / `.pdf` | Cùng nội dung, dàn trang IEEEtran hai cột giống bản tiếng Anh; file `.tex` **tự sinh** bởi `make_ieee.py`, không sửa tay |
| `make_ieee.py` | Sinh `aeb_v5_2_vi_ieee.tex` từ bản một cột |
| `build.sh` | Chạy `make_ieee.py` rồi build cả hai PDF bằng XeLaTeX + BibTeX |
| `check_numbers.py` | So khớp mọi con số giữa bản tiếng Anh và bản dịch |

Phần duy nhất được thêm so với bản tiếng Anh là phụ lục bảng thuật ngữ
Anh–Việt ở cuối.

**Đây không phải bản tác giả `../aeb_ieee_6page_vi.tex`.** Bản tác giả là bản
song song dùng để làm việc: không giới hạn số trang và vẫn giữ những đoạn đã bị
cắt khỏi bản tiếng Anh để vừa sáu trang. Bản dịch ở đây thì khớp đúng bản tiếng
Anh, không thêm và không bớt.

## Build lại

Cần `xelatex`, `bibtex` và `python3`. Font: Noto Serif/Noto Sans (bản một cột),
TeX Gyre Termes (bản IEEE), DejaVu Sans Mono.

```bash
cd paper/paper_v5_2/translation_vi
./build.sh
python3 check_numbers.py ../aeb_ieee_6page.tex aeb_v5_2_vi_doc_hieu.tex
python3 check_numbers.py ../aeb_ieee_6page.tex aeb_v5_2_vi_ieee.tex
```

Hình và tài liệu tham khảo không được sao chép: cả hai file `.tex` dùng
`\graphicspath{{../figures/}}` và `\bibliography{../references}`, tức là dùng
chung `../figures/` và `../references.bib` với bản tiếng Anh.
`check_numbers.py` hiện chỉ báo khác biệt `5.2` (tên phiên bản trong ghi chú
đầu bản dịch).

Khi sửa bản dịch hoặc build lại PDF, cập nhật `../SHA256SUMS.txt`.
