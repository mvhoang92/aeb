# Physical false-positive fusion comparison (repeat x5, no reload)

This comparison uses `configs/scenarios/suites/fusion_physical_false_positive.yaml`.
Unlike the synthetic false-object injection suite, these cases spawn real CARLA
static props (`static.prop.trafficcone01`) near the ego path. They are labelled
non-hazards because the ego can pass without collision when AEB does not brake.
A radar-only BRAKE is therefore counted as a false brake.

## Commands

Radar-only:

```bash
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/fusion_physical_false_positive.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --repeat 5 \
  --run-id paper_v4_radar_only_physical_false_positive_repeat5_noreload \
  --load-map \
  --scenario-cooldown-s 0.5 \
  --reload-world-every 0 \
  --reload-world-wait-s 2.0
```

Fusion:

```bash
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/fusion_physical_false_positive.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --repeat 5 \
  --run-id paper_v4_fusion_physical_false_positive_repeat5_noreload \
  --load-map \
  --scenario-cooldown-s 0.5 \
  --reload-world-every 0 \
  --reload-world-wait-s 2.0
```

## Result

| Configuration | Runs | PASS | FAIL | Collision | Brake activated | False brake |
|---|---:|---:|---:|---:|---:|---:|
| Radar-only | 10 | 0 | 10 | 0 | 10 | 10 |
| Camera-gated fusion | 10 | 10 | 0 | 0 | 0 | 0 |

## Scenario-level result

| Scenario | Radar-only | Fusion |
|---|---:|---:|
| `physical_right_cone_60_20_offset_1p45` | 0/5 PASS, 5/5 brake | 5/5 PASS, 0/5 brake |
| `physical_left_cone_60_20_offset_1p40` | 0/5 PASS, 5/5 brake | 5/5 PASS, 0/5 brake |

## Interpretation

- Radar-only selected the physical traffic-cone return as an AEB target and
  braked in all `10/10` runs, without any collision being recorded.
- Camera-gated fusion suppressed braking in all `10/10` runs and also recorded
  no collision, showing a physically instantiated case where fusion behaves
  more appropriately than radar-only.
- Fusion tick reasons include `fusion_blocked_brake:no_yolo_detection`, then
  `fusion_blocked_brake:no_radar_target` after the non-vehicle target leaves the
  selected radar gate while ego continues to pass.

## Metric caveat

`minimum_bumper_gap_m` can become negative in these pass-by cone scenarios even
when `collision=False`, because the existing scorer was designed for same-lane
lead-vehicle gaps and is not a robust clearance metric for small static props
near the lane edge. For this stress suite, the primary pass/fail evidence is the
combination of `brake_activated`, `collision`, and the labelled non-hazard
scenario definition.

## Paper wording

Safe wording:

> In a physical false-positive stress suite with real CARLA traffic cones placed
> near the ego path, radar-only produced false AEB activations in 10/10 runs,
> whereas camera-gated fusion suppressed braking in 10/10 runs with no recorded
> collisions.

This is stronger than synthetic radar injection because the radar returns come
from physical CARLA props, but it is still a targeted stress suite rather than a
broad real-world false-positive rate estimate.

## Artifacts

- Radar-only summary: `docs/log/repeatability/paper_v4_radar_only_physical_false_positive_repeat5_noreload/`
- Fusion summary: `docs/log/repeatability/paper_v4_fusion_physical_false_positive_repeat5_noreload/`
- Scenario config: `configs/scenarios/suites/fusion_physical_false_positive.yaml`
