# Refactor Plan: Project Structure v1

## Objective

Reduce entry-point and controller coupling without changing AEB decisions,
scenario definitions, CLI/config compatibility, telemetry schemas or frozen
evidence. Work is isolated on `refactor/project-structure-v1`; `main` is not
merged automatically.

## Invariants

- No algorithm tuning, threshold changes or PERG-AEB implementation.
- Preserve radar-only, hard camera gate and emergency-fallback behavior.
- Preserve `laucher.py`, both historical runner paths and existing CLI options.
- Preserve YAML keys/defaults and CSV/JSON summary fields.
- Do not delete dataset, log, output, model or training artifacts.
- Do not modify frozen evidence, paper generations or frozen tags.

## Phases

1. **Inventory and baseline**
   - Add structure/artifact documentation and capture baseline test gates.
2. **Launcher compatibility**
   - Introduce correctly spelled `launcher.py`; retain `laucher.py` as a thin
     compatibility wrapper.
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
/home/mvhoang/CARLA_0.9.11/venv/bin/python -m compileall -q control core evaluation perception scripts tests ui launcher.py laucher.py
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
