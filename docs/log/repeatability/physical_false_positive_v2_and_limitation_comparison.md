# Physical false-positive v2 and non-vehicle hazard limitation (repeat x5, no reload)

This page documents the full trade-off of camera-gated fusion on **physical**
CARLA static props, without any synthetic radar injection.

## Suites

| Suite | Question | Expected |
|---|---|---|
| `fusion_physical_false_positive_v2.yaml` | Does fusion suppress radar false brakes on non-vehicle props near the ego path? | Radar-only false brakes; fusion does not brake and does not collide |
| `fusion_nonvehicle_hazard_limitation.yaml` | Does car-only camera gating miss genuine non-vehicle hazards in the ego path? | Radar-only brakes and avoids collision; fusion suppresses brake and collides |

## Commands

Radar-only (v2):

```bash
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/fusion_physical_false_positive_v2.yaml \
  --sensor-config configs/sensors.yaml --control-mode physics --repeat 5 \
  --run-id paper_v4_radar_only_physical_false_positive_v2_repeat5_noreload \
  --load-map --scenario-cooldown-s 0.5 --reload-world-every 0 --reload-world-wait-s 2.0
```

Fusion (v2):

```bash
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/fusion_physical_false_positive_v2.yaml \
  --sensor-config configs/sensors.yaml --control-mode physics --repeat 5 \
  --run-id paper_v4_fusion_physical_false_positive_v2_repeat5_noreload \
  --load-map --scenario-cooldown-s 0.5 --reload-world-every 0 --reload-world-wait-s 2.0
```

Limitation suite is run identically with
`fusion_nonvehicle_hazard_limitation.yaml` and run IDs
`paper_v4_{radar_only,fusion}_nonvehicle_hazard_repeat5_noreload`.

## Result: fusion advantage (props near ego path, non-hazard)

| Configuration | Runs | PASS | FAIL | Collision | Brake activated | False brake |
|---|---:|---:|---:|---:|---:|---:|
| Radar-only | 40 | 0 | 40 | 0 | 40 | 40 |
| Camera-gated fusion | 40 | 40 | 0 | 0 | 0 | 0 |

Props included: `static.prop.barrel`, `static.prop.box01`,
`static.prop.trashcan01`, `static.prop.streetbarrier` at lane-edge offsets
(1.30 m, 1.40 m, 1.50 m) on both left and right.

## Result: fusion limitation (non-vehicle in ego path, genuine hazard)

| Configuration | Runs | PASS | FAIL | Collision | Brake activated | Missed brake |
|---|---:|---:|---:|---:|---:|---:|
| Radar-only | 10 | 10 | 0 | 0 | 10 | 0 |
| Camera-gated fusion | 10 | 0 | 10 | 10 | 0 | 10 |

Props: `static.prop.box01`, `static.prop.barrel` directly in the ego path
(`lateral_offset_m: 0.0`). Radar-only stopped with a minimum gap of ~0.85 m in
all runs; fusion suppressed every BRAKE and collided in all runs.

## Interpretation

- The YOLO car gate gives a real, repeatable false-brake reduction when radar
  selects a non-vehicle object that ego can pass safely: 40/40 false brakes
  removed versus radar-only.
- The same car-only gate is a **safety limitation** for non-vehicle hazards in
  the ego path: radar-only avoided collisions 10/10, while fusion missed every
  brake and collided 10/10.
- This pair of suites is the honest headline result for the camera-gating
  contribution: it trades radar false-brake robustness against non-vehicle
  obstacle coverage. The current gate only confirms CAR-class YOLO boxes.

## Paper wording

Recommended:

> On physical CARLA static props near the ego path, camera-gated fusion removed
> 40/40 radar-only false AEB activations without introducing a collision.
> However, because the gate only confirms vehicle-class boxes, fusion missed
> every non-vehicle obstacle placed directly in the ego path (10/10 collisions),
> whereas radar-only stopped safely in 10/10 runs. We therefore report the YOLO
> gate as a false-positive suppression mechanism with a documented non-vehicle
> coverage limitation, not as a general obstacle-avoidance improvement.

## Artifacts

- `docs/log/repeatability/paper_v4_radar_only_physical_false_positive_v2_repeat5_noreload/`
- `docs/log/repeatability/paper_v4_fusion_physical_false_positive_v2_repeat5_noreload/`
- `docs/log/repeatability/paper_v4_radar_only_nonvehicle_hazard_repeat5_noreload/`
- `docs/log/repeatability/paper_v4_fusion_nonvehicle_hazard_repeat5_noreload/`
- `configs/scenarios/suites/fusion_physical_false_positive_v2.yaml`
- `configs/scenarios/suites/fusion_nonvehicle_hazard_limitation.yaml`
