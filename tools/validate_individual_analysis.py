"""Generate an explicitly synthetic P3 demonstration and verify all artifacts. Zero API."""
import argparse
import json
from pathlib import Path

from individual_analysis import analyze, audit, digest, publish, verify, write_json
from test_individual_analysis import fixture


def run(root, records_root):
    root=Path(root).resolve()
    if root.exists():raise ValueError('Choose a new validation directory; existing evidence is preserved')
    root.mkdir(parents=True)
    scenarios=[]
    for x in (2,4):
        for tau in (0,.4,.8):
            for cv in (.005,.1):
                scenarios.append(dict(id=f'x{x}_tau{tau:g}_cv{cv:g}',nearbyAgentCount=x,exitNonBlockage=tau,volunteerCost=cv,failureCost=.5,unwillingness=5))
    for tau in (0,.4,.8):
        scenarios.append(dict(id=f'single_tau{tau:g}',nearbyAgentCount=1,exitNonBlockage=tau,volunteerCost=.005,failureCost=.5,unwillingness=5))
    scenarios += [dict(id='zero_players',nearbyAgentCount=0,exitNonBlockage=.5,volunteerCost=.005,failureCost=.5,unwillingness=5),
                  dict(id='unblocked',nearbyAgentCount=4,exitNonBlockage=1,volunteerCost=.005,failureCost=.5,unwillingness=5)]
    outcomes={}
    for i,s in enumerate(scenarios):
        k=1+i%6
        outcomes[s['id']]=[True]*k+[False]*(7-k)+['invalid','missing','missing']
    outcomes['x4_tau0.8_cv0.1']=['invalid']*4+['missing']*6
    outcomes['zero_players']=[False]*10
    outcomes['unblocked']=[False]*10
    fixture(root/'synthetic_input',scenarios,repetitions=10,outcomes=outcomes)
    input_root=root/'synthetic_input'
    interruption=dict(index=0,execution='interrupted_unknown_result',attempts=0,error='synthetic_interruption')
    (input_root/'interruptions.jsonl').write_text(json.dumps(interruption)+'\n',encoding='utf-8')
    ledger=json.loads((input_root/'ledger.json').read_text());ledger['reservedAttempts']+=3;write_json(input_root/'ledger.json',ledger)
    before={f.relative_to(input_root).as_posix():digest(f) for f in input_root.rglob('*') if f.is_file()}
    rejected=False
    try:audit(input_root)
    except ValueError:rejected=True
    if not rejected:raise AssertionError('Synthetic data entered the default empirical path')
    data,groups=analyze(input_root,root/'report',True)
    artifacts=verify(root/'report')
    if not all(digest(input_root/name)==sha for name,sha in before.items()):raise AssertionError('Analysis mutated input')
    if not groups or not any(g['stratum']=='ReferenceBoundary' for g in groups):raise AssertionError('Missing stratified curves')
    row=next(r for r in data['rows'] if r['scenario']=='x4_tau0.8_cv0.1')
    if row['rate'] is not None or row['invalid']!=4 or row['missing']!=6:raise AssertionError('Unresolved state became a valid choice')
    published=publish(root/'report',records_root)
    result=dict(passed=True,scenarios=len(scenarios),plannedTrials=170,curves=len(groups),hashedArtifacts=artifacts,
                syntheticRejectedWithoutOptIn=True,inputUnchanged=True,notebookRecorded=published,remoteRequests=0,formalTrials=0,
                note='Arbitrary synthetic action patterns test plumbing and charts only; no model or human behavior was measured.')
    write_json(root/'validation.json',result)
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--records-root',type=Path,required=True);a=p.parse_args();run(a.root,a.records_root)
