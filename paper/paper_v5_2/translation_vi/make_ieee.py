#!/usr/bin/env python3
"""Generate aeb_v5_2_vi_ieee.tex (IEEEtran two-column, same layout as the EN master)
from the single-column reading copy aeb_v5_2_vi_doc_hieu.tex, so the translated
text exists in exactly one place. Run by build.sh before compiling."""
import re
from pathlib import Path

here = Path(__file__).resolve().parent
src = (here / "aeb_v5_2_vi_doc_hieu.tex").read_text(encoding="utf-8")

def between(text, start, end):
    i = text.index(start); j = text.index(end, i)
    return text[i:j]

vi_title = re.search(r"\{\\LARGE\\bfseries (.*?)\\par\}", src, re.S).group(1).strip()
en_title = re.search(r"\{\\large\\itshape (.*?)\\par\}", src, re.S).group(1).strip()
note = re.search(r"\\textit\{(Bản dịch tiếng Việt phục vụ đọc hiểu.*?)\}\n", src, re.S).group(1)

abstract = between(src, "\\begin{abstract}", "\\end{abstract}") + "\\end{abstract}\n"
abstract = abstract.replace("\\begin{abstract}\n\\noindent\n", "\\begin{abstract}\n")
kw = re.search(r"\\noindent\\textbf\{\\textit\{Từ khóa\}\}---(.*?)\n\n", src, re.S).group(1).strip()
keywords = "\\begin{IEEEkeywords}\n" + kw + "\n\\end{IEEEkeywords}\n"

body = between(src, "\\section{Giới thiệu}", "\\bibliographystyle{IEEEtran}")

# --- Floats: restore the EN master's environments, widths and sizes. ---
body = body.replace("\\includegraphics[width=\\textwidth]", "\\includegraphics[width=\\columnwidth]")
body = body.replace("\\begin{tabular}{p{0.20\\textwidth}p{0.75\\textwidth}}",
                    "\\begin{tabular}{p{0.27\\columnwidth}p{0.66\\columnwidth}}")
body = re.sub(r"\\begin\{tabular\*\}\{\\textwidth\}\{@\{\\extracolsep\{\\fill\}\}([^}]*)\}",
              r"\\begin{tabular}{\1}", body)
body = body.replace("\\end{tabular*}", "\\end{tabular}")
body = re.sub(r"\\centering\\(small|footnotesize)\n\\setlength\{\\tabcolsep\}\{\dpt\}",
              r"\\centering\\scriptsize\n\\setlength{\\tabcolsep}{3pt}", body)
# Table II is table* in the EN master.
i = body.index("\\label{tab:primary}")
s = body.rindex("\\begin{table}[t]", 0, i)
e = body.index("\\end{table}", i)
body = (body[:s] + "\\begin{table*}[t]" + body[s + len("\\begin{table}[t]"):e]
        + "\\end{table*}" + body[e + len("\\end{table}"):])

# --- Glossary: unnumbered section before the references (no longtable in 2-col). ---
gl = between(src, "\\midrule\\endhead", "\\end{longtable}")
rows = re.findall(r"^(.*?) & (.*?)\\\\$", gl, re.M)
glossary = ("\\section*{Phụ lục: Bảng thuật ngữ Anh–Việt}\n"
            "% Phần bổ sung duy nhất so với bản tiếng Anh.\n"
            "{\\footnotesize\\setlength{\\parindent}{0pt}\\setlength{\\parskip}{1pt}\n"
            + "\n".join(f"\\textit{{{a}}}: {b}\\par" for a, b in rows) + "\n}\n\n")

preamble = r"""% Bản dịch tiếng Việt phục vụ đọc hiểu, dàn trang giống bản tiếng Anh paper v5.2
% (IEEEtran conference, hai cột). TỰ SINH bởi make_ieee.py từ aeb_v5_2_vi_doc_hieu.tex;
% sửa nội dung ở file một cột rồi chạy lại build.sh.
% IEEEtran selects ptm (Times) while the class loads, before fontspec exists. Under
% XeLaTeX that is TU/ptm, which has no .fd: map it to the TeX Gyre Termes OTF files
% (the same Times-like design) so no font-shape substitution occurs.
\DeclareFontFamily{TU}{ptm}{}
\DeclareFontShape{TU}{ptm}{m}{n}{<->"[texgyretermes-regular.otf]:mapping=tex-text"}{}
\DeclareFontShape{TU}{ptm}{m}{it}{<->"[texgyretermes-italic.otf]:mapping=tex-text"}{}
\DeclareFontShape{TU}{ptm}{b}{n}{<->"[texgyretermes-bold.otf]:mapping=tex-text"}{}
\DeclareFontShape{TU}{ptm}{b}{it}{<->"[texgyretermes-bolditalic.otf]:mapping=tex-text"}{}
\DeclareFontShape{TU}{ptm}{bx}{n}{<->ssub * ptm/b/n}{}
\DeclareFontShape{TU}{ptm}{bx}{it}{<->ssub * ptm/b/it}{}
\documentclass[conference]{IEEEtran}
\IEEEoverridecommandlockouts
\usepackage{amsmath}
\usepackage{newtxmath}
\usepackage[no-math]{fontspec}
% TeX Gyre Termes (Times-like, Vietnamese glyphs, real small caps via smcp),
% loaded by file name from the TeX tree.
\setmainfont{texgyretermes}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,
  ItalicFont=*-italic,BoldItalicFont=*-bolditalic]
\setmonofont{DejaVu Sans Mono}[Scale=MatchLowercase]
\usepackage{polyglossia}
\setdefaultlanguage{vietnamese}
\usepackage{graphicx}
\graphicspath{{../figures/}}
\usepackage{booktabs,array,url,balance,microtype}
\renewcommand\IEEEkeywordsname{Từ khóa}
% Fill in when the Zenodo archive is minted (one place for both languages' text).
\newcommand{\artifactdoi}{\textit{DOI sẽ được cấp (Zenodo)}}

"""
title = (f"\\title{{{vi_title}\\\\[0.4em]\n{{\\Large\\itshape {en_title}}}}}\n"
         "\\author{\n\\IEEEauthorblockN{Mai Viet Hoang and Duc An Pham}\n"
         "\\IEEEauthorblockA{\\textit{Hanoi University of Science and Technology}\\\\\n"
         "Hanoi, Vietnam\\\\hoangmai04222@gmail.com}\\\\[0.6em]\n"
         f"\\parbox{{0.9\\textwidth}}{{\\centering\\small\\itshape {note}}}\n}}\n")

out = (preamble + title + "\\begin{document}\n\\maketitle\n\n" + abstract + keywords + "\n"
       + body + glossary
       + "\\balance\n\\bibliographystyle{IEEEtran}\n\\bibliography{../references}\n\\end{document}\n")
(here / "aeb_v5_2_vi_ieee.tex").write_text(out, encoding="utf-8")
print("wrote aeb_v5_2_vi_ieee.tex")
