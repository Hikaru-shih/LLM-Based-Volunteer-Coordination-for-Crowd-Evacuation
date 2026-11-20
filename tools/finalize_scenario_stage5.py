"""Publish complete pilot evidence and English research record; no extra API calls."""
import json,hashlib,os,msvcrt,collections
from pathlib import Path
import scenario_agent_contract as c
from closed_loop_study import source_sha

def main():
    root=c.ROOT;p=c.DESIGN;analysis=root/'experiment_records/data/analysis/scenario_pilot_v1_20261116'
    raw=root/'experiment_records/data/scenario_pilot_v1_20261116';reg=root/'experiment_records/study_preparations/scenario_pilot_v1_20261116'
    summary=c.read(analysis/'summary.json');assert summary['trials']==208 and summary['invalid']==0
    assert source_sha()=='1466241a451c2d176f942ec8ebe26452a9df7e1a1be440d841f4b8cf83e2c59a'
    assert c.sha((root/'experiment_records/data/formal_summary/group_v2/COMPLETE.json').read_bytes())=='c28c59e67ba21092cb72fa4888f8eb79bd5d40e48c9310900a4f8607b40d8d6c'
    groups=summary['groups'];abstract=[];physical=[]
    for cell in sorted({x['scenario'] for x in groups if x['phase']=='abstract_choice'}):
        g={x['information']:x for x in groups if x['scenario']==cell}
        abstract.append(f"| {cell} | {g['numeric']['participate']}/5 | {g['contextual_equivalent']['participate']}/5 | {g['numeric']['referenceProbability']*100:.2f}% |")
    for cell in sorted({x['scenario'] for x in groups if x['phase']=='physical_choice'}):
        g={x['information']:x for x in groups if x['scenario']==cell}
        physical.append(f"| {cell} | {g['geometry_only']['participate']}/5 | {g['calibrated_forecast']['participate']}/5 |")
    totals={}
    for phase in ('abstract_choice','physical_choice'):
        rows=[x for x in summary['reasonGroups'] if x['phase']==phase];counts=collections.Counter()
        for x in rows:counts.update(x['labelCounts'])
        totals[phase]=dict(counts)
    report='''# 新版情境小型先導結果

2026年11月16日。P-029已完成208次真實API選擇與全量理由覆核。這是新設計的開發先導，不是舊P-028的補跑，也不是正式優劣排名。最清楚的發現是：在這批設定中，LLM並非只能選協助；但資訊不足時仍高度傾向協助，提供個人撤離時間估計後，其選擇明顯隨情境改變。

## 收集與有效性

| 階段 | 規劃 | 完成 | 用途 |
|---|---:|---:|---|
| 抽象效用診斷 | 36 | 36 | 已知他人聯合機率的效用比較 |
| 物理時間診斷 | 32 | 32 | 指定他人背景下的時間表比較 |
| 抽象自由選擇 | 60 | 60 | 六格成本比例及尺度、兩種措辭 |
| 物理自由選擇 | 80 | 80 | 八格布局與處理時間、兩種資訊 |

208個不同provider response ID、208次HTTP嘗試、0重試、0技術無效。未新增Unity模擬。原始回覆有119,752個prompt tokens及12,544個completion tokens，合計132,296。這是供應端回報用量，不直接當成美元費用。

抽象診斷32個非平手動作全部正確，4筆平手正確陳述報酬相等；物理診斷32筆動作與指定平均時間比較全部正確。68筆理由均經助理全字閱讀、比較及算術覆核後才放行自由選擇。這是窄範圍理解gate，不證明一般推理能力或全部自由理由正確。

## 抽象效用仍高度協助

自由選擇56/60協助，即93.33%。數值措辭28/30、情境等價措辭28/30，整體相同不表示兩種措辭已證明等效。四次拒絕全出現在成本損失比β=.9，較低兩個β全協助。每格每措辭只有5次，不能把這個模式當穩定比例或已證明的交互作用。

| 效用設定 | 數值措辭協助數 | 情境措辭協助數 | 原公式參與機率 |
|---|---:|---:|---:|
'''+ '\n'.join(abstract)+'''

A30/A70分別是無人協助損失av=.3/.7；R10/R50/R90是β=.1/.5/.9，cv=av×β。原公式在同β的兩尺度給相同機率，LLM這次高β觀測數不同，但不足以證明尺度反應穩定。LLM得到原基礎報酬與X/τ/ω，沒有被要求解原調整行為公式；不能把觀測差異稱為偏離全域最優或人類理性。

## 時間資訊改變了物理情境的選擇

只給布局時40/40協助；加入開發時間預測時13/40協助，即32.5%，並有27次拒絕。這是同一模型在本提示及資訊條件中的輸出差異，不是40個真人，也不是已觀測到新撤離速度改善。

| 物理情境 | 只有布局的協助數 | 提供時間預測的協助數 |
|---|---:|---:|
'''+ '\n'.join(physical)+'''

預測組B2、B3 M1、B4全部拒絕；B5兩種處理時間皆協助。B3 M4同時有3次協助、2次拒絕：這個條件中，自己的較佳選擇會隨其他人的意願背景改變，回覆對兩種端點的取捨不同。沒有提供端點機率，不能替這五筆指定唯一正確期望效用答案。

預測來自先前六個開發種子的條件平均及觀察範圍，不是當輪未來。提供時間表同時改變可用資訊量及提示內容；不能把選擇改變直接解釋成更像人類、純推理能力提升或獨立於資訊的心理效應。原公式也不能直接套到這個不同報酬任務，所以物理層與原模型抽象比較分開報告。

## 理由的發現與問題

抽象自由理由主要陳述自己的協助成本與無人協助損失；60/60標出個人效益比較，58/60提及無人協助後果，57/60承認未知選擇或結果限制。四次拒絕較強調避免參與成本，以及可能由其他人協助。這些是陳述內容，不等於已識別內部風險偏好或利他人格。

物理預測組40/40理由都引用提供的預測，且著重自己的撤離時間；只有布局組40/40仍協助，很多文字強調未提供足夠個人成本或未來時間。依事前手冊，當中11筆只陳述預設願意、沒有拒絕理由或模擬器不保證結果，未提出具體支持取捨，標為insufficient_reason。這是助理的編碼判斷，未經獨立第二位真人覆核。

品質問題全部保留：

- 1筆明確報酬條件誤讀：AC_A70_R10_contextual_equivalent_r002把「自己是唯一不協助者」說成會損失.7；此時其實已有其他人協助，原報酬應為1。原始協助動作未修改。
- 1筆比較語意註記：PC_B2_M1_calibrated_forecast_r002提到跨兩個假設端點的平均，但沒有說明權重。拒絕在兩端點均有較低自己的均值，選擇本身不依賴平均；仍不能把該句視為已知機率下的期望效用計算。
- 1筆資訊適用註記：PC_B5_M4_geometry_only_r002在τ=0情境提到部分阻塞仍可撤離的通則，未明確說本情境也能通行，故保留可能條件混用的unclear註記，而非直接斷言捏造出口。

208筆均已覆核；未見明確主張相反最終動作的理由。11筆理由支持關係仍不清楚，不能把「沒有明確矛盾」當成理由全部充分或正確。多標籤可重疊，品質欄位亦可能重疊，不能把各數量直接相加當不同失敗人數。沒有真人一致性或kappa，也沒有使用另一個付費LLM替本批自動分類。

## 這批先導支持什麼

它支持繼續研究「資訊條件下的協助決策差異」：近乎全協助不一定是動作被系統固定，也可能與缺少可用個人代價資訊的任務表達有關。已知機率診斷與物理時間表條件中，模型確實能拒絕。但這不能單獨確定舊99.61%協助率的成因，因為新舊版本、任務與資訊不同，並非單因素重跑。

正式設計可優先保留原效用層的成本比例比較，以及物理層的資訊條件與端點取捨；不要只挑會出現拒絕的格子。原模型仍在其合法且相同報酬層比較，時間資訊擴充另報。先決定正式問題、樣本精度及理由覆核安排，再事前登錄。現在未自動啟動第6步正式收集。

## 限制與證據

每個自由條件只有5次，屬可行性與變異先導，無確認性p值或等效主張。相同模型的新請求不是不同人類；模型別名相同也不保證後端完全不變。所有條件與負面理由皆保留，不追加到顯著、不修復回覆、不把本批併入未來正式樣本。完整編碼、原文與例子規則均可追溯。

事前計畫位於experiment_records/study_preparations/scenario_pilot_v1_20261116/plan.json；原始四階段在experiment_records/data/scenario_pilot_v1_20261116。分析位於experiment_records/data/analysis/scenario_pilot_v1_20261116，包含TRIAL_CATALOG.csv、choice-summary.csv、reason-coding.csv、summary.json、SOURCE_MANIFEST.json及COMPLETE.json。英文研究筆記記錄P-029與各階段開始、完成及本次V-042總結。
'''
    (p/'PILOT_RESULTS.zh-TW.md').write_text(report,encoding='utf-8')
    english='''# P029 small scenario pilot results

Completed208 live choices:36 abstract diagnostics,32 physical diagnostics,60 abstract free choices and80 physical free choices.208 unique provider response IDs,208 recorded HTTP attempts,0 retries,0 technical invalids,0 new Unity runs. All208 reasons were assistant-reviewed with source-bound coding. Pilot data remain separate from P028 and future formal data.

All32 non-tie abstract actions and32 physical comparison actions were correct;4 abstract ties correctly stated equality. Full68-reason gate review preceded free choices. This is a narrow comprehension check, not general capability or human validation.

Abstract free choices:56/60 participate. All4 declines occur at cost/loss ratio.9; the two wording conditions each28/30, which does not prove equivalence. Each free condition has only5 repetitions. Reference probabilities are theoretical adjusted-law values, not global optima or a full expected-utility specification for the LLM.

Physical free choices: geometry-only40/40 participate; calibrated forecasts13/40 participate. Forecast B2(M1/M4),B3M1,B4(M1/M4) all decline; B5M1/M4 all participate; B3M4 has3 participate and2 decline. Endpoint beliefs are unspecified, so the mixed-profile task has no unique expected-utility answer. Forecasts are earlier six-seed development summaries, not observed future outcomes. The information conditions differ in available information and text; no human similarity, independent reasoning gain or new group evacuation benefit is established.

Quality:1 definite payoff-condition misreading in abstract free choice;1 ambiguous endpoint-average phrase;1 possible partial-blockage-rule applicability ambiguity;11 geometry-only reasons coded insufficient with unclear action support. No explicit opposite-final-action contradiction observed. All remain in data. Assistant coding is not independent human reliability or classifier accuracy. No second paid model graded reasons. Token usage:119752 input,12544 output,total132296 as reported by provider; no dollar-cost claim.

The prospective208-request ceiling and all conditions were retained. No outcome-based expansion, reply repair or formal pooling occurred. Next: freeze a focused formal design and sampling rationale, preserving original-utility versus physical-time task boundaries. Formal collection has not started. See summary.json and the complete raw/source manifests for audit evidence.
'''
    (analysis/'RESULTS.md').write_text(english,encoding='utf-8')
    status={'date':'2026-11-16','stage5':'small_pilot_complete_reviewed','registration':'P-029','liveChoices':208,'actualHTTPAttempts':208,'retries':0,'technicalInvalids':0,'newUnityRuns':0,
        'abstractDiagnostics':36,'physicalDiagnostics':32,'abstractFreeParticipate':56,'abstractFreeN':60,'physicalGeometryParticipate':40,'physicalGeometryN':40,'physicalForecastParticipate':13,'physicalForecastN':40,
        'reasonReviewCount':208,'independentHumanReview':False,'formalStudyStarted':False,'report':'PILOT_RESULTS.zh-TW.md','analysis':'experiment_records/data/analysis/scenario_pilot_v1_20261116','next':'Stage6: prospectively specify focused formal questions, sample rationale and coding plan; do not automatically dispatch.'}
    (p/'STAGE5_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    workflow=c.read(p/'WORKFLOW_STATUS.json');workflow.update(currentMilestone='stage5_complete_next_formal_design',newLLMCalls=208,currentReport='PILOT_RESULTS.zh-TW.md');workflow['stages']['5']='P029 pilot208 choices complete and fully reason-reviewed';workflow['stages']['6']='not started; formal design and prospective registration required'
    (p/'WORKFLOW_STATUS.json').write_text(json.dumps(workflow,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for target,link in [(p/'README.zh-TW.md','PILOT_RESULTS.zh-TW.md'),(root/'README.md','research/scenario_decisions_v2/PILOT_RESULTS.zh-TW.md')]:
        text=target.read_text(encoding='utf-8');pointer=f'> **新版小型先導完成（P-029）**：[208次選擇與理由分析]({link})。抽象效用56/60協助；物理布局40/40、提供時間預測13/40協助。各自由條件僅5次，不當正式結論；沒有自動開始正式實驗。\n\n'
        if '新版小型先導完成（P-029）' not in text:target.write_text(text.replace('\n\n','\n\n'+pointer,1),encoding='utf-8')
    entry='''## V-042 — Complete P029 pilot collection and full reason review (2026-11-16, Asia/Taipei)

Completed the prospectively registered208-choice ceiling exactly:36 abstract diagnostics,32 physical diagnostics,60 abstract free choices,80 physical free choices.208 unique provider IDs across phases,208 HTTP attempts,0 retries,0 technical invalids,0 new Unity runs. Sources, exact phase matrices/order, original response hashes and complete reason coverage audited. Provider usage119752 prompt tokens+12544 completion tokens=132296; no dollar claim. Model alias gpt-6-luna with the frozen profile succeeded, not proof of an immutable backend. P028 remains sealed and separate.

All32 non-tie abstract actions and32 physical mean-time comparison actions correct;4 abstract ties correctly stated equality. Assistant full-text review of all68 diagnostic reasons completed and qualified matching live gates before free collection. All208 explanations later fully coded; no second paid classifier or independent human reviewer. The explicit packet-hash-bound judgment applicator is tools/apply_scenario_reason_judgments.py; it applies authored judgments and exact evidence, never infers semantics or repairs actions. Gate metadata remain historical; campaign receipt records completed reason review.

Abstract free:56/60 participate (numeric28/30,contextual28/30); all4 declines at ratio.9. Six numerical cells remain in the paper domain, with adjusted reference probabilities reported separately from model utility beliefs. Physical free:geometry-only40/40 participate,forecast13/40; B2/B3M1/B4 forecast conditions all decline,B5 both work intervals all participate,B3M4 has3/5 participate. Prior six-seed forecasts are information treatments, not the present decision's future or new physical outcome evidence. No claim that a single mechanism explains old99.61%, that LLM is humanlike, or that the physical task shares the reference payoff assumptions.

Reason findings:abstract reasons mainly compare own cost and no-helper loss; forecast reasons use own time conditional on other-willingness endpoints. Quality flags retained:1 definite payoff-condition error(only non-volunteer incorrectly said to incur failure loss),1 unclear endpoint-average phrase,1 possible partial-blockage-rule applicability ambiguity,11 insufficient geometry-only reasons with unclear action support. No explicit opposite-final-action conflict observed; this is not comprehensive factual certification. Full labels and opposing/ambiguous cases retained; no sample expansion, selection of refusing conditions, repair or pooling.

Artifacts: raw experiment_records/data/scenario_pilot_v1_20261116; source plan under study_preparations/scenario_pilot_v1_20261116; analysis data/analysis/scenario_pilot_v1_20261116/{TRIAL_CATALOG.csv,choice-summary.csv,reason-coding.csv,summary.json,SOURCE_MANIFEST.json,COMPLETE.json,RESULTS.md}; Chinese report research/scenario_decisions_v2/PILOT_RESULTS.zh-TW.md. Each free condition n5, purely developmental/descriptive; no confirmatory p-values/equivalence or human independence. Next is focused formal design and prospective sample/coding lock, not automatic formal dispatch. Stage5 complete,stage6 unstarted.

'''
    log=root/'experiment_records/EXPERIMENT_LOG.md'
    with (root/'experiment_records/.notebook.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:
            text=log.read_text(encoding='utf-8');marker='<!-- AUTO-RECORDED RUNS -->';assert marker in text and '## V-042 —' not in text
            tail=text.split(marker,1)[1];text=text.replace(marker,entry+marker,1);assert text.split(marker,1)[1]==tail
            temp=log.with_suffix('.v042.tmp');temp.write_text(text,encoding='utf-8');os.replace(temp,log)
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    for item in c.read(analysis/'SOURCE_MANIFEST.json'):assert c.sha((root/item['path']).read_bytes())==item['sha256']
    files=[p/'PILOT_RESULTS.zh-TW.md',p/'STAGE5_STATUS.json',root/'tools/register_scenario_stage5.py',root/'tools/apply_scenario_reason_judgments.py',root/'tools/analyze_scenario_stage5.py',Path(__file__)]
    files += [f for f in analysis.rglob('*') if f.is_file()]
    receipt={'schema':'scenario-stage5-delivery-v1','status':status,'files':[{'path':str(f.relative_to(root)).replace('\\','/'),'sha256':c.sha(f.read_bytes())} for f in files]}
    c.write_new(p/'STAGE5_RECEIPT.json',receipt)
    for item in receipt['files']:assert c.sha((root/item['path']).read_bytes())==item['sha256']
    print(json.dumps(status,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
