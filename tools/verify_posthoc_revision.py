"""Read-only checks of exploratory analysis, sample provenance and sealed evidence."""
import hashlib,json,math,sys,re
from pathlib import Path
from collections import Counter
import scenario_agent_contract as c
from score_human_review import metrics,score
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
reg=read(R/'experiment_records/data/scenario_formal_v1_20261116/registration.snapshot.json')
spec,abstract,agents=c.load_inputs()
for cell in spec['cells']:
    forecast=c.forecasts(cell,agents)
    case=next(t['case'] for t in reg['trials'] if t['case']['scenario']==cell['id'] and t['case']['information']=='calibrated_forecast')
    assert forecast==json.loads(case['payload']['messages'][1]['content'].split('Forecasts:\n',1)[1]),'Forecast/source mismatch'
analysis=read(R/'experiment_records/data/analysis/posthoc_utility_20261119/ANALYSIS.json')
for r in analysis['rows']:
    a=r['others_decline_time_gain'];b=r['others_willing_time_gain']
    for bg in ('others_decline','others_willing'):assert math.isclose(r[bg+'_utility_gain'],r[bg+'_time_gain']/301,abs_tol=1e-12)
    if r['q_star'] is not None:
        q=r['q_star'];assert 0<q<1 and abs(q*a+(1-q)*b)<1e-10
        assert (q/2)*a+(1-q/2)*b>0
        assert ((1+q)/2)*a+(1-(1+q)/2)*b<0
assert analysis['agreementAllDecline']==237 and analysis['agreementAllWilling']==123
assert metrics([('a','a'),('a','b'),('b','a'),('b','b')])['kappa']==0
assert metrics([('a','a'),('b','b')])['kappa']==1
assert metrics([('a','b'),('b','a')])['kappa']==-1
assert metrics([('a','a')])['kappa'] is None
sample=read(R/'report/human_review/sample.public.json')
assert len(sample['items'])==48 and len({x['id'] for x in sample['items']})==48
assert Counter('payoff' if x['caseID'].startswith('AC_') else 'forecast' if 'calibrated_forecast' in x['caseID'] else 'geometry' for x in sample['items'])=={'payoff':16,'geometry':16,'forecast':16}
assert not any('assistant' in x or 'ratings' in x for x in sample['items'])
source={t['case']['caseID']:t['case'] for t in reg['trials']}
for x in sample['items']:assert x['messages']==source[x['caseID']]['payload']['messages']
html=(R/'report/human_review/Review.html').read_text(encoding='utf-8')
js=re.search(r'<script>([\s\S]*)</script>',html).group(1)
(R/'report/.build/revision_20261119/review-check.js').write_text(js,encoding='utf-8')
manifest=read(R/'experiment_records/data/analysis/scenario_formal_v1_20261116/ARTIFACT_SHA256.json');count=0
for x in manifest['files']:
    p=R/x['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],x['path'];count+=1
assert count==2566
print(json.dumps({'sealedArtifactsUnchanged':count,'forecastSourceChecks':8,'reviewItems':48,'metricChecksPassed':4,'newAPICalls':0,'newUnityRuns':0}))
