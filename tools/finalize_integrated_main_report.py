from pathlib import Path
import json,hashlib,shutil
from docx import Document
from pypdf import PdfReader
R=Path(__file__).resolve().parents[1];O=R/'report';B=O/'.build/integrated_main_20261120';A=R/'local_archive/20261120_before_main_report_integration'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
x=read(R/'experiment_records/data/analysis/information_control_v1_20261120/RESULTS.json')
pages={k:len(PdfReader(B/k/'QA.pdf').pages) for k in ('en','zh')}
docs={k:Document(O/name) for k,name in [('en','Report.docx'),('zh','Report.zh-TW.docx')]}
for lang,d in docs.items():
    assert len(d.sections)==2 and len(d.tables)==7 and len(d.inline_shapes)==2
    assert d.styles['Normal'].font.size.pt==12 and d.styles['Heading 1'].font.size.pt==14 and d.styles['Heading 2'].font.size.pt==14
    assert [[c.text for c in row.cells] for row in d.tables[5].rows[1:]]==[[r['scenario']]+[f"{r[k]}/20" for k in ('geometry_only','length_control','calibrated_forecast')] for r in x['scenarioCounts']]
    assert [[c.text for c in row.cells][1:] for row in d.tables[6].rows[1:]]==[['79/80 (98.75%)','62/80 (77.50%)'],['73/80 (91.25%)','43/80 (53.75%)'],['25/80 (31.25%)','28/80 (35.00%)']]
    txt='\n'.join(p.text for p in d.paragraphs)
    assert '39.375' in txt and '41.25' in txt and '-60.00' in txt.replace('−','-')
    assert 'but it has not been run' not in txt and '但尚未執行' not in txt
    assert not any(p.text.startswith(('Appendix','附錄')) for p in d.paragraphs)
    assert [p.text for p in d.paragraphs if p.text.strip()][-1].startswith('[7]')
# Ensure historical and new sealed evidence is unchanged.
sealed=read(R/'experiment_records/data/analysis/information_control_v1_20261120/SEALED_ARTIFACTS.json')
for item in sealed['files']:assert sha(R/item['path'])==item['sha256']
for name in ['Followup_Information_Control.en.docx','Followup_Information_Control.zh-TW.docx']:
    src=(O/name).resolve();dest=(A/name).resolve()
    assert src.is_relative_to(R.resolve()) and dest.is_relative_to(R.resolve())
    if src.exists():shutil.move(str(src),str(dest))
p=O/'Speaker_Notes.en.md';s=p.read_text(encoding='utf-8').replace('Full follow-up methods and results are in the separate English information-control report. The main report remains the P030 edition.','The main English report now integrates the original study and the information-control experiment in separate analyses. Methods are in Section 4.1 and new results in Section 5.3.');p.write_text(s,encoding='utf-8')
(O/'README.md').write_text('''# Research report and presentation

Updated 20 November 2026. Start with **Report.docx**, the integrated English main report. It now includes the completed information-control experiment in its methods, results, abstract, discussion and conclusion. The original 840 responses and the new 480 responses remain separate analyses.

## Current deliverables

- [English main report](Report.docx): 15 pages including a separate cover. Advisor: Sai-Keung Wong. Seven tables, two figures and seven academic references.
- [Traditional Chinese translation](Report.zh-TW.docx): 16 pages including a separate cover. The same scientific claims and seven numerical tables.
- [English presentation](Presentation.en.pptx): 16 slides with four editable native charts and the model workflow.
- [English speaker notes](Speaker_Notes.en.md): synchronized slide order, including the three new experiment slides.
- [Review differences](Review_Differences.en.md): descriptive classification of the original 27 field differences, without adjudication.

The main reports retain 14-point section headings and 12-point body text. They end at the references, without appendices or paragraph divider rules. The English and Chinese reports were exported using background Word after the bundled renderer reported missing LibreOffice. Every final page was inspected. Presentation checks cover the artifact renders, package, geometry, font use and chart workbooks. Native PowerPoint rendering of the current deck has not been tested.

## Evidence and interpretation

P030 is the original 840-choice study. P031 is the later 480-choice information-control experiment, locked after inspecting P030 and before any new response. P031 compares layout alone, matched unrelated catalogue information and forecasts, each with two instruction option orders. Participation counts are 141/160, 116/160 and 53/160. Forecast minus control is -39.375 percentage points, with a descriptive 95% interval of [-42.50,-36.25]. That contrast is -60.00 points with participate first and -18.75 with decline first. One control topic and fixed forecast table row order/action names leave semantic and presentation limitations.

Methods and all new setting/order tables are integrated into main-report Sections 4.1 and 5.3. The endpoint-utility analysis and non-blind 48-response author review apply to the original study. New explanations remain verbatim and uncoded. No second model, temperature experiment, human behavior benchmark or new Unity runs were added.

The original sealed evidence and new evidence manifest remain unchanged. Raw new responses: experiment_records/data/information_control_v1_20261120/. New analysis: experiment_records/data/analysis/information_control_v1_20261120/. Prospective design: experiment_records/study_preparations/information_control_v1_20261120/. Complete English research history: experiment_records/EXPERIMENT_LOG.md. Source copies: source/Report.en.md and source/Report.zh-TW.md. These local records are distinct from academic references.

## Prior versions

The previous main reports and superseded standalone information-control documents are retained in local_archive/20261120_before_main_report_integration/. Prior deck: local_archive/20261120_presentation_before_followup/. Historical QA receipts describe their own editions. report/ and local_archive/ are Git ignored. Earlier defense practice documents remain historical study aids and have not been rewritten as part of this main-report integration.
''',encoding='utf-8')
p=O/'PACKAGE_COMPLETE.json';package=read(p)
package.update(date='2026-11-20',reportPages=pages['en'],englishSlides=16,nativeCharts=4,primaryReport='Report.docx',latestStudy='P031_INFORMATION_CONTROL_20261120',mainReportStudies=['P030','P031'],historicalAndFollowupPooled=False,canonicalReportSynchronized=True,visualQACompleted=True,reportAppendicesIncluded=False)
package.pop('historicalMainReportStudy',None)
old=package.pop('followupReports',None)
package['mainReportIntegration']={'completed':True,'pages':pages,'tables':7,'figures':2,'originalChoices':840,'newBatchChoices':480,'pooled':False,'newAPICallsThisIntegration':0,'newUnityRuns':0,'oldStandaloneReportsArchived':True,'archive':A.relative_to(R).as_posix()}
if old:package['archivedStandaloneReportMetadata']=old
package['files']=[{'path':p.relative_to(O).as_posix(),'sha256':sha(p)} for p in sorted(O.rglob('*')) if p.is_file() and '.build' not in p.parts and p.name!='PACKAGE_COMPLETE.json' and not p.name.startswith('~$')]
write(O/'PACKAGE_COMPLETE.json',package)
p=R/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';w=read(p);w.update(currentMilestone='main_report_integrates_original_and_information_control_studies',primaryReport='report/Report.docx',translatedReport='report/Report.zh-TW.docx',followupReport='report/Report.docx',followupIntegratedIntoMainReport=True,reportPages={'English':pages['en'],'TraditionalChinese':pages['zh']},next='Review the integrated main report and synchronized English presentation. No additional collection is scheduled.');write(p,w)
write(B/'QA.json',{'status':'complete','pages':pages,'everyPageVisuallyInspected':True,'renderMethod':'Background Word PDF export and pdf2image after missing LibreOffice','tablesCheckedAgainstSavedCounts':7,'sealedEvidenceUnchanged':True,'headingsPt':14,'bodyPt':12,'coverSeparate':True,'appendices':False,'reportSHA256':sha(O/'Report.docx'),'translationSHA256':sha(O/'Report.zh-TW.docx')})
p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-062 ' not in s
entry='## V-062 — Integrated information-control evidence into the main report (2026-11-20, Asia/Taipei)\n\nAt the author’s request, Report.docx is now the primary integrated report rather than a historical report plus a standalone follow-up. Updated the abstract, introduction, physical-task scope, methods, discussion and conclusion. Added Section4.1 for the separately locked 480-choice information-control design and Section5.3 for new results, full eight-setting counts and both instruction orders. All original five numerical tables and both figures retained, with the original workflow caption explicitly scoped to P030. P030840 and P031480 remain separately analysed. Added matching limits, fixed forecast row/action labels, pointwise descriptive intervals, order interaction and prespecified B2–B4/B5 subgroups. No new reason coding or human validation claim. English and Chinese reports have15 and16 pages including separate covers,14pt headings and12pt body, ending at reference[7] without appendices. Seven numerical tables verified and every rendered page visually inspected using background Word and rasterization after missing LibreOffice. All sealed evidence hashes unchanged. Previous main and standalone reports archived under local_archive/20261120_before_main_report_integration/. English speaker notes now point to the integrated report. Updated report sources, README, package metadata and workflow. No new API calls or Unity simulations.\n\n'
p.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8')
print(json.dumps({'integrated':True,'pages':pages,'tables':7,'sealedEvidenceUnchanged':True,'newAPICalls':0}))
