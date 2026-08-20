# Repeatability Summary

Run directory: `logs/paper_v4_fusion_nonvehicle_hazard_repeat5_noreload`

## Overall

| Metric | Value |
|---|---:|
| Scenarios | 2 |
| Runs | 10 |
| PASS runs | 0 |
| FAIL runs | 10 |
| Collision runs | 10 |
| Brake activated runs | 0 |
| All-PASS scenarios | 0 |
| All-FAIL scenarios | 2 |
| Mixed-outcome scenarios | 0 |

## By family

| Family | Runs | PASS | FAIL | Collision | Brake |
|---|---:|---:|---:|---:|---:|
| prop | 10 | 0 | 10 | 10 | 0 |

## Scenario outcomes

| Scenario | Runs | PASS | FAIL | Collision | Brake | First brake mean/std (s) | Brake gap mean/std (m) | Min gap mean/std (m) | Min gap min/max (m) | Hazard match mean (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `prop_barrel_in_path_0p00` | 5 | 0 | 5 | 5 | 0 | --/-- | --/-- | 0.014/0.000 | 0.014/0.014 | 100.0 |
| `prop_box_in_path_0p00` | 5 | 0 | 5 | 5 | 0 | --/-- | --/-- | 0.011/0.000 | 0.011/0.011 | 100.0 |

## Largest minimum-gap variation

| Scenario | Mean min gap | Std | Range | Min | Max |
|---|---:|---:|---:|---:|---:|
| `prop_barrel_in_path_0p00` | 0.014 | 0.000 | 0.000 | 0.014 | 0.014 |
| `prop_box_in_path_0p00` | 0.011 | 0.000 | 0.000 | 0.011 | 0.011 |
