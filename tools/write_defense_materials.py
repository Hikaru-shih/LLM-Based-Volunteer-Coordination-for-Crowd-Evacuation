from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'report'
zh='''# 專題口試準備

## 一分鐘介紹

我的專題研究LLM在撤離情境中，如何決定自己是否願意協助搬移障礙物，並觀察其選擇與原賽局模型的差異。重點不是證明LLM比較好。正式實驗有28個條件、每條件30份，共840次API回覆。第一項任務保留原報酬規則，發現成本提高時LLM參與率下降，但幅度比參考公式小。第二項任務比較僅提供布局與加入時間預測，參與率由98.33%變為26.25%，但出口五個參考位置全受阻的設定仍全部參與。事後效用分析進一步指出，四個設定在兩種已提供背景下有同向個人偏好，其中120份選擇都相符；另四個設定則需要對其他人的信念才能解讀。我也完成48則理由的作者人工評分，揭露先前AI答案接觸，並保留與AI的分歧。

## 1 你的研究問題與貢獻是什麼

比較個人LLM協助意願在成本與資訊改變時，如何偏離調整參與公式，以及何時符合已提供的自身平均結果。貢獻是可追溯的條件比較、兩端點效用解讀及理由品質紀錄；不是新的普適賽局定理，也不是已驗證的人類模型。原模型參考、物理延伸與事後分析分開，讓比較的意義明確。

## 2 為什麼不是讓LLM全域指揮或規劃路線

那會同時改變路徑規劃、任務分配與協助意願，難以知道差異從何而來。這個研究先限制每個請求只代表一位行人的協助意願，實際啟用與移動由模擬器處理。正式資料收集是固定情境的API決策，不是每一步都由LLM操作Unity。

## 3 這算AI agent嗎

是受限的個人決策代理，不是具有持續記憶、反思、規劃與長期互動的完整生成式代理。每次請求重設上下文，沒有跨回合學習。我會用實際具備的功能界定agent，不借用其他架構的人類可信度結論。

## 4 數學模型是不是理想最優解

不是整體撤離最優解。原基本賽局的對稱混合策略另有公式，本研究p_ref還包含出口未受阻比例與行為係數調整。自由選擇沒有提供所有他人拒絕的機率，因此不能把偏離p_ref一概標成錯誤或不理性。

## 5 為什麼一開始幾乎都願意幫忙

不能從參與率直接確定原因。在報酬任務，協助沒有額外獎勵，仍得到高協助率；它可能反映提示與模型設定下的決策傾向，不能直接叫作利他或人類特性。高成本參與率降至89.17%，表示並非完全沒有成本反應。物理任務有預測時B2至B4幾乎都拒絕，說明高參與率並非所有條件下固定不變。

## 6 為什麼B5仍全部協助

對已提供的六組開發平均值而言，兩個B5設定在全拒絕與全願意背景下，參與都對自身平均截尾時間較有利，因此全部參與與這些個人結果資訊一致。這是條件平均值的一致性，不是保證、逐種子支配，也不能證明模型真的計算過效用。

## 7 加入預測就變合理了嗎

只能局部地說與已提供資訊一致。B2_M1、B4_M1兩端點都偏好拒絕，兩個B5都偏好參與，四設定120份選擇全部相符；另外四個設定會反轉偏好，沒有信念便沒有唯一答案。不能把237/240與123/240兩端點符合數合成一個準確率。

## 8 q門檻代表什麼

只是敏感度分析：假設可能背景只有其他九人全拒絕或全願意，q是前者機率。用已提供平均時間求兩行動效用相等的門檻。四個門檻約0.2397、0.0294、0.0941、0.0069；未量測LLM信念，也沒校準混合意願背景。它不能用來反推模型實際相信多少人會幫忙。

## 9 預測組同時變長，怎麼排除混淆

目前無法排除。預測資訊、數字、細節與長度一起改變，所以我們稱為資訊條件差，而不是預測本身的因果效果。長度相近但不含決策相關資訊的控制條件是後續實驗，不會寫成已完成。

## 10 30次回覆是30個獨立的人嗎

不是。它們是同一模型設定下的重複API輸出。30個區塊是排程單位，不是30位真人或持續代理。低溫下的頻率也不代表刻意實行混合策略。描述性bootstrap以整區塊重抽，依賴區塊可交換性等條件，不能當成已證明請求獨立。

## 11 48則人工評分能驗證什麼

是作者對五項理由品質的人工檢查。我先前看過AI示範並取得中文閱讀翻譯，因此非獨立盲評。各欄一致率是93.75%、85.42%、66.67%、97.92%、100%。27個欄位分歧涉及25則回應，不能宣稱是27個模型錯誤，也未回頭更改原標籤。

## 12 為什麼比較判斷一致率比較低

16個差異都是作者評正確、AI評不適用。作者常把正確敘述有條件的參與成本與無志工損失視為比較，AI原標籤未把它算作適用的比較。另有7個行動理由關係、3個理由充分性、1個未提供資訊的分歧。我整理這些差異，但沒有把整理當成第三位人工裁決或把答案硬改一致。

## 13 為什麼97.92%一致的κ卻是0

因為原AI在未提供資訊欄全部選「沒有」，類別極不平衡；人類47則沒有、1則不明確，實際一致率與邊際推得的機會一致率相同。算術欄雙方48則都不適用，因此κ分母為0，無法定義。不能只看高百分比就說能辨識錯誤。

## 14 Unity與原有模擬在這裡扮演什麼角色

174次先前開發物理模擬提供固定預測，正式840次是API決策。沒有把208份先導、先前群體研究或開發模擬混入正式選擇樣本。B是相關出口受阻參考位置數、總障礙固定5；M是每單位工作進度間隔，不是危險、重量或真人秒數。提示中的網格是八鄰居，不能把它說成只有四方向。

## 15 若有更多時間，優先做什麼

先用長度相近的控制提示分離資訊效果，再在相同報酬任務測第二個模型，最後才考慮群體撤離結果或真人行為對照。這些是後續研究，不是本次交付已完成的部分。若學校有指定格式，還需補作者／系所等資料；目前不自行猜測。

## 報告時的數字與措辭

正式840次、28條件、每格30；報酬345/360，物理236/240與63/240。Contrast A為+10.27個百分點[5.27,15.27]，B為−72.08點[−74.17,−69.58]。區間是逐項描述性95%區間，沒有確認性p值。主張「成本下降較參考小」「資訊條件差」「與已提供自身平均結果的一致性」，避免改說「LLM較好」「人類行為已驗證」「整體效率提升」或「預測獨立造成改變」。
'''
(O/'Oral_Defense.zh-TW.md').write_text(zh,encoding='utf-8')
en='''# Defense questions and short answers

## What is the contribution

I compare cost response and information-conditioned personal assistance choices under explicit conditions. The added endpoint analysis shows where own conditional mean-utility preferences agree across supplied backgrounds and where beliefs are needed. The study provides traceable response and quality records; it does not establish a superior evacuation policy.

## Is the reference an optimal evacuation policy

No. It is the evacuation model's adjusted participation law, distinct from the unadjusted symmetric mixed equilibrium. Without beliefs about others, the free-choice payoff table does not identify one uniquely best action.

## Why did the LLM almost always help

The data do not identify one cause. There is no participation bonus. Payoff participation still falls from 100% to 89.17% as relative cost rises. With physical forecasts, B2-B4 participation drops to 3/180, while B5 stays at full participation. The tendency depends on the condition rather than being universal altruism.

## Are forecast choices personally sensible

In four settings the supplied conditional means favour the same action at both endpoints, and all 120 choices agree. Four other settings reverse preference; interpreting them requires a belief or decision criterion. These are development means, not guaranteed outcomes or a test of hidden reasoning.

## What does the belief threshold mean

Only under a hypothetical two-endpoint mixture, q is the probability of all other nine declining. The thresholds describe sensitivity of the preferred mean-utility action. No beliefs were elicited, and mixed willingness profiles were not calibrated.

## Did you isolate the effect of forecasts

No. Forecast content, numbers, detail and prompt length changed together. I describe an information-package contrast. A length-matched irrelevant-information control remains future work.

## Do the repeated API proportions represent a mixed strategy

Not necessarily. They are empirical output frequencies from one model configuration at temperature .15. The study does not identify deliberate randomization, independent human-like agents or stable population participation probabilities.

## Was explanation coding independently validated

All 840 original explanations were assistant-coded. I personally reviewed five quality fields for 48 sampled responses after having access to the AI example and Chinese reading translations. This is disclosed non-blind author review, not independent validation. Original labels remain unchanged.

## Why are some agreement statistics misleading on their own

The unsupported-information field has 47/48 agreement but kappa zero because the assistant used one category throughout. Arithmetic has 48/48 agreement with all labels not applicable, so kappa is undefined. Category coverage matters alongside agreement percentages.

## What did the differences reveal

There are 27 differing field entries across 25 responses: 16 concern comparison scope, seven supportive reasoning versus absence of contradiction, three sufficiency thresholds, and one an uncertain burden inference. This is an assistant interpretation of the notes, not adjudication or 27 demonstrated model errors.

## What exactly ran in Unity

Earlier development simulations supplied the fixed forecasts. The formal dataset is 840 API choices, not 840 new evacuation runs. The LLM controls personal willingness only; simulator activation, handling and movement are separate.

## What would you test next

First a length-matched prompt control, then a second model under the same payoff task. Group evacuation outcomes and human behavioral validation require separate designs. None was added during this writing revision.
'''
(O/'Defense_QA.en.md').write_text(en,encoding='utf-8')
print('Updated Chinese oral-defense preparation and English short-answer script.')
