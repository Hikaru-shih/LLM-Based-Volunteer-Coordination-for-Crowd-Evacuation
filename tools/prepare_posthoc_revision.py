"""Existing-data analysis and blinded quality-review packet. Never dispatches API calls."""
import csv,hashlib,json,random,html,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1]
RUN=R/'experiment_records/data/scenario_formal_v1_20261116'
A=R/'experiment_records/data/analysis/posthoc_utility_20261119'
H=R/'report/human_review';A.mkdir(parents=True,exist_ok=True);H.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reg=read(RUN/'registration.snapshot.json');coded=read(RUN/'coding.json')['records'];byid={r['trialID']:r for r in coded}
cases={t['case']['caseID']:t['case'] for t in reg['trials']}
assert len(coded)==840 and len(cases)==28
rows=[]
for case in sorted(cases.values(),key=lambda c:c['caseID']):
    if case['information']!='calibrated_forecast':continue
    fs=json.loads(case['payload']['messages'][1]['content'].split('Forecasts:\n',1)[1])
    diffs=[];rec={'scenario':case['scenario']}
    for bg in ('others_decline','others_willing'):
        pp=next(f for f in fs if f['otherProfile']==bg and f['ownChoice']=='participate')['ownCappedExitSteps']['mean']
        dd=next(f for f in fs if f['otherProfile']==bg and f['ownChoice']=='decline_assistance')['ownCappedExitSteps']['mean']
        gain=dd-pp;diffs.append(gain)
        rec[bg+'_time_gain']=gain;rec[bg+'_utility_gain']=gain/301
    a,b=diffs
    rec['endpoint_class']='participate_both' if min(a,b)>0 else 'decline_both' if max(a,b)<0 else 'background_dependent'
    rec['q_star']=(-b/(a-b)) if a*b<0 else None
    rec['participate_if']='all q in [0,1]' if min(a,b)>0 else 'no q in [0,1]' if max(a,b)<0 else ('q < q_star' if a<b else 'q > q_star')
    rr=[r for r in coded if r['scenario']==case['scenario'] and r['information']=='calibrated_forecast']
    assert len(rr)==30
    rec['forecast_participate']=sum(r['rawAction']=='participate' for r in rr);rec['forecast_n']=30
    rec['agree_others_decline']=sum((r['rawAction']=='participate')==(a>0) for r in rr)
    rec['agree_others_willing']=sum((r['rawAction']=='participate')==(b>0) for r in rr)
    rows.append(rec)
with (A/'endpoint_utility.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary={'status':'post_hoc_exploratory_existing_data','date':'2026-11-19','q_definition':'Probability of all-other-nine-decline, assuming only the two supplied endpoint backgrounds exist. Not the original payoff-task q over arbitrary profiles.','sourceMeans':'Exact six-decimal means shown in the locked prompts; not new simulation estimates.','formula':'DeltaU(q)=[q*(Tdecline_D-Tparticipate_D)+(1-q)*(Tdecline_W-Tparticipate_W)]/301','scope':'Conditional mean comparison, not per-seed dominance, known beliefs, validated optimality or evidence about uncalibrated mixed willingness profiles. No p-values.','rows':rows,'agreementAllDecline':sum(r['agree_others_decline'] for r in rows),'agreementAllWilling':sum(r['agree_others_willing'] for r in rows),'n':240,'sources':{'registration.snapshot.json':sha(RUN/'registration.snapshot.json'),'coding.json':sha(RUN/'coding.json')},'newAPICalls':0,'newUnityRuns':0}
write(A/'ANALYSIS.json',summary)
lines=['# Exploratory endpoint utility analysis','',summary['formula'],'','Positive differences favour participating. q is an assumed probability over ONLY the two supplied endpoint backgrounds, not a measured belief. Mixed profiles remain uncalibrated. Prompt-rounded means are used. This is post hoc and separate from the registered primary contrasts.','', '| Setting | Time gain: all decline | Time gain: all willing | Endpoint class | q threshold | Forecast participate |','|---|---:|---:|---|---:|---:|']
for r in rows:lines.append(f"| {r['scenario']} | {r['others_decline_time_gain']:.3f} | {r['others_willing_time_gain']:.3f} | {r['endpoint_class']} | {r['q_star'] if r['q_star'] is not None else 'none'} | {r['forecast_participate']}/30 |")
lines+=['',f"Agreement if all others decline: {summary['agreementAllDecline']}/240. If all others are willing: {summary['agreementAllWilling']}/240. These endpoint-specific counts must not be pooled as one accuracy score.",'','B2_M1 and B4_M1 favour declining at both supplied mean endpoints, whereas B5_M1 and B5_M4 favour participating at both. The remaining four settings reverse preference across endpoints. Small differences such as 0.5 ticks do not establish robust superiority; forecasts come from only six development seeds.','']
(A/'ANALYSIS.en.md').write_text('\n'.join(lines),encoding='utf-8')
# Select 48 without inspecting AI quality labels: 16 payoff, 16 geometry, 16 forecast.
rng=random.Random(2026111901);selected=[]
for info in ('numeric','contextual_equivalent','geometry_only','calibrated_forecast'):
    groups={}
    for t in reg['trials']:
        if t['case']['information']==info:groups.setdefault(t['case']['caseID'],[]).append(t)
    take=2 if info in ('geometry_only','calibrated_forecast') else 1
    chosen=[]
    for key in sorted(groups):chosen+=rng.sample(groups[key],take)
    if info in ('numeric','contextual_equivalent'):
        remain=[t for g in groups.values() for t in g if t not in chosen];chosen+=rng.sample(remain,2)
    selected+=chosen
assert len(selected)==48 and len({t['trialID'] for t in selected})==48
rng.shuffle(selected)
fields={'insufficient_reason':['yes','no','unclear'],'actionReasonRelation':['consistent','conflict','unclear'],'comparisonJudgment':['correct','incorrect','not_applicable','unclear'],'unsupportedInformation':['none','present','unclear'],'arithmeticJudgment':['correct','incorrect','not_applicable','unclear']}
packet=[];baseline=[]
for i,t in enumerate(selected,1):
    c=t['case'];r=byid[t['trialID']];rid=f'H{i:02d}'
    packet.append({'id':rid,'caseID':c['caseID'],'decision':r['rawAction'],'explanation':r['reasonText'],'messages':c['payload']['messages']})
    baseline.append({'id':rid,'trialID':t['trialID'],'rawSHA256':r['rawSHA256'],'assistant':{k:('yes' if 'insufficient_reason' in r['labels'] else 'no') if k=='insufficient_reason' else r[k] for k in fields}})
private=R/'local_archive/20261119_review_key';private.mkdir(parents=True,exist_ok=True)
write(private/'baseline.json',{'sampleSeed':2026111901,'selection':'16 payoff (one per cell plus four extras); two per physical information cell; labels not used to select','records':baseline})
write(H/'sample.public.json',{'schema':'human-quality-review-48-v1','fields':fields,'items':packet})
guide='''# 人工評分填寫說明

請用瀏覽器開啟 Review.html。共 48 則：16 則報酬任務、16 則僅幾何資訊、16 則附時間預測。這是「理由品質核對」，不是評 LLM 是否善良、是否應該協助，也不是重新選擇行動。

1. 填寫你的姓名或穩定代號、與研究的關係，以及過去是否看過 AI 評分。已接觸過的情況如實揭露，不影響填寫。
2. 每題先展開並讀完完整原始 prompt，再讀原始 decision 與 explanation。只依提供資訊評分，不要猜模型內心。
3. 填完五個欄位，從原 explanation 複製一段原文作為證據，再用自己的話說明原因。不能用 AI 代評；有疑義選 unclear 並寫原因。
4. 頁面會嘗試在本機瀏覽器保存，但不能保證換瀏覽器或換路徑後仍在。請定期按「下載目前評分」另存 JSON；之後可匯入繼續。
5. 全部完成後下載 JSON，告訴我存在哪個位置即可。我再計算人類與既有 AI 的逐欄一致率、Cohen's kappa 和混淆表。填寫前不提供 AI 標籤。不要打開 local_archive 裡的答案基準。

## 五個欄位

- 理由不足 insufficient_reason：yes＝只有宣告願意／不願意、重述規則、說資訊不足，沒有指出支持其選擇的考量；no＝至少一個可辨認、支持選擇的考量；unclear＝難以判定。理由有錯不一定等於「沒有理由」，可同時在其他欄標錯。
- 行動理由關係 actionReasonRelation：consistent＝所述考量支持最後行動；conflict＝理由明確主張相反行動；unclear＝沒有清楚連結或有多種解讀。
- 比較 comparisonJudgment：correct／incorrect＝涉及效用、時間、背景比較且可判定正誤；not_applicable＝沒有比較；unclear＝有比較但權重或解讀無法判定。未給背景機率時，把兩個端點平均當作已知期望值不能直接判 correct。
- 未提供資訊 unsupportedInformation：none＝沒有斷言未給資訊；present＝把未提供的承諾、傷害、出口或成功保證當成事實；unclear＝語意難定。明確表達假設或不確定不自動算 present。
- 算術 arithmeticJudgment：correct／incorrect＝有可核對計算；not_applicable＝沒有計算；unclear＝有計算意涵但無法判定。單純比較誰較快只評比較欄，未必是算術。

這份評分聚焦五項理由品質，不是全部 12 個理由主題標籤的人工驗證。抽樣刻意平衡任務，不能把 48 則總一致率當成全部 840 則的代表性正確率。若你是專題作者，會記為作者人工核對，不宣稱外部獨立評審。舊的 AI 示範不算人工評分。尚未填完前，報告不會宣稱已通過人工驗證。
'''
(H/'START_HERE.zh-TW.md').write_text(guide,encoding='utf-8')
template='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>人工理由品質評分</title><style>body{max-width:1000px;margin:30px auto;padding:0 20px;font:17px/1.65 system-ui;color:#182631}header{background:#edf2f5;padding:20px;position:sticky;top:0;z-index:2}article{border:1px solid #b9c7d0;padding:24px;margin:24px 0}pre{white-space:pre-wrap;background:#f5f7f8;padding:16px;font:14px/1.5 monospace}label{display:inline-block;margin:6px 14px 6px 0}textarea{display:block;width:96%;min-height:70px}button{padding:10px;margin:8px}input[type=text]{width:250px}fieldset{margin:12px 0}h1{font-size:24px}</style><header><h1>人工理由品質評分 · 48 則</h1><div>先讀同資料夾 START_HERE.zh-TW.md。AI 標籤已隱藏；請自行判斷。</div><label>評分者 <input id="reviewer" type="text"></label><label>身分 <select id="role"><option value="">請選擇</option><option value="author">專題作者</option><option value="classmate">同學</option><option value="other">其他人工評分者</option></select></label><label>以前看過 AI 評分？ <select id="exposure"><option value="">請選擇</option><option value="yes">看過或可能看過</option><option value="no">沒有</option></select></label><div id="progress"></div><button id="save">下載目前評分 JSON</button><label>匯入續填 <input id="load" type="file" accept=".json"></label></header><main id="items"></main><script>
const data=__DATA__, fields=__FIELDS__, names={insufficient_reason:'理由不足',actionReasonRelation:'行動與理由關係',comparisonJudgment:'比較判斷',unsupportedInformation:'未提供資訊',arithmeticJudgment:'算術判斷'};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state={schema:'human-quality-review-48-v1',reviewer:'',role:'',exposure:'',items:data.map(x=>({id:x.id,caseID:x.caseID,ratings:{},quote:'',note:''}))};
try{let s=localStorage.getItem('human-review-20261119-v1');if(s)state=JSON.parse(s)}catch(e){}
function persist(){try{localStorage.setItem('human-review-20261119-v1',JSON.stringify(state))}catch(e){} let n=state.items.filter(x=>Object.keys(fields).every(k=>fields[k].includes(x.ratings[k]))&&x.quote.trim()&&x.note.trim()).length;document.getElementById('progress').textContent=`完成 ${n}/48 題（五欄＋原文證據＋說明）`;}
function render(){for(const k of ['reviewer','role','exposure']){document.getElementById(k).value=state[k]||'';document.getElementById(k).onchange=e=>{state[k]=e.target.value;persist()}}document.getElementById('items').innerHTML=data.map((x,i)=>`<article><h2>${x.id} · ${esc(x.caseID)}</h2><details><summary>完整原始 prompt（請展開閱讀）</summary>${x.messages.map(m=>`<h3>${esc(m.role)}</h3><pre>${esc(m.content)}</pre>`).join('')}</details><p><strong>Decision:</strong> ${esc(x.decision)}</p><blockquote>${esc(x.explanation)}</blockquote>${Object.entries(fields).map(([k,vs])=>`<fieldset><legend>${names[k]}</legend>${vs.map(v=>`<label><input type="radio" name="${x.id}_${k}" value="${v}" data-i="${i}" data-k="${k}" ${state.items[i].ratings[k]===v?'checked':''}>${v}</label>`).join('')}</fieldset>`).join('')}<label>原 explanation 的證據片段（直接複製）</label><textarea data-i="${i}" data-text="quote">${esc(state.items[i].quote)}</textarea><label>你的評分理由／疑義（中文可）</label><textarea data-i="${i}" data-text="note">${esc(state.items[i].note)}</textarea></article>`).join('');document.querySelectorAll('[data-k]').forEach(e=>e.onchange=()=>{state.items[e.dataset.i].ratings[e.dataset.k]=e.value;persist()});document.querySelectorAll('[data-text]').forEach(e=>e.oninput=()=>{state.items[e.dataset.i][e.dataset.text]=e.value;persist()});persist()}
document.getElementById('save').onclick=()=>{let blob=new Blob([JSON.stringify({...state,exportedAt:new Date().toISOString()},null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='Human_Review_48.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
document.getElementById('load').onchange=async e=>{try{let s=JSON.parse(await e.target.files[0].text());if(s.schema!==state.schema||s.items.length!==48||s.items.some((x,i)=>x.id!==data[i].id||x.caseID!==data[i].caseID))throw Error('不是同一份評分表');state=s;render()}catch(err){alert('無法匯入：'+err.message)}};render();
</script></html>'''
(H/'Review.html').write_text(template.replace('__DATA__',json.dumps(packet,ensure_ascii=False).replace('</','<\\/')).replace('__FIELDS__',json.dumps(fields)),encoding='utf-8')
write(H/'REVIEW_STATUS.json',{'status':'awaiting_actual_human_ratings','planned':48,'completed':0,'seed':2026111901,'humanValidation':False,'aiLabelsHiddenInPacket':True,'fiveQualityFieldsOnly':True,'sampleSHA256':sha(H/'sample.public.json')})
print(json.dumps({'reviewRows':48,'analysis':str(A),'endpointAgreement':[summary['agreementAllDecline'],summary['agreementAllWilling']]}))
