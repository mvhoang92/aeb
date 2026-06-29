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
- `assets/`: ảnh dùng riêng cho báo cáo.
- `build_report.py`: ghép các chương thành `report.md`.

## Cách làm việc

Sửa từng file trong `chapters/`, sau đó chạy:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb/report
python3 build_report.py
```

Không nên sửa trực tiếp `report/report.md` nếu thay đổi đó cần giữ lâu dài; hãy sửa file chương tương ứng rồi build lại.
