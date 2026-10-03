#!/usr/bin/env bash
# Build cả hai bản dịch tiếng Việt của paper v5.2 (XeLaTeX + BibTeX):
#   aeb_v5_2_vi_doc_hieu.pdf  - bản đọc hiểu một cột (nguồn nội dung duy nhất)
#   aeb_v5_2_vi_ieee.pdf      - cùng nội dung, dàn trang IEEEtran hai cột như bản EN
#                               (aeb_v5_2_vi_ieee.tex được sinh bởi make_ieee.py)
# Hình và tài liệu tham khảo dùng chung với bản EN: ../figures/ và ../references.bib
# (\graphicspath và \bibliography trong .tex trỏ tới đó).
set -euo pipefail
cd "$(dirname "$0")"
for tool in xelatex bibtex python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing $tool" >&2; exit 1; }
done
python3 make_ieee.py

build() {
  local STEM=$1
  xelatex -interaction=nonstopmode -halt-on-error "$STEM.tex" >/dev/null
  bibtex "$STEM" >/dev/null
  xelatex -interaction=nonstopmode -halt-on-error "$STEM.tex" >/dev/null
  xelatex -interaction=nonstopmode -halt-on-error "$STEM.tex" >/dev/null
  if grep -Eiq 'Citation .* undefined|Reference .* undefined|There were undefined references|Missing character' "$STEM.log"; then
    echo "Unresolved references/citations or missing glyphs in $STEM.log" >&2; exit 1
  fi
  if grep -Eq 'Font shape .* undefined' "$STEM.log"; then
    echo "Font-shape substitution in $STEM.log" >&2; exit 1
  fi
  worst=$(grep -o 'Overfull \\[hv]box ([0-9.]*pt' "$STEM.log" | grep -o '[0-9.]*' | sort -g | tail -1 || true)
  if [[ -n "$worst" ]] && awk -v w="$worst" 'BEGIN { exit !(w > 1.0) }'; then
    echo "Overfull box of ${worst}pt (> 1pt) in $STEM.log" >&2; exit 1
  fi
  command -v pdfinfo >/dev/null 2>&1 && echo "$STEM: $(pdfinfo "$STEM.pdf" | grep '^Pages:')"
}
build aeb_v5_2_vi_doc_hieu
build aeb_v5_2_vi_ieee
echo "PASS: both Vietnamese PDFs built."
