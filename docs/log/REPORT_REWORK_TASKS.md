# Task List Viết Lại Báo Cáo Đồ Án

File này ghi các việc cần làm trước và trong quá trình viết lại `report/report.md`.
Mục tiêu là tránh quên ngữ cảnh khi báo cáo được viết qua nhiều lượt chỉnh sửa.

## 1. Dọn Cấu Trúc Và Tài Liệu Dự Án

- [x] Cập nhật `README.md` để phản ánh trạng thái hiện tại: dataset v7 same-lane,
  fusion, staged PID, final evidence 66 kịch bản, launcher và report.
- [x] Giữ `README.md` ở mức giới thiệu/chạy nhanh, không biến thành báo cáo.
- [x] Tạo `docs/official/16_REPORT_FORMAT_AND_CAPTIONS.md` để chuẩn hóa form
  báo cáo, tên hình và tên bảng.
- [x] Bổ sung task list viết lại báo cáo tại file này.
- [x] Tách báo cáo full vào `report/chapters/*.md` và ghép bằng
  `report/build_report.py`.
- [ ] Rà lại các file `docs/official/*.md` sau khi report final chốt xong.
- [ ] Không đưa dataset/log/video thô vào Git; chỉ đưa summary, script và tài
  liệu cần thiết.
- [ ] Trước khi nộp, thêm link GitHub và link Google Drive video vào phụ lục.

## 2. Cập Nhật Phạm Vi Và Chuẩn Tham Khảo NCAP

- [x] Thêm phần Euro NCAP/NCAP vào chương tổng quan.
- [x] Nêu rõ bộ test của đồ án chỉ học theo cấu trúc car-to-car của NCAP, không
  phải bài chứng nhận NCAP chính thức.
- [x] Giải thích các nhóm CCRs, CCRm, CCRb:
  - CCRs: xe phía trước đứng yên.
  - CCRm: xe phía trước chạy chậm hơn.
  - CCRb: xe phía trước đang chạy rồi phanh.
- [x] Nêu cut-in là tình huống mở rộng để tìm giới hạn, không phải phần CCR rear
  cơ bản trong bộ C2C rear cũ.
- [x] Tách kết quả theo hai nhóm:
  - Bộ test mục tiêu: dải vận tốc/khoảng cách mong muốn, dùng để chứng minh hệ
    thống hoạt động tốt.
  - Bộ test giới hạn: mở rộng tốc độ/gap để xác định khi nào hệ thống bắt đầu
    không đảm bảo tránh va chạm.

## 3. Viết Sâu Các Phần Thuật Toán

- [ ] Radar processing phải viết như đặc tả thuật toán, không viết chung chung:
  - Tên mục trong report: `3.3. Xử Lý Dữ Liệu Radar`.
  - Nêu rõ đầu vào CARLA radar gồm những trường nào và được đưa về hệ ego ra sao:
    `x_forward_m`, `y_right_m`, `z_up_m`, `relative_velocity_mps`,
    `world_location`.
  - Nêu đúng file/hàm triển khai:
    `core/radar_aeb_pipeline.py::valid_path_target`,
    `is_ground_point`, `height_above_road`,
    `perception/radar/radar_object_tracker.py::cluster_radar_points`,
    `_points_are_neighbors`, `_make_measurement`,
    `RadarClusterTracker.update`, `_associate`, `_predicted_position`,
    `core/radar_object.py::radar_object_from_cluster`,
    `cluster_confidence`,
    `core/target_selector.py::select_aeb_target`.
  - Nêu đầy đủ các hằng số từ `configs/sensors.yaml`:
    radar range/FOV/PPS/tick, `min_radar_forward_distance_m`,
    `min_radar_z_up_m`, `max_radar_z_up_m`, `min_height_above_road_m`,
    `max_lateral_offset_m`, cluster `tolerance_m`,
    `velocity_tolerance_mps`, `vertical_tolerance_m`, `min_points`,
    `confirm_frames`, `release_frames`, `match_distance_m`,
    `match_velocity_mps`, target gate `selected_confirm_frames`.
  - Viết công thức lọc vùng quan tâm:
    `x_forward` trong `[min_forward, radar_range]`, `z_up` trong `[z_min,z_max]`,
    khoảng cách tới predicted path nhỏ hơn lateral limit.
  - Viết công thức lọc mặt đường:
    `h = z_point - z_road`, nếu `h < min_height_above_road_m` thì bỏ.
  - Viết điều kiện gom cụm:
    khoảng cách phẳng <= `tolerance_m`, chênh cao <= `vertical_tolerance_m`,
    chênh vận tốc <= `velocity_tolerance_mps`.
  - Viết rõ measurement của cụm:
    `x_forward` lấy percentile 20%, `y/z/v` lấy median, vì sao không dùng mean.
  - Viết tracking qua frame:
    dự đoán `x_hat = x + v_rel*dt`, `y_hat = y`,
    match bằng khoảng cách và chênh vận tốc,
    `confirmed` khi `hit_streak >= confirm_frames`,
    xóa khi `missed_frames >= release_frames`.
  - Viết công thức confidence proxy:
    `score = 0.4*point_score + 0.4*hit_score + 0.2*fresh_score`,
    giải thích đây không phải RCS/SNR của radar thật.
  - Viết rõ output trả về là `RadarObjectList` gồm:
    `object_id`, `longitudinal_m`, `lateral_m`, `height_m`,
    `relative_velocity_mps`, `point_count`, `confidence`, `confirmed`,
    `age_frames`, `hit_streak`, `missed_frames`, `ttc_s`.
  - Viết rõ chọn target:
    chỉ object confirmed và không stale, ưu tiên TTC hữu hạn nhỏ nhất,
    sau đó khoảng cách dọc nhỏ nhất; target còn đi qua target gate/fusion ở bước sau.
  - Nhấn mạnh đây là đồ án môn học/kỹ thuật, không phải báo cáo thường niên:
    mọi thuật toán phải đủ rõ để người đọc hiểu cách triển khai, hằng số,
    công thức, đầu vào/đầu ra và lý do chọn.
- [ ] TTC và khoảng cách dừng phải viết rõ như phần thuật toán:
  - Tên mục trong report: `3.4. Tính Thời Gian Va Chạm Và Khoảng Cách Dừng`.
  - Nêu đúng file/hàm triển khai:
    `control/brake.py::compute_ttc`,
    `BinaryAEB.required_stopping_distance`,
    `BinaryAEB.decide`.
  - Nêu quy ước dấu của `relative_velocity_mps`:
    âm là target đang tiến lại gần ego, dương là đang rời xa.
  - Viết công thức `v_closing = -v_rel` và điều kiện `v_closing > 0`.
  - Viết công thức TTC theo từng trường hợp:
    `d <= 0 -> TTC = 0`, `v_rel < 0 -> TTC = d / (-v_rel)`,
    `v_rel >= 0 -> TTC = inf`.
  - Giải thích vì sao chỉ TTC là chưa đủ, nhất là ở tốc độ cao.
  - Viết công thức khoảng cách dừng:
    `d_ego = v_ego*t_response + v_ego^2/(2*a_ego)`,
    `d_target = v_target^2/(2*a_target)`,
    `v_target = max(0, v_ego + v_rel)`,
    `d_required = max(offset, d_ego - d_target + offset)`.
  - Viết rõ `distance_margin_m = distance_m - required_distance_m`.
  - Nêu đầy đủ hằng số từ `configs/sensors.yaml`:
    `warning_ttc_s`, `brake_ttc_s`, `release_ttc_s`,
    `response_time_s`, `ego_emergency_decel_mps2`,
    `target_emergency_decel_mps2`, `stopping_distance_offset_m`,
    `min_closing_speed_mps`, `min_valid_distance_m`, `max_valid_distance_m`.
  - Nêu output trả về cho AEB decision:
    `ttc_s`, `required_distance_m`, `distance_margin_m`,
    `reason`, `state`, `brake`.
- [ ] Camera/YOLO phải viết đủ bốn phần: lý do chọn model, thu data, fine-tune,
  đánh giá model:
  - Tên mục trong report: `3.5. Thu Dữ Liệu Và Fine-Tune YOLO26n`.
  - Nêu lý do chọn YOLO26n:
    bản `n` nhẹ nhất, phù hợp GPU laptop 4 GB VRAM, bài toán một class `car`,
    hỗ trợ export ONNX và chạy runtime/fusion mượt hơn model lớn.
  - Giải thích ngắn nguyên lý YOLO:
    one-stage detector, dự đoán bbox/class/confidence, các loss chính
    `box_loss`, `cls_loss`, `dfl_loss`, xử lý box trùng bằng NMS.
  - Nêu cách tạo label từ CARLA ground truth:
    spawn ego/NPC, lấy bbox 3D actor, chiếu 3D sang ảnh 2D, dùng depth/semantic
    để ước lượng visible ratio, fit box theo phần xe nhìn thấy, ghi label YOLO.
  - Nêu rõ ground truth chỉ dùng để tạo dataset, runtime AEB không dùng ground
    truth để quyết định phanh.
  - Nêu các kịch bản thu data:
    v3-v6 để thử nghiệm, v7 same-lane là bộ final; Town04, Tesla Model 3,
    4 xe cùng làn, khoảng cách ban đầu khoảng 30/65/100/135 m, lưu mỗi 40 frame.
  - Đánh giá dataset:
    train/val/test = 1505/300/200 ảnh, box = 1872/379/264,
    empty ratio khoảng 16-21%, near-duplicate dưới 11%, khoảng cách label tới
    khoảng 100 m, train có 21 mẫu xe.
  - Nêu cấu hình fine-tune:
    `models/yolo26n.pt`, imgsz 640, epochs 100, patience 20, batch 16,
    AdamW, lr0 0.001, mosaic 0.5, seed 2026.
  - Đánh giá model bằng biểu đồ:
    `results.png`, `BoxPR_curve.png`, `BoxF1_curve.png`,
    `confusion_matrix.png`, `val_batch*_pred.jpg`.
  - Nêu metric run final:
    best epoch 78, precision 0.9919, recall 0.9642, mAP50 0.9940,
    mAP50-95 0.9495; epoch cuối mAP50-95 0.9466.
  - Nhắc lại vai trò:
    YOLO xác nhận object là ô tô, radar vẫn là nguồn chính cho khoảng cách,
    vận tốc tương đối, TTC và khoảng cách dừng.
- [x] Fusion phải viết như đặc tả thuật toán camera-radar:
  - Tên mục trong report: `3.6. Hợp Nhất Dữ Liệu Cảm Biến Camera-Radar`.
  - Nhấn mạnh runtime không dùng ground truth/actor id của CARLA để quyết định
    target; chỉ dùng radar object/point, ảnh camera, YOLO bbox và transform cảm
    biến.
  - Nêu đúng file/hàm triển khai:
    `ui/manual_control_common.py::camera_intrinsic`,
    `project_world_to_camera`, `nms_detections`,
    `ui/fusion_view.py::_project_radar_points`,
    `_match_radar_to_boxes`,
    `ui/aeb_demo_view.py::_project_radar_points`,
    `_match_radar_to_boxes`,
    `scripts/run_fusion_aeb_scenarios.py::_confirm_target`,
    `_fusion_gated_decision`.
  - Viết ma trận nội tại camera:
    `f = W/(2*tan(FOV/2))`, `K=[[f,0,W/2],[0,f,H/2],[0,0,1]]`.
  - Viết biến đổi hệ tọa độ:
    world point -> inverse camera transform -> Unreal camera coordinates ->
    camera coordinates `[Y, -Z, X]`.
  - Viết phép chiếu:
    `pixel = K*[Xc,Yc,Zc]^T`, `u=px/pz`, `v=py/pz`,
    bỏ điểm có `Zc <= 0` hoặc ngoài ảnh.
  - Nêu lọc radar trước khi chiếu:
    `min_radar_forward_distance_m`, `max_lateral_offset_m`,
    `min/max_radar_z_up_m`, radar range, hoặc dùng `valid_path_target`.
  - Nêu YOLO detection và NMS:
    confidence 0.25, `nms_iou=0.50`, class `car`.
  - Viết điều kiện match:
    `x1 <= u <= x2` và `y1 <= v <= y2`; nếu nhiều điểm trong bbox thì chọn
    điểm gần ego nhất theo `x_forward_m`.
  - Viết logic fusion gate:
    radar không BRAKE thì giữ nguyên; radar BRAKE và fusion confirmed thì cho
    phanh; radar BRAKE nhưng không confirmed thì chặn phanh về RELEASE.
  - Nêu `confirmation_hold_s=0.35s` để giảm lỗi lệch frame camera/radar/YOLO.
  - Liệt kê các reason khi fusion không xác nhận:
    `no_radar_target`, `radar_target_without_world_location`,
    `camera_not_ready`, `no_yolo_detection`, `radar_target_behind_camera`,
    `radar_target_outside_image`, `radar_target_not_in_yolo_box`.
  - Nêu ưu/nhược điểm:
    giảm phanh nhầm nhưng có thể bỏ phanh nếu YOLO miss hoặc hiệu chỉnh lệch;
    đây là geometric gating, chưa phải multi-sensor Kalman/probabilistic fusion.
- [x] Dự đoán quỹ đạo di chuyển phải viết rõ thuật toán:
  - Tên mục trong report: `3.7. Dự Đoán Quỹ Đạo Di Chuyển`.
  - Nêu đúng file/hàm:
    `core/radar_aeb_pipeline.py::update_predicted_path`,
    `constant_curvature_path`, `distance_to_predicted_path`,
    `valid_path_target`.
  - Nêu đầu vào: ego speed, yaw rate, steering, không dùng ground truth/lane id.
  - Viết công thức độ cong từ yaw rate:
    `kappa_yaw = yaw_rate / ego_speed`.
  - Viết công thức độ cong từ steering:
    `kappa_steer = steer_gain * steer`.
  - Viết công thức trộn:
    `kappa_desired = 0.75*kappa_yaw + 0.25*kappa_steer` khi đủ tốc độ/yaw rate.
  - Viết giới hạn và làm mượt độ cong:
    clip theo `path_max_abs_curvature_1pm`,
    `kappa_t = kappa_prev + alpha*(kappa_desired-kappa_prev)`.
  - Viết công thức constant curvature path:
    `theta=kappa*s`, `x=sin(theta)/kappa`,
    `y=(1-cos(theta))/kappa`, nếu kappa gần 0 thì `x=s,y=0`.
  - Viết công thức horizon:
    `L = min(radar_range, max(path_min_horizon_m, ego_speed*path_horizon_time_s))`.
  - Viết công thức khoảng cách radar point tới path segment bằng projection.
  - Nêu các hằng số path từ `configs/sensors.yaml`.
- [x] Brake control phải viết rõ quá trình chọn target, risk và staged PID:
  - Tên mục trong report:
    `3.8. Chọn Mục Tiêu, Đánh Giá Rủi Ro Va Chạm Và Điều Khiển Phanh PID`.
  - Nêu đúng file/hàm:
    `core/target_selector.py::select_aeb_target`,
    `core/radar_aeb_pipeline.py::_target_ready_for_brake`,
    `control/brake.py::BinaryAEB.decide`,
    `_desired_state`, `_apply_hysteresis`, `_pid_brake_command`,
    `_staged_pid_target`, `_rate_limited_brake`, `make_brake_control`.
  - Viết target selection:
    chỉ confirmed/non-stale, ưu tiên TTC hữu hạn nhỏ nhất, sau đó khoảng cách dọc.
  - Viết target gate:
    `selected_confirm_frames=5`, immediate brake theo distance/margin.
  - Viết state machine: NORMAL, WARNING, BRAKE, RELEASE.
  - Viết công thức trạng thái theo TTC và stopping distance margin.
  - Viết hysteresis: min hold time, hold until stopped, release TTC.
  - Viết công thức PID:
    margin error, TTC error, integral clamp, derivative positive-only,
    brake target.
  - Viết staged PID:
    soft/medium/hard/emergency cap theo TTC, distance và distance margin.
  - Viết rate limit tăng/giảm phanh và output VehicleControl.
  - Nêu rõ staged PID là bản cuối tạm thời, các mode cũ giữ để so sánh.

## 4. Hình Ảnh Cần Bổ Sung

Các hình này hiện cần chụp lại, tự vẽ hoặc dùng AI tạo ảnh minh họa kỹ thuật.

- [ ] Hình nguyên lý radar ô tô FMCW.
  - Gợi ý: dùng AI tạo sơ đồ kỹ thuật đơn giản hoặc tự vẽ bằng draw.io.
- [ ] Hình pipeline radar từ điểm đo đến object list.
  - Gợi ý: tự vẽ bằng draw.io/PowerPoint để đúng thuật toán của project.
- [ ] Hình mô hình TTC.
  - Gợi ý: tự vẽ ego-target, khoảng cách `d`, vận tốc đóng.
- [x] Hình phép chiếu fusion camera-radar.
  - Đã thêm `report/assets/camera_radar_fusion_projection.svg`.
- [x] Hình hành lang quỹ đạo dự đoán.
  - Đã thêm `report/assets/predicted_path_corridor.svg`.
- [ ] Hình máy trạng thái AEB nhiều tầng.
  - Gợi ý: tự vẽ SAFE/WARNING/SOFT/HARD/EMERGENCY/RELEASE.
- [ ] Hình kiến trúc tổng thể hệ thống.
  - Gợi ý: tự vẽ block diagram từ CARLA đến VehicleControl.
- [ ] Hình UI final 3 màn.
  - Gợi ý: chụp screenshot lúc chạy `ui/aeb_demo_view.py`.
- [ ] Hình sensor coverage.
  - Có thể dùng `outputs/sensor_coverage/near_side_view.png` và
    `far_top_view.png`.
- [ ] Hình biểu đồ phanh đại diện.
  - Có thể dùng `logs/final_evidence_staged_pid_20260628/plots/`.

## 5. Bảng Biểu Cần Có

- [x] Bảng so sánh camera/radar/LiDAR/ultrasonic.
- [x] Bảng mapping scenario của đồ án với nhóm NCAP tham khảo.
- [x] Bảng cấu hình camera và radar.
- [x] Bảng cấu trúc thư mục dự án.
- [x] Bảng thống kê dataset v7 same-lane.
- [x] Bảng kết quả YOLO26n.
- [x] Bảng so sánh các bộ phanh.
- [x] Bảng kết quả bộ test mục tiêu.
- [x] Bảng kết quả bộ test giới hạn.
- [x] Bảng 2-3 case đại diện cho mỗi nhóm scenario.
- [x] Bảng các trường hợp không đạt và nguyên nhân.

## 6. Những Điểm Cần Sửa Trong `report/report.md`

- [x] Phần tóm tắt cần nói kịch bản được xây dựng dựa trên/ lấy cảm hứng từ
  tiêu chuẩn đánh giá NCAP.
- [x] Đổi tên “dataset v7 same-lane” trong caption để tránh hiểu nhầm là YOLOv7.
  Gợi ý: “bộ dữ liệu phiên bản v7 same-lane”.
- [x] Bỏ phần đường dẫn video local khỏi nội dung chính; đưa link Drive vào phụ
  lục sau.
- [ ] Bỏ phụ lục A/B dạng lệnh chạy chi tiết khỏi report chính nếu làm báo cáo
  nộp trường; thay bằng link GitHub và mô tả ngắn.
- [x] Bỏ các mục “Tài liệu nội bộ project” trong tài liệu tham khảo. README sẽ
  chịu trách nhiệm hướng dẫn đọc tài liệu nội bộ.
- [x] Giới thiệu lại cấu trúc thư mục dự án trong chương thiết kế.
- [x] Bổ sung phần UI final 3 màn.
- [x] Bổ sung so sánh staged PID với binary/PID v1/PID v2.
- [x] Bổ sung nhận xét kết quả theo từng nhóm scenario, mỗi nhóm 2-3 đại diện.

## 7. Nguồn Tham Khảo Nên Dùng Trong Report

- Euro NCAP AEB C2C Test Protocol v4.2, June 2023.
- Euro NCAP AEB Test Protocol v1.0, July 2013, dùng để giải thích CCRs/CCRm/CCRb.
- Euro NCAP Safety Assist Assessment Protocol, dùng để nói cách đánh giá dựa
  trên tốc độ va chạm còn lại.
- CARLA 0.9.11 documentation.
- Ultralytics YOLO documentation.
- Autoware, openpilot, Apollo, dùng ở mức tham khảo kiến trúc.
