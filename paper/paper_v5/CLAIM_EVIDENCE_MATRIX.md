# Paper v5 Claim–Evidence Matrix

| Claim | Evidence | Interpretation boundary |
|---|---|---|
| Core primary unit is 105 named conditions/policy | `docs/log/repeatability/paper_v5_derived/named_scenario_metrics.csv` | Each condition has five deterministic consistency repeats |
| Core radar/hard/fallback P/R = .913/.988, 1.000/.965, 1.000/.988 | Same CSV | Scenario-level finite-grid metrics; not road prevalence |
| Core PASS = 93/105, 99/105, 101/105 | Same CSV | PASS includes brake, collision, minimum-gap and configured assertions |
| Core collision conditions = 3/5/3 | Same CSV and `collision_severity_summary.csv` | Correspond to 15/25/15 repeated collision runs |
| Hold-out PASS = 6/14, 11/14, 7/14 | Same CSV | Frozen adverse mechanism hold-out, not deployment distribution |
| Hold-out fallback P/R = .600/.857 | Same CSV | Four of five negative ghost conditions trigger fallback |
| Hard vs fallback hold-out paired = 7 both pass, 4 hard-only, 0 fallback-only, 3 both fail | `named_paired_outcomes.csv` | Named-condition pairing |
| Fallback ghost FP: 20/20 runs stop below 1 km/h | `false_brake_severity_runs.csv` | Explicit synthetic fault injection |
| Ghost FP median onset/duration/deceleration = 78.4 km/h / 3.60 s / 9.02 m/s² | `false_brake_severity_summary.csv` | CARLA dynamics; not occupant or following-vehicle risk |
| Bench last-tick pre-impact speed radar/hard/fallback = 32.57/59.95/54.93 km/h | `collision_severity_summary.csv` | Last 0.05-s tick before first collision event |
| Cart has no brake and 49.96 km/h pre-impact under all policies | Same CSV and raw tick logs | Missing confirmed radar cluster occurs before policy gate |
| Warning first brake 21.87 m and pre-impact 7.82 km/h under all policies | Same CSV | Collision count hides mitigation |
| Perturbation PASS = 19/20, 15/20, 18/20; fallback has one collision condition | `named_scenario_metrics.csv` | Its second FAIL is 0.353-m gap, not collision |
| Camera-off PASS hard/fallback = 4/10, 8/10 | Same CSV | Hard PASS cases are all true negatives |
| Dataset = 1505/300/200 images, 28/6/4 sessions | `training_runs/dataset_audit_v7_same_lane.json` | All splits remain Town04 in-domain |
| Model hash prefix `dc0a6ca1754a` | `models/yolo26n_aeb_v7.onnx`; frozen metadata/archive | Full SHA-256 stored in runtime metadata |
| 474 CUDA sessions, 74,928 inferences, zero errors | v4 `gpu_latency.csv` and raw runtime sessions | ONNX host processing, not end-to-end ECU timing |
| Campaign = 2,461 runs, 639 sessions | Frozen campaign manifest/raw archive | Coverage and consistency, not independent sample size |

No v5 claim implies radar-fault prevalence, road-safety performance, Euro NCAP
compliance, functional-safety certification, real-time ECU validation or
real-vehicle validation.
