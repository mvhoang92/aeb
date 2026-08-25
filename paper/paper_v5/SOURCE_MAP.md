# Paper v5 Source Map

## Manuscripts

- English master: `aeb_ieee_6page.tex` / `aeb_ieee_6page.pdf` (exactly 6 pages)
- Vietnamese full review: `aeb_ieee_6page_vi.tex` / `aeb_ieee_6page_vi.pdf`
- Shared bibliography: `references.bib`
- Shared generated figure: `figures/scenario_level_tradeoff.png`
- Build gate: `build.sh`

## Frozen campaign (unchanged from v4)

- Policy/protocol tag: `safe-fallback-eval-v1`
- Protocol: `../../docs/log/PAPER_V4_EVALUATION_PROTOCOL.md`
- Final evidence: `../../docs/log/repeatability/paper_v4_gpu_final/`
- Raw archive: `../../docs/log/repeatability/artifacts/paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz`

## Reviewer-derived v5 evidence

- Generation script: `../../scripts/analyze_v5_review_metrics.py`
- Output: `../../docs/log/repeatability/paper_v5_derived/`
- Primary CSV: `named_scenario_metrics.csv`
- Severity CSV: `collision_severity_summary.csv`, `false_brake_severity_summary.csv`
- Narrative audit: `V5_REVIEW_DERIVED_EVIDENCE.md`

## Detector evidence

- Frozen GPU config: `../../configs/sensors_fusion_safe_fallback_batch_gpu.yaml`
- Dataset-audit snapshot: `../../docs/log/repeatability/paper_v5_derived/dataset_audit_v7_same_lane.json`
- Training config: `../../configs/model_training.yaml`
- Model full hash is present in final runtime metadata/raw archive.

## Rebuild

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/analyze_v5_review_metrics.py
cd paper/paper_v5
./build.sh
```
