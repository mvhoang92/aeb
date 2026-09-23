# Current System Architecture

## Decision flow

```text
CARLA camera/radar
       │
       ├─ perception/radar tracker ─→ RadarObject/target
       └─ YOLO detector ────────────→ camera evidence
                                      │
RadarAEBPipeline ─→ provisional AEBDecision
                                      │
                           BrakePermissionPolicy
                                      │
                              final AEBDecision
                                      │
                  BinaryAEB/staged-PID + actuation
                                      │
                         telemetry/scoring/summary
```

## Module ownership

- `perception/`: sensor measurement processing and tracking.
- `core/radar_aeb_pipeline.py`: target/risk orchestration and provisional decision.
- `core/brake_permission_policy.py`: radar-only, hard gate and fallback contract.
- `core/fusion_brake_gate.py`: frozen camera gate/fallback mechanism.
- `core/headless_aeb_runtime.py`: pipeline → policy → actuation tick order.
- `control/`: TTC/stopping risk, state machine, brake command and vehicle control.
- `evaluation/`: frozen output schema, scoring, severity and artifact writing.
- `scripts/run_*`: CARLA lifecycle and stable CLI, not reusable algorithm logic.

Dependencies point from entry points toward domain modules, never from control or
evaluation back into scenario scripts. Historical wrappers may delegate but must
preserve CLI, exit code and public imports.

## Stability boundary

Threshold/config changes are algorithm changes, not refactors. Frozen tags and
paper evidence remain the reference implementation. Structural changes require
golden tests and CARLA smoke but not an automatic rerun of 2,461 runs.
