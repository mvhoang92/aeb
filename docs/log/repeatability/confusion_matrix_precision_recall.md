# Precision/recall trade-off of camera gating (headline results)

This page aggregates all paired radar-only vs fusion runs into a single
confusion matrix at the brake-decision level. It is the headline quantitative
result for the camera-gating contribution.

## Definition

A run is a hazard if `expected_brake=true`, otherwise a non-hazard. The brake
decision is the run-level `brake_activated` flag.

| Cell | Meaning |
|---|---|
| TP | braked on a hazard |
| FN | did not brake on a hazard |
| FP | braked on a non-hazard (false brake) |
| TN | did not brake on a non-hazard |

## Source suites (all paired, repeat x5)

| Suite | hazard runs | non-hazard runs |
|---|---:|---:|
| `system_limit_extended_sweep` (full66) | 330 | 0 |
| `radar_only_regression` (negative regression) | 85 | 60 |
| `fusion_physical_false_positive_v2` | 0 | 40 |
| `fusion_nonvehicle_hazard_limitation` | 10 | 0 |

## Confusion matrix

| Config | TP | FP | TN | FN | Precision | Recall | F1 | FP-rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Radar-only | 421 | 40 | 60 | 4 | 0.913 | 0.991 | 0.950 | 0.400 |
| Camera-gated fusion | 410 | 0 | 100 | 15 | 1.000 | 0.965 | 0.982 | 0.000 |

Per-suite breakdown is in `confusion_matrix_by_suite.csv`.

## Reading

- **Fusion achieves perfect precision (1.000)**: it never braked on a
  non-hazard run, removing all 40 radar-only false brakes.
- **Radar-only has higher recall (0.991 vs 0.965)**: it missed only the
  borderline `cut_out_late_65_35` (4/5), while fusion additionally missed the 10
  non-vehicle in-path hazards (car-only gate limitation).
- **F1**: fusion 0.982 vs radar-only 0.950 in this aggregate.

## Caveats to state in the paper

1. The 40 radar-only false positives come from a deliberate physical
   false-positive stress suite (static props near the ego path). On the
   realistic negative regression subset, radar-only also had 0 false brakes.
2. The 10 fusion false negatives are the documented car-only detection
   limitation (non-vehicle obstacles directly in the path).
3. The aggregate mixes suites with different priors, so precision/recall are
   relative to this specific labelled set, not a real-world rate.

## Brake-onset latency (fusion vs radar-only, full66)

| Metric | Value |
|---|---:|
| Mean first-brake difference (fusion − radar) | +4.5 ms |
| Median difference | 0.0 ms |
| Max absolute difference | 250 ms (one cut-in case) |

Conclusion: the camera gate adds negligible brake-onset latency on confirmed
car targets (median 0 ms, mean +4.5 ms), so its precision gain does not come at
a latency cost for ordinary vehicle hazards.
