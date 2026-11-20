"""Remove only the report appendices; preserve seven references and all result tables."""
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
import shutil,json
R=Path(__file__).resolve().parents[1];O=R/'report';A=R/'local_archive/20261120_trim_appendices';A.mkdir(parents=True,exist_ok=True)
for name in ('Report.docx','Report.formal.en.docx','Report.zh-TW.docx','README.md','PACKAGE_COMPLETE.json'):
    p=O/name
    if p.exists() and not (A/name).exists():shutil.copyfile(p,A/name)
for lang,name,heading in [('en','Report.formal.en.docx','Appendix A Complete prompt examples'),('zh-TW','Report.zh-TW.docx','附錄A 完整提示範例')]:
    source=O/'source'/f'Report.{lang}.md'
    if not (A/f'Report.{lang}.md').exists():shutil.copyfile(source,A/f'Report.{lang}.md')
    d=Document(A/name);tables=[[[c.text for c in r.cells] for r in t.rows] for t in d.tables]
    first=next(p for p in d.paragraphs if p.text==heading)
    node=first._p
    while node is not None:
        following=node.getnext()
        if node.tag!=qn('w:sectPr'):node.getparent().remove(node)
        node=following
    for p in d.paragraphs:
        if '(project records in Appendix B)' in p.text:p.text=p.text.replace(' (project records in Appendix B)','')
        if '（專案紀錄見附錄B）' in p.text:p.text=p.text.replace('（專案紀錄見附錄B）','')
        if p.text=='References and project records':p.text='References'
        if p.text=='參考文獻與專案紀錄':
            p.text='參考文獻';p.paragraph_format.page_break_before=True
    assert tables==[[[c.text for c in r.cells] for r in t.rows] for t in d.tables]
    assert len(d.inline_shapes)==2 and len(d.tables)==5
    paras=[p.text for p in d.paragraphs if p.text.strip()]
    assert paras[-1].startswith('[7]') and sum(p.startswith(tuple(f'[{i}]' for i in range(1,8))) for p in paras)==7
    assert not any('Appendix' in p or '附錄' in p for p in paras)
    d.save(O/name)
    md=[]
    for el in d.element.body:
        if el.tag==qn('w:p'):
            p=Paragraph(el,d)
            if p.text:md += [('## ' if p.style.name.startswith('Heading') else '# ' if p.style.name=='Title' else '')+p.text,'']
        elif el.tag==qn('w:tbl'):
            rr=[[c.text.replace('|','/') for c in row.cells] for row in Table(el,d).rows];md+=['| '+' | '.join(rr[0])+' |','| '+' | '.join(['---']*len(rr[0]))+' |']+['| '+' | '.join(row)+' |' for row in rr[1:]]+['']
    source.write_text('\n'.join(md),encoding='utf-8')
    print(lang+': ended after reference [7]; five tables and two figures unchanged.')
