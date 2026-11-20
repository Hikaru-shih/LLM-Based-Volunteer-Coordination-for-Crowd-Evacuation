from pathlib import Path
import json,hashlib
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
R=Path(__file__).resolve().parents[1];O=R/'report';A=R/'local_archive/20261120_before_neutral_cost_wording';B=O/'.build/neutral_cost_20261120'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for lang,name in [('en','Report.docx'),('zh-TW','Report.zh-TW.docx')]:
    assert sha(O/name)==sha(B/name)
    d=Document(O/name);old=Document(A/name)
    tables=lambda v:[[[c.text for c in r.cells] for r in t.rows] for t in v.tables]
    assert tables(d)==tables(old)
    changes=[(p.text,q.text) for p,q in zip(old.paragraphs,d.paragraphs) if p.text!=q.text]
    assert len(changes)==3 and len(old.paragraphs)==len(d.paragraphs)
    assert 'smaller decline than the reference formula' in '\n'.join(p.text for p in d.paragraphs) if lang=='en' else True
    md=[]
    for el in d.element.body:
        if el.tag==qn('w:p'):
            p=Paragraph(el,d)
            if p.text:md.extend([('## ' if p.style.name.startswith('Heading') else '# ' if p.style.name=='Title' else '')+p.text,''])
        elif el.tag==qn('w:tbl'):
            rows=[[c.text.replace('|','/') for c in r.cells] for r in Table(el,d).rows];md.extend(['| '+' | '.join(rows[0])+' |','| '+' | '.join(['---']*len(rows[0]))+' |']+['| '+' | '.join(r)+' |' for r in rows[1:]]+[''])
    (O/'source'/f'Report.{lang}.md').write_text('\n'.join(md),encoding='utf-8')
p=O/'README.md';s=p.read_text(encoding='utf-8');s+='\n## Neutral cost comparison wording\n\nMain findings and conclusion now describe a smaller observed participation decline than the reference, without inferring lower underlying cost sensitivity. Discussion explicitly states that the design cannot separate baseline assistance tendency from cost sensitivity. The abstract already used the neutral smaller-decline comparison and remains unchanged. Numerical tables and appendix prompts are unchanged.\n';p.write_text(s,encoding='utf-8')
p=O/'PACKAGE_COMPLETE.json';x=json.loads(p.read_text(encoding='utf-8'));x['neutralCostWording']={'completed':True,'paragraphsChangedPerLanguage':3,'abstractAlreadyNeutral':True,'costSensitivityNotIdentified':True,'numericalDataChanged':False};x['files']=[{'path':f.relative_to(O).as_posix(),'sha256':sha(f)} for f in sorted(O.rglob('*')) if f.is_file() and '.build' not in f.parts and f.name!='PACKAGE_COMPLETE.json' and not f.name.startswith('~$')];p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-066 ' not in s
entry='## V-066 — Neutral observed-decline wording (2026-11-20, Asia/Taipei)\n\nReplaced weaker/flatter cost-response claims in main findings and conclusion with the descriptive smaller participation decline than the reference. Discussion now explicitly says the design does not separate baseline assistance tendency and cost sensitivity. Three paragraphs changed in each language. The abstract already said smaller decline than the reference and remains unchanged. All tables, figures, prompt examples, methods and numerical results unchanged. English21 and Chinese24 pages retained. Re-rendered using background Word after unavailable LibreOffice; changed pages visually checked and remaining raster pages matched prior reviewed renders. Main reports, source copies and package metadata updated. No new API calls or simulations. Previous versions: local_archive/20261120_before_neutral_cost_wording/.\n\n'
p.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8')
(B/'QA.json').write_text(json.dumps({'status':'complete','paragraphsChangedPerLanguage':3,'tablesUnchanged':8,'abstractUnchangedAlreadyNeutral':True,'pages':{'en':21,'zh':24},'visualReview':'Changed pages inspected; others identical to prior inspected renders','enSHA256':sha(O/'Report.docx'),'zhSHA256':sha(O/'Report.zh-TW.docx')},indent=2)+'\n',encoding='utf-8')
print('Neutral wording synchronized in both main reports.')
