# 12. Quy Trình Làm Việc Với AI

File này quy định cách dùng AI trong dự án để việc code, test, viết tài liệu và
review không bị lệch khỏi mục tiêu AEB CARLA.

Nếu một AI/người mới nhảy vào dự án lần đầu, hãy đọc thêm
`docs/official/15_CONTRIBUTING_AND_TASK_WORKFLOW.md`. File đó đóng vai trò
onboarding chi tiết: thứ tự đọc tài liệu, bản đồ module, cách nhận task, test
tối thiểu và mẫu bàn giao kết quả.

## Vai Trò Của AI

AI có thể hỗ trợ:

- Đọc codebase và giải thích pipeline.
- Refactor cấu trúc file/thư mục.
- Viết hoặc sửa code theo yêu cầu đã rõ.
- Sinh unit test, smoke test và batch scenario.
- Phân tích log, ảnh, video thử nghiệm.
- Viết tài liệu kỹ thuật, research và prompt slide.
- Review code trước khi commit/push.

AI không tự thay quyết định kỹ thuật cuối cùng của người làm dự án. Các quyết
định như phạm vi sensor, tiêu chí PASS/FAIL, hướng báo cáo và mức độ chấp nhận
UI/cảm giác phanh vẫn do chủ dự án duyệt.

## Vai Trò Của Người Làm Dự Án

Người làm dự án cần:

- Mô tả mục tiêu và kỳ vọng rõ ràng.
- Chạy hoặc bật CARLA server khi cần test mô phỏng.
- Kiểm tra UI/cảm giác lái vì AI không trực tiếp cảm nhận được trải nghiệm thật.
- Duyệt các thay đổi lớn về thuật toán và tài liệu.
- Quyết định khi nào một kết quả đủ tốt để ghi vào tài liệu chính thức.

## Nguyên Tắc Sửa Code

- Đọc file liên quan trước khi sửa.
- Giữ cấu trúc hiện tại:
  - `ui/`: giao diện/debug view.
  - `scripts/`: batch scenario, collect data, train model.
  - `core/`: pipeline và dữ liệu dùng chung.
  - `perception/`: xử lý cảm biến.
  - `control/`: quyết định phanh/controller.
  - `configs/`: cấu hình.
- Không nhồi thuật toán phức tạp vào UI nếu có thể đặt trong `core/`,
  `perception/` hoặc `control/`.
- Không đổi tên file/thư mục lớn nếu chưa có lý do rõ ràng.
- Không xóa hoặc revert thay đổi của người dùng nếu chưa được yêu cầu.

## Nguyên Tắc Cập Nhật Tài Liệu

- `README.md`: chỉ cập nhật ngắn gọn trạng thái, lệnh chạy chính và thứ tự đọc.
- `docs/log/EXPERIMENT_LOG.md`: cập nhật thường xuyên khi có test, lỗi, sửa,
  kết quả mới.
- `docs/official/*`: cập nhật khi pipeline/kết luận kỹ thuật đã tương đối chốt.
- `docs/research/*`: cập nhật khi có nghiên cứu mới, so sánh repo hoặc so sánh
  với cảm biến/thực tế.
- `docs/history/legacy_docs/*`: chỉ để tra cứu tài liệu cũ, không dùng làm nguồn chính.

## Nguyên Tắc Test

Sau khi sửa code logic:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
../venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Sau khi sửa radar/AEB hoặc scenario, nên chạy smoke test CARLA:

```bash
../venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/radar_only_regression.yaml \
  --control-mode physics \
  --scenario clear_road_50 \
  --scenario ccrs_50 \
  --load-map
```

Nếu thay đổi lớn, cần chạy regression rộng hơn và ghi kết quả vào
`docs/log/EXPERIMENT_LOG.md`.

## Nguyên Tắc Với Data, Log Và Model

Không commit/push mặc định:

- `$AEB_WORKSPACE_ROOT/datasets/`
- `$AEB_WORKSPACE_ROOT/runs/`
- `$AEB_WORKSPACE_ROOT/training/`
- video/ảnh log nặng
- model `.pt`, `.onnx`, `.engine`

Chỉ đưa các file này lên GitHub nếu đã có lý do rõ ràng, ví dụ release model
nhỏ, sample ảnh minh họa hoặc artifact cần cho báo cáo.

## Cách Giao Task Cho AI

Một yêu cầu tốt nên có:

- Mục tiêu: muốn sửa/làm gì.
- File liên quan nếu biết.
- Lệnh đã chạy và lỗi nếu có.
- Kết quả mong muốn.
- Có cần chạy CARLA/test/push GitHub hay không.

Ví dụ:

```text
Sửa radar-only AEB để giảm phanh nhầm khi xe cua.
File liên quan: core/radar_aeb_pipeline.py, perception/radar/radar_object_tracker.py.
Sau khi sửa chạy unit test và smoke test clear_road_50 + ccrs_50.
Ghi kết quả vào docs/log/EXPERIMENT_LOG.md.
```

## Checklist Trước Khi Push GitHub

1. Chạy unit test.
2. Chạy smoke test nếu sửa logic AEB/CARLA.
3. Kiểm tra `git diff --check`.
4. Kiểm tra `git status --short`.
5. Đảm bảo không stage dataset/log/model nặng.
6. Commit message rõ ràng.
7. Push đúng branch.

## Quy Ước Báo Cáo Kết Quả

Khi AI hoàn thành một task, nên báo ngắn gọn:

- Đã sửa file nào.
- Logic thay đổi chính là gì.
- Đã chạy test nào và kết quả.
- Có phần nào chưa làm được hoặc cần người dùng kiểm tra bằng mắt/cảm giác lái.

Mục tiêu là sau này đọc lại có thể hiểu dự án tiến triển như thế nào mà không
cần lục toàn bộ lịch sử chat.
