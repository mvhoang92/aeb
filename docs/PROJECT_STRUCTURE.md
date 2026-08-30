# Project Structure

This document is the maintainer-facing map of the AEB repository. Historical
reports and evidence remain authoritative for reported experiments; this map
only describes the live source tree.

## Runtime layers

| Layer | Location | Responsibility |
|---|---|---|
| Entry points | `launcher.py`, `laucher.py`, `ui/`, `scripts/` | Desktop launcher, interactive views and command-line jobs |
| Scenario runtime | `scripts/run_*_aeb_scenarios.py` | CARLA actor lifecycle, simulation loop and compatibility CLIs |
| Evaluation | `evaluation/` (refactor target) | Scoring, telemetry schema, severity metrics and summary output |
| Policy | `core/brake_permission_policy.py` (refactor target) | Radar-only, hard camera gate and emergency-fallback permission |
| AEB pipeline | `core/radar_aeb_pipeline.py` | Radar tracking, target selection and provisional AEB decision |
| Fusion gate | `core/fusion_brake_gate.py` | Frozen hard-gate/fallback decision logic |
| Perception | `perception/`, `core/radar_object.py` | Radar clustering/tracking and object representation |
| Control | `control/brake.py` | Frozen controller facade; risk/controller/state helpers are refactor targets |
| Configuration | `configs/` | Sensor, scenario, evaluation, dataset and training configuration |
| Verification | `tests/`, validation scripts | Unit, schema, manuscript and campaign checks |

Dependencies should point downward. UI and scenario scripts may orchestrate core,
perception, control and evaluation code; reusable logic must not move back into
an entry-point script.

## Configuration

- `configs/sensors*.yaml`: runtime sensor, detector, fusion and brake settings.
- `configs/scenarios/car_to_car/`: reusable scenario definitions.
- `configs/scenarios/suites/`: named evaluation suites.
- `configs/evaluation/`: frozen campaign matrices.
- `configs/legacy/`: retained compatibility inputs; do not silently reinterpret.
- Dataset and training YAML files are independent of runtime evaluation.

Relative paths continue to resolve from the repository root. Refactoring must
preserve existing CLI defaults and YAML keys.

## Evidence and manuscripts

- `docs/log/repeatability/paper_v4_gpu_final/`: final CUDA evidence summaries.
- `docs/log/repeatability/paper_v5_derived/`: scenario-level/severity derivation.
- `docs/log/repeatability/artifacts/`: archived raw evidence and checksums.
- `paper/paper_v1/` through `paper/paper_v5/`: immutable paper generations.
- `report/chapters_v3/`, `report/report_v3.md`, `report/exports/`: report v3.
- `logs/` and `outputs/`: local runtime products, mostly ignored by Git.

The tags `baseline-hard-camera-gate-v1`, `safe-fallback-eval-v1`,
`paper-v4-final-gpu-evidence-v1`, `paper-v5-scenario-severity-v1` and
`pre-refactor-project-v1` preserve historical states. Do not move or rewrite
them.

## Large local data

Dataset generations, training runs, logs, outputs and local environments are
intentionally kept in place but are not source modules. They must never be
moved or deleted as a side effect of structural refactoring. See
`docs/ARTIFACT_POLICY.md`.

## Supported compatibility entry points

```bash
/usr/bin/python3 launcher.py
/usr/bin/python3 laucher.py          # historical spelling, retained wrapper
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_radar_aeb_scenarios.py --help
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py --help
```

The script names, options, output field names and exit-code semantics are part
of the compatibility surface until a separately reviewed migration changes
them.
