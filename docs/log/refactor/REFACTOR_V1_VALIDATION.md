# Project Structure Refactor v1 — Validation Evidence

## Scope

Structural refactor on `refactor/project-structure-v1`; no threshold, scenario,
config-schema or algorithm tuning. Frozen evidence, papers, reports and tags
were not modified. The full 2,461-run paper campaign was intentionally not
rerun because no algorithm behavior changed.

## Static and golden gates

At the final validation checkpoint:

- 89 unit/golden tests: PASS.
- Paper v4/report v3 claim validator: PASS.
- Paper v5 scenario/severity/bilingual validator: PASS.
- `compileall` for control/core/evaluation/perception/scripts/tests/ui: PASS.
- Historical radar/fusion `--help` output: unchanged.
- Canonical and historical launcher `--check`: identical, 7/7 prerequisites OK,
  66 scenarios found.
- Ordered telemetry schemas: 57 tick fields and 41 summary fields unchanged.
- Fourteen extracted evaluation helper ASTs matched `pre-refactor-project-v1`.
- Golden PASS/FAIL scoring and severity output matched the pre-refactor function.
- Config parsing, actuation and 3,500 sequential controller decisions across
  binary, staged, PID variants and staged-PID matched `pre-refactor-project-v1`.
- `git diff --check`: PASS.

## CARLA/CUDA smoke

Smoke runs used CARLA 0.9.11, Town04, fixed 0.05 s simulation steps, physics
control and seed 2026. Metadata records clean commit
`ac1e9b4c237d28944117ec6a6f04134f06c5db2e`.

| Policy | Named condition | Result | Key policy evidence |
|---|---|---|---|
| Radar-only | `ccrs_30` | PASS; brake; no collision; 7.75 m minimum gap | Historical radar CLI and pass-through policy |
| Hard camera gate | `limit_ccrs_40_gap_40` | PASS; brake; no collision; 7.54 m minimum gap | `camera_confirmed`; 27 inferences; 0 errors |
| Emergency fallback | `dev_box_in_path` | PASS; brake; no collision; 0.85 m minimum gap | fallback + hold actions; 49 fallback ticks; 19 inferences; 0 errors |

Both fusion runs configured and required `CUDAExecutionProvider`. Runtime
reported CUDA active (along with ONNX Runtime's CPU fallback provider), and the
required-provider check passed. There were no inference errors.

Local run directories (not paper evidence):

- `$AEB_WORKSPACE_ROOT/runs/logs/refactor_v1_smoke_radar_only_20260825/`
- `$AEB_WORKSPACE_ROOT/runs/logs/refactor_v1_smoke_hard_gate_cuda_20260825/`
- `$AEB_WORKSPACE_ROOT/runs/logs/refactor_v1_smoke_fallback_cuda_20260825/`

SHA-256:

```text
f47bd700e81cde89304740fea1d4e3012b58b37ca87faa6df3b9490d881736de  radar summary.json
71e3683408a932c58ddd542daa046c2e7886e5b763a97e8a3f4e7d6aad049626  radar run_metadata.json
cb7cd4a11b6164503eb593d49e12b14b80e3af1b1da2701a9dce58b2c200b1f9  hard-gate summary.json
38030baee543e41ed2b8b0187f6fe0a0114bce69319cc6f5ccde39e9fc24ba73  hard-gate run_metadata.json
a2725c6c9a99e4d44c230aa458012a5d93a73cbe04c803c8cab8a6a2d2a58afd  fallback summary.json
c866cde6e8d15ef53bf09ec55b6cb7439ec0eb2283fe03d03ece09fcb3b2c3b4  fallback run_metadata.json
```

These runs validate refactor compatibility only; they do not replace or extend
the frozen scientific campaign.
