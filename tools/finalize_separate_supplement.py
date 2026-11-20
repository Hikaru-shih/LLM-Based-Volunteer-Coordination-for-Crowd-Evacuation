from pathlib import Path
import json,hashlib,shutil,zipfile
from docx import Document
from pypdf import PdfReader
R=Path(__file__).resolve().parents[1];O=R/'report';B=O/'.build/separate_supplement_20261120';A=R/'local_archive/20261120_before_separate_supplement';U=O/'upload'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
pages={k:len(PdfReader(B/k/'QA.pdf').pages) for k in ('en','zh','supp_en','supp_zh')}
def js(d):
    out=[]
    for p in d.paragraphs:
        if p.text.startswith(('{','[')):
            try:out.append(json.loads(p.text))
            except ValueError:pass
    return out
for name in ('Report.docx','Report.zh-TW.docx','Supplement.en.docx','Supplement.zh-TW.docx'):shutil.copy2(B/name,O/name)
for lang,name,suppname in [('en','Report.docx','Supplement.en.docx'),('zh-TW','Report.zh-TW.docx','Supplement.zh-TW.docx')]:
    d=Document(O/name);supp=Document(O/suppname);old=Document(A/name)
    tables=lambda v:[[[c.text for c in r.cells] for r in t.rows] for t in v.tables]
    assert tables(d)==tables(old)[:7] and tables(supp)==tables(old)[7:]
    assert js(supp)==js(old) and len(js(supp))==4
    assert d.core_properties.author==supp.core_properties.author=='Pin Kuang Shih'
    assert [p.text for p in d.paragraphs if p.text.strip()][-1].startswith('[7]')
    assert not any('Appendix A' in p.text or '附錄A' in p.text for p in d.paragraphs)
    assert any(suppname in p.text for p in d.paragraphs)
    for src,dest in [(('Report.md' if lang=='en' else 'Report.zh-TW.md'),f'Report.{lang}.md'),(suppname.replace('.docx','.md'),suppname.replace('.docx','.md'))]:shutil.copy2(B/src,O/'source'/dest)
shutil.copy2(B/'slides/output/Presentation.en.pptx',O/'Presentation.en.pptx')
p=O/'Speaker_Notes.en.md';s=p.read_text(encoding='utf-8').replace('Appendix A gives scheduling seeds, matching checks and actual prompt examples.','The separate supplement gives scheduling seeds, matching checks and actual prompt examples.').replace('AppendixA supplies seeds, the matching audit and verbatim physical-task prompt examples.','The separate Supplement.en.docx supplies seeds, the matching audit and physical-task prompt examples.');s+='\nThe main report ends at References. Reproduction details are in Supplement.en.docx, supplied alongside the report.\n';p.write_text(s,encoding='utf-8')
p=R/'README.md';s=p.read_text(encoding='utf-8').replace('The main report includes both separately analysed studies and an appendix with seeds, matching checks and actual prompt examples.','The main report includes both separately analysed studies and ends at References. A separate supplement provides seeds, matching checks and actual prompt examples.');p.write_text(s,encoding='utf-8')
(O/'README.md').write_text('''# Main report and separate supplement

Updated20November2026. Author: Pin Kuang Shih. Advisor: Sai-Keung Wong.

## Current documents

- Report.docx: primary English report,15 pages including its cover. Ends at References.
- Supplement.en.docx: separate7-page English Reproduction Details and Prompt Examples document. Contains scheduling seeds, the matching audit, actual prompts and JSON schema. Supply this alongside the main report.
- Report.zh-TW.docx:16-page Traditional Chinese main-report translation, ending at references.
- Supplement.zh-TW.docx: separate8-page Traditional Chinese supplement. Original English prompts remain unchanged.
- Presentation.en.pptx:16-slide English presentation with four editable charts. Notes reference the separate supplement.
- Speaker_Notes.en.md: English script and report navigation.

The main reports retain the research questions, essential methods, numerical results and limitations. Reproduction details were moved, not discarded. All seven main result/configuration tables and both figures are unchanged. The matching-audit table moved to the supplement. All four JSON objects in each supplement parse identically to the prior appendix. Only display whitespace changes in formatted JSON.

## Submission

upload/Project_Submission_20261120.zip contains both English documents, the English presentation and script, optional Chinese main/supplement translations, readme and checksums. Keep the supplement with the report for reviewer access. It contains no raw API replies or credentials. The source-only GitHub ZIP remains its earlier source snapshot and excludes report documents. No upload, commit or push was performed.

## Evidence and layout

The original840 and new480 choices remain separate. Main report Section5.4 covers information control,5.5 exploratory utility and5.6 author review. The main-text Methods section names the companion supplement. Original data and the English experiment history remain in experiment_records/. Public raw-data deposition has not occurred.

Reports retain14pt headings and12pt body. JSON uses12pt Consolas. All supplement pages and changed main pages were rendered and visually inspected using background Word after missing LibreOffice; unchanged main renders matched the prior inspected edition. PowerPoint package, fonts, geometry and four chart workbooks passed checks, without native PowerPoint rendering of this edition. Previous combined reports and submission ZIP are in local_archive/20261120_before_separate_supplement/.
''',encoding='utf-8')
(U/'SUBMISSION_README.txt').write_text('Research submission package\n20 November 2026\nAuthor: Pin Kuang Shih\nAdvisor: Sai-Keung Wong\n\nReport.docx: primary English report,15 pages, ends at References.\nSupplement.en.docx: separate7-page Reproduction Details and Prompt Examples document. Provide it alongside the main report so reviewers can inspect seeds, matching checks and actual prompts.\nPresentation.en.pptx:16-slide English presentation.\nSpeaker_Notes.en.md: English speaking script.\nChinese/Report.zh-TW.docx and Chinese/Supplement.zh-TW.docx: optional Traditional Chinese translations,16 and8 pages.\n\nThe two datasets remain separately analysed. JSON formatting is for readability, with token counts based on original serialized inputs. Check any institution-specific cover and student-ID requirements. Raw API replies, credentials, previous drafts and build outputs are excluded.\n',encoding='utf-8')
files=[(O/'Report.docx','Report.docx'),(O/'Supplement.en.docx','Supplement.en.docx'),(O/'Presentation.en.pptx','Presentation.en.pptx'),(O/'Speaker_Notes.en.md','Speaker_Notes.en.md'),(O/'Report.zh-TW.docx','Chinese/Report.zh-TW.docx'),(O/'Supplement.zh-TW.docx','Chinese/Supplement.zh-TW.docx'),(U/'SUBMISSION_README.txt','README.txt')]
write(U/'SUBMISSION_MANIFEST.json',{'date':'2026-11-20','author':'Pin Kuang Shih','files':[{'path':rel,'sha256':sha(p),'bytes':p.stat().st_size} for p,rel in files]});files.append((U/'SUBMISSION_MANIFEST.json','MANIFEST.json'))
candidate=B/'Project_Submission_20261120.zip'
with zipfile.ZipFile(candidate,'w',zipfile.ZIP_DEFLATED) as z:
    for p,rel in files:z.write(p,rel)
with zipfile.ZipFile(candidate) as z:
    assert z.testzip() is None
    for p,rel in files:assert hashlib.sha256(z.read(rel)).hexdigest()==sha(p)
shutil.copy2(candidate,U/'Project_Submission_20261120.zip')
p=R/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';w=read(p);w.update(reportAppendicesIncluded=False,reportPages={'English':pages['en'],'TraditionalChinese':pages['zh']},separateSupplements={'English':'report/Supplement.en.docx','TraditionalChinese':'report/Supplement.zh-TW.docx'},currentMilestone='main_report_ends_at_references_with_separate_reproduction_supplement');write(p,w)
p=O/'PACKAGE_COMPLETE.json';x=read(p);x.update(reportPages=pages['en'],reportAppendicesIncluded=False);x['mainReportIntegration'].update(pages={'en':pages['en'],'zh':pages['zh']},tables=7);x['separateSupplements']={'en':{'path':'Supplement.en.docx','pages':pages['supp_en']},'zh':{'path':'Supplement.zh-TW.docx','pages':pages['supp_zh']},'jsonObjectsUnchangedPerLanguage':4,'matchingAuditTables':1,'submissionZIPRefreshed':True,'mainReportsEndAtReferences':True};x['files']=[{'path':f.relative_to(O).as_posix(),'sha256':sha(f)} for f in sorted(O.rglob('*')) if f.is_file() and '.build' not in f.parts and f.name!='PACKAGE_COMPLETE.json' and not f.name.startswith('~$')];write(p,x)
p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-069 ' not in s
entry='## V-069 — Separate reproducibility supplement (2026-11-20, Asia/Taipei)\n\nAt the author’s request, moved AppendixA from both main reports into standalone Reproduction Details and Prompt Examples supplements. Main reports now end after reference[7] and retain clear companion-file references in Methods. All seven main numerical tables and both figures unchanged. The matching-audit table and all four JSON objects per language moved without value changes. Supplement includes author/advisor metadata and reading guidance, seeds, matching, prompt content, order replacements and schema. Main reports15/16pages, supplements7/8pages. Background Word rendering used after missing LibreOffice; every supplement page and changed main page inspected, other main renders identical to prior inspected pages. Updated source copies, README, notes and a validated PowerPoint note to point to the separate supplement. Refreshed document submission ZIP with both supplements and checksums. Previous combined reports and ZIP archived under local_archive/20261120_before_separate_supplement/. No data changes, experiments, API calls or publication.\n\n';p.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8')
write(B/'QA.json',{'status':'complete','pages':pages,'mainTablesUnchanged':7,'supplementAuditTables':1,'jsonObjectsUnchangedPerLanguage':4,'mainReportsEndAtReferences':True,'changedMainPagesAndEverySupplementPageInspected':True,'submissionZIPSHA256':sha(U/'Project_Submission_20261120.zip')})
print(json.dumps({'status':'complete','pages':pages,'mainReportsEndAtReferences':True,'submissionZIPRefreshed':True}))
