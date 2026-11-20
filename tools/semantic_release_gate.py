"""Recompute the preregistered v3 release gate; never alter actions or raw replies."""
import argparse
import hashlib
import json
from pathlib import Path
from individual_analysis import answer, read, require, write_json


def evaluate(folder):
    folder=Path(folder)
    registration=read(folder/'registration.json')
    criteria=dict(valid=50,uniqueOptimumActionsCorrect=40,numericalAndComparisonExplanationsCorrectAtLeast=48,tieExplanationsCorrectAtLeast=9,explicitActionExplanationContradictions=0)
    require(registration['criteria']==criteria,'Release criteria changed')
    status=read(folder/'live/summary.json')
    require(status['outcome']=='completed' and status['saved']==50,'Incomplete release diagnostic')
    cells={c['id']:c for c in read(folder/'cells.json')}
    planned={t['id']:t for t in read(folder/'plan.json')['trials']}
    review=read(folder/'manual-review.json')
    require(len(review)==50 and len({r['id'] for r in review})==50,'Missing/duplicate manual judgments')
    judgments={r['id']:r for r in review}
    totals=dict(valid=0,uniqueOptimumActionsCorrect=0,numericalAndComparisonExplanationsCorrect=0,tieExplanationsCorrect=0,explicitActionExplanationContradictions=0)
    files=list((folder/'live/trials').glob('*.json'));require(len(files)==50,'Expected 50 raw trials')
    for file in files:
        t=read(file);c=cells[t['id']];r=judgments[t['id']]
        require(r['rawSHA256']==hashlib.sha256(file.read_bytes()).hexdigest() and r['reviewer'] and r['note'],'Unbound/incomplete manual review')
        require(all(type(r[k]) is bool for k in ('numericalAndComparisonCorrect','explicitContradiction')),'Review labels must be boolean')
        require(t['valid'] and t['payload']==planned[t['id']]['payload'],'Invalid/changed trial')
        a,e=answer(t['response']);require(a is not None and e['model']=='gpt-6-luna' and t['willing']==(a['decision']=='participate'),'Raw action/provider mismatch')
        schema=json.loads(t['payload'])['response_format']['json_schema']['schema']
        require(list(schema['properties'])==['explanation','decision'] and schema['properties']['decision']=={'type':'string'},'Wrong release protocol')
        ec=1-c['observation']['volunteerCost'];ed=1-c['observation']['failureCost']*c['h']
        expected=None if abs(ec-ed)<1e-12 else 'participate' if ec>ed else 'decline_assistance'
        require(c['expectedAction']==expected and abs(c['expectedC']-ec)<1e-12 and abs(c['expectedD']-ed)<1e-12,'Incorrect diagnostic key')
        totals['valid']+=1
        totals['uniqueOptimumActionsCorrect']+=int(expected is not None and a['decision']==expected)
        totals['numericalAndComparisonExplanationsCorrect']+=int(r['numericalAndComparisonCorrect'])
        totals['tieExplanationsCorrect']+=int(expected is None and r['numericalAndComparisonCorrect'])
        totals['explicitActionExplanationContradictions']+=int(r['explicitContradiction'])
    passed=totals['valid']==50 and totals['uniqueOptimumActionsCorrect']==40 and totals['numericalAndComparisonExplanationsCorrect']>=48 and totals['tieExplanationsCorrect']>=9 and totals['explicitActionExplanationContradictions']==0
    result=dict(schema='response-v3-semantic-release-gate-v1',passed=passed,totals=totals,criteria=criteria,independentHumanReview=False,scope='Development release gate for fixed-state raw-action research; not universal reasoning correctness, human validity or formal test data')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--write',action='store_true');a=p.parse_args();result=evaluate(a.folder)
    if a.write:
        target=a.folder/'release-gate.json';require(not target.exists(),'Keep previous gate result');write_json(target,result)
    print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)
