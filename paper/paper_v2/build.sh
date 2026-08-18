#!/usr/bin/env bash
set -euo pipefail

pdflatex -interaction=nonstopmode -halt-on-error aeb_ieee_6page.tex
bibtex aeb_ieee_6page
pdflatex -interaction=nonstopmode -halt-on-error aeb_ieee_6page.tex
pdflatex -interaction=nonstopmode -halt-on-error aeb_ieee_6page.tex

pdflatex -interaction=nonstopmode -halt-on-error aeb_ieee_6page_vi.tex
bibtex aeb_ieee_6page_vi
pdflatex -interaction=nonstopmode -halt-on-error aeb_ieee_6page_vi.tex
pdflatex -interaction=nonstopmode -halt-on-error aeb_ieee_6page_vi.tex

english_page_count=$(pdfinfo aeb_ieee_6page.pdf | awk '/^Pages:/ {print $2}')
if [[ "$english_page_count" != "6" ]]; then
  echo "Build failed: aeb_ieee_6page.pdf has ${english_page_count:-unknown} pages; expected 6." >&2
  exit 1
fi
vietnamese_page_count=$(pdfinfo aeb_ieee_6page_vi.pdf | awk '/^Pages:/ {print $2}')
echo "Built aeb_ieee_6page.pdf: $english_page_count pages (required: 6)"
echo "Built aeb_ieee_6page_vi.pdf: $vietnamese_page_count pages (review copy; no page limit)"
