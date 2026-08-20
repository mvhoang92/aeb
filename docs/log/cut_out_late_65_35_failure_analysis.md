# Failure analysis: `cut_out_late_65_35`

## Scenario

From `configs/scenarios/suites/radar_only_regression.yaml`:

```yaml
id: cut_out_late_65_35
type: cut_out
ego_speed_kph: 65.0
duration_s: 7.0
lane_follow: true
max_lane_offset_m: 1.25
expected_brake: true
expected_collision: false
actors:
  - role: cut_out
    hazard: true
    speed_kph: 35.0
    initial_gap_m: 38.0
    spawn_lane: ego
    lane_change: { start_s: 0.8, direction: left }
```

A slow lead (35 km/h) starts in the ego lane, 38 m ahead, then begins a left
lane change at t=0.8 s while the ego approaches at 65 km/h.

## Observed outcomes

| Config | Result |
|---|---|
| Radar-only | 4/5 FAIL (missed brake), 1/5 PASS |
| Fusion (camera gate) | 5/5 FAIL (missed brake) |

## Timeline (tick-level, representative runs)

| t (s) | ego (km/h) | gap (m) | target lateral (m) | TTC (s) | state |
|---|---:|---:|---:|---:|---|
| 0.35 | 64.9 | 34.8 | +0.02 | 4.17 | NORMAL |
| 1.55 | 64.9 | 24.7 | -0.10 | 2.91 | WARNING |
| 1.85 | 64.9 | 22.1 | -0.84 | 2.65 | WARNING |
| 2.00 | 64.9 | 20.9 | **-0.88 / -1.16** | 2.50 | WARNING/BRAKE boundary |
| 2.15 | 64.9 | 19.6 | -1.03 | 2.36 | WARNING |
| 2.20–2.45 | 64.9 | 17.1 | > 1.25 | — | RELEASE (target lost) |

## Root cause

Two lateral thresholds race against the stopping-distance margin at roughly the
same moment (~t = 2.0 s):

1. **Path corridor** (`max_lateral_offset_m = 1.25`): the radar target must stay
   within 1.25 m laterally to remain a valid path target.
2. **Distance-brake threshold** (`pid_target_margin_max_lateral_m = 0.95`):
   when `abs(target_lateral) <= 0.95 m`, the stopping-distance brake threshold
   is `pid_target_margin_m = 4.0 m`; beyond 0.95 m it drops to 0 m.

The stopping-distance margin is:

```text
margin = target_distance - required_stopping_distance
```

At ego 65 km/h (18.1 m/s) closing 8.3 m/s, `required_stopping_distance ≈ 17.1 m`
and `target_distance ≈ 20.9 m`, so `margin ≈ 3.75 m`, which crosses below the
4.0 m threshold at almost exactly the same time the cut-out target's lateral
offset crosses 0.95 m.

Consequence at the critical frame (t = 2.0 s):

| Run | target lateral (m) | distance-brake threshold | margin (m) | Decision |
|---|---|---|---:|---:|---|
| Radar-only run 05 | -0.88 (≤ 0.95) | 4.0 | 3.76 | BRAKE |
| Radar-only runs 01–04 | > 0.95 | 0.0 | ~3.78 | no brake |
| Fusion runs 01–05 | > 0.95 | 0.0 | ~3.78 | no brake |

A ~0.28 m difference in the cut-out vehicle's lateral position at one frame
determines whether the distance brake triggers before the target leaves the
corridor. The TTC never reaches the 1.5 s TTC brake threshold (minimum ~2.36 s),
so TTC braking never engages.

## Camera gate role

In the fusion run that mirrors radar-only run 05, the tick reason is
`ttc_below_warning_threshold|fusion_confirmed` up to the target-loss frame. The
camera gate **did not block** the brake; the radar target itself left the path
corridor. Therefore this case is a **lateral-corridor timing boundary**, not a
camera-gating failure.

## Conclusion for the paper

- `cut_out_late_65_35` is a borderline scenario: the cut-out vehicle is already
  leaving the lane, and its lateral offset crosses the 0.95 m / 1.25 m corridor
  thresholds at nearly the same time the stopping-distance margin reaches the
  brake trigger.
- Radar-only and fusion both miss for the same reason; the single radar-only
  pass is a one-frame lateral-threshold coincidence, not a systematic advantage.
- The `expected_brake: true` label is itself arguable for a vehicle that is
  actively cutting out of the lane.
- Report this in "Threats to validity" as a lateral-gating timing sensitivity,
  and avoid using it as evidence of camera-gate regression.
