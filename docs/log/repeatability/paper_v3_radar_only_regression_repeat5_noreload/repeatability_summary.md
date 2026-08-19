# Paper V3 Radar Only Regression Repeat5 Noreload Summary

This file is a lightweight, git-tracked derived summary generated from local logs. Raw per-tick CSV logs are archived under `docs/log/repeatability/artifacts/`.

Generation command:

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/summarize_repeatability.py \
  logs/paper_v3_radar_only_regression_repeat5_noreload \
  --output-dir outputs/paper_v3_reproduction/repeatability/paper_v3_radar_only_regression_repeat5_noreload
```

Run directory: `logs/paper_v3_radar_only_regression_repeat5_noreload`

## Overall

| Metric | Value |
|---|---:|
| Scenarios | 29 |
| Runs | 145 |
| PASS runs | 141 |
| FAIL runs | 4 |
| Collision runs | 0 |
| Brake activated runs | 81 |
| All-PASS scenarios | 28 |
| All-FAIL scenarios | 0 |
| Mixed-outcome scenarios | 1 |

## By family

| Family | Runs | PASS | FAIL | Collision | Brake |
|---|---:|---:|---:|---:|---:|
| CCRb | 15 | 15 | 0 | 0 | 15 |
| CCRm | 15 | 15 | 0 | 0 | 15 |
| CCRs | 25 | 25 | 0 | 0 | 25 |
| adjacent | 15 | 15 | 0 | 0 | 0 |
| clear | 15 | 15 | 0 | 0 | 0 |
| curve | 20 | 20 | 0 | 0 | 5 |
| cut | 25 | 21 | 4 | 0 | 11 |
| multi | 10 | 10 | 0 | 0 | 10 |
| non | 5 | 5 | 0 | 0 | 0 |

## Scenario outcomes

| Scenario | Runs | PASS | FAIL | Collision | Brake | First brake mean/std (s) | Brake gap mean/std (m) | Min gap mean/std (m) | Min gap min/max (m) | Hazard match mean (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `adjacent_stationary_50` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `adjacent_stationary_65` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `adjacent_stationary_80` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `ccrb_50_to_0` | 5 | 5 | 0 | 0 | 5 | 2.800/0.000 | 19.519/0.001 | 6.986/0.001 | 6.985/6.988 | 100.0 |
| `ccrb_65_to_0` | 5 | 5 | 0 | 0 | 5 | 2.900/0.000 | 27.628/0.016 | 7.323/0.008 | 7.319/7.339 | 100.0 |
| `ccrb_80_to_0` | 5 | 5 | 0 | 0 | 5 | 3.000/0.000 | 37.577/0.002 | 8.458/0.002 | 8.456/8.460 | 100.0 |
| `ccrm_50_20` | 5 | 5 | 0 | 0 | 5 | 2.720/0.024 | 17.124/0.183 | 12.250/0.188 | 12.020/12.404 | 100.0 |
| `ccrm_65_30` | 5 | 5 | 0 | 0 | 5 | 2.750/0.000 | 23.017/0.003 | 15.536/0.001 | 15.534/15.537 | 100.0 |
| `ccrm_80_50` | 5 | 5 | 0 | 0 | 5 | 3.650/0.000 | 24.234/0.007 | 18.179/0.005 | 18.174/18.189 | 100.0 |
| `ccrs_50` | 5 | 5 | 0 | 0 | 5 | 1.750/0.000 | 20.491/0.000 | 6.251/0.005 | 6.242/6.255 | 100.0 |
| `ccrs_60_demo_150` | 5 | 5 | 0 | 0 | 5 | 7.500/0.000 | 25.324/0.000 | 7.148/0.001 | 7.146/7.149 | 100.0 |
| `ccrs_60_gap_200` | 5 | 5 | 0 | 0 | 5 | 10.500/0.000 | 25.325/0.000 | 7.146/0.001 | 7.145/7.149 | 100.0 |
| `ccrs_65` | 5 | 5 | 0 | 0 | 5 | 1.750/0.000 | 28.207/0.000 | 5.400/0.006 | 5.393/5.405 | 100.0 |
| `ccrs_80` | 5 | 5 | 0 | 0 | 5 | 1.600/0.000 | 39.254/0.000 | 6.611/0.004 | 6.603/6.613 | 100.0 |
| `clear_road_50` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `clear_road_65` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `clear_road_80` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `curve_adjacent_stationary_65` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `curve_ccrs_65` | 5 | 5 | 0 | 0 | 5 | 1.250/0.000 | 26.054/0.001 | 2.973/0.004 | 2.965/2.977 | 100.0 |
| `curve_clear_65` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `curve_clear_80` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | -- |
| `cut_in_65_45` | 5 | 5 | 0 | 0 | 5 | 3.850/0.000 | 15.974/0.004 | 13.545/0.004 | 13.540/13.551 | 100.0 |
| `cut_in_80_50` | 5 | 5 | 0 | 0 | 5 | 2.750/0.000 | 24.540/0.018 | 18.621/0.018 | 18.600/18.655 | 100.0 |
| `cut_out_65_35` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | 100.0 |
| `cut_out_80_50` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | --/-- | --/-- | 100.0 |
| `cut_out_late_65_35` | 5 | 1 | 4 | 0 | 1 | 2.000/0.000 | 20.868/0.000 | -13.670/14.264 | -20.804/14.858 | 100.0 |
| `multi_adjacent_decoy_65` | 5 | 5 | 0 | 0 | 5 | 2.550/0.000 | 22.964/0.017 | 15.594/0.010 | 15.588/15.614 | 100.0 |
| `multi_two_leads_80` | 5 | 5 | 0 | 0 | 5 | 1.050/0.000 | 30.062/0.001 | 13.828/0.040 | 13.791/13.877 | 100.0 |
| `non_closing_60_80` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | 29.996/0.000 | 29.996/29.996 | 100.0 |

## Largest minimum-gap variation

| Scenario | Mean min gap | Std | Range | Min | Max |
|---|---:|---:|---:|---:|---:|
| `cut_out_late_65_35` | -13.670 | 14.264 | 35.662 | -20.804 | 14.858 |
| `ccrm_50_20` | 12.250 | 0.188 | 0.384 | 12.020 | 12.404 |
| `multi_two_leads_80` | 13.828 | 0.040 | 0.086 | 13.791 | 13.877 |
| `cut_in_80_50` | 18.621 | 0.018 | 0.055 | 18.600 | 18.655 |
| `multi_adjacent_decoy_65` | 15.594 | 0.010 | 0.026 | 15.588 | 15.614 |
| `ccrb_65_to_0` | 7.323 | 0.008 | 0.020 | 7.319 | 7.339 |
| `ccrs_65` | 5.400 | 0.006 | 0.012 | 5.393 | 5.405 |
| `ccrm_80_50` | 18.179 | 0.005 | 0.015 | 18.174 | 18.189 |
| `ccrs_50` | 6.251 | 0.005 | 0.013 | 6.242 | 6.255 |
| `curve_ccrs_65` | 2.973 | 0.004 | 0.012 | 2.965 | 2.977 |

## Mixed-outcome scenarios

- `cut_out_late_65_35`: PASS 1, FAIL 4
