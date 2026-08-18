# Revision Notes

## Files

- `aeb_ieee_6page.tex`: English master manuscript.
- `aeb_ieee_6page_vi.tex`: Vietnamese review manuscript.
- `references.bib`: shared BibTeX database.
- `build.sh`: reproducible build command.

## paper_v2 narrative decisions

- Repositioned the manuscript around the agreed novelty: a closed-loop CARLA AEB
  engineering pipeline, not a new TTC formula, detector architecture, PID theory,
  or production-ready safety system.
- Made the main contributions explicit:
  1. object-level CARLA radar processing before braking;
  2. radar-first, camera-verified target validation through YOLO image-space
     association without online CARLA actor IDs or ground truth;
  3. path-aware TTC/stopping-distance risk assessment with staged PID braking;
  4. ODD-separated evaluation with retained failure cases.
- Corrected the final-evidence description: the 66-case aggregate consists of
  24 CCRm, 30 CCRb, and 12 cut-in cases. Clear-road, adjacent-lane, curve,
  cut-out, and multi-actor runs are treated as additional development checks,
  not part of the 63/66 aggregate result.
- Preserved the final evidence split: 38/38 intended-ODD passes, 25/28 stress
  passes, and 63/66 passes overall.

## Claims deliberately limited

- No NCAP certification, real-vehicle validation, real-time production claim,
  quantitative ablation, statistical reliability estimate, or transfer claim is
  made.
- The camera gate is described as semantic verification of a radar-selected
  target, not as range/velocity estimation or probabilistic multi-sensor fusion.
- Adjacent-lane, curved-road, and multi-actor observations are described only as
  configured checks, not as proof that one module quantitatively reduces false
  braking.

## Build and validation results

Built on 2026-08-17 with `pdflatex`, followed by BibTeX and two additional LaTeX
passes for each manuscript through `./build.sh`.

| Output | Pages | Validation |
|---|---:|---|
| `aeb_ieee_6page.pdf` | 6 | Required English page count satisfied; no undefined citations or references after final pass. |
| `aeb_ieee_6page_vi.pdf` | 6 | Vietnamese review copy built successfully; no page target is enforced. |

The English build retains the same negligible IEEE column-balancing warning
(`Overfull \\vbox` about 1.73 pt) as the previous version; it does not affect
references, citations, or the required six-page output.
