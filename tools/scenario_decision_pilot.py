"""Isolated scenario-v2 payload exporter and response auditor. No network or Unity."""
import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from individual_analysis import SYSTEM, answer, strict_json

ROOT=Path(__file__).resolve().parents[1]
DESIGN=ROOT/'research/scenario_decisions_v2'
VERSION='scenario-pilot-offline-v1'
FACTORS=('nearbyAgentCount','exitNonBlockage','unwillingness','volunteerCost','failureCost')

def require(ok,message):
    if not ok:raise ValueError(message)

def digest(data):return hashlib.sha256(data).hexdigest()
def encode(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')

def sections(text):
    text=text.replace('\r\n','\n')
    chunks=text.split('\n## ')
    return {c.split('\n',1)[0].strip():c.split('\n',1)[1].strip() for c in chunks[1:]}

def instruction(prompt,wording,q=None):
    parts=sections(prompt)
    shared=parts['Shared instructions']
    # Transport implementation advice belongs in the artifact, not in the model task.
    shared=shared.replace(' Use the frozen verified transport schema and serialization, not an unvalidated replacement schema.','')
    if q is not None:
        old="Other pedestrians' choices and their probabilities are unknown."
        require(shared.count(old)==1,'Missing unique belief insertion point')
        belief=(f'The probability that all other eligible pedestrians decline is q={q:g}. '
            'This is the joint probability, not each individual\'s probability. '
            'For this diagnostic, choose the action with the larger risk-neutral expected payoff according to the supplied table. '
            'Either action is acceptable if the expected payoffs are equal.')
        shared=shared.replace(old,belief)
    additions={'numeric':'Numeric wording addition','contextual_equivalent':'Contextual equivalent addition'}
    require(wording in additions,'Unknown wording')
    return shared+'\n\n'+parts[additions[wording]]+'\n\n'

def payload(cell,prompt,wording,model,q=None):
    require(model=='gpt-6-luna','Only previous study profile implemented; availability must be checked before execution')
    obs='; '.join(f'{name}={cell[key]:g}' for name,key in zip(('X','tau','omega','cv','av'),FACTORS))+'.'
    schema={'type':'object','properties':{'explanation':{'type':'string'},'decision':{'type':'string'}},'required':['explanation','decision'],'additionalProperties':False}
    return {'model':model,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':instruction(prompt,wording,q)+'Observation:\n'+obs}],
            'temperature':.15,'max_completion_tokens':220,'reasoning_effort':'none',
            'response_format':{'type':'json_schema','json_schema':{'name':'paper_individual_choice','strict':True,'schema':schema}}}

def expected(cell,q):
    diff=q*cell['failureCost']-cell['volunteerCost']
    return None if abs(diff)<1e-12 else 'participate' if diff>0 else 'decline_assistance'

def build(plan,prompt,model='gpt-6-luna'):
    require(plan['status']=='design_prepared_not_implemented_not_preregistered','Unexpected source design state')
    require(len(plan['cells'])==6,'Expected six cells')
    for c in plan['cells']:
        require(all(type(c[k]) in (float,int) and math.isfinite(c[k]) for k in FACTORS),'Invalid numeric input')
        require(0<c['volunteerCost']<c['failureCost']<1 and c['nearbyAgentCount']==10 and c['exitNonBlockage']==.4 and c['unwillingness']==5,'Domain/fixed-factor drift')
        require(math.isclose(c['volunteerCost']/c['failureCost'],c['costRatio'],abs_tol=1e-12),'Ratio mismatch')
    trials=[]
    def add(c,phase,wording,rep,q=None):
        tid=f"{phase}_{c['cell']}_{wording}"+(f'_q{round(q*100):02d}' if q is not None else '')+f'_r{rep:02d}'
        request=payload(c,prompt,wording,model,q)
        trial={'id':tid,'phase':phase,'cell':c['cell'],'wording':wording,'repetition':rep,'observation':{k:c[k] for k in FACTORS},'qAllOthersDecline':q,'expectedDiagnosticAction':expected(c,q) if q is not None else None,'payload':request,'payloadSHA256':digest(encode(request))}
        trials.append(trial)
    for c in plan['cells']:
        for q in [.05,.5,.95]:
            for rep in [1,2]:add(c,'gate','numeric',rep,q)
        for wording in ['numeric','contextual_equivalent']:
            for rep in range(1,11):add(c,'free',wording,rep)
    ordered=[]
    for phase,seed in [('gate',2026111601),('free',2026111602)]:
        group=[t for t in trials if t['phase']==phase];random.Random(seed).shuffle(group);ordered+=group
    require(len(ordered)==156 and len({t['id'] for t in ordered})==156,'Incorrect trial counts/IDs')
    return ordered

def export(folder):
    require(not folder.exists(),'Output already exists; preserve previous exports')
    raw=(DESIGN/'pilot-plan.draft.json').read_bytes();promptRaw=(DESIGN/'PROMPT_CANDIDATE.en.md').read_bytes()
    trials=build(strict_json(raw.decode()),promptRaw.decode())
    folder.mkdir(parents=True)
    for name,data in [('design.snapshot.json',raw),('prompt.snapshot.en.md',promptRaw),('trials.json',encode(trials))]:
        (folder/name).write_bytes(data)
    receipt={'schema':VERSION,'status':'offline_preparation_only','preregistered':False,'executionEnabled':False,'modelAvailabilityVerified':False,'newAPICalls':0,'newUnityRuns':0,'trials':156,'gate':36,'free':120,'model':'gpt-6-luna','orderSeeds':[2026111601,2026111602],'sourceSHA256':digest(Path(__file__).read_bytes()),'files':{n:digest((folder/n).read_bytes()) for n in ['design.snapshot.json','prompt.snapshot.en.md','trials.json']}}
    (folder/'OFFLINE_RECEIPT.json').write_bytes(encode(receipt))
    return verify(folder)

def review_sheet(folder,target):
    """Prepare all planned rows, without pretending any response was observed."""
    import csv
    verify(folder)
    require(not target.exists(),'Preserve existing review sheets')
    trials=strict_json((folder/'trials.json').read_text(encoding='utf-8'))
    fields=['requestID','phase','cell','wording','rawSHA256','rawAction','parsedAction','reasonText',
            'personal_cost','avoid_unhandled_loss','reliance_on_others','shared_benefit','guaranteed_payoff',
            'context_use','unsupported_assumption','action_reason_conflict','insufficient_reason',
            'evidenceSpans','arithmeticIssue','reviewer','codebookVersion','uncertaintyNote','reviewStatus']
    with target.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for t in trials:w.writerow({'requestID':t['id'],'phase':t['phase'],'cell':t['cell'],'wording':t['wording'],'reviewStatus':'not_collected'})
    return {'plannedRows':len(trials),'observedResponses':0,'path':str(target)}

def verify(folder):
    rec=strict_json((folder/'OFFLINE_RECEIPT.json').read_text(encoding='utf-8'))
    require(rec['executionEnabled'] is False and rec['preregistered'] is False,'Offline export cannot authorize execution')
    require(rec['sourceSHA256']==digest(Path(__file__).read_bytes()),'Exporter source drift')
    for name,sha in rec['files'].items():
        require(Path(name).name==name,'Unsafe snapshot path')
        require(digest((folder/name).read_bytes())==sha,'Snapshot hash mismatch: '+name)
    trials=strict_json((folder/'trials.json').read_text(encoding='utf-8'))
    rebuilt=build(strict_json((folder/'design.snapshot.json').read_text(encoding='utf-8')),(folder/'prompt.snapshot.en.md').read_text(encoding='utf-8'))
    require(trials==rebuilt,'Payload, diagnostic key or order drift')
    return {'passed':True,'plannedChoices':len(trials),'newAPICalls':0,'executionEnabled':False}

def audit_reply(trial,raw):
    body,envelope=answer(raw)
    require(body is not None,'Invalid raw response; no repair or action inferred from reason')
    require(bool(body['explanation'].strip()),'Empty explanation')
    require(envelope.get('model')==trial['payload']['model'],'Provider model drift')
    require(isinstance(envelope.get('id'),str) and bool(envelope['id']),'Missing provider response ID')
    willing=body['decision']=='participate'
    return {'rawSHA256':digest(raw.encode()),'providerID':envelope['id'],'rawAction':body['decision'],'willing':willing,'explanation':body['explanation'],'diagnosticCorrect':None if trial['phase']=='free' or trial['expectedDiagnosticAction'] is None else body['decision']==trial['expectedDiagnosticAction'],'reasonReviewed':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['export','verify','review-sheet']);parser.add_argument('folder',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.command=='review-sheet':
        require(args.output is not None,'Provide --output for the blank review sheet');result=review_sheet(args.folder,args.output)
    else:result=export(args.folder) if args.command=='export' else verify(args.folder)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
