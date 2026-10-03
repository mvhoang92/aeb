# Paper v5.2 Source Map

## Manuscripts and build

- English: `aeb_ieee_6page.tex` / `aeb_ieee_6page.pdf` (pdfLaTeX, six pages).
- Vietnamese author copy: `aeb_ieee_6page_vi.tex` / `aeb_ieee_6page_vi.pdf`
  (XeLaTeX).
- Bibliography: `references.bib` (31 entries).
- Figures: `figures/pipeline_permission_policies.pdf`,
  `figures/timeseries_ghost_vs_bench.pdf` (byte copies of the derived figures).
- Build: `build.sh`.
- Validator: `../../scripts/analysis/validate_v52_manuscript_claims.py`
  (shim: `../../scripts/validate_v52_manuscript_claims.py`); tests:
  `../../tests/test_v52_analysis.py`.

## Frozen scientific sources (unchanged from v5.1)

- Protocol and thresholds: `../../docs/log/PAPER_V4_EVALUATION_PROTOCOL.md`.
- Final campaign narrative and per-condition outcomes:
  `../../docs/log/repeatability/paper_v4_gpu_final/` (`FINAL_GPU_EVIDENCE.md`,
  `scenario_consistency.csv`).
- Raw archive (SHA256 `4d60f2568a7049128db08d282699ada7b4cc28680dac47812fcabd465a85b524`,
  sidecar `.sha256`):
  `../../docs/log/repeatability/artifacts/paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz`.
- Derived scenario/severity tables: `../../docs/log/repeatability/paper_v5_derived/`
  (`../../scripts/analysis/analyze_v5_review_metrics.py`).

## New v5.2 derivations

| Output | Script | Inputs |
|---|---|---|
| `paper_v5_2_derived/paired_exact_mcnemar.{csv,json}` | `scripts/analysis/analyze_v52_paired_tests.py` | `paper_v4_gpu_final/scenario_consistency.csv`; cross-check `paper_v5_derived/named_paired_outcomes.csv` |
| `paper_v5_2_derived/figures/pipeline_permission_policies.pdf` | `scripts/analysis/plot_v52_figures.py` | Protocol thresholds (drawn, not computed) |
| `paper_v5_2_derived/figures/timeseries_ghost_vs_bench.pdf`, `timeseries_selected_runs.csv`, `timeseries_selection.json` | `scripts/analysis/plot_v52_figures.py` | Raw archive (read in place, SHA-verified); run selection from `false_brake_severity_runs.csv` and `collision_severity_runs.csv` |
| `paper_v5_2_derived/SHA256SUMS.txt` | both scripts | all files above |

## Main claim sources

| Manuscript claim | Source |
|---|---|
| 105 core and 14 hold-out named conditions; TP/FP/TN/FN/PASS/collision | `named_scenario_metrics.csv` |
| Paired policy outcomes (Table II counts) | `named_paired_outcomes.csv` |
| Table II exact McNemar p | `paired_exact_mcnemar.csv` |
| Bench/cart/warning pre-impact severity | `collision_severity_summary.csv` |
| Ghost duration, onset, deceleration and stop count | `false_brake_severity_runs.csv`, `false_brake_severity_summary.csv` |
| Fig. 2 traces | `timeseries_selected_runs.csv` (raw tick logs) |
| CUDA sessions, inference count, latency and errors | `FINAL_GPU_EVIDENCE.md`, campaign manifests/raw metadata |
| Detector and dataset metrics | `dataset_audit_v7_same_lane.json`, frozen runtime metadata |

## Text-revision evidence (wording clarifications)

| Statement | Source |
|---|---|
| Cut-out FN corridor (±1.25 m predicted path) | raw `cut_out_late_65_35_run_01.csv` (radar_only/hard_gate/safe_fallback regression jobs); frozen `config_snapshot/sensors.yaml` `brake.max_lateral_offset_m`; `core/radar_aeb_pipeline.py` `brake_lateral_limit`/`valid_path_target` |
| Cart: ≤2 radar points/frame on the predicted path, 0 clusters | hold-out `summary.json` `maximum_path_candidates`, `maximum_clusters`; `scripts/run_radar_aeb_scenarios.py` (`path_candidates = len(pipeline.candidate_points)`) |
| Ghost combinations (6/8/10-pt central, 8-pt at 0.50 m and 0.75 m) | hold-out `summary.json` and `fusion_fallback_holdout.yaml` scenario ids |
| Ghost medians 78.4 km/h / 3.60 s / 9.02 m/s² over 20 fallback runs | `false_brake_severity_runs.csv` (Table IV) |

## Bibliography verification (v5.2 additions)

| Key | Verified via |
|---|---|
| `cicchino2017effectiveness` | Crossref DOI 10.1016/j.aap.2016.11.009 |
| `coelingh2010collision` | Crossref DOI 10.1109/ITSC.2010.5625077 |
| `iso21448` | https://www.iso.org/standard/77490.html |
| `iso22839` | https://www.iso.org/standard/45339.html |
| `unr152` | EUR-Lex OJ L 360, 30.10.2020, pp. 66–89 (https://eur-lex.europa.eu/eli/reg/2020/1597/oj/eng); UNTS registration (entry into force 22 Jan 2020) |
| `nobis2019crfnet` | Crossref DOI 10.1109/SDF.2019.8916629 |
| `chadwick2019distant` | Crossref DOI 10.1109/ICRA.2019.8794312 |
| `riedmaier2020survey` | Crossref DOI 10.1109/ACCESS.2020.2993730 |
| `jha2019mlfi` | Crossref DOI 10.1109/DSN.2019.00025 |
| `wilson1927` | Crossref DOI 10.1080/01621459.1927.10502953 |
| `mcnemar1947` | Crossref DOI 10.1007/BF02295996 |
| `fagerland2013mcnemar` | Crossref DOI 10.1186/1471-2288-13-91 |
| `euroncap_aeb` (completed) | Official PDF title page, v4.2 June 2023 (cdn.euroncap.com) |

Entries inherited from v5.1 were not re-verified in v5.2.

## Literature positioning

Related work cites radar–vision AEB target selection (Kim and Song; Hsu et
al.; Zhang et al.), learned radar–camera detection (CRF-Net, Chadwick et al.,
CenterFusion), verification-oriented AEB (Akula et al., discussed as a nearby
method, not a numerical baseline), simulation/scenario-based assessment
(Riedmaier et al.; Gómez-Huélamo et al.; Rao et al.), radar ghosts and fault
injection (Kraus et al.; Jha et al.), probabilistic threat/existence work
(Sandblom and Brännström; Lindenmaier et al.) and standards/regulation
(ISO 15623, ISO 22839, ISO 21448, UN R152, Euro NCAP) only as scope boundaries.
