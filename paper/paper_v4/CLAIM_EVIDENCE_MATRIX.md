# Claim–Evidence Matrix

Final campaign: `paper_v4_gpu_final_locked_20260825`

Frozen algorithm/protocol: `3be8ae4`, tag `safe-fallback-eval-v1`

| Claim | Evidence source | Scope/caveat |
|---|---|---|
| Core radar-only precision/recall = 0.913/0.988 | `docs/log/repeatability/paper_v4_gpu_final/core_confusion_metrics.csv` | 525 designed runs; synthetic faults excluded |
| Core hard-gate precision/recall = 1.000/0.965 | Same CSV | Wilson lower precision bound 0.991; not literal population perfection |
| Core fallback precision/recall = 1.000/0.988 | Same CSV | Benchmark-specific; not dominance |
| Core collision counts = 15/25/15 | Same CSV and raw `summary.json` | Includes system-limit and non-vehicle collisions |
| Weak four-point synthetic fault: radar 30 FP, camera policies 0 FP | `section_metrics.csv`, suite `fusion_benefit_stress` | Explicit labelled fault injection, not native CARLA ghost rate |
| Edge props: radar 40 FP; camera policies 0 FP | `section_metrics.csv`, physical v2 suite | Four prop types, offsets 1.30–1.50 m |
| Core box/barrel: radar/fallback 10/10 PASS; hard 0/10 | `section_metrics.csv`, non-vehicle suite | Only two known props at one nominal setup |
| Fallback improves 70 radar and 10 hard-gate core outcomes | `paired_outcomes.csv` | Paired system PASS, 555 core runs |
| Central path, point threshold and latch have observable ablation effects | `ablation_metrics.csv` | Focused development suite; not every rule independently proven |
| Point/stability/TTC sensitivity changes outcome | `sensitivity_metrics.csv` | Six-scenario one-factor subset; no global optimum claim |
| Perturbation outcomes 57/60, 45/60, 54/60 | `section_metrics.csv` | 20 named local perturbations ×3 |
| Camera-off hard/fallback outcomes 12/30 and 24/30 | `section_metrics.csv` | Controlled detector-disabled fault, not natural camera-failure prevalence |
| Frozen hold-out PASS = 30/70, 55/70, 35/70 | `section_metrics.csv` | 14 named designed conditions ×5 |
| Fallback hold-out precision/recall = 0.600/0.857 | Same CSV | Four high-support ghost groups create 20 FP |
| All policies collide 15/15 on three new central props | `scenario_consistency.csv` and raw summaries | Cart lacks a confirmed track; bench/warning are late/collision cases |
| 474 CUDA sessions, 74,928 inferences, zero errors | `gpu_latency.csv`, `runtime_sessions.json` in raw archive | Fusion sessions requiring CUDA only |
| Session-median p50/p95 = 9.95/11.53 ms | `gpu_latency.csv` | Wall-clock host timing, not ECU deadline |
| One >150 ms cold start per CUDA session; max 276.10 ms | Same CSV/session manifest | Retained rather than removed as outlier |
| Campaign technically complete: 2,461 runs, 639 server sessions | Campaign manifest in raw archive; `FINAL_GPU_EVIDENCE.md` | Algorithmic FAIL remains valid evidence |

No manuscript claim implies road prevalence, Euro NCAP compliance, functional-safety certification, real-time ECU validation, or real-vehicle validation.
