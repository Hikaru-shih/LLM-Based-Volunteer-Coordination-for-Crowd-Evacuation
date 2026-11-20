"""Record prospective P030 design readiness only, without collecting formal choices."""
from pathlib import Path
import json,hashlib,msvcrt,os
import scenario_agent_contract as c
import scenario_formal as f
from closed_loop_study import source_sha

def main():
    root=c.ROOT;p=c.DESIGN;folder=root/'experiment_records/study_preparations/scenario_formal_v1_20261116_r2'
    reg=f.verify(folder/'registration.json');seal=c.read(folder/'LOCK.json')
    assert len(reg['trials'])==840 and not (f.CLAIMS_ROOT/(f.CAMPAIGN+'.json')).exists()
    assert source_sha()=='1466241a451c2d176f942ec8ebe26452a9df7e1a1be440d841f4b8cf83e2c59a'
    for item in c.read(root/'experiment_records/data/analysis/scenario_pilot_v1_20261116/SOURCE_MANIFEST.json'):
        assert c.sha((root/item['path']).read_bytes())==item['sha256']
    assert c.sha((root/'experiment_records/data/formal_summary/group_v2/COMPLETE.json').read_bytes())=='c28c59e67ba21092cb72fa4888f8eb79bd5d40e48c9310900a4f8607b40d8d6c'
    status={'date':'2026-11-16','registration':'P-030','status':'formal_design_locked_collection_not_started','formalConditions':28,'perCondition':30,'plannedChoices':840,
        'abstractChoices':360,'physicalChoices':480,'schedulingBlocks':30,'formalCollected':0,'newAPICallsThisStep':0,'newUnityRunsThisStep':0,
        'formalGuardTestsPassed':15,'lockID':seal['lockID'],'lockFolder':str(folder.relative_to(root)).replace('\\','/'),
        'readyForExplicitCollection':True,'automaticDispatch':False,'paperUtilityToTimeValidated':False,'humanValidityEstablished':False,
        'report':'FORMAL_DESIGN.zh-TW.md','scope':'Design and precollection tooling complete; formal results do not exist yet.',
        'next':'Execute the sealed P030 registration only as a separately explicit formal-collection action, then review all reasons and run the prespecified analysis.'}
    (p/'STAGE6_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    workflow=c.read(p/'WORKFLOW_STATUS.json');workflow.update(currentMilestone='formal_design_locked_collection_not_started',currentReport='FORMAL_DESIGN.zh-TW.md')
    workflow['stages']['3']='Two-layer interface implemented; P029 verified the same live profile and narrow comprehension gates'
    workflow['stages']['6']='P030 design and tools locked;840 planned choices,0 collected'
    (p/'WORKFLOW_STATUS.json').write_text(json.dumps(workflow,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for target,link in [(p/'README.zh-TW.md','FORMAL_DESIGN.zh-TW.md'),(root/'README.md','research/scenario_decisions_v2/FORMAL_DESIGN.zh-TW.md')]:
        text=target.read_text(encoding='utf-8');pointer=f'> **正式設計已鎖定（P-030）**：[研究問題、840次矩陣與分析規則]({link})。全部28條件各30次；正式收集0次。本步只完成設計與準備，不代表正式結果。\n\n'
        if '正式設計已鎖定（P-030）' not in text:target.write_text(text.replace('\n\n','\n\n'+pointer,1),encoding='utf-8')
    entry='''## P-030 — Prospective formal scenario comparison lock (2026-11-16, Asia/Taipei)

Pilot-informed formal descriptive replication, registered after P029 and before any new formal dispatch. Retain all28 free-choice conditions:6 abstract utility cells x2 wordings=12,8 physical scenarios x2 information conditions=16. Thirty fresh requests per condition,840 total (360 abstract,480 physical). Thirty scheduling blocks each contain all28, randomized within blocks with seed2026111661. New P030 trial IDs exclude all pilot IDs; no pilot replies or old P028 group outcomes enter formal estimates. Same fresh-context model/profile and exact stimulus contract as qualified P029;68 live gate/reason judgments reused only as identical-version qualification evidence.

Primary descriptive A: per-block mean across2 utility scales and2 wordings of [(Y_R90-Y_R10)-(pRef_R90-pRef_R10)], then mean across30 blocks. Primary B: per-block equal mean across8 physical scenarios of Y_forecast-Y_geometry, then mean across30 blocks. Five thousand whole-block bootstrap resamples, seed2026111662, pointwise descriptive95% percentile intervals. No confirmatory p-values or joint coverage claim. Other cell/scale/wording/layout/work/reason comparisons secondary/exploratory. Thirty per cell is a feasibility/full-review rationale, not a power or human-independent sampling guarantee; n30 Wilson worst-case interval scale~[.332,.668] only under independent-binomial assumptions.

All840 readable valid reasons require fixed scenario-reasons-v3, exact evidence spans, named assistant coding and full denominator/coverage reporting. Quality problems retained without raw-action repair or outcome-based exclusion; no human agreement or hidden-reasoning claim. Physical-time task remains separate from original Eq20 utility. Fixed earlier six-seed forecasts are stimuli, not840 independent simulations or validated human seconds.

One process,840 HTTP attempts max,one per trial,220 output tokens each (184800 maximum),60s attempt timeout,10800s collection wall ceiling,0 retries/fallback/refill/automatic restart. First technical invalid/network uncertainty/source-profile drift/duplicate provider ID/budget stop ends collection with partial evidence retained and formal incomplete. Valid free reason problems remain coded rather than treated as technical invalids. Campaign-wide exclusive dispatch claim prevents resending under another output path or copied lock. Claim is a reservation, not proof of provider dispatch. No dollar-price guarantee.

Active lock: experiment_records/study_preparations/scenario_formal_v1_20261116_r2/LOCK.json; exact registration,design and source snapshot adjacent. Lock ID eb5b35d6f58193969a45216669c0aa5d25425794134a12da7b7fc766c732d716. Initial unexecuted lock folder without_r2 is retained as a precollection development snapshot; final guard audit added cross-output campaign uniqueness and strengthened completion-binding checks, so its old source bindings no longer match and it cannot execute with current tooling. No data or API requests existed in either formal lock at this entry. New tools scenario_formal.py and scenario_formal_analysis.py preserve old frozen transport files via a bounded single-process verifier adapter;15 offline tests passed, including deterministic full blocks, analysis signs, source/registration drift, synthetic stop/missing rows, explicit opt-in and cross-output duplicate dispatch prevention. Synthetic fixtures are not formal observations.

Current state: formal registration complete,collection0,0 new API/Unity calls this step. Existing208 P029 replies,174 physical development runs and original production SHA1466241a451c2d176f942ec8ebe26452a9df7e1a1be440d841f4b8cf83e2c59a unchanged. Freeze/verify never reads credentials or dispatches. This entry does not represent automatic collection start. Documentation: research/scenario_decisions_v2/FORMAL_DESIGN.zh-TW.md and STAGE6_STATUS.json.

'''
    log=root/'experiment_records/EXPERIMENT_LOG.md'
    with (root/'experiment_records/.notebook.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:
            text=log.read_text(encoding='utf-8');marker='<!-- AUTO-RECORDED RUNS -->';assert marker in text and '## P-030 —' not in text
            tail=text.split(marker,1)[1];text=text.replace(marker,entry+marker,1);assert text.split(marker,1)[1]==tail
            tmp=log.with_suffix('.p030.tmp');tmp.write_text(text,encoding='utf-8');os.replace(tmp,log)
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    files=[p/'FORMAL_DESIGN.zh-TW.md',p/'STAGE6_STATUS.json',root/'tools/scenario_formal.py',root/'tools/scenario_formal_analysis.py',root/'tools/test_scenario_formal.py',Path(__file__)]
    files += [x for x in folder.rglob('*') if x.is_file()]
    receipt={'schema':'scenario-formal-design-delivery-v1','status':status,'files':[{'path':str(x.relative_to(root)).replace('\\','/'),'sha256':c.sha(x.read_bytes())} for x in files]}
    c.write_new(p/'STAGE6_DESIGN_RECEIPT.json',receipt)
    for item in receipt['files']:assert c.sha((root/item['path']).read_bytes())==item['sha256']
    print(json.dumps(status,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
