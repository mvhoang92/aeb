# Paper v5.2 Self-Review

## Recommendation

**Ready for supervisor review and submission screening as an empirical
simulation paper**, with the open items below. Submit to a venue whose scope
accepts CARLA/ADAS evaluation, verification or failure analysis; do not
present it as a new perception-fusion algorithm.

## What changed relative to v5.1

1. English master builds with standard IEEEtran/pdfLaTeX (true small-caps
   headings); Vietnamese copy stays on XeLaTeX with free font fallback.
2. Bibliography 19 -> 31 verified entries (standards/regulation, SOTIF,
   learned radar–camera detection, scenario-based assessment, AV fault
   injection, AEB field effectiveness, Wilson, McNemar, Fagerland et al.).
   Related Work ends with an explicit positioning sentence.
3. Table II gains exact two-sided McNemar p-values computed by a committed
   script from frozen evidence, framed as descriptive on a constructed grid.
4. New Fig. 1 (pipeline and where each policy grants/denies permission) and
   Fig. 2 (median fallback ghost run vs. median hard-gate bench run). The v5
   trade-off figure, which duplicated Table I, was removed.
5. `\artifactdoi` macro for the future Zenodo DOI.
6. New v5.2 validator, shim and unit tests.

7. Text revision: shorter abstract (178 words), explicit
   mechanisms-not-significance limitation, repeats framed as determinism
   checks, and six ambiguous phrases rewritten from frozen configs/logs.

## Strengths (unchanged)

Narrow research question; shared upstream pipeline; named conditions as the
unit; adverse outcomes retained; severity beyond binary metrics; full
traceability to a frozen CUDA campaign.

## Remaining weaknesses / reviewer risks

- Algorithmic novelty is limited; stated directly.
- The hold-out was designed with knowledge of the fallback rule.
- Small discordant counts: only one of six paired contrasts has p<0.05, and no
  multiplicity adjustment is applied; the exact conditional test is
  conservative (Fagerland et al. recommend mid-p), so p-values are reported
  only as descriptive.
- The study has no estimate of run-to-run variability: repeats were
  deterministic, so sensor noise and seed variation remain untested.
- The abstract now omits the core precision/recall trio; reviewers looking
  for headline rates must go to Table I.
- Fig. 2 shows one run per mechanism; repeats are deterministic in the
  descriptors used for selection, so the figure illustrates mechanism, not
  variability.
- Point-level CARLA radar, one map, one ego platform, one seed, one-class
  in-domain imagery; no matched class-agnostic, soft-gate, learned or
  probabilistic baseline.
- Severity values are kinematic proxies, not injury or secondary-crash risk.
- English page budget is tight (six full pages); any further addition needs
  an equivalent cut.
- The Akula et al. preprint (arXiv 2606.27556) is inherited from v5.1; its
  status should be re-checked before submission.
- `REVIEW_RESPONSE.md`, `REVIEW_BOARD_NOTES.md` and
  `AUTHOR_READING_GUIDE_VI.md` now describe v5.2, including the McNemar
  column and the new figures. They keep the v5.1 content as marked history;
  no reviewer board has been run on v5.2.

## Claims checked

- No first/new-fusion claim; no dominance claim for fallback.
- Synthetic returns called synthetic fault injection.
- Repetitions are consistency measurements; McNemar uses named conditions only.
- Hold-out called a frozen adverse mechanism hold-out.
- No road prevalence, real-time ECU, HIL, vehicle, NCAP, UN R152, ISO or
  functional-safety/SOTIF claim.

## Required author checks before submission

- Confirm authors, affiliation, email and venue template/page limit.
- Fill `\artifactdoi` with the minted Zenodo DOI (both `.tex` files).
- Decide whether to tag v5.2 as a frozen version.
- Decide whether the venue accepts the UN R152/ISO/Euro NCAP `@misc` style.
- Supervisor review of title, novelty paragraph and McNemar wording.
