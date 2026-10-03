# v5.2 Review Response Outline

This outline is for supervisor/venue review. It does not claim that all
reviewer objections are experimentally solved.

**Source of the concerns.** No external or board review has been run on the
v5.2 text yet. The rows below are *anticipated* concerns: the v5.1 outline
(kept verbatim at the end as history), the v5.1 reviewer-board findings
(`REVIEW_BOARD_NOTES.md`) and the v5.2 self-review (`SELF_REVIEW.md`). They
are not reviewer comments on v5.2. The responses describe the v5.2 text as
revised by the "Text revision (abstract, limits, wording)" step in
`CHANGELOG.md`.

## What changed relative to v5.1

No CARLA run was added, removed or retuned. All new numbers and figures come
from committed scripts reading frozen evidence.

- **Build:** the English master uses standard IEEEtran with pdfLaTeX
  (Times via `newtx`, true small-caps headings) instead of XeLaTeX/fontspec.
  The Vietnamese author copy stays on XeLaTeX and is not page-capped.
- **References:** 19 -> 31 entries, each checked (see `SOURCE_MAP.md`).
- **Table III (paired outcomes):** new column with the exact two-sided
  McNemar p-value on discordant named conditions
  (`scripts/analysis/analyze_v52_paired_tests.py` ->
  `docs/log/repeatability/paper_v5_2_derived/paired_exact_mcnemar.csv`).
- **Figures:** Fig. 1 is a new pipeline diagram (where each policy grants or
  denies the radar request). Fig. 2 is a new tick-log time series (median
  fallback ghost run vs. median hard-gate bench run). The v5 scenario-level
  trade-off figure, which repeated Table II numbers, was removed.
- **`\artifactdoi`:** one macro in each `.tex` holds the Zenodo DOI,
  currently "DOI to be assigned (Zenodo)".
- **Validator:** `scripts/validate_v52_manuscript_claims.py` checks the tables
  against frozen CSV, recomputes the McNemar column, checks bilingual parity,
  derived-evidence checksums, the macro and the six-page English budget.
- **Text revision:** the abstract is 178 words and keeps only the story
  numbers. "Late" means position in the pipeline ("delayed permission" for
  timing). Repeats are described as measuring determinism. The shared
  cut-out FN names the +/-1.25-m predicted-path corridor. A McNemar
  limitation sentence opens the Limits subsection.

## Anticipated concerns and v5.2 responses

| Likely concern | Response in v5.2 | Remaining boundary |
|---|---|---|
| Camera/radar fusion is established | Unchanged from v5.1: no new fusion primitive is claimed. Related Work now cites learned radar–camera detectors (CRF-Net, distant-vehicle detection, CenterFusion) and ends with an explicit positioning sentence | The contribution is an empirical comparison |
| Why is fallback not radar-only? | Equations (3)–(5) and Fig. 1 show where each policy grants or denies $B_r$; fallback needs camera confirmation or the stricter $E_r$ | The same radar track can still be a ghost |
| Are the paired differences statistically significant? | Table III reports exact two-sided McNemar p-values next to the discordant counts. Only 1 of 6 contrasts is below 0.05 (core radar-only vs. fallback, 0 vs. 8, p = 0.0078). The Limits subsection opens by saying the conclusions rest on mechanisms, not significance | Constructed grid, at most ten discordant conditions per pair, no multiplicity adjustment; the exact conditional test is conservative (mid-p not used) |
| Are repeated runs independent samples? | No. Named conditions are the unit. No condition had mixed PASS/FAIL repeats, so repeats are reported as measuring the determinism of the simulated pipeline | Run-to-run variability (sensor noise, seeds) is not estimated |
| What does "late" permission mean? | Its position at the end of the pipeline. The temporal sense is now called "delayed (fallback) permission" | — |
| Why does a shared core FN exist? | The late cut-out target's radar returns leave the +/-1.25-m predicted-path corridor (`brake.max_lateral_offset_m`) before the brake threshold. All three policies share this miss | It is a path-prediction limit, not a camera veto |
| Is the hold-out truly blind? | Unchanged: frozen adverse mechanism hold-out, designed with rule knowledge; post-hoc derivation disclosed | Not an unbiased deployment test |
| Does fallback dominate hard gating? | No. The core and hold-out orderings differ, and Fig. 2 shows both costs: a fallback ghost full stop and a hard-gate bench impact | No universal policy recommendation |
| Is a synthetic ghost a real radar ghost? | No. It is synthetic fault injection; Fig. 2a shows the injected six-point track qualifying at 0.15 s | Real multipath prevalence is not estimated |
| Do the figures cherry-pick runs? | Fig. 2 uses a fixed rule: the run whose severity descriptors equal the policy median, with the lowest scenario/run identifier on ties (15/20 ghost and 5/5 bench runs tie). The selection is recorded in `paper_v5_2_derived/figures/timeseries_selection.json` | One run per mechanism shows the mechanism, not variability |
| Is this a new probabilistic AEB? | No. Probabilistic threat/existence work is cited; fallback is a deterministic rule | A probabilistic method needs a new protocol and hold-out |
| Does CUDA prove real-time operation? | No. Unchanged host ONNX timing with its scope and exclusions | No ECU, HIL or actuator-deadline claim |
| Where are the artifacts? | Source, manuscript, checksums and curated evidence are in the repository. The archive is cited through `\artifactdoi` and prepared as a Zenodo package (data CC-BY-4.0, model AGPL-3.0) | The DOI is not minted yet; the macro must be filled before submission |
| Are the references real? | 31 entries, each verified against Crossref/DOI metadata or the official publisher or standards page (`SOURCE_MAP.md`) | The Akula et al. preprint status must be re-checked before submission |
| Headline precision/recall missing from the abstract? | Intentional (178-word abstract). The core rates are in Table II and Sec. V-A | Reviewers must read Table II for headline rates |

## Historical: v5.1 review response outline (unchanged)

The table below is the v5.1 outline, kept verbatim for traceability. Table
and section references in it point to the v5.1 manuscript.

| Likely concern | Response in v5.1 | Remaining boundary |
|---|---|---|
| Camera/radar fusion is established | Agreed; the paper explicitly disclaims a new fusion primitive and isolates late brake permission | Contribution is empirical comparison |
| Why is fallback not radar-only? | Equations and text show fallback requires camera confirmation or a stricter emergency condition | Same radar track can still be a ghost |
| Why not report only precision/recall? | Paired conditions, collision status, braking onset and severity are added | Severity remains kinematic, not injury risk |
| Are repeated runs independent samples? | Named condition is the primary unit; repeats assess consistency | Grid is constructed and not prevalence representative |
| Is the hold-out truly blind? | It is labelled a frozen adverse mechanism hold-out; rule knowledge and post-hoc derivation are disclosed | It is not an unbiased deployment test |
| Does fallback dominate hard gating? | No. Core and hold-out produce different orderings; the manuscript reports both | No universal policy recommendation |
| Is a synthetic ghost a real radar ghost? | No. It is explicitly synthetic fault injection, motivated by ghost failure mechanisms | Real multipath prevalence is not estimated |
| Is this a new probabilistic AEB? | No. Existing probabilistic threat/existence work is cited; current fallback is deterministic | A probabilistic method would need a new protocol and hold-out |
| Does CUDA prove real-time operation? | No. Host ONNX timing is reported with its scope and exclusions | No ECU, HIL or actuator deadline claim |
