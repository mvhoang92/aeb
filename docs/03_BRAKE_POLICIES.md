# Brake-Permission Policies

The radar pipeline produces a provisional `AEBDecision`. A policy may pass it
through or replace provisional BRAKE with RELEASE; it must not recompute TTC,
stopping distance or brake magnitude.

| Policy | Camera role | Main trade-off |
|---|---|---|
| `RadarOnlyPolicy` | None | High recall, radar false-brake exposure |
| `HardCameraGatePolicy` | Current/recent positive confirmation required | High precision, camera-miss false negatives |
| `EmergencyFallbackPolicy` | Gate plus critical central radar fallback | Recovers misses, admits supported ghosts/non-vehicle hazards |

Shared contract:

```python
evaluate(BrakePermissionContext) -> BrakePermissionResult
reset() -> None
```

Context includes provisional decision, target, camera confirmation/reason,
simulation timestamp and path offset. Result includes final decision, stable
action/reason diagnostics and fallback state.

`confirmation_hold_s=0.35` and fallback thresholds are frozen baseline behavior.
Do not tune them after hold-out. PERG-AEB is a future policy requiring a new
protocol/config/tag/hold-out; it must not alter these baseline implementations.
