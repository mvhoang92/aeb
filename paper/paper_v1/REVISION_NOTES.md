# Revision Notes

## Files

- `aeb_ieee_6page.tex`: English master manuscript.
- `aeb_ieee_6page_vi.tex`: Vietnamese review manuscript.
- `references.bib`: shared BibTeX database.
- `build.sh`: reproducible build command.

## Narrative and technical corrections

- Reframed the paper as an engineering-system study, not a claim of a novel or
  production-ready AEB algorithm.
- Described perception as radar-first target selection with geometric camera
  verification; range, relative velocity, TTC, and track state remain radar
  quantities.
- Distinguished the supervisory AEB states (`NORMAL`, `WARNING`, `BRAKE`,
  `RELEASE`) from staged brake-command limits.
- Preserved the final evidence split: 38/38 intended-range passes, 25/28
  boundary-test passes, and 63/66 passes overall.

## Claims deliberately limited

- No NCAP certification, real-vehicle validation, real-time claim, quantitative
  ablation, or statistical comparison is claimed.
- Adjacent-lane and curved-road observations are reported as configured-case
  outcomes rather than proof that a component reduces false braking.

## Build and validation results

Built on 2026-08-15 with `pdflatex`, followed by BibTeX and two additional
LaTeX passes for each manuscript.

| Output | Pages | Validation |
|---|---:|---|
| `aeb_ieee_6page.pdf` | 6 | No undefined citations or references; embedded fonts checked. |
| `aeb_ieee_6page_vi.pdf` | Review copy | Full Vietnamese content and its T5/Times font are retained; no page target is applied. |

The English PDF page thumbnails were also inspected. The English build retains one negligible 1.73-pt page-output warning from
IEEE column balancing; it does not affect content, references, or the rendered
layout.
