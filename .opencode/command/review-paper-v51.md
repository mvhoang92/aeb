---
description: Runs a multi-model reviewer board for paper_v5_1 and asks the chair to synthesize the decision.
agent: general
---

Run a full multi-reviewer board for `paper/paper_v5_1`.

Use the project subagents below. Invoke the seven specialist reviewers first, ideally in parallel. Then invoke `paper-v51-chair` with the collected reviewer reports and ask it to synthesize an editorial decision.

Specialist reviewers:

- `paper-v51-novelty-reviewer`
- `paper-v51-methodology-reviewer`
- `paper-v51-statistics-reviewer`
- `paper-v51-aeb-control-reviewer`
- `paper-v51-perception-fusion-reviewer`
- `paper-v51-reproducibility-reviewer`
- `paper-v51-writing-reviewer`

Chair:

- `paper-v51-chair`

Core documents to review:

- `paper/paper_v5_1/aeb_ieee_6page.tex`
- `paper/paper_v5_1/aeb_ieee_6page_vi.tex`
- `paper/paper_v5_1/CLAIM_EVIDENCE_MATRIX.md`
- `paper/paper_v5_1/SOURCE_MAP.md`
- `paper/paper_v5_1/REVIEW_RESPONSE.md`
- `paper/paper_v5_1/SELF_REVIEW.md`
- `paper/paper_v5_1/AUTHOR_READING_GUIDE_VI.md`
- `docs/log/PAPER_V4_EVALUATION_PROTOCOL.md`
- `docs/log/repeatability/paper_v4_gpu_final/FINAL_GPU_EVIDENCE.md`
- `docs/log/repeatability/paper_v5_derived/`

Reviewer-output requirements:

- Write in Vietnamese.
- Quote exact English manuscript phrases when they need revision.
- Do not edit files.
- Separate major concerns from minor concerns.
- Assign a verdict and confidence.
- Prefer fixes feasible within a six-page IEEE paper.
- Do not demand new CARLA runs unless a claim is otherwise indefensible.

Final output to the user:

1. A compact table of reviewer verdicts and confidence.
2. The chair meta-review.
3. Top blocking issues ordered by severity.
4. Required revision checklist.
5. Optional improvements.
6. Safe-to-submit checklist.

Additional user request, if any: `$ARGUMENTS`
