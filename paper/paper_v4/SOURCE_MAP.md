# Paper v4 Source Map

## Manuscripts

- English source/PDF: `aeb_ieee_6page.tex`, `aeb_ieee_6page.pdf`
- Vietnamese review source/PDF: `aeb_ieee_6page_vi.tex`, `aeb_ieee_6page_vi.pdf`
- Bibliography: `references.bib`
- Build gate: `build.sh` (English PDF must be exactly six pages)

## Algorithm

- Radar emergency gate: `../../core/fusion_brake_gate.py`
- Radar object/risk pipeline: `../../core/radar_aeb_pipeline.py`
- Brake controller: `../../control/brake.py`
- Fusion scenario runner: `../../scripts/run_fusion_aeb_scenarios.py`
- Final orchestration: `../../scripts/run_v4_final_pipeline.py`

## Frozen configuration and protocol

- Tag: `safe-fallback-eval-v1`
- Protocol: `../../docs/log/PAPER_V4_EVALUATION_PROTOCOL.md`
- Hard gate GPU config: `../../configs/sensors_fusion_hard_batch_gpu.yaml`
- Fallback GPU config: `../../configs/sensors_fusion_safe_fallback_batch_gpu.yaml`
- Variant specification: `../../configs/evaluation/paper_v4_experiments.yaml`
- Development/perturbation/degradation/hold-out YAML: `../../configs/scenarios/suites/fusion_*.yaml`

## Final evidence

- Narrative and generated CSV: `../../docs/log/repeatability/paper_v4_gpu_final/`
- Reproducible analysis: `../../scripts/analyze_v4_final.py`
- Raw archive and SHA-256: `../../docs/log/repeatability/artifacts/paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz*`
- Figure source: `figures/`

## Rebuild

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/analyze_v4_final.py
cd paper/paper_v4
./build.sh
```
