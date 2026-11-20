"""Record the locked new study before dispatch, without exposing credentials."""
from pathlib import Path
import json,os,msvcrt
import information_control_experiment as e
R=e.R;e.verify()
entry='''## V-059 — Locked information-control follow-up (2026-11-20, Asia/Taipei)

Purpose: address the forecast information/length/detail confound and test fixed action-presentation order using the user's configured paid OpenAI API, without changing model or pooling with P030. The user explicitly requested completion including collection. Prospectively locked P031_INFORMATION_CONTROL_20261120 after observing P030: eight settings x three information conditions x two option orders x ten complete scheduling blocks = 480 fresh requests, ten per full factorial cell. Conditions are geometry-only, unrelated administrative catalogue control, and the original forecast package. Both action enumerations are counterbalanced; all remaining role/schema/model settings are held fixed. Original participate-first geometry/forecast payloads match P030.

Matching: all eight control/forecast pairs have equal o200k_base proxy user-message token counts in both orders; numeric literal counts are 41 in each full user message. Character length is about 7% longer and lexical word count about 8% longer in the control, inside frozen tolerances. The proxy is not independently established as the provider's tokenizer; returned actual prompt-token usage will be audited. Neutral catalogue entries use arbitrary administrative labels/decimal strings, not source outcome values, personal effects, risks or promises. One control topic and remaining semantic/attention differences remain limitations. No claim that length matching isolates all possible causes or that a null contrast proves equivalence.

Analysis locked before collection: primary forecast-minus-control and forecast-minus-geometry willingness; secondary control-minus-geometry, order effects and order interaction. Planned B2-B4/B5 summaries retained. Whole-block descriptive bootstrap, 5000 resamples of ten complete blocks, seed 2026112002; pointwise percentile intervals, no p-values, equivalence, independent-person or broad-model generalization claims. Retain every technically valid free choice and reason. No new reason coding or Unity simulations. Seven offline tests passed for original prompt preservation, counterbalance, matching, cell balance, irrelevant control content and strict envelope/model/action parsing. Prior semantic gates are context only, not fresh validation of the new stimulus.

Execution policy: requested gpt-6-luna, temperature0.15, reasoning none, output220 tokens; https://api.openai.com/v1/chat/completions. One sequential worker, one attempt, 60-second timeout, 480 requests and 105600 generated-token ceiling, wall limit10800 seconds. First technical, model-identity, duplicate-ID, network or unknown-result failure stops the batch; preserve partial records, no retries/refill/restart. No fallback to free or different models. Costs remain provider-side. Package dependencies were installed only in private ignored workspace build folders for tokenizer matching and scientific plotting; no system runtime changes.

Design and sources: experiment_records/study_preparations/information_control_v1_20261120/{design.json,registration.json,PROMPT_MATCH_AUDIT.json,SEAL.json}. Intended run: experiment_records/data/information_control_v1_20261120/. Intended analysis: experiment_records/data/analysis/information_control_v1_20261120/. Source seal binds the collection, tests, analysis and historical prompt snapshot. This preparation itself made zero model calls. Existing P030 and current report files remain unchanged at this stage.

'''
with (R/'experiment_records/.notebook.lock').open('a+b') as f:
    f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    try:
        p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-059 ' not in s
        t=p.with_suffix('.control-plan.tmp');t.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8');os.replace(t,p)
    finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
p=R/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';x=e.read(p);x.update(date='2026-11-20',currentMilestone='information_control_followup_locked_before_collection',supplementaryExperiment='user_authorized_480_request_information_control_followup',followupCampaign=e.CAMPAIGN,followupDesign=str((e.PRE/'design.json').relative_to(R)).replace('\\','/'),followupExpectedChoices=480,followupCompletedChoices=0,next='Execute the locked new independent batch; stop on first technical failure without retry or substitution, then analyse complete data separately from P030.')
p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Recorded prospective plan, seven offline checks, matching limits and 480-request execution scope.')
