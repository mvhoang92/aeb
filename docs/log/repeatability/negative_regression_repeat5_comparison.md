# Negative Regression Repeat5 Comparison

This note summarizes the repeat5 regression runs used to check unnecessary braking and compare camera-gated fusion with radar-only behavior.

## Run IDs

```text
paper_v3_fusion_regression_repeat5_noreload
paper_v3_radar_only_regression_repeat5_noreload
paper_v3_fusion_on_radar_regression_repeat5_noreload
```

The first two use the project-specific regression suites:

```text
configs/scenarios/suites/fusion_regression.yaml
configs/scenarios/suites/radar_only_regression.yaml
```

The third run executes `radar_only_regression.yaml` with the fusion runner, giving a direct paired comparison against radar-only on the same scenario IDs.

## Summary

| Run | Scenarios | Runs | PASS | FAIL | Negative runs | False brake | Positive runs | Missed brake | Mixed scenarios |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Fusion regression suite | 25 | 125 | 125 | 0 | 35 | 0 | 90 | 0 | none |
| Radar-only regression suite | 29 | 145 | 141 | 4 | 60 | 0 | 85 | 4 | `cut_out_late_65_35` |
| Fusion on radar regression suite | 29 | 145 | 140 | 5 | 60 | 0 | 85 | 5 | none; `cut_out_late_65_35` all-FAIL |

## False-brake result

Across the negative subsets:

| Configuration | Negative runs | False-brake runs | False-brake rate |
|---|---:|---:|---:|
| Fusion regression suite | 35 | 0 | 0.0% |
| Radar-only regression suite | 60 | 0 | 0.0% |
| Fusion on radar regression suite | 60 | 0 | 0.0% |

This means the current negative suites do not show a false-brake advantage for the camera gate: both radar-only and fusion avoid braking in the tested clear-road, adjacent-lane, curve, non-closing, and cut-out-negative cases.

## Paired comparison on `radar_only_regression.yaml`

Fusion and radar-only were paired on 145 `(scenario_id, run_index)` rows from `radar_only_regression.yaml`.

| Paired check | Result |
|---|---:|
| Same status | 144/145 |
| Same brake flag | 144/145 |

The only paired difference:

| Scenario | Run | Fusion | Radar-only | Note |
|---|---:|---|---|---|
| `cut_out_late_65_35` | 5 | FAIL, brake=False, min_gap=-20.804 m | PASS, brake=True, min_gap=14.858 m | Positive case expected to brake; fusion did not improve it. |

## Interpretation for paper v4

Supported statements:

- The regression suites produced no false-brake runs in the tested negative cases.
- On the same radar regression suite, camera-gated fusion and radar-only were nearly identical, except one positive cut-out-late run where radar-only braked and fusion did not.
- The current evidence still does not support a broad claim that camera gating reduces false braking, because radar-only already has zero false-brake runs on these negative cases.

Unsuitable claims:

- Do not claim camera gate improves safety or reduces false braking from these results.
- Do not claim fusion is superior to radar-only on the regression suite; if anything, `cut_out_late_65_35` suggests the camera gate can block a required brake in a late cut-out edge case.

Recommended next step:

- Inspect `cut_out_late_65_35` logs/video to decide whether the scenario label `expected_brake=True` is appropriate or whether the camera gate is too conservative for late cut-out geometry.
- If claiming camera benefit is still desired, design harder radar false-positive cases where radar-only actually brakes unnecessarily and fusion can suppress it.
