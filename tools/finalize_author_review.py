from pathlib import Path
import json,hashlib,shutil,msvcrt,os
from docx import Document
R=Path(__file__).resolve().parents[1];O=R/'report';A=R/'experiment_records/data/analysis/human_review_return_20261119'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
agreement=read(A/'AGREEMENT.json');ratings=read(A/'ratings.author-confirmed.json');original=read(A/'ratings.extracted.pending.json')
assert ratings['items']==original['items'],'Submitted judgments changed'
before=Document(R/'local_archive/20261119_author_review_report/Report.formal.en.docx');after=Document(O/'Report.formal.en.docx')
assert len(after.tables)==len(before.tables)+1
for t1,t2 in zip(before.tables,after.tables[:4]):assert [[c.text for c in r.cells] for r in t1.rows]==[[c.text for c in r.cells] for r in t2.rows]
assert len(after.inline_shapes)==len(before.inline_shapes)==2
# Independent marginal calculation of the displayed agreement values.
key={x['id']:x for x in read(R/'local_archive/20261119_review_key/baseline.json')['records']}
for field,m in agreement['fields'].items():
    pairs=[(x['ratings'][field],key[x['id']]['assistant'][field]) for x in ratings['items']]
    assert sum(a==b for a,b in pairs)==m['agree']
    cats={v for pair in pairs for v in pair};pe=sum(sum(a==c for a,b in pairs)*sum(b==c for a,b in pairs) for c in cats)/48**2
    if pe==1:assert m['kappa'] is None
    else:assert abs(((m['agree']/48-pe)/(1-pe))-m['kappa'])<1e-12
synced=False
try:
    with (O/'Report.docx').open('r+b'):pass
    shutil.copyfile(O/'Report.formal.en.docx',O/'Report.docx');synced=True
except PermissionError:pass
primary='Report.docx' if synced else 'Report.formal.en.docx'
h=O/'human_review/REVIEW_STATUS.json';status=read(h);status.update(status='completed_nonblind_author_review',completed=48,humanValidation=False,independentHumanValidation=False,reviewerRole='project_author',priorAIExposure=True,ratingsChangedByAssistant=False,results='experiment_records/data/analysis/human_review_return_20261119/AGREEMENT.json');write(h,status)
report=O/'README.md'
report.write_text(f'''# Current English report and review status

Updated 19 November 2026. Primary report: [{primary}]({primary}); formal copy: Report.formal.en.docx. Seventeen pages, including decision workflow, physical parameters, exploratory endpoint analysis, author review, seven academic references and four complete prompt examples. Section headings 14 pt; body 12 pt. All seventeen pages rendered and visually inspected using native Microsoft Word after the bundled renderer reported missing LibreOffice.

## Completed author review

The author submitted Review_filled.html and clarified that all 48 items were personally completed. Every one of the 240 ratings, 48 notes and exact source quotes passed checks. The supplied HTML and blank submitted identity/exposure metadata are preserved separately from normalized metadata added using the conversation. The author had prior access to the AI-filled example and Chinese reading translations. This is disclosed non-blind author review, not independent validation. Five quality fields only; no claim that the complete thematic codebook or model reasoning has been validated.

Results: reason-insufficient 45/48 (93.75%, kappa .854); action-reason relation 41/48 (85.42%, .580); comparison judgment 32/48 (66.67%, .400); unsupported information 47/48 (97.92%, .000); arithmetic 48/48 (100%, kappa undefined). Arithmetic was not applicable for every sampled response, and unsupported-information labels were almost constant, limiting interpretation of the raw agreement. The 27 field-level differences remain unadjudicated; original assistant labels and model choices are unchanged.

Analysis, original submission, normalized author-confirmed ratings, confusion matrices and differences: experiment_records/data/analysis/human_review_return_20261119/. Summary: AUTHOR_REVIEW.en.md. Reproduction: tools/complete_author_review.py, tools/update_report_author_review.py and tools/finalize_author_review.py. Original submitted ratings are never filled or corrected by these scripts; only disclosed metadata is normalized.

## Other existing evidence

The separate post hoc utility analysis remains under experiment_records/data/analysis/posthoc_utility_20261119/. It compares the two supplied background means and provides hypothetical two-endpoint belief thresholds; it does not assume actual background probabilities or calibrated mixed profiles. The original primary contrasts, raw data and count tables remain unchanged. No new API calls or Unity runs.

Review.html remains the author's editable translated review interface. AI_Example.html is explicitly assistant-only demonstration. The author-submitted HTML is retained as inert source evidence and was not executed during extraction. The sample was stratified across 16 payoff, 16 geometry and 16 forecast responses; agreement is not a population coding-validity estimate.

The Chinese report and English slides remain earlier editions. The current source is source/Report.en.md. This folder is Git ignored. Pre-review report preserved at local_archive/20261119_author_review_report/.
''',encoding='utf-8')
p=O/'PACKAGE_COMPLETE.json';receipt=read(p)
receipt.update(reportPages=17,primaryReport=primary,canonicalReportSynchronized=synced,revision='author-review-integrated-v1',independentHumanValidation=False,authorQualityReviewCompleted=True)
receipt['humanReview'].update(completed=48,status='completed_nonblind_author_review',priorAIExposure=True,independentBlindReview=False,originalRatingsChanged=False)
receipt['files']=[{'path':x.relative_to(O).as_posix(),'sha256':sha(x)} for x in sorted(O.rglob('*')) if x.is_file() and '.build' not in x.parts and x!=p and not x.name.startswith('~$')];write(p,receipt)
p=R/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';w=read(p);w.update(currentMilestone='author_review_integrated_writing_package_ready',primaryReport='report/'+primary,canonicalReportSynchronized=synced,humanQualityReviewCompleted=True,humanQualityReviewCompletedRows=48,humanValidation=False,independentHumanValidation=False,priorAIExposureDisclosed=True,next='Review the updated English report; original coding differences remain explicitly unadjudicated. Chinese translation and slides are earlier editions. No additional experiments launched.');write(p,w)
write(A/'COMPLETE.json',{'status':'author_review_integrated_not_independent_validation','n':48,'fieldJudgments':240,'differences':27,'ratingsUnchanged':True,'priorAIExposureDisclosed':True,'translationAssistanceDisclosed':True,'originalHTMLSHA256':sha(A/'Review_filled.submitted.html'),'agreementSHA256':sha(A/'AGREEMENT.json'),'reportPages':17,'report':primary,'sourceCountTablesUnchanged':True,'visualQACompleted':True,'newAPICalls':0,'newUnityRuns':0})
entry='''## V-056 — Submitted author review and descriptive agreement (2026-11-19, Asia/Taipei)

Intake: preserved the user-submitted Review_filled.html and extracted its saved state using JSON parsing only, without executing its scripts. All 48 items, 240 judgments, 48 notes and exact original-text quotes passed checks. Original reviewer/role/exposure fields were blank. An initially ambiguous partial-review answer was superseded by the user's explicit clarification that the submitted items were personally completed. The user is recorded as Project author; prior access to the AI example and translated reading assistance are disclosed. Normalized metadata is stored separately; the 48 original rating entries are unchanged.

Results: insufficient_reason 45/48, 93.75%, kappa 0.854398; actionReasonRelation 41/48, 85.42%, kappa 0.580; comparisonJudgment 32/48, 66.67%, kappa 0.400; unsupportedInformation 47/48, 97.92%, kappa 0; arithmeticJudgment 48/48, 100%, kappa undefined. Unsupported-information assistant labels were all none; arithmetic was not_applicable for both reviewers throughout. Constant or imbalanced margins limit raw-agreement interpretation. The 27 field-level differences are retained without adjudication. Category margins, confusion matrices and task-stratum results are saved. Independent marginal checks reproduced all agreement and kappa values.

Interpretation: this is author-confirmed, non-blind quality review with prior AI-label access, not independent blinded validation, human-human reliability or ground-truth coding accuracy. The balanced 48-response sample covers five quality fields, not the full thematic codebook or population validity. No original model decisions or frozen assistant labels were changed. The English report now includes methods, results and limitations for this review; Chinese report and slides remain earlier editions.

Validation: original four report tables and two images preserved; author rating entries unchanged. All seventeen report pages exported using a separate Microsoft Word instance and visually inspected after the bundled renderer reported missing LibreOffice. Data and provenance: experiment_records/data/analysis/human_review_return_20261119/. Pre-edit report: local_archive/20261119_author_review_report/. No new API calls or Unity runs.

'''
with (R/'experiment_records/.notebook.lock').open('a+b') as f:
    f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    try:
        p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-056 ' not in s
        t=p.with_suffix('.author.tmp');t.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8');os.replace(t,p)
    finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
print(json.dumps({'primary':primary,'pages':17,'authorRatings':48,'originalRatingsUnchanged':True,'independentValidation':False}))
