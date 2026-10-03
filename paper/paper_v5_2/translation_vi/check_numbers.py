import re,sys
from collections import Counter
def body(path):
    t=open(path,encoding='utf-8').read()
    t=re.sub(r'(?<!\\)%.*','',t)                      # comments
    d=t.index('\\begin{document}')
    head=t[t.index('\\title'):d] if '\\title' in t[:d] else ''   # title/author/note block in the preamble (IEEEtran files)
    t=head+t[d:]
    if '\\section*{Phụ lục' in t:
        t=t[:t.index('\\section*{Phụ lục')]           # glossary appendix: the only addition (contains no digits)
    t=re.sub(r'\\(cite|label|ref|includegraphics|graphicspath|bibliography|bibliographystyle|url)(\[[^\]]*\])?\{[^}]*\}','',t)
    t=re.sub(r'\\setlength\{[^}]*\}\{[^}]*\}|\\vspace\{[^}]*\}|p\{0\.\d+\\(text|column)width\}|\[[0-9.]+em\]|0\.\d+\\(text|column)width','',t)  # LaTeX lengths
    t=re.sub(r'\\begin\{tabular\*?\}(\{\\textwidth\})?\{[^\n]*','',t)
    t=re.sub(r'\\extracolsep\{\\fill\}','',t)
    return t
def nums(t): return Counter(re.findall(r'\d+(?:[.,]\d+)*',t))
en=nums(body(sys.argv[1])); vi=nums(body(sys.argv[2]))
print('EN tokens',sum(en.values()),'VI tokens',sum(vi.values()))
print('Only/more in EN:',dict(en-vi)); print('Only/more in VI:',dict(vi-en))
