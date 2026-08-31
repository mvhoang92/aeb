# Project Structure

This document is the maintainer-facing map of the AEB repository. Historical
reports and evidence remain authoritative for reported experiments; this map
only describes the live source tree.

## Runtime layers

| Layer | Location | Responsibility |
|---|---|---|
| Entry points | `launcher.py`, `laucher.py`, `ui/`, `scripts/` | Desktop launcher, interactive views and command-line jobs |
| Scenario runtime | `scripts/run_*_aeb_scenarios.py` | CARLA actor lifecycle, simulation loop and compatibility CLIs |
| Runtime composition | `core/headless_aeb_runtime.py` | Shared radar pipeline → permission policy → actuation order |
| Evaluation | `evaluation/` | Frozen schemas, scoring, telemetry, severity and summary output |
| Policy | `core/brake_permission_policy.py` | Radar-only, hard camera gate and emergency-fallback permission |
| AEB pipeline | `core/radar_aeb_pipeline.py` | Radar tracking, target selection and provisional AEB decision |
| Fusion gate | `core/fusion_brake_gate.py` | Frozen hard-gate/fallback decision logic |
| Perception | `perception/`, `core/radar_object.py` | Radar clustering/tracking and object representation |
| Control | `control/` | Risk model, staged/PID command, state machine and actuation; `brake.py` is the compatibility facade |
| Script jobs | `scripts/{campaign,analysis,dataset,training,maintenance}/` | Categorized implementations behind historical root wrappers |
| Configuration | `configs/` | Sensor, scenario, evaluation, dataset and training configuration |
| Workspace infrastructure | `infrastructure/workspace.py` | Explicit legacy-to-external artifact path mapping |
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

Source/config/model paths continue to resolve from the repository/CARLA root.
Known historical dataset/log/output/training paths resolve through
`AEB_WORKSPACE_ROOT` when the repository-local path does not exist. Refactoring
must preserve existing CLI defaults and YAML keys.

## Evidence and manuscripts

- `docs/log/repeatability/paper_v4_gpu_final/`: final CUDA evidence summaries.
- `docs/log/repeatability/paper_v5_derived/`: scenario-level/severity derivation.
- `docs/log/repeatability/artifacts/`: archived raw evidence and checksums.
- `paper/paper_v1/` through `paper/paper_v5/`: immutable paper generations.
- `report/chapters_v3/`, `report/report_v3.md`, `report/exports/`: report v3.
- `$AEB_WORKSPACE_ROOT/runs/`: machine-local logs, campaigns and generated review products.

The tags `baseline-hard-camera-gate-v1`, `safe-fallback-eval-v1`,
`paper-v4-final-gpu-evidence-v1`, `paper-v5-scenario-severity-v1` and
`pre-refactor-project-v1` preserve historical states. Do not move or rewrite
them.

## Large local data

Dataset generations, training runs, logs and outputs live in the sibling local
workspace and are not source modules. The migration preserved all 46,099 files
and verified SHA-256 at the destination. Local environments remain
machine-specific. See `docs/ARTIFACT_POLICY.md` and
`docs/maintenance/WORKSPACE_MIGRATION_MANIFEST.md`.

## Supported compatibility entry points

```bash
/usr/bin/python3 launcher.py
/usr/bin/python3 laucher.py          # historical spelling, retained wrapper
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_radar_aeb_scenarios.py --help
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py --help
```

The script names, options, output field names and exit-code semantics are part
of the compatibility surface until a separately reviewed migration changes
them. See `scripts/README.md` for the categorized implementation map and
`docs/log/refactor/REFACTOR_V1_VALIDATION.md` for refactor regression evidence.
