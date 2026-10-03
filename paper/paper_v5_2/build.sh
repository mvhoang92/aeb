#!/usr/bin/env bash
# v5.2: English master = standard IEEEtran + pdfLaTeX (Times via newtx);
# Vietnamese author copy = XeLaTeX/fontspec (Vietnamese glyph coverage).
set -euo pipefail
cd "$(dirname "$0")"
for tool in pdflatex xelatex bibtex pdfinfo; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing $tool" >&2; exit 1; }
done

build() {  # $1 = engine, $2 = stem
  "$1" -interaction=nonstopmode -halt-on-error "$2.tex" >/dev/null
  bibtex "$2" >/dev/null
  "$1" -interaction=nonstopmode -halt-on-error "$2.tex" >/dev/null
  "$1" -interaction=nonstopmode -halt-on-error "$2.tex" >/dev/null
  if grep -Eq 'Citation .* undefined|Reference .* undefined|There were undefined references|Missing character:' "$2.log"; then
    echo "Unresolved references or missing glyphs in $2.log" >&2
    exit 1
  fi
  # IEEEtran selects ptm while the class loads, before fontspec replaces it under
  # XeLaTeX; those TU/ptm notices typeset no text. Any other substitution
  # (e.g. a missing small-caps shape) fails the build.
  if grep -E 'Font shape .* undefined' "$2.log" | grep -vq 'TU/ptm/'; then
    echo "Font-shape substitution in $2.log" >&2
    exit 1
  fi
  worst=$(grep -o 'Overfull \\[hv]box ([0-9.]*pt' "$2.log" | grep -o '[0-9.]*' | sort -g | tail -1 || true)
  if [[ -n "$worst" ]] && awk -v w="$worst" 'BEGIN { exit !(w > 1.0) }'; then
    echo "Overfull box of ${worst}pt (> 1pt) in $2.log" >&2
    exit 1
  fi
  pdfinfo "$2.pdf" | grep '^Pages:'
}

build pdflatex aeb_ieee_6page
build xelatex aeb_ieee_6page_vi
pages=$(pdfinfo aeb_ieee_6page.pdf | awk '/^Pages:/ {print $2}')
[[ "$pages" == 6 ]] || { echo "English manuscript must be six pages, got $pages" >&2; exit 1; }
echo 'PASS: English six-page pdfLaTeX draft and complete Vietnamese XeLaTeX author copy built.'
