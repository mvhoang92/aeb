# Paper v5.1 Source Map

## Manuscripts

- English: `aeb_ieee_6page.tex` / `aeb_ieee_6page.pdf` (six pages).
- Vietnamese author copy: `aeb_ieee_6page_vi.tex` / `aeb_ieee_6page_vi.pdf`.
- Bibliography: `references.bib`.
- Figure: `figures/scenario_level_tradeoff.png`, copied byte-for-byte from the
  v5-derived evidence directory.
- Build: `build.sh`.
- Validator: `../../scripts/analysis/validate_v51_manuscript_claims.py`.

## Frozen scientific sources

- Protocol and thresholds:
  `../../docs/log/PAPER_V4_EVALUATION_PROTOCOL.md`.
- Final campaign narrative:
  `../../docs/log/repeatability/paper_v4_gpu_final/FINAL_GPU_EVIDENCE.md`.
- Raw archive:
  `../../docs/log/repeatability/artifacts/paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz`.
- Derived scenario/severity tables:
  `../../docs/log/repeatability/paper_v5_derived/`.
- Derivation code:
  `../../scripts/analysis/analyze_v5_review_metrics.py`.

## Main claim sources

| Manuscript claim | Source |
|---|---|
| 105 core and 14 hold-out named conditions | `named_scenario_metrics.csv` |
| Core/hold-out TP, FP, TN, FN, PASS and collision | `named_scenario_metrics.csv` |
| Paired policy outcomes | `named_paired_outcomes.csv` |
| Bench/cart/warning pre-impact severity | `collision_severity_summary.csv` |
| Ghost duration, onset, deceleration and stop count | `false_brake_severity_runs.csv` and `false_brake_severity_summary.csv` |
| CUDA sessions, inference count, latency and errors | `FINAL_GPU_EVIDENCE.md`, campaign manifests/raw metadata |
| Detector and dataset metrics | `dataset_audit_v7_same_lane.json`, frozen runtime metadata |

## Literature positioning

The related-work claims are supported by the DOI/arXiv entries in
`references.bib`, especially: Kim and Song (2013), Hsu et al. (2015), Zhang
and Cao (2019), Sandblom and Brännström (2011), Kraus et al. (2021),
Lindenmaier et al. (2022), Rao et al. (2024), and Akula et al. (2026).
The Akula paper is discussed as a nearby method, not as a numerical baseline,
because its sensor, speed, labels and verification mechanism differ.
