"""Prospective scenario formal lock and guarded adapter; no API without explicit formal opt-in."""
from contextlib import contextmanager
from pathlib import Path
import argparse,datetime,json,random,shutil
import scenario_agent_contract as c
import scenario_agent_transport as t
import scenario_reason_coding as reason

CAMPAIGN='P030_SV3_20261116'
BUNDLE=c.ROOT/'experiment_records/data/preparation/scenario_agent_stage3_20261116'
PILOT=c.ROOT/'experiment_records/data/scenario_pilot_v1_20261116'
SCHEMA='scenario-formal-registration-v1'

def source_files():
    return [Path(__file__),c.ROOT/'tools/scenario_formal_analysis.py',c.ROOT/'tools/scenario_agent_contract.py',
        c.ROOT/'tools/scenario_agent_transport.py',c.ROOT/'tools/scenario_reason_coding.py',c.ROOT/'tools/individual_analysis.py',
        c.ROOT/'tools/individual_sampling.py',c.DESIGN/'reason-codebook.v3.json',c.DESIGN/'stage2-scenario-specification.json']

def design():
    return {'schema':'scenario-formal-design-v1','campaignID':CAMPAIGN,'registrationID':'P-030','dateLocal':'2026-11-16',
        'scope':'Pilot-informed formal descriptive replication, individual choices and stated reasons; no new group simulations or human participants',
        'questions':{'A':'How does LLM willingness change with the relative cost, compared with the adjusted reference formula under the shared base payoff specification?',
                     'B':'How does willingness change with supplied earlier-development time forecasts in the physical extension?'},
        'blocks':30,'conditionsPerBlock':28,'conditions':{'abstract':12,'physical':16},'totalChoices':840,
        'orderSeed':2026111661,'sampling':'One fresh request per condition in each of30 scheduling blocks; shuffle all28 within each block, then concatenate blocks. Blocks are time/scheduling units, not people or paired simulation trajectories.',
        'sampleRationale':'Thirty per condition balances full scenario coverage and full-text reason review, not a formal power guarantee. Independent-binomial Wilson half-width at p=.5,n30 is about.1685 as a scale reference only; model requests need not be independent. Primary summaries average per-block contrasts; no result-driven extension.',
        'primaryA':{'name':'relative_cost_response_difference','formula':'Per block, mean over av(.3,.7) and wording(numeric,contextual): (Y_R90-Y_R10)-(pRef_R90-pRef_R10); then mean over30 blocks','unit':'probability difference','reference':'Adjusted reference-law probability, not a global optimum or a complete belief specification supplied to the LLM'},
        'primaryB':{'name':'forecast_minus_geometry','formula':'Per block, equal mean over8 physical scenarios of Y_forecast-Y_geometry; then mean over30 blocks','unit':'probability difference','scope':'Information-and-prompt condition difference, not isolated reasoning, human realism, group evacuation benefit or proof of mediation'},
        'intervals':{'method':'Resample whole scheduling blocks with replacement, recomputing mean contrast','iterations':5000,'seed':2026111662,'coverage':'Pointwise descriptive95%, conditional on these model/prompt/scenarios and exchangeable scheduling blocks','confirmatoryPValues':False,'multiplicity':'Two separately named descriptive summaries, no joint95% coverage or significance claims. All other cell, scale, wording, layout/work or reason comparisons secondary/exploratory.'},
        'secondary':['All28 cell willingness counts/n30','Abstract mean LLM-minus-reference difference','Full three-level cost profile, scale and wording patterns','Physical eight per-scenario information contrasts','Twelve reason labels and quality fields, separated by task/information; no hidden-reasoning or motive causality'],
        'reasonAnalysis':{'version':'scenario-reasons-v3','coverage':'All840 valid readable reasons, exact spans and named assistant reviewer; no second human agreement claim','denominator':'Reviewed eligible reasons per task/scenario/information, with planned/readable/reviewed/unreviewed shown','quality':'Retain and code insufficient, contradictory, arithmetic and unsupported-info reasons; do not repair/relabel raw action or exclude inconvenient valid choices','gate':'Existing live68-choice P029 comprehension/reason gates reused only for identical hashes/profile; excluded from formal estimates. Successful gates do not imply all free explanations are correct.'},
        'resources':{'maxAttempts':840,'attemptsPerTrial':1,'maxGeneratedTokens':184800,'timeoutSeconds':60,'wallSeconds':10800,'parallelWorkers':1,'automaticRetries':0,'cost':'Request/token limits, no dollar-cost guarantee'},
        'failureRule':'First technical invalid, unknown network result, source/profile drift, repeated provider ID or budget/time stop ends the campaign. Preserve all partial records; mark formal incomplete, no automatic refill/restart or pooling. A valid free reason-quality problem is retained and coded, not a technical invalid.',
        'exclusions':{'P029':'All208 pilot replies and their208 provider IDs excluded; source forecasts are fixed stimulus estimates, not new independent physical samples','P028':'Original1140-run study remains separate','physicalCalibration':'174 development Unity runs stay development evidence, not formal outcome trials'},
        'stimulusPolicy':'Retain all6 abstract cells x2 wordings and8 physical scenarios x2 information conditions, including saturated conditions; no new maps, rewards, q, deadlines, personality, history or model changes',
        'limits':['No validated mapping from time to original Eq20 utility; physical extension analyzed separately','Only six earlier geometry seeds support fixed forecast means/ranges; no general forecast-accuracy claim','Same alias does not guarantee immutable backend; record raw provider metadata','Independent-binomial or exchangeable-block assumptions are not established human sampling','Pilot informed hypotheses, so this is a prospective replication after development, not an untouched initial hypothesis test'],
        'collectionAutomaticallyStarted':False}

def make_trials(cases,d):
    selected=[x for x in cases if x['phase'] in ('abstract_choice','physical_choice')]
    c.require(len(selected)==28,'Keep all28 free conditions')
    rng=random.Random(d['orderSeed']);trials=[]
    for block in range(1,d['blocks']+1):
        group=[{'trialID':f'{CAMPAIGN}_b{block:03d}_'+x['caseID'],'case':x,'block':block,'repetition':block} for x in selected]
        rng.shuffle(group);trials+=group
    return trials

def freeze(folder,validation_only=False):
    c.require(not folder.exists(),'Preserve existing formal lock')
    c.verify(BUNDLE);d=design();cases=c.read(BUNDLE/'cases.json');trials=make_trials(cases,d)
    gates=[t.gate_evidence(PILOT/phase,PILOT/phase/'gate-review.json',BUNDLE) for phase in ('abstract_diagnostic','physical_diagnostic')]
    pilot_ids=set()
    for phase in ('abstract_diagnostic','physical_diagnostic','abstract_choice','physical_choice'):
        p=PILOT/phase;c.require((p/'COMPLETE.json').exists(),'Pilot incomplete')
        reason.validate(p,p/'coding.json',True)
        pilot_ids|={row['trialID'] for row in reason.source(p)[1]}
    c.require(not pilot_ids&{x['trialID'] for x in trials},'Pilot/formal trial ID overlap')
    folder.mkdir(parents=True)
    c.write_new(folder/'design.json',d)
    registration={'schema':SCHEMA,'registeredAtUtc':t.now(),'purpose':'P030 formal individual scenario comparison, prospectively locked after P029; not a pilot or human study',
        'campaignID':CAMPAIGN,'sealPath':str((folder/'LOCK.json').resolve()),'bundlePath':str(BUNDLE),'bundleSHA256':c.sha((BUNDLE/'INTERFACE.json').read_bytes()),
        'phase':'formal_mixed_choice','execution':'synthetic_test' if validation_only else 'live','model':c.MODEL,'endpoint':t.ENDPOINT,'attemptsPerTrial':1,
        'maxAttempts':840,'maxGeneratedTokens':184800,'maxPayloadBytes':sum(len(c.data(x['case']['payload'])) for x in trials),
        'timeoutSeconds':60,'wallSeconds':10800,'automaticRetries':0,'gateEvidence':gates,'trials':trials}
    c.write_new(folder/'registration.json',registration)
    bindings={str(f.relative_to(c.ROOT)).replace('\\','/'):c.sha(f.read_bytes()) for f in source_files()}
    descriptor={'schema':'scenario-formal-lock-v1','campaignID':CAMPAIGN,'designSHA256':c.sha((folder/'design.json').read_bytes()),
        'registrationSHA256':c.sha((folder/'registration.json').read_bytes()),'sources':bindings,
        'priorPilotCompletionSHA256':c.sha((c.ROOT/'experiment_records/data/analysis/scenario_pilot_v1_20261116/COMPLETE.json').read_bytes()),
        'codebookSHA256':c.sha(reason.CODEBOOK.read_bytes()),'trials':840,'executedAtLock':0,'validationOnly':validation_only}
    descriptor['lockID']=c.sha(c.data(descriptor));c.write_new(folder/'LOCK.json',descriptor)
    snapshots=folder/'source_snapshot';snapshots.mkdir()
    for f in source_files():
        dest=snapshots/f.relative_to(c.ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
    verify(folder/'registration.json')
    return {'locked':True,'choices':840,'conditions':28,'perCondition':30,'newAPICalls':0,'lockID':descriptor['lockID']}

def verify(path,bundle=None):
    reg=c.read(path);c.require(reg['schema']==SCHEMA and reg['campaignID']==CAMPAIGN,'Not this formal registration')
    seal_path=Path(reg['sealPath']).resolve();c.require(seal_path.is_relative_to(c.ROOT),'Unsafe formal seal path')
    seal=c.read(seal_path);unsigned={k:v for k,v in seal.items() if k!='lockID'}
    c.require(c.sha(c.data(unsigned))==seal['lockID'],'Formal seal drift')
    c.require(c.sha(path.read_bytes())==seal['registrationSHA256'],'Registration differs from formal seal')
    folder=seal_path.parent;c.require(c.sha((folder/'design.json').read_bytes())==seal['designSHA256'],'Design drift')
    d=c.read(folder/'design.json');c.require(d==design(),'Analysis, budget or sampling drift')
    for name,digest in seal['sources'].items():
        f=(c.ROOT/name).resolve();c.require(f.is_relative_to(c.ROOT) and c.sha(f.read_bytes())==digest,'Formal source drift: '+name)
    c.require(c.sha(reason.CODEBOOK.read_bytes())==seal['codebookSHA256'],'Formal codebook drift')
    c.verify(BUNDLE);c.require(reg['bundlePath']==str(BUNDLE) and reg['bundleSHA256']==c.sha((BUNDLE/'INTERFACE.json').read_bytes()),'Formal stimulus drift')
    c.require(reg['trials']==make_trials(c.read(BUNDLE/'cases.json'),d),'Formal IDs, payloads or block order changed')
    c.require(type(seal['validationOnly']) is bool,'Invalid seal execution class')
    for k,v in {'phase':'formal_mixed_choice','execution':'synthetic_test' if seal['validationOnly'] else 'live','model':c.MODEL,'endpoint':t.ENDPOINT,'maxAttempts':840,'maxGeneratedTokens':184800,'timeoutSeconds':60,'wallSeconds':10800,'attemptsPerTrial':1,'automaticRetries':0}.items():c.require(reg[k]==v,'Formal transport drift: '+k)
    c.require(reg['maxPayloadBytes']==sum(len(c.data(x['case']['payload'])) for x in reg['trials']),'Payload resource drift')
    c.require({x['phase'] for x in reg['gateEvidence']}=={'abstract_diagnostic','physical_diagnostic'} and len(reg['gateEvidence'])==2,'Missing gates')
    for evidence in reg['gateEvidence']:
        current=t.gate_evidence(Path(evidence['runPath']),Path(evidence['reviewPath']),BUNDLE)
        c.require(current==evidence,'Gate evidence drift')
    return reg

@contextmanager
def bound_verifier():
    """Single-process adapter preserves the frozen transport file and pilot reader."""
    original=t.verify_registration
    def dispatch(path,bundle=None):
        if c.read(path).get('schema')==SCHEMA:return verify(path,bundle)
        return original(path,bundle)
    t.verify_registration=dispatch
    try:yield
    finally:t.verify_registration=original

def run(path,output,confirm=False):
    reg=verify(path);c.require(reg['execution']=='live','Validation-only lock cannot dispatch live')
    c.require(confirm,'Formal collection requires --confirm-formal-execution; freeze/verify do not dispatch')
    with bound_verifier():result=t.run(path,output,confirm_live=True)
    c.write_new(output/'FORMAL_LOCK_BINDING.json',c.read(Path(c.read(path)['sealPath'])))
    return result

def coding(command,run_folder,sheet,target=None,complete=False):
    with bound_verifier():
        if command=='template':return reason.template(run_folder,sheet)
        if command=='validate':return {k:v for k,v in reason.validate(run_folder,sheet,complete).items() if k!='records'}
        return reason.summarize(run_folder,sheet,target,complete)

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('freeze','verify'):
        p=sub.add_parser(name);p.add_argument('path',type=Path)
    p=sub.add_parser('run');p.add_argument('registration',type=Path);p.add_argument('output',type=Path);p.add_argument('--confirm-formal-execution',action='store_true')
    for name in ('template','validate','summarize'):
        p=sub.add_parser(name);p.add_argument('run',type=Path);p.add_argument('sheet',type=Path)
        if name=='summarize':p.add_argument('target',type=Path)
        if name!='template':p.add_argument('--require-complete',action='store_true')
    a=parser.parse_args()
    if a.command=='freeze':result=freeze(a.path)
    elif a.command=='verify':r=verify(a.path);result={'verified':True,'choices':len(r['trials']),'newAPICalls':0}
    elif a.command=='run':result=run(a.registration,a.output,a.confirm_formal_execution)
    else:result=coding(a.command,a.run,a.sheet,getattr(a,'target',None),getattr(a,'require_complete',False))
    print(json.dumps(result,indent=2))
    if result.get('outcome')=='stopped':raise SystemExit(1)
if __name__=='__main__':main()
