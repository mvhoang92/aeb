# Repeatability Summary

Run directory: `logs/paper_v4_radar_only_physical_false_positive_v2_repeat5_noreload`

## Overall

| Metric | Value |
|---|---:|
| Scenarios | 8 |
| Runs | 40 |
| PASS runs | 0 |
| FAIL runs | 40 |
| Collision runs | 0 |
| Brake activated runs | 40 |
| All-PASS scenarios | 0 |
| All-FAIL scenarios | 8 |
| Mixed-outcome scenarios | 0 |

## By family

| Family | Runs | PASS | FAIL | Collision | Brake |
|---|---:|---:|---:|---:|---:|
| prop | 40 | 0 | 40 | 0 | 40 |

## Scenario outcomes

| Scenario | Runs | PASS | FAIL | Collision | Brake | First brake mean/std (s) | Brake gap mean/std (m) | Min gap mean/std (m) | Min gap min/max (m) | Hazard match mean (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `prop_barrel_right_1p30` | 5 | 0 | 5 | 0 | 5 | 0.350/0.000 | 13.955/0.000 | -3.169/0.000 | -3.169/-3.169 | 100.0 |
| `prop_barrel_right_1p40` | 5 | 0 | 5 | 0 | 5 | 0.800/0.000 | 6.459/0.000 | -10.664/0.000 | -10.664/-10.664 | 100.0 |
| `prop_box_right_1p40` | 5 | 0 | 5 | 0 | 5 | 0.450/0.000 | 12.290/0.000 | -4.834/0.000 | -4.834/-4.834 | 100.0 |
| `prop_box_right_1p50` | 5 | 0 | 5 | 0 | 5 | 0.650/0.000 | 8.958/0.000 | -8.166/0.000 | -8.166/-8.165 | 100.0 |
| `prop_streetbarrier_right_1p30` | 5 | 0 | 5 | 0 | 5 | 0.650/0.000 | 8.958/0.000 | -8.166/0.000 | -8.166/-8.166 | 100.0 |
| `prop_streetbarrier_right_1p40` | 5 | 0 | 5 | 0 | 5 | 0.700/0.000 | 8.125/0.000 | -9.001/0.000 | -9.001/-9.001 | 100.0 |
| `prop_trashcan_left_1p30` | 5 | 0 | 5 | 0 | 5 | 0.400/0.000 | 13.123/0.000 | -4.004/0.000 | -4.004/-4.004 | 100.0 |
| `prop_trashcan_left_1p40` | 5 | 0 | 5 | 0 | 5 | 0.900/0.000 | 4.793/0.000 | -12.332/0.000 | -12.332/-12.332 | 100.0 |

## Largest minimum-gap variation

| Scenario | Mean min gap | Std | Range | Min | Max |
|---|---:|---:|---:|---:|---:|
| `prop_box_right_1p50` | -8.166 | 0.000 | 0.001 | -8.166 | -8.165 |
| `prop_barrel_right_1p30` | -3.169 | 0.000 | 0.000 | -3.169 | -3.169 |
| `prop_barrel_right_1p40` | -10.664 | 0.000 | 0.000 | -10.664 | -10.664 |
| `prop_box_right_1p40` | -4.834 | 0.000 | 0.000 | -4.834 | -4.834 |
| `prop_streetbarrier_right_1p30` | -8.166 | 0.000 | 0.000 | -8.166 | -8.166 |
| `prop_streetbarrier_right_1p40` | -9.001 | 0.000 | 0.000 | -9.001 | -9.001 |
| `prop_trashcan_left_1p30` | -4.004 | 0.000 | 0.000 | -4.004 | -4.004 |
| `prop_trashcan_left_1p40` | -12.332 | 0.000 | 0.000 | -12.332 | -12.332 |
