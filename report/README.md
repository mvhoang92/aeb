# Report Sources

Thư mục này chứa bản báo cáo được tách theo chương để dễ chỉnh sửa cuốn chiếu.

## Cấu trúc

- `chapters/00_front_matter.md`: bìa dự kiến, lời cảm ơn, tóm tắt, mục lục, danh mục hình/bảng.
- `chapters/01_tong_quan.md`: Chương 1.
- `chapters/02_thiet_lap_moi_truong_mo_phong.md`: Chương 2 - thiết lập môi trường mô phỏng.
- `chapters/03_trien_khai_thuat_toan.md`: Chương 3 - triển khai thuật toán AEB.
- `chapters/04_kiem_thu_danh_gia.md`: Chương 4 - kiểm thử và đánh giá.
- `chapters/05_ket_luan.md`: Chương 5.
- `chapters/99_tai_lieu_tham_khao_phu_luc.md`: tài liệu tham khảo và phụ lục.
- `chapters_v3/`: nguồn chính của báo cáo v3 có final GPU/fallback/hold-out evidence.
- `assets/`: ảnh dùng riêng cho báo cáo; `assets/evidence_v3/` được sinh từ CSV final.
- `exports/`: bản DOCX/PPTX/PDF/ảnh đã xuất để duyệt nhanh; xem `exports/README.md` trước khi dùng.
- `build_report.py`: ghép nguồn lịch sử `chapters/` thành `report.md`.
- `build_report_v3.py`: ghép `chapters_v3/` thành `report_v3.md`.
- `export_report_v3.py`: xuất DOCX/PDF v3 theo style/margin bản report cũ.

## Cách làm việc

Sửa từng file trong `chapters/`, sau đó chạy:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb/report
python3 build_report.py
```

Không nên sửa trực tiếp `report/report.md` hoặc `report/report_v3.md` nếu thay đổi đó cần giữ lâu dài; hãy sửa file chương tương ứng rồi build lại.

## Báo cáo v3

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/usr/bin/python3 report/build_report_v3.py
/usr/bin/python3 report/export_report_v3.py
```

Đầu ra hiện tại:

- `report/report_v3.md`;
- `report/exports/aeb_report_v3.docx`;
- `report/exports/aeb_report_v3.pdf`.

Sau khi mở DOCX trong Microsoft Word, nên cập nhật field TOC/caption và kiểm tra page break lần cuối.
