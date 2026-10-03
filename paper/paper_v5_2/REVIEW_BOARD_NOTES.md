# Paper v5.1 Reviewer Board Notes

Generated from the `/review-paper-v51` multi-reviewer board run after creating
the paper-v5.1 reviewer agents. These notes are advisory review output, not
frozen scientific evidence and not a new CARLA campaign.

## Overall Chair Assessment

Decision before revision: **Major Revision nhẹ, không cần chạy CARLA mới**.

The board found that v5.1 is scientifically close to submission because it
already avoids the largest overclaims: no new fusion primitive, no deployment
readiness claim, named conditions as the statistical unit, adverse hold-out
framed as mechanism testing, and failures retained in evidence. Remaining issues
were mainly wording, artifact availability, and reviewer-facing clarity.

## Reviewer Verdicts

| Reviewer | Verdict | Confidence | Main concern |
|---|---|---|---|
| Novelty / related work | Weak Accept after minor fixes | High | Contribution is empirical and narrow; title/abstract could still sound broader than late brake permission. |
| Methodology | Major Revision nhẹ | High | `An unseen bench` could imply blind/unseen testing despite rule-aware hold-out design. |
| Statistics | Major Revision nhẹ | High | Wilson CI wording could be mistaken for population inference on a nonrandom constructed grid. |
| AEB control | Weak Accept | Medium-High | Explain nominal risk parameter `$a_e=8$` versus logged peak deceleration `9.02 m/s^2`. |
| Perception / fusion | Major Revision nhẹ | Medium-High | Explain car-only camera confirmation and why validation metrics are reported despite a test split. |
| Reproducibility | Weak Accept if artifact availability is clear | Medium | Clarify what is public, what is local, and what is referenced by hash/path policy. |
| Writing | Accept with Minor Revision | High | Abstract is dense; one ghost-severity sentence is hard to parse. |

## Blocking Issues Identified

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

## Required Revision Checklist

- Replace `An unseen bench exposes...` with non-blind hold-out wording.
- Add `car-only` to camera-gate framing early in the abstract/setup.
- Clarify validation metrics versus test split/audit role.
- Reword Wilson CI labels as descriptive ranges on a constructed grid.
- Add a sentence distinguishing nominal risk parameters from logged closed-loop
  peak deceleration.
- Add artifact availability text explaining public source/curated evidence versus
  large local artifacts and model files.

## Follow-Up Already Applied

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

## Final Status

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
