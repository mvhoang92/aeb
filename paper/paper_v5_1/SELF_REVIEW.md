# Paper v5.1 Self-Review

## Recommendation

**Ready for supervisor review and submission screening as an empirical
simulation paper.** It should be submitted to a venue whose scope accepts
CARLA/ADAS evaluation, verification or failure analysis. It should not be
presented as a new perception-fusion algorithm.

## Strengths

1. The research question is narrow: what changes when only the late
   brake-permission policy changes?
2. All three policies share radar processing, risk equations, controller,
   scenario harness and scoring.
3. Named conditions, not repeated runs, are the primary descriptive unit.
4. The paper retains adverse outcomes and separates track, permission and
   stopping failures.
5. Severity metrics prevent a brake TP or collision count from being treated as
   a complete safety outcome.
6. The evidence is traceable to a frozen CUDA campaign and derived CSV files.

## Main reviewer risks

- Algorithmic novelty is limited; the manuscript states this directly.
- The hold-out is designed and was created with knowledge of the fallback rule.
- The CARLA radar is point-level and does not model real multipath prevalence.
- One map, one ego platform, one fixed seed and one-class in-domain imagery
  limit external validity.
- There is no matched class-agnostic verification, soft gate, learned fusion
  or probabilistic existence baseline.
- Severity values are kinematic proxies, not injury or secondary-crash risk.
- The nearby Akula et al. preprint must be acknowledged, but its real-vehicle
  edge-density results must not be presented as a direct numerical baseline.

## Claims checked

- No first/new-fusion claim.
- No dominance claim for fallback.
- Synthetic returns are called synthetic fault injection.
- Repetitions are consistency measurements.
- Hold-out is called a frozen adverse mechanism hold-out.
- CUDA mismatch/inference error is a technical hard stop.
- Algorithmic FAIL is retained.
- No road prevalence, real-time ECU, HIL, vehicle, NCAP or functional-safety
  claim.

## Required author checks before submission

- Confirm author names, affiliation, email and venue template.
- Confirm that the selected venue permits a six-page IEEE-style manuscript.
- Check citation style and any policy on preprints.
- Decide whether the GitHub repository and artifact archive can be public under
  the relevant CARLA/model/data licenses.
- Have the supervisor review the title, novelty paragraph and hold-out wording.
- Do not edit frozen v5 or report v3 in order to make v5.1 appear consistent;
  v5.1 has its own source map and validator.
