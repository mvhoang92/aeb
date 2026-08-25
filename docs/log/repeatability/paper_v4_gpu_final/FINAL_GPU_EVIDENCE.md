# Paper v4 final GPU evidence

Campaign: `paper_v4_gpu_final_locked_20260825`  
Frozen commit: `recorded per runtime session`  
Status: **completed**, 47 jobs and 639 isolated scenario sessions.

## Core benchmark (synthetic faults excluded)

| Policy | TP | FP | TN | FN | Precision | Recall | Collision |
|---|---:|---:|---:|---:|---:|---:|---:|
| Radar-only | 420 | 40 | 60 | 5 | 0.913 | 0.988 | 15 |
| Hard camera gate | 410 | 0 | 100 | 15 | 1.000 | 0.965 | 25 |
| Safe fallback | 420 | 0 | 100 | 5 | 1.000 | 0.988 | 15 |

The frozen core benchmark reproduces the intended trade-off. Safe fallback matched radar-only recall (0.988) and hard-gate precision (1.000) on this constructed suite, while reducing hard-gate collisions from 25 to 15. This is a benchmark-specific result, not a prevalence-weighted road estimate.

## Core including labelled synthetic fault injection

| Policy | TP | FP | TN | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| Radar-only | 420 | 70 | 60 | 5 | 0.857 | 0.988 |
| Hard camera gate | 410 | 0 | 130 | 15 | 1.000 | 0.965 |
| Safe fallback | 420 | 0 | 130 | 5 | 1.000 | 0.988 |

## Frozen hold-out

| Policy | PASS | FAIL | TP | FP | TN | FN | Precision | Recall | Collision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Radar-only | 30 | 40 | 30 | 25 | 10 | 5 | 0.545 | 0.857 | 15 |
| Hard camera gate | 55 | 15 | 25 | 0 | 35 | 10 | 1.000 | 0.714 | 15 |
| Safe fallback | 35 | 35 | 30 | 20 | 15 | 5 | 0.600 | 0.857 | 15 |

Safe fallback did not dominate the hard gate on hold-out: four high-support central synthetic ghosts produced 20/25 false-brake runs, while the 0.75 m-offset ghost was blocked. All three policies failed the three unseen central physical-prop scenarios (15 collisions each): the cart generated no confirmed radar cluster, and the bench/warning cases triggered too late to avoid impact. These outcomes were retained without retuning.

## CUDA processing evidence

- 474 CUDA sessions, 74928 inferences and 0 inference errors.
- Session-median p50/p95: 9.95/11.53 ms; weighted mean 11.56 ms.
- Maximum 276.10 ms; exactly 474 >150 ms cold-start events across 474 isolated sessions.
- Timing is host wall-clock processing evidence, not proof of a real-vehicle real-time deadline.

## Interpretation safeguards

- Repeats measure consistency; named scenarios are the scenario-level unit.
- Core/hold-out class ratios were designed, so aggregate precision/F1 are composition-dependent.
- Synthetic returns are explicit fault injection, not native CARLA radar ghosts.
- Euro NCAP compliance, real-vehicle validation and functional-safety certification are not claimed.
