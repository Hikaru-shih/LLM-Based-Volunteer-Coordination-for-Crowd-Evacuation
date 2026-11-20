"""Score author-confirmed submitted ratings with prior AI access disclosed."""
import json,hashlib
from pathlib import Path
from score_human_review import score
R=Path(__file__).resolve().parents[1];A=R/'experiment_records/data/analysis/human_review_return_20261119'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
x=read(A/'ratings.extracted.pending.json')
assert all(not x.get(k) for k in ('reviewer','role','exposure'))
x.update(reviewer='Project author',role='author',exposure='yes',translationAssistance={'language':'zh-TW','type':'AI-assisted reading translations provided; English originals retained'},provenance={'submission':'Review_filled.html','confirmation':'User clarified that all submitted items were personally completed.','metadataSource':'Conversation clarification; blank submitted metadata retained in original extraction','priorAIExample':'Separate assistant-filled example provided before submission; not label-naive independent blind review'})
write(A/'ratings.author-confirmed.json',x)
result=score(A/'ratings.author-confirmed.json');result.update(status='author_review_descriptive_comparison_not_independent_validation',priorAIExampleAvailable=True,reviewProvenance=x['provenance'],originalHTMLSHA256=hashlib.sha256((A/'Review_filled.submitted.html').read_bytes()).hexdigest())
write(A/'AGREEMENT.json',result)
public=read(R/'report/human_review/sample.public.json')['items'];baseline={r['id']:r for r in read(R/'local_archive/20261119_review_key/baseline.json')['records']};ratings={r['id']:r for r in x['items']}
diff=[]
for p in public:
    for k,v in ratings[p['id']]['ratings'].items():
        old=baseline[p['id']]['assistant'][k]
        if old!=v:diff.append({'id':p['id'],'field':k,'author':v,'assistant':old,'quote':ratings[p['id']]['quote'],'note':ratings[p['id']]['note']})
write(A/'DISAGREEMENTS.json',{'status':'not_adjudicated_original_labels_unchanged','differences':diff})
names={'insufficient_reason':'Reason insufficient','actionReasonRelation':'Action-reason relation','comparisonJudgment':'Comparison judgment','unsupportedInformation':'Unsupported information','arithmeticJudgment':'Arithmetic judgment'}
lines=['# Author review of 48 sampled explanations','','The project author confirmed personal completion of all 48 submitted ratings. Identity is recorded by role, not an inferred name. The submitted HTML and its original empty metadata are preserved; role and prior-exposure fields were completed from the conversation, with that provenance retained.','','The author had access to the assistant-filled example and AI-assisted Chinese reading translations before submission. This is a disclosed author review, not independent blinded validation or human-human inter-rater reliability. Agreement and kappa are descriptive only; they cannot establish coding validity or model reasoning accuracy. The stratified sample contains 16 payoff, 16 geometry and 16 forecast responses, and covers five quality fields rather than all reason themes.','','| Quality field | Agreement | Kappa |','|---|---:|---:|']
for k,r in result['fields'].items():lines.append(f"| {names[k]} | {r['agree']}/{r['n']} ({100*r['agreement']:.2f}%) | {r['kappa']:.3f} |" if r['kappa'] is not None else f"| {names[k]} | {r['agree']}/{r['n']} ({100*r['agreement']:.2f}%) | undefined (constant margins) |")
lines+=['','Not-applicable and unclear are explicit nominal categories. Constant matching margins make kappa undefined despite full raw agreement. All 240 judgments, 48 notes and exact source quotes passed completeness checks. No missing ratings were inferred or filled. Confusion matrices and stratum-specific summaries are in AGREEMENT.json.','','## Differences requiring interpretation','']
for z in diff:lines.append(f"- {z['id']} / {z['field']}: author={z['author']}; assistant={z['assistant']}. No adjudication or source-label change.")
if not diff:lines.append('No categorical differences in the submitted five-field ratings. This agreement is not independent corroboration because the author had prior AI-label access.')
lines+=['','No new API calls, Unity runs or changes to formal model actions or original assistant coding.','']
(A/'AUTHOR_REVIEW.en.md').write_text('\n'.join(lines),encoding='utf-8')
intake=read(A/'INTAKE.json');intake.update(status='author_confirmed_all_48_scored_descriptively',humanCompletionConfirmed=True,confirmedReviewedItemIDs=[p['id'] for p in public],agreementStatisticsCalculated=True,independentBlindReviewClaimed=False,provenanceCorrection='Latest user clarification supersedes the earlier ambiguous partial-completion answer.');write(A/'INTAKE.json',intake)
print(json.dumps({'fields':{k:{'agreement':v['agree'],'n':v['n'],'kappa':v['kappa']} for k,v in result['fields'].items()},'differences':len(diff)},ensure_ascii=False))
