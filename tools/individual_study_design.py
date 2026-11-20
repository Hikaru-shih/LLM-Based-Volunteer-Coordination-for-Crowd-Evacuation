"""Audit the current P4 draft and bounded pilot. This never authorizes/freezes a formal study."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

from individual_analysis import FACTORS, audit as audit_run, contrasts, kind, read, require, validate_plan, verify as verify_report, write_json


def audit(draft, pilot):
    require(draft.get('schema')=='individual-study-design-v1' and draft.get('status')=='draft_before_pilot_not_formal_lock', 'Expected pre-pilot draft, not a formal lock')
    validate_plan(pilot)
    require(draft.get('information')=='Core' and draft.get('promptVersion')==pilot['promptVersion']=='paper-agent-v5' and draft.get('responseProtocol')=='paper-choice-response-v1', 'Unsupported task/protocol')
    require(draft.get('model')==pilot['model'], 'Pilot and draft models differ')
    require(draft.get('formalExecutionAuthorized') is False and draft.get('formalRepetitionsLocked') is False and draft['pilotLimits'].get('paidExecutionAuthorized') is False, 'Draft cannot claim execution authorization or a formal lock')
    comprehension=draft['pilotComprehension']
    require(comprehension==dict(version='paper-comprehension-v3',questions=10,requiredCorrect=10,maxHttpAttempts=30), 'Require the complete current comprehension suite')
    eligible=sum(kind(s)!='NoGame' for s in pilot['scenarios'])*pilot['repetitions']
    no_game=sum(kind(s)=='NoGame' for s in pilot['scenarios'])*pilot['repetitions']
    limits=draft['pilotLimits']
    require(pilot['maxHttpAttempts']==eligible*3, 'Pilot reservation cap does not match its eligible choices')
    require(limits['choiceLogicalCalls']==eligible and limits['comprehensionLogicalCalls']==10 and limits['totalLogicalCalls']==eligible+10 and limits['maxHttpAttempts']==eligible*3+30, 'Incorrect planned pilot budget')
    require(limits.get('monetaryBudget') is None, 'This draft has no approved monetary budget; do not infer one from request counts')
    levels=draft['proposedFactors']
    require(set(levels)==set(FACTORS) and all(isinstance(levels[f],list) and levels[f] and len(set(levels[f]))==len(levels[f]) for f in FACTORS), 'Invalid/duplicate factor levels')
    candidates=[dict(id=f'candidate_{i:03d}',**dict(zip(FACTORS,values))) for i,values in enumerate(itertools.product(*(levels[f] for f in FACTORS)))]
    require(all(s['nearbyAgentCount']>1 and s['exitNonBlockage']<1 for s in candidates), 'Main matrix must exclude single/no-game states')
    single=draft['singlePlayer']
    boundaries=[dict(id=f'single_{i:03d}',**{f:single[f] for f in FACTORS if f!='exitNonBlockage'},exitNonBlockage=tau) for i,tau in enumerate(single['exitNonBlockage'])]
    require(all(kind(s)=='ReferenceBoundary' for s in boundaries), 'Invalid single-player boundary design')
    controls=draft['noGameControls']
    require(len(controls)==2 and all(kind(s)=='NoGame' for s in controls), 'Require zero-player and unblocked negative controls')
    require(any(s['nearbyAgentCount']==0 for s in controls) and any(s['exitNonBlockage']==1 for s in controls), 'Missing no-game gate coverage')
    repetitions=draft['proposedFormalRepetitions']
    candidate_plan=dict(pilot,repetitions=repetitions,maxHttpAttempts=0,scenarios=candidates+boundaries+controls)
    validate_plan(candidate_plan)
    states={tuple(s[f] for f in FACTORS) for s in candidate_plan['scenarios']}
    require(all(tuple(s[f] for f in FACTORS) in states for s in pilot['scenarios']), 'Pilot state not represented by candidate design')
    contrast=draft['primaryContrast'];factor=contrast['factor']
    require(factor in FACTORS and set(contrast['fixed'])==set(FACTORS)-{factor} and contrast['fromValue']!=contrast['toValue'], 'Invalid primary contrast')
    for value in (contrast['fromValue'],contrast['toValue']):
        state=dict(contrast['fixed'],**{factor:value})
        require(tuple(state[f] for f in FACTORS) in states and kind(state)=='Choice', 'Primary contrast is not a controlled main-matrix comparison')
    require(draft.get('failurePolicy') and draft.get('separation') and draft.get('sampleSizeRule') and len(draft.get('pendingBeforeFormal',[]))>=4, 'Missing failure/split/readiness specification')
    n=repetitions
    halfwidth=1.959963984540054/(2*((n+1.959963984540054**2)**.5))
    return dict(schema='individual-study-draft-audit-v1',status='draft_validated_offline_not_live_ready',
                pilotStates=len(pilot['scenarios']),pilotEligibleChoices=eligible,pilotNoGameRecords=no_game,
                comprehensionQuestions=10,pilotTotalLogicalCalls=eligible+10,plannedPilotMaxHttpAttempts=eligible*3+30,
                pilotBudgetScope='One scheduled comprehension pass plus one sampling folder. Not a shared cross-run ledger or monetary cap; extra runs require separately recorded budget.',
                candidateMainStates=len(candidates),candidateBoundaryStates=len(boundaries),candidateNoGameStates=len(controls),
                provisionalRepetitions=n,candidateEligibleCalls=(len(candidates)+len(boundaries))*n,candidateMaxHttpAttempts=(len(candidates)+len(boundaries))*n*3,
                worstCaseWilsonHalfwidthIfAllValid=halfwidth,formalLocked=False,paidExecutionAuthorized=False,remoteRequests=0,
                remaining=draft['pendingBeforeFormal'])


def seal(root, draft_path, output):
    root=Path(root).resolve();draft_path=Path(draft_path).resolve();output=Path(output).resolve()
    require(not output.exists(), 'Preserve old audit; choose a new output')
    require(draft_path.is_relative_to(root), 'Draft must be project-local')
    draft=read(draft_path);pilot_path=(root/draft['pilotPlan']).resolve()
    require(pilot_path.is_relative_to(root), 'Pilot must be project-local')
    result=audit(draft,read(pilot_path))
    files=[draft_path,pilot_path,root/'tools/individual_study_design.py',root/'tools/individual_analysis.py',root/'tools/individual_sampling.py']
    files+=sorted((root/'Assets/scripts/Decision').glob('*.cs'))
    files+=[root/'Assets/scripts/Editor/IndividualSamplingRunner.cs',root/'Assets/scripts/Editor/LLMComprehensionRunner.cs']
    batch=root/'Assets/scripts/Editor/IndividualSamplingBatch.cs'
    if batch.exists():files.append(batch)
    result['files']=[dict(path=p.relative_to(root).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
    result['auditID']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    output.parent.mkdir(parents=True,exist_ok=True);write_json(output,result)
    return result


def verify(root,path):
    root=Path(root).resolve();value=read(path);identity=value.pop('auditID')
    require(hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()==identity, 'Audit changed')
    for file in value['files']:
        p=(root/file['path']).resolve()
        require(p.is_relative_to(root) and hashlib.sha256(p.read_bytes()).hexdigest()==file['sha256'], 'Draft/pilot/source changed; generate a new audit')
    return identity


def primary(draft, report_folder, allow_synthetic=False):
    """Evaluate the declared endpoints, which need not be adjacent matrix levels."""
    report_folder=Path(report_folder);verify_report(report_folder)
    data=audit_run(report_folder/'input_snapshot',allow_synthetic)
    require(data['plan']['model']==draft['model'] and data['plan']['promptVersion']==draft['promptVersion'], 'Primary contrast report/model mismatch')
    if data.get('formalLockID'):
        frozen=read(report_folder/'input_snapshot/study_lock/design.json')
        require(draft['primaryContrast']==frozen['primaryContrast'],'Primary contrast differs from the frozen study')
    contrast=draft['primaryContrast'];factor=contrast['factor'];points=[]
    for level in (contrast['fromValue'],contrast['toValue']):
        state=dict(contrast['fixed'],**{factor:level})
        # Unity float JSON is a float32 representation, not necessarily the short draft decimal.
        import math
        found=[r for r in data['rows'] if all(math.isclose(r[f],state[f],rel_tol=2e-7,abs_tol=1e-9) for f in FACTORS)]
        require(len(found)==1 and found[0]['stratum']=='Choice', 'Primary endpoint missing/ambiguous or outside main stratum')
        points.append(found[0])
    result=contrasts([dict(id='declared_primary',factor=factor,stratum='Choice',points=points)])[0]
    return dict(schema='individual-locked-primary-estimate-v1' if data.get('formalLockID') else 'individual-draft-primary-estimate-v1',execution=data['mode'],formalInference=False,
                formalLockID=data.get('formalLockID'),
                note='Frozen primary contrast, descriptive interval conditional on valid independent outputs; synthetic estimates are software validation only.' if data.get('formalLockID') else 'Declared draft contrast only. Pilot/synthetic estimates are not formal findings; intervals condition on valid independent outputs.',
                reportManifestSHA256=hashlib.sha256((report_folder/'manifest.json').read_bytes()).hexdigest(),estimate=result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('draft',type=Path);p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--output',type=Path);p.add_argument('--verify',action='store_true');p.add_argument('--primary-report',type=Path);p.add_argument('--allow-synthetic',action='store_true');a=p.parse_args()
    if a.verify:print('Verified draft audit '+verify(a.root,a.draft)+'; not a formal lock or live authorization.')
    elif a.primary_report:
        if a.output is None:p.error('--output required')
        require(not a.output.exists(), 'Preserve old primary estimate; choose a new output')
        result=primary(read(a.draft),a.primary_report,a.allow_synthetic);a.output.parent.mkdir(parents=True,exist_ok=True);write_json(a.output,result);print('Saved draft primary estimate; not formal inference.')
    else:
        if a.output is None:p.error('--output required')
        print(json.dumps(seal(a.root,a.draft,a.output),indent=2))
