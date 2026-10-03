# Script Taxonomy

Historical root-level commands remain supported.  Thin wrappers delegate to
categorized implementations where moving the implementation is safe.

| Category | Location | Purpose |
|---|---|---|
| Scenario runtime | `run_radar_aeb_scenarios.py`, `run_fusion_aeb_scenarios.py` | Stable evidence-facing CARLA CLIs; intentionally kept at historical paths |
| Campaign | `campaign/` | Campaign orchestration, isolated final pipeline, video/smoke tooling and suite generation |
| Analysis | `analysis/` | Frozen-evidence analysis, repeatability summaries, plots and manuscript validators |
| Dataset | `dataset/` | Collection, label audit/cleanup and visualization |
| Training | `training/` | Model training and ONNX export |
| Maintenance | `maintenance/` | Sensor visualization and one-off repository tools |

For example, `scripts/run_v4_campaign.py` is a compatibility wrapper around
`scripts/campaign/run_v4_campaign.py`. External automation should continue to
use the historical path until a versioned CLI migration is announced.

Manuscript claim validators keep stable root-level wrappers:
`validate_v4_manuscript_claims.py`, `validate_v5_manuscript_claims.py`,
`validate_v51_manuscript_claims.py` and `validate_v52_manuscript_claims.py`
(each delegates to `analysis/`). Paper v5.2 derivations live in
`analysis/analyze_v52_paired_tests.py` and `analysis/plot_v52_figures.py`.

Do not classify algorithmic FAIL as a technical failure in campaign scripts.
CUDA provider mismatch and inference errors remain hard-stops for final
evidence. `run_fusion_aeb_scenarios.py` re-executes itself once with the CUDA
library dirs on `LD_LIBRARY_PATH` (`AEB_CUDA_LIBRARY_PATH`, else
`/usr/local/cuda-11.7/lib64`) and probes `CUDAExecutionProvider` in a
subprocess; a failed probe exits with code 3 (technical hard-stop), never 1
(algorithm FAIL). `run_metadata.json` records the result under
`runtime_environment`. Generated paths use `AEB_WORKSPACE_ROOT`; run
`scripts/check_workspace.py` to inspect active dataset/log/output locations.

`scripts/doctor.py` (wrapper around `maintenance/doctor.py`) prints one
`OK`/`WARN`/`FAIL` line per prerequisite: Git branch/dirty state, workspace
(reusing `check_workspace.collect_status`), launcher prerequisites (reusing
`ui.launcher.config.check_prerequisites`, the `launcher.py --check` logic),
model files against `docs/log/repeatability/environment_20260818/model_sha256.txt`,
a CUDA ONNX Runtime probe in a subprocess via `infrastructure/cuda_runtime.py`,
free GPU memory (`nvidia-smi`, optional) and whether the CARLA port is
listening (local hosts are looked up in the socket table; no connection is
made). It exits 0 unless a check FAILs; `--skip-cuda-probe` and
`--sensor-config` adjust the CUDA/model checks.
