# Paper V3 Fusion Regression Repeat5 Noreload Summary

This file is a lightweight, git-tracked derived summary generated from local logs. Raw per-tick CSV logs are archived under `docs/log/repeatability/artifacts/`.

Generation command:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/summarize_repeatability.py \
  logs/paper_v3_fusion_regression_repeat5_noreload \
  --output-dir outputs/paper_v3_reproduction/repeatability/paper_v3_fusion_regression_repeat5_noreload
```

Run directory: `logs/paper_v3_fusion_regression_repeat5_noreload`

## Overall

| Metric | Value |
|---|---:|
| Scenarios | 25 |
| Runs | 125 |
| PASS runs | 125 |
| FAIL runs | 0 |
| Collision runs | 0 |
| Brake activated runs | 90 |
| All-PASS scenarios | 25 |
| All-FAIL scenarios | 0 |
| Mixed-outcome scenarios | 0 |

## By family

| Family | Runs | PASS | FAIL | Collision | Brake |
|---|---:|---:|---:|---:|---:|
| braking | 15 | 15 | 0 | 0 | 15 |
| false | 35 | 35 | 0 | 0 | 0 |
| limit | 35 | 35 | 0 | 0 | 35 |
| moving | 10 | 10 | 0 | 0 | 10 |
| short | 30 | 30 | 0 | 0 | 30 |

## Scenario outcomes

| Scenario | Runs | PASS | FAIL | Collision | Brake | First brake mean/std (s) | Brake gap mean/std (m) | Min gap mean/std (m) | Min gap min/max (m) | Hazard match mean (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `braking_65_gap_28` | 5 | 5 | 0 | 0 | 5 | 2.500/0.000 | 23.122/0.004 | 6.025/0.003 | 6.023/6.030 | 100.0 |
| `braking_80_gap_40` | 5 | 5 | 0 | 0 | 5 | 2.710/0.020 | 32.519/0.258 | 7.137/0.247 | 6.642/7.267 | 100.0 |
| `braking_90_gap_55` | 5 | 5 | 0 | 0 | 5 | 3.000/0.000 | 42.862/0.021 | 8.759/0.011 | 8.748/8.773 | 100.0 |
| `false_adjacent_90` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `false_clear_90` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `false_curve_adjacent_65` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `false_curve_adjacent_70` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `false_curve_adjacent_75` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `false_curve_adjacent_80` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `false_curve_clear_90` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `limit_ccrs_100_gap_105` | 5 | 5 | 0 | 0 | 5 | 1.700/0.000 | 58.098/0.000 | 10.058/0.003 | 10.051/10.060 | 100.0 |
| `limit_ccrs_40_gap_40` | 5 | 5 | 0 | 0 | 5 | 2.150/0.000 | 16.402/0.000 | 7.540/0.000 | 7.540/7.541 | 100.0 |
| `limit_ccrs_50_gap_45` | 5 | 5 | 0 | 0 | 5 | 1.800/0.000 | 20.295/0.000 | 6.150/0.002 | 6.145/6.152 | 100.0 |
| `limit_ccrs_60_gap_55` | 5 | 5 | 0 | 0 | 5 | 1.800/0.000 | 25.299/0.000 | 5.401/0.040 | 5.375/5.481 | 100.0 |
| `limit_ccrs_70_gap_65` | 5 | 5 | 0 | 0 | 5 | 1.700/0.000 | 32.247/0.000 | 5.964/0.006 | 5.957/5.969 | 100.0 |
| `limit_ccrs_80_gap_75` | 5 | 5 | 0 | 0 | 5 | 1.600/0.000 | 39.752/0.000 | 6.713/0.000 | 6.712/6.713 | 100.0 |
| `limit_ccrs_90_gap_90` | 5 | 5 | 0 | 0 | 5 | 1.700/0.000 | 47.814/0.000 | 8.302/0.001 | 8.301/8.303 | 100.0 |
| `moving_80_50_gap_35` | 5 | 5 | 0 | 0 | 5 | 1.350/0.000 | 23.981/0.017 | 15.731/0.009 | 15.726/15.749 | 100.0 |
| `moving_90_60_gap_45` | 5 | 5 | 0 | 0 | 5 | 2.350/0.000 | 25.653/0.017 | 20.662/0.012 | 20.647/20.681 | 100.0 |
| `short_gap_60_25` | 5 | 5 | 0 | 0 | 5 | 0.200/0.000 | 21.952/0.000 | 3.771/0.000 | 3.771/3.771 | 100.0 |
| `short_gap_60_30` | 5 | 5 | 0 | 0 | 5 | 0.350/0.000 | 24.453/0.000 | 5.419/0.000 | 5.419/5.419 | 100.0 |
| `short_gap_80_35` | 5 | 5 | 0 | 0 | 5 | 0.200/0.000 | 30.845/0.000 | 1.285/0.000 | 1.285/1.285 | 100.0 |
| `short_gap_80_45` | 5 | 5 | 0 | 0 | 5 | 0.350/0.000 | 37.513/0.000 | 3.681/0.000 | 3.681/3.681 | 100.0 |
| `short_gap_90_55` | 5 | 5 | 0 | 0 | 5 | 0.380/0.024 | 45.794/0.612 | 3.703/0.004 | 3.700/3.708 | 100.0 |
| `short_gap_90_65` | 5 | 5 | 0 | 0 | 5 | 0.650/0.000 | 49.048/0.000 | 3.845/0.000 | 3.845/3.845 | 100.0 |

## Largest minimum-gap variation

| Scenario | Mean min gap | Std | Range | Min | Max |
|---|---:|---:|---:|---:|---:|
| `braking_80_gap_40` | 7.137 | 0.247 | 0.625 | 6.642 | 7.267 |
| `limit_ccrs_60_gap_55` | 5.401 | 0.040 | 0.106 | 5.375 | 5.481 |
| `moving_90_60_gap_45` | 20.662 | 0.012 | 0.034 | 20.647 | 20.681 |
| `braking_90_gap_55` | 8.759 | 0.011 | 0.025 | 8.748 | 8.773 |
| `moving_80_50_gap_35` | 15.731 | 0.009 | 0.023 | 15.726 | 15.749 |
| `limit_ccrs_70_gap_65` | 5.964 | 0.006 | 0.012 | 5.957 | 5.969 |
| `short_gap_90_55` | 3.703 | 0.004 | 0.008 | 3.700 | 3.708 |
| `limit_ccrs_100_gap_105` | 10.058 | 0.003 | 0.009 | 10.051 | 10.060 |
| `braking_65_gap_28` | 6.025 | 0.003 | 0.007 | 6.023 | 6.030 |
| `limit_ccrs_50_gap_45` | 6.150 | 0.002 | 0.007 | 6.145 | 6.152 |
