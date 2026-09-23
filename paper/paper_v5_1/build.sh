#!/usr/bin/env bash
# XeTeX/fontspec manuscript: do not route through pdflatex.
set -euo pipefail
cd "$(dirname "$0")"
for stem in aeb_ieee_6page aeb_ieee_6page_vi; do
  if command -v tectonic >/dev/null 2>&1; then
    tectonic --keep-logs --keep-intermediates "$stem.tex"
  elif [[ -x "$HOME/.local/bin/tectonic" ]]; then
    "$HOME/.local/bin/tectonic" --keep-logs --keep-intermediates "$stem.tex"
  elif command -v xelatex >/dev/null 2>&1 && command -v bibtex >/dev/null 2>&1; then
    xelatex -interaction=nonstopmode -halt-on-error "$stem.tex"
    bibtex "$stem"
    xelatex -interaction=nonstopmode -halt-on-error "$stem.tex"
    xelatex -interaction=nonstopmode -halt-on-error "$stem.tex"
  else
    echo 'Install Tectonic or XeLaTeX + BibTeX (fontspec requires a Unicode engine).' >&2
    exit 1
  fi
  if grep -Eq 'Citation .* undefined|Reference .* undefined|There were undefined references|Missing character:' "$stem.log"; then
    echo "Unresolved references or missing glyphs in $stem.log" >&2
    exit 1
  fi
  pdfinfo "$stem.pdf" | grep '^Pages:'
done
pages=$(pdfinfo aeb_ieee_6page.pdf | awk '/^Pages:/ {print $2}')
[[ "$pages" == 6 ]] || { echo "English manuscript must be six pages, got $pages" >&2; exit 1; }
echo 'PASS: English six-page draft and complete Vietnamese author-reading copy built.'
