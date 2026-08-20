# Repeatability Summary

Run directory: `logs/paper_v4_radar_only_nonvehicle_hazard_repeat5_noreload`

## Overall

| Metric | Value |
|---|---:|
| Scenarios | 2 |
| Runs | 10 |
| PASS runs | 10 |
| FAIL runs | 0 |
| Collision runs | 0 |
| Brake activated runs | 10 |
| All-PASS scenarios | 2 |
| All-FAIL scenarios | 0 |
| Mixed-outcome scenarios | 0 |

## By family

| Family | Runs | PASS | FAIL | Collision | Brake |
|---|---:|---:|---:|---:|---:|
| prop | 10 | 10 | 0 | 0 | 10 |

## Scenario outcomes

| Scenario | Runs | PASS | FAIL | Collision | Brake | First brake mean/std (s) | Brake gap mean/std (m) | Min gap mean/std (m) | Min gap min/max (m) | Hazard match mean (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `prop_barrel_in_path_0p00` | 5 | 5 | 0 | 0 | 5 | 0.150/0.000 | 17.287/0.000 | 0.846/0.000 | 0.846/0.846 | 100.0 |
| `prop_box_in_path_0p00` | 5 | 5 | 0 | 0 | 5 | 0.150/0.000 | 17.287/0.000 | 0.846/0.000 | 0.846/0.846 | 100.0 |

## Largest minimum-gap variation

| Scenario | Mean min gap | Std | Range | Min | Max |
|---|---:|---:|---:|---:|---:|
| `prop_barrel_in_path_0p00` | 0.846 | 0.000 | 0.000 | 0.846 | 0.846 |
| `prop_box_in_path_0p00` | 0.846 | 0.000 | 0.000 | 0.846 | 0.846 |
