from pathlib import Path
import json,hashlib,shutil
from docx import Document
from pypdf import PdfReader
R=Path(__file__).resolve().parents[1];O=R/'report';B=O/'.build/json_polish_20261120';A=R/'local_archive/20261120_before_json_polish'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
pages={k:len(PdfReader(B/k/'QA.pdf').pages) for k in ('en','zh')}
def blocks(d):
    out=[];active=False
    for p in d.paragraphs:
        if p.text.startswith(('Appendix A','附錄A')):active=True
        if active and p.text.startswith(('{','[')):
            try:out.append(json.loads(p.text))
            except ValueError:pass
    return out
for lang,name in [('en','Report.docx'),('zh','Report.zh-TW.docx')]:
    assert sha(O/name)==sha(B/name)
    d=Document(O/name);old=Document(A/name)
    tables=lambda v:[[[c.text for c in r.cells] for r in t.rows] for t in v.tables]
    assert tables(d)==tables(old) and len(d.tables)==8 and len(d.inline_shapes)==2
    assert blocks(d)==blocks(old) and len(blocks(d))==4
    start=next(i for i,p in enumerate(d.paragraphs) if p.text==('6 Discussion' if lang=='en' else '6 討論'))
    end=next(i for i,p in enumerate(d.paragraphs) if p.text.startswith('7 Limitations' if lang=='en' else '7 限制'))
    assert len([p for p in d.paragraphs[start+1:end] if p.text])==3
    for p in d.paragraphs:
        if p.text.startswith(('{','[')) and '\n' in p.text:
            assert all(r.font.name=='Consolas' and r.font.size.pt==12 for r in p.runs)
    shutil.copy2(B/('Report.en.md' if lang=='en' else 'Report.zh-TW.md'),O/'source'/('Report.en.md' if lang=='en' else 'Report.zh-TW.md'))
for item in read(R/'experiment_records/data/analysis/information_control_v1_20261120/SEALED_ARTIFACTS.json')['files']:assert sha(R/item['path'])==item['sha256']
p=O/'README.md';s=p.read_text(encoding='utf-8').replace('19 pages including','21 pages including').replace('22 pages including','24 pages including')
s+='\n## Appendix readability and discussion revision\n\nDiscussion now has three interpretation-focused paragraphs without repeating result estimates. Appendix JSON uses12pt Consolas with indentation and line breaks. All four displayed JSON blocks in each language parse identically to the previous exact-input examples. Natural-language prompt wording and JSON field order/values are unchanged, but displayed JSON whitespace differs from the original serialized API input. This distinction is disclosed next to the examples; matching counts still refer to original input. The report is21 English pages and24 Chinese pages, including appendices. Changed page renders were inspected and unchanged pages matched prior inspected renders. No new data collection or public upload. Public deposition remains undecided pending author/supervisor review.\n';p.write_text(s,encoding='utf-8')
p=O/'PACKAGE_COMPLETE.json';x=read(p);x.update(reportPages=pages['en']);x['mainReportIntegration']['pages']=pages;x['jsonReadabilityRevision']={'pages':pages,'font':'Consolas','fontPt':12,'jsonBlocksPerLanguageVerified':4,'JSONWhitespaceDisplayOnly':True,'discussionParagraphs':3,'resultTablesUnchanged':8,'publicUpload':False,'newAPICalls':0,'newUnityRuns':0};x['files']=[{'path':f.relative_to(O).as_posix(),'sha256':sha(f)} for f in sorted(O.rglob('*')) if f.is_file() and '.build' not in f.parts and f.name!='PACKAGE_COMPLETE.json' and not f.name.startswith('~$')];write(p,x)
p=R/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';w=read(p);w.update(reportPages={'English':pages['en'],'TraditionalChinese':pages['zh']},publicDepositionStatus='not_published_pending_author_supervisor_decision');write(p,w)
write(B/'QA.json',{'status':'complete','pages':pages,'JSONObjectsVerifiedUnchangedPerLanguage':4,'resultAndAuditTablesUnchanged':8,'discussionParagraphs':3,'visualReview':'Changed pages inspected; unchanged pages hash-matched to prior inspected raster pages','publicUpload':False,'reportSHA256':sha(O/'Report.docx'),'translationSHA256':sha(O/'Report.zh-TW.docx')})
p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-065 ' not in s
entry='## V-065 — Readable appendix JSON and shorter discussion (2026-11-20, Asia/Taipei)\n\nPurpose: implement final presentation refinements without extending the study. JSON observation, forecast, matched-control and response-schema blocks now use12pt Consolas with indentation and line breaks. Parsed objects, field order and values were checked against the earlier exact-input examples in both report languages. Display whitespace differs from original API serialization, so the appendix explicitly says token checks use the original inputs. No scientific prompt or result was changed. Discussion shortened to three paragraphs emphasizing interpretation rather than repeating estimates, while retaining baseline/reference distinctions and limits of reason/utility analyses. All eight tables and both figures unchanged. Current reports21 English pages and24 Chinese pages, including appendices. Changed page renders inspected, unchanged renders matched to prior reviewed pages. Background Word used after bundled renderer lacked LibreOffice. Sealed evidence hashes verified unchanged. Main/source files, README and package/workflow updated. No API calls, new trials, simulations or public publication. A public deposit remains a future author/supervisor decision. Previous reports retained in local_archive/20261120_before_json_polish/.\n\n'
p.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8')
print(json.dumps({'status':'complete','pages':pages,'tablesUnchanged':8,'JSONObjectsVerified':8,'publicUpload':False}))
