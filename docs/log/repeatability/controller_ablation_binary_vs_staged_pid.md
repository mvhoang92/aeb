# Controller ablation: binary vs staged_pid (fusion, full 66 x5, no reload)

Holding perception (camera-gated fusion), scenario suite, control mode, and
repeat count constant, we compare the two braking controllers to justify the
`staged_pid` choice used throughout the paper.

## Configs

- `staged_pid`: `configs/sensors.yaml` (`brake_mode: staged_pid`)
- `binary`: `configs/sensors_binary.yaml` (`brake_mode: binary`, all other brake
  parameters identical)

## Commands

```bash
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/system_limit_extended_sweep.yaml \
  --sensor-config configs/sensors_binary.yaml \
  --control-mode physics --repeat 5 \
  --run-id paper_v4_fusion_binary_full66_repeat5_noreload \
  --load-map --scenario-cooldown-s 1.0 --reload-world-every 0 --reload-world-wait-s 2.0
```

The `staged_pid` reference run is
`paper_v3_fusion_full66_repeat5_noreload` (same suite, `configs/sensors.yaml`).

## Result

| Metric | binary | staged_pid |
|---|---:|---:|
| Runs | 330 | 330 |
| PASS runs | 310 | 315 |
| FAIL runs | 20 | 15 |
| Collision runs | 20 | 15 |
| All-PASS scenarios | 62 | 63 |
| All-FAIL scenarios | 4 | 3 |

The only scenario where the two controllers differ:

| Scenario | binary | staged_pid |
|---|---|---|
| `ccrb_110_gap_30` | 0/5 PASS, 5/5 collision | 5/5 PASS, 0 collision |

## Root cause

Both controllers eventually trigger `distance_below_stopping_threshold`, but the
stopping-distance margin threshold differs by braking mode:

- `staged_pid`: distance brake fires when `distance_margin <= pid_target_margin_m (4.0 m)`.
- `binary`: the PID distance-margin path is disabled, so distance brake fires
  only when `distance_margin <= 0.0 m` (target already inside the required
  stopping distance).

On `ccrb_110_gap_30` (ego 110 km/h, lead full-brakes at 30 m gap) this makes
staged_pid brake ~0.10 s earlier (first BRAKE at 2.25 s vs 2.35 s), which is
enough to avoid collision (final gap 1.65 m vs 0.00 m).

| Controller | first BRAKE (s) | final gap (m) | collision |
|---|---:|---:|---:|
| staged_pid | 2.25 | 1.653 | 0 |
| binary | 2.35 | 0.0035 | 1 |

## Comfort

Mean across all-PASS scenarios:

| Controller | mean max decel (m/s²) | mean max jerk (m/s³) |
|---|---:|---:|
| binary | 11.2 | 170.2 |
| staged_pid | 10.5 | 169.4 |

Binary is slightly harsher on average (full-brake command) but the dominant
safety difference is the earlier distance-margin intervention of staged_pid.

## Conclusion

`staged_pid` is retained because it triggers braking slightly earlier through
the stopping-distance margin, avoiding one additional high-speed collision with
no meaningful comfort penalty. This ablation justifies the controller choice in
the paper and is reported as the controller ablation.

## Artifacts

- Binary summary: `docs/log/repeatability/paper_v4_fusion_binary_full66_repeat5_noreload/`
- Config: `configs/sensors_binary.yaml`
- Raw logs: `docs/log/repeatability/artifacts/paper_v4_fusion_binary_full66_repeat5_noreload_raw_logs.tar.gz`
