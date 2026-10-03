# Paper v5.2 Reviewer Board Notes

## Status for v5.2

No reviewer board has been run on the v5.2 manuscript. The repository has
only the v5.1 board (`/review-paper-v51`, commits `53628db` and `d7c39a1`),
whose notes are kept verbatim below as history. This file adds no new
reviewer comments. It records how the v5.2 text (as of the "Text revision"
step in `CHANGELOG.md`) handles the v5.1 board's required revisions, and which
items remain open. A v5.2 board run, if wanted, is an author decision.

## v5.1 required revisions, checked against the v5.2 text

| v5.1 board item | Where it stands in v5.2 |
|---|---|
| Hold-out wording must not imply a blind test | Kept: "frozen adverse mechanism hold-out", designed "with knowledge of the rule" (Sec. IV-A); Limits repeats that it tests mechanisms, not unbiased generalization |
| Car-only camera confirmation framing | Kept and moved earlier: the abstract opens with "A car-only camera detector..."; Fig. 1 caption says "car-only confirmation" |
| Validation vs. test split metrics | Kept: detector metrics are "validation metrics from model selection"; the test split is retained in the dataset audit (Sec. III-A) |
| Wilson intervals as descriptive ranges | Kept: Table II caption and Sec. IV-B call them descriptive intervals on the constructed grid |
| Nominal $a_e=8$ m/s$^2$ vs. logged peak deceleration | Kept: "Later peak decelerations are logged closed-loop outcomes, not constraints imposed by $a_e$" (Sec. III-B) |
| Artifact availability | Extended: repository URL plus `\artifactdoi` (Zenodo DOI placeholder), source map and hash/path policy for large artifacts |
| Optional: no mixed PASS/FAIL repeats | Kept and sharpened: repeats now "measure the determinism of the simulated pipeline, not run-to-run variability" |

## Changes in v5.2 that the v5.1 board did not see

- Exact two-sided McNemar p-values in Table III (paired outcomes), described
  as descriptive. The Limits subsection opens with "The conclusions rest on
  identified mechanisms, not statistical significance". Only core radar-only
  vs. fallback (0 vs. 8, p = 0.0078) is below 0.05.
- Fig. 1 (pipeline and permission rules) and Fig. 2 (median fallback ghost
  run vs. median hard-gate bench run from frozen tick logs). The v5 trade-off
  figure was removed.
- References 19 -> 31, all verified; pdfLaTeX English build; `\artifactdoi`;
  validator v5.2.
- Text revision: 178-word abstract without the core precision/recall trio,
  "late" defined as pipeline position, the +/-1.25-m path corridor named for
  the shared cut-out FN, and ghost medians stated next to Table IV.

## Open items before submission (from `SELF_REVIEW.md`, not board output)

- Small discordant counts and no multiplicity adjustment. The exact test is
  conservative, so the p-values remain descriptive.
- No estimate of run-to-run variability. Fig. 2 shows one run per mechanism.
- No matched soft-gate, class-agnostic, learned or probabilistic baseline.
- Fill `\artifactdoi` once the Zenodo DOI is minted, and re-check the status
  of the Akula et al. preprint.
- Author sign-off, venue template/page limit and supervisor review of the
  McNemar wording.

## Historical: Paper v5.1 Reviewer Board Notes (unchanged)

Generated from the `/review-paper-v51` multi-reviewer board run after creating
the paper-v5.1 reviewer agents. These notes are advisory review output, not
frozen scientific evidence and not a new CARLA campaign.

### Overall Chair Assessment

Decision before revision: **Major Revision nhẹ, không cần chạy CARLA mới**.

The board found that v5.1 is scientifically close to submission because it
already avoids the largest overclaims: no new fusion primitive, no deployment
readiness claim, named conditions as the statistical unit, adverse hold-out
framed as mechanism testing, and failures retained in evidence. Remaining issues
were mainly wording, artifact availability, and reviewer-facing clarity.

### Reviewer Verdicts

| Reviewer | Verdict | Confidence | Main concern |
|---|---|---|---|
| Novelty / related work | Weak Accept after minor fixes | High | Contribution is empirical and narrow; title/abstract could still sound broader than late brake permission. |
| Methodology | Major Revision nhẹ | High | `An unseen bench` could imply blind/unseen testing despite rule-aware hold-out design. |
| Statistics | Major Revision nhẹ | High | Wilson CI wording could be mistaken for population inference on a nonrandom constructed grid. |
| AEB control | Weak Accept | Medium-High | Explain nominal risk parameter `$a_e=8$` versus logged peak deceleration `9.02 m/s^2`. |
| Perception / fusion | Major Revision nhẹ | Medium-High | Explain car-only camera confirmation and why validation metrics are reported despite a test split. |
| Reproducibility | Weak Accept if artifact availability is clear | Medium | Clarify what is public, what is local, and what is referenced by hash/path policy. |
| Writing | Accept with Minor Revision | High | Abstract is dense; one ghost-severity sentence is hard to parse. |

### Blocking Issues Identified

1. Artifact availability needed a clearer statement. If raw archives or model
   artifacts are local rather than public, the manuscript/package should say so.
2. Hold-out wording should avoid implying a blind deployment test. Replace
   `unseen bench` with a wording such as `previously unused hold-out bench
   condition`.
3. Camera confirmation should be described as **car-only detector confirmation**,
   not generic camera verification.
4. The manuscript listed `1505/300/200` train/val/test images but reported only
   validation detector metrics. It should explain that those are validation
   metrics from model selection and that the test split remains an audit/split
   artifact unless test metrics are added.
5. Wilson intervals should be labelled as descriptive ranges/reference intervals
   on constructed named conditions, not inferential evidence for road prevalence.
6. The stopping-risk parameter `$a_e=8$ m/s^2` should be distinguished from
   realized closed-loop peak deceleration in severity logs.

### Required Revision Checklist

- Replace `An unseen bench exposes...` with non-blind hold-out wording.
- Add `car-only` to camera-gate framing early in the abstract/setup.
- Clarify validation metrics versus test split/audit role.
- Reword Wilson CI labels as descriptive ranges on a constructed grid.
- Add a sentence distinguishing nominal risk parameters from logged closed-loop
  peak deceleration.
- Add artifact availability text explaining public source/curated evidence versus
  large local artifacts and model files.

### Follow-Up Already Applied

The manuscript/package was revised after this review:

- `aeb_ieee_6page.tex`: car-only camera framing, hold-out bench wording,
  validation/test clarification, nominal-vs-logged deceleration sentence, Wilson
  range wording, artifact availability wording.
- `aeb_ieee_6page_vi.tex`: Vietnamese author copy synchronized with the same
  clarifications.
- `README.md`: artifact availability note added.
- PDFs rebuilt and `SHA256SUMS.txt` updated.

Verification after revision:

```text
./build.sh
PASS: English six-page draft and complete Vietnamese author-reading copy built.

/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/analysis/validate_v51_manuscript_claims.py
PASS: v5.1 primary/paired/extended/severity tables match frozen CSV; bilingual equations, citations and PDFs checked.
```

Residual note: the Vietnamese build emitted small TeX layout warnings
(`underfull hbox`, `overfull vbox` around 1--2 pt), but the validator passed and
the page budget remained six pages.

### Final Status

All six required revisions from the board are applied in both the English and
Vietnamese manuscripts. The optional consistency strengthening was also applied:
the paper now states that no named condition produced mixed PASS/FAIL outcomes
across its repeats. The package rebuilds to six pages and passes the frozen
claim-evidence validator.

Remaining work is external to the board and to this repository, not a blocker
identified by the reviewers:

- author sign-off and supervisor/venue review;
- plagiarism and formatting check by the target venue;
- optional future work (class-agnostic verification, soft gate, multi-map/weather
  sweep) that the paper already lists as out of scope.

With those caveats, v5.1 is technically complete against the reviewer board's
required-revision list.
