# Paper V3 Fusion On Radar Regression Repeat5 Noreload Summary

This file is a lightweight, git-tracked derived summary generated from local logs. Raw per-tick CSV logs are archived under `docs/log/repeatability/artifacts/`.

Generation command:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/summarize_repeatability.py \
  logs/paper_v3_fusion_on_radar_regression_repeat5_noreload \
  --output-dir outputs/paper_v3_reproduction/repeatability/paper_v3_fusion_on_radar_regression_repeat5_noreload
```

Run directory: `logs/paper_v3_fusion_on_radar_regression_repeat5_noreload`

## Overall

| Metric | Value |
|---|---:|
| Scenarios | 29 |
| Runs | 145 |
| PASS runs | 140 |
| FAIL runs | 5 |
| Collision runs | 0 |
| Brake activated runs | 80 |
| All-PASS scenarios | 28 |
| All-FAIL scenarios | 1 |
| Mixed-outcome scenarios | 0 |

## By family

| Family | Runs | PASS | FAIL | Collision | Brake |
|---|---:|---:|---:|---:|---:|
| CCRb | 15 | 15 | 0 | 0 | 15 |
| CCRm | 15 | 15 | 0 | 0 | 15 |
| CCRs | 25 | 25 | 0 | 0 | 25 |
| adjacent | 15 | 15 | 0 | 0 | 0 |
| clear | 15 | 15 | 0 | 0 | 0 |
| curve | 20 | 20 | 0 | 0 | 5 |
| cut | 25 | 20 | 5 | 0 | 10 |
| multi | 10 | 10 | 0 | 0 | 10 |
| non | 5 | 5 | 0 | 0 | 0 |

## Scenario outcomes

| Scenario | Runs | PASS | FAIL | Collision | Brake | First brake mean/std (s) | Brake gap mean/std (m) | Min gap mean/std (m) | Min gap min/max (m) | Hazard match mean (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `adjacent_stationary_50` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `adjacent_stationary_65` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `adjacent_stationary_80` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `ccrb_50_to_0` | 5 | 5 | 0 | 0 | 5 | 2.800/0.000 | 19.502/0.020 | 6.964/0.030 | 6.927/6.989 | 100.0 |
| `ccrb_65_to_0` | 5 | 5 | 0 | 0 | 5 | 2.900/0.000 | 27.620/0.001 | 7.323/0.005 | 7.318/7.330 | 100.0 |
| `ccrb_80_to_0` | 5 | 5 | 0 | 0 | 5 | 3.000/0.000 | 37.575/0.000 | 8.456/0.002 | 8.453/8.457 | 100.0 |
| `ccrm_50_20` | 5 | 5 | 0 | 0 | 5 | 2.700/0.000 | 17.272/0.001 | 12.402/0.002 | 12.399/12.404 | 100.0 |
| `ccrm_65_30` | 5 | 5 | 0 | 0 | 5 | 2.750/0.000 | 23.021/0.015 | 15.538/0.010 | 15.531/15.559 | 100.0 |
| `ccrm_80_50` | 5 | 5 | 0 | 0 | 5 | 3.650/0.000 | 24.227/0.003 | 18.174/0.002 | 18.173/18.179 | 100.0 |
| `ccrs_50` | 5 | 5 | 0 | 0 | 5 | 1.750/0.000 | 20.491/0.000 | 6.270/0.034 | 6.249/6.338 | 100.0 |
| `ccrs_60_demo_150` | 5 | 5 | 0 | 0 | 5 | 7.500/0.000 | 25.325/0.001 | 7.147/0.002 | 7.144/7.149 | 100.0 |
| `ccrs_60_gap_200` | 5 | 5 | 0 | 0 | 5 | 10.500/0.000 | 25.326/0.001 | 7.146/0.001 | 7.145/7.149 | 100.0 |
| `ccrs_65` | 5 | 5 | 0 | 0 | 5 | 1.750/0.000 | 28.207/0.000 | 5.423/0.043 | 5.394/5.508 | 100.0 |
| `ccrs_80` | 5 | 5 | 0 | 0 | 5 | 1.600/0.000 | 39.254/0.000 | 6.617/0.018 | 6.603/6.652 | 100.0 |
| `clear_road_50` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `clear_road_65` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `clear_road_80` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `curve_adjacent_stationary_65` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `curve_ccrs_65` | 5 | 5 | 0 | 0 | 5 | 1.250/0.000 | 26.054/0.001 | 2.973/0.004 | 2.965/2.978 | 100.0 |
| `curve_clear_65` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `curve_clear_80` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `cut_in_65_45` | 5 | 5 | 0 | 0 | 5 | 3.850/0.000 | 15.981/0.017 | 13.552/0.016 | 13.543/13.584 | 100.0 |
| `cut_in_80_50` | 5 | 5 | 0 | 0 | 5 | 2.750/0.000 | 24.530/0.001 | 18.618/0.008 | 18.612/18.633 | 100.0 |
| `cut_out_65_35` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | 100.0 |
| `cut_out_80_50` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | 100.0 |
| `cut_out_late_65_35` | 5 | 0 | 5 | 0 | 0 | --/-- | --/-- | -20.798/0.013 | -20.809/-20.772 | 100.0 |
| `multi_adjacent_decoy_65` | 5 | 5 | 0 | 0 | 5 | 2.550/0.000 | 22.957/0.002 | 15.579/0.014 | 15.551/15.589 | 100.0 |
| `multi_two_leads_80` | 5 | 5 | 0 | 0 | 5 | 1.050/0.000 | 30.061/0.000 | 14.109/0.634 | 13.790/15.377 | 100.0 |
| `non_closing_60_80` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | 29.996/0.000 | 29.996/29.996 | 100.0 |

## Largest minimum-gap variation

| Scenario | Mean min gap | Std | Range | Min | Max |
|---|---:|---:|---:|---:|---:|
| `multi_two_leads_80` | 14.109 | 0.634 | 1.587 | 13.790 | 15.377 |
| `ccrs_65` | 5.423 | 0.043 | 0.114 | 5.394 | 5.508 |
| `ccrs_50` | 6.270 | 0.034 | 0.089 | 6.249 | 6.338 |
| `ccrb_50_to_0` | 6.964 | 0.030 | 0.062 | 6.927 | 6.989 |
| `ccrs_80` | 6.617 | 0.018 | 0.049 | 6.603 | 6.652 |
| `cut_in_65_45` | 13.552 | 0.016 | 0.041 | 13.543 | 13.584 |
| `multi_adjacent_decoy_65` | 15.579 | 0.014 | 0.038 | 15.551 | 15.589 |
| `cut_out_late_65_35` | -20.798 | 0.013 | 0.037 | -20.809 | -20.772 |
| `ccrm_65_30` | 15.538 | 0.010 | 0.028 | 15.531 | 15.559 |
| `cut_in_80_50` | 18.618 | 0.008 | 0.021 | 18.612 | 18.633 |
