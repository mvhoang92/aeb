# Report Export Files Guide

Thư mục này chứa các file xuất ra từ nguồn báo cáo/slides để duyệt nhanh, kiểm tra hình thức hoặc chuyển cho người khác. **Với bản v3, nguồn chính là `report/chapters_v3/*.md`, `report/report_v3.md`, `report/assets/` và các script build/export**, không phải các file `.docx`, `.pptx`, `.pdf` đã xuất. Nguồn `chapters/`/`report.md` vẫn được giữ cho phiên bản lịch sử.

## Nguyên tắc sử dụng

- Sửa nội dung lâu dài ở `report/chapters/*.md`, sau đó chạy `report/build_report.py` để ghép lại `report/report.md`.
- Dùng file trong `exports/` để xem nhanh layout, gửi duyệt, hoặc lấy ảnh minh họa.
- Không coi `.docx`/`.pptx` là source of truth vì dễ lệch khỏi Markdown nguồn.
- Các file nặng như `.docx`, `.pptx`, `.pdf` mặc định bị `.gitignore`; riêng snapshot hiện tại đã được force-add vào Git để khi kéo repo sang máy khác vẫn có bản export phục vụ chuẩn bị paper/report.
- Nếu các file nhị phân này lớn lên nhiều trong các lần export sau, nên đưa lên Drive/GitHub Release và chỉ commit link/hash.
- Các ảnh/sơ đồ nhỏ nên track nếu cần tái dựng report/slides trên máy khác.

## Cấu trúc hiện tại

```text
report/exports/
├── README.md                         # file hướng dẫn này
├── aeb_project_slides_outline.md     # dàn ý slide dạng Markdown
├── aeb_project_slides.pptx           # bản PowerPoint export, local/ignored
├── aeb_report_draft.docx             # bản DOCX lịch sử
├── aeb_report_v3.docx                # report v3 theo style cũ
├── aeb_report_v3.pdf                 # PDF render của report v3
├── generated_images/                 # ảnh/sơ đồ dùng cho report hoặc export
├── slides/generated/                 # ảnh/sơ đồ đã copy/resize cho slide
└── validate/                         # file kiểm tra PDF/text/page render
```

## Mô tả từng nhóm file

### `aeb_project_slides_outline.md`

Dàn ý nội dung slide. Dùng để:

- rà bố cục thuyết trình;
- copy nội dung sang PowerPoint/Google Slides;
- kiểm tra xem slide có bám đúng kết quả final evidence không.

Nếu sửa nội dung slide, nên sửa file này trước rồi mới export lại `.pptx`.

### `aeb_project_slides.pptx`

Bản PowerPoint đã xuất. Dùng để trình chiếu hoặc gửi duyệt nhanh. File này là artifact nhị phân, không nên chỉnh sửa như nguồn chính nếu thay đổi cần lưu lâu dài.

### `aeb_report_draft.docx`

Bản DOCX xuất từ báo cáo Markdown. Dùng để:

- kiểm tra format theo mẫu nộp;
- chỉnh sửa nhỏ cuối cùng trước khi nộp nếu bắt buộc;
- gửi người hướng dẫn duyệt.

Nếu có sửa nội dung học thuật/kỹ thuật, cần đưa ngược lại vào `report/chapters/*.md` để không mất đồng bộ.

### `generated_images/`

Ảnh/sơ đồ kỹ thuật phục vụ report hoặc kiểm tra bản export. Một số file quan trọng:

| File | Nội dung |
|---|---|
| `aeb_functional_architecture.png` | Kiến trúc chức năng AEB từ cảm biến đến phanh |
| `radar_object_processing.png` | Pipeline radar point -> object/track |
| `camera_radar_fusion_projection.png` | Phép chiếu camera-radar |
| `predicted_path_corridor.png` | Hành lang quỹ đạo dự đoán |
| `ttc_stopping_distance.png` | Mô hình TTC/khoảng cách dừng |
| `aeb_staged_pid_state_machine.png` | State machine/staged PID |
| `final_demo_cutin_80_50_gap_25.png` | Ảnh demo cut-in PASS |
| `final_demo_cutin_100_60_gap_25.png` | Ảnh demo cut-in FAIL/giới hạn |
| `yolo_val_batch0_labels.png` | Ví dụ label/validation YOLO |
| `nguyenlyradar.png` | Minh họa nguyên lý radar |
| `carla.png` | Minh họa CARLA |

Nếu ảnh là bản cuối dùng trong report, nên cân nhắc copy sang `report/assets/` để đường dẫn ổn định hơn.

### `slides/generated/`

Bản ảnh phục vụ slide. Nội dung có thể trùng một phần với `generated_images/`. Dùng khi tạo hoặc chỉnh PowerPoint. Nếu chỉ dùng report, ưu tiên `report/assets/` hoặc `generated_images/` để tránh trùng lặp.

### `validate/`

Nhóm file kiểm tra bản export:

| File/thư mục | Vai trò |
|---|---|
| `aeb_report_draft.pdf` | PDF render từ DOCX/Markdown để kiểm tra layout |
| `aeb_report_text.txt` | Text extract từ bản export, dùng kiểm tra nội dung |
| `aeb_report_text_final.txt` | Text extract bản gần cuối/cuối |
| `page_map.json` | Mapping trang hoặc metadata kiểm tra render |
| `pages/page-*.png` | Ảnh từng trang để xem nhanh layout |

Các file này dùng cho QA hình thức, không phải nguồn nội dung chính. Snapshot hiện tại đã được track để có thể kiểm tra layout khi chuyển máy.

## Quy trình đề xuất khi sửa báo cáo

1. Với bản v3, sửa nội dung trong `report/chapters_v3/*.md`.
2. Build và export lại:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/usr/bin/python3 report/build_report_v3.py
/usr/bin/python3 report/export_report_v3.py
```

3. Export lại DOCX/PDF bằng công cụ đang dùng trên máy.
4. Nếu sinh ảnh mới, đặt tên rõ nghĩa và ghi nguồn trong caption/report.
5. Nếu file export cần chia sẻ qua Git, ưu tiên commit `.md`, `.csv`, ảnh nhỏ. Với `.docx`, `.pptx`, `.pdf` nặng, ưu tiên Drive/Release + SHA-256.

## Liên hệ với paper v4

Các export báo cáo/slides không thay thế evidence paper. Evidence repeatability cho paper v4 nằm ở:

```text
docs/log/PAPER_V4_EVALUATION_PROTOCOL.md
docs/log/repeatability/paper_v4_gpu_final/
docs/log/repeatability/artifacts/paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz
```

Khi viết paper v4, dùng `report/exports/` chủ yếu để lấy hình minh họa hoặc kiểm tra cách diễn giải trong báo cáo đồ án; dùng `docs/log/repeatability/` để lấy bảng số liệu chạy lặp.
