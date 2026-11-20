"""Build/verify immutable individual sampling bundles; never starts API calls."""
import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path
from individual_analysis import audit, digest, read, require, strict_json, validate_plan, write_json

FULL={'single_help_payoff':'.95','single_decline_partial':'.5','single_decline_blocked':'.5','multi_help':'.95','multi_free_ride':'1','multi_nobody':'.5','multi_high_help':'.8','multi_high_nobody':'.5'}
BASE={'payoff_participate':'.98','payoff_free_ride':'1','payoff_nobody':'.4','loss_meaning':'B','decline_not_escape':'false','candidate_not_handler':'false','omega_not_personality':'C','base_not_adjusted_law':'false','reference_not_prescription':'false','blockage_scope':'A'}


def assessment(folder,version,key,model):
    folder=Path(folder);s=read(folder/'summary.json')
    require(s['suiteVersion']==version and s['specVersion']=='paper-agent-v5' and s['model']==model and s['passed'] is True and s['correct']==len(key) and s['attempted']==len(key) and s['invalid']==0,'Assessment incomplete/incompatible')
    rows=[strict_json(r) for r in (folder/'trace.jsonl').read_text(encoding='utf-8-sig').splitlines() if r.strip()]
    require(len(rows)==len(key) and {r['questionID'] for r in rows}==set(key),'Assessment question coverage mismatch')
    providers=set()
    for r in rows:
        require(r['transportSucceeded'] is True and not r['requestError'],'Failed assessment transport')
        envelope=strict_json(r['response']);require(len(envelope['choices'])==1,'Assessment choices')
        c=envelope['choices'][0];m=c['message']
        require(c['finish_reason']=='stop' and m['role']=='assistant' and not m.get('refusal'),'Invalid assessment envelope')
        answer=strict_json(m['content']);require(set(answer)=={'question_id','answer'} and answer['question_id']==r['questionID'] and isinstance(answer['answer'],str),'Invalid assessment answer')
        expected=key[r['questionID']];value=answer['answer'].strip()
        if expected in ('A','B','C','false','true'):ok=value.lower()==expected.lower()
        else:
            try:ok=math.isfinite(float(value)) and abs(float(value)-float(expected))<=1e-6
            except ValueError:ok=False
        require(ok,'Incorrect factual assessment answer')
        require(isinstance(envelope.get('model'),str) and envelope['model'],'Missing provider version')
        providers.add(envelope['model'])
    require(len(providers)==1,'Assessment model drift')
    return providers.pop()


def identity(d):
    lines=[d[k] for k in ('schema','executionMode','planSHA256','promptSHA256','expectedProviderModel')]+[str(d['sessionChoices'])]
    lines += ['A:'+f['path']+':'+f['sha256'] for f in sorted(d['artifacts'],key=lambda f:f['path'])]
    lines += ['S:'+f['path']+':'+f['sha256'] for f in sorted(d['sourceFiles'],key=lambda f:f['path'])]
    return hashlib.sha256('\n'.join(lines).encode()).hexdigest()


def verify(bundle,root=None):
    bundle=Path(bundle).resolve();d=read(bundle/'lock.json');require(d['lockID']==identity(d),'Lock identity changed')
    require(d['schema']=='individual-sampling-lock-v1' and d['executionMode'] in ('api','synthetic_test') and 1<=d['sessionChoices']<=1000,'Unsupported lock')
    for f in d['artifacts']:
        path=(bundle/f['path']).resolve();require(path.is_relative_to(bundle) and digest(path)==f['sha256'],'Frozen artifact changed')
    require(digest(bundle/'plan.json')==d['planSHA256'],'Frozen plan changed')
    if root is not None:
        root=Path(root).resolve()
        for f in d['sourceFiles']:
            path=(root/f['path']).resolve();require(path.is_relative_to(root) and digest(path)==f['sha256'],'Frozen source changed')
        expected={f['path'] for f in d['sourceFiles'] if f['path'].startswith('Assets/scripts/') and f['path'].endswith('.cs')}
        require(expected=={p.relative_to(root).as_posix() for p in (root/'Assets/scripts').rglob('*.cs')},'Source inventory changed')
    return d


def freeze(root,plan_path,design_path,comprehension,diagnostic,pilot,output,session_choices=250,synthetic=False):
    root=Path(root).resolve();output=Path(output).resolve();require(not output.exists(),'Choose a new immutable bundle directory')
    p=read(plan_path);validate_plan(p);require(p['purpose'].startswith('Formal:'),'Formal purpose prefix required')
    eligible=sum(s['nearbyAgentCount']>0 and s['exitNonBlockage']<1 for s in p['scenarios'])*p['repetitions']
    require(p['maxHttpAttempts']>=3*eligible,'Global reservation budget cannot cover planned choices')
    require(type(session_choices) is int and 1<=session_choices<=1000,'Session limit must be 1..1000')
    data=audit(pilot,synthetic);require(data['plan']['model']==p['model'] and all(r['invalid']==r['missing']==0 for r in data['rows']),'Pilot incomplete/incompatible')
    require(not data['plan']['purpose'].startswith('Formal:'),'Formal data cannot serve as the independent pilot')
    require(data['mode']==('synthetic_test' if synthetic else 'api'),'Pilot execution mode mismatch')
    require(len(data['providerModels'])==1,'Pilot provider version missing')
    provider=data['providerModels'][0]
    require(assessment(comprehension,'paper-comprehension-v3',BASE,p['model'])==provider,'Comprehension provider mismatch')
    require(assessment(diagnostic,'paper-payoff-diagnostic-v2',FULL,p['model'])==provider,'Diagnostic provider mismatch')
    rules=(Path(pilot)/'instructions.txt').read_bytes()
    require(all((Path(f)/'public_rules.txt').read_bytes()==rules for f in (comprehension,diagnostic)),'Public rules changed across phases')
    design=read(design_path)
    require(design.get('schema')=='individual-formal-design-v1' and design.get('model')==p['model'] and design.get('promptVersion')==p['promptVersion'] and design.get('primaryContrast') and design.get('failurePolicy') and design.get('multiplicityPolicy') and design.get('pilotExcluded') is True and design.get('modelLifecycleReviewed') is True,'Formal design fields/review required')
    semantic=None
    if design.get('transport',{}).get('responseProtocol')=='paper-choice-response-v3':
        from semantic_release_gate import evaluate
        semantic=(root/design['semanticReleaseGate']).resolve()
        require(semantic.is_relative_to(root), 'Semantic gate must be project-local')
        gate=evaluate(semantic)
        require(gate['passed'] and read(semantic/'release-gate.json')==gate, 'Current v3 semantic release gate failed or changed')
        from individual_analysis import validate_payload
        for trial in (Path(pilot)/'trials').glob('*.json'):
            t=read(trial)
            if t['execution']!='no_game':
                require(validate_payload(t['payload'],t['observation'],p['model'],rules.decode('utf-8-sig'))=='paper-choice-response-v3', 'V3 formal lock requires a fresh v3 pilot')
    contrast=design['primaryContrast'];factor=contrast.get('factor')
    require(factor in ('nearbyAgentCount','exitNonBlockage','volunteerCost','failureCost','unwillingness') and set(contrast.get('fixed',{}))==set(p['scenarios'][0])-{'id',factor} and contrast.get('fromValue')!=contrast.get('toValue'),'Invalid primary comparison specification')
    for value in (contrast['fromValue'],contrast['toValue']):
        state=dict(contrast['fixed'],**{factor:value})
        require(sum(all(math.isclose(s[f],v,rel_tol=2e-7,abs_tol=1e-9) for f,v in state.items()) for s in p['scenarios'])==1,'Primary endpoint missing or ambiguous')
    require(not output.is_relative_to(Path(pilot).resolve()) and not Path(pilot).resolve().is_relative_to(output),'Separate formal bundle from pilot')
    output.mkdir(parents=True)
    shutil.copyfile(plan_path,output/'plan.json');shutil.copyfile(design_path,output/'design.json')
    for name,folder in [('comprehension',comprehension),('diagnostic',diagnostic)]:
        for filename in ('summary.json','trace.jsonl','suite_key.json','public_rules.txt'):
            target=output/'prerequisites'/name/filename;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(Path(folder)/filename,target)
    for file in data['files']:
        target=output/'prerequisites/pilot'/file.relative_to(Path(pilot).resolve());target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
    if semantic is not None:
        for file in sorted(semantic.rglob('*')):
            if file.is_file():
                target=output/'prerequisites/semantic'/file.relative_to(semantic)
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
    sources=sorted((root/'Assets/scripts').rglob('*.cs'))+[root/'tools'/n for n in ('formal_sampling.py','individual_analysis.py','individual_sampling.py','payoff_review.py','run_formal_sampling.py','individual_study_design.py','individual_readiness.py','run_individual_study.ps1')]
    if semantic is not None:sources.append(root/'tools/semantic_release_gate.py')
    source_hashes=[]
    for file in sources:
        rel=file.relative_to(root).as_posix();source_hashes.append(dict(path=rel,sha256=digest(file)));target=output/'source_snapshot'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
    d=dict(schema='individual-sampling-lock-v1',executionMode='synthetic_test' if synthetic else 'api',planSHA256=digest(output/'plan.json'),promptSHA256=hashlib.sha256(rules).hexdigest(),expectedProviderModel=provider,sessionChoices=session_choices,
           artifacts=[dict(path=f.relative_to(output).as_posix(),sha256=digest(f)) for f in sorted(output.rglob('*')) if f.is_file()],sourceFiles=source_hashes)
    d['lockID']=identity(d);write_json(output/'lock.json',d);verify(output,root);return d


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--verify',type=Path);p.add_argument('--plan',type=Path);p.add_argument('--design',type=Path);p.add_argument('--comprehension',type=Path);p.add_argument('--diagnostic',type=Path);p.add_argument('--pilot',type=Path);p.add_argument('--output',type=Path);p.add_argument('--session-choices',type=int,default=250);p.add_argument('--synthetic',action='store_true');a=p.parse_args()
    if a.verify:print('Verified '+verify(a.verify,a.root)['lockID'])
    else:
        if any(v is None for v in (a.plan,a.design,a.comprehension,a.diagnostic,a.pilot,a.output)):p.error('All plan/design/prerequisite/output paths are required')
        print('Frozen '+freeze(a.root,a.plan,a.design,a.comprehension,a.diagnostic,a.pilot,a.output,a.session_choices,a.synthetic)['lockID']+'; no API calls')
