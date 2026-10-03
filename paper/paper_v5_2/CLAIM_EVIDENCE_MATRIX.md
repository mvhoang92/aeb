# Paper v5.2 Claim–Evidence Matrix

All v5.1 claims are retained with identical numbers; rows marked **new** were
added in v5.2.

| Claim | Evidence | Boundary |
|---|---|---|
| Three policies share upstream radar risk and staged PID | Protocol, source code, frozen campaign metadata; Fig. 1 | Comparison is policy-level; not a new detector |
| Core named-condition results are .913/.988, 1/.965 and 1/.988 | `paper_v5_derived/named_scenario_metrics.csv` | Constructed core grid, not traffic prevalence |
| Fallback passes 101/105 core conditions | `named_scenario_metrics.csv` | Five repeats are consistency checks |
| Hard gate passes 11/14 hold-out conditions; fallback 7/14 | `named_scenario_metrics.csv` | Frozen adverse mechanism hold-out, not blind deployment test |
| Camera policies suppress eight edge-prop false-brake conditions | `named_scenario_metrics.csv` and raw logs | Specific suite composition |
| Hard gate vetoes two central non-vehicle hazards that fallback recovers | Core logs and scenario summaries | Fallback still fails other physical mechanisms |
| Four persistent ghost conditions pass fallback rules | Hold-out logs and fault-injection YAML | Synthetic fault injection, not measured multipath prevalence |
| Fallback ghost brakes are full stops | `false_brake_severity_runs.csv` | Kinematic descriptor, no occupant/rear-vehicle model |
| Ghost onset/duration/deceleration are 78.4 km/h, 3.60 s, 9.02 m/s² | Derived severity CSVs | Median over the specified repeated runs |
| Bench last-tick speeds are 32.57/54.93/59.95 km/h | `collision_severity_summary.csv` | Last 0.05-s pre-impact proxy, not contact speed |
| 2,461 runs, 639 sessions, 474 CUDA sessions and 74,928 inferences | Final GPU evidence and campaign manifests | Not 2,461 independent traffic samples; not ECU real-time proof |
| Protocol prevents CPU fallback and retries only technical failures | Frozen protocol and runtime metadata | Policy failures are retained as evidence |
| **new** Exact two-sided McNemar p on named-condition paired PASS: core radar/hard 2 vs 8, p=0.1094; radar/fallback 0 vs 8, p=0.0078; hard/fallback 0 vs 2, p=0.5000; hold-out radar/hard 0 vs 5, p=0.0625; radar/fallback 0 vs 1, p=1.0000; hard/fallback 4 vs 0, p=0.1250 | `paper_v5_2_derived/paired_exact_mcnemar.{csv,json}` from `scripts/analysis/analyze_v52_paired_tests.py` (counts cross-checked against `named_paired_outcomes.csv` and `paper_v4_gpu_final/scenario_consistency.csv`) | Descriptive on a constructed, non-random grid; no multiplicity adjustment; no population inference; repeats never counted as pairs |
| **new** Only the core radar/fallback discordance reaches p<0.05 | Same | Small discordant counts (≤10); exact conditional test is conservative |
| **new** Fig. 2(a): fallback grants emergency permission at 0.15 s on the 6-point ghost and stops below 1 km/h | `paper_v5_2_derived/figures/timeseries_selected_runs.csv` (from the SHA-verified raw archive) | One representative run; 15 of 20 fallback ghost runs share the median descriptors |
| **new** Fig. 2(b): hard gate vetoes the radar request on the bench until impact; last-tick speed 59.95 km/h | Same; matches `collision_severity_runs.csv` | One representative run; all five runs share the median pre-impact speed |
| **new** Related-work positioning against standards (ISO 15623/22839, UN R152, Euro NCAP), SOTIF, learned radar–camera detectors, scenario-based assessment and AV fault injection | `references.bib` (verified entries) | Protocol-inspired cases are not compliance or certification evidence |
| v5.2 is empirically differentiated from nearby work | Related-work citations and explicit positioning sentence | No claim of first camera gate, first probabilistic AEB or first ghost study |

## Negative claims intentionally retained

- No general fusion dominance claim.
- No claim that tracker confidence is physical-existence probability.
- No claim of road prevalence, real vehicle, HIL, ECU deadline, Euro NCAP,
  UN R152, ISO or functional-safety/SOTIF compliance.
- McNemar p-values are not presented as population inference or as evidence
  that one policy is generally safer.
- No claim that refactoring or later launcher work is scientific evidence.
