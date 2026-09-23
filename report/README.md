# Report Index

## Current frozen report

Report v3 is the current project report and must not be edited in place:

- `report_v3.md`
- `chapters_v3/`
- `exports/aeb_report_v3.docx`
- `exports/aeb_report_v3.pdf`
- `exports/aeb_report_v3.SHA256SUMS.txt`

Build helpers are retained for reproducibility:

```bash
/usr/bin/python3 report/build_report_v3.py
/usr/bin/python3 report/export_report_v3.py
```

`export_report_v3.py` uses `templates/aeb_report_template_v3.docx`. Rebuilding
is a verification operation; changes for a future algorithm belong in a new
report generation rather than overwriting v3.

## Supporting material

- `assets/`: report diagrams and curated evidence images.
- `exports/generated_images/`: generated report illustrations.
- `presentation/`: project slide deck and outline.
- `templates/`: local/report export templates.

## Historical material

- `archive/legacy/`: report v1/v2, mini report, old chapters and builder.
- `archive/validation/`: report-v3 page renders and text extraction used for
  layout QA.

The architecture-only refactor is documented in
`REFACTOR_AND_STRUCTURE_ADDENDUM.md`; it does not replace scientific report v3.
