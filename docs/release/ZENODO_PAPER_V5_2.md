# Zenodo Release: Paper v5.2 Reproducibility Package

Status: **staged locally, not uploaded.** Prepared 2026-10-03. The authors
upload and publish it themselves; no tool in this repository talks to Zenodo.

## Staging locations (outside Git)

| Path | Purpose |
|---|---|
| `$AEB_WORKSPACE_ROOT/releases/zenodo_paper_v5_2/` | Full package as a directory tree with `README.md`, `LICENSES.md`, `VERIFICATION.md`, `SHA256SUMS`, `.zenodo.json` |
| `$AEB_WORKSPACE_ROOT/releases/zenodo_paper_v5_2_upload/record1_data/` | Ready-to-drag files for the **data record** (CC-BY-4.0): `aeb_paper_v5_2_evidence.zip`, `README.md`, `LICENSES.md`, `SHA256SUMS` |
| `$AEB_WORKSPACE_ROOT/releases/zenodo_paper_v5_2_upload/record2_model/` | Ready-to-drag files for the **model record** (AGPL-3.0): `yolo26n_aeb_v7.onnx`, `yolo26n_aeb_v7.pt`, `MODEL_CARD.md`, `yolo26n_aeb_v7_training_run.zip`, `LICENSES.md`, `SHA256SUMS` |

Default `AEB_WORKSPACE_ROOT` is `/home/mvhoang/CARLA_0.9.11/aeb_workspace`.
Zenodo flattens folders on upload, so the directory tree is shipped as a zip
(Zenodo previews zip contents); top-level `README.md` and `LICENSES.md` are
uploaded separately so they are readable on the record page.

## Package contents (39.6 MB, 93 files)

| Part | Size | Source |
|---|---:|---|
| Frozen raw archive `paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz` (47 jobs, 2,461 runs, tick CSVs, run metadata, config snapshots, campaign and CARLA server logs) | 21.3 MB | `docs/log/repeatability/artifacts/` |
| Curated evidence `paper_v4_gpu_final/` and `paper_v5_derived/` | 0.6 MB | `docs/log/repeatability/` |
| `campaign_manifest.json`, `runtime_sessions.json` (639 sessions) | 1.0 MB | `$AEB_WORKSPACE_ROOT/runs/campaigns/paper_v4_final_pipeline/paper_v4_gpu_final_locked_20260825/` |
| 3 sensor configs + 9 scenario suites + 22 campaign-generated sensor configs, with a SHA-256 table against `run_metadata.json` (34/34 match) | 0.2 MB | `configs/`, campaign `generated_sensor_configs/` |
| Environment capture + `ENVIRONMENT.md` (CARLA 0.9.11, Python 3.7.17, onnxruntime-gpu 1.14.1, CUDA 11.7 libs, cuDNN 8.9.7, driver 580.173.02, RTX 3050 Laptop 4 GB) | 15 kB | `docs/log/repeatability/environment_20260818/` + system inspection |
| Protocol, claim–evidence matrix, source map | 9 kB | `docs/log/PAPER_V4_EVALUATION_PROTOCOL.md`, `paper/paper_v5_1/` |
| `v7_same_lane` dataset definition and per-file SHA-256 (6,131 files, 1.87 GB; images **not** included) | 0.9 MB | `$AEB_WORKSPACE_ROOT/manifests/DESTINATION_SHA256SUMS.txt` |
| Model record: `yolo26n_aeb_v7.onnx` / `.pt`, `MODEL_CARD.md`, training `args.yaml`, `results.csv`, plots | 15.6 MB | `models/` (main checkout, untracked), `$AEB_WORKSPACE_ROOT/training/detect/yolo26n_aeb_20260619_011359/` |

Verification done while staging (details in the package `VERIFICATION.md`):
the raw archive matches its committed `.sha256` manifest
(`4d60f256…5b524`); all 47 files copied from the repository are
byte-identical to tag `paper-v5-scenario-severity-v1`; `paper_v5_derived`
matches its `SHA256SUMS.txt` (10/10); model hashes match the run metadata;
re-running `scripts/analyze_v5_review_metrics.py` on the packaged archive
reproduced the derived CSV/Markdown/PNG files byte-identically; secret scan
found nothing.

## Licensing — decision required

Zenodo allows one license per record, hence two records:

- **Record 1 (data)**: CC-BY-4.0 — logs, tables, configs, documentation.
- **Record 2 (model)**: AGPL-3.0 — the weights are fine-tuned from Ultralytics
  YOLO26n; the installed `ultralytics` 8.4.70 metadata says `License:
  AGPL-3.0` and the exported ONNX embeds the same license string.
- The GitHub repository has **no LICENSE file**. Choose one before (or with)
  the release; see `LICENSES.md` in the package.

If the authors prefer not to publish the weights, skip record 2; the paper
tables can still be re-derived from record 1, and the model is identified by
SHA-256.

## Upload steps

1. **Account.** Open <https://zenodo.org>, *Log in* → *Sign up/Log in with
   GitHub* or *ORCID*. Linking ORCID lets Zenodo fill creator identifiers.
   (Optional: practise first on <https://sandbox.zenodo.org>, which issues
   non-real DOIs.)
2. **Copy files to the computer with the browser**, e.g.
   `rsync -av navi-home:CARLA_0.9.11/aeb_workspace/releases/zenodo_paper_v5_2_upload/ ./zenodo_upload/`
   and verify: `cd zenodo_upload/record1_data && sha256sum -c SHA256SUMS`
   (same for `record2_model`).
3. **New upload (record 1).** Click *New upload*. Drag all files from
   `record1_data/` into the file area and wait until every upload shows 100 %.
4. **Reserve the DOI.** Under *Digital Object Identifier*, answer *No* to
   "Do you already have a DOI?" and click *Get a DOI now!*. Write the reserved
   DOI down (`10.5281/zenodo.NNNNNNN`); it is final once published.
5. **Metadata.** Fill the form from `.zenodo.json` in the package root:
   resource type *Dataset*; title; creators *Mai, Viet Hoang* and *Pham, Duc
   An* (affiliation Hanoi University of Science and Technology; add ORCID iDs;
   check name order/spelling); description (copy the HTML text); license
   *Creative Commons Attribution 4.0 International*; keywords; version `v5.2`;
   related works: *Is supplement to* `https://github.com/mvhoang92/aeb`
   (Software, URL) and *Is derived from* the tag URLs for
   `paper-v5-scenario-severity-v1` and `safe-fallback-eval-v1`. Do not upload
   the `.zenodo.json` file itself.
6. **Save draft → Preview.** Check that `README.md` renders, the zip is
   previewable and the license is right.
7. **Record 2 (model), optional.** Repeat steps 3–6 with `record2_model/` and
   `model_record/.zenodo.json`: resource type *Software* (or *Model* if
   offered), license *GNU Affero General Public License v3.0*. Add related
   work *Is supplement to* the record-1 DOI, and in record 1 add *Is
   supplemented by* the record-2 DOI (both DOIs are known after reservation).
8. **Publish.** Publishing is permanent: files cannot be replaced afterwards,
   only superseded by a new version (*New version* button, new DOI; the
   concept DOI always resolves to the latest version).

The public GitHub tags already exist on `origin`:
`safe-fallback-eval-v1`, `paper-v4-final-gpu-evidence-v1`,
`paper-v5-scenario-severity-v1`. The v5.2 work branch is not pushed yet; if
the release should cite a v5.2 tag, push that branch/tag first and add it as
another related identifier.

## After publication: where the DOI goes

1. **Manuscript.** Paper v5.2 defines the LaTeX macro `\artifactdoi`. Set it
   in both `paper/paper_v5_2/aeb_ieee_6page.tex` and
   `paper/paper_v5_2/aeb_ieee_6page_vi.tex` to the **version DOI** of record 1,
   e.g. `\newcommand{\artifactdoi}{10.5281/zenodo.NNNNNNN}`, rebuild with
   `build.sh`, run the v5.2 claim validator and refresh the paper's
   `SHA256SUMS.txt` (a new manuscript build, so record it in the paper
   changelog).
2. **This file.** Replace "staged locally, not uploaded" above with the
   record URLs and DOIs (data, model, concept DOI).
3. **Repository index.** Add the DOI to the paper v5.2 `README.md` /
   `SOURCE_MAP.md` and, if desired, a DOI badge in the root `README.md`
   (owned by the maintainers of those files).
4. Optional: add a `CITATION.cff` with the paper and the DOI.
