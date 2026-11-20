"""Publish reason-analysis delivery and append its English notebook record; no API."""
from pathlib import Path
import hashlib,json,msvcrt,os
import scenario_agent_contract as c
import scenario_reason_coding as s
from closed_loop_study import source_sha

p=c.DESIGN;validation=c.ROOT/'experiment_records/data/validation/scenario_reason_stage4_20261116'
proof=c.read(validation/'VALIDATION.json');assert proof['passed'] and proof['newAPICalls']==0 and proof['execution']=='synthetic_test'
source=source_sha();assert source=='1466241a451c2d176f942ec8ebe26452a9df7e1a1be440d841f4b8cf83e2c59a'
assert c.verify(c.ROOT/'experiment_records/data/preparation/scenario_agent_stage3_20261116')['passed']
status={'date':'2026-11-16','stage4':'two_layer_reason_codebook_and_audit_tools_complete','codebookVersion':'scenario-reasons-v3',
    'labels':12,'newTestsPassed':25,'stage3RegressionTestsPassed':27,'legacyRegressionTestsPassed':11,
    'syntheticWorkedRows':16,'realNewLLMReasonsAnalyzed':0,'newAPICalls':0,'newUnityRuns':0,
    'independentHumanReview':False,'semanticClassifierAccuracyEstablished':False,
    'report':'STAGE4_REASON_ANALYSIS.zh-TW.md','codebook':'REASON_CODEBOOK_V3.zh-TW.md',
    'next':'Stage5: prospectively lock small-pilot sampling and exact registrations; collect real diagnostic replies, review reasons, then permit free-choice phases.'}
(p/'STAGE4_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
workflow={'date':'2026-11-16','currentMilestone':'stage4_complete_next_stage5','stages':{'1':'reference boundaries documented','2':'physical characterization and scoring specification complete; paper utility-to-time not established','3':'two-layer individual interface and explicit transport implemented; live support not verified','4':'versioned reason coding, evidence validation and summaries complete','5':'not started; prospective pilot sampling and registrations required','6':'not started'},'newLLMCalls':0,'developmentPhysicalRuns':174,'humanValidation':False,'currentReport':'STAGE4_REASON_ANALYSIS.zh-TW.md'}
(p/'WORKFLOW_STATUS.json').write_text(json.dumps(workflow,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name,link in [('README.zh-TW.md','STAGE4_REASON_ANALYSIS.zh-TW.md'),('REASON_CODEBOOK.zh-TW.md','REASON_CODEBOOK_V3.zh-TW.md')]:
    file=p/name;text=file.read_text(encoding='utf-8')
    pointer=f'> **第4步更新**：[雙層理由分析與工具]({link})已完成，25項新檢查及38項回歸通過。尚未取得新LLM理由；現行流程見[狀態檔](WORKFLOW_STATUS.json)。\n\n'
    if '第4步更新' not in text:file.write_text(text.replace('\n\n','\n\n'+pointer,1),encoding='utf-8')
readme=c.ROOT/'README.md';text=readme.read_text(encoding='utf-8')
pointer='> **新版理由分析完成（2026-11-16）**：[第4步手冊、證據編碼與摘要工具](research/scenario_decisions_v2/STAGE4_REASON_ANALYSIS.zh-TW.md)已完成。下一步為小型先導規劃與登錄，尚未新增LLM呼叫。\n\n'
if 'STAGE4_REASON_ANALYSIS.zh-TW.md' not in text:readme.write_text(text.replace('\n\n','\n\n'+pointer,1),encoding='utf-8')
entry='''## V-041 — Two-layer reason analysis and provenance-bound coding (2026-11-16, Asia/Taipei)

Purpose: complete stage4 before collecting new model behavior. Published scenario-reasons-v3 with12 multi-label categories, including supplied-forecast use, uncertainty awareness and scale/normalization. The legacy personal_cost label explicitly includes personal payoff/earlier-escape comparisons. Four quality dimensions keep action/reason relation, comparison correctness, unsupported information and arithmetic separate. Free choices with unknown beliefs are not given a unique expected-utility correctness grade. Teaching examples are hand-authored, not provider or human observations.

Implemented tools/scenario_reason_coding.py: reconstruct every registered row from raw responses and durable claims; preserve unknown, missing, invalid and duplicate records; retain readable diagnostic-wrong-action reasons as semantic_failure. Labels require exact raw Unicode-codepoint quote spans, named reviewer/type and notes. No raw action/reason repairs, guessed reasons, keyword classifier or second-LLM classification. Unclear judgments require notes; arithmetic/comparison errors require evidence. Codebook/source/raw tampering fails validation. Source-text provenance checks do not establish label semantic accuracy.

Summaries stratify phase/scenario/information, display planned/record classes/readable/reviewed/unreviewed counts, and use reviewed eligible reasons as the explicit label-rate denominator. Zero-review rates are null, not0%. collectionComplete and coding coverage are separate; no eligible reasons does not count as full coverage. Multi-label proportions need not sum100%. Examples follow first-ID positive/label-absent rules, not editorial selection; absence does not imply an opposite motive. Gate-review exports only fully reviewed diagnostics and cannot qualify synthetic data as live. Stage3 transport and its source-bound interface remain unchanged and verified.

Validation:25 new coding tests plus27 stage3 and11 legacy regressions passed. The persistent16-row worked coding example reuses stage3 synthetic placeholder sentences, all explicitly non-substantive and coded insufficient_reason with unclear action/reason relation. This demonstrates bookkeeping and evidence binding only, not an empirical LLM reason distribution, independent human reliability, hidden reasoning or classifier accuracy. No new API calls, key reads or Unity simulations. Original production remains1466241a451c2d176f942ec8ebe26452a9df7e1a1be440d841f4b8cf83e2c59a; prior raw/formal evidence unchanged.

Artifacts: research/scenario_decisions_v2/{REASON_CODEBOOK_V3.zh-TW.md,reason-codebook.v3.json,REASON_CODING_EXAMPLES.en.md,STAGE4_REASON_ANALYSIS.zh-TW.md,STAGE4_STATUS.json,WORKFLOW_STATUS.json}; validation under experiment_records/data/validation/scenario_reason_stage4_20261116. Next stage5 still requires prospective small-pilot sampling, exact registrations and real semantic gates with reason review before free choices. A codebook revision after pilot must be versioned and affected records recoded; this delivery is not formal-study registration.

'''
log=c.ROOT/'experiment_records/EXPERIMENT_LOG.md'
with (c.ROOT/'experiment_records/.notebook.lock').open('a+b') as lock:
    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    try:
        text=log.read_text(encoding='utf-8');marker='<!-- AUTO-RECORDED RUNS -->';assert marker in text
        if '## V-041 —' not in text:
            tail=text.split(marker,1)[1];text=text.replace(marker,entry+marker,1);assert text.split(marker,1)[1]==tail
            tmp=log.with_suffix('.stage4.tmp');tmp.write_text(text,encoding='utf-8');os.replace(tmp,log)
    finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
files=[s.CODEBOOK,p/'REASON_CODEBOOK_V3.zh-TW.md',p/'REASON_CODING_EXAMPLES.en.md',p/'STAGE4_REASON_ANALYSIS.zh-TW.md',p/'STAGE4_STATUS.json',p/'WORKFLOW_STATUS.json',
       c.ROOT/'tools/scenario_reason_coding.py',c.ROOT/'tools/test_scenario_reason_coding.py',c.ROOT/'tools/validate_scenario_reason_workflow.py',Path(__file__)]
files += [f for f in validation.rglob('*') if f.is_file()]
receipt={'schema':'scenario-stage4-delivery-v1','status':status,'files':[{'path':str(f.relative_to(c.ROOT)).replace('\\','/'),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in files],
    'stage3ReceiptSHA256':hashlib.sha256((p/'STAGE3_RECEIPT.json').read_bytes()).hexdigest()}
c.write_new(p/'STAGE4_RECEIPT.json',receipt)
for item in receipt['files']:assert hashlib.sha256((c.ROOT/item['path']).read_bytes()).hexdigest()==item['sha256']
print(json.dumps(status,ensure_ascii=False,indent=2))
