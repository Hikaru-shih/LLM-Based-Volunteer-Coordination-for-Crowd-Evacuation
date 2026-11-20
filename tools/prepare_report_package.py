"""Existing-data report assembly, literature positioning and defense notes; no API dispatch."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'report';OUT.mkdir(exist_ok=True)
SRC=OUT/'source';SRC.mkdir(exist_ok=True)
old=ROOT/'research/scenario_decisions_v2/poststudy_20261117/THESIS_DRAFT.zh-TW.md'
text=old.read_text(encoding='utf-8')
text=text.replace('教授審閱草稿　2026年11月17日','教授審閱版本　2026年11月17日')
text=text.replace('尚未完成系統性文獻定位，故本稿不宣稱首次提出此問題或具有已證實的領域原創性。','本稿以原撤離模型、生成式代理、LLM受試研究與解釋忠實性四項相關工作定位研究；這是聚焦文獻整理，不是系統性回顧，也不宣稱領域首次。')
text=text.replace('[1,2]','[1,5]').replace('停止規則[3]','停止規則[6]')
for before,after in [('第六章','第七章'),('第五章','第六章'),('第四章','第五章'),('第三章','第四章'),('第二章','第三章')]:text=text.replace('## '+before,'## '+after)
related='''## 第二章 相關研究與本研究定位

Lin與Wong將細胞自動機與賽局模型結合，研究可搬移障礙下的撤離，並比較障礙位置、數量與搬移時間等條件對群體及志工的影響[1]。本研究沿用其基礎報酬與調整參與公式作比較，P030的量測單位則是固定情境中的個人選擇，並未重新驗證原論文全部群體數值結果。

Park等人的Generative Agents以記憶、反思與規劃支援持續互動的代理，並在25名代理的小鎮環境中評估可信的行為表現[2]。本研究每次使用全新上下文，只研究個人協助意願；沒有將該架構或其人類行為可信度結論移植到本系統。

Aher等人以Turing Experiments檢查語言模型能否重現既有人類受試研究，亦發現特定模擬偏差[3]。這提醒我們，模型輸出與人類行為的一致性必須經過對照；本研究沒有真人行為基準，因此將LLM與賽局公式的差異限定為模型反應比較。

Turpin等人顯示，思維鏈文字可能未忠實呈現輸入偏差對答案的影響[4]。本研究的簡短理由不是該研究的思維鏈任務，不能直接沿用其錯誤率；引用此工作是為了界定方法上的保守原則：陳述理由不能直接當作內部決策機制的證據。

上述工作分別提供撤離模型、持續代理架構、人類對照及文字解釋的研究背景。本研究的具體定位，是在單一模型及固定條件內，提供成本反應差、物理資訊條件差與來源綁定的理由品質紀錄。貢獻主張建立在本批可量測的比較上，不以LLM優越、人類相似或文獻中尚無相關研究為前提。

'''
text=text.replace('## 第三章 原模型與任務邊界',related+'## 第三章 原模型與任務邊界')
english='''## English Abstract

This study compares individual LLM assistance choices with a volunteer-game reference in evacuation scenarios. The prospectively locked study collected 840 fresh choices across 28 conditions, with 30 requests per condition. Abstract conditions varied cost, loss scale and wording. A separate physical task compared layout information with calibrated time forecasts. Abstract participation was 345/360, with a weaker cost decline than the reference. Physical participation was 236/240 with layouts and 63/240 with forecasts; both B5 settings retained full participation. All reasons were assistant-reviewed. Findings describe fixed-scenario model outputs, not validated human behavior, an isolated causal mechanism or new group evacuation effects.

'''
text=text.replace('## 第一章 研究問題與定位',english+'## 第一章 研究問題與定位')
text=text.replace('此步不是獨立評分者驗證。','此步不是獨立評分者驗證。其後28份樣本的助理示範填答亦不計為人類評分，不改寫正式編碼或計算人類一致率。')
text=text.split('## 參考依據與提交前事項')[0]
refs=[
{'id':1,'authors':'Guan-Wen Lin and Sai-Keung Wong','title':'Evacuation simulation with consideration of obstacle removal and using game theory','publication':'Physical Review E 97, 062303 (2018)','url':'https://doi.org/10.1103/PhysRevE.97.062303','evidence':'Original supplied PDF page 1 and saved pages 7–8; bibliography verified directly from PDF.'},
{'id':2,'authors':"Joon Sung Park, Joseph C. O’Brien, Carrie J. Cai, Meredith Ringel Morris, Percy Liang, and Michael S. Bernstein",'title':'Generative Agents: Interactive Simulacra of Human Behavior','publication':'arXiv:2304.03442v2 (2023)','url':'https://arxiv.org/abs/2304.03442v2','evidence':'Author abstract and metadata; architectural positioning only.'},
{'id':3,'authors':'Gati V Aher, Rosa I. Arriaga, and Adam Tauman Kalai','title':'Using Large Language Models to Simulate Multiple Humans and Replicate Human Subject Studies','publication':'Proceedings of the 40th International Conference on Machine Learning, PMLR 202:337–371 (2023)','url':'https://proceedings.mlr.press/v202/aher23a.html','evidence':'Official proceedings abstract and BibTeX metadata.'},
{'id':4,'authors':'Miles Turpin, Julian Michael, Ethan Perez, and Samuel R. Bowman','title':"Language Models Don’t Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting",'publication':'arXiv:2305.04388v2, NeurIPS 2023','url':'https://arxiv.org/abs/2305.04388v2','evidence':'Author abstract and metadata; no transfer of its error rates to P030.'},
{'id':5,'authors':'Project artifacts','title':'Original model correspondence and frozen implementation','publication':'Local source evidence, not an external peer-reviewed publication','url':'local_archive/20261117_cleanup/original/research/individual_agent_v1/MODEL_CORRESPONDENCE.zh-TW.md','evidence':'Saved formula correspondence and current source; does not replace paper citation.'},
{'id':6,'authors':'Project P030','title':'Prospective registration and sealed scenario decision results','publication':'2026-11-16; 840 choices, 30 scheduling blocks','url':'experiment_records/study_preparations/scenario_formal_v1_20261116_r2/registration.json','evidence':'Raw replies and sealed analysis in experiment_records/data/scenario_formal_v1_20261116 and data/analysis/scenario_formal_v1_20261116.'}]
text+='## 參考文獻與專案證據\n\n'
for r in refs:text+=f"[{r['id']}] {r['authors']}. {r['title']}. {r['publication']}. {r['url']}\n\n"
submission_notes='''## 提交資訊與使用界線

本文是依現有證據完成的教授審閱報告，採一般A4格式。作者姓名、學號、校系、指導教授及校系規定版型尚未提供，因此未臆填封面資訊。相關工作採四篇直接相關論文的聚焦整理，不宣稱為完整系統性回顧。人工行為效度與獨立人類理由覆核均未完成；使用者對個別例子的認同不視為新增獨立評分。

本稿正文、英文簡報與口試準備使用同一P030結果；不把舊P028群體研究或P029先導併入分母。口試問答是依現有證據準備的答辯建議，不是已發生的教授評語。研究內容可供審閱，正式提交前仍須套用校系版型並補齊個人資訊。
'''
(SRC/'Report.zh-TW.md').write_text(text,encoding='utf-8')
(SRC/'references.json').write_text(json.dumps({'checkedDate':'2026-11-17','scope':'Focused related work; not an exhaustive systematic review','references':refs},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
qa='''# 口試準備與研究說明

## 一分鐘研究介紹

我的研究比較個人LLM在撤離協助情境中的選擇，與原志工賽局參考公式的反應差異。正式研究包含840次決策，分成抽象報酬與物理資訊兩層。結果顯示LLM會隨成本提高而較少協助，但反應比原公式平緩；在物理任務中，提供時間預測後協助率明顯下降，而B5仍全數協助。我研究的是固定條件下的模型差異及其解釋界線，沒有宣稱LLM較好或已重現真人。

## 為什麼這是Agent研究

每次模型代表一名行人，只能選自己的協助意願，不控制其他人。這是個人決策代理的評估，沒有跨回合記憶或人格，不等於Generative Agents那種持續生活的完整架構。

## 原模型是不是理想答案

原公式是明確的參與機率參考，不是整場撤離的全域最優解。報酬表的個人期望效用差為q·av−cv，但正式自由選擇未提供其他人全部拒絕的聯合機率q，故不能把每個LLM動作判成唯一最佳或錯誤。

## 最重要的結果是什麼

抽象層成本由低到高，協助率100%降至89.17%，下降10.83個百分點；原公式約下降21.10個百分點。物理層布局組98.33%，提供預測組26.25%，差−72.08個百分點。後者是資訊條件差，不是實際撤離效率差。

## 為什麼提供時間預測後比較不協助

回答常引用自身時間結果，而且B2至B4預測組僅3／180次協助、B5仍60／60次。這與具體後果資訊有關的解釋相容；但預測組也增加篇幅、數字與細節，不能識別單一因果機制。

## 為什麼B5仍全數協助

固定預測中，B5的自身參與平均截尾時間在兩端點都較短，回答也常引用此點。這是該固定情境的選擇分布；不能把它說成已發現普遍的人類救援心理。也不能將部分出口τ直接推成整體路網狀態。

## 是否把協助獎勵設得太高

抽象層沒有額外協助獎金，參與仍扣cv；物理層沒有另發協助獎勵，使用自己的截尾時間。其他人的時間結果不被加成自己的獎勵。兩層效用並未建立可互換的校準關係。

## 840次是否代表840個人

不代表。它們是單一模型在固定設定下的840次新上下文請求。每條件30次是涵蓋情境與完整理由檢查的可行性選擇，不是人類樣本數或正式檢定力保證。

## 信賴區間能說明什麼

這是30個完整排程區塊的5000次重抽、逐點描述性95%區間。主量A為+10.27個百分點[5.27,15.27]，B為−72.08[−74.17,−69.58]。它們依賴區塊可交換等假設，沒有確認性p值、同時涵蓋或真人外推保證。

## 理由分析可靠嗎

840份由助理編碼，199／240份布局理由被保守標為不足，判準有主觀性。後續28份也只是助理示範，不是獨立人工驗證。應把理由數字放在探索性品質描述，不當作隱藏思考或因果動機的證明。

## 跟原論文及既有LLM研究差在哪

原論文研究有可搬移障礙的群體撤離；本批直接量測個人決策與理論機率的成本反應差。Generative Agents研究持續記憶反思架構；本研究隔離單次選擇。人類受試模擬文獻有外部人類對照，本研究沒有，所以貢獻限定於模型比較與追溯方法。

## 為什麼不再增加實驗

目前選擇把研究範圍固定在既有正式資料並如實交代限制。增加模型、提示控制或群體研究需要新登錄及新的資料邊界，不應在看到結果後反覆調整直到出現期待現象。

## 研究貢獻與最大限制

貢獻是同一報酬契約下可量化的模型反應對照、隔離的物理資訊比較，以及完整來源與品質紀錄。最大限制是單一模型、固定刺激、資訊與篇幅混雜、沒有真人基準及獨立人工編碼。這支持一份範圍明確的實證畢業研究，尚不支持普遍的人類模擬或撤離政策效益主張。
'''
(OUT/'Oral_Defense.zh-TW.md').write_text(qa,encoding='utf-8')
print({'reportCharacters':len(text),'references':len(refs),'defensePrepared':True})
