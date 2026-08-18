# IEEE Paper Versions

Each submitted revision is isolated in its own directory. `paper_v1` is the
first complete bilingual manuscript; later revisions are created as new
directories rather than overwriting old source. `paper_v3` is the current
research-audited manuscript; hồ sơ nghiên cứu, phản biện, claim map và revision
notes được hợp nhất tại `paper_v3/HO_SO_NGHIEN_CUU_VA_PHAN_BIEN.md`.

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
cd paper/paper_v3
./build.sh
```

The script runs the required LaTeX and BibTeX passes, validates the English PDF
at six pages, and reports the Vietnamese review-PDF page count. It expects
`pdflatex`, `bibtex`, and `pdfinfo`. Figures are read from `report/assets/`; no
assets are duplicated in a paper version.
