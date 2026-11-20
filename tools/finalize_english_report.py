"""Validate and publish an English-language revision without altering study evidence."""
import json,csv,re,hashlib,os,msvcrt,subprocess,shutil
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'report';ARCHIVE=ROOT/'local_archive/20261118_english_report'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prior=read(ARCHIVE/'PACKAGE_COMPLETE.json')
for item in prior['files']:assert sha(ARCHIVE/item['path'])==item['sha256'],item['path']
formal=ROOT/'experiment_records/data/analysis/scenario_formal_v1_20261116'
for item in read(formal/'ARTIFACT_SHA256.json')['files']:assert sha(ROOT/item['path'])==item['sha256'],item['path']
with (formal/'CELL_SUMMARY.csv').open(encoding='utf-8-sig',newline='') as stream:cells=list(csv.DictReader(stream))
counts={(r['scenario'],r['information']):int(r['participate']) for r in cells}
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(OUT/'Report.en.docx') as z:
    body=E.fromstring(z.read('word/document.xml'));styles=E.fromstring(z.read('word/styles.xml'))
    text=' '.join(body.xpath('//w:t/text()',namespaces=ns));assert not re.search('[\u3400-\u9fff]',text)
    for name,size in [('Normal','24'),('Heading1','28')]:assert styles.xpath('//w:style[@w:styleId="'+name+'"]/w:rPr/w:sz/@w:val',namespaces=ns)==[size]
    assert not styles.xpath('//w:pBdr',namespaces=ns) and not body.xpath('//w:pBdr|//w:br[@w:type="page"]',namespaces=ns)
    tables=body.xpath('//w:tbl',namespaces=ns);assert len(tables)==2
    grids=[[[''.join(c.xpath('.//w:t/text()',namespaces=ns)) for c in row.xpath('./w:tc',namespaces=ns)] for row in table.xpath('./w:tr',namespaces=ns)] for table in tables]
    assert len(grids[0])==7 and len(grids[1])==9
    for row in grids[0][1:]:
        av,beta,num,context,ref=row;key=f'A{round(float(av)*100)}_R{round(float(beta)*100)}'
        assert int(num)==counts[(key,'numeric')] and int(context)==counts[(key,'contextual_equivalent')]
    for setting,geometry,forecast in grids[1][1:]:assert int(geometry)==counts[(setting,'geometry_only')] and int(forecast)==counts[(setting,'calibrated_forecast')]
for value in ('345','360','236','240','63','10.27','5.27','15.27','72.08','74.17','69.58','199/240','AI assistant'):assert value in text,value
assert sha(OUT/'Presentation.en.pptx')==sha(ARCHIVE/'Presentation.en.pptx')
subprocess.run(['git','check-ignore','report/Report.en.docx'],cwd=ROOT,capture_output=True,check=True)
# Update the common filename only if the user's open document no longer holds it.
canonical_updated=False
try:
    with (OUT/'Report.docx').open('r+b'):pass
    shutil.copyfile(OUT/'Report.en.docx',OUT/'Report.docx');canonical_updated=True
except PermissionError:pass
readme=OUT/'README.md';s=readme.read_text(encoding='utf-8')
s=s.replace('Prepared 2026-11-17','Revised 2026-11-18')
s=s.replace('[Report.docx](Report.docx): eight-page Chinese research report with Chinese/English abstracts','[Report.en.docx](Report.en.docx): seven-page English research report with an abstract')
s=s.replace('[source/Report.zh-TW.md](source/Report.zh-TW.md)','[source/Report.en.md](source/Report.en.md)')
s+='\nThe report was rewritten in direct student-project English,with shorter explanations and less repeated framing. Numerical results,references and AI-assisted coding disclosures remain. The prior package is archived at local_archive/20261118_english_report/.\n'
if not canonical_updated:s+='\nReport.docx is the older Chinese copy currently locked by Word. Use Report.en.docx for the revised report; the common filename can be updated once the old document is closed.\n'
else:s+='\nReport.docx is synchronized with the new English report.\n'
readme.write_text(s,encoding='utf-8')
log=ROOT/'experiment_records/EXPERIMENT_LOG.md';title='## V-048 — English-only report revision (2026-11-18, Asia/Taipei)'
entry=title+'''\n\nUser requested the report entirely in English and less formulaic prose. Rewrote the report in direct student-project language,keeping numerical results,full28 condition tables,references,method details and scientific limitations. Preserved the disclosure that all840 explanations and the later28-response demonstration were assistant-coded,not independent human ratings. No invented personal experience or human validation.\n\nSaved report/Report.en.docx and source/Report.en.md;all7 pages visually checked. Body12pt,section headings14pt,no paragraph divider rules or forced page breaks;all visible report text and the existing figure are English. Count tables checked against sealed cells,main result values retained,and2566 formal artifact hashes unchanged. The presentation was left byte-identical. Prior report package archived under local_archive/20261118_english_report. Zero new experimental API calls or Unity runs.\n\n'''
entry+=('Report.docx was also synchronized with the English revision.\n\n' if canonical_updated else 'The user-held Word lock prevented overwriting the old Report.docx;the new English file is complete and is the primary report. The old open copy was not forcibly closed or edited.\n\n')
with (ROOT/'experiment_records/.notebook.lock').open('a+b') as gate:
    gate.seek(0);msvcrt.locking(gate.fileno(),msvcrt.LK_NBLCK,1)
    try:
        old=log.read_text(encoding='utf-8');marker='<!-- AUTO-RECORDED RUNS -->';assert title not in old and old.count(marker)==1
        tmp=log.with_suffix('.english-revision.tmp');tmp.write_text(old.replace(marker,entry+marker,1),encoding='utf-8');os.replace(tmp,log)
    finally:gate.seek(0);msvcrt.locking(gate.fileno(),msvcrt.LK_UNLCK,1)
workflow=ROOT/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';state=read(workflow)
state.update(date='2026-11-18',reportLanguage='English',primaryReport='report/Report.en.docx',currentReportPackage='report',canonicalReportSynchronized=canonical_updated)
workflow.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copyfile(Path(__file__),OUT/'source/finalize_english_report.py')
items=[{'path':p.relative_to(OUT).as_posix(),'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file() and '.build' not in p.parts and p.name!='PACKAGE_COMPLETE.json' and not p.name.startswith('~$') and (canonical_updated or p.name!='Report.docx')]
receipt={**{k:v for k,v in prior.items() if k!='files'},'date':'2026-11-18','reportPages':7,'reportLanguage':'English','primaryReport':'Report.en.docx','canonicalReportSynchronized':canonical_updated,'priorPackage':'local_archive/20261118_english_report','allReportTextEnglish':True,'presentationUnchanged':True,'files':items}
(OUT/'PACKAGE_COMPLETE.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print({'englishReportComplete':True,'pages':7,'conditionCountsChecked':28,'canonicalUpdated':canonical_updated,'formalHashesUnchanged':2566})
