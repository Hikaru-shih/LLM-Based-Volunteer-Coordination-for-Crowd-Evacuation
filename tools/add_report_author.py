from pathlib import Path
import shutil
from docx import Document
from docx.shared import Pt
R=Path(__file__).resolve().parents[1];O=R/'report';A=R/'local_archive/20261120_before_author_name';B=O/'.build/author_name_20261120'
A.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
for name in ('Report.docx','Report.zh-TW.docx'):
    if not (A/name).exists():shutil.copy2(O/name,A/name)
    d=Document(A/name)
    advisor=next(p for p in d.paragraphs if p.text.startswith(('Advisor:','指導教授：')))
    author=advisor.insert_paragraph_before('Author: Pin Kuang Shih' if name=='Report.docx' else '作者：Pin Kuang Shih')
    author.style=d.styles['Normal'];author.alignment=1
    author.paragraph_format.space_after=Pt(16 if name=='Report.docx' else 6)
    author.paragraph_format.keep_with_next=True
    for run in author.runs:run.font.size=Pt(12)
    d.core_properties.author='Pin Kuang Shih'
    d.save(B/name)
    print(name)
