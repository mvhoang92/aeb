# Scenario and Evaluation Contract

## Statistical unit

A named condition is the primary unit. Repetitions measure consistency and are
not independent road samples. Report both named-condition outcomes and run-level
consistency without pseudo-replication.

## Outcome contract

Scenario PASS combines configured brake expectation, collision expectation,
minimum gap and optional lane constraints. Algorithmic FAIL is retained as
evidence. Retry only technical failures such as CARLA timeout/crash, CUDA
provider mismatch or inference error.

## Core metrics

- TP/FP/TN/FN and precision/recall by named condition.
- Collision conditions, minimum gap and last-tick pre-impact speed proxy.
- False-brake onset speed, duration and full-stop rate.
- Peak deceleration and absolute jerk.
- Fusion-blocked/fallback ticks and target-match diagnostics.

`evaluation/schemas.py` freezes 57 tick fields and 41 summary fields. Changing
field order/name requires a versioned schema and migration, not an incidental
refactor.

Synthetic radar returns are **synthetic fault injection**, not estimates of
native CARLA ghost prevalence. The frozen adverse hold-out is a mechanism
hold-out, not a deployment distribution.
