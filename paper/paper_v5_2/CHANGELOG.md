# v5.2 Change Log

## Text revision (abstract, limits, wording)

- Abstract rewritten from 209 to 178 words (whitespace-delimited). Kept
  only the story numbers: 105/14 conditions, hold-out 11/14 vs 7/14, and
  bench last-tick speeds 32.57/54.93/59.95 km/h. Moved to the body: the core
  precision/recall trio (Table II), eight edge-prop false brakes, four ghost
  conditions, "all 20 fallback ghost runs stop" and the medians 78.4 km/h,
  3.60 s and 9.02 m/s^2 (new sentence by Table IV), and the 2,461-run campaign
  size (Sec. IV). The closing scope sentence is unchanged.
- Limits: the conclusions rest on identified mechanisms, not statistical
  significance; only 1 of 6 exact McNemar contrasts (core radar-only vs.
  fallback, 0 vs. 8, p=0.0078) is below 0.05. The p<0.05 sentence in
  Results now points to this subsection.
- Repeats: they measure determinism of the simulated pipeline (no mixed
  outcomes), not run-to-run variability; sensor-noise and seed variation are
  future work.
- Ambiguities resolved from frozen configs/logs: "late" = pipeline position,
  with "delayed (fallback) permission" for the temporal sense; the shared
  cut-out FN leaves the +/-1.25 m predicted-path corridor
  (`brake.max_lateral_offset_m`, frozen `config_snapshot/sensors.yaml`) before
  the brake threshold; the ghost combinations are named; the cart has at most
  two radar points per frame passing the range/height/path filter and no
  cluster; ghost severity values are stated as medians; TTC and margin must
  both hold.
- To stay at six pages, EN drops: "The intended benefit is selective
  recovery..." (Intro), "It demonstrates mitigation hidden by a binary
  collision count." (warning prop), the sentence listing what the ghost rows
  report (replaced by the new median sentence), and "Repeats are correlated,"
  (now covered by the determinism sentence). The Vietnamese copy is synced
  for every content change but not shortened.
- The v5.2 validator now checks the abstract's story numbers, the EN
  abstract length (150-185 words) and closing sentence, and that each moved
  or clarified statement is present in the body of both languages.

## Gates and package documentation

- New validator `scripts/analysis/validate_v52_manuscript_claims.py` (shim
  `scripts/validate_v52_manuscript_claims.py`): tables vs. frozen CSV, McNemar
  column vs. the recomputed derivation, bilingual equation/citation/figure/
  table parity, derived-evidence checksums, `\artifactdoi`, ASCII-only
  English source, PDFs present and English PDF at most six pages.
- `tests/test_v52_analysis.py` covers the McNemar computation and checks that
  the validator rejects altered values and unbalanced citations.
- README, CLAIM_EVIDENCE_MATRIX, SOURCE_MAP (incl. per-reference
  verification), SELF_REVIEW and SHA256SUMS rewritten for v5.2;
  `paper/CURRENT.md` and `paper/README.md` name v5.2 as the submission draft
  (v5 remains the latest frozen version).

## Artifact availability DOI placeholder

- Both sources define `\newcommand{\artifactdoi}{\textit{DOI to be assigned (Zenodo)}}`
  and the artifact-availability paragraph now states that the package is
  archived at `\artifactdoi`. Replace the macro body with the minted Zenodo
  DOI once the archive exists; no other text needs to change.

## Figures: pipeline diagram and failure time series

- New committed script `scripts/analysis/plot_v52_figures.py` (vector PDF,
  reproducible bytes) writes to `docs/log/repeatability/paper_v5_2_derived/figures/`
  and copies the PDFs into `paper_v5_2/figures/`:
  - `pipeline_permission_policies.pdf` (Fig. 1): shared radar chain, car-only
    camera confirmation, the three permission rules (where each grants or
    denies $B_r$), the emergency condition $E_r$ and the staged PID brake;
  - `timeseries_ghost_vs_bench.pdf` (Fig. 2): speed, radar TTC and brake
    command for one fallback synthetic-ghost run (false full stop) and one
    hard-gate hold-out bench run (vetoed request, impact). The raw-log archive
    SHA256 is verified against its sidecar first; tick CSVs are read directly
    from the archive (nothing extracted into the repository). Selection rule:
    run whose severity descriptors equal the policy median, lowest
    scenario/run identifier on ties (15/20 ghost and 5/5 bench runs tie).
    Traces and the selection record are kept as `timeseries_selected_runs.csv`
    and `timeseries_selection.json`.
- Removed the v5 `scenario_level_tradeoff.png` figure (a double-column figure
  that duplicated the Table II numbers) from the v5.2 manuscript to make room; it
  remains in `paper_v5_derived/figures/` and in v5/v5.1.
- Text tightened to stay at six pages (EN only; the VI author copy is not
  shortened): merged the two "contributions are empirical" sentences, removed
  the repeated provenance sentence in Computation/reproducibility and the last
  sentence of the RQ1--RQ3 discussion paragraph.
- Vietnamese copy: same figures/captions; `\balance` removed because the
  uncapped copy now runs to seven pages and balancing produced an 11-pt
  overfull vbox. `build.sh` now also fails on overfull vboxes > 1 pt.

## Exact paired McNemar tests

- New script `scripts/analysis/analyze_v52_paired_tests.py` recomputes the
  named-condition 2x2 paired PASS tables from
  `paper_v4_gpu_final/scenario_consistency.csv`, cross-checks them against the
  frozen `paper_v5_derived/named_paired_outcomes.csv`, and adds the exact
  two-sided McNemar p-value (conditional binomial on discordant pairs).
  Outputs: `docs/log/repeatability/paper_v5_2_derived/paired_exact_mcnemar.{csv,json}`
  with `SHA256SUMS.txt`.
- Table III (paired outcomes) gains a `p` column; the analysis section frames it as descriptive
  on a constructed grid (discordant counts shown, no multiplicity adjustment,
  no population inference). References 29 -> 31 (McNemar 1947; Fagerland et
  al. 2013). Vietnamese copy synchronized. EN remains six pages.

## References: 19 -> 29 verified entries

Added (each checked against Crossref DOI metadata or the official
publisher/standards page): Cicchino (2017) AEB field effectiveness;
Coelingh et al. (2010) production AEB; ISO 21448:2022 SOTIF;
Nobis et al. (2019) CRF-Net; Chadwick et al. (2019) radar--vision distant
vehicle detection; Riedmaier et al. (2020) scenario-based assessment survey;
Jha et al. (2019) ML-based fault injection; ISO 22839:2013 FVCMS;
UN Regulation No. 152 (AEBS M1/N1); Wilson (1927) score interval. The
Euro NCAP entry now carries its exact title, version/date and official URL.
Related Work ends with an explicit positioning sentence: a controlled
empirical comparison of late brake-permission policies, not a new fusion
primitive. Vietnamese copy synchronized.

## Build: English master on standard pdfLaTeX

- The v5.1 English source used `fontspec` + Times New Roman under XeLaTeX.
  That font has no small-caps shape (`TU/TimesNewRoman(0)/m/sc undefined`),
  so IEEE section headings lost their small caps. The English master now uses
  standard IEEEtran with pdfLaTeX, `[T1]{fontenc}` and `newtxtext/newtxmath`
  (Times). The source contained no non-ASCII characters to replace;
  `amssymb` was dropped because `newtxmath` provides the symbols.
- The Vietnamese author copy stays on XeLaTeX/fontspec. It uses Times New
  Roman/Arial when installed and the metric-compatible TeX Gyre Termes /
  Liberation Sans otherwise, so it builds on machines without Microsoft fonts.
- `build.sh` builds EN with pdfLaTeX and VI with XeLaTeX, and fails on
  unresolved citations/references, missing glyphs, font-shape substitution
  (except the IEEEtran class-load `TU/ptm` notices under XeLaTeX, which
  typeset no text), overfull boxes wider than 1 pt, or an English PDF that is
  not six pages.
- Page count: EN 6 -> 6 (v5.1 PDF was six pages; the pdfLaTeX build leaves
  roughly half of page six free). VI: 6 pages.

## Compared with paper v5.1 (scaffold)

- `paper_v5_2/` created as a byte-for-byte copy of the tracked v5.1 package
  (sources, PDFs, figure, bibliography and review notes). No content change in
  this step; each later v5.2 revision adds its own section above this one.
- `paper_v5_1/` remains unchanged as the reference draft.

# v5.1 Change Log

## Compared with paper v5

- New title and framing: the object of comparison is the late brake-permission
  policy, not a claim of a new fusion detector.
- Reorganized the six-page narrative around three research questions:
  condition-level policy changes, surviving failure mechanisms, and information
  hidden by binary metrics.
- Added direct positioning against radar-guided camera verification,
  non-standard AEB corner-case testing, radar-ghost datasets, probabilistic
  threat assessment and Bayesian existence tracking.
- Added a paired named-condition table to make policy-only PASS differences
  explicit.
- Added the Boolean permission ordering and clarified why its closed-loop
  outcomes are not necessarily nested after different braking histories.
- Clarified labels: a non-vehicle physical hazard can be positive even when
  outside the one-class detector label space; a synthetic ghost is negative
  despite a stable radar track.
- Strengthened the distinction between missing radar track, camera semantic
  veto, late fallback qualification, and collision despite brake permission.
- Added explicit post-hoc/frozen-evidence and provenance language.
- Added a complete Vietnamese author-reading copy with matching tables,
  equations, citations and claims.

## Unchanged

- No CARLA run was added, removed or retuned.
- Policy thresholds, model, scenarios, labels and frozen hold-out remain those
  of `safe-fallback-eval-v1`.
- Report v3, paper v5, tags and curated evidence remain untouched.
- New v5.1 tables are derived from `paper_v5_derived/` CSV files.
