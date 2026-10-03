# v5.2 Change Log

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
