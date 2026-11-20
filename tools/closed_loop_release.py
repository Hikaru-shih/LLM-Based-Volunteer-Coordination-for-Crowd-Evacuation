"""Freeze/check a group-study release; final execution is a separate explicit command."""
import argparse
import concurrent.futures
import hashlib
import json
import random
import shutil
from pathlib import Path

import closed_loop_study as s
from individual_analysis import require


def seal_folder(folder,name='artifact-manifest.json'):
    folder=Path(folder);target=folder/name
    files=[dict(path=f.relative_to(folder).as_posix(),sha256=s.digest(f),bytes=f.stat().st_size) for f in sorted(folder.rglob('*')) if f.is_file() and f!=target]
    s.save(target,dict(schema='group-evidence-sha256-v1',files=files));return len(files)
def verify_manifest(folder,name='artifact-manifest.json'):
    folder=Path(folder);d=s.read(folder/name)
    listed={f['path'] for f in d['files']};actual={f.relative_to(folder).as_posix() for f in folder.rglob('*') if f.is_file()}
    require(len(listed)==len(d['files']) and actual==listed|{name},'Frozen preparation inventory changed')
    for f in d['files']:
        path=(folder/f['path']).resolve();require(path.is_relative_to(folder.resolve()) and s.digest(path)==f['sha256'] and path.stat().st_size==f['bytes'],'Preparation evidence changed')
    return len(d['files'])
def phase_summary(prep,name,runs,geometry=False):
    v=s.read(prep/(name+'-analysis')/'summary.json')
    require(v['runs']==runs and v['invalid']==0 and v['geometryOnly']==geometry and not v['formalSimulationExecuted'],'Incomplete or wrong preparation evidence: '+name)
    return v
def verify_preparation(prep):
    prep=Path(prep);r=s.read(prep/'registration.json');require(r['sourceSHA']==s.source_sha() and r['includeRandomMatched'] and not r['finalSimulationExecutionAuthorized'],'Preparation source/scope changed')
    for name,n,geometry in [('geometry',60,True),('offline-development',120,False),('live-development',20,False),('calibration',80,False),('random-preflight',16,False),('replay',2,False),('final-geometry',300,True)]:
        v=phase_summary(prep,name,n,geometry);require(v['productionSourceSHA']==r['sourceSHA'],'Mixed preparation source')
        if name not in ('live-development','calibration'):require(v.get('httpAttempts',0)==0,'A no-API stage called a model')
    replay=s.read(prep/'replay-comparison.json');require(replay['passed'] and replay['cases']==2 and replay['apiRequests']==0,'Replay diverged')
    development=s.read(prep/'live-development-analysis/summary.json');calibration=s.read(prep/'calibration-analysis/summary.json')
    require(len(development['promptTemplateHashes'])==1 and development['promptTemplateHashes']==calibration['promptTemplateHashes'],'Development/calibration task prompt drift')
    quality=s.read(prep/'manual-quality-review.json')
    require(quality['reviewComplete'] and quality['explicitContradictions']==0 and quality['unresolvedSubstantiveIssues']==0 and quality['prespecifiedFirstLastReviewed']==192,'Quality review incomplete')
    expected_review=set();prespecified=set()
    for stage in ['live-development-0','live-development-1','calibration-0','calibration-1']:
        for trace in (prep/stage).rglob('*_agent_trace.jsonl'):
            lines=trace.read_text(encoding='utf-8-sig').splitlines()
            require(lines,'Empty paid-run trace')
            rel=trace.relative_to(prep).as_posix()
            prespecified.update((rel,i) for i in [0,len(lines)-1])
            for i,line in enumerate(lines):
                if s.answer(s.strict_json(line)['response'])[0]['decision']=='decline_assistance':expected_review.add((rel,i))
    require(len(prespecified)==192,'Paid-run first/last coverage changed')
    expected_review.update(prespecified);observed=set()
    # All declared annotation hashes must still refer to preserved original responses.
    for row in quality['records']:
        key=(row['trace'],row['line']);require(key not in observed,'Duplicate review annotation');observed.add(key)
        path=(prep/row['trace']).resolve();require(path.is_relative_to(prep.resolve()),'Review path outside preparation');lines=path.read_text(encoding='utf-8-sig').splitlines()
        require(hashlib.sha256(lines[row['line']].encode()).hexdigest()==row['lineSHA256'] and row['reviewed'] and not row['explicitContradiction'] and not row['unresolvedSubstantiveIssue'],'Unbound or unresolved manual review')
    require(observed==expected_review,'Prespecified/all-decline review coverage incomplete')
    cals=list((prep/'calibrations').glob('*.json'));require(len(cals)==8,'Missing calibrations')
    calibration_runs=s.read(prep/'calibration-analysis/runs.json')
    for f in cals:
        c=s.read(f);require(c['schema']=='cooperation-calibration-v2' and c['responseProtocol']=='paper-choice-response-v3' and c['productionSourceSHA']==r['sourceSHA'] and c['horizon']==300 and c['seeds']==list(range(42001,42011)) and c['decisions']>0 and 0<=c['probability']<=1,'Invalid independent calibration')
        rows=[row for row in calibration_runs if row['cell']==f.stem]
        require(len(rows)==10 and sorted(row['seed'] for row in rows)==c['seeds'],'Calibration cell/seed coverage drift')
        decisions=sum(row['decisions'] for row in rows);willing=sum(row['willing'] for row in rows)
        require(c['decisions']==decisions and abs(c['probability']-willing/decisions)<1e-12,'Calibration rate differs from preserved decisions')
        require(all(row['condition']==c['conditionKey'] and row['templateSHA']==c['geometryTemplateSHA'] for row in rows),'Calibration condition binding drift')
        identity=dict(c);identity.pop('calibrationID');require(c['calibrationID']==hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest(),'Calibration identity changed')
    offline=s.read(prep/'offline-development-analysis/runs.json')
    require(all(x['termination']=='completed' for x in offline if x['blocked']==0),'Benign open-room control failed within H')
    require(all(x['evacuated']==0 and x['termination']=='timeout' and x['A_H']==300 for x in offline if x['blocked']==5 and x['policy']=='NoVolunteers'),'Full-blockage physical control inconsistent')
    return r
def lock_identity(d):
    text=d['schema']+'\n'+d['productionSourceSHA']+'\n'+d['formalPlanSHA']+'\n'+'\n'.join(f['path']+':'+f['sha256'] for f in sorted(d['artifacts'],key=lambda f:f['path']))
    return hashlib.sha256(text.encode()).hexdigest()
def freeze(prep,bundle,registration=None):
    prep,bundle=Path(prep).resolve(),Path(bundle).resolve();require(not bundle.exists(),'Choose a new immutable group bundle')
    r=verify_preparation(prep);verify_manifest(prep)
    spec=s.read(s.ROOT/'research/closed_loop_v1/design.draft.json');cells=spec['cells'];seeds=list(range(51001,51031))
    replacement=s.read(registration) if registration else None
    geometry=prep/'final-geometry-analysis'
    if replacement:
        require(replacement['executionAuthorized'] and replacement['productionSourceSHA']==s.source_sha(),'Unapproved/source-drift replacement')
        seeds=replacement['seeds'];require(len(seeds)==30 and len(set(seeds))==30 and all(type(v)is int for v in seeds),'Invalid replacement seeds')
        require(not set(seeds)&set(range(51001,51031)),'Cannot reuse interrupted final seeds')
        geometry=s.ROOT/replacement['geometryAnalysis']
        summary=s.read(geometry/'summary.json');require(summary['runs']==300 and summary['geometryOnly'] and summary['invalid']==0 and summary['productionSourceSHA']==s.source_sha(),'Replacement geometry incomplete')
    rows=s.read(geometry/'runs.json');bindings={(row['cell'],row['seed']):row for row in rows};require(set(bindings)=={(c['id'],seed) for c in cells for seed in seeds},'Final geometry coverage mismatch')
    work=s.jobs(cells,seeds,['OriginalGameTheory','LLM','NoVolunteers'],'FinalTest')+s.jobs([c for c in cells if c['stratum']=='blocked'],seeds,['RandomMatched'],'FinalTest')
    for j in work:
        b=bindings[(j['cell'],j['seed'])];j['conditionKey']=b['condition'];j['initialStateSHA']=b['initialStateSHA']
        if j['policy']=='RandomMatched':j['calibrationFile']='calibration/'+j['cell']+'.json'
    require(len(work)==1140 and len({j['id'] for j in work})==1140,'Wrong final matrix')
    random.Random(2026111305).shuffle(work)
    calibration_rows=s.read(prep/'calibration-analysis/runs.json');maxima={}
    for row in calibration_rows:maxima[row['cell']]=max(maxima.get(row['cell'],0),row['apiCalls'])
    # Reserve twice the sum of condition-wise observed maximum calls, extrapolated to30 seeds.
    budget=3*2*30*sum(maxima.values());require(budget>0,'No calibration usage evidence')
    bundle.mkdir(parents=True);s.campaign(bundle/'formal-plan.json','FinalTest',work,budget,wall_seconds=43200)
    design=dict(schema='closed-loop-formal-design-v1',scope='Group evacuation, individual willingness only',status='locked_before_final_collection',model='gpt-6-luna',promptVersion='paper-agent-v5',responseProtocol='paper-choice-response-v3',information='Core',wording='Standard',horizon=300,finalSeedBlocks=30,seedSplits=spec['seedCandidates'],policies=['OriginalGameTheory','LLM','NoVolunteers','RandomMatched'],cells=cells,formalRuns=1140,LLMJobs=300,potentiallyPaidLLMJobs=240,populationNNotEligibilityX=True,primary=dict(metric='mean_i min(T_i,H)',contrast='Per base seed, equal mean of LLM-minus-original A_H over eight blocked cells, then average over30 seeds',bootstrapIterations=4000,bootstrapSeed=2026111304,confirmatoryTests=False,multiplicity='One designated primary descriptive interval; all other comparisons exploratory'),sampleSizeRationale='Thirty prospective balanced-mirror base seed blocks is a feasibility/descriptive design, not a power guarantee. Development and calibration are not final replicates.',resources=dict(perRunLogicalGuard='H*N*5',globalMaxHttpReservations=budget,globalMaximumLogicalReservations=budget//3,formula='3 attempts x safety factor2 x30 final seeds x sum(condition-wise maximum observed Calibration logical calls)',limitation='Below the universal H*N*obstacle bound; an unexpected resource stop invalidates/stops the campaign, never selectively excludes high-call runs or becomes a horizon timeout.'),failurePolicy='Stop on invalid/source/provider drift/budget/wall failure; retain all valid timeouts and unknown claims/reservations. No source changes, outcome-based exclusions, mock/repair or rescue reruns.',calibration='Eight condition-specific decision-weighted constant probabilities from10 independent calibration seeds each; no exact FinalTest rate guarantee; no inference of intelligence from matched-control differences.',randomization='Fixed job orderSeed2026111305; deterministic nested/mirrored initial states, policy-paired actual manifests; no claim of identical exogenous draws after trajectory divergence.',replayAndPilotsExcluded=True,finalExecutionAuthorized=False,physics='PaperRelocation/PaperReference/PolicyWillingness with common frozen manifest and settings',interpretation='Layout not pure tau effect; N also changes density; API latency is not simulated evacuation latency; no human validation or global optimality claim.',modelAliasLimitation='Provider-reported alias is required; identical alias cannot guarantee immutable backend or independent outputs.')
    design['taskTemplateSHA256']=s.read(prep/'live-development-analysis/summary.json')['promptTemplateHashes'][0]
    design['registeredFinalSeeds']=seeds
    if replacement:
        design['replacementRegistration']=replacement
        design['seedSplits']['replacementFinal']=seeds
        s.save(bundle/'replacement-registration.json',replacement)
        s.save(bundle/'replacement-geometry-runs.json',rows)
        s.save(bundle/'replacement-geometry-summary.json',summary)
        for name in ['experiment_records/data/validation/progress_share_v1/result.json','experiment_records/data/preparation/group_replacement_v2/python-validation.json']:
            f=s.ROOT/name;require(f.is_file(),'Replacement validation missing')
            s.save(bundle/('replacement-'+f.parent.name+'-'+f.name),s.read(f))
    design['resources']['wallSecondsPerWorker']=43200
    design['resources']['wallRationale']='12-hour computational ceiling per worker, separate from physical H300. Two workers and conservative HTTP reservations address runtime feasibility, not outcome-dependent censoring.'
    design['decisionTiming']='Calls occur only at the original individual willingness trigger. Record actual decision steps/X/tau; a one-round recruitment outcome is not continuous LLM planning.'
    design['calibrationUncertainty']='Final intervals condition on the frozen estimated p and do not propagate calibration-estimation uncertainty. Preserve per-seed calibration counts/rates/SD; RandomMatched contrasts remain exploratory.'
    design['formalExplanationReview']=dict(selection='First and last raw response per paid blocked LLM job, plus all declines separately; union avoids double counting',plannedFirstLastSelections=480,scope='Assistant manual narrow explicit action/reason and stated-payoff contradiction screen; not independent human validation, optimality grading with unknown beliefs or access to hidden reasoning',qualitativeClaimsPendingReview=True,rawActionsNeverRelabeled=True)
    s.save(bundle/'design.json',design)
    for f in (prep/'calibrations').glob('*.json'):
        target=bundle/'calibration'/f.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
    # Short, flat evidence filenames avoid Windows legacy export-path limits.
    index=[]
    selected=[prep/'registration.json',prep/'artifact-manifest.json',prep/'manual-quality-review.json',prep/'replay-comparison.json',prep/'unity-offline-result.json',prep/'python-tests.log']
    selected += sorted(prep.glob('*-analysis/summary.json'))
    for f in selected:
        require(f.is_file(),'Missing essential release evidence');name=s.digest(f)+f.suffix;target=bundle/'evidence'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
        index.append(dict(original=f.relative_to(s.ROOT).as_posix(),frozen=target.relative_to(bundle).as_posix(),sha256=s.digest(f)))
    s.save(bundle/'evidence-index.json',dict(preparation=prep.relative_to(s.ROOT).as_posix(),preparationManifestSHA256=s.digest(prep/'artifact-manifest.json'),files=index))
    s.snapshot(bundle)
    for filename in ['closed_loop_release.py','closed_loop_report.py','run_closed_loop_study.ps1','individual_sampling.py','test_closed_loop_study.py','shared_progress_io.py']:
        f=s.ROOT/'tools'/filename;dest=bundle/'source_snapshot/tools'/filename;shutil.copyfile(f,dest)
    for relative in ['research/closed_loop_v1/formal-launch.json','research/closed_loop_v1/design.draft.json']:
        dest=bundle/'source_snapshot'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(s.ROOT/relative,dest)
    files=[dict(path=f.relative_to(bundle).as_posix(),sha256=s.digest(f)) for f in sorted(bundle.rglob('*')) if f.is_file()]
    d=dict(schema='closed-loop-lock-v1',productionSourceSHA=s.source_sha(),formalPlanSHA=s.digest(bundle/'formal-plan.json'),artifacts=files);d['lockID']=lock_identity(d);s.save(bundle/'lock.json',d)
    return check(bundle,[s.ROOT/'tmp/completion-project',s.ROOT/'tmp/wb'])
def check(bundle,projects=()):
    bundle=Path(bundle).resolve();d=s.read(bundle/'lock.json');require(d['lockID']==lock_identity(d),'Group lock identity changed')
    require(s.source_sha()==d['productionSourceSHA'],'Current production source differs from group lock')
    for project in projects:require(s.source_sha(project)==d['productionSourceSHA'],'Worker source drift')
    for frozen in (bundle/'source_snapshot/tools').iterdir():
        require(s.digest(s.ROOT/'tools'/frozen.name)==s.digest(frozen),'Current operational tool differs from frozen source: '+frozen.name)
    require(s.digest(s.ROOT/'research/closed_loop_v1/formal-launch.json')==s.digest(bundle/'source_snapshot/research/closed_loop_v1/formal-launch.json'),'Launch configuration drift')
    for f in d['artifacts']:
        path=(bundle/f['path']).resolve();require(path.is_relative_to(bundle) and s.digest(path)==f['sha256'],'Group frozen artifact changed')
    require(s.digest(bundle/'formal-plan.json')==d['formalPlanSHA'],'Final plan drift')
    index=s.read(bundle/'evidence-index.json');prep=s.ROOT/index['preparation'];require(s.digest(prep/'artifact-manifest.json')==index['preparationManifestSHA256'],'Preparation manifest changed');verified=verify_manifest(prep)
    p=s.read(bundle/'formal-plan.json');require(p['phase']=='FinalTest' and not p['paidFinalExecutionByDefault'] and len(p['jobs'])==1140,'Invalid final defaults/matrix')
    seeds=s.final_seed_blocks(p)
    design=s.read(bundle/'design.json')
    require(design.get('registeredFinalSeeds',seeds)==seeds,'Design/plan final seeds differ')
    claims=s.ROOT/'experiment_records/group_execution'/d['lockID']/'claims'
    return dict(schema='closed-loop-readiness-v1',sourceAndArtifactsVerified=True,readyScope='group_formal_collection_only_after_explicit_execution',lockID=d['lockID'],formalRuns=1140,finalSeedBlocks=30,finalJobsClaimed=len(list(claims.glob('*.json'))) if claims.exists() else 0,preparationVerifiedFiles=verified,groupLockArtifacts=len(d['artifacts']),globalMaxHttpReservations=p['maxReservedHttp'],finalExecutionPerformed=claims.exists() and any(claims.glob('*.json')))
def verify_preflight(path,lock_id):
    proof=s.read(path)
    require(proof['passed'] and proof['lockID']==lock_id and proof['cases']==76 and proof['remoteRequests']==proof['simulationSteps']==proof['formalJobsClaimed']==0,'Actual final-lock zero-step proof missing or mismatched')
    return proof

def execute(bundle,projects,outputs,preflight):
    require(len(projects)==len(outputs)==2,'Two distinct worker projects/outputs required');result=check(bundle,projects)
    require(len({Path(p).resolve() for p in projects})==2 and len({Path(p).resolve() for p in outputs})==2,'Worker/output paths must be distinct')
    verify_preflight(preflight,result['lockID'])
    require(result['finalJobsClaimed']==0 and not any(Path(p).exists() for p in outputs),'No automatic rerun/resume of a claimed final campaign')
    lock=Path(bundle)/'lock.json';plan=Path(bundle)/'formal-plan.json';stop=Path(outputs[0]).parent/'FINAL_STOP.txt'
    require(not stop.exists(),'Prior final-campaign stop requires review; no automatic retry')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(s.run,plan,projects[i],outputs[i],False,lock,True,stop,f'{i}/2') for i in range(2)]
        try:
            for f in concurrent.futures.as_completed(futures):f.result()
        except Exception as error:
            stop.parent.mkdir(parents=True,exist_ok=True)
            if not stop.exists():stop.write_text('Python campaign failure: '+str(error),encoding='utf-8')
            raise
    result=check(bundle,projects);require(result['finalJobsClaimed']==1140,'Final claims do not cover the complete matrix')
    return dict(result,outcome='final_campaign_completed')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='action',required=True)
    p=sub.add_parser('freeze');p.add_argument('preparation',type=Path);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--registration',type=Path)
    p=sub.add_parser('check');p.add_argument('--bundle',type=Path,required=True);p.add_argument('--projects',nargs='*',type=Path,default=[])
    p=sub.add_parser('execute');p.add_argument('--bundle',type=Path,required=True);p.add_argument('--projects',nargs=2,type=Path,required=True);p.add_argument('--outputs',nargs=2,type=Path,required=True);p.add_argument('--preflight',type=Path,required=True);p.add_argument('--execute-final',action='store_true')
    a=ap.parse_args()
    if a.action=='freeze':r=freeze(a.preparation,a.bundle,a.registration)
    elif a.action=='check':r=check(a.bundle,a.projects)
    else:require(a.execute_final,'Final execution is not part of preparation');r=execute(a.bundle,a.projects,a.outputs,a.preflight)
    print(json.dumps(r,indent=2))
