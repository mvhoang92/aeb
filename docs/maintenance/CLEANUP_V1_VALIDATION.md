# Repository Cleanup v1 — Validation

## Scope

Cleanup branch: `maintenance/repository-cleanup-v1`. The operation separated
machine-local bulk artifacts from Git source, organized report/docs history and
added canonical documentation. It did not modify policy thresholds, frozen
paper versions, curated repeatability evidence or final report-v3 deliverables.

## Storage migration

- 46,099 dataset/log/output/training files, 11,423,016,216 bytes.
- Source and mapped destination SHA-256 verified for every file.
- Missing files: 0; mismatches: 0; status: PASS.
- Active dataset v7 audit: 1,505 train, 300 validation, 200 test images; all
  quality gates PASS.
- YOLO Python environment moved atomically to
  `aeb_workspace/environments/yolo310`; imports and PyTorch CUDA availability
  PASS. Comparison with independent backup showed no non-cache file changes.

See `WORKSPACE_MIGRATION_MANIFEST.md` and external
`aeb_workspace/manifests/`.

## Code/documentation gates

- 95 unit/golden/compatibility tests: PASS.
- 80 control/core/evaluation/infrastructure/perception/script imports: PASS.
- Paper-v4/report-v3 claim validator: PASS.
- Paper-v5 scenario/severity/bilingual validator: PASS.
- Compile audit and `git diff --check`: PASS.
- Canonical launcher prerequisite check: PASS, 66 scenarios. The misspelled
  historical wrapper was subsequently retired by maintainer decision.
- Workspace resolver/check: all seven dataset generations and directories PASS.
- Report-v3 PDF/DOCX checksums remain equal to the frozen checksum file.

## Post-migration CARLA/CUDA smoke

Runs were written directly to `aeb_workspace/runs/logs` at clean commit
`fbc0134418389985789791a1ebe880914d424d38`.

| Policy | Condition | Outcome | Runtime evidence |
|---|---|---|---|
| Radar-only | `ccrs_30` | PASS, brake, no collision, 7.752 m gap | External default log root used |
| Hard camera gate | `limit_ccrs_40_gap_40` | PASS, brake, no collision, 7.540 m gap | camera-confirmed; CUDA required/active; 27 inference; 0 errors |
| Emergency fallback | `dev_box_in_path` | PASS, brake, no collision, 0.846 m gap | 49 fallback ticks; CUDA required/active; 19 inference; 0 errors |

Smoke checksums:

```text
f47bd700e81cde89304740fea1d4e3012b58b37ca87faa6df3b9490d881736de  radar summary.json
8b1f60c6e791e836d5127374dfb1de662a140bd249caff1309b201ee835e0aef  radar run_metadata.json
154e017a27f2bcd990c5dff7ba6dc170881895ff295e5d992eb65fd65706eaa3  hard-gate summary.json
a5a693f0a755b56f10aee81a64f126f8b0671ba82a6d074d59d91c99c285788c  hard-gate run_metadata.json
a2725c6c9a99e4d44c230aa458012a5d93a73cbe04c803c8cab8a6a2d2a58afd  fallback summary.json
1ebca81a9ea8cda480d4df8c95fce758773657994fd255ddab51788d9c28809c  fallback run_metadata.json
```

These are cleanup compatibility smokes, not new scientific evidence.
