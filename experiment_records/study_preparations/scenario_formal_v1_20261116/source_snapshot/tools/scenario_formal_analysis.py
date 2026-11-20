"""Prespecified block-based descriptive analysis for P030; no network or simulations."""
import csv,json,random
from pathlib import Path
import scenario_agent_contract as c
import scenario_agent_transport as t
import scenario_formal as f
import scenario_reason_coding as reason

def mean(xs):return sum(xs)/len(xs)

def contrasts(trials,choices,reference):
    c.require(len(trials)==len(choices)==840 and len({x['trialID'] for x in trials})==840,'Complete formal matrix required')
    blocks=[]
    for block in range(1,31):
        selected=[x for x in trials if x['block']==block]
        c.require(len(selected)==28,'Incomplete scheduling block')
        table={(x['case']['phase'],x['case']['scenario'],x['case']['information']):choices[x['trialID']] for x in selected}
        a=[]
        for scale in ('A30','A70'):
            for wording in ('numeric','contextual_equivalent'):
                high=scale+'_R90';low=scale+'_R10'
                a.append(table[('abstract_choice',high,wording)]-table[('abstract_choice',low,wording)]-(reference[high]-reference[low]))
        b=[table[('physical_choice',f'B{layout}_M{work}','calibrated_forecast')]-table[('physical_choice',f'B{layout}_M{work}','geometry_only')] for layout in (2,3,4,5) for work in (1,4)]
        overall=mean([table[('abstract_choice',cell,wording)]-reference[cell] for cell in reference for wording in ('numeric','contextual_equivalent')])
        blocks.append({'block':block,'primaryA':mean(a),'primaryB':mean(b),'secondaryAbstractOverall':overall})
    return blocks

def quantile(values,p):
    v=sorted(values);pos=(len(v)-1)*p;lo=int(pos);hi=min(lo+1,len(v)-1);return v[lo]+(pos-lo)*(v[hi]-v[lo])

def intervals(blocks):
    c.require(len(blocks)==30,'Thirty complete blocks required')
    rng=random.Random(2026111662);draws={'primaryA':[],'primaryB':[]}
    for _ in range(5000):
        sample=[blocks[rng.randrange(30)] for _ in range(30)]
        for key in draws:draws[key].append(mean([x[key] for x in sample]))
    return {key:{'estimate':mean([x[key] for x in blocks]),'pointwiseDescriptive95':[quantile(values,.025),quantile(values,.975)]} for key,values in draws.items()}

def audit(run):
    with f.bound_verifier():reg=t.verify_registration(run/'registration.snapshot.json')
    counts={'planned':len(reg['trials']),'claims':0,'results':0,'technicalValid':0,'technicalInvalid':0,'unknownClaims':0,'completedMarker':(run/'COMPLETE.json').exists(),'formalInferenceAvailable':False}
    for trial in reg['trials']:
        folder=run/'trials'/trial['trialID'];claim=(folder/'CLAIM.json').exists();result=(folder/'result.json').exists()
        counts['claims']+=claim;counts['results']+=result;counts['unknownClaims']+=claim and not result
        if result:
            item=c.read(folder/'result.json');counts['technicalValid']+=item['valid'];counts['technicalInvalid']+=not item['valid']
    return counts

def analyze(run,out):
    c.require(not out.exists(),'Preserve prior formal analysis')
    counts=audit(run);c.require(counts['completedMarker'] and counts['technicalValid']==counts['planned']==840 and not counts['technicalInvalid'],'Incomplete/invalid formal batch: descriptive audit only, never rescue or pool')
    completion=c.read(run/'COMPLETE.json');c.require(completion['execution']=='live' and completion['completed']==840,'Wrong completion provenance/count')
    with f.bound_verifier():
        reg=t.verify_registration(run/'registration.snapshot.json');coded=reason.validate(run,run/'coding.json',True)
    c.require(reg['execution']=='live','Synthetic validation is not formal evidence')
    c.require(c.read(run/'FORMAL_LOCK_BINDING.json')==c.read(Path(reg['sealPath'])),'Missing or changed formal source binding')
    choices={};seen=set();catalog=[]
    prior=set()
    pilot_catalog=c.ROOT/'experiment_records/data/analysis/scenario_pilot_v1_20261116/TRIAL_CATALOG.csv'
    with pilot_catalog.open(encoding='utf-8-sig',newline='') as stream:prior={x['providerID'] for x in csv.DictReader(stream)}
    for trial in reg['trials']:
        folder=run/'trials'/trial['trialID'];raw=(folder/'response.raw').read_bytes();item=c.read(folder/'result.json')
        c.require(item['valid'] and item['execution']=='live' and item['httpStatus']==200 and c.sha(raw)==item['responseSHA256'],'Invalid raw formal record')
        parsed=c.parse_reply(trial['case'],raw.decode());c.require(parsed==item['parsed'],'Formal parsed response drift')
        c.require(parsed['providerID'] not in seen|prior,'Provider response overlaps pilot or formal');seen.add(parsed['providerID'])
        choices[trial['trialID']]=int(parsed['willing'])
        catalog.append({'trialID':trial['trialID'],'block':trial['block'],'phase':trial['case']['phase'],'scenario':trial['case']['scenario'],'information':trial['case']['information'],'action':parsed['rawAction'],'providerID':parsed['providerID'],'rawSHA256':item['responseSHA256']})
    reference={x['cell']:x['referenceProbability'] for x in c.read(c.DESIGN/'pilot-plan.draft.json')['cells']}
    blocks=contrasts(reg['trials'],choices,reference);estimates=intervals(blocks)
    out.mkdir(parents=True)
    c.write_new(out/'primary-results.json',{'campaignID':f.CAMPAIGN,'n':840,'blocks':30,'estimates':estimates,'bootstrapIterations':5000,'bootstrapSeed':2026111662,'scope':'Pointwise descriptive intervals conditional on scheduling-block exchangeability and fixed prompts/model/scenarios. No confirmatory significance, human independence or joint coverage claim.'})
    c.write_new(out/'block-contrasts.json',blocks)
    with (out/'TRIAL_CATALOG.csv').open('x',encoding='utf-8-sig',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(catalog[0]));w.writeheader();w.writerows(catalog)
    with f.bound_verifier():reason.summarize(run,run/'coding.json',out/'reason-summary.json',True)
    c.write_new(out/'COMPLETE.json',{'campaignID':f.CAMPAIGN,'formalData':True,'trials':840,'reviewed':coded['reviewed'],'primarySHA256':c.sha((out/'primary-results.json').read_bytes())})
    return estimates

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['audit','analyze']);p.add_argument('run',type=Path);p.add_argument('--output',type=Path);args=p.parse_args()
    if args.command=='analyze':c.require(args.output is not None,'Provide --output');result=analyze(args.run,args.output)
    else:result=audit(args.run)
    print(json.dumps(result,indent=2))
