# Fusion gate hold-time sensitivity (confirmation_hold_s sweep)

We sweep `fusion.confirmation_hold_s` over `{0.10, 0.35, 0.70, 1.00}` s while
holding perception, scenarios, control mode, and repeat count constant, to check
whether the default `0.35 s` is a sensitive hyperparameter of the YOLO gate.

## Setup

- Runner: `scripts/run_fusion_aeb_scenarios.py`
- Scenario suite: `configs/scenarios/suites/radar_only_regression.yaml`,
  filtered to 8 scenarios:
  - hazards (`expected_brake=true`): `ccrb_65_to_0`, `cut_in_65_45`,
    `cut_in_80_50`, `cut_out_late_65_35`
  - non-hazards (`expected_brake=false`): `clear_road_65`,
    `adjacent_stationary_65`, `cut_out_65_35`, `cut_out_80_50`
- `--control-mode physics --repeat 5 --reload-world-every 0`
- Configs: `configs/sensors_fusion_hold_{0p10,0p35,0p70,1p00}.yaml`

## Result

| hold_s (s) | TP | FP | TN | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| 0.10 | 16 | 0 | 20 | 4 | 1.000 | 0.800 |
| 0.35 | 15 | 0 | 20 | 5 | 1.000 | 0.750 |
| 0.70 | 15 | 0 | 20 | 5 | 1.000 | 0.750 |
| 1.00 | 15 | 0 | 20 | 5 | 1.000 | 0.750 |

## Reading

1. **False brakes stay at zero** for every hold value: the YOLO gate does not
   confirm non-car objects, so lengthening the confirmation hold window does not
   introduce false brakes on this set.
2. **The single FN source is `cut_out_late_65_35`**, and it is hold-time
   invariant. That miss is driven by the radar target leaving the lateral path
   corridor (see `docs/log/cut_out_late_65_35_failure_analysis.md`), not by the
   fusion confirmation window.
3. The one extra TP at `hold=0.10` is a single `cut_out_late_65_35` run that
   braked at 2.0 s (run 4/5). This matches the known run-to-run lateral-threshold
   stochasticity of that scenario (radar-only shows the same 4/5 vs 1/5
   pattern), not a systematic hold-time effect.

## Conclusion

`confirmation_hold_s` is **not** a sensitive knob for the FP/FN trade-off in
this scenario set: precision stays 1.0 and the only missed-brake case is
determined by radar corridor loss, independent of the hold window. The default
`0.35 s` is a safe, non-knife-edge choice.

## Artifacts

- Run IDs: `paper_v4_fusion_hold_{0p10,0p35,0p70,1p00}_sensitivity_repeat5_noreload`
- Configs: `configs/sensors_fusion_hold_{0p10,0p35,0p70,1p00}.yaml`
