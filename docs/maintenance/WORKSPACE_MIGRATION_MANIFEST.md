# Workspace Migration Manifest

## Migration

Machine-local bulk artifacts were moved from the Git working-tree root to
`/home/mvhoang/CARLA_0.9.11/aeb_workspace` on branch
`maintenance/repository-cleanup-v1`. No dataset, log, output or training file
was intentionally deleted.

| Source generation/root | Files | Bytes | Destination |
|---|---:|---:|---|
| `dataset` | 136 | 28,456,742 | `datasets/archive/v1` |
| `dataset_v2` | 787 | 211,654,683 | `datasets/archive/v2` |
| `dataset_v3` | 6,028 | 1,797,854,074 | `datasets/archive/v3` |
| `dataset_v4` | 364 | 101,389,015 | `datasets/archive/v4` |
| `dataset_v5` | 8,443 | 2,314,325,031 | `datasets/archive/v5` |
| `dataset_v6` | 8,034 | 1,652,730,358 | `datasets/archive/v6` |
| `dataset_v7_same_lane` | 6,131 | 1,873,600,729 | `datasets/active/v7_same_lane` |
| `logs` | 8,083 | 362,512,887 | `runs/logs` |
| `outputs` | 8,003 | 2,751,463,298 | categorized under `runs/` |
| `training_runs` | 90 | 329,029,399 | `training` |
| **Total** | **46,099** | **11,423,016,216** | |

## Verification

Every source file was SHA-256 hashed before the move. Destination paths were
mapped deterministically and all 46,099 files were rehashed after the move:

```text
missing: 0
mismatches: 0
source files: 46,099
destination files: 46,099
status: PASS
```

Workspace manifest checksums:

```text
8d8632fa2709b2c748b4c3ffd8c3cc1c066899ea28f40f1890494c69be53982f  SOURCE_SHA256SUMS.txt
e62b97cb748bfa646809756c8cef31c01116677e8233efdbeafd62a3378fcb7b  DESTINATION_SHA256SUMS.txt
459f36801a028fed9ca31be36fada12f826114fb199e8663096e139a4b41d234  SOURCE_INVENTORY.json
88d64151bfcfe99e586228ef9d071968ab3f432e79cd7104242dea2e5cfef468  MIGRATION_VERIFICATION.json
```

Full manifests remain outside Git in `aeb_workspace/manifests/` because they
contain 46,099 machine-local paths. The independent pre-refactor backup and Git
bundle remain unchanged.

## Post-migration checks

- Legacy path resolver found active v7, archived v6, logs, campaign output,
  training runs and deployment model.
- Dataset-v7 audit: 1,505 train, 300 validation and 200 test images; all quality
  gates passed.
- Repository unit/claim/compile gates passed before and after migration.
