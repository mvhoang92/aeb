# Paper v5 reviewer-derived evidence

No CARLA run was added or removed. Metrics are derived from the frozen campaign tick logs.

## Named-condition confusion (primary statistical unit)

| Scope | Policy | N | TP | FP | TN | FN | Precision (95% Wilson) | Recall (95% Wilson) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| core_without_synthetic_fault | radar_only | 105 | 84 | 8 | 12 | 1 | 0.913 [0.838, 0.955] | 0.988 [0.936, 0.998] |
| core_without_synthetic_fault | hard_gate | 105 | 82 | 0 | 20 | 3 | 1.000 [0.955, 1.000] | 0.965 [0.901, 0.988] |
| core_without_synthetic_fault | safe_fallback | 105 | 84 | 0 | 20 | 1 | 1.000 [0.956, 1.000] | 0.988 [0.936, 0.998] |
| frozen_adverse_holdout | radar_only | 14 | 6 | 5 | 2 | 1 | 0.545 [0.280, 0.787] | 0.857 [0.487, 0.974] |
| frozen_adverse_holdout | hard_gate | 14 | 5 | 0 | 7 | 2 | 1.000 [0.566, 1.000] | 0.714 [0.359, 0.918] |
| frozen_adverse_holdout | safe_fallback | 14 | 6 | 4 | 3 | 1 | 0.600 [0.313, 0.832] | 0.857 [0.487, 0.974] |

## False-brake severity on adverse hold-out

- radar_only: 25 false-brake runs; median onset 78.4 km/h, duration 3.60 s, peak deceleration 9.02 m/s^2; 25/25 stopped below 1 km/h.
- safe_fallback: 20 false-brake runs; median onset 78.4 km/h, duration 3.60 s, peak deceleration 9.02 m/s^2; 20/20 stopped below 1 km/h.

Binary FP counts therefore represent full simulated emergency stops in these injected-ghost cases, not one-tick brake pulses.

## Physical hold-out collision severity

Pre-impact speed is the ego speed at the last 0.05-s tick before the first collision event.

| Policy | Scenario | Runs | Median pre-impact speed | Median first-brake gap |
|---|---|---:|---:|---:|
| hard_gate | holdout_bench_center_v60_g22 | 5 | 59.95 km/h | no brake |
| hard_gate | holdout_cart_center_v50_g18 | 5 | 49.96 km/h | no brake |
| hard_gate | holdout_warning_center_v70_g25 | 5 | 7.82 km/h | 21.87 m |
| radar_only | holdout_bench_center_v60_g22 | 5 | 32.57 km/h | 12.62 m |
| radar_only | holdout_cart_center_v50_g18 | 5 | 49.96 km/h | no brake |
| radar_only | holdout_warning_center_v70_g25 | 5 | 7.82 km/h | 21.87 m |
| safe_fallback | holdout_bench_center_v60_g22 | 5 | 54.93 km/h | 4.29 m |
| safe_fallback | holdout_cart_center_v50_g18 | 5 | 49.96 km/h | no brake |
| safe_fallback | holdout_warning_center_v70_g25 | 5 | 7.82 km/h | 21.87 m |

## Scoring definition audited from the frozen runner

- `brake_activated`: at least one logged tick with `aeb_override=true`.
- Brake confusion compares this binary event with the scenario's preassigned `expected_brake` label.
- Collision is true when any logged tick has `collision_count>0`; final scenarios normally set `expected_collision=false`.
- `PASS` requires brake and collision expectations to match. Positive non-collision scenarios additionally require minimum bumper gap >= the configured threshold (default 0.5 m); selected scenarios also enforce lane/target assertions.
- Collision and PASS remain separate from brake TP/FN because a brake may activate too late.
