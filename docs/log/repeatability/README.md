# Repeatability Evidence For Paper V3/V4

Thư mục này chứa các bảng và artifact nhẹ đã được đưa vào Git để có thể kéo về máy khác và phân tích tiếp cho `paper_v4`.

## Nguyên tắc lưu artifact

- `logs/` và `outputs/` vẫn bị `.gitignore` vì có thể rất lớn.
- Các bảng summary nhỏ được commit trực tiếp dưới `docs/log/repeatability/<run-id>/`.
- Raw log CSV của các run quan trọng được nén thành `.tar.gz` trong `docs/log/repeatability/artifacts/` để máy khác vẫn có thể phân tích lại.
- `SHA256SUMS.txt` lưu hash của các archive để kiểm tra khi copy/chuyển máy.

## Run đã lưu

### Full suite fusion repeat3

Run ID:

```text
paper_v3_fusion_full66_repeat3_noreload
```

Bảng đã track:

```text
paper_v3_fusion_full66_repeat3_noreload/repeatability_summary.md
paper_v3_fusion_full66_repeat3_noreload/repeatability_by_family.csv
paper_v3_fusion_full66_repeat3_noreload/repeatability_by_scenario.csv
```

Raw log archive:

```text
artifacts/paper_v3_fusion_full66_repeat3_noreload.tar.gz
```

### Full suite fusion repeat5

Run ID:

```text
paper_v3_fusion_full66_repeat5_noreload
```

Bảng đã track:

```text
paper_v3_fusion_full66_repeat5_noreload/repeatability_summary.md
paper_v3_fusion_full66_repeat5_noreload/repeatability_by_family.csv
paper_v3_fusion_full66_repeat5_noreload/repeatability_by_scenario.csv
```

Raw log archive:

```text
artifacts/paper_v3_fusion_full66_repeat5_noreload.tar.gz
```

### Radar-only full suite repeat5

Run ID:

```text
paper_v3_radar_only_full66_repeat5_noreload
```

Bảng đã track:

```text
paper_v3_radar_only_full66_repeat5_noreload/repeatability_summary.md
paper_v3_radar_only_full66_repeat5_noreload/repeatability_by_family.csv
paper_v3_radar_only_full66_repeat5_noreload/repeatability_by_scenario.csv
```

Raw log archive:

```text
artifacts/paper_v3_radar_only_full66_repeat5_noreload.tar.gz
```

### Fusion vs radar-only repeat5 comparison

```text
fusion_vs_radar_only_repeat5_comparison.md
fusion_vs_radar_only_repeat5_comparison.csv
```

### Negative/regression repeat5

Run IDs:

```text
paper_v3_fusion_regression_repeat5_noreload
paper_v3_radar_only_regression_repeat5_noreload
paper_v3_fusion_on_radar_regression_repeat5_noreload
```

Tracked summaries:

```text
paper_v3_fusion_regression_repeat5_noreload/
paper_v3_radar_only_regression_repeat5_noreload/
paper_v3_fusion_on_radar_regression_repeat5_noreload/
negative_regression_repeat5_comparison.md
```

Raw log archives:

```text
artifacts/paper_v3_fusion_regression_repeat5_noreload.tar.gz
artifacts/paper_v3_radar_only_regression_repeat5_noreload.tar.gz
artifacts/paper_v3_fusion_on_radar_regression_repeat5_noreload.tar.gz
```

### Boundary probes x10

Raw log archives:

```text
artifacts/paper_v3_probe_fusion_ccrb_80_gap_20_repeat10_noreload.tar.gz
artifacts/paper_v3_probe_fusion_ccrb_95_gap_20_repeat10_noreload.tar.gz
artifacts/paper_v3_probe_fusion_ccrb_95_gap_30_repeat10_noreload.tar.gz
artifacts/paper_v3_probe_fusion_ccrb_110_gap_20_repeat10_noreload.tar.gz
```

Các kết quả chính của probe đã được ghi trong:

```text
../PAPER_V3_REPRODUCTION_NOTES.md
```

## Môi trường reproduction

Thông tin môi trường đã track tại:

```text
environment_20260818/
```

Gồm commit, model SHA-256, Python versions, `pip freeze`, `nvidia-smi`, `uname`.

## Cách khôi phục raw logs sau khi clone/pull

Từ thư mục `aeb/`:

```bash
mkdir -p logs
for f in docs/log/repeatability/artifacts/*.tar.gz; do
  tar -xzf "$f" -C logs
 done
```

Kiểm tra hash archive:

```bash
sha256sum -c docs/log/repeatability/artifacts/SHA256SUMS.txt
```

Sau khi giải nén, ví dụ full-suite x5 nằm tại:

```text
logs/paper_v3_fusion_full66_repeat5_noreload/
```

Có thể sinh lại bảng bằng:

```bash
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/summarize_repeatability.py \
  logs/paper_v3_fusion_full66_repeat5_noreload \
  --output-dir outputs/paper_v3_reproduction/repeatability/paper_v3_fusion_full66_repeat5_noreload
```

Nếu chạy trên máy khác, thay path Python bằng venv CARLA tương ứng.

## Ghi chú

Archive hiện còn nhỏ: fusion full66 repeat3 khoảng 2.2 MB, fusion full66 repeat5 khoảng 3.6 MB, radar-only full66 repeat5 khoảng 2.9 MB; regression archives khoảng 0.8--1.2 MB sau nén. Nếu sau này chạy repeat10 hoặc nhiều ablation và artifact quá lớn, nên đưa raw archive lên GitHub Release/Drive rồi chỉ commit bảng summary + URL + SHA-256.
