# Changelog

## paper_v2 — 2026-08-17

- Tạo `paper_v2` từ `paper_v1`, giữ quy tắc build song ngữ và bản tiếng Anh đúng 6 trang.
- Đổi tiêu đề để làm rõ định vị mới: *A Closed-Loop AEB Pipeline in CARLA Using Object-Level Radar, YOLO Verification, and Staged PID Braking*.
- Viết lại abstract và phần đóng góp theo hướng engineering-system study: object-level CARLA radar, radar-first/camera-verified gate, path-aware TTC/stopping-distance risk assessment, staged PID, và ODD-separated limit-finding evaluation.
- Rà consistency của final evidence: kết quả 66-case aggregate trong paper gồm 24 CCRm, 30 CCRb và 12 cut-in; các clear-road/adjacent/curve/cut-out/multi-actor run được mô tả là kiểm tra bổ sung, không gộp vào tỷ lệ 63/66.
- Giữ giới hạn claim: không NCAP certification, không real-vehicle validation, không statistical reliability hoặc ablation claim.
- Cập nhật bản tiếng Việt review để khớp title, abstract, contribution và cách diễn giải final evidence.

## paper_v1 — 2026-08-15

- Cập nhật tiêu đề thống nhất: *An Automatic Emergency Braking System in CARLA Using Radar–Camera Fusion and Staged PID Control*.
- Khóa thông tin tác giả và email liên hệ `hoangmai04222@gmail.com` cho cả hai bản.
- Thay phần tóm tắt tiếng Việt theo nội dung đã được cung cấp: làm rõ radar là nguồn đo chính, camera--YOLO là tầng xác nhận ngữ nghĩa, và báo cáo đầy đủ kết quả 38/38, 25/28, 63/66 cùng ba ca va chạm.
- Bản tiếng Anh là manuscript chính và bắt buộc đúng 6 trang; bản tiếng Việt là bản review, giữ nguyên nội dung/font và không bị cắt để ép số trang.
- `build.sh` luôn build cả PDF tiếng Anh lẫn PDF tiếng Việt.
