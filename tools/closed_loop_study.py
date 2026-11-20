"""Versioned group preparation, calibration and final lock. No implicit final execution."""
import argparse
import collections
import csv
import hashlib
import json
import math
import os
import random
import shutil
import statistics
import subprocess
from pathlib import Path

from analyze_experiments import load_run, read_csv
from individual_analysis import answer, strict_json, require, validate_payload
from shared_progress_io import read_progress

ROOT=Path(__file__).resolve().parents[1]
UNITY=Path('C:/Program Files/Unity/Hub/Editor/6000.0.59f2/Editor/Unity.exe')


def read(p):
    return read_progress(p) if Path(p).name=='progress.json' else strict_json(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source_sha(root=ROOT):
    root=Path(root);files=sorted((root/'Assets/scripts').rglob('*.cs'),key=lambda f:f.relative_to(root).as_posix())
    return hashlib.sha256('\n'.join(f.relative_to(root).as_posix()+':'+digest(f) for f in files).encode()).hexdigest()
def snapshot(folder):
    folder=Path(folder);files=sorted((ROOT/'Assets/scripts').rglob('*.cs'))
    files += [ROOT/'tools'/n for n in ['closed_loop_study.py','analyze_experiments.py','individual_analysis.py']]
    manifest=[]
    for f in files:
        rel=f.relative_to(ROOT);target=folder/'source_snapshot'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
        manifest.append(dict(path=rel.as_posix(),sha256=digest(f)))
    save(folder/'source-manifest.json',manifest)
def sync_runtime(project):
    project=Path(project)
    for f in (ROOT/'Assets/scripts').rglob('*.cs'):
        target=project/f.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
    require(source_sha(project)==source_sha(),'Runtime source inventory mismatch')
def jobs(cells,seeds,policies,phase):
    return [dict(id=f"{c['id']}_s{s}_{policy}",cell=c['id'],seed=s,agents=c['agents'],blocked=c['initialBlockedObstacles'],cv=c['cv'],policy=policy,phase=phase,calibrationFile='',replayFile='',conditionKey='',initialStateSHA='') for s in seeds for c in cells for policy in policies]
def campaign(path,phase,work,max_http=0,horizon=300,wall_seconds=21600):
    require(not Path(path).exists(),'Preserve prior campaign plan')
    ids=[j['id'] for j in work];require(len(ids)==len(set(ids)) and ids,'Duplicate/empty job matrix')
    if phase not in ('FinalGeometry','FinalTest'):require(not any(51001<=j['seed']<=51030 or 53001<=j['seed']<=53030 for j in work),'Final seeds cannot enter preparatory simulations')
    save(path,dict(schema='closed-loop-campaign-v1',phase=phase,sourceSHA=source_sha(),model='gpt-6-luna',horizon=horizon,maxReservedHttp=max_http,wallSeconds=wall_seconds,paidFinalExecutionByDefault=False,jobs=work))
def run(plan,project,output,geometry=False,lock=None,execute_final=False,stop=None,partition=None):
    plan,project,output=map(lambda p:Path(p).resolve(),(plan,project,output));p=read(plan)
    require(source_sha()==p['sourceSHA']==source_sha(project),'Source drift')
    if p['phase']=='FinalTest':require(execute_final and lock,'Final simulations are a separate explicit action')
    expected=p['jobs']
    if partition:
        require(p['phase']=='FinalTest','Only final plans can be partitioned')
        parts=partition.split('/');require(len(parts)==2 and all(x.isdecimal() for x in parts),'Invalid worker partition')
        index,count=map(int,parts);require(1<=count<=4 and 0<=index<count,'Invalid worker partition')
        expected=[j for i,j in enumerate(p['jobs']) if i%count==index]
        require(expected,'Empty worker partition')
    if output.exists():
        require(read(output/'progress.json')['outcome']=='completed' and (output/'registered-plan.json').read_bytes()==plan.read_bytes(),'Previous incomplete run: inspect; no automatic retry')
        require(read(output/'executed-plan.json')['jobs']==expected and read(output/'progress.json')['completed']==len(expected),'Existing output belongs to a different partition')
        return dict(outcome='completed_existing',output=str(output))
    require(not (project/'Temp/UnityLockfile').exists(),'Isolated Unity project already open')
    output.parent.mkdir(parents=True,exist_ok=True);log=output.with_suffix('.unity.log')
    cmd=[str(UNITY),'-batchmode','-nographics','-projectPath',str(project),'-executeMethod','ClosedLoopCampaignRunner.Run','-groupPlan',str(plan),'-groupOutput',str(output),'-credentialRoot',str(ROOT),'-logFile',str(log)]
    if geometry:cmd+=['-geometryOnly','true']
    if lock:cmd+=['-groupLock',str(Path(lock).resolve())]
    if execute_final:cmd+=['-confirmFinalExecution','true']
    if stop:cmd+=['-groupStopFile',str(Path(stop).resolve())]
    if partition:cmd+=['-groupPartition',partition]
    with output.with_suffix('.process.log').open('w',encoding='utf-8') as stream:
        result=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,timeout=p['wallSeconds']+600)
    require(result.returncode==0,'Campaign stopped; retain all raw records and inspect before further dispatch')
    result=read(output/'progress.json');require(result['outcome']=='completed' and result['completed']==len(expected),'Campaign incomplete')
    return result
def one(folder,suffix):
    fs=list(Path(folder).glob('*'+suffix));require(len(fs)==1,'Expected one '+suffix);return fs[0]
def optional(folder,suffix):
    fs=list(Path(folder).glob('*'+suffix));require(len(fs)<=1,'Ambiguous export');return read_csv(fs[0]) if fs else []

def final_seed_blocks(plan):
    seeds=sorted({j['seed'] for j in plan['jobs']})
    require(len(seeds)==30 and all(type(v)is int for v in seeds),'Expected thirty registered final seed blocks')
    pairs=collections.Counter((j['cell'],j['policy']) for j in plan['jobs'])
    require(len(plan['jobs'])==1140 and len(pairs)==38 and all(v==30 for v in pairs.values()),'Incomplete registered policy/cell matrix')
    expected=set(pairs)
    require(all({(j['cell'],j['policy']) for j in plan['jobs'] if j['seed']==seed}==expected for seed in seeds),'Unbalanced registered seed blocks')
    require(len({j['id'] for j in plan['jobs']})==1140 and len({(j['seed'],j['cell'],j['policy']) for j in plan['jobs']})==1140,'Duplicate registered jobs')
    return seeds


def restricted_time(steps,n,h):
    require(n>0 and h>0 and len(steps)<=n and all(type(s)is int and 1<=s<=h for s in steps),'Invalid censored outcome')
    return (sum(steps)+(n-len(steps))*h)/n
def block_interval(values,iterations=4000):
    require(len(values)>=2 and all(math.isfinite(v) for v in values),'Need finite seed-block outcomes')
    rng=random.Random(2026111304)
    samples=sorted(statistics.fmean(rng.choices(values,k=len(values))) for _ in range(iterations))
    return [samples[int(.025*iterations)],samples[int(.975*iterations)-1]]


def analyze(outputs,out,geometry=False,bundle=None):
    out=Path(out);require(not out.exists(),'Preserve previous analysis')
    results=[];provider_ids=set();seen=set();rows_by_cell={};source=None;expected=0;traces_for_review=[];prompt_hashes=set()
    final_expected=None
    for output in map(Path,outputs):
        original=read(output/'registered-plan.json')
        if original['phase']=='FinalTest':
            require(bundle is not None,'Final analysis requires its frozen group bundle')
            import closed_loop_release
            locked=closed_loop_release.check(bundle)
            require(digest(output/'registered-plan.json')==digest(Path(bundle)/'formal-plan.json'),'Analyzed final plan differs from frozen plan')
            required={j['id'] for j in original['jobs']};require(final_expected is None or final_expected==required,'Mixed final plans');final_expected=required
        p=read(output/'executed-plan.json') if (output/'executed-plan.json').exists() else read(output/'registered-plan.json');status=read(output/'progress.json')
        require(status['outcome']=='completed' and status['completed']==len(p['jobs']),'Do not analyze a partial campaign as complete')
        source=source or p['sourceSHA'];require(source==p['sourceSHA'],'Mixed sources')
        expected+=len(p['jobs']);attempts_for_worker=0
        for j in p['jobs']:
            require(j['id'] not in seen,'Duplicate job');seen.add(j['id']);folder=output/j['id']
            c=read(one(folder,'_config.json'));binding=read(folder/'binding.json');state=read(folder/'initial-state.json')
            require(c['personalResponseVersion']=='paper-choice-response-v3' and c['paperPromptVersion']=='paper-agent-v5' and c['closedLoopSourceSHA']==source,'Version/source drift')
            require(c['conditionKey']==binding['conditionKey'] and c['initialStateSHA']==binding['initialStateSHA'] and c['geometryTemplateSHA']==binding['templateSHA'],'Binding drift')
            require(c['actualAgents']==j['agents'] and c['actualObstacles']==5 and c['initialBlockedObstacles']==j['blocked'] and c['observationScope']=='Core' and c['availabilityMode']=='PolicyWillingness' and c['executionMode']=='PaperReference','Physical condition drift')
            require(state['agents']==j['agents'] and state['seed']==j['seed'] and len(state['obstacleCells'])==5,'Initial manifest drift')
            initial=[r for r in optional(folder,'_trajectories.csv') if int(r['Step'])==0]
            require(len(initial)==j['agents'] and [(int(r['X']),int(r['Y'])) for r in initial]==[(q['x'],q['y']) for q in state['agentCells']],'Initial positions mismatch')
            if p['phase']=='FinalTest':require(j['conditionKey']==binding['conditionKey'] and j['initialStateSHA']==binding['initialStateSHA'] and not c['zeroStepValidation'],'Final binding/zero-step drift')
            if p['phase']=='FinalTest':require(c['studyPlanID']==locked['lockID'],'Final run lock identity drift')
            if j['policy']=='RandomMatched':
                calibration=Path(j['calibrationFile'])
                if not calibration.is_absolute():
                    require(bundle is not None,'Relative calibration needs frozen bundle');calibration=Path(bundle)/calibration
                cal=read(calibration)
                require(c['calibrationID']==cal['calibrationID'] and math.isclose(c['calibratedProbability'],cal['probability'],abs_tol=1e-7),'Applied random-control calibration drift')
            total=read_csv(one(folder,'_global.csv'))[0]
            if geometry:
                require(int(total['ApiRequests'])==0 and int(total['TotalSteps'])==0,'Geometry preflight executed requests or steps')
                results.append(dict(job=j['id'],cell=j['cell'],seed=j['seed'],policy=j['policy'],condition=c['conditionKey'],initialStateSHA=c['initialStateSHA'],templateSHA=c['geometryTemplateSHA'],agents=j['agents'],blocked=j['blocked'],cv=j['cv']))
                continue
            physical=load_run(one(folder,'_config.json'));require(physical['valid'] and int(total['MockDecisions'])==0,'Invalid physical/model outcome')
            evac=optional(folder,'_agents.csv');steps=[int(r['EvacuationStep']) for r in evac];ah=restricted_time(steps,j['agents'],p['horizon'])
            require(math.isclose(ah,physical['restricted_mean_steps'],abs_tol=1e-9),'Restricted outcome mismatch')
            # Independently recompute from complete recorded trajectories, including non-evacuees.
            trajectories=optional(folder,'_trajectories.csv');alive=collections.Counter()
            for r in trajectories:
                if r['Evacuated'].lower()=='false':alive[int(r['Step'])]+=1
            recorded_steps=int(total['TotalSteps']);require(recorded_steps<=p['horizon'],'Horizon exceeded')
            integral=sum(alive[t] for t in range(recorded_steps))
            if total['Termination']=='timeout':integral+=(p['horizon']-recorded_steps)*(j['agents']-len(steps))
            require(math.isclose(integral/j['agents'],ah,abs_tol=1e-9),'Trajectory/evacuee capped-time mismatch')
            traces=[];prompt_tokens=completion_tokens=cached_tokens=0;api_seconds=0.
            for f in folder.glob('*_agent_trace.jsonl'):
                traces.extend(strict_json(s) for s in f.read_text(encoding='utf-8-sig').splitlines() if s.strip())
            for t in traces:
                body,envelope=answer(t['response']);payload=strict_json(t['payload'])
                require(t['promptVersion']=='paper-agent-v5' and t['requestedModel']==p['model'] and t['conditionKey']==c['conditionKey'],'Trace configuration drift')
                suffix='Observation:\n'+t['observation'];message=payload['messages'][1]['content'];require(message.endswith(suffix),'Payload observation drift')
                instructions=message[:-len(suffix)];prompt_hash=hashlib.sha256(instructions.encode()).hexdigest();prompt_hashes.add(prompt_hash)
                require(instructions.startswith('Task specification: paper-agent-v5; information condition: Core.') and prompt_hash==t['promptTemplateHash'] and validate_payload(t['payload'],t['observation'],p['model'],instructions)=='paper-choice-response-v3','Prompt/history/hash drift')
                require(t['succeeded'] and body is not None and t['willing']==(body['decision']=='participate') and envelope['model']=='gpt-6-luna' and t['httpStatus']==200 and not t['error'],'Raw response/flag/provider mismatch')
                require(t['execution']=='live' and t['responseValidationVersion']=='paper-choice-response-v3','Non-live/wrong protocol')
                require(envelope['id'] not in provider_ids,'Repeated provider response');provider_ids.add(envelope['id'])
                schema=payload['response_format']['json_schema']['schema'];require(list(schema['properties'])==['explanation','decision'] and schema['properties']['decision']=={'type':'string'},'Output schema drift')
                require(payload['reasoning_effort']=='none' and payload['max_completion_tokens']==220 and math.isclose(payload['temperature'],.15,abs_tol=1e-7),'Transport drift')
                require(t['attempts']==len(t['attemptAudit']),'Attempt audit mismatch');attempts_for_worker+=t['attempts']
                usage=envelope.get('usage',{});pt=usage.get('prompt_tokens');ct=usage.get('completion_tokens');cached=usage.get('prompt_tokens_details',{}).get('cached_tokens',0)
                require(all(type(v)is int and v>=0 for v in [pt,ct,cached]) and cached<=pt,'Invalid provider token usage')
                require(math.isfinite(t['elapsedSeconds']) and t['elapsedSeconds']>=0,'Invalid API wall latency')
                prompt_tokens+=pt;completion_tokens+=ct;cached_tokens+=cached;api_seconds+=t['elapsedSeconds']
                o=strict_json(t['observation']);require(set(o)=={'nearbyAgentCount','exitNonBlockage','volunteerCost','failureCost','unwillingness'} and o['nearbyAgentCount']>0 and o['exitNonBlockage']<1,'Information/no-game drift')
                traces_for_review.append(dict(job=j['id'],cell=j['cell'],seed=j['seed'],step=t['step'],agent=t['agent'],obstacle=t['obstacle'],decision=body['decision'],explanation=body['explanation']))
            require(len(traces)==int(total['ApiRequests']),'Logical request accounting drift')
            if j['policy']!='LLM' or j['blocked']==0:require(not traces,'Control called a model')
            decisions=optional(folder,'_paper_decisions.csv');events=optional(folder,'_obstacle_events.csv');effort=optional(folder,'_agent_effort.csv');willing={(r['ObstacleID'],r['AgentID']) for r in decisions if r['Willing']=='True'}
            if traces:
                key=lambda r:(int(r['Step']),int(r['AgentID']),int(r['ObstacleID']))
                decision_map={key(r):r for r in decisions};observations=optional(folder,'_agent_observations.csv');observation_map={key(r):r for r in observations}
                trace_keys={(t['step'],t['agent'],t['obstacle']) for t in traces}
                require(len(trace_keys)==len(traces)==len(decision_map)==len(decisions)==len(observation_map)==len(observations) and trace_keys==decision_map.keys()==observation_map.keys(),'API/decision/observation correspondence drift')
                for t in traces:
                    k=(t['step'],t['agent'],t['obstacle']);d=decision_map[k];o=observation_map[k];obs=strict_json(t['observation'])
                    require(d['Source']==o['Source']=='api' and (d['Willing']=='True')==(o['Willing']=='True')==t['willing'] and strict_json(o['ObservationJSON'])==obs,'Applied decision differs from raw LLM choice')
                    require(int(d['Players'])==obs['nearbyAgentCount'] and math.isclose(float(d['ExitNonBlockage']),obs['exitNonBlockage'],abs_tol=1e-6),'Decision context drift')
            active=set()
            for e in events:
                pair=(e['ObstacleID'],e['AgentID'])
                if e['Action']=='activate':
                    require(pair in willing and any(r['ObstacleID']==pair[0] and r['AgentID']==pair[1] and r['Willing']=='True' and int(r['Step'])<=int(e['Step']) for r in decisions),'Activation without prior willingness');active.add(pair)
                if e['Action'] in ('push','pull','rotate','settle'):require(pair in active,'Manipulation without activation')
            if j['policy']=='NoVolunteers':require(not events and not effort,'No-volunteer control manipulated an obstacle')
            if j['blocked']==0:require(not decisions and not events and not effort,'Unblocked control generated assistance')
            ids={str(i) for i in range(j['agents'])};counts=collections.Counter(r['AgentID'] for r in effort);require(not set(counts)-ids,'Unknown worker')
            require(len({(r['Step'],r['AgentID']) for r in effort})==len(effort),'Duplicate effort tick')
            worker_values=[counts[i] for i in ids];work=sum(worker_values);gini=sum(abs(a-b) for a in worker_values for b in worker_values)/(2*j['agents']*work) if work else None
            row=dict(job=j['id'],cell=j['cell'],seed=j['seed'],policy=j['policy'],phase=p['phase'],condition=c['conditionKey'],initialStateSHA=c['initialStateSHA'],templateSHA=c['geometryTemplateSHA'],agents=j['agents'],blocked=j['blocked'],cv=j['cv'],horizon=p['horizon'],termination=total['Termination'],evacuated=len(steps),fraction=len(steps)/j['agents'],A_H=ah,T100=recorded_steps if total['Termination']=='completed' else None,decisions=len(decisions),willing=sum(r['Willing']=='True' for r in decisions),apiCalls=len(traces),httpAttempts=sum(t['attempts'] for t in traces),activations=sum(e['Action']=='activate' for e in events),settled=sum(e['Action']=='settle' for e in events),effort=work,meanEffort=work/j['agents'],maxEffort=max(worker_values),zeroEffort=sum(v==0 for v in worker_values),gini=gini,noWork=work==0)
            row.update(promptTokens=prompt_tokens,completionTokens=completion_tokens,cachedPromptTokens=cached_tokens,apiWallSeconds=api_seconds)
            row.update(decisionSteps=sorted({int(d['Step']) for d in decisions}),observedEligibleCounts=sorted({int(d['Players']) for d in decisions}),observedExitNonBlockage=sorted({float(d['ExitNonBlockage']) for d in decisions}))
            results.append(row)
        require(attempts_for_worker<=status['reservedHttp']<=p['maxReservedHttp'],'Campaign reservation accounting drift')
    require(len(results)==expected,'Incomplete matrix')
    require(len(prompt_hashes)<=1,'Mixed task instructions')
    if final_expected is not None:require(seen==final_expected and len(seen)==1140,'Final matrix is incomplete or duplicated')
    # Pairing is based on actual state hashes, not on policy-name metadata.
    pairing=collections.defaultdict(set)
    for r in results:pairing[(r['cell'],r['seed'])].add(r['initialStateSHA'])
    require(all(len(v)==1 for v in pairing.values()),'Policies started from different states')
    out.mkdir(parents=True);save(out/'runs.json',results);save(out/'explanations.json',traces_for_review)
    with (out/'runs.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
    summary=dict(schema='closed-loop-analysis-v1',phase=p['phase'],geometryOnly=geometry,runs=len(results),invalid=0,pairedInitialStatesVerified=True,productionSourceSHA=source,formalSimulationExecuted=not geometry and p['phase']=='FinalTest')
    summary['promptTemplateHashes']=sorted(prompt_hashes)
    if not geometry:summary.update(completed=sum(r['termination']=='completed' for r in results),timeouts=sum(r['termination']=='timeout' for r in results),logicalCalls=sum(r['apiCalls'] for r in results),httpAttempts=sum(r['httpAttempts'] for r in results),declines=sum(t['decision']=='decline_assistance' for t in traces_for_review))
    if final_expected is not None:
        final_seeds=final_seed_blocks(original)
        summary['primary']=primary_estimate(results,final_seeds)
    save(out/'summary.json',summary);return summary


def primary_estimate(rows,seeds):
    mapping={}
    for r in rows:
        key=(r['cell'],r['seed'],r['policy']);require(key not in mapping,'Duplicate cell/seed/policy');mapping[key]=r
    cells=sorted({r['cell'] for r in rows if r['blocked']>0});require(len(cells)==8,'Need eight blocked cells')
    values=[]
    for seed in seeds:
        contrasts=[]
        for cell in cells:
            a=mapping.get((cell,seed,'OriginalGameTheory'));b=mapping.get((cell,seed,'LLM'))
            require(a is not None and b is not None and a['horizon']==b['horizon'] and a['initialStateSHA']==b['initialStateSHA'],'Missing/unpaired primary outcome')
            contrasts.append(b['A_H']-a['A_H'])
        values.append(dict(seed=seed,difference=statistics.fmean(contrasts)))
    return dict(metric='equal-cell-weight mean LLM minus Original A_H, then mean over base seeds',seedBlocks=len(values),estimate=statistics.fmean(v['difference'] for v in values),pointwise95=block_interval([v['difference'] for v in values]),bootstrapIterations=4000,bootstrapSeed=2026111304,blocks=values,confirmatoryTests=False)


def calibrate(outputs,out,expected_seeds):
    out=Path(out);require(not out.exists(),'Do not overwrite calibration');groups=collections.defaultdict(list)
    for output in map(Path,outputs):
        p=read(output/'registered-plan.json');require(p['phase']=='Calibration' and read(output/'progress.json')['outcome']=='completed','Only complete calibration campaigns allowed')
        for j in p['jobs']:
            require(j['policy']=='LLM' and j['blocked']>0,'Calibration cannot use controls or another policy')
            folder=output/j['id'];c=read(one(folder,'_config.json'));physical=load_run(one(folder,'_config.json'))
            require(physical['valid'] and c['researchPhase']=='Calibration' and c['decisionExecution']=='live','Invalid/non-independent calibration data')
            obs=optional(folder,'_agent_observations.csv');require(obs and all(r['Source']=='api' for r in obs),'No live decisions for calibration')
            groups[j['cell']].append((j,c,obs,folder))
    require(len(groups)==8,'Need eight blocked-cell calibrations');out.mkdir(parents=True)
    for cell,values in groups.items():
        seeds=[j['seed'] for j,c,o,f in values];require(len(seeds)==len(set(seeds)) and set(seeds)==set(expected_seeds),'Missing/duplicate calibration seeds')
        signatures={(c['conditionKey'],c['model'],c['personalResponseVersion'],c['geometryTemplateSHA'],c['closedLoopSourceSHA'],c['maxSteps']) for j,c,o,f in values};require(len(signatures)==1,'Mixed calibration bindings')
        key,model,protocol,template,source,h=signatures.pop();allobs=[r for j,c,obs,f in values for r in obs]
        artifact=dict(schema='cooperation-calibration-v2',split='Calibration',conditionKey=key,model=model,promptVersion='paper-agent-v5',informationCondition='Core',responseProtocol=protocol,geometryTemplateSHA=template,productionSourceSHA=source,horizon=h,decisions=len(allobs),probability=sum(r['Willing']=='True' for r in allobs)/len(allobs),seeds=sorted(seeds),sourceHashes=[digest(f) for j,c,o,folder in values for f in [one(folder,'_config.json'),one(folder,'_agent_observations.csv'),one(folder,'_agent_trace.jsonl')]],scope='Decision-weighted constant p within calibration condition, not exact test-rate matching')
        artifact['perSeed']=[dict(seed=j['seed'],decisions=len(obs),willing=sum(r['Willing']=='True' for r in obs),probability=sum(r['Willing']=='True' for r in obs)/len(obs)) for j,c,obs,f in sorted(values,key=lambda v:v[0]['seed'])]
        artifact['betweenSeedProbabilitySD']=statistics.stdev(v['probability'] for v in artifact['perSeed'])
        artifact['calibrationID']=hashlib.sha256(json.dumps(artifact,sort_keys=True).encode()).hexdigest();save(out/(cell+'.json'),artifact)
    return len(groups)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='action',required=True)
    r=sub.add_parser('run');r.add_argument('plan',type=Path);r.add_argument('--project',type=Path,required=True);r.add_argument('--output',type=Path,required=True);r.add_argument('--geometry',action='store_true');r.add_argument('--stop',type=Path);r.add_argument('--lock',type=Path);r.add_argument('--execute-final',action='store_true');r.add_argument('--partition')
    a=sub.add_parser('analyze');a.add_argument('campaigns',nargs='+',type=Path);a.add_argument('--output',type=Path,required=True);a.add_argument('--geometry',action='store_true');a.add_argument('--bundle',type=Path)
    c=sub.add_parser('calibrate');c.add_argument('campaigns',nargs='+',type=Path);c.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    if args.action=='run':result=run(args.plan,args.project,args.output,args.geometry,args.lock,args.execute_final,args.stop,args.partition)
    elif args.action=='analyze':result=analyze(args.campaigns,args.output,args.geometry,args.bundle)
    else:result=dict(calibrations=calibrate(args.campaigns,args.output,range(42001,42011)))
    print(json.dumps(result,indent=2))
