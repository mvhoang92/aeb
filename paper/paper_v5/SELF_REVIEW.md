# Paper v5 Final Self-Review

## Verdict

**Ready as a revised engineering-simulation paper.** No numeric inconsistency or
unqualified safety claim was found in the final audit. For a competitive ITS
venue, the remaining limitation is scientific scope/novelty rather than hidden
experimental error.

## Gates

- English PDF: exactly six IEEE pages including references.
- Vietnamese PDF: full structural parity, five pages, no missing glyphs.
- Both versions: 16 section/subsection headings, four tables, one figure, 14
  citation commands and all 15 bibliography entries cited.
- Scenario-level headline values regenerate from frozen logs.
- Severity values regenerate without adding/removing a CARLA run.
- Raw campaign/provider/model evidence remains immutable and checksummed.

## Residual limitations disclosed in the paper

1. One map, ego, fixed seed, favorable imaging and point-level CARLA radar.
2. Fourteen-condition adverse hold-out is small and deliberately constructed.
3. Synthetic ghosts falsify rule logic but do not estimate real multipath rate.
4. No learned/probabilistic or confidence-matched soft-fusion baseline.
5. No HIL, real sensor, weather/friction sweep, occupant-risk or following-vehicle model.
6. Last-tick pre-impact speed has 0.05-s discretization.

## Reviewer issue status

M1--M4, M7 and bilingual M8 are directly resolved. M5 is resolved by precise
scope and a registered future protocol, not by claiming broader robustness. M6
is resolved at the claim level by positioning the contribution as empirical;
additional fusion baselines remain necessary for a stronger algorithmic-paper
submission.
