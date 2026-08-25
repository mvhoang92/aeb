# IEEE Paper Versions

Each submitted revision is isolated in its own directory. `paper_v1` is the
first complete bilingual manuscript; later revisions are created as new
directories rather than overwriting old source. `paper_v5` is the current
reviewer-driven manuscript; claim map, review response, source map, changelog và
structured self-review nằm trực tiếp trong `paper_v5/`. Paper v4 remains the
immutable first final-campaign manuscript.

The English manuscript is the master version. The Vietnamese manuscript has the
same claims, figures, tables, and references, and is provided for review.

## Mandatory bilingual-output rule

Every `paper_vN` must include and build both PDFs:

- `aeb_ieee_6page.pdf` --- English master manuscript;
- `aeb_ieee_6page_vi.pdf` --- Vietnamese review manuscript.

The version is incomplete if either PDF is missing, fails to compile, or has
unresolved citations/references. The English master must be exactly six pages.
The Vietnamese PDF is a full review copy: retain its original content and font,
and do not shorten it merely to meet a page target. Its `build.sh` must build
both manuscripts, and must fail when the English PDF is not six pages. Keep the
two source files and their shared BibTeX database in the same version directory.

## Build

```bash
cd paper/paper_v5
./build.sh
```

The script runs the required LaTeX/BibTeX passes, validates the English PDF at
six pages, and reports the Vietnamese review-PDF page count. It supports either
`pdflatex`+`bibtex` or Tectonic and requires `pdfinfo`. Final generated figures
are kept in `paper/paper_v5/figures/` and trace back to frozen logs through
`scripts/analyze_v5_review_metrics.py`.
