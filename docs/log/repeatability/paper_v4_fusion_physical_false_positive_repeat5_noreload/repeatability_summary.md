# Repeatability Summary

Run directory: `logs/paper_v4_fusion_physical_false_positive_repeat5_noreload`

## Overall

| Metric | Value |
|---|---:|
| Scenarios | 2 |
| Runs | 10 |
| PASS runs | 10 |
| FAIL runs | 0 |
| Collision runs | 0 |
| Brake activated runs | 0 |
| All-PASS scenarios | 2 |
| All-FAIL scenarios | 0 |
| Mixed-outcome scenarios | 0 |

## By family

| Family | Runs | PASS | FAIL | Collision | Brake |
|---|---:|---:|---:|---:|---:|
| physical | 10 | 10 | 0 | 0 | 0 |

## Scenario outcomes

| Scenario | Runs | PASS | FAIL | Collision | Brake | First brake mean/std (s) | Brake gap mean/std (m) | Min gap mean/std (m) | Min gap min/max (m) | Hazard match mean (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `physical_left_cone_60_20_offset_1p40` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | -46.845/0.000 | -46.845/-46.845 | 100.0 |
| `physical_right_cone_60_20_offset_1p45` | 5 | 5 | 0 | 0 | 0 | --/-- | --/-- | -46.845/0.000 | -46.845/-46.845 | 100.0 |

## Largest minimum-gap variation

| Scenario | Mean min gap | Std | Range | Min | Max |
|---|---:|---:|---:|---:|---:|
| `physical_left_cone_60_20_offset_1p40` | -46.845 | 0.000 | 0.000 | -46.845 | -46.845 |
| `physical_right_cone_60_20_offset_1p45` | -46.845 | 0.000 | 0.000 | -46.845 | -46.845 |
