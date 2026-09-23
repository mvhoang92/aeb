# Workspace and Artifact Storage

## Boundary

Git repository contains source, config, canonical docs, curated evidence and
versioned manuscripts. Machine-local bulk data lives in `AEB_WORKSPACE_ROOT`
(default `/home/mvhoang/CARLA_0.9.11/aeb_workspace`).

```text
aeb_workspace/
├── datasets/active/v7_same_lane
├── datasets/archive/v1 ... v6
├── runs/logs
├── runs/campaigns
├── runs/videos
├── runs/sensor_coverage
├── runs/dataset_box_checks
├── training
├── manifests
└── quarantine
```

Run `scripts/check_workspace.py` to print resolved paths. Existing explicit
paths win; missing historical paths are deterministically mapped by
`infrastructure/workspace.py`. Resolution must be recorded in runtime metadata
for new campaigns.

Do not commit datasets, runtime logs, environments or new large model binaries.
Do not rewrite Git history to remove existing historical binaries. Before move
or cleanup, capture file count, byte count and SHA-256; verify destination before
removing old path entries.

See `ARTIFACT_POLICY.md` and `maintenance/WORKSPACE_MIGRATION_MANIFEST.md`.
