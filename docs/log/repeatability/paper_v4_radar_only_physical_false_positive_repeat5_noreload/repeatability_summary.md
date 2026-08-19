# Repeatability Summary

Run directory: `logs/paper_v4_radar_only_physical_false_positive_repeat5_noreload`

## Overall

| Metric | Value |
|---|---:|
| Scenarios | 2 |
| Runs | 10 |
| PASS runs | 0 |
| FAIL runs | 10 |
| Collision runs | 0 |
| Brake activated runs | 10 |
| All-PASS scenarios | 0 |
| All-FAIL scenarios | 2 |
| Mixed-outcome scenarios | 0 |

## By family

| Family | Runs | PASS | FAIL | Collision | Brake |
|---|---:|---:|---:|---:|---:|
| physical | 10 | 0 | 10 | 0 | 10 |

## Scenario outcomes

| Scenario | Runs | PASS | FAIL | Collision | Brake | First brake mean/std (s) | Brake gap mean/std (m) | Min gap mean/std (m) | Min gap min/max (m) | Hazard match mean (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `physical_left_cone_60_20_offset_1p40` | 5 | 0 | 5 | 0 | 5 | 0.900/0.000 | 4.793/0.000 | -12.332/0.000 | -12.332/-12.332 | 100.0 |
| `physical_right_cone_60_20_offset_1p45` | 5 | 0 | 5 | 0 | 5 | 0.600/0.000 | 9.791/0.000 | -7.332/0.000 | -7.332/-7.332 | 100.0 |

## Largest minimum-gap variation

| Scenario | Mean min gap | Std | Range | Min | Max |
|---|---:|---:|---:|---:|---:|
| `physical_left_cone_60_20_offset_1p40` | -12.332 | 0.000 | 0.000 | -12.332 | -12.332 |
| `physical_right_cone_60_20_offset_1p45` | -7.332 | 0.000 | 0.000 | -7.332 | -7.332 |
