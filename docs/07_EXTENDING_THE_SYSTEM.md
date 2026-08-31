# Extending the System

## Add a brake policy

1. Implement `BrakePermissionPolicy` in a new module.
2. Keep baseline policy classes unchanged.
3. Add sequence/golden tests for action, reason, reset and temporal state.
4. Inject via `PolicyControlledAEBRuntime`; do not fork the scenario loop.
5. Add a new config generation and protocol before CARLA tuning.

## Add a scenario

Place reusable definitions in `configs/scenarios/car_to_car/` and named suites
in `configs/scenarios/suites/`. Declare expected brake/collision and scoring
constraints explicitly. New adverse mechanisms intended for hold-out must not
be inspected during tuning.

## Add telemetry or metrics

Keep tick derivation in `evaluation/telemetry.py`, severity in `severity.py` and
scenario scoring in `scoring.py`. Version the schema if external field order or
meaning changes. Add golden CSV/JSON tests.

## Add scripts

Implementation belongs under `scripts/campaign`, `analysis`, `dataset`,
`training` or `maintenance`. Preserve an existing root script as a thin wrapper
when external automation uses that path.

Minimum gate: unit tests, manuscript validators, compile/import audit and
`git diff --check`; changes touching a runner also require three policy smokes.
