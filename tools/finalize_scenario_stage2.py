"""Publish scenario specification from audited zero-API calibration, with bounded claims."""
from pathlib import Path
import json,csv,statistics,hashlib,msvcrt,os,shutil
from closed_loop_study import ROOT,source_sha
r=ROOT;p=r/'research/scenario_decisions_v2';a=r/'experiment_records/data/analysis/scenario_physical_v2_20261116_final'
def read(f):return json.loads(f.read_text(encoding='utf-8-sig'))
def rows(f):return list(csv.DictReader(f.open(encoding='utf-8-sig',newline='')))
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def mean(xs):return statistics.mean(list(xs))
result=read(a/'results.json');assert result['runs']==174 and result['apiCalls']==0 and result['invalid']==0
assert source_sha()==result['baseSourceSHA']
runs=rows(a/'runs.csv');agents=rows(a/'agent-costs.csv');contrasts=rows(a/'own-action-counterfactuals.csv')
lookup={(int(x['seed']),int(x['blocked']),x['policy'],int(x['manipulationSteps'])):x for x in runs}
cells=[];table=[];payoffs=[]
for b in [2,3,4,5]:
    for m in [1,4]:
        cc=[x for x in contrasts if int(x['blocked'])==b and int(x['manipulationSteps'])==m and x['others']=='others_willing']
        focal=next(x for x in result['summaries'] if x['blocked']==b and x['policy']=='Focal0' and x['manipulationSteps']==m)
        controlled=next(x for x in result['summaries'] if x['blocked']==b and x['policy']=='AllHelp' and x['manipulationSteps']==m)
        cell={'id':f'B{b}_M{m}','initialExitNonBlockage':1-b/5,'manipulationStepsPerWorkUnit':m,'population':10,'totalMovableObstacles':5,'seeds':6,'meaning':('Fully blocked relevant exit' if b==5 else 'Partial exit blockage with remaining routes in this layout')+f'; {m} progress ticks per manipulation unit, without extra injury assumptions','focalWhenOthersDecline':{'meanAssignedBurdenTicks':focal['meanBurden'],'meanApproachTicks':focal['meanApproach'],'meanHandlerTicks':focal['meanHandling'],'meanOwnDelay':focal['meanFocalDelay'],'meanOthersBenefit':focal['meanOthersBenefit']},'ownActionWhenOthersWilling':{'meanOwnDelay':mean(float(x['focalDelay']) for x in cc),'meanOthersBenefit':mean(float(x['othersBenefit']) for x in cc),'sacrificePublicBenefitSeeds':sum(x['personalSacrificePublicBenefit']=='True' for x in cc)},'referenceProxyMappingEligible':focal['paperDomainEligible'],'referenceProxyCV':focal['timeProxyCV'],'referenceProxyAV':focal['timeProxyAV'],'usedAsPaperUtility':False,'use':'Physical extension candidate, fully-blocked case also a necessary-removal control' if b==5 else 'Physical extension candidate; keep negative-benefit outcomes'}
        cells.append(cell)
        table.append(f"| B{b} M{m} | {1-b/5:.1f} | {focal['meanApproach']:.2f} | {focal['meanHandling']:.2f} | {focal['meanFocalDelay']:+.2f} | {cell['ownActionWhenOthersWilling']['meanOwnDelay']:+.2f} | {cell['ownActionWhenOthersWilling']['meanOthersBenefit']:+.2f} |")
        for context,cp,dp in [('others_decline','Focal0','None'),('others_willing','AllHelp','OthersHelp')]:
            values={}
            for action,policy in [('participate',cp),('decline_assistance',dp)]:
                selected=[lookup[(s,b,policy,1 if policy=='None' else m)] for s in range(71001,71007)]
                steps=mean(float(x['focalExit']) for x in selected)
                values[action]={'meanCappedOwnExitStep':steps,'normalizedTimeUtility':1-steps/301,'formula':'1 - min(T,300)/301','sourceJobs':[x['job'] for x in selected]}
                payoffs.append({'scenario':cell['id'],'otherProfile':context,'ownAction':action,'meanCappedOwnExitStep':steps,'normalizedTimeUtility':1-steps/301,'seeds':6})
            cell.setdefault('empiricalConditionalPayoffs',{})[context]=values
with (p/'physical-scenario-payoffs.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(payoffs[0]));w.writeheader();w.writerows(payoffs)
spec={'schema':'scenario-stage2-specification-v1','date':'2026-11-16','status':'physical_characterization_and_scoring_rules_complete','originalPaperUtilityCalibrationEstablished':False,'humanValidityEstablished':False,'timeUnit':'simulation ticks; no human seconds conversion','normalization':{'H':300,'scale':301,'utility':'1 - min(T,H)/(H+1)','why':'Keeps capped utilities positive; arbitrary transparent common affine scale, no reward for participation','limitations':'Censoring and task burden are not the same as additive Eq20 cost. No mortality or physiological interpretation.'},'cells':cells,'pilotExecutionHold':True,'holdReason':'Earlier 156-choice exporter remains an abstract-utility diagnostic candidate, not these eight empirical physical scenarios. Exact prompt/protocol and registered sampling must be aligned at step3.','data':'experiment_records/data/analysis/scenario_physical_v2_20261116_final/results.json','sampling':'Development-only six seed blocks; all geometries/costs retained, no selection of favorable seeds','oldSixUtilityCells':'Retained as numerical cost-ratio/scale diagnostic, not validated physical time mapping'}
(p/'stage2-scenario-specification.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
doc='''# 情境與分數設定完成說明

2026年11月16日。第2步已完成物理特性檢查、情境表與計分規則；這不等於已證實八個情境都能套用原公式。最重要的定案是保留原模型效用與實際時間兩個層次，不偽造它們之間的一對一換算。下一步是第3步的介面整合與新登錄，暫不執行舊156次候選先導。

## 已完成的量測

使用隔離Unity實際跑174輪開發校準，人口固定10人、21×21格、總可移動障礙5個、H=300，種子71001–71006。包含6輪未阻塞基準、24輪各阻塞布局無人協助、48輪只固定ID0願意、48輪全員願意，以及48輪只有ID0拒絕。共168輪全員撤離、6輪有效逾時，技術無效0、API0。六個逾時均為完全阻塞且無人協助。這些是開發物理控制，不是新LLM或正式研究結果。

第一批66輪採原有B0/B2/B5幾何；看到邊界結果後，另登錄60輪B3/B4完整中間跨度，沒有挑選有利條件；再登錄48輪他人願意而自己拒絕的對照，分離他人意願背景。它們是順序開發，不是事先一次凍結的174輪確認性實驗。完整資料全部保留。

## 八個情境與可量測的代價

B是出口鄰近5個參考位置中被障礙占用的數目，不等於出口總數，也不等於房間總障礙數。B2、B3、B4仍可透過此格網的剩餘通路撤離；B5為完整阻塞。格網沿用原模型八鄰域，不能以看起來三個出口格前都有障礙就斷言無路可走。

M是每次搬運單位需累積的工作步數，測試1與4。M4表示同一動作需要較長準備與處理時間，不宣稱等於重量4倍、受傷機率4倍或四秒。位置與接近距離由布局及同種子初始狀態決定。

| 情境 | 初始τ | 接近步數 | 搬運步數 | 他人不幫時自己的延後 | 他人願意時自己的延後 | 他人願意時其他人受益 |
|---|---:|---:|---:|---:|---:|---:|
'''+ '\n'.join(table)+'''

前兩項工作量為固定ID0獨自願意時的6種子平均，包含無效移動及未成功接手前的接近時間，接近步數不等於路徑距離。自己的延後為同ID協助減拒絕的截尾撤離步數；正值表示較晚。其他人受益為其餘9人拒絕背景減協助背景的平均截尾步數；正值表示較快。每次比較固定他人意願，不固定後續路徑與所有亂數事件。

接近與搬運工作量是「投入」，不能當成「淨延後」。B5即使投入很多步，自己仍因通道打開而比無人協助快很多。也不能把全員願意下每人的平均投入當成單一實際搬運者的成本。

## 現實意義與限制

部分仍能通行的布局代表障礙干擾但不必處理才能離開；額外搬運可能得不償失。完整阻塞代表需要處理才可完成撤離，協助者自己也可能直接受益。M1與M4對應較短與較長的處理工作，但沒有時間壓力、火勢、傷害或真人體力資料，不能把這些危險加入故事。

在他人都願意的背景下，B4 M1平均出現自己延後約3.33步、其餘人平均快約1.61步。但只有2/6種子同時出現自己較晚與別人較快；B4 M4另有1/6。全部96個固定他人背景的自己動作對照，只有3個符合此符號條件。這些不是可挑出當代表的正式發現，亦不足以把整個環境稱為穩定的犧牲自己情境。其餘負效益與反例全部保留。

## 分數如何設定

原模型層保留Eq20的1−cv、1、1−av及0<cv<av<1，舊六格成本比例與尺度矩陣只用於抽象決策診斷，不再宣稱已對應六種實體障礙。當期望效用或參與機率比較沿用原論文時，不能偷偷改用物理時間報酬。

物理擴充層採自己的截尾撤離步數T作主要結果。若介面需要分數，使用共同尺度U=1−min(T,300)/301；越早撤離效用越高，協助動作本身不額外加分。301只為讓上限時的效用仍為正，沒有真實心理量尺意義。選擇不用分數而直接呈現估計步數，也具有同樣的排序。其他人的平均撤離時間另報，不把群體受益自動加成個人獎勵。

`physical-scenario-payoffs.csv`保留八格各四種條件結果：自己協助或拒絕，以及他人全不協助或全願意。這兩種他人背景只是明確控制端點，不代表所有可能混合選擇，也不等於至少一人協助。六種子平均是開發估計，不能當未來個案確定值或從同輪未來結果洩漏到LLM。

## 為何不能直接把時間換成原公式成本

校準前訂下的代理規則為cv_time=平均接近及搬運投入/301，av_time=max(0,無協助時相對開放基準的截尾延誤)/301。原始負延誤另保留，不因max操作消失。這只是明確的時間代理，並沒有識別出Eq20的心理效用。

B2至B4在此代理下全都無法滿足平均0<cv<av<1；B2的無協助相對開放基準平均差甚至略為負值，可能來自路徑與互動改變，不能把它修成預期正數。B5符合數值域，但τ=0讓原參與公式退化成p=1，而且av受300步截尾影響，不能解釋成完整的災害損失。即使數值合法，也不表示報酬假設已驗證。

原Eq20假設自己協助的效用不隨他人選擇改變、自己拒絕而有人協助可得同一基準報酬；實際時間會隨搬運分派、壅塞及其他人行動而變，所以通常不存在唯一的一組cv、av精確重現四個條件。不得把不合法數值裁切進研究域，亦不得把原模型與新時間任務的差異全歸因於LLM。

## 定案與下一步

八個物理情境全部保留為可追溯擴充候選。原六格保留為理論效用診斷，兩者的數據、任務與結論分開。這完成情境含義、可量測代價、分數規則及原模型適用範圍的設定；沒有宣稱完成真人效度或已建成理想的社會困境。

第3步應先將這個雙層規格接入候選提示與觀測，讓讀者分清抽象報酬及物理時間估計，處理開發估計的不確定性，再凍結新版先導。舊156筆離線匯出不直接代表八格物理情境，維持執行暫停。未新增LLM請求，亦不修改P-028。

## 資料與再現

原始資料為`experiment_records/data/scenario_physical_v2_20261116_r2`、`_r3`及`_r4`，各自包含執行前plan快照、幾何、逐步軌跡、決策、搬運事件及結果。完整分析在`experiment_records/data/analysis/scenario_physical_v2_20261116_final`，包括runs、agent-costs、paired-effects、own-action-counterfactuals與scenario-summary CSV。登錄與額外觀測程式快照保存於`experiment_records/study_preparations`的同名三資料夾。

原production C# SHA保持1466241a451c2d176f942ec8ebe26452a9df7e1a1be440d841f4b8cf83e2c59a。只在隔離專案新增接近分支的紀錄hook與決策控制callback；B3/B4也是隔離幾何擴充。原匯出config可能仍顯示建立manager時的OriginalGameTheory欄位，實際政策以physical-result.json及calibration_*來源為準，不可將這些列算成原模型或LLM的正式結果。工作與撤離結果已對照原始CSV核對。
'''
(p/'STAGE2_COMPLETE.zh-TW.md').write_text(doc,encoding='utf-8')
status={'date':'2026-11-16','stage2':'physical_characterization_and_scoring_specification_complete','paperUtilityToTimeValidated':False,'newLLMCalls':0,'developmentUnityRuns':174,'formalUnityRuns':0,'validTimeouts':6,'invalid':0,'stage3ExecutionHold':True,'reason':'Align abstract diagnostic and physical extension interfaces; old156-choice plan is not the calibrated physical task','report':'STAGE2_COMPLETE.zh-TW.md','specification':'stage2-scenario-specification.json','analysis':'experiment_records/data/analysis/scenario_physical_v2_20261116_final/results.json'}
(p/'STAGE2_STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
readme=p/'README.zh-TW.md';text=readme.read_text(encoding='utf-8')
pointer='> **第2步更新**：[物理校準與情境設定定案](STAGE2_COMPLETE.zh-TW.md)已完成，174輪零API。原六格不是已校準實體情境；舊156筆先導維持暫停，須先接入雙層規格。\n\n'
if 'STAGE2_COMPLETE.zh-TW.md' not in text:text=text.replace('\n\n','\n\n'+pointer,1)
readme.write_text(text,encoding='utf-8')
# Add visible supersession notices without altering old immutable exports or source receipts.
for name in ['MODEL_AND_SCENARIOS.zh-TW.md','PILOT_AND_GATES.zh-TW.md','OFFLINE_TOOLING.zh-TW.md']:
    f=p/name;t=f.read_text(encoding='utf-8')
    note='> 2026年11月16日後續更新：原六格為抽象效用候選，物理校準與適用界線以[第2步完成說明](STAGE2_COMPLETE.zh-TW.md)為準。此頁的舊先導不可直接啟動為八格物理實驗。\n\n'
    if '第2步完成說明' not in t:f.write_text(t.replace('\n\n','\n\n'+note,1),encoding='utf-8')
entry='''## V-039 — Stage 2 physical characterization and scoring specification (2026-11-16, Asia/Taipei)

Purpose: ground evacuation scenario meanings and personal costs before any new LLM pilot. Completed174 development Unity runs,1740 agent records,96 intervention-vs-none pairs and96 own-action contrasts over6 seed blocks71001–71006. Policies are deterministic None,Focal0,AllHelp,OthersHelp; no LLM, no key loading,0 API,0 mock decisions.168 full evacuations,6 valid H300 timeouts (B5 None),0 invalid simulated trials. All negative benefits and counterexamples retained. Data are separate from P-028 and are not new formal comparison data.

Sequential development registrations: r2=66 runs covering open/B2/B5; after inspecting these results, r3=60 runs systematically covers both intermediate B3/B4 layouts; r4=48 OthersHelp controls completes focal-action comparisons while holding others willing. Registrations and code snapshots precede their dispatches. This is adaptive development coverage, not a single prospectively locked confirmatory174-run cohort. Original production source remains1466241a451c2d176f942ec8ebe26452a9df7e1a1be440d841f4b8cf83e2c59a. Isolated code adds a pure approach event observer, controlled decision callback and B3/B4 geometry extension. Manager config may retain nominal OriginalGameTheory while actual decision source is calibration_POLICY: do not count these as reference or LLM results. Compiler/editor launch failures before execution are retained in tmp/scenario-physical-v2*.unity.log and the original registration; first hook referenced an Editor assembly from runtime, then corrected via a runtime observer. An extra launch before corrected preparation also compiled the old failing source; no simulations/API occurred in those attempts. A stale lock was removed only after launched processes had exited and exclusive access succeeded.

Measurements distinguish approach-assigned ticks (including blocked attempts), approach moves/distance, active-handler ticks (including work preparation), net same-ID capped exit differences and other-agent benefits. Focal0 vs None holds others declining; AllHelp vs OthersHelp holds others willing. Initial states match within contrasts; divergent trajectories do not imply all future random events align. All agents' exit records cross-check CSV; decisions, work IDs, sourceSHA, tau, total5 obstacles and zero API/mock counters were audited.

Findings: partial layouts often worsen with handling; full blockage benefits self and others and all no-help runs time out. Under others-willing B4/M1, mean focal delay+3.333 ticks and other-agent benefit+1.611 ticks, but joint positive signs only2/6 seeds; B4/M4 adds1/6. Only3/96 own-action pairs meet the sacrifice/public-benefit sign definition. No stable altruistic dilemma or human validity is established; no favorable seeds were selected.

Scoring specification: keep original Eq20 utility and six ratio/scale cells as abstract diagnostics. Physical extension keeps8 B2/B3/B4/B5 x M1/M4 scenarios with conditional own capped-time payoffs and optional affine U=1-min(T,300)/301. No participation bonus, no group-benefit reward, no seconds/injury conversion. Predeclared burden/301 and no-help-vs-open loss/301 proxies fail0<cv<av<1 for partial-layout averages; B5 proxies fit numeric domain but tau0 forces reference p1 and losses are horizon-censored. Do not clip proxies into a valid paper game or treat time as identified Eq20 psychological utility. All four conditional action/background outcomes retained.

Artifacts: research/scenario_decisions_v2/{STAGE2_COMPLETE.zh-TW.md,STAGE2_STATUS.json,stage2-scenario-specification.json,physical-scenario-payoffs.csv}; raw r2/r3/r4 under experiment_records/data/scenario_physical_v2_20261116_*; combined audit under data/analysis/scenario_physical_v2_20261116_final. Stage2 characterization and scoring-rule documentation complete; original utility-to-time validation is explicitly not established. Old156-choice offline export remains unexecuted and cannot be relabeled physical pilot. Next is step3 interface alignment and new prospective locking, not automatic live collection.

'''
log=r/'experiment_records/EXPERIMENT_LOG.md'
with (r/'experiment_records/.notebook.lock').open('a+b') as lock:
    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    try:
        t=log.read_text(encoding='utf-8');marker='<!-- AUTO-RECORDED RUNS -->';assert marker in t
        if '## V-039 —' not in t:
            tail=t.split(marker,1)[1];t=t.replace(marker,entry+marker,1);assert t.split(marker,1)[1]==tail
            tmp=log.with_suffix('.physical.tmp');tmp.write_text(t,encoding='utf-8');os.replace(tmp,log)
    finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
# Dedicated catalogue keeps calibration policy names and purpose distinct from prior formal runs.
catalog=a/'CALIBRATION_RUN_CATALOG.csv'
assert not catalog.exists()
with catalog.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['job','seed','blocked','policy','manipulationSteps','termination','purpose','phase','apiCalls']);w.writeheader()
    for row in runs:w.writerow({**{k:row[k] for k in ['job','seed','blocked','policy','manipulationSteps','termination']},'purpose':'Stage2 scenario interpretation and physical time-cost calibration','phase':'Development','apiCalls':0})
for rec in read(a/'source-manifest.json'):assert sha(r/rec['path'])==rec['sha256']
assert source_sha()==result['baseSourceSHA']
manifest={'date':'2026-11-16','stage':'2','status':status,'files':[{'path':str(f.relative_to(r)).replace('\\','/'),'sha256':sha(f)} for folder in [a] for f in sorted(folder.iterdir()) if f.is_file()],'specSHA256':sha(p/'stage2-scenario-specification.json'),'reportSHA256':sha(p/'STAGE2_COMPLETE.zh-TW.md')}
(p/'STAGE2_RECEIPT.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(status,ensure_ascii=False,indent=2))
