# Paper v5.1 Claim–Evidence Matrix

| Claim | Evidence | Boundary |
|---|---|---|
| Three policies share upstream radar risk and staged PID | Protocol, source code and frozen campaign metadata | Comparison is policy-level; not a new detector |
| Core named-condition results are .913/.988, 1/.965 and 1/.988 | `named_scenario_metrics.csv` | Constructed core grid, not traffic prevalence |
| Fallback passes 101/105 core conditions | `named_scenario_metrics.csv` | Five repeats are consistency checks |
| Hard gate passes 11/14 hold-out conditions; fallback 7/14 | `named_scenario_metrics.csv` | Frozen adverse mechanism hold-out, not blind deployment test |
| Camera policies suppress eight edge-prop false-brake conditions | `named_scenario_metrics.csv` and raw logs | Specific suite composition |
| Hard gate vetoes two central non-vehicle hazards that fallback recovers | Core logs and scenario summaries | Fallback still fails other physical mechanisms |
| Four persistent ghost conditions pass fallback rules | Hold-out logs and fault-injection YAML | Synthetic fault injection, not measured multipath prevalence |
| Fallback ghost brakes are full stops | `false_brake_severity_runs.csv` | Kinematic simulation descriptor, no occupant/rear-vehicle model |
| Ghost onset/duration/deceleration are 78.4 km/h, 3.60 s, 9.02 m/s² | Derived severity CSVs | Median over the specified repeated runs |
| Bench last-tick speeds are 32.57/54.93/59.95 km/h | `collision_severity_summary.csv` | Last 0.05-s pre-impact proxy, not contact speed |
| 2,461 runs, 639 sessions, 474 CUDA sessions and 74,928 inferences | Final GPU evidence and campaign manifests | Not 2,461 independent traffic samples; not ECU real-time proof |
| Protocol prevents CPU fallback and retries only technical failures | Frozen protocol and runtime metadata | Policy failures are retained as evidence |
| v5.1 is empirically differentiated from nearby work | Related-work citations and explicit scope paragraph | No claim of first camera gate, first probabilistic AEB or first ghost study |

## Negative claims intentionally retained

- No general fusion dominance claim.
- No claim that tracker confidence is physical-existence probability.
- No claim of road prevalence, real vehicle, HIL, ECU deadline, Euro NCAP or
  functional safety.
- No claim that refactoring or later launcher work is scientific evidence.
