# Fusion vs Radar-Only Repeat5 Comparison

This comparison pairs the full 66-case suite run with camera-gated fusion against the radar-only run, both with `--repeat 5`, `--control-mode physics`, and `--reload-world-every 0`.

Compared run IDs:

```text
paper_v3_fusion_full66_repeat5_noreload
paper_v3_radar_only_full66_repeat5_noreload
```

CSV with per-scenario deltas:

```text
fusion_vs_radar_only_repeat5_comparison.csv
```

## Overall outcome comparison

| Metric | Fusion | Radar-only |
|---|---:|---:|
| Scenarios | 66 | 66 |
| Runs | 330 | 330 |
| PASS runs | 315 | 315 |
| FAIL runs | 15 | 15 |
| Collision runs | 15 | 15 |
| Brake activated runs | 330 | 330 |
| All-PASS scenarios | 63 | 63 |
| All-FAIL scenarios | 3 | 3 |
| Mixed-outcome scenarios | 0 | 0 |

Paired run agreement:

| Paired check | Result |
|---|---:|
| Same status | 330/330 |
| Same collision flag | 330/330 |

## Family comparison

| Family | Fusion PASS/FAIL | Radar-only PASS/FAIL | Comment |
|---|---:|---:|---|
| CCRm | 120/0 | 120/0 | Identical outcome |
| CCRb | 140/10 | 140/10 | Identical outcome |
| Cut-in | 55/5 | 55/5 | Identical outcome |

## Repeated all-FAIL scenarios

The all-FAIL set is identical in both configurations:

```text
ccrb_95_gap_20
ccrb_110_gap_20
cutin_100_60_gap_25
```

All fail runs in both configurations activated braking and matched the configured hazard target at 100% in the summary logs. This supports the existing interpretation that these are kinematic/boundary failures, not target-selection misses.

## Largest mean minimum-gap differences

Mean difference is `fusion mean - radar-only mean` for `minimum_bumper_gap_m`.

| Scenario | Status agreement | Mean min-gap delta |
|---|---:|---:|
| `cutin_80_50_gap_25` | 5/5 same | -0.741 m |
| `cutin_100_60_gap_35` | 5/5 same | -0.337 m |
| `ccrm_100_70_gap_20` | 5/5 same | +0.284 m |
| `cutin_80_50_gap_35` | 5/5 same | -0.190 m |
| `ccrb_95_gap_60` | 5/5 same | -0.160 m |
| `ccrm_110_80_gap_50` | 5/5 same | -0.109 m |
| `ccrm_100_70_gap_50` | 5/5 same | +0.102 m |
| `ccrm_60_30_gap_20` | 5/5 same | +0.094 m |
| `ccrm_100_70_gap_80` | 5/5 same | +0.069 m |
| `ccrb_110_gap_20` | 5/5 same | -0.032 m |

## Interpretation for paper v4

For the hazardous 66-case final suite, radar-only and camera-gated fusion produced the same PASS/FAIL and collision outcomes in all 330 paired repeat runs. Therefore this suite alone does **not** provide evidence that the camera gate improves safety or reduces false braking.

What this comparison does support:

- the camera gate did not change the configured hazardous-suite outcome map under this setup;
- the three stress failures remain boundary cases in both configurations;
- fusion-vs-radar claims must be based on negative/adjacent-lane regression or other cases where false positive behavior is observable.

Required next evidence before claiming camera benefit:

```text
fusion_regression.yaml repeat5
radar_only_regression.yaml repeat5
```

or another matched negative suite with clear-road, adjacent-lane, and curve scenarios.
