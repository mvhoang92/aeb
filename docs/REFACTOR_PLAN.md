# Refactor Plan: Project Structure v1

## Objective

Reduce entry-point and controller coupling without changing AEB decisions,
scenario definitions, CLI/config compatibility, telemetry schemas or frozen
evidence. Work is isolated on `refactor/project-structure-v1`; `main` is not
merged automatically.

## Status

Phases 1–8 are complete on the refactor branch. Static/golden gates and all
three CARLA policy smokes passed. Validation details are recorded in
`docs/log/refactor/REFACTOR_V1_VALIDATION.md`. Merge remains a user decision.

## Invariants

- No algorithm tuning, threshold changes or PERG-AEB implementation.
- Preserve radar-only, hard camera gate and emergency-fallback behavior.
- Preserve historical runner paths and existing CLI options. The temporary
  `laucher.py` compatibility wrapper was retired after cleanup by explicit
  maintainer decision; `launcher.py` is now the only desktop entry point.
- Preserve YAML keys/defaults and CSV/JSON summary fields.
- Do not delete dataset, log, output, model or training artifacts.
- Do not modify frozen evidence, paper generations or frozen tags.

## Phases

1. **Inventory and baseline**
   - Add structure/artifact documentation and capture baseline test gates.
2. **Launcher compatibility**
   - Introduce correctly spelled `launcher.py`; the temporary `laucher.py`
     wrapper was later removed after callers and documentation migrated.
3. **Brake-permission policy boundary**
   - Add a common policy result/interface and adapters for radar-only, hard gate
     and emergency fallback. Keep `FusionBrakeGate` as the frozen mechanism.
4. **Evaluation extraction**
   - Move pure scoring, motion/severity metrics, CSV and metadata helpers out of
     the CARLA runner. Keep compatibility re-exports in the historical module.
5. **Runner policy injection**
   - Replace fusion subclass overrides with explicit policy composition where
     this can be proven behavior-equivalent. Keep historical runner CLIs.
6. **Brake module decomposition**
   - Separate data/state, risk math, stopping-distance/config and controller
     implementation behind `control.brake` compatibility exports.
7. **Script taxonomy**
   - Document campaign/analysis/dataset/maintenance roles. Move only when a
     wrapper and import regression test protect every historical path.
8. **Runtime smoke and review**
   - Run radar-only, hard-gate and fallback smoke cases in isolated CARLA/CUDA
     sessions, compare output schemas/outcomes, and prepare merge evidence.

## Required gates

After every structural checkpoint:

```bash
/home/mvhoang/CARLA_0.9.11/venv/bin/python -m unittest discover -s tests -q
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/validate_v4_manuscript_claims.py
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/validate_v5_manuscript_claims.py
/home/mvhoang/CARLA_0.9.11/venv/bin/python -m compileall -q control core evaluation perception scripts tests ui launcher.py
git diff --check
```

When a scenario runner changes, static gates are necessary but insufficient:
run one named radar-only, hard-gate and fallback smoke case. A CUDA provider
mismatch or inference error is a technical hard-stop. Algorithmic FAIL remains
an outcome and must not be retried as a technical failure.

## Rollback

Each phase is a small commit pushed to the refactor branch. Roll back the latest
phase with Git; use `pre-refactor-project-v1` or the independent backup for a
full restore. Never force-update frozen tags or rewrite shared history.

## Post-submission deferred work (added 2026-10-03)

Status: **deferred until the paper v5.2 manuscript is submitted and its Zenodo
package (`release/ZENODO_PAPER_V5_2.md`) is published.** Measurements below
were taken at `53628db`.

### Why this waits

The submitted claims rest on the frozen campaign
`paper_v4_gpu_final_locked_20260825`, produced by commit `3be8ae4`
(`safe-fallback-eval-v1`) and re-derived offline by
`scripts/analyze_v5_review_metrics.py`. Reviewers may ask for re-derivation
or a targeted re-run during review. Until the review cycle ends, the code
paths and config bytes that a reviewer would execute must stay where the
manuscript, source map and Zenodo README say they are. A structural change
now adds risk to reproducibility of frozen evidence without adding scientific
value; the items below bring maintainability only and are scheduled after
submission (and before any new protocol generation such as PERG-AEB).

### A. Split `scripts/run_radar_aeb_scenarios.py` into a package

Current state: 1,688 lines, 64 kB. It holds `HeadlessRadarAEB`,
`CollisionRecorder`, `ScenarioEvidenceRecorder` (lines 55–245),
`ScenarioRunner` (lines 246–1346, about 1,100 lines), 17 CARLA geometry, unit and brake-label
helpers (lines 1347–1586) and the CLI (`parse_args`/`main`, lines
1587–1688). `scripts/run_fusion_aeb_scenarios.py` (322 lines) imports the core
runner from it, and so do `launcher.py`, `ui/radar_aeb_view.py`,
`scripts/campaign/run_v4_campaign.py`,
`scripts/campaign/smoke_yolo_fusion_full.py` and two test modules.

Plan: create a package (for example `evaluation/runner/` or
`scenario_runner/`) with modules for recorders, CARLA geometry helpers,
scenario setup/actors, the tick loop and the CLI. Keep
`scripts/run_radar_aeb_scenarios.py` as the entry point and re-export every
public name it has today.

Prerequisites:

- paper v5.2 submitted, Zenodo record published, DOI in the manuscript;
- golden fixtures built from the frozen raw archive (read-only extraction to a
  temp/workspace directory, never into `docs/log/`);
- a CUDA-capable CARLA 0.9.11 session available for the smoke runs.

Acceptance criteria (golden-log equivalence):

1. Offline gate (no simulator): for every tick CSV in the frozen archive, the
   refactored scoring/summary code reproduces the archived per-run
   `summary.csv`/`summary.json` fields and `aggregate_summary.*` byte- or
   value-identically, and `scripts/analyze_v5_review_metrics.py` still
   reproduces `docs/log/repeatability/paper_v5_derived/` byte-identically
   (CSV, Markdown, PNG — as verified on 2026-10-03).
2. Schema gate: the tick-CSV header (column names **and order**), summary
   fields and `run_metadata.json` keys are identical to the frozen logs.
3. Online gate: with the same seed (2026), sensor/scenario configs (same
   SHA-256), model SHA and CUDA provider, one named scenario per policy
   (radar-only, hard gate, safe fallback) plus one hold-out ghost and one
   physical-prop case yields the same `brake_activated`, collision, PASS/FAIL
   and first-brake tick as the frozen run of that scenario. Tick-level float
   differences are reported, not silently accepted.
4. Import gate: every historical import path and CLI option still works
   (existing tests plus a new import-surface test).
5. Unit tests, `validate_v4/v5/v51` claim validators, `compileall` and
   `git diff --check` pass; no file under `docs/log/repeatability/` or
   `paper/` changes.

### B. Sensor configs: base + overlay for new configs only

Current state: 11 `configs/sensors*.yaml` files (158–181 lines each, 1,844
lines total). Measured with `diff`, they differ from `configs/sensors.yaml` by
2–17 changed lines and from each other by 2–27 changed lines (55 pairs). The
final campaign pins `sensors.yaml`, `sensors_fusion_hard_batch_gpu.yaml` and
`sensors_fusion_safe_fallback_batch_gpu.yaml` by SHA-256 in every
`run_metadata.json`; older v4 archives reference `sensors_binary.yaml` and the
`sensors_fusion_hold_*.yaml` files by path. The campaign driver already
generates variant configs by deep-copying a base and writing the resolved YAML
(`generated_sensor_configs/`).

Plan: introduce a loader for `base` + `overlay` YAML (deep merge, explicit
list replacement) used **only by new configurations**. The loader writes the
fully resolved YAML next to the run output and records the SHA-256 of the
resolved file, the base and each overlay in `run_metadata.json`.

Rules and acceptance criteria:

1. The 11 existing `configs/sensors*.yaml` files stay in place and
   **byte-identical** (checked against their current SHA-256 in a test). They
   are not regenerated, reformatted or replaced by overlays.
2. Expressibility test: for each existing config, an overlay over the base
   resolves to a dict equal (`yaml.safe_load`) to the existing file. This
   proves the mechanism without touching frozen bytes.
3. Runners keep accepting a plain single-file config exactly as today.
4. Resolved-config SHA-256 is what new runs compare and cite.

### C. Compatibility shims in `scripts/` stay

There are 23 compatibility wrappers of exactly 17 lines in `scripts/` (for
example `scripts/analyze_v5_review_metrics.py`,
`scripts/run_v4_final_pipeline.py`, `scripts/validate_v5_manuscript_claims.py`)
that re-export the implementations moved to `scripts/{analysis,campaign,
dataset,training,maintenance}/`. They are kept indefinitely: frozen tags,
protocols, manuscripts, the Zenodo README and archived commands use these
paths. They cost about 400 lines and no maintenance. Removal is out of scope;
new code should import the package modules directly.

### D. Sequencing

1. Submit paper v5.2 and publish the Zenodo record.
2. Tag the submitted state (e.g. `paper-v5.2-submitted`).
3. Build offline golden fixtures and the schema test (A.1, A.2).
4. Split the runner in small commits, each passing the offline gates; run the
   online gate once at the end (A.3).
5. Add the overlay loader and its byte-identity/expressibility tests (B).
6. Record validation in `docs/log/refactor/` as for refactor v1.
