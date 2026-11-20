"""S5 dataset/schedule locking and descriptive analysis. No Unity launch or API client."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines()]


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def jsonl(path, values):
    Path(path).write_text(''.join(canonical(v) + '\n' for v in values), encoding='utf-8')


SPLITS = {'Development': list(range(410001, 410005)), 'Calibration': list(range(420001, 420005)), 'FinalTest': list(range(430001, 430013))}
GROUPS = {'A1', 'A2', 'A3', 'W1', 'W2', 'R0', 'R1'}


def validate_snapshots(records, inventory):
    cells = {c['cellId'] for c in inventory['cells']}
    seen = set()
    for row in records:
        key = (row['split'], row['seed'], row['cellId'], row['sourcePolicy'], row['checkpoint'])
        if key in seen or row['seed'] not in SPLITS[row['split']] or row['cellId'] not in cells or row['sourcePolicy'] not in {'A1', 'A2'} or row['checkpoint'] not in {1, 10}:
            raise ValueError('Unexpected/duplicate snapshot sampling unit')
        seen.add(key)
        s = row['snapshot']
        if s['step'] != row['checkpoint'] or not s['snapshotId']:
            raise ValueError('Wrong snapshot checkpoint')
        agents = {a['agentId'] for a in s['candidates']}
        tasks = {t['obstacleId'] for t in s['tasks']}
        if len(agents) != len(s['candidates']) or len(tasks) != len(s['tasks']):
            raise ValueError('Duplicate snapshot IDs')
        pairs = set()
        for e in s['edges']:
            pair = e['agentId'], e['obstacleId']
            if pair in pairs or e['agentId'] not in agents or e['obstacleId'] not in tasks or not math.isfinite(e['approachCost']) or e['approachCost'] < 0:
                raise ValueError('Invalid edge/cost')
            pairs.add(pair)
    expected = {(split, seed, cell, source, checkpoint) for split, seeds in SPLITS.items() for seed in seeds for cell in cells for source in ('A1', 'A2') for checkpoint in (1, 10)}
    if seen != expected:
        raise ValueError('Missing predeclared snapshots; no silent exclusions')


def prepare(root):
    root = Path(root).resolve()
    folder = root / 'research/s5/datasets'
    if (root / 'research/s5/design.json').exists():
        raise ValueError('Design already prepared; create a disclosed new version')
    inventory = read(folder / 'conditions.json')
    snapshots = lines(folder / 'snapshots.raw.jsonl')
    validate_snapshots(snapshots, inventory)
    contexts = lines(folder / 'willingness.raw.jsonl')
    if len(contexts) != 160 or len({r['observation'] for r in contexts}) != 160 or len({r['recordId'] for r in contexts}) != 160:
        raise ValueError('Expected 160 distinct factorial willingness contexts')
    strata = defaultdict(list)
    for row in contexts:
        c = json.loads(row['observation'])
        n, tau, cv, av, omega = (c[k] for k in ('nearbyAgentCount', 'exitNonBlockage', 'volunteerCost', 'failureCost', 'unwillingness'))
        if type(n) is not int or not all(math.isfinite(v) for v in (tau,cv,av,omega,row['referenceProbability'])) or not 0 < cv < av < 1 or not 0 <= tau < 1 or n < 1 or omega < 0:
            raise ValueError('Invalid paper-game context')
        p = (1.0 if tau == 0 else 0.0) if n == 1 else 1 - (1 - math.exp(-omega*tau))**(1/n)*(cv/av)**(1/(n-1))
        if abs(p-row['referenceProbability']) > 2e-6:
            raise ValueError('Analytical label differs from implementation')
        strata[n, tau].append(row)
    if len(strata) != 20 or any(len(g) != 8 for g in strata.values()):
        raise ValueError('Incomplete factorial strata')
    for group in strata.values():
        ordered = sorted(group, key=lambda r: hashlib.sha256(('s5-v1:'+r['observation']).encode()).hexdigest())
        for index, row in enumerate(ordered):
            row['split'] = 'Development' if index < 2 else 'Calibration' if index < 4 else 'FinalTest'
    contexts = sorted(contexts, key=lambda r: r['recordId'])
    for split in SPLITS:
        jsonl(folder / (split+'.snapshots.jsonl'), [r for r in snapshots if r['split'] == split])
        jsonl(folder / (split+'.willingness.jsonl'), [r for r in contexts if r['split'] == split])
    jobs = []
    for row in snapshots:
        jobs.append(dict(jobID='snap_'+row['recordId'], kind='fixed_dispatch', phase=row['split'], seed=row['seed'], cellId=row['cellId'], groupId='A3', inputId=row['recordId'], maxLogicalCalls=1, maxHttpAttempts=1, maxOutputTokens=1024, maxPromptChars=60000))
    for row in contexts:
        jobs.append(dict(jobID='will_'+row['recordId'], kind='fixed_willingness', phase=row['split'], seed=0, cellId='factorial', groupId='W2', inputId=row['recordId'], maxLogicalCalls=1, maxHttpAttempts=3, maxOutputTokens=220))
    # Closed-loop confirmatory geometry uses n=8; n=16 is a fixed-snapshot stress stratum.
    for phase, seeds in (('Calibration', SPLITS['Calibration'][:2]), ('FinalTest', SPLITS['FinalTest'])):
        for c in inventory['conditions']:
            if not c['cellId'].endswith('_n8'):
                continue
            for seed in seeds:
                logical = 20 if c['groupId'] == 'A3' else 100 if c['groupId'] == 'W2' else 0
                attempts = logical * (3 if c['groupId'] == 'W2' else 1)
                jobs.append(dict(c, jobID=f"run_{phase}_{seed}_{c['cellId']}_{c['groupId']}", kind='closed_loop', phase=phase, seed=seed,
                                 maxAgentRequests=100, maxDispatchRequests=20, maxOutputTokens=1024, maxPromptChars=60000,
                                 maxLogicalCalls=logical, maxHttpAttempts=attempts))
    jsonl(root/'research/s5/schedule.jsonl', jobs)
    design = dict(schema='coordination-study-v1', model=inventory['model'], horizon=inventory['horizon'], dispatchVersion='coordination-dispatch-v1', willingnessVersion='paper-agent-v3',
                  developmentSeeds=SPLITS['Development'], calibrationSeeds=SPLITS['Calibration'], testSeeds=SPLITS['FinalTest'],
                  primaryContrast='Fixed-snapshot A3 minus A1 task coverage; oracle A2 defines per-snapshot coverage ceiling. Paired seed-block mean difference.',
                  multiplicityTreatment='One primary descriptive 95% paired seed-block bootstrap interval; no confirmatory p-values or power claim. All other contrasts exploratory, unadjusted and labeled.',
                  jobs=jobs, metrics=dict(primary='coverage on all scheduled snapshots; invalid outputs assigned operational coverage 0 and reported separately',
                  secondary=['legality','coverage_gap_to_oracle','cost_gap_only_equal_coverage','participation_minus_formula_probability','H_completion','restricted_T100_steps','invalid_rate','work_ticks_all_agents','work_gini_including_zeros','reported_tokens','attempts','wall_latency']),
                  stoppingRules=['No adaptive stopping or favorable-state filtering. No retry/replacement of a claimed job without an immutable amendment.',
                                 'Pilot gate: zero physical/ledger corruption, complete audits for every started call, zero silent fallback, no split/source drift; API/schema incompatibility pauses all model jobs.',
                                 'Any budget invalidation retained separately; report conditional physical metrics and operational success, never turn API invalid into a physical timeout.',
                                 'If pilot changes model, prompt, horizon, quotas or scenarios, freeze a new version before revealing FinalTest model outcomes.'],
                  runtimeConfigTool='Research/Coordination/Configure scheduled study job (no run)',
                  budgets=dict(maxLogicalCalls=sum(j['maxLogicalCalls'] for j in jobs), maxHttpAttempts=sum(j['maxHttpAttempts'] for j in jobs),
                               maxLogicalCompletionTokens=sum((220 if j['groupId']=='W2' else 1024)*j['maxLogicalCalls'] for j in jobs),
                               maxCompletionTokens=sum((220 if j['groupId']=='W2' else 1024)*j['maxHttpAttempts'] for j in jobs),
                               moneyBudget='Not estimated: no current pricing/account budget assumed. These are conservative request/output bounds, not an expenditure authorization.'),
                  readiness='design_and_inputs_only_no_live_results', datasetCounts=dict(snapshots=len(snapshots), willingness=len(contexts), jobs=len(jobs)))
    design['pilotGate']=dict(minimumLiveDispatchResponses=8,minimumWillingnessResponses=8,minimumDispatchLegality=.9,maximumWillingnessInvalidFraction=.1,
                             maximumClosedLoopLLMInvalidFraction=.1,requireCompleteScheduledCalibration=True,requireCompleteCoordinationAudits=True,efficiencyOrCooperationThreshold=None)
    write(root/'research/s5/design.json', design)
    return design


def local(root, name):
    path = (root/name).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Path outside project')
    return path


def validate_payload(p):
    if p.get('schema') != 'coordination-study-v1' or p.get('dispatchVersion') != 'coordination-dispatch-v1' or p.get('willingnessVersion') != 'paper-agent-v3' or not p.get('model') or p.get('horizon', 0) <= 0:
        raise ValueError('Study schema/versions/model/horizon missing')
    splits = [p.get(k, []) for k in ('developmentSeeds','calibrationSeeds','testSeeds')]
    if any(not s or any(type(v) is not int for v in s) or len(s) != len(set(s)) for s in splits) or len(set(sum(splits, []))) != sum(map(len, splits)):
        raise ValueError('Seed splits overlap or are invalid')
    jobs = p.get('jobs', [])
    if not jobs or len({j['jobID'] for j in jobs}) != len(jobs):
        raise ValueError('Missing/duplicate jobs')
    allowed = dict(zip(('Development','Calibration','FinalTest'), splits))
    for j in jobs:
        if not all(c.isalnum() or c in '_-' for c in j['jobID']) or j['groupId'] not in GROUPS or j['phase'] not in allowed or j['kind'] not in {'closed_loop','fixed_dispatch','fixed_willingness'}:
            raise ValueError('Invalid scheduled job')
        if j['kind'] != 'fixed_willingness' and j['seed'] not in allowed[j['phase']]:
            raise ValueError('Job seed outside split')
        if any(type(j.get(k)) is not int or j[k] < 0 for k in ('maxLogicalCalls','maxHttpAttempts','maxOutputTokens')):
            raise ValueError('Invalid job bounds')
    if not p.get('primaryContrast') or not p.get('multiplicityTreatment'):
        raise ValueError('Specify primary analysis')
    if any(p['budgets'][key] != sum(j[field] for j in jobs) for key, field in (('maxLogicalCalls','maxLogicalCalls'),('maxHttpAttempts','maxHttpAttempts'))):
        raise ValueError('Aggregate budget mismatch')
    if p['budgets']['maxCompletionTokens']!=sum((220 if j['groupId']=='W2' else 1024)*j['maxHttpAttempts'] for j in jobs):
        raise ValueError('Retry-inclusive completion budget mismatch')


def freeze(root, output):
    root = Path(root).resolve(); output = Path(output)
    if output.exists():
        raise ValueError('Locked plans are immutable; choose a new version')
    p = read(root/'research/s5/design.json'); validate_payload(p)
    inventory = read(root/'research/s5/datasets/conditions.json')
    validate_snapshots(lines(root/'research/s5/datasets/snapshots.raw.jsonl'), inventory)
    if set(j['groupId'] for j in p['jobs'] if j['kind']=='closed_loop') != GROUPS:
        raise ValueError('Missing research controls')
    files = sorted((root/'Assets/scripts').rglob('*.cs')) + sorted((root/'Assets/Scenes').glob('*.unity')) + sorted((root/'tools').glob('*.py'))
    files += [root/n for n in ('Packages/manifest.json','ProjectSettings/ProjectVersion.txt','RESEARCH_PROTOCOL.zh-TW.md','RESEARCH_INTEGRATION_PLAN.zh-TW.md','COORDINATION_DISPATCH_SPEC.md','S5_STUDY_PROTOCOL.zh-TW.md','research/s5/design.json')]
    p['sourceFiles'] = [dict(path=f.relative_to(root).as_posix(),sha256=sha(f)) for f in files]
    datasets = sorted((root/'research/s5/datasets').glob('*')) + [root/'research/s5/schedule.jsonl']
    p['datasetFiles'] = [dict(path=f.relative_to(root).as_posix(),sha256=sha(f)) for f in datasets if f.is_file()]
    payload = canonical(p)
    result = dict(schema='coordination-study-lock-v1',locked=True,planID=hashlib.sha256(payload.encode()).hexdigest(),payloadJson=payload)
    write(output,result);return result


def verify(path, root):
    root=Path(root).resolve(); lock=read(path)
    if lock.get('schema')!='coordination-study-lock-v1' or lock.get('locked') is not True or hashlib.sha256(lock['payloadJson'].encode()).hexdigest()!=lock.get('planID'):
        raise ValueError('Plan checksum/schema mismatch')
    p=json.loads(lock['payloadJson']);validate_payload(p)
    current={f.relative_to(root).as_posix() for f in (list((root/'Assets/scripts').rglob('*.cs'))+list((root/'Assets/Scenes').glob('*.unity'))+list((root/'tools').glob('*.py')))}
    frozen={f['path'] for f in p['sourceFiles'] if f['path'].endswith(('.cs','.unity','.py'))}
    if current!=frozen:raise ValueError('Frozen source file set changed')
    for f in p['sourceFiles']+p['datasetFiles']:
        if sha(local(root,f['path']))!=f['sha256']:
            raise ValueError('Frozen file changed: '+f['path'])
    return lock,p


def claim(path, root, job_id, ledger_root):
    lock,p=verify(path,root)
    jobs=[j for j in p['jobs'] if j['jobID']==job_id]
    if len(jobs)!=1:raise ValueError('Job not scheduled')
    if jobs[0]['phase']=='FinalTest':verify_gate(Path(ledger_root)/'study_ledgers'/lock['planID']/'pilot-gate.json',lock['planID'],root)
    directory=(Path(ledger_root)/'study_ledgers'/lock['planID']).resolve()
    if os.name=='nt' and not str(directory).startswith('\\\\?\\'):
        directory=Path('\\\\?\\'+str(directory))
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/(job_id+'.claim.json')).open('x',encoding='utf-8') as stream:json.dump(jobs[0],stream,indent=2)
    return jobs[0]


def verify_gate(path,plan_id,root):
    envelope=read(path)
    if envelope.get('schema')!='coordination-pilot-gate-lock-v1' or hashlib.sha256(envelope['payloadJson'].encode()).hexdigest()!=envelope.get('gateID'):
        raise ValueError('Invalid pilot gate checksum')
    p=json.loads(envelope['payloadJson'])
    if p.get('schema')!='coordination-pilot-gate-v1' or p.get('planID')!=plan_id or p.get('passed') is not True or not p.get('inputFiles'):
        raise ValueError('Pilot has not passed for this plan')
    for f in p['inputFiles']:
        if sha(local(Path(root).resolve(),f['path']))!=f['sha256']:raise ValueError('Pilot evidence changed')
    return p


def interval(values):
    if len(values)<2:return None
    rng=random.Random(5102026);resamples=sorted(statistics.fmean(rng.choices(values,k=len(values))) for _ in range(4000))
    return [resamples[100],resamples[3899]]


def analyze_fixed(plan_path,root,results,phase):
    """Results use jobID and coverage/legality/cost from common-validated snapshot comparison.

    Missing jobs stay missing; invalid outputs have operational coverage zero. No replay
    or synthetic model measurements are accepted as actual research observations.
    """
    _,p=verify(plan_path,root);dataset={r['recordId']:r for r in lines(Path(root)/('research/s5/datasets/'+phase+'.snapshots.jsonl'))};expected={j['jobID']:j for j in p['jobs'] if j['kind']=='fixed_dispatch' and j['phase']==phase}
    observed={};blocks=defaultdict(list);invalid=0;equal_cost_gaps=[]
    for row in lines(results):
        key=row['jobID']
        if key not in expected or key in observed or row.get('execution') not in {'live','no_eligible_edges'}:
            raise ValueError('Unexpected/duplicate/non-live measurement')
        if type(row.get('llmValid')) is not bool or not all(type(row.get(k)) is int and row[k]>=0 for k in ('localCount','optimalCount')):
            raise ValueError('Missing counts/legality')
        if row['llmValid'] and (type(row.get('llmCount')) is not int or not 0<=row['llmCount']<=row['optimalCount']):
            raise ValueError('Invalid coverage')
        reference=dataset[expected[key]['inputId']]
        if row['localCount']!=reference['referenceLocalCount'] or row['optimalCount']!=reference['referenceOptimalCount'] or (row['execution']=='no_eligible_edges' and row['optimalCount']!=0):
            raise ValueError('Comparison baseline differs from frozen snapshot')
        if row['llmValid']:
            cost=row.get('llmCost')
            if type(cost) not in (float,int) or not math.isfinite(cost) or cost<0:raise ValueError('Missing finite proposal cost')
            if row['llmCount']==row['optimalCount']:
                gap=cost-reference['referenceOptimalCost']
                if gap < -1e-5:raise ValueError('Cost below frozen oracle at equal coverage')
                equal_cost_gaps.append(gap)
        observed[key]=row;invalid+=not row['llmValid']
        blocks[expected[key]['seed']].append((row['llmCount'] if row['llmValid'] else 0)-row['localCount'])
    complete=len(observed)==len(expected)
    differences=[statistics.fmean(v) for v in blocks.values()]
    return dict(phase=phase,scheduled=len(expected),observed=len(observed),missing=len(expected)-len(observed),invalid=invalid,
                complete=complete,primaryMeanDifference=statistics.fmean(differences) if complete and differences else None,
                interval95=interval(differences) if complete else None,seedBlocks=len(blocks),legalityRateObserved=(len(observed)-invalid)/len(observed) if observed else None,
                equalCoveragePairs=len(equal_cost_gaps),equalCoverageCostGapMean=statistics.fmean(equal_cost_gaps) if complete and equal_cost_gaps else None,
                interpretation='No primary estimate until the entire scheduled phase is present. Invalid replies count as operational zero coverage and remain separately reported. Paired bootstrap resamples seeds, never individual snapshots; interval is descriptive.')


def analyze_willingness(plan_path,root,results,phase):
    _,p=verify(plan_path,root)
    expected={j['jobID']:j for j in p['jobs'] if j['kind']=='fixed_willingness' and j['phase']==phase}
    contexts={r['recordId']:r for r in lines(Path(root)/('research/s5/datasets/'+phase+'.willingness.jsonl'))}
    observed={};valid=[]
    for row in lines(results):
        key=row['jobID']
        if key not in expected or key in observed or row.get('execution')!='live' or type(row.get('valid')) is not bool:
            raise ValueError('Unexpected/duplicate/non-live willingness measurement')
        if row['valid'] and type(row.get('participate')) is not bool:raise ValueError('Missing participation action')
        observed[key]=row
        if row['valid']:
            c=contexts[expected[key]['inputId']]
            valid.append(dict(context=c['recordId'],nearby=c['nearbyAgentCount'],tau=c['exitNonBlockage'],difference=int(row['participate'])-c['referenceProbability']))
    return dict(phase=phase,scheduled=len(expected),observed=len(observed),missing=len(expected)-len(observed),invalid=len(observed)-len(valid),
                complete=len(observed)==len(expected),meanDifferenceFromFormula=statistics.fmean(r['difference'] for r in valid) if valid and len(observed)==len(expected) else None,
                validContexts=valid,interpretation='Exploratory finite-grid participation minus theoretical probability, conditional on valid responses. One action per context is not a probability estimate, comprehension score or human-behavior measurement. No significance claim.')


def csvrows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))


def analyze_runs(plan_path,root,folder,phase):
    lock,p=verify(plan_path,root)
    expected={j['jobID']:j for j in p['jobs'] if j['kind']=='closed_loop' and j['phase']==phase};observed={}
    for path in sorted(Path(folder).rglob('*_config.json')):
        c=read(path);key=c.get('coordinationStudyJob')
        if key not in expected or key in observed or c.get('studyPlanID')!=lock['planID'] or c.get('researchPhase')!=phase:
            raise ValueError('Unscheduled/duplicate/unlocked runtime result')
        job=expected[key]
        if c.get('conditionKey')!=job['conditionKey'] or c.get('model')!=p['model'] or c.get('maxSteps')!=p['horizon'] or c.get('seed')!=job['seed']:
            raise ValueError('Runtime metadata differs from lock')
        from analyze_experiments import load_run
        load_run(path)  # Existing evacuation/obstacle conservation checks also apply.
        prefix=str(path)[:-len('_config.json')];total=csvrows(prefix+'_global.csv')
        if len(total)!=1:raise ValueError('Ambiguous runtime totals')
        total=total[0];termination=total['Termination'];valid=termination in {'completed','timeout'}
        if c.get('coordinationExecution')=='strict_replay' or c.get('decisionExecution')=='strict_replay':raise ValueError('Replay is validation, not a study replicate')
        attempts=0;latency=0;tokens=0;unknown_usage=0
        for suffix in ('_coordination_trace.jsonl','_agent_trace.jsonl'):
            audit_path=Path(prefix+suffix)
            if not audit_path.exists():continue
            for a in lines(audit_path):
                if suffix.startswith('_coordination') and a.get('execution') not in {'live','no_eligible_edges'}:raise ValueError('Synthetic/replayed runtime audit')
                count=a.get('attempts',0);attempts+=count;latency+=a.get('elapsedSeconds',0)
                if count:
                    usage=read_usage(a)
                    if usage is None:unknown_usage+=1
                    else:tokens+=usage
        if attempts>job['maxHttpAttempts']:raise ValueError('Recorded attempts exceed locked job cap')
        completed=termination=='completed';steps=int(total['TotalSteps'])
        if completed and (steps>p['horizon'] or int(total['EvacuatedCount'])!=c['actualAgents']):raise ValueError('Inconsistent completion')
        initial=csvrows(prefix+'_trajectories.csv');agents={r['AgentID'] for r in initial if r['Step']=='0'}
        if len(agents)!=c['actualAgents']:raise ValueError('Missing initial agents')
        effort=Counter();effort_file=Path(prefix+'_agent_effort.csv')
        if effort_file.exists():effort.update(r['AgentID'] for r in csvrows(effort_file))
        work=[effort[a] for a in agents];work_sum=sum(work)
        gini=sum(abs(a-b) for a in work for b in work)/(2*len(work)*work_sum) if work_sum and work else 0
        observed[key]=dict(jobID=key,seed=job['seed'],cellId=job['cellId'],groupId=job['groupId'],termination=termination,valid=valid,
                           operationalCompleted=int(completed and valid),restrictedT100=steps if completed else p['horizon'] if valid else None,
                           workTicks=work_sum,workGini=gini,httpAttempts=attempts,apiWallSeconds=latency,reportedTotalTokens=tokens,requestsWithoutUsage=unknown_usage)
    complete=len(expected)==len(observed);comparisons=[]
    for left,right in (('A3','A1'),('A3','A2'),('W2','W1'),('R1','R0')):
        lookup={(r['seed'],r['cellId'],r['groupId']):r for r in observed.values()}
        for metric in ('operationalCompleted','restrictedT100','workTicks','workGini'):
            blocks=defaultdict(list);invalid_pairs=0
            for j in expected.values():
                if j['groupId']!=left:continue
                a=lookup.get((j['seed'],j['cellId'],left));b=lookup.get((j['seed'],j['cellId'],right))
                if a is None or b is None:continue
                if metric!='operationalCompleted' and (not a['valid'] or not b['valid']):invalid_pairs+=1;continue
                blocks[j['seed']].append(a[metric]-b[metric])
            delta=[statistics.fmean(v) for v in blocks.values()]
            comparisons.append(dict(contrast=left+' minus '+right,metric=metric,seedBlocks=len(delta),invalidPairs=invalid_pairs,
                                    mean=statistics.fmean(delta) if complete and delta else None,interval95=interval(delta) if complete else None))
    return dict(phase=phase,scheduled=len(expected),observed=len(observed),missing=len(expected)-len(observed),invalid=sum(not r['valid'] for r in observed.values()),complete=complete,
                runs=list(observed.values()),comparisons=comparisons,interpretation='Exploratory paired seed-block summaries. Invalid API runs are separate from physical timeouts. Operational completion includes invalid executions as failures; physical/effort contrasts condition on both runs valid. No primary estimates while scheduled results are missing; no replay or synthetic replicates.')


def read_usage(audit):
    if audit.get('usageReported'):return audit['totalTokens']
    try:return json.loads(audit.get('response') or '{}').get('usage',{}).get('total_tokens')
    except (TypeError,ValueError):return None


def pilot_gate(plan_path,root,dispatch_results,willingness_results,runtime_folder,output):
    lock,_=verify(plan_path,root)
    if Path(output).exists():raise ValueError('Pilot gates are immutable; a failed gate requires a disclosed amended plan')
    dispatch=analyze_fixed(plan_path,root,dispatch_results,'Calibration')
    willingness=analyze_willingness(plan_path,root,willingness_results,'Calibration')
    runtime=analyze_runs(plan_path,root,runtime_folder,'Calibration')
    if not all(r['complete'] for r in (dispatch,willingness,runtime)):raise ValueError('Pilot phase is incomplete; do not certify a partial favorable subset')
    live=[r for r in lines(dispatch_results) if r['execution']=='live'];live_valid=sum(r['llmValid'] for r in live)
    api_runs=[r for r in runtime['runs'] if r['groupId'] in {'A3','W2'}]
    complete_audits=True
    for config in Path(runtime_folder).rglob('*_config.json'):
        c=read(config)
        if c['coordinationStudyGroup']!='A3':continue
        prefix=str(config)[:-len('_config.json')]
        if len(lines(prefix+'_coordination_requests.jsonl'))!=len(lines(prefix+'_coordination_trace.jsonl')) or len(lines(prefix+'_coordination_trace.jsonl'))!=len(lines(prefix+'_coordination_application.jsonl')):
            complete_audits=False
    passed=(len(live)>=8 and live_valid/len(live)>=.9 and willingness['observed']>=8 and willingness['invalid']/willingness['observed']<=.1 and bool(api_runs) and sum(not r['valid'] for r in api_runs)/len(api_runs)<=.1 and complete_audits)
    inputs=[Path(dispatch_results),Path(willingness_results)]+[f for f in Path(runtime_folder).rglob('*') if f.is_file() and f.suffix in {'.json','.jsonl','.csv'}]
    payload=dict(schema='coordination-pilot-gate-v1',planID=lock['planID'],passed=passed,completeAudits=complete_audits,
                 liveDispatchResponses=len(live),validLiveDispatchResponses=live_valid,willingness=willingness,runtimeInvalid=sum(not r['valid'] for r in api_runs),
                 inputFiles=[dict(path=f.resolve().relative_to(Path(root).resolve()).as_posix(),sha256=sha(f)) for f in sorted(set(inputs))])
    text=canonical(payload);envelope=dict(schema='coordination-pilot-gate-lock-v1',gateID=hashlib.sha256(text.encode()).hexdigest(),payloadJson=text)
    write(output,envelope);return dict(passed=passed,gateID=envelope['gateID'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','freeze','verify','claim','analyze-fixed','analyze-willingness','analyze-runs','pilot-gate']);parser.add_argument('--root',type=Path,default=Path('.'));parser.add_argument('--plan',type=Path,default=Path('research/s5/coordination-study.lock.json'));parser.add_argument('--output',type=Path);parser.add_argument('--job');parser.add_argument('--results',type=Path);parser.add_argument('--phase',choices=SPLITS,default='Calibration');parser.add_argument('--ledger-root',type=Path,default=Path('experiment_records'));parser.add_argument('--dispatch-results',type=Path);parser.add_argument('--willingness-results',type=Path);parser.add_argument('--runtime-results',type=Path)
    a=parser.parse_args()
    if a.command=='prepare':result=prepare(a.root)
    elif a.command=='freeze':result=freeze(a.root,a.output or a.plan)
    elif a.command=='verify':lock,p=verify(a.plan,a.root);result=dict(planID=lock['planID'],budgets=p['budgets'],jobs=len(p['jobs']))
    elif a.command=='claim':result=claim(a.plan,a.root,a.job,a.ledger_root)
    elif a.command=='analyze-fixed':result=analyze_fixed(a.plan,a.root,a.results,a.phase)
    elif a.command=='analyze-willingness':result=analyze_willingness(a.plan,a.root,a.results,a.phase)
    elif a.command=='analyze-runs':result=analyze_runs(a.plan,a.root,a.results,a.phase)
    else:
        lock,_=verify(a.plan,a.root)
        result=pilot_gate(a.plan,a.root,a.dispatch_results,a.willingness_results,a.runtime_results,a.output or a.ledger_root/'study_ledgers'/lock['planID']/'pilot-gate.json')
    if a.command not in {'freeze','pilot-gate'} and a.output:write(a.output,result)
    print(json.dumps({k:v for k,v in result.items() if k not in {'jobs','payloadJson','sourceFiles','datasetFiles'}},ensure_ascii=False))


if __name__=='__main__':main()
