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
