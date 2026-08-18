# Changelog

## paper_v3 — 2026-08-18

- Thực hiện focused literature review qua Crossref, OpenAlex và arXiv; kết quả
  được hợp nhất vào `HO_SO_NGHIEN_CUU_VA_PHAN_BIEN.md`.
- Viết lại paper theo định vị *sensor-to-brake engineering baseline* thay vì
  claim thuật toán fusion/PID mới.
- Đổi title thành *A Sensor-to-Brake AEB Pipeline in CARLA with Object-Level
  Radar, Camera Verification, and Limit-Finding Evaluation*.
- Bổ sung bảng positioning với các công trình radar--vision AEB, closest
  in-path association, curved-road staged braking, CARLA DVS AEB và radar-guided
  camera verification trên xe thật.
- Audit code/config và sửa các claim quan trọng: map-height privilege, execution
  order, frame gates, wall-time camera hold, brake latch, PASS criteria và final
  suite composition.
- Phân biệt ODD với intended-range/stress subsets.
- Làm rõ 63/66 chỉ là configured-case outcome, không phải reliability estimate.
- Bổ sung threat-to-validity đầy đủ, trong đó có single run, không ablation,
  final suite không có negative case và thiếu raw logs/model artifacts.
- Thêm kiến trúc mới `report/assets/aeb_closed_loop_architecture_en.png`.
- Viết lại đầy đủ bản review tiếng Việt để cùng claim/hình/bảng/reference với
  bản tiếng Anh.
- Hợp nhất literature review, strict review, source map và revision notes thành
  một hồ sơ tiếng Việt: `HO_SO_NGHIEN_CUU_VA_PHAN_BIEN.md`.
- Tăng validation trong `build.sh`: fail khi citation/reference chưa resolve,
  thiếu PDF hoặc bản tiếng Anh không đúng 6 trang.
- Bổ sung kế hoạch hoàn thiện paper trên máy CARLA: repeated baseline,
  radar-only/camera-gated ablation, negative regression, controller ablation,
  simulation-time synchronization và checklist artifact cho `paper_v4`.

## paper_v2 — 2026-08-17

- Định vị paper quanh object-level radar, radar-first/camera-verified gate,
  path-aware risk và ODD-separated evaluation.
- Sửa mô tả aggregate 66 case thành 24 CCRm, 30 CCRb và 12 cut-in.

## paper_v1 — 2026-08-15

- Hoàn thiện manuscript IEEE song ngữ đầu tiên và quy tắc build tiếng Anh đúng
  6 trang.
