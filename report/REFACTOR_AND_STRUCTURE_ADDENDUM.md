# Addendum: Source Refactor and Workspace Separation

## Status

This addendum documents structural work performed after frozen report v3. It
does not revise report-v3 scientific claims, algorithms, thresholds or final
campaign outcomes.

## Source architecture

The previous monolithic runner/controller implementation was decomposed into:

- an explicit brake-permission policy contract for radar-only, hard camera gate
  and emergency fallback;
- shared policy-controlled headless runtime composition;
- independent evaluation schema/scoring/telemetry/severity writers;
- control risk, state-machine, staged/PID and actuation modules;
- categorized script implementations behind historical CLI wrappers.

Compatibility exports preserve the historical `control.brake`, runner and
launcher paths.

## Artifact architecture

Bulk local data moved to sibling `aeb_workspace/`:

- dataset v7 is active; v1–v6 are archived without deletion;
- logs, campaign outputs, videos, sensor-coverage and box-check products are
  separated by class;
- training runs and migration manifests are outside Git;
- source/config/docs/curated evidence remain in the repository.

`infrastructure/workspace.py` resolves existing explicit paths first and then
maps known historical paths. New runs record external output locations; frozen
curated evidence and tags remain unchanged.

## Regression evidence

The refactor passed unit/golden tests, manuscript validators, import/compile
checks and CARLA smokes for all three policies. Controller sequence decisions,
output schemas and extracted scoring helpers were compared with the
pre-refactor tag. Workspace migration separately verified 46,099/46,099 files
by SHA-256 with zero missing or mismatched files.

Detailed records:

- `../docs/log/refactor/REFACTOR_V1_VALIDATION.md`
- `../docs/maintenance/WORKSPACE_MIGRATION_MANIFEST.md`

A future PERG-AEB algorithm belongs in a new report generation after a new
protocol and hold-out; it must not be retrofitted into report v3.
