"""Prospective bounded scenario pilot registration; no API dispatch."""
from pathlib import Path
import json,hashlib,random,shutil,msvcrt,os
import scenario_agent_contract as c
import scenario_agent_transport as t

def main():
    root=c.ROOT;bundle=root/'experiment_records/data/preparation/scenario_agent_stage3_20261116'
    folder=root/'experiment_records/study_preparations/scenario_pilot_v1_20261116'
    c.require(not folder.exists(),'Preserve previous pilot registration')
    c.verify(bundle)
    for item in c.read(c.DESIGN/'STAGE4_RECEIPT.json')['files']:
        c.require(c.sha((root/item['path']).read_bytes())==item['sha256'],'Stage4 source/codebook drift')
    folder.mkdir(parents=True);cases=c.read(bundle/'cases.json')
    settings=[('abstract_diagnostic',2,2026111651),('physical_diagnostic',2,2026111652),('abstract_choice',5,2026111653),('physical_choice',5,2026111654)]
    phases=[]
    for phase,reps,seed in settings:
        trials=[{'trialID':f"{x['caseID']}_r{i:03d}",'case':x,'repetition':i} for x in cases if x['phase']==phase for i in range(1,reps+1)]
        random.Random(seed).shuffle(trials)
        phases.append({'phase':phase,'repetitions':reps,'orderSeed':seed,'count':len(trials),'trials':trials,'trialSHA256':c.sha(c.data(trials))})
    require=lambda x,msg:c.require(x,msg)
    require([x['count'] for x in phases]==[36,32,60,80],'Pilot allocation mismatch')
    plan={'schema':'scenario-stage5-prospective-pilot-v1','registrationID':'P-029','registeredAtUtc':t.now(),'dateLocal':'2026-11-16',
        'purpose':'Small development pilot of individual choices and stated reasons across abstract utilities and physically grounded forecast information; not a new formal ranking or human study',
        'model':c.MODEL,'profile':c.profile(),'bundlePath':str(bundle),'bundleSHA256':c.sha((bundle/'INTERFACE.json').read_bytes()),
        'codebookVersion':c.read(c.DESIGN/'reason-codebook.v3.json')['version'],'codebookSHA256':c.sha((c.DESIGN/'reason-codebook.v3.json').read_bytes()),
        'phases':phases,'maxLogicalChoices':208,'maxAttempts':208,'automaticRetries':0,'maxGeneratedTokens':208*220,
        'maxPayloadBytes':sum(len(c.data(trial['case']['payload'])) for phase in phases for trial in phase['trials']),
        'phaseOrder':['abstract_diagnostic','manual_abstract_reason_review','physical_diagnostic','manual_physical_reason_review','abstract_choice','physical_choice','full_reason_coding'],
        'gateCriteria':'All32 abstract non-tie actions correct;4 ties accept either. All32 physical actions follow supplied mean-own-time comparisons (ties accept either). All68 reasons reviewed: correct comparison, consistent action, no unsupported information, arithmetic correct or not applicable, not insufficient. No unclear gate judgments.',
        'stopRule':'Any technical invalid, wrong diagnostic action, source/profile drift, missing evidence, or failed/unclear gate reason stops the whole campaign. Preserve all raw and partial data. No automatic retry, refill, resume, prompt repair or next phase after a stop.',
        'sampleRationale':'Five repetitions per free-choice condition is a feasibility/variation pilot, not a power or precision guarantee. Use counts and full reasons. Retain saturated/negative conditions. Never expand based on outcomes; pilot excluded from later formal data.',
        'analysis':'Report abstract cells by wording and physical cells by geometry-only versus forecast. Do not pool tasks/diagnostics/free choices. Report all readable reasons, failures and missing registered rows. Multi-label denominator is reviewed eligible reasons; no independent human/hidden-reasoning claim.',
        'modelAvailability':'First registered request also establishes account/profile compatibility only if it succeeds; no unrecorded preflight request or model substitution.',
        'resources':'Each attempt timeout60s, phase wall budget from frozen transport. Fixed request/output ceilings are not a dollar-price guarantee. Actual provider usage retained in raw response.',
        'officialModelDocumentation':'https://developers.openai.com/api/docs/models/gpt-6-luna','sourceSHA256':{str(f.relative_to(root)).replace('\\','/'):c.sha(f.read_bytes()) for f in [Path(__file__),root/'tools/scenario_agent_contract.py',root/'tools/scenario_agent_transport.py',root/'tools/scenario_reason_coding.py',c.DESIGN/'reason-codebook.v3.json']}}
    c.write_new(folder/'plan.json',plan)
    for f in [root/'tools/scenario_agent_contract.py',root/'tools/scenario_agent_transport.py',root/'tools/scenario_reason_coding.py',c.DESIGN/'reason-codebook.v3.json']:
        shutil.copyfile(f,folder/f.name)
    c.write_new(folder/'REGISTRATION.json',{'registeredBeforeDispatch':True,'registrationID':'P-029','planSHA256':c.sha((folder/'plan.json').read_bytes()),'plannedMaxAttempts':208,'actualDispatchesAtRegistration':0})
    t.register(bundle,folder/'abstract_diagnostic.registration.json','abstract_diagnostic',2,2026111651)
    actual=c.read(folder/'abstract_diagnostic.registration.json')['trials'];require(actual==phases[0]['trials'],'Phase registration differs from prospective master')
    entry='''## P-029 — Prospective small two-layer scenario pilot (2026-11-16, Asia/Taipei)

Purpose: inspect scenario-dependent individual choices and stated reasons at small scale, not demonstrate superiority or human validity. Frozen master: experiment_records/study_preparations/scenario_pilot_v1_20261116/plan.json. Maximum208 logical choices/HTTP attempts, no automatic retries:36 abstract diagnostic (18 conditions x2),32 physical diagnostic (16 x2),60 abstract free (12 x5),80 physical free (16 x5). Fixed order seeds2026111651–54. All phases' exact payloads/order and source/codebook hashes prospectively stored. Free phase registrations are materialized only after matching live gate/reason evidence, and must match the master matrix.

All32 non-tie abstract actions correct and4 tie actions unrestricted; physical diagnostics follow supplied own-time means. All68 reasons require full named comparison/action/information/arithmetic review, no unresolved or insufficient reason. Any invalid, wrong diagnostic action, failed/unclear gate reason, source drift or missing evidence stops the whole campaign; preserve partial data, no automatic next phase, refill, retry or repair. First registered request tests account/profile support; no hidden model probe or fallback. Model gpt-6-luna,temperature.15,reasoning none,220 output tokens. Five free repetitions per condition is a feasibility pilot, not a power/precision guarantee. All saturated and adverse conditions remain. Pilot is excluded from any later formal cohort. No Unity runs or human data.

Full reason coding uses scenario-reasons-v3 and bound original explanations; summaries separate tasks, diagnostic/free phases and information conditions. Actual token usage, raw replies, HTTP outcomes and uncertain dispatch claims retained. Fixed ceilings are not a dollar-price guarantee. This entry precedes all pilot dispatches;0 calls at registration. Source interface and analysis rules from V-040/V-041 remain unchanged.

'''
    log=root/'experiment_records/EXPERIMENT_LOG.md'
    with (root/'experiment_records/.notebook.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:
            text=log.read_text(encoding='utf-8');marker='<!-- AUTO-RECORDED RUNS -->';require(marker in text and '## P-029 —' not in text,'Registration notebook collision')
            tail=text.split(marker,1)[1];text=text.replace(marker,entry+marker,1);require(text.split(marker,1)[1]==tail,'Automatic tail changed')
            tmp=log.with_suffix('.p029.tmp');tmp.write_text(text,encoding='utf-8');os.replace(tmp,log)
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    print(json.dumps({'registered':'P-029','phaseCounts':[p['count'] for p in phases],'maxAttempts':208,'newAPICalls':0,'planSHA256':c.sha((folder/'plan.json').read_bytes())},indent=2))
if __name__=='__main__':main()
