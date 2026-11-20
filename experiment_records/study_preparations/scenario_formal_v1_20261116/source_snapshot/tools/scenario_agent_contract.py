"""Stage-3 two-layer individual decision contract; no networking or Unity imports."""
import csv
import hashlib
import json
import math
from pathlib import Path
from individual_analysis import answer, strict_json

ROOT=Path(__file__).resolve().parents[1]
DESIGN=ROOT/'research/scenario_decisions_v2'
ANALYSIS=ROOT/'experiment_records/data/analysis/scenario_physical_v2_20261116_final'
VERSION='scenario-individual-contract-v3'
PROTOCOL='paper-choice-response-v3'
MODEL='gpt-6-luna'
PHASES=('abstract_diagnostic','physical_diagnostic','abstract_choice','physical_choice')
SYSTEM='You represent one pedestrian making an individual assistance decision. Respond with strict JSON only.'

def require(condition,message):
    if not condition:raise ValueError(message)
def data(value):return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def sha(value):return hashlib.sha256(value).hexdigest()
def read(path):return strict_json(Path(path).read_text(encoding='utf-8-sig'))
def write_new(path,value):
    with Path(path).open('xb') as f:f.write(data(value));f.flush();__import__('os').fsync(f.fileno())

COMMON='''You decide only your own willingness to assist with movable obstacles during a simulated evacuation. Actions are participate and decline_assistance. Both are allowed. You cannot assign other people or control movement. Willingness does not guarantee activation, obstacle movement or faster evacuation. Do not invent injuries, deadlines, alternative exits or commitments from other pedestrians. You have no personal history. Give a brief explanation based on the supplied information. Explanation text describes your stated considerations, not a report of hidden calculations.
Return exactly a JSON object with explanation and decision. decision must be participate or decline_assistance.'''
ABSTRACT='''This task uses the reference volunteer game's normalized dimensionless utilities, not measured travel times or money. Baseline utility is 1. Participation gives 1-cv regardless of others. Declining gives 1 if at least one other player participates, and 1-av if all other players decline. There is no extra participation bonus. X includes you. tau is the unblocked fraction of the relevant exit. omega is a separate coefficient in the reference behavioral law, not injury risk, personality or a payoff deduction. The reference adjusts behavior separately from the base payoff table. Do not reproduce its probability or infer a utility loss from tau or omega.'''
ABSTRACT_WORDING={
    'numeric':'cv is your personal utility cost. av is your loss if nobody participates.',
    'contextual_equivalent':'Assisting imposes the personal burden cv. Leaving the obstacle without any volunteer carries the loss av. These descriptions add no extra physical effects to the same payoff table.'}
PHYSICAL='''This is an extension using capped evacuation time, not the reference game's payoff table or participation formula. Population is 10 and there are five movable obstacles. You are the focal pedestrian, ID 0, in a fixed grid-layout family. Initial tau describes the relevant exit, not every path. The grid uses eight-neighbor movement. Partial blockage in these layouts still permits evacuation without handling. M is the work-progress interval per manipulation unit, not total handling time, weight, seconds or injury risk. Only the simulator activates candidates and executes movement.
Your own time utility, if needed, is U=1-min(T,300)/301. Earlier evacuation gives higher utility. The number 301 is a common normalization, not a human psychological scale. Helping gives no separate reward. Other pedestrians' time outcomes are reported separately, never added as a reward to your own utility. Handling burden and net evacuation delay are different quantities.'''
UNCERTAINTY='''The forecasts below are estimates from six earlier development seeds, not this decision's future outcome, human measurements, or guarantees. Means and observed ranges describe variation across those six seeds, not confidence bounds. Non-evacuation by step 300 counts as 300. The two background profiles are hypothetical endpoints: all other nine decline, or all other nine are willing. Willingness is not actual handling. Mixed profiles were not calibrated. Do not treat 'all others willing' as 'at least one other willing', infer their probability, or assume an endpoint describes the current situation.'''

def profile():
    # Preserve the historical profile without claiming current provider support.
    return dict(model=MODEL,temperature=.15,reasoning_effort='none',max_completion_tokens=220)

def payload(text):
    schema={'type':'object','properties':{'explanation':{'type':'string'},'decision':{'type':'string'}},'required':['explanation','decision'],'additionalProperties':False}
    return {**profile(),'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':COMMON+'\n\n'+text}],
            'response_format':{'type':'json_schema','json_schema':{'name':'paper_individual_choice','strict':True,'schema':schema}}}

def expected_utility(cv,av,q):
    delta=q*av-cv
    return None if abs(delta)<1e-12 else 'participate' if delta>0 else 'decline_assistance'

def expected_time(a,b):
    return None if abs(a-b)<1e-10 else 'participate' if a<b else 'decline_assistance'

def load_inputs():
    # The stage-2 receipt binds these documents; input manifests also bind the raw calibration.
    receipt=read(DESIGN/'STAGE2_RECEIPT.json')
    require(sha((DESIGN/'stage2-scenario-specification.json').read_bytes())==receipt['specSHA256'],'Stage2 specification drift')
    for item in receipt['files']:
        path=(ROOT/item['path']).resolve();require(path.is_relative_to(ROOT),'Unsafe stage2 source path')
        require(sha(path.read_bytes())==item['sha256'],'Stage2 analysis drift')
    spec=read(DESIGN/'stage2-scenario-specification.json');abstract=read(DESIGN/'pilot-plan.draft.json')['cells']
    require(len(spec['cells'])==8 and len(abstract)==6,'Scenario matrix drift')
    with (ANALYSIS/'agent-costs.csv').open(encoding='utf-8-sig',newline='') as f:agents=list(csv.DictReader(f))
    return spec,abstract,agents

def forecasts(cell,agents):
    table=[]
    for background in ('others_decline','others_willing'):
        for action in ('participate','decline_assistance'):
            source=cell['empiricalConditionalPayoffs'][background][action]
            jobs=source['sourceJobs'];require(len(jobs)==len(set(jobs))==6,'Expected six source jobs')
            own=[];others=[]
            for job in jobs:
                group=[a for a in agents if a['job']==job]
                require(len(group)==10 and {int(a['agent']) for a in group}==set(range(10)),'Incomplete source agents')
                own.append(float(next(a['cappedExit'] for a in group if a['agent']=='0')))
                others.append(sum(float(a['cappedExit']) for a in group if a['agent']!='0')/9)
            avg=sum(own)/6
            require(math.isclose(avg,source['meanCappedOwnExitStep'],abs_tol=1e-9),'Forecast/source mismatch')
            require(math.isclose(1-avg/301,source['normalizedTimeUtility'],abs_tol=1e-12),'Time utility mismatch')
            table.append({'otherProfile':background,'ownChoice':action,
                'ownCappedExitSteps':{'mean':round(avg,6),'observedMin':min(own),'observedMax':max(own)},
                'otherNineMeanCappedExitSteps':{'mean':round(sum(others)/6,6),'observedMin':round(min(others),6),'observedMax':round(max(others),6)},
                'developmentSeedCount':6})
    return table

def build_cases(spec,abstract,agents):
    cases=[]
    def add(case_id,phase,scenario,condition,text,expected=None,metadata=None):
        request=payload(text)
        require(len(data(request))<40000,'Prompt exceeds preflight byte ceiling')
        cases.append({'caseID':case_id,'phase':phase,'scenario':scenario,'information':condition,'payload':request,
                      'payloadSHA256':sha(data(request)),'diagnosticExpectedAction':expected,'metadata':metadata or {}})
    for cell in abstract:
        cv=cell['volunteerCost'];av=cell['failureCost']
        require(0<cv<av<1 and math.isclose(cv/av,cell['costRatio'],abs_tol=1e-12),'Illegal abstract costs')
        obs={k:cell[k] for k in ('nearbyAgentCount','exitNonBlockage','unwillingness','volunteerCost','failureCost')}
        for q in (.05,.5,.95):
            text=ABSTRACT+'\nFor this diagnostic only, the joint probability that ALL other players decline is q='+str(q)+'. It is not an individual probability. Choose the action with greater risk-neutral expected utility. Either action is acceptable on an exact tie.\nObservation:\n'+json.dumps(obs)
            add(f"AD_{cell['cell']}_Q{round(q*100):02d}",'abstract_diagnostic',cell['cell'],'known_joint_belief',text,expected_utility(cv,av,q),{'qAllOthersDecline':q})
        for wording in ABSTRACT_WORDING:
            text=ABSTRACT+'\n'+ABSTRACT_WORDING[wording]+"\nOther players' current choices and their probabilities are unknown. Choose for yourself under these rules.\nObservation:\n"+json.dumps(obs)
            add(f"AC_{cell['cell']}_{wording}",'abstract_choice',cell['cell'],wording,text)
    for cell in spec['cells']:
        b=int(cell['id'][1]);m=cell['manipulationStepsPerWorkUnit']
        require(b in (2,3,4,5) and m in (1,4) and cell['population']==10,'Illegal physical cell')
        require(math.isclose(cell['initialExitNonBlockage'],1-b/5,abs_tol=1e-12),'Geometry tau mismatch')
        observation={'initialExitNonBlockage':cell['initialExitNonBlockage'],'population':10,'totalMovableObstacles':5,'workProgressIntervalM':m,'horizon':300,'timeUnit':'simulation ticks, not human seconds'}
        f=forecasts(cell,agents)
        base=PHYSICAL+'\nObservation:\n'+json.dumps(observation)
        for info in ('geometry_only','calibrated_forecast'):
            text=base+"\nOther pedestrians' willingness is unknown. Make your personal choice."
            if info=='geometry_only':text+=' No numerical future-time forecasts are supplied. Do not invent them.'
            else:text+='\n'+UNCERTAINTY+'\nForecasts:\n'+json.dumps(f,ensure_ascii=False)
            add(f"PC_{cell['id']}_{info}",'physical_choice',cell['id'],info,text,metadata={'derivedForecasts':info=='calibrated_forecast','notOriginalFormulaTask':True})
        for background in ('others_decline','others_willing'):
            pair=[x for x in f if x['otherProfile']==background]
            a=next(x['ownCappedExitSteps']['mean'] for x in pair if x['ownChoice']=='participate')
            d=next(x['ownCappedExitSteps']['mean'] for x in pair if x['ownChoice']=='decline_assistance')
            text=base+'\n'+UNCERTAINTY+'\nFor this comprehension diagnostic only, use the specified background '+background+'. Choose the action with the lower supplied MEAN own capped exit steps, ignoring other peoples\' outcomes for this arithmetic check. Either action is acceptable if the means tie. This is a comparison of development estimates, not guaranteed future performance.\nForecasts:\n'+json.dumps(pair)
            add(f"PD_{cell['id']}_{background}",'physical_diagnostic',cell['id'],background,text,expected_time(a,d),{'notOriginalFormulaTask':True})
    require(len(cases)==62 and len({c['caseID'] for c in cases})==62,'Expected 62 unique contract specimens')
    return cases

def source_paths():
    return [Path(__file__),ROOT/'tools/scenario_agent_transport.py',ROOT/'tools/individual_analysis.py',ROOT/'tools/individual_sampling.py',DESIGN/'stage2-scenario-specification.json',DESIGN/'pilot-plan.draft.json',DESIGN/'STAGE2_RECEIPT.json',ANALYSIS/'agent-costs.csv',ANALYSIS/'results.json']

def prepare(folder):
    require(not folder.exists(),'Preserve existing interface bundle')
    cases=build_cases(*load_inputs());folder.mkdir(parents=True)
    write_new(folder/'cases.json',cases)
    manifest={'schema':VERSION,'status':'interface_contract_only_not_experiment','modelAvailabilityVerified':False,
        'newAPICalls':0,'newUnityRuns':0,'phases':{phase:sum(c['phase']==phase for c in cases) for phase in PHASES},
        'inputs':{str(f.relative_to(ROOT)).replace('\\','/'):sha(f.read_bytes()) for f in source_paths()},'casesSHA256':sha((folder/'cases.json').read_bytes()),
        'sampling':'One specimen per condition, not a pilot sample plan. Repetitions and phase registration must precede collection.',
        'sources':['https://developers.openai.com/api/docs/guides/structured-outputs','https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create','https://developers.openai.com/api/docs/guides/error-codes']}
    write_new(folder/'INTERFACE.json',manifest)
    return verify(folder)

def verify(folder):
    manifest=read(folder/'INTERFACE.json');require(manifest['schema']==VERSION,'Wrong interface version')
    for name,digest in manifest['inputs'].items():
        f=(ROOT/name).resolve();require(f.is_relative_to(ROOT),'Unsafe input path')
        require(sha(f.read_bytes())==digest,'Interface input/source drift: '+name)
    require(sha((folder/'cases.json').read_bytes())==manifest['casesSHA256'],'Case manifest drift')
    cases=read(folder/'cases.json');require(cases==build_cases(*load_inputs()),'Prompt, forecast or answer-key drift')
    return {'passed':True,'contractSpecimens':len(cases),'phases':manifest['phases'],'newAPICalls':0}

def parse_reply(case,raw):
    require(isinstance(raw,str),'Response must be UTF-8 text')
    body,envelope=answer(raw)
    require(body is not None,'invalid_response_contract')
    require(body['explanation'].strip() and len(body['explanation'])<=16000,'missing_or_oversize_explanation')
    require(envelope.get('model')==case['payload']['model'],'provider_model_drift')
    require(isinstance(envelope.get('id'),str) and envelope['id'].strip(),'missing_provider_id')
    expected=case['diagnosticExpectedAction']
    return {'rawSHA256':sha(raw.encode('utf-8')),'providerID':envelope['id'],'rawAction':body['decision'],
            'parsedAction':body['decision'],'willing':body['decision']=='participate','explanation':body['explanation'],
            'diagnosticActionCorrect':None if 'diagnostic' not in case['phase'] or expected is None else body['decision']==expected,
            'tie': 'diagnostic' in case['phase'] and expected is None,'reasonReviewed':False}

def consume(case,raw):
    parsed=parse_reply(case,raw)
    # Typed adapter suitable for a future Unity bridge. Never executes grid movement itself.
    return {'agentID':0,'willing':parsed['willing'],'action':parsed['rawAction'],'explanation':parsed['explanation'],
            'caseID':case['caseID'],'contractVersion':VERSION,'source':'validated_individual_response','controlsOtherAgents':False}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','verify']);parser.add_argument('folder',type=Path);args=parser.parse_args()
    print(json.dumps(prepare(args.folder) if args.command=='prepare' else verify(args.folder),indent=2))
