"""Record revision provenance and leave genuine human review pending."""
from pathlib import Path
import hashlib,json,shutil,msvcrt,os
from docx import Document
R=Path(__file__).resolve().parents[1];O=R/'report';A=R/'experiment_records/data/analysis/posthoc_utility_20261119'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
doc=Document(O/'Report.formal.en.docx')
assert doc.styles['Normal'].font.size.pt==12 and doc.styles['Heading 1'].font.size.pt==14
assert len(doc.tables)==4 and len(doc.inline_shapes)==2
old=Document(R/'local_archive/20261119_report_revision/Report.formal.en.docx')
for j,k in ((0,1),(1,2)):
    assert [[c.text for c in r.cells] for r in old.tables[j].rows]==[[c.text for c in r.cells] for r in doc.tables[k].rows]
text='\n'.join(p.text for p in doc.paragraphs)
assert all(x in text for x in ['237/240','123/240','120 forecast choices','human review is pending','not an isolated causal effect','Cohen'])
reg=read(R/'experiment_records/data/scenario_formal_v1_20261116/registration.snapshot.json')
for cid in ('AC_A30_R50_numeric','AC_A30_R50_contextual_equivalent','PC_B3_M4_geometry_only','PC_B3_M4_calibrated_forecast'):
    c=next(t['case'] for t in reg['trials'] if t['case']['caseID']==cid)
    for m in c['payload']['messages']:
        for line in m['content'].split('\n'):
            if line:assert line in text,'Prompt appendix altered'
synced=False
try:
    with (O/'Report.docx').open('r+b'):pass
    shutil.copyfile(O/'Report.formal.en.docx',O/'Report.docx');synced=True
except PermissionError:pass
primary='Report.docx' if synced else 'Report.formal.en.docx'
refs=read(O/'source/references.json');refs['references']=[x for x in refs['references'] if x['id']<5]
refs['references'] +=[
 {'id':5,'authors':'Andreas Diekmann','title':"Volunteer's Dilemma",'publication':'Journal of Conflict Resolution 29(4), 605-610 (1985)','url':'https://doi.org/10.1177/0022002785029004003','evidence':'Publisher title, author, volume/issue and abstract checked 19 November 2026.'},
 {'id':6,'authors':'John J. Horton','title':'Large Language Models as Simulated Economic Agents: What Can We Learn from Homo Silicus?','publication':'arXiv:2301.07543v1 (2023)','url':'https://arxiv.org/abs/2301.07543v1','evidence':'Version-specific original single-author abstract checked; later coauthor revision is not substituted.'},
 {'id':7,'authors':'Elif Akata, Lion Schulz, Julian Coda-Forno, Seong Joon Oh, Matthias Bethge, Eric Schulz','title':'Playing repeated games with Large Language Models','publication':'arXiv:2305.16867v2 (2025)','url':'https://arxiv.org/abs/2305.16867v2','evidence':'Author list, version date and abstract checked on arXiv 19 November 2026.'}]
refs['checkedDate']='2026-11-19';refs['projectRecords']='Separate Appendix B; no local file paths counted as academic references.';write(O/'source/references.json',refs)
(O/'README.md').write_text(f'''# Revised research report package

Updated 19 November 2026. Primary English report: [{primary}]({primary}), sixteen pages including four complete prompt examples and study-record appendix. The formal edition is also retained as Report.formal.en.docx. Heading size 14 pt; body 12 pt. All sixteen pages were rendered using an independent background Microsoft Word instance and inspected. The bundled renderer was attempted but LibreOffice was unavailable.

## Human review pending

Open [Review.html](human_review/Review.html) in a browser and read [instructions](human_review/START_HERE.zh-TW.md). There are 48 selected original responses with their exact prompts, five blank quality fields, an original-text evidence field and a justification field. AI labels are absent from the public packet. Download the JSON regularly and again when finished. The packet can import its own downloaded JSON for resuming. Browser storage is best effort. No ratings have been filled by the assistant.

The sample contains 16 payoff, 16 geometry and 16 forecast responses, selected without using the AI quality labels. The sample is balanced, not population representative. This is a five-field quality review, not validation of all reason-theme labels. The scoring script tools/score_human_review.py rejects incomplete fields, missing identity/exposure metadata and non-verbatim quotes; it produces nominal Cohen's kappa, raw agreement and confusion matrices by field and stratum. Categories not_applicable and unclear are retained. Undefined kappa is reported rather than replaced with 1. Author ratings will be described as author review, with prior exposure disclosed. Original labels remain untouched.

## What changed

- Exploratory endpoint-utility analysis and two-endpoint belief thresholds, separate from the preregistered primary contrasts.
- Empirical API choice frequencies distinguished from mixed strategies; adjusted reference distinguished from base game equilibrium; ceiling effect disclosed.
- Forecast prompt length, details and numerical-content confound made a principal limitation. No new control condition claimed.
- Motivation, physical parameter table, defined archive identifiers and four full prompt examples.
- Seven academic references. Project evidence moved to a separate data-access appendix, without implying a public repository or DOI exists.

Existing-data analysis: experiment_records/data/analysis/posthoc_utility_20261119/ANALYSIS.en.md and endpoint_utility.csv. B2_M1 and B4_M1 favour declining at both supplied mean endpoints; B5_M1 and B5_M4 favour participating. All 120 choices in those four settings agree with the endpoint-invariant preference. Four settings reverse preference across endpoints. The endpoint-conditional agreement counts 237/240 and 123/240 must not be pooled as one accuracy rate. Forecasts and beliefs are not new observed outcomes.

## Reproduction and scope

Use the bundled Python runtime. tools/prepare_posthoc_revision.py prepares the existing-data analysis and original review packet; do not rerun it over an ongoing review without preserving the packet and downloaded ratings. tools/revise_report_posthoc.py revises the preserved input in local_archive/20261119_report_revision. tools/verify_posthoc_revision.py checks forecast/source consistency, utility thresholds, sampling and all 2,566 sealed artifacts. tools/check_review_form.cjs checks initial form construction and JSON export in a mocked DOM; it is not a browser layout test.

The original payoff/physical count tables are unchanged. All 2,566 sealed files were checked unchanged; no API calls or Unity runs were made. This is a post hoc writing/analysis revision, with no new model or prompt control experiment. The English presentation and Chinese translation are preserved earlier editions and do not yet include this revision or pending human results. Source text is source/Report.en.md. The package is Git ignored.
''',encoding='utf-8')
receipt=read(O/'PACKAGE_COMPLETE.json')
receipt.update(date='2026-11-19',reportPages=16,primaryReport=primary,canonicalReportSynchronized=synced,bodyTextAndTablesUnchanged=False,originalCountTablesUnchanged=True,existingResearchTextPreserved=False,revision='posthoc-utility-and-review-packet-v1',humanReview={'planned':48,'completed':0,'status':'awaiting_actual_human_ratings','fields':5,'aiLabelsHidden':True},academicReferences=7,completePromptExamples=4,visualQACompleted=True,formalHashesVerifiedUnchanged=2566,reportLanguage='English',newAPICalls=0,newUnityRuns=0)
receipt['translations']['zh-TW']['status']='earlier_edition_not_updated_for_posthoc_revision';receipt['translations']['zh-TW'].pop('researchContentUnchangedWithFormalEdition',None)
receipt['presentationRevisionStatus']='earlier_edition_unchanged'
receipt['files']=[{'path':p.relative_to(O).as_posix(),'sha256':sha(p)} for p in sorted(O.rglob('*')) if p.is_file() and '.build' not in p.parts and p.name!='PACKAGE_COMPLETE.json' and not p.name.startswith('~$')]
write(O/'PACKAGE_COMPLETE.json',receipt)
wpath=R/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';w=read(wpath)
w.update(date='2026-11-19',currentMilestone='report_revision_ready_human_review_pending',primaryReport='report/'+primary,canonicalReportSynchronized=synced,humanQualityReviewCompleted=False,humanQualityReviewPlannedRows=48,humanValidation=False,next='User completes the 48-item label-hidden quality packet and returns the exported JSON. Then score human-AI agreement and update the report; do not count earlier assistant demonstrations as human ratings.',posthocAnalysis='experiment_records/data/analysis/posthoc_utility_20261119/ANALYSIS.json');write(wpath,w)
write(A/'REVISION_RECEIPT.json',{'date':'2026-11-19','status':'existing_data_work_complete_human_review_pending','sealedFilesVerifiedUnchanged':2566,'sourceForecastsVerified':8,'tableCountsPreserved':True,'reportPages':16,'academicReferences':7,'promptExamples':4,'reviewPlanned':48,'reviewCompleted':0,'htmlMockDOMPassed':True,'browserLayoutTested':False,'kappaUnitChecks':4,'newAPICalls':0,'newUnityRuns':0,'files':[{'path':p.relative_to(R).as_posix(),'sha256':sha(p)} for p in [A/'ANALYSIS.json',A/'endpoint_utility.csv',O/'human_review/sample.public.json',O/'human_review/Review.html',R/'tools/score_human_review.py']]})
entry='''## V-053 — Existing-data utility analysis and 48-item human review packet (2026-11-19, Asia/Taipei)

Purpose: address report critique without additional model calls or evacuation runs. The post hoc exploratory analysis uses the exact forecast means in the locked requests and computes the own utility difference separately at all-other-nine-decline and all-other-nine-willing endpoints. In four settings preferences retain the same sign and 120/120 forecast choices agree; four settings reverse sign. Endpoint-specific agreement is 237/240 and 123/240, not a pooled accuracy estimate. Two-endpoint belief thresholds are sensitivity calculations, not elicited beliefs or calibrated mixed-profile utilities. The registered primary contrasts remain unchanged.

Human review: a new label-hidden 48-item packet contains 16 payoff, 16 geometry and 16 forecast responses. Seed 2026111901; selection did not use AI quality judgments. Five quality fields, verbatim evidence and human notes are blank. Exact original prompts are included. Reviewer project role and prior label exposure must be disclosed. No human ratings exist yet; prior assistant examples remain assistant work. The scorer validates all entries and calculates nominal Cohen's kappa, agreement, margins and confusion tables by field and task. Four metric unit checks pass. The HTML initial render/export passed mocked-DOM checks; no native-browser layout test was performed.

Writing: English report revised to sixteen pages with physical parameters, empirical-frequency versus mixed-strategy interpretation, ceiling effect, principal information-package confound, three verified additional academic references, four exact prompt examples and separate project-record appendix. Local archive paths are not presented as academic publications. The new analysis is explicitly post hoc; human review is pending. No isolated forecast-effect, human-realism, hidden-belief or general optimality claim is added. Chinese translation and presentation remain earlier editions.

Verification: all 2,566 sealed file hashes unchanged; eight forecast tables independently reproduced from existing development sources; both original count tables and appendix prompt strings checked. All sixteen final report pages rendered and visually inspected using Microsoft Word after the packaged renderer reported missing LibreOffice. Data: experiment_records/data/analysis/posthoc_utility_20261119/. Review: report/human_review/Review.html. Prior report: local_archive/20261119_report_revision/. New API calls: 0; new Unity runs: 0.

'''
with (R/'experiment_records/.notebook.lock').open('a+b') as f:
    f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    try:
        p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-053 ' not in s
        tmp=p.with_suffix('.revision.tmp');tmp.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8');os.replace(tmp,p)
    finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
print(json.dumps({'primary':primary,'reportPages':16,'reviewPlanned':48,'reviewCompleted':0,'canonicalSynchronized':synced}))
