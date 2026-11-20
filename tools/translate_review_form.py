"""Add reading translations only; never fills or reveals quality ratings."""
import json,re,shutil,hashlib
from pathlib import Path
import scenario_agent_contract as c
R=Path(__file__).resolve().parents[1];H=R/'report/human_review'
old=H/'Review.html';archive=R/'local_archive/20261119_review_translation';archive.mkdir(parents=True,exist_ok=True)
if not (archive/'Review.en-content.html').exists():shutil.copyfile(old,archive/'Review.en-content.html')
data=json.loads((H/'sample.public.json').read_text(encoding='utf-8'))['items']
translations='''我願意協助搬移障礙物。在提供的預測中，當其他人拒絕協助時，參與與我大幅提早撤離有關；當其他人願意協助時，參與也與我稍微提早撤離有關。這些是估計，不是保證。
我願意協助處理可搬移障礙物。提供的資訊沒有個人風險或搬移時間的估計，因此我選擇參與，但不假設這會改善撤離時間。
我願意協助：參與成本為 0.27，而如果沒有人參與，拒絕協助的成本為 0.3。其他參與者的選擇未知。
我願意協助處理可搬移障礙物。出口部分受阻，但不搬移仍可撤離；僅靠作業間隔，無法確定整體負擔或對撤離時間的影響。
我願意參與，因為我的效用成本為 0.15，而如果沒有其他人參與，拒絕協助的成本為 0.3。其他參與者的選擇未知，因此我會協助，而不冒承受該結果的風險。
我願意協助處理可搬移障礙物。出口部分受阻，但不搬移仍可撤離；僅靠作業間隔，無法確定整體負擔或對撤離時間的影響。
我會拒絕協助。在其他人全部拒絕的預測中，若我拒絕，我的平均截尾離開時間低得多；雖然在其他人全部願意的預測中，參與與較低的平均時間有關，但那個假設端點不能確定其他人會怎麼做。這些是估計，不是保證。
我願意協助處理可搬移障礙物；提供的資訊沒有具體的搬移風險或個人成本，不過參與不保證能更快撤離。
我願意協助處理可搬移障礙物，同時了解模擬器會決定我是否被啟用，以及搬移是否影響撤離。
參與負擔為 0.03，而如果沒有其他人參與，拒絕協助的成本為 0.3。其他人的選擇未知，我願意協助，以避免障礙物無人自願處理。
我願意協助處理可搬移障礙物，同時了解參與不保證會被啟用、發生搬移或更快撤離。
我會拒絕協助，因為預測顯示，在兩種假設背景下，拒絕時我自己的平均截尾離開時間都較低。這些是六組種子的估計，不是保證。
我會拒絕協助，因為預測顯示，若其他人拒絕，我拒絕時自己的平均截尾離開步數較少；若其他人願意，平均值也稍低。這些是估計，不是保證。
參與的個人負擔為 0.27。如果有任何其他人參與，拒絕便可避免該負擔；若全部拒絕，則有 0.3 的損失。考量到其他行人的選擇未知，我願意協助。
我願意協助處理可搬移障礙物。提供的資訊沒有個人搬移風險或時間預測，因此我是在選擇協助意願，而不假設協助會加快撤離或我一定會被啟用。
我的參與成本為 0.63。只有在沒有其他人參與時，拒絕才有 0.7 的成本，否則沒有成本；其他人的選擇未知，我較傾向拒絕，而不承受參與成本。
參與的個人負擔為 0.35。如果有任何其他人參與，拒絕便可避免該負擔；若全部拒絕，則有 0.7 的損失。在其他人的選擇未知時，我願意協助。
我願意協助處理可搬移障礙物，同時了解模擬器會決定我是否被啟用，以及搬移是否影響撤離時間。
我選擇不搬移障礙物。在預測中，當其他人拒絕時，我拒絕與我大幅提早撤離有關；當其他人願意時，差異則微乎其微。預測只是有限的估計，而有意願不保證會實際搬移或更快撤離。
我願意協助處理可搬移障礙物。提供的資訊沒有具體的搬移負擔或預測延誤，我也了解有意願不保證會被啟用或更快撤離。
我會拒絕協助，因為預測顯示，在兩種假設背景下，拒絕時我自己的平均撤離時間都較低。這些是少量開發種子的估計，不是保證。
參與的個人負擔為 0.63。如果有任何其他人參與，拒絕便可避免該負擔；若全部拒絕，則有 0.7 的損失。其他人的選擇未知，我願意協助，以避免障礙物無人自願處理。
我會拒絕協助，因為預測顯示，若其他人也拒絕，我拒絕時自己的平均截尾離開時間較低；若其他人願意，則只有不大的差異。預測只是有限的估計，不是保證。
我會優先考慮自己的撤離時間。在預測中，其他人拒絕時，我拒絕對自己較快；其他人全部願意時，參與則稍快。他們實際的協助意願未知，因此若沒有清楚的個人時間效益，我較傾向不承擔搬移工作。
我願意協助處理可搬移障礙物。所述作業間隔短，而且沒有提供資訊顯示搬移會特別費力；我了解參與可能不會被啟用，也可能不會改善撤離時間。
我的參與成本為 0.07。如果沒有其他人參與，拒絕的成本為 0.7，因此我願意協助以降低該風險。
我願意協助處理可搬移障礙物。提供的資訊指出，部分受阻的布局仍容許不搬移就撤離，而僅靠作業間隔，無法確定搬移負擔或對撤離時間的影響。
參與的個人負擔為 0.15，而只有在沒有其他人參與時，拒絕才會有 0.3 的損失。我願意協助，而不冒讓障礙物無人自願處理的風險。
參與的個人負擔低（0.07），而障礙物無人自願處理會帶來大得多的損失（0.7）。我願意協助，儘管其他人的選擇未知。
我會拒絕協助，因為預測顯示，若其他人也拒絕，我拒絕會讓自己大幅提早撤離；若其他人願意，參與則只有小幅的估計改善。這些是不確定的估計，不是保證。
我願意協助搬移障礙物。出口部分受阻，搬移可能有用，儘管不搬移仍可撤離，而且不保證會更快。
我會拒絕協助，因為預測顯示，若其他人也拒絕，我拒絕會讓自己大幅提早撤離；若其他人願意，參與對自己的改善則很小。這些是六組種子的估計，不是保證，而且我不知道哪種背景適用。
我願意協助：參與成本為 0.15，而如果沒有人參與，拒絕可能造成 0.3 的損失。其他參與者的選擇未知。
參與的個人負擔為 0.35。只有在其他人也全部拒絕時，拒絕才有 0.7 的成本，而且其他參與者的選擇未知；我願意協助，而不冒讓障礙物無人自願處理的風險。
我願意協助處理可搬移障礙物；資訊中沒有會讓我拒絕的個人風險或時間預測。
我願意協助：所述參與效用成本為 0.35，而如果沒有人參與，拒絕會造成 0.7 的損失。其他參與者的選擇未知。
我會拒絕協助，因為預測顯示，若其他人也拒絕，我拒絕時自己的平均截尾離開時間較低；而全部願意的背景只是假設端點，不能據此假設其他人會搬移障礙物。
我會拒絕協助。在全部拒絕的預測中，若我拒絕，我自己的平均截尾離開時間低得多；雖然在全部願意的預測中，參與與較低的平均時間有關，但那個假設端點不能確定其他人會怎麼做。這些是估計，不是保證。
參與的個人負擔低（0.03），而障礙物無人自願處理會帶來較大的損失（0.3）。我願意協助，儘管其他人的選擇未知。
我願意協助處理可搬移障礙物。作業進度間隔有限，我接受協助可能不會被啟用，也可能不會改善撤離；不需要額外獎勵。
我願意協助搬移障礙物。在提供的端點預測中，當其他人拒絕時，參與與我較早撤離有關；但結果隨種子而異，並不保證有益處。
我願意協助處理可搬移障礙物。相關出口部分受阻，但不搬移仍可撤離，而且作業間隔有限；我沒有協助會改善自身撤離時間的預測。
我願意協助搬移障礙物。在兩種假設背景下，預測都顯示，若我參與，自己的截尾離開步數較少，儘管這些估計不是保證。
我的參與成本低（0.03），而沒有人參與時的損失較高（0.3）。我願意協助處理可搬移障礙物。
我願意協助搬移障礙物。在兩種假設端點背景下，預測都顯示，若我參與，自己的平均截尾離開步數較少，儘管這些估計有限，也不是保證。
我會拒絕協助，因為預測顯示，若其他人也拒絕，我拒絕會讓自己大幅提早撤離；若其他人全部願意，參與則只有小幅的估計個人時間優勢。這些是不確定的端點估計，不是保證。
我願意協助處理可搬移障礙物。提供的資訊沒有個人搬移風險細節或時間預測，因此我選擇參與，但不假設這會加快撤離。
我的參與成本為 0.63。只有在沒有其他人參與時，拒絕才有 0.7 的成本，而且其他參與者的選擇未知；我願意協助，而不冒承受該結果的風險。'''.splitlines()
assert len(translations)==48
common='''你只決定自己是否願意在模擬撤離期間協助搬移障礙物。可選「參與協助」（participate）或「拒絕協助」（decline_assistance），兩者都允許。你不能指派其他人，也不能控制移動。有意願不保證被啟用、發生搬移或撤離更快。不要虛構傷害、期限、其他出口或其他行人的承諾。你沒有個人歷史。請依提供資訊給簡短解釋；解釋是你陳述的考量，不是隱藏計算的紀錄。
只回傳含 explanation 與 decision 的 JSON 物件；decision 必須是 participate 或 decline_assistance。'''
abstract='''這項任務使用參考志願者賽局的標準化無單位效用，不是實測通行時間或金錢。基準效用為 1。參與的效用一律為 1-cv。拒絕時，若至少另一人參與，效用為 1；若其他人全部拒絕，則為 1-av。協助沒有額外獎勵。X 包含你自己。tau 是相關出口未受阻的比例。omega 是參考行為公式的獨立係數，不是受傷風險、人格或效用扣減。參考模型會在基本報酬表之外另行調整行為。不要重現其機率，也不要從 tau 或 omega 推算效用損失。'''
physical='''這是使用截尾撤離時間的延伸任務，不是參考賽局的報酬表或參與公式。共有 10 人、5 個可搬移障礙物。你是在固定網格布局系列中的焦點行人，編號 0。初始 tau 描述相關出口，不代表所有路徑。網格採八鄰居移動。這些布局部分受阻時，即使不搬移仍可撤離。M 是每一單位搬移工作的進度間隔，不是總搬移時間、重量、秒數或受傷風險。只有模擬器會啟用候選人並執行移動。
如需使用自身時間效用，其公式為 U=1-min(T,300)/301。越早撤離，效用越高。301 是共同的標準化數值，不是人類心理量尺。協助沒有額外獎勵。其他行人的時間結果分開列出，不會加成你自己的效用。搬移負擔與淨撤離延誤是不同量。'''
uncertainty='''以下預測來自先前六組開發種子的估計，不是本次決策的未來結果、真人量測或保證。平均值與觀察範圍描述六組種子的變異，不是信賴界限。到第 300 步仍未撤離者以 300 計算。兩種背景是假設端點：其餘九人全部拒絕，或其餘九人全部願意。有意願不等於實際搬移。混合背景尚未校準。不要把「其他人全部願意」當成「至少另一人願意」，不要推斷背景機率，也不要假設任何端點就是當前情況。'''
mapping={c.COMMON:common,c.ABSTRACT:abstract,c.PHYSICAL:physical,c.UNCERTAINTY:uncertainty,c.ABSTRACT_WORDING['numeric']:'cv 是你自己的效用成本；av 是沒有人參與時你的損失。',c.ABSTRACT_WORDING['contextual_equivalent']:'協助會帶來個人負擔 cv。障礙物無人自願處理會帶來損失 av。這些敘述沒有在相同報酬表之外增加物理效果。',"Other players' current choices and their probabilities are unknown. Choose for yourself under these rules.":'其他參與者目前的選擇及其機率未知。請依上述規則為自己選擇。',"Other pedestrians' willingness is unknown. Make your personal choice.":'其他行人的協助意願未知。請做自己的選擇。',' No numerical future-time forecasts are supplied. Do not invent them.':' 未提供數值形式的未來時間預測，不要自行捏造。','Observation:':'觀察資料：','Forecasts:':'預測資料：'}
obsnames={'nearbyAgentCount':'人數 X（包含自己）','exitNonBlockage':'相關出口未受阻比例 tau','unwillingness':'行為係數 omega（原欄位 unwillingness）','volunteerCost':'參與成本 cv','failureCost':'無人參與損失 av','initialExitNonBlockage':'初始相關出口未受阻比例 tau','population':'總人數','totalMovableObstacles':'可搬移障礙物總數','workProgressIntervalM':'每單位工作的進度間隔 M','horizon':'截尾上限（模擬步）','timeUnit':'時間單位'}
def translate_prompt(messages):
    s=messages[1]['content']
    for en,zh in mapping.items():s=s.replace(en,zh)
    lines=[]
    for line in s.splitlines():
        if line.startswith('{'):
            obs=json.loads(line);lines+= [f'{obsnames[k]}：'+('模擬步，不是真人秒數' if k=='timeUnit' else str(v)) for k,v in obs.items()]
        elif line.startswith('[{'):
            fs=json.loads(line)
            for f in fs:
                bg='其他九人全部拒絕' if f['otherProfile']=='others_decline' else '其他九人全部願意'
                act='我參與協助' if f['ownChoice']=='participate' else '我拒絕協助'
                lines.append(f'背景：{bg}；我的選擇：{act}')
                for key,title in [('ownCappedExitSteps','我自己的截尾離開步數'),('otherNineMeanCappedExitSteps','其他九人的平均截尾離開步數')]:
                    v=f[key];lines.append(f"  {title}：平均 {v['mean']}，觀察範圍 {v['observedMin']}–{v['observedMax']}")
                lines.append(f"  開發種子數：{f['developmentSeedCount']}")
        else:lines.append(line)
    result='系統訊息：你代表一位行人，做個人的協助決策。只回傳嚴格 JSON。\n\n使用者訊息：\n'+'\n'.join(lines)
    assert 'You decide' not in result and 'This is an extension' not in result
    return result
zh={r['id']:{'explanation':translations[i],'prompt':translate_prompt(r['messages'])} for i,r in enumerate(data)}
(H/'translations.zh-TW.json').write_text(json.dumps({'status':'AI-assisted reading translation; not human coding','items':zh},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
text=(archive/'Review.en-content.html').read_text(encoding='utf-8')
text=text.replace("const esc=s=>",'const zh='+json.dumps(zh,ensure_ascii=False).replace('</','<\\/')+''';
const optionText={yes:'是：理由不足',no:'否：有支持選擇的考量',unclear:'無法明確判斷',consistent:'一致：理由支持行動',conflict:'衝突：理由明確支持相反行動',correct:'正確',incorrect:'錯誤',not_applicable:'不適用：未做這類比較／計算',none:'沒有',present:'有：將未提供的資訊當成事實'};
const help={insufficient_reason:'有沒有提出支持自己選擇的考量？單純宣告願意、重述規則或表示資訊不足，不一定構成支持理由。',actionReasonRelation:'判斷理由是否支持最後選擇，不是你是否同意該選擇。',comparisonJudgment:'是否有比較效用、時間或不同背景？沒有比較選不適用。未提供背景機率時，不要自行假設等機率。',unsupportedInformation:'是否將 prompt 沒給的資訊當成事實？明確提出假設或表示不確定，不自動算有。',arithmeticJudgment:'是否有可核對的計算？單純比較誰較快，不一定是算術；沒有計算選不適用。'};
const esc=s=>''')
text=text.replace('AI 標籤已隱藏；請自行判斷。','AI 標籤已隱藏；請自行判斷。中文為 AI 輔助翻譯，若有歧義請核對英文，不是評分建議。')
text=text.replace('<h2>${x.id} · ${esc(x.caseID)}</h2><details>', '<h2>${x.id} · ${esc(x.caseID)}</h2><details open><summary>題目與情境：中文翻譯</summary><pre>${esc(zh[x.id].prompt)}</pre></details><details>')
text=text.replace('<strong>Decision:</strong> ${esc(x.decision)}</p><blockquote>${esc(x.explanation)}</blockquote>', '<strong>模型最後選擇：</strong> ${x.decision===\'participate\'?\'參與協助\':\'拒絕協助\'} (${esc(x.decision)})</p><p><strong>模型理由：中文翻譯</strong></p><blockquote>${esc(zh[x.id].explanation)}</blockquote><p><strong>模型理由：英文原文（證據請從這裡複製）</strong></p><blockquote>${esc(x.explanation)}</blockquote>')
text=text.replace('<legend>${names[k]}</legend>','<legend>${names[k]}</legend><div>${help[k]}</div>')
text=text.replace('>${v}</label>','>${optionText[v]}</label>')
text=text.replace("function persist(){", "state.translationAssistance={language:'zh-TW',type:'AI-assisted reading translation',version:'20261119-v1',englishOriginalRetained:true};\nfunction persist(){")
text=text.replace("function persist(){try{", "function persist(){state.translationAssistance={language:'zh-TW',type:'AI-assisted reading translation',version:'20261119-v1',englishOriginalRetained:true};try{")
text=text.replace('原 explanation 的證據片段（直接複製）','英文原始理由的證據片段（直接複製英文，可在下面用中文解釋）')
text=text.replace('完成 ${n}/48 題（五欄＋原文證據＋說明）','完成 ${n}/48 題（五欄＋英文原文證據＋你的說明）')
assert text.count('const zh=')==1 and '${optionText[v]}' in text and '中文翻譯</strong>' in text
old.write_text(text,encoding='utf-8')
guide=H/'START_HERE.zh-TW.md';g=guide.read_text(encoding='utf-8')
addition='\n## 中文閱讀版本\n\n表單已附上全部 48 則模型理由與完整情境的中文翻譯，所有選項也改成中文顯示。中文是 AI 輔助翻譯，不是評分答案；原始英文、數值與正式評分代碼保留。遇到翻譯疑義請核對英文並在備註說明。證據欄仍請複製英文原句，你的評分說明可以用中文。下載的 JSON 會記錄曾提供中文翻譯輔助，這不會被當作 AI 替你評分。\n\n原有勾選會沿用同一個瀏覽器的儲存鍵；重新整理前建議先下載目前 JSON 備份，必要時可匯入。\n'
if '## 中文閱讀版本' not in g:guide.write_text(g+addition,encoding='utf-8')
print('Translated 48 explanations and exact-context reading versions; original packet, rating values and storage key retained.')
