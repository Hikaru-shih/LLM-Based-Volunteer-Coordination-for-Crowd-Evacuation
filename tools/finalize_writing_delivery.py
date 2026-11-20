"""Publish verified writing files and record final package without new experiments."""
from pathlib import Path
import json,shutil,hashlib,msvcrt,os
R=Path(__file__).resolve().parents[1];O=R/'report';B=O/'.build/delivery_20261119'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
check=read(B/'CONSISTENCY_CHECK.json');assert check['status']=='pass'
validation=read(B/'PRESENTATION_VALIDATION.json');ppt=B/'output/Presentation.en.pptx'
assert sha(ppt)==validation['finalSha256']
shutil.copyfile(ppt,O/'Presentation.en.pptx')
synced=False
try:
    with (O/'Report.docx').open('r+b'):pass
    shutil.copyfile(O/'Report.formal.en.docx',O/'Report.docx');synced=True
except PermissionError:pass
primary='Report.docx' if synced else 'Report.formal.en.docx'
shutil.copyfile(R/'experiment_records/data/analysis/human_review_return_20261119/DISAGREEMENT_TAXONOMY.en.md',O/'Review_Differences.en.md')
(O/'README.md').write_text(f'''# Completed writing package

Updated 19 November 2026. No new API experiment or Unity simulation was run.

## Deliverables

- [{primary}]({primary}): current seventeen-page English report, including the decision flowchart, exploratory utility analysis, disclosed author review, disagreement taxonomy, seven academic references and four complete prompt examples.
- [Report.formal.en.docx](Report.formal.en.docx): formal English copy.
- [Report.zh-TW.docx](Report.zh-TW.docx): synchronized sixteen-page Traditional Chinese translation. Five tables and the narrative match the English version. The exact English prompt appendix, bibliography and original English figures are retained deliberately for source fidelity, with Chinese explanations/captions.
- [Presentation.en.pptx](Presentation.en.pptx): synchronized thirteen-slide English presentation, two editable native charts with embedded data snapshots, editable workflow shapes and thirteen source/interpretation notes.
- [Speaker_Notes.en.md](Speaker_Notes.en.md): English script in slide order.
- [Defense_QA.en.md](Defense_QA.en.md): short English oral-defense answers.
- [Oral_Defense.zh-TW.md](Oral_Defense.zh-TW.md): Chinese one-minute introduction and fifteen likely oral-defense questions.
- [Review_Differences.en.md](Review_Differences.en.md): classification of 27 field differences across 25 responses. No adjudication or recoding.

## Verified evidence and boundaries

All 28 formal condition counts match the sealed source table. The reports' numerical result tables match each other, both appendices retain four verbatim prompt examples, and native chart arrays match counts to within 1e-12. All 2,566 sealed artifacts remain unchanged. The 48 submitted author ratings and original assistant labels remain unchanged. The five quality-field agreement counts are 45/48, 41/48, 32/48, 47/48 and 48/48. Kappa is undefined for arithmetic because all ratings are not applicable; unsupported-information agreement is category-imbalanced. Author review is explicitly non-blind after AI-example access and reading translation, not independent validation.

The endpoint utility analysis is post hoc and uses fixed development forecast means, with unknown background probabilities and uncalibrated mixed profiles. A two-endpoint belief threshold is not an elicited model belief. The forecast condition bundles length, detail, numerical content and outcome information. Single-model scope, no human evacuation benchmark and no new group-efficiency test remain limitations. These were not resolved by additional experiments in this delivery.

## Layout and file checks

English report seventeen pages; Chinese report sixteen pages; thirteen slides. Every final report page and slide was rendered and visually inspected. Reports retain 14 pt headings and 12 pt body text, with no paragraph divider rules. The bundled document renderer lacked LibreOffice, so native background Word PDF export and page rasterization were used. The exported PPTX passed package/layout/font/chart-workbook checks and opened in PowerPoint; all thirteen native slide renders were inspected.

Native chart export initially lacked workbooks. The validated PPTX now contains two explicitly generated chart-data snapshots; these are not recovered source workbooks or formulas. Complete literal chart proportions were rounded to Excel-compatible fifteen significant digits (agreement with authoritative counts within 1e-12). Source counts and reported results are unchanged. PowerPoint may apply theme colours differently from the live viewer; the validated local PPTX is the delivered presentation.

## Sources and reproduction

Editable report sources: source/Report.en.md and source/Report.zh-TW.md. Bibliographic metadata: source/references.json. Reviewer/source evidence: experiment_records/data/analysis/human_review_return_20261119/. Endpoint analysis: experiment_records/data/analysis/posthoc_utility_20261119/. Reproduction helpers: tools/prepare_final_delivery.py, translate_final_report.py, prepare_slide_delivery.py, update_final_slides.mjs, validate_final_slides.mjs, write_defense_materials.py and verify_final_delivery.py. See private .build/delivery_20261119/ for validation receipts, not user deliverables.

Prior writing files are preserved in local_archive/20261119_final_delivery/. report/ and the local archive are Git ignored. This is a general graduation-project report format. Advisor Sai-Keung Wong is user supplied; institutional submission rules and author/department identity have not been supplied or invented.
''',encoding='utf-8')
p=O/'PACKAGE_COMPLETE.json';receipt=read(p)
receipt.update(date='2026-11-19',reportPages=17,englishSlides=13,nativeCharts=2,conditionCountsChecked=28,visualQACompleted=True,formalHashesVerifiedUnchanged=2566,newAPICalls=0,newUnityRuns=0,primaryReport=primary,canonicalReportSynchronized=synced,revision='synchronized-writing-delivery-v1',presentationUnchanged=False,presentationRevisionStatus='synchronized_with_current_report',disagreementTaxonomy={'fieldDifferences':27,'distinctResponses':25,'adjudicated':False},writingDeliveryComplete=True,independentHumanValidation=False,presentationNativeOpenVerified=True)
receipt['translations']['zh-TW'].update(status='synchronized_with_current_English_narrative',pages=16,sourceEnglishSHA256=sha(O/'Report.formal.en.docx'),tablesAndReferencesMatched=True,visualQACompleted=True,appendix='Verbatim English prompts retained; Chinese explanatory narrative',figure='Original English figures with Chinese captions')
receipt['files']=[{'path':x.relative_to(O).as_posix(),'sha256':sha(x)} for x in sorted(O.rglob('*')) if x.is_file() and '.build' not in x.parts and x!=p and not x.name.startswith('~$')];write(p,receipt)
p=R/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';w=read(p);w.update(currentMilestone='synchronized_writing_delivery_complete',primaryReport='report/'+primary,canonicalReportSynchronized=synced,translatedReport='report/Report.zh-TW.docx',currentPresentation='report/Presentation.en.pptx',writingDeliveryComplete=True,disagreementTaxonomyComplete=True,disagreementAdjudicationPerformed=False,next='Author reads and rehearses the completed writing package; supply institutional identity/format only if needed for submission. No additional experiments are required by this writing task or launched.');write(p,w)
write(B/'DELIVERY_COMPLETE.json',{'status':'complete_for_authorized_writing_scope','checks':check,'primaryReport':primary,'canonicalSynchronized':synced,'visualReview':{'EnglishPages':17,'ChinesePages':16,'slides':13,'nativePowerPointOpen':True},'sealedOriginalLabelsUnchanged':True,'authorRatingsUnchanged':True,'newAPICalls':0,'newUnityRuns':0,'finalPresentationSHA256':sha(O/'Presentation.en.pptx'),'packageReceiptSHA256':sha(O/'PACKAGE_COMPLETE.json')})
entry='''## V-057 — Synchronized final writing and defense package (2026-11-19, Asia/Taipei)

Purpose: complete the user's requested disagreement organisation, Chinese translation, English presentation, consistency checks and oral-defense preparation. Classified the 27 field-level author-AI differences across 25 distinct responses: 16 comparison-scope, seven action-reason support, three sufficiency-threshold and one unsupported-inference ambiguity. This taxonomy is an assistant post hoc interpretation, not human adjudication or a codebook revision. Original model actions, assistant labels and author-submitted ratings remain unchanged.

Deliverables: current English report seventeen pages; synchronized Chinese report sixteen pages; thirteen-slide English presentation with two editable charts, an editable personal-decision workflow and updated source/interpretation notes. Updated the slide-order English script and Chinese oral-defense guide, plus English short answers. The Chinese narrative/tables are translated; exact English prompt examples, original English figures and bibliography are retained with Chinese explanations. Both reports retain 14 pt headings and 12 pt body with no paragraph divider rules. Institutional author/department metadata were not invented.

Presentation workflow: reused the existing Artifact Session, preserved dimensions/theme and edited current elements. Reviewed all live slides, then exported locally per the user's report-folder preference. The chart gate identified absent embedded workbooks, followed by excess literal numeric precision. A documented portability repair rounded plot proportions to fifteen significant digits and generated two honest chart-owned data snapshots from complete checked literals; no original workbook/formula lineage is claimed. The local finalizer passed package, layout, font, native-chart and import checks. A sandbox-denied temporary-file replacement was retried with reviewed escalation and succeeded. The final PPTX opened in background PowerPoint and all thirteen native slide renders were inspected. PowerPoint theme colour rendering differs slightly from the live viewer, without data changes.

Verification: all 28 condition counts match sealed data; translated numeric tables and four verbatim prompt examples per report checked; both native chart arrays match authoritative counts within 1e-12; thirteen speaker notes present; 48-response review retains 240 judgments and 27 unadjudicated differences. All 2,566 sealed artifacts unchanged. Rendered and inspected every final English/Chinese page; used background Word export after the bundled renderer reported missing LibreOffice. Chinese image paragraph line-height and table continuity were corrected and re-rendered before delivery. No new API calls or Unity runs. Prior deliverables: local_archive/20261119_final_delivery/. Evidence and receipts: report/.build/delivery_20261119/{CONSISTENCY_CHECK.json,PRESENTATION_VALIDATION.json,DELIVERY_COMPLETE.json}; package hashes: report/PACKAGE_COMPLETE.json. The completed documents remain local and Git ignored; no external publication or messages.

Limits retained: one model/configuration; prompt information/length/detail confound; six development seeds; unknown endpoint probabilities and uncalibrated mixed profiles; no human behavior or group-efficiency validation; non-blind author quality review after AI-label access. Original registered contrasts and later post hoc analyses stay separate. No additional experimental work is claimed.

'''
with (R/'experiment_records/.notebook.lock').open('a+b') as f:
    f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    try:
        p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-057 ' not in s
        t=p.with_suffix('.delivery.tmp');t.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8');os.replace(t,p)
    finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
print(json.dumps({'primary':primary,'EnglishPages':17,'ChinesePages':16,'EnglishSlides':13,'writingScopeComplete':True,'sealedArtifactsUnchanged':2566,'newExperiments':0}))
