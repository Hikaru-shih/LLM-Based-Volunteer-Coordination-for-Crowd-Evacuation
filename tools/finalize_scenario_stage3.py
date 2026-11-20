"""Record stage3 delivery and hash its local evidence; no provider calls."""
import json,hashlib,os,msvcrt
from pathlib import Path
from closed_loop_study import ROOT,source_sha
import scenario_agent_contract as c

p=ROOT/'research/scenario_decisions_v2'
bundle=ROOT/'experiment_records/data/preparation/scenario_agent_stage3_20261116'
validation=ROOT/'experiment_records/data/validation/scenario_agent_stage3_20261116'
assert c.verify(bundle)['passed']
proof=c.read(validation/'VALIDATION.json');assert proof['passed'] and proof['newAPICalls']==0
source=source_sha();assert source=='1466241a451c2d176f942ec8ebe26452a9df7e1a1be440d841f4b8cf83e2c59a'
status={'date':'2026-11-16','stage3':'decision_interface_and_transport_implemented_and_offline_verified','newAPICalls':0,'newUnityRuns':0,
    'newTestsPassed':27,'legacyRegressionTestsPassed':11,'persistentSyntheticRoundtrip':16,'syntheticStopFixture':1,
    'contractSpecimens':62,'notPilotSamples':True,'model':c.MODEL,'liveProviderSupportVerified':False,'liveSemanticGatesPassed':False,
    'livePilotStarted':False,'formalStudyRegistered':False,'productionSourceSHA':source,
    'report':'STAGE3_INTERFACE.zh-TW.md','interfaceBundle':str(bundle.relative_to(ROOT)).replace('\\','/'),
    'next':'Align stage4 reason coding across both tasks, lock stage5 sampling/registrations, then execute actual semantic gates before free choice.',
    'unityLiveSceneReplaced':False,'scope':'Individual decision layer and CLI; physical extension remains separate from original reference utility.'}
(p/'STAGE3_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
readme=p/'README.zh-TW.md';text=readme.read_text(encoding='utf-8')
pointer='> **第3步已完成**：[兩層決策介面、API工具與驗證](STAGE3_INTERFACE.zh-TW.md)。27項新檢查＋11項舊回歸通過；尚未呼叫LLM或開始先導。第2步與原156筆匯出是歷史設計紀錄，現行狀態以[第3步狀態](STAGE3_STATUS.json)為準。\n\n'
if 'STAGE3_INTERFACE.zh-TW.md' not in text:text=text.replace('\n\n','\n\n'+pointer,1)
readme.write_text(text,encoding='utf-8')
rootreadme=ROOT/'README.md';text=rootreadme.read_text(encoding='utf-8')
pointer='> **新版情境決策介面完成（2026-11-16）**：[第3步工具、提示與驗證](research/scenario_decisions_v2/STAGE3_INTERFACE.zh-TW.md)。抽象報酬與物理預測分開；實際先導尚未開始。\n\n'
if 'STAGE3_INTERFACE.zh-TW.md' not in text:rootreadme.write_text(text.replace('\n\n','\n\n'+pointer,1),encoding='utf-8')
entry='''## V-040 — Complete two-layer decision interface and explicit transport (2026-11-16, Asia/Taipei)

Purpose: complete step3 against stage2 without collecting pilot behavior. New code: tools/scenario_agent_contract.py, scenario_agent_transport.py, test_scenario_agent_interface.py and validate_scenario_stage3_pipeline.py. Abstract utility uses6 legal cells and two equivalent wordings. Physical extension uses8 layouts/work intervals with geometry-only versus calibrated-forecast information; calibrated tables recompute focal and other-nine capped-time means and observed ranges from6 earlier development seeds, not this decision's future. Two extreme other-willingness profiles are not a complete mixed-profile model or probability. No utility-proxy substitution into the reference formula, no human-validity or optimality claim.

Prepared62 interface specimens:18 abstract diagnostic,16 physical diagnostic,12 abstract choice,16 physical choice. These are payload contracts, not collected responses or a registered sample-size plan. Abstract diagnostic has8 participate optima,8 decline optima,2 ties before repetition. Physical diagnostic checks supplied mean-own-time comparisons only. Free prompts contain no diagnostic q, expected action or reference probability. Existing156-choice exports remain historical, unexecuted and separate.

Transport preserves previous model/profile and response-v3 without enum. Supports prospective exact-payload phase registration, explicit live flag, fresh contexts, durable pre-dispatch claim, fixed endpoint, one attempt, no retries/refill/resume/model substitution, raw HTTP body and request IDs, strict schema/model/action parsing, duplicate-ID rejection, error preservation, typed own-willingness adapter and unreviewed reason templates. Exception details and authorization are not logged; an echoed credential would be redacted and invalidated. Key is only read during explicit live dispatch. Live campaigns automatically append English notebook start/completion/stop events; a crash with only a claim remains an unknown dispatch, not an invitation to resend. No Unity live-scene policy was replaced.

Free phases require matching live semantic-gate evidence and all reason reviews, revalidated from exact raw content/action/hashes. Physical choice additionally requires physical diagnostic. A completed network batch, a pass flag, synthetic fixtures or a blank reason sheet cannot qualify. Provider availability/profile compatibility is NOT live verified. Official OpenAI structured-output, chat-completion and error documentation was checked, without inferring alias availability or current account pricing. Request/output/time ceilings are not a dollar-cost guarantee.

Validation:27 new tests plus11 legacy exporter regressions passed. Persistent synthetic roundtrip has16 fixtures (8 participate,8 decline) plus1 single-attempt synthetic429 stop;0 actual HTTP calls,0 Unity runs,0 key reads. Synthetic raw envelopes are clearly labeled synthetic_test and cannot qualify as live. Artifacts are data/preparation/scenario_agent_stage3_20261116 and data/validation/scenario_agent_stage3_20261116; reports/status in research/scenario_decisions_v2/STAGE3_INTERFACE.zh-TW.md and STAGE3_STATUS.json. Original production SHA remains1466241a451c2d176f942ec8ebe26452a9df7e1a1be440d841f4b8cf83e2c59a; P-028 and stage2 raw calibration unmodified. Next: align reason coding and prospectively lock actual pilot sampling, then run live gates, not automatic free-choice collection.

'''
log=ROOT/'experiment_records/EXPERIMENT_LOG.md'
with (ROOT/'experiment_records/.notebook.lock').open('a+b') as gate:
    gate.seek(0);msvcrt.locking(gate.fileno(),msvcrt.LK_NBLCK,1)
    try:
        text=log.read_text(encoding='utf-8');marker='<!-- AUTO-RECORDED RUNS -->';assert marker in text
        if '## V-040 —' not in text:
            tail=text.split(marker,1)[1];text=text.replace(marker,entry+marker,1);assert text.split(marker,1)[1]==tail
            temp=log.with_suffix('.stage3.tmp');temp.write_text(text,encoding='utf-8');os.replace(temp,log)
    finally:gate.seek(0);msvcrt.locking(gate.fileno(),msvcrt.LK_UNLCK,1)
def item(f):return {'path':str(f.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
files=[*c.source_paths(),ROOT/'tools/test_scenario_agent_interface.py',ROOT/'tools/validate_scenario_stage3_pipeline.py',Path(__file__),p/'STAGE3_INTERFACE.zh-TW.md',p/'STAGE3_STATUS.json']
files += [f for folder in [bundle,validation] for f in folder.rglob('*') if f.is_file()]
receipt={'schema':'scenario-stage3-delivery-v1','status':status,'files':[item(f) for f in files],'priorStudyCompletionSHA256':hashlib.sha256((ROOT/'experiment_records/data/formal_summary/group_v2/COMPLETE.json').read_bytes()).hexdigest()}
target=p/'STAGE3_RECEIPT.json';assert not target.exists(),'Preserve prior delivery receipt'
target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for x in receipt['files']:assert hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()==x['sha256']
print(json.dumps(status,ensure_ascii=False,indent=2))
