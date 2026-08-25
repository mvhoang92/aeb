#!/usr/bin/env bash
set -euo pipefail

build_manuscript() {
  local stem="$1"
  if command -v pdflatex >/dev/null 2>&1 && command -v bibtex >/dev/null 2>&1; then
    pdflatex -interaction=nonstopmode -halt-on-error "${stem}.tex"
    bibtex "$stem"
    pdflatex -interaction=nonstopmode -halt-on-error "${stem}.tex"
    pdflatex -interaction=nonstopmode -halt-on-error "${stem}.tex"
  elif command -v tectonic >/dev/null 2>&1; then
    tectonic --keep-logs --keep-intermediates "${stem}.tex"
  elif [[ -x "$HOME/.local/bin/tectonic" ]]; then
    "$HOME/.local/bin/tectonic" --keep-logs --keep-intermediates "${stem}.tex"
  else
    echo "Build failed: install pdflatex+bibtex or tectonic." >&2
    exit 1
  fi

  if grep -Eq "Citation .* undefined|Reference .* undefined|There were undefined references" "${stem}.log"; then
    echo "Build failed: ${stem}.log contains unresolved citations or references." >&2
    exit 1
  fi
}

build_manuscript aeb_ieee_6page
build_manuscript aeb_ieee_6page_vi

for pdf in aeb_ieee_6page.pdf aeb_ieee_6page_vi.pdf; do
  if [[ ! -s "$pdf" ]]; then
    echo "Build failed: missing or empty $pdf." >&2
    exit 1
  fi
done

english_page_count=$(pdfinfo aeb_ieee_6page.pdf | awk '/^Pages:/ {print $2}')
if [[ "$english_page_count" != "6" ]]; then
  echo "Build failed: aeb_ieee_6page.pdf has ${english_page_count:-unknown} pages; expected 6." >&2
  exit 1
fi

vietnamese_page_count=$(pdfinfo aeb_ieee_6page_vi.pdf | awk '/^Pages:/ {print $2}')
echo "Built aeb_ieee_6page.pdf: $english_page_count pages (required: 6)"
echo "Built aeb_ieee_6page_vi.pdf: $vietnamese_page_count pages (review copy)"
