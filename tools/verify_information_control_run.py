"""Independent completeness and source integrity audit for P031."""
import collections,json,csv,hashlib
from pathlib import Path
import information_control_experiment as e
import scenario_agent_contract as c
R=e.R;A=R/'experiment_records/data/analysis/information_control_v1_20261120'
def audit():
    e.verify();reg=e.read(e.OUT/'registration.snapshot.json');complete=e.read(e.OUT/'COMPLETE.json');assert complete['completed']==complete['reservedAttempts']==480
    assert e.sha(e.OUT/'registration.snapshot.json')==e.sha(e.PRE/'registration.json')
    cells=collections.Counter();blocks=collections.Counter();ids=set();provider=collections.Counter();actualtokens={};allrows=[]
    historical={row['providerID'] for row in csv.DictReader((R/'experiment_records/data/analysis/scenario_formal_v1_20261116/TRIAL_CATALOG.csv').open(encoding='utf-8-sig',newline=''))}
    for t in reg['trials']:
        f=e.OUT/'trials'/t['trialID'];claim=e.read(f/'CLAIM.json');result=e.read(f/'result.json');raw=(f/'response.raw').read_bytes();payload=t['case']['payload']
        assert claim['index']==reg['trials'].index(t) and claim['attempt']==1 and claim['execution']=='live'
        assert claim['payloadSHA256']==result['payloadSHA256']==c.sha(c.data(payload))==t['case']['payloadSHA256']
        assert result['httpStatus']==200 and result['valid'] and result['execution']=='live' and not result['secretRedacted']
        assert result['responseSHA256']==c.sha(raw)
        parsed=c.parse_reply(t['case'],raw.decode('utf-8'));assert parsed==result['parsed'] and parsed['providerID'] not in ids and parsed['providerID'] not in historical
        ids.add(parsed['providerID']);case=t['case'];cells[(case['scenario'],case['information'],case['optionOrder'])]+=1;blocks[t['block']]+=1
        env=json.loads(raw);provider[env['model']]+=1;usage=env.get('usage',{});actualtokens.setdefault((case['scenario'],case['optionOrder'],case['information']),set()).add(usage.get('prompt_tokens'))
    assert len(cells)==48 and set(cells.values())=={10};assert len(blocks)==10 and set(blocks.values())=={48};assert len(ids)==480
    matched=[]
    for s in sorted({k[0] for k in actualtokens}):
        for o in e.ORDERS:
            f=actualtokens[s,o,'calibrated_forecast'];ctl=actualtokens[s,o,'length_control'];assert None not in f and None not in ctl
            matched.append({'scenario':s,'order':o,'forecast':sorted(f),'control':sorted(ctl),'exactProviderInputTokenMatch':f==ctl})
    assert not (e.OUT/'STOPPED.json').exists()
    # Source evidence is read-only, including earlier signed artifacts.
    checked=0
    for r in e.read(R/'experiment_records/data/analysis/scenario_formal_v1_20261116/ARTIFACT_SHA256.json')['files']:
        assert e.sha(R/r['path'])==r['sha256'],r['path'];checked+=1
    result={'status':'passed','completed':480,'factorialCells':48,'perCell':10,'blocks':10,'perBlock':48,'uniqueProviderIDs':480,'overlapWithHistoricalProviderIDs':0,'models':dict(provider),'providerInputTokenPairs':matched,'exactProviderTokenMatchPairs':sum(m['exactProviderInputTokenMatch'] for m in matched),'historicalSealedFilesUnchanged':checked,'newUnityRuns':0,'automaticRetries':0}
    c.write_new(A/'VERIFICATION.json',result)
    files=[p for p in e.OUT.rglob('*') if p.is_file()]+[p for p in e.PRE.rglob('*') if p.is_file()]+[p for p in A.rglob('*') if p.is_file()]
    c.write_new(A/'SEALED_ARTIFACTS.json',{'schema':'information-control-evidence-manifest-v1','excludes':'this manifest and mutable notebook/status/writing files','files':[{'path':str(p.relative_to(R)).replace('\\','/'),'sha256':e.sha(p),'bytes':p.stat().st_size} for p in sorted(files)]})
    print(json.dumps({k:v for k,v in result.items() if k!='providerInputTokenPairs'}));return result
if __name__=='__main__':audit()
