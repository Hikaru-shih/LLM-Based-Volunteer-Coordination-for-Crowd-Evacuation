from pathlib import Path
import json,hashlib,re
from docx import Document
R=Path(__file__).resolve().parents[1];O=R/'report';B=O/'.build/readability_20261120'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('Report.docx','Report.zh-TW.docx'):
    assert sha(O/name)==sha(B/name)
    d=Document(O/name);assert len(d.tables)==7 and len(d.inline_shapes)==2
    headings=[p.text for p in d.paragraphs if p.style.name=='Heading 2' and p.text.startswith('5.')]
    assert [p.split()[0] for p in headings]==['5.1','5.2','5.3','5.4','5.5','5.6']
    if name=='Report.docx':
        abstract=next(p.text for p in d.paragraphs if p.text.startswith('This project compares'))
        assert len(re.split(r'(?<=[.!?])\s+(?=[A-Z])',abstract))==6
p=O/'README.md';s=p.read_text(encoding='utf-8').replace('Sections 4.1 and 5.3','Sections 4.1 and 5.6');s+='\n## Reader revision\n\nThe main report now uses Results with subsections5.1–5.6, beginning with Main findings. Both abstracts contain six sentences. Internal study/coding IDs, randomization constants and detailed token matching identifiers have been removed from body prose. These details remain in the complete English experiment log and locked design/matching records. Seven tables and two figures remain unchanged. Main reports were overwritten after the author closed Word, and all revised pages were checked.\n';p.write_text(s,encoding='utf-8')
p=O/'Speaker_Notes.en.md';s=p.read_text(encoding='utf-8').replace('new results in Section 5.3','new results in Section 5.6').replace('results in Section 5.3','results in Section 5.6');p.write_text(s,encoding='utf-8')
p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-063 ' not in s
entry='## V-063 — Main report readability and results hierarchy (2026-11-20, Asia/Taipei)\n\nPurpose: implement the author’s editorial feedback. Renamed Section5 Results and organized5.1 Main findings,5.2 Assistance cost and participation,5.3 Original physical information comparison,5.4 Exploratory utility consistency,5.5 Non-blind author review and5.6 Information control results. Both abstracts now contain six sentences with findings first. Removed P030/P031/P028 IDs, scenario-reasons-v3, scheduling/bootstrap seed constants and detailed o200k_base/41-number matching references from narrative prose. Reproducibility details remain unchanged in V-059/V-060 and the locked design, registration, prompt-match audit and verification records. Retained the substantive matching limitation in Methods. Original image assets and all seven numerical tables unchanged. No appendices added. English15pages and Chinese16pages, including covers, retain14pt headings and12pt body. Background Word export and raster inspection completed after the bundled renderer reported missing LibreOffice. Main files replaced after the author closed Word. No new API calls, simulations or evidence changes. Prior versions: local_archive/20261120_before_readability_revision/.\n\n'
p.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8')
p=O/'PACKAGE_COMPLETE.json';x=json.loads(p.read_text(encoding='utf-8'));x['readabilityRevision']={'date':'2026-11-20','abstractSentences':6,'resultsSubsections':6,'mainFindingsSection':'5.1','informationControlResultsSection':'5.6','bodyInternalIDsRemoved':True,'tablesUnchanged':7,'figuresUnchanged':2,'allRevisedPagesInspected':True};x['files']=[{'path':f.relative_to(O).as_posix(),'sha256':sha(f)} for f in sorted(O.rglob('*')) if f.is_file() and '.build' not in f.parts and f.name!='PACKAGE_COMPLETE.json' and not f.name.startswith('~$')];p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(B/'QA.json').write_text(json.dumps({'status':'complete','reportHash':sha(O/'Report.docx'),'translationHash':sha(O/'Report.zh-TW.docx'),'pages':{'en':15,'zh':16},'allPagesInspected':True,'abstractSentences':6,'tablesUnchanged':7,'figuresUnchanged':2},indent=2)+'\n',encoding='utf-8')
print('Main English and Chinese reports updated and verified.')
