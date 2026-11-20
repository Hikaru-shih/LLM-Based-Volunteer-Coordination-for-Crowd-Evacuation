"""Publish original assistant judgments as an explicitly non-human demonstration."""
from pathlib import Path
import json,html,hashlib,msvcrt,os
R=Path(__file__).resolve().parents[1];H=R/'report/human_review'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
packet=read(H/'sample.public.json')['items'];translations=read(H/'translations.zh-TW.json')['items']
key={x['id']:x for x in read(R/'local_archive/20261119_review_key/baseline.json')['records']}
original={x['trialID']:x for x in read(R/'experiment_records/data/scenario_formal_v1_20261116/coding.json')['records']}
names={'insufficient_reason':'理由不足','actionReasonRelation':'行動與理由關係','comparisonJudgment':'比較判斷','unsupportedInformation':'未提供資訊','arithmeticJudgment':'算術判斷'}
values={'yes':'是：理由不足','no':'否：有支持選擇的考量','consistent':'一致','conflict':'衝突','unclear':'無法明確判斷','correct':'正確','incorrect':'錯誤','not_applicable':'不適用','none':'沒有','present':'有'}
items=[];cards=[];e=html.escape
for p in packet:
    k=key[p['id']];o=original[k['trialID']];assert p['explanation']==o['reasonText'] and k['rawSHA256']==o['rawSHA256']
    quotes=list(dict.fromkeys(span['quote'] for span in o['evidenceSpans']))
    row={'id':p['id'],'caseID':p['caseID'],'trialID':k['trialID'],'reviewerType':'assistant','ratings':k['assistant'],'evidenceQuotes':quotes,'note':o['note'],'uncertaintyNote':o['uncertaintyNote']}
    items.append(row)
    tr=''.join(f'<tr><th>{e(names[f])}</th><td>{e(values[v])} <small>({e(v)})</small></td></tr>' for f,v in row['ratings'].items())
    cards.append(f'''<article><h2>{p['id']} · {e(p['caseID'])}</h2><p class="tag">AI 原有編碼示範 · 非人工評分</p><details><summary>中文情境</summary><pre>{e(translations[p['id']]['prompt'])}</pre></details><p><b>模型選擇：</b>{'參與協助' if p['decision']=='participate' else '拒絕協助'}</p><p><b>模型理由中文翻譯</b></p><blockquote>{e(translations[p['id']]['explanation'])}</blockquote><p><b>模型理由英文原文</b></p><blockquote>{e(p['explanation'])}</blockquote><table>{tr}</table><details><summary>既有 AI 編碼備註與原文證據（英文原始紀錄）</summary><p>{e(o['note'])}</p><p>{e(o['uncertaintyNote'])}</p><ul>{''.join('<li>'+e(q)+'</li>' for q in quotes)}</ul></details></article>''')
demo={'schema':'assistant-quality-demonstration-48-v1','reviewerType':'assistant','humanCompleted':False,'source':'Previously recorded assistant judgments; not new human observations or independent validation','items':items}
write(H/'AI_Example_48.json',demo)
page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>AI 填寫示範 · 48 則</title><style>body{font:17px/1.65 system-ui;max-width:1000px;margin:30px auto;padding:0 20px;color:#192b35}header{background:#f1f4f6;padding:24px}article{padding:24px;margin:24px 0;border:1px solid #bac6ce}h1{font-size:26px}h2{font-size:22px}table{border-collapse:collapse;width:100%;margin:16px 0}td,th{border:1px solid #c3cdd4;text-align:left;padding:10px}th{width:35%}pre{white-space:pre-wrap;font:15px/1.6 system-ui;background:#f5f7f8;padding:14px}small{color:#53616b}.tag{color:#73551c}blockquote{margin:12px 0;padding:14px;background:#f5f7f8}</style><header><h1>AI 填寫示範 · 48 則</h1><p>這份完整表單列出先前 AI 的既有編碼，不是你或其他人完成的評分，也不代表唯一正確答案。它不會修改原表單、勾選狀態或瀏覽器儲存。</p><p>中文為閱讀翻譯，英文原文與既有編碼備註保留。看過這份後再評原表，請在「以前看過 AI 評分？」選「看過或可能看過」。如逐則審查後接受，可記為作者核對 AI 編碼；不應當作獨立盲評一致率。</p><p><a href="AI_Example_48.json" download>下載 AI 示範資料 JSON</a> · <a href="Review.html">回到你的空白／續填表單</a></p></header>'''+''.join(cards)+'</html>'
assert page.count('<article>')==48 and page.count('<tr>')==240
(H/'AI_Example.html').write_text(page,encoding='utf-8')
status=read(H/'REVIEW_STATUS.json');status.update(assistantExampleAvailable=True,assistantExamplePath='AI_Example.html',note='Original rating packet still hides labels, but the user requested separate visible assistant examples. Do not assume label-naive review. Human completion is not inferred.');write(H/'REVIEW_STATUS.json',status)
p=R/'report/README.md';s=p.read_text(encoding='utf-8');s+='\n## Assistant-filled demonstration\n\nAt the user\'s request, human_review/AI_Example.html and AI_Example_48.json expose the existing assistant judgments for all 48 sampled responses. These are explicitly non-human demonstrations. They do not modify the blank form or local browser storage. Subsequent author review must disclose prior AI-label access; it is not automatically independent blind review. Human completion remains pending. The demonstration uses a distinct schema rejected by the human-rating scorer.\n';p.write_text(s,encoding='utf-8')
p=R/'report/PACKAGE_COMPLETE.json';receipt=read(p);receipt['humanReview']['assistantExampleAvailable']=True;receipt['files']=[{'path':x.relative_to(R/'report').as_posix(),'sha256':sha(x)} for x in sorted((R/'report').rglob('*')) if x.is_file() and '.build' not in x.parts and x!=p and not x.name.startswith('~$')];write(p,receipt)
entry='''## V-055 — Explicit assistant-filled 48-item example (2026-11-19, Asia/Taipei)

Purpose: provide the completed example requested by the user without misrepresenting assistant coding as human ratings. AI_Example.html shows all 48 prior assistant judgments in Chinese option labels with original explanation text, reading translations and the original coding notes/evidence. AI_Example_48.json has a distinct assistant-only schema and humanCompleted=false. The human scorer rejects that schema. Sample text and raw hashes were matched against the original coding records; 48 cards and 240 judgments were checked.

The blank review form and browser storage were not changed. The assistant key is now available in a separate example, so later review must disclose prior access and must not automatically be called independent blinded review. No actual human completion is inferred, no agreement statistic is calculated and the report's pending-human-review status is unchanged. No API calls or Unity runs. Original data and report contents unchanged.

'''
with (R/'experiment_records/.notebook.lock').open('a+b') as f:
    f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    try:
        p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-055 ' not in s
        t=p.with_suffix('.example.tmp');t.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8');os.replace(t,p)
    finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
print('Created 48-item assistant-only example. Human ratings unchanged.')
