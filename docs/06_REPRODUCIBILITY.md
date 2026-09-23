# Reproducibility Contract

A reproducible run records:

- Git commit and dirty state;
- exact command/Python executable;
- sensor/scenario config paths and SHA-256;
- CARLA client/server/map/fixed timestep;
- seed, repetition and control mode;
- model SHA/provider/cadence/inference diagnostics;
- ordered tick and summary schemas.

Final headline evidence requires CUDA. Provider mismatch or inference error is a
technical hard-stop. CPU campaigns may be diagnostic but cannot be mixed into
final evidence.

Protocol order:

1. Define development suites and metrics.
2. Tune only on development data.
3. Freeze config, suite and code tag.
4. Open hold-out once.
5. Preserve algorithmic FAIL.
6. Derive named-condition and severity metrics.
7. Archive raw logs/checksums and create claim–evidence mapping.

Do not tune after hold-out. A new algorithm such as PERG-AEB needs protocol v2,
a new development generation and hold-out B.
