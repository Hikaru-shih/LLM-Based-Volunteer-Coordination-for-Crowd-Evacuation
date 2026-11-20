from pathlib import Path
import json,hashlib,shutil,msvcrt,os
from docx import Document
R=Path(__file__).resolve().parents[1];O=R/'report';A=R/'local_archive/20261120_trim_appendices'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name,marker in [('Report.formal.en.docx','Appendix A Complete prompt examples'),('Report.zh-TW.docx','附錄A 完整提示範例')]:
    before=Document(A/name);after=Document(O/name)
    old=[p.text for p in before.paragraphs];old=old[:old.index(marker)]
    old=[p.replace(' (project records in Appendix B)','').replace('（專案紀錄見附錄B）','').replace('References and project records','References').replace('參考文獻與專案紀錄','參考文獻') for p in old]
    assert old==[p.text for p in after.paragraphs],'Unexpected main-text change'
    assert [[[c.text for c in r.cells] for r in t.rows] for t in before.tables]==[[[c.text for c in r.cells] for r in t.rows] for t in after.tables]
assert sha(O/'Presentation.en.pptx')==next(x['sha256'] for x in read(A/'PACKAGE_COMPLETE.json')['files'] if x['path']=='Presentation.en.pptx')
synced=False
try:
    with (O/'Report.docx').open('r+b'):pass
    shutil.copyfile(O/'Report.formal.en.docx',O/'Report.docx');synced=True
except PermissionError:pass
primary='Report.docx' if synced else 'Report.formal.en.docx'
p=O/'README.md';s=p.read_text(encoding='utf-8')
s=s.replace('Updated 19 November 2026.','Updated 20 November 2026.').replace('current seventeen-page English report','current twelve-page English report').replace(', seven academic references and four complete prompt examples',', and seven academic references').replace('synchronized sixteen-page Traditional Chinese translation','synchronized eleven-page Traditional Chinese translation').replace('The exact English prompt appendix, bibliography and original English figures are retained deliberately for source fidelity, with Chinese explanations/captions.','The bibliography and original English figures are retained for source fidelity, with Chinese captions. Both reports end after their seven references; the former prompt and project-record appendices have been removed.').replace('both appendices retain four verbatim prompt examples, and ','').replace('English report seventeen pages; Chinese report sixteen pages; thirteen slides.','English report twelve pages; Chinese report eleven pages; thirteen slides.')
s+='\n## Appendices removed at author request\n\nOn 20 November 2026, both report appendices and their main-text cross-references were removed. All seven academic references, five result/configuration tables, two figures and the scientific narrative remain. No replacement supplementary document was created. The locked original requests and experiment records remain in the project. Previous full reports are archived in local_archive/20261120_trim_appendices/. Latest trim checks are in .build/trim_20261120/. Historical writing validation receipts describe their original editions.\n';p.write_text(s,encoding='utf-8')
p=O/'PACKAGE_COMPLETE.json';x=read(p);x.update(date='2026-11-20',reportPages=12,primaryReport=primary,canonicalReportSynchronized=synced,revision='reports-end-at-references-v1',completePromptExamples=0,reportAppendicesIncluded=False,mainResultsUnchanged=True)
x['translations']['zh-TW'].update(pages=11,appendix='Removed at user request',sourceEnglishSHA256=sha(O/'Report.formal.en.docx'))
x['files']=[{'path':p.relative_to(O).as_posix(),'sha256':sha(p)} for p in sorted(O.rglob('*')) if p.is_file() and '.build' not in p.parts and p.name!='PACKAGE_COMPLETE.json' and not p.name.startswith('~$')];write(O/'PACKAGE_COMPLETE.json',x)
p=R/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';w=read(p);w.update(date='2026-11-20',primaryReport='report/'+primary,canonicalReportSynchronized=synced,reportAppendicesIncluded=False,reportPages={'English':12,'TraditionalChinese':11});write(p,w)
write(O/'.build/trim_20261120/TRIM_COMPLETE.json',{'status':'complete','EnglishPages':12,'ChinesePages':11,'academicReferences':7,'tablesPerReport':5,'figuresPerReport':2,'mainTextUnchangedExceptAppendixReferences':True,'presentationUnchanged':True,'visualQACompleted':True,'newAPICalls':0,'newUnityRuns':0})
entry='''## V-058 — Removed report appendices at author request (2026-11-20, Asia/Taipei)

Purpose: remove content after References from both English and Chinese reports. Deleted the complete-prompt and project-record appendices, removed the Method cross-reference to Appendix B and simplified the reference heading. Both reports now end with academic reference [7]. No supplementary document was substituted. Original locked prompts and experimental evidence remain in the project; prior full reports are preserved in local_archive/20261120_trim_appendices/.

Verification: the entire retained paragraph sequence matches the pre-edit report except the removed appendix cross-reference and reference heading; all five tables and two figures per report remain. The presentation is byte-identical to the prior edition. All twelve English pages and eleven Chinese pages were rendered and visually inspected. Chinese references were grouped onto one page to avoid a two-reference orphan tail. The bundled renderer reported missing LibreOffice, so native background Word PDF export was used. Sources, README and package/workflow receipts updated. No API calls, Unity runs, scientific result changes or original-data deletion.

'''
with (R/'experiment_records/.notebook.lock').open('a+b') as f:
    f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    try:
        p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-058 ' not in s
        t=p.with_suffix('.trim.tmp');t.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8');os.replace(t,p)
    finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
print({'primary':primary,'EnglishPages':12,'ChinesePages':11,'endedAtReferences':True})
