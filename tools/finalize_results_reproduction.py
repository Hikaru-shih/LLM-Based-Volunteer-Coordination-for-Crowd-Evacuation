from pathlib import Path
import hashlib,json,shutil
from docx import Document
from pypdf import PdfReader
R=Path(__file__).resolve().parents[1];O=R/'report';B=O/'.build/reproduction_20261120';A=R/'local_archive/20261120_before_results_reproduction'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
reg=read(R/'experiment_records/study_preparations/information_control_v1_20261120/registration.json')
cases={t['case']['information']:t['case'] for t in reg['trials'] if t['block']==1 and t['case']['scenario']=='B2_M1' and t['case']['optionOrder']=='participate_first'}
pages={lang:len(PdfReader(B/lang/'QA.pdf').pages) for lang in ('en','zh')}
for lang,name in [('en','Report.docx'),('zh','Report.zh-TW.docx')]:
    assert sha(O/name)==sha(B/name)
    d=Document(O/name);old=Document(A/name)
    tables=lambda doc:[[[c.text for c in r.cells] for r in t.rows] for t in doc.tables]
    assert tables(d)[:7]==[tables(old)[i] for i in [0,1,2,5,6,3,4]]
    assert len(d.tables)==8 and len(d.inline_shapes)==2 and len(d.sections)==2
    assert d.styles['Normal'].font.size.pt==12 and d.styles['Heading 2'].font.size.pt==14
    heads=[p.text for p in d.paragraphs if p.style.name=='Heading 2' and p.text.startswith('5.')]
    assert [h.split()[0] for h in heads]==['5.1','5.2','5.3','5.4','5.5','5.6']
    assert 'Information control' in heads[3] if lang=='en' else '資訊控制' in heads[3]
    ps=d.paragraphs
    def block(start,end):
        a=next(i for i,p in enumerate(ps) if p.text==start)+1
        b=next(i for i,p in enumerate(ps) if i>=a and p.text==end)
        return '\n'.join(p.text for p in ps[a:b])
    prefix=block('Shared user prefix','A3 Information condition suffixes' if lang=='en' else 'A3 各資訊條件的後段')
    suffixes={
      'geometry_only':block('Layout only suffix','Forecast suffix'),
      'calibrated_forecast':block('Forecast suffix','Matched control suffix'),
      'length_control':block('Matched control suffix','A4 Option order and response format' if lang=='en' else 'A4 選項順序與回覆格式')}
    for info,suffix in suffixes.items():assert prefix+suffix==cases[info]['payload']['messages'][1]['content'],(lang,info)
    system=block('System message','Shared user prefix');assert system==cases['geometry_only']['payload']['messages'][0]['content']
    shutil.copy2(B/('Report.en.md' if lang=='en' else 'Report.zh-TW.md'),O/'source'/('Report.en.md' if lang=='en' else 'Report.zh-TW.md'))
# Retain sealed source evidence, including original and new data hashes.
for item in read(R/'experiment_records/data/analysis/information_control_v1_20261120/SEALED_ARTIFACTS.json')['files']:
    assert sha(R/item['path'])==item['sha256']
p=O/'README.md';s=p.read_text(encoding='utf-8')
s=s.replace('15 pages including a separate cover','19 pages including a separate cover and the reproduction appendix').replace('16 pages including a separate cover','22 pages including a separate cover and the reproduction appendix')
s=s.replace('Seven tables, two figures','Seven result/configuration tables, one matching-audit table and two figures')
s=s.replace('They end at the references, without appendices or paragraph divider rules.','A reproduction appendix now follows the references at the author’s request. Paragraph divider rules remain absent.')
s=s.replace('Sections 4.1 and 5.6','Sections 4.1 and 5.4')
s+='\n## Primary results and reproduction appendix\n\nSection5.4 now presents the information-control experiment before the exploratory utility and author-review analyses in5.5 and5.6. Main findings include345/360 and ContrastA +10.27 pp [5.27,15.27]. All seven original numerical tables are unchanged but reordered and renumbered. AppendixA contains scheduling/bootstrap seeds, control-generation seed rule, matching method and eight-setting audit, exact shared system/user text with the three condition suffixes, option-order replacements and JSON schema. Each example was reconstructed from the document and compared exactly with the locked request. The appendix adds four English pages and six Chinese pages. All final pages visually inspected. No new API or Unity collection.\n'
p.write_text(s,encoding='utf-8')
p=O/'Speaker_Notes.en.md';s=p.read_text(encoding='utf-8').replace('new results in Section 5.6','new results in Section 5.4').replace('results in Section 5.6','results in Section 5.4');s+='\nReport navigation: Section5.4 contains information-control results,5.5 exploratory utility and5.6 author review. AppendixA supplies seeds, the matching audit and verbatim physical-task prompt examples.\n';p.write_text(s,encoding='utf-8')
p=R/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';w=read(p);w.update(reportPages={'English':pages['en'],'TraditionalChinese':pages['zh']},reportAppendicesIncluded=True,informationControlResultsSection='5.4',reproductionAppendix='A',currentMilestone='main_report_primary_results_reordered_and_reproduction_appendix_verified');write(p,w)
p=O/'PACKAGE_COMPLETE.json';x=read(p);x.update(reportPages=pages['en'],reportAppendicesIncluded=True)
x['mainReportIntegration'].update(pages=pages,tables=8)
x['resultsAndReproductionRevision']={'informationControlSection':'5.4','utilitySection':'5.5','authorReviewSection':'5.6','resultTablesUnchanged':7,'auditTablesAdded':1,'appendix':'A','exactPromptExamplesReconstructed':3,'bothLanguagesVerified':True,'sealedEvidenceUnchanged':True,'pages':pages,'newAPICalls':0,'newUnityRuns':0}
x['files']=[{'path':f.relative_to(O).as_posix(),'sha256':sha(f)} for f in sorted(O.rglob('*')) if f.is_file() and '.build' not in f.parts and f.name!='PACKAGE_COMPLETE.json' and not f.name.startswith('~$')];write(p,x)
write(B/'QA.json',{'status':'complete','pages':pages,'everyFinalPageInspected':True,'unchangedResultTables':7,'matchingAuditTable':1,'exampleMessagesExactlyReconstructed':3,'bothLanguagesVerified':True,'sealedEvidenceUnchanged':True,'reportSHA256':sha(O/'Report.docx'),'translationSHA256':sha(O/'Report.zh-TW.docx')})
p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-064 ' not in s
entry='## V-064 — Primary result order and reader-accessible reproduction appendix (2026-11-20, Asia/Taipei)\n\nAt the author’s request, moved the information-control experiment immediately after the original physical comparison as Section5.4, followed by exploratory utility5.5 and explanation/author review5.6. Moved original AI-coded reason observations into5.6 too. Renumbered result tables without changing any numerical cells. Expanded5.1 with345/360 and ContrastA +10.27 pp [5.27,15.27], retaining the six-sentence abstract. Added AppendixA at the author’s explicit request, superseding the earlier no-appendix preference: original scheduling/bootstrap seeds2026111661/2026111662, control-study2026112001/2026112002, nominal-control seed rule2026112000+10B+M, tiktoken0.14.0/o200k_base matching, prespecified tolerances, eight-setting proxy and provider token audit, exact B2_M1 shared system/user prompt and geometry/forecast/control suffixes, option-order replacements and JSON schema. All three full user examples in both DOCX files were reconstructed and matched exactly to the frozen registration. The appendix discloses semantic/format/attention mismatch and that local evidence is not a public dataset. All seven result/configuration tables preserved, one audit table added, both figures unchanged. English19pages and Chinese22pages, including4/6-page appendices. All rendered pages inspected via background Word after missing LibreOffice. Sealed evidence hashes unchanged. Updated main reports, source copies, package, workflow, README and report navigation in speaker notes. No new API calls or Unity runs. Previous reports retained in local_archive/20261120_before_results_reproduction/.\n\n'
p.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8')
print(json.dumps({'status':'complete','pages':pages,'verbatimExampleMessagesChecked':6,'unchangedResultTables':7,'newAPICalls':0}))
