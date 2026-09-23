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

Do not classify algorithmic FAIL as a technical failure in campaign scripts.
CUDA provider mismatch and inference errors remain hard-stops for final
evidence. Generated paths use `AEB_WORKSPACE_ROOT`; run
`scripts/check_workspace.py` to inspect active dataset/log/output locations.
