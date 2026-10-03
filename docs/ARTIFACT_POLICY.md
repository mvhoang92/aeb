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
| Models/environments | `models/`, `$AEB_WORKSPACE_ROOT/environments/`, CARLA `venv/` | Machine-local or release assets; do not commit new large binaries |
| Raw release archive | tarballs, model weights, large datasets | Use GitHub Release, LFS or an external archive after license review |

Existing tracked binaries remain in history. Do not rewrite history merely to
remove them. New large artifacts should not be added directly to Git.

## Binary size rule (forward-looking, from 2026-10-03)

1. Do not add any new file larger than about **5 MB** to Git (archives, model
   weights, `.docx`/`.pptx`/PDF exports, videos, datasets, large images).
2. Publish large exports and archives as **GitHub Release assets** or on
   **Zenodo** (see `release/ZENODO_PAPER_V5_2.md`). Record in Git, next to the
   evidence that depends on them: file name, byte size, SHA-256 and the
   release/DOI URL (for example a `*.sha256` file or a `SHA256SUMS.txt` entry).
3. Small curated evidence (CSV/JSON/Markdown summaries, figures used by a
   manuscript) stays in Git.
4. Prefer referencing an existing tracked file over committing a second copy
   of the same bytes.
5. **History is never rewritten.** Existing tracked binaries — including the
   21 MB frozen raw archive and the report exports — stay in history and in
   their current paths. No `git filter-repo`/BFG, no force-push, no deletion
   or move of frozen evidence to save space. Reducing clone size is not a
   reason to break the checksum and tag chain.

## Repository size snapshot (measured 2026-10-03 at `53628db`)

Tracked working tree: 541 files, 125.8 MB (518 distinct blobs). History over
all refs: 807 blobs, 173.1 MB uncompressed. The shared object store
`/home/mvhoang/CARLA_0.9.11/aeb/.git` occupies 159 MB on disk (1,247 loose
objects, no packfiles).

| Top-level path | Tracked files | Bytes |
|---|---:|---:|
| `report/` | 102 | 70,977,711 |
| `docs/` | 191 | 40,595,022 |
| `paper/` | 78 | 13,036,757 |
| `scripts/` | 57 | 386,669 |
| `configs/` | 45 | 308,001 |
| `ui/` | 8 | 172,770 |
| root files | 3 | 73,878 |
| `tests/` | 15 | 69,575 |
| `core/` | 8 | 50,427 |
| `control/` | 9 | 35,042 |
| `evaluation/` | 10 | 19,928 |
| `.opencode/` | 9 | 18,586 |
| `perception/` | 3 | 13,878 |
| `infrastructure/` | 2 | 5,902 |
| `models/` | 1 | 1 (`.gitkeep`; weights are untracked) |

Largest tracked files (5 above 5 MB, 20 above 1 MB):

| Bytes | Path |
|---:|---|
| 21,270,043 | `docs/log/repeatability/artifacts/paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz` |
| 14,927,927 | `report/exports/aeb_report_v3.docx` |
| 14,651,551 | `report/templates/aeb_report_template_v3.docx` |
| 10,525,527 | `report/presentation/aeb_project_slides.pptx` |
| 6,208,983 | `report/archive/validation/report_v3_layout_review/aeb_report_draft.pdf` |
| 4,789,605 | `report/exports/aeb_report_v3.pdf` |
| 3,724,905 | `docs/log/repeatability/artifacts/paper_v3_fusion_full66_repeat5_noreload.tar.gz` |
| 3,548,808 | `docs/log/repeatability/artifacts/paper_v4_fusion_binary_full66_repeat5_noreload_raw_logs.tar.gz` |
| 3,071,029 | `report/exports/generated_images/yolo_val_batch0_labels.png` (and an identical copy, see below) |
| 2,951,264 | `docs/log/repeatability/artifacts/paper_v3_radar_only_full66_repeat5_noreload.tar.gz` |

### Duplicate tracked content

`git ls-files -s | awk {print } | sort | uniq -d` lists **16 blobs**
tracked under more than one path. Git stores each blob once, so duplicates
cost no object-store space; they add about 5.1 MB to every checkout and can
drift if only one copy is edited. Main groups:

| Blob size | Paths |
|---:|---|
| 3,071,029 | `report/exports/generated_images/yolo_val_batch0_labels.png` = `report/exports/slides/generated/yolo_val_batch0_labels.png` |
| 819,192 | `report/exports/{generated_images,slides/generated}/final_demo_cutin_80_50_gap_25.png` |
| 261,707 | `report/exports/{generated_images,slides/generated}/carla.png` |
| 121,818 | `scenario_level_tradeoff.png` in `docs/log/repeatability/paper_v5_derived/figures/`, `paper/paper_v5/figures/`, `paper/paper_v5_1/figures/` |
| 57,704–99,445 | five v4 figures (`fallback_ablation`, `core_precision_recall`, `holdout_pass_fail`, `gpu_inference_latency`, `stress_suite_pass_rates`) in `docs/log/repeatability/paper_v4_gpu_final/figures/`, `paper/paper_v4/figures/` and `report/assets/evidence_v3/` |
| 21,437 | `configs/scenarios/car_to_car/ccrs_stationary_lead.yaml` = `configs/scenarios/suites/system_limit_ccrs_sweep.yaml` |
| < 6 kB | `references.bib` (v1=v2, v3=v4), `build.sh` (v1=v2, v4=v5), `paper_v1..v3/.gitignore`, one `repeatability_by_family.csv` pair |

Paper-figure duplicates are intentional: each manuscript generation carries a
byte-for-byte copy of the evidence figure it cites. They are documented here,
not removed. Future generations should still copy cited figures (immutability
beats deduplication); report export duplicates should not be repeated.

Possible later maintenance that does not rewrite history: `git gc` to pack the
loose objects (local disk only), and publishing future report exports as
release assets.

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
