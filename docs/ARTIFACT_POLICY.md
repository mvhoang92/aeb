# Artifact Policy

## Principles

1. Source refactoring must not delete, rename or regenerate historical evidence.
2. A failed algorithm run is evidence. Retry only documented technical failures.
3. Final headline evidence must remain the frozen CUDA campaign; CPU outputs are
   diagnostic only.
4. Synthetic radar returns are synthetic fault injection, not native CARLA
   prevalence statistics.
5. Checksums and frozen Git tags are part of the evidence chain.

## Storage classes

| Class | Examples | Policy |
|---|---|---|
| Source/configuration | `core/`, `control/`, `scripts/`, `configs/`, `tests/` | Track in Git and review normally |
| Curated evidence | `docs/log/repeatability/`, claim matrices, CSV summaries | Track when required for reproducibility; never rewrite frozen generations |
| Manuscript/report | `paper/paper_v*/`, `report/chapters_v3/`, approved exports | Preserve each version; create a new version instead of overwriting history |
| Raw local runtime data | `$AEB_WORKSPACE_ROOT/datasets`, `runs`, `training` | Keep outside Git; move only with manifest/checksum verification |
| Models/environments | `models/`, `.venv_yolo310/`, CARLA `venv/` | Machine-local or release assets; do not commit new large binaries |
| Raw release archive | tarballs, model weights, large datasets | Use GitHub Release, LFS or an external archive after license review |

Existing tracked binaries remain in history. Do not rewrite history merely to
remove them. New large artifacts should not be added directly to Git.

## Frozen evidence

The local final campaign root is
`$AEB_WORKSPACE_ROOT/runs/campaigns/paper_v4_final_pipeline/paper_v4_gpu_final_locked_20260825/`;
curated evidence is in `docs/log/repeatability/paper_v4_gpu_final/`. Paper v5 derived
metrics are in `docs/log/repeatability/paper_v5_derived/`. Refactoring may read
these files for golden checks but may not regenerate them in place.

Before any future algorithm or protocol change:

- create a new branch and configuration generation;
- freeze development settings before opening a new hold-out;
- use a new run ID/output directory and tag;
- report named conditions as the primary statistical unit;
- retain repetitions as consistency evidence;
- record provider, detector and technical-failure metadata.

PERG-AEB or other new algorithms are explicitly outside the structural-refactor
campaign and require a new protocol and hold-out.

## Backup and recovery

The pre-refactor independent backup is outside the repository at
`/home/mvhoang/CARLA_0.9.11/aeb_backup_pre_refactor_20260825`. Its companion Git
bundle, manifest and critical-file SHA-256 list are in the CARLA root. Restore
or compare against these assets; never edit them from the refactor branch.
