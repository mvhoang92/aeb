# Fusion-benefit stress comparison (repeat x5, no reload)

This comparison uses `configs/scenarios/suites/fusion_benefit_stress.yaml`.
The suite intentionally injects radar-only synthetic false objects in clear-road
scenarios. It is **not** normal CARLA radar evidence; it is a labelled sensor
fault / false-object stress test to show the intended value of camera-gated
fusion when radar proposes an object that YOLO cannot confirm as a car.

## Commands

Radar-only:

```bash
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_radar_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/fusion_benefit_stress.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --repeat 5 \
  --run-id paper_v3_radar_only_fusion_benefit_stress_repeat5_noreload \
  --load-map \
  --scenario-cooldown-s 1.0 \
  --reload-world-every 0 \
  --reload-world-wait-s 2.0
```

Fusion:

```bash
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/run_fusion_aeb_scenarios.py \
  --scenario-config configs/scenarios/suites/fusion_benefit_stress.yaml \
  --sensor-config configs/sensors.yaml \
  --control-mode physics \
  --repeat 5 \
  --run-id paper_v3_fusion_benefit_stress_repeat5_noreload \
  --load-map \
  --scenario-cooldown-s 1.0 \
  --reload-world-every 0 \
  --reload-world-wait-s 2.0
```

## Result

| Configuration | Runs | PASS | FAIL | Collision | Brake activated |
|---|---:|---:|---:|---:|---:|
| Radar-only | 30 | 0 | 30 | 0 | 30 |
| Camera-gated fusion | 30 | 30 | 0 | 0 | 0 |

## Interpretation

- Radar-only treated the synthetic radar false object as a valid AEB target and
  braked in all `30/30` runs, which is a false brake because the road is clear.
- Camera-gated fusion blocked all provisional radar BRAKE decisions in `30/30`
  runs because YOLO did not confirm a vehicle box at the radar projection.
- Tick-level fusion reason was dominated by
  `fusion_blocked_brake:no_yolo_detection`.

## Paper wording guardrail

Safe wording:

> In an explicit radar false-object injection stress suite, camera-gated fusion
> suppressed all radar-only false brakes (30/30 vs. 0/30 pass). This demonstrates
> the intended fault-containment role of the YOLO gate under labelled synthetic
> radar false-positive conditions.

Do **not** overclaim that this proves a lower real-world CARLA false-brake rate.
The normal negative regression suite still had 0% false-brake rate for both
radar-only and fusion, so this stress evidence should be reported separately as
synthetic false-object robustness evidence.

## Artifacts

- Radar-only summary: `docs/log/repeatability/paper_v3_radar_only_fusion_benefit_stress_repeat5_noreload/`
- Fusion summary: `docs/log/repeatability/paper_v3_fusion_benefit_stress_repeat5_noreload/`
- Scenario config: `configs/scenarios/suites/fusion_benefit_stress.yaml`
