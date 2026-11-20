# 正式情境決策研究結果（P-030）

2026年11月16日。已依事前鎖定完成28條件各30次，共840次全新個人API選擇；30個完整排程區塊。840份回覆有效、零重試、零技術無效，全部840份理由完成具名助理覆核。先導208份、既有P-028群體實驗與174輪物理校準分開保存，不併入本次估計。

**本次觀察：抽象報酬層345/360次選協助；物理層只給布局時236/240次，提供時間預測時63/240次。**這是指定模型、提示與固定情境下的輸出分布，不是840位真人，也不是840輪撤離模擬。

最直接的三個發現如下。抽象層低成本120/120次協助、中成本118/120、高成本107/120；LLM有成本反應，但高減低約−10.83個百分點，比原公式約−21.10個百分點的下降小。物理層的協助率由98.33%降至26.25%，差−72.08個百分點；B2至B4提供預測後僅3/180次協助，B5兩個工作間隔仍為60/60。這支持「特定資訊與情境下選擇明顯不同」的描述，不支持「永遠協助」或「LLM比原模型好」的概括。

[英文標註結果圖（PNG）](../../experiment_records/data/analysis/scenario_formal_v1_20261116/SCENARIO_RESULTS.png) · [向量PDF](../../experiment_records/data/analysis/scenario_formal_v1_20261116/SCENARIO_RESULTS.pdf)。曲線連線僅輔助閱讀三個固定成本點，不表示已量測中間成本。

## 事前指定的兩個主要描述量

| 描述量 | 估計值與逐點描述性95%區間 |
|---|---:|
| A：LLM高成本減低成本變動，再扣原公式相同變動 | 0.1027 [0.0527, 0.1527] |
| B：提供時間預測減只給布局的協助率 | -0.7208 [-0.7417, -0.6958] |

A為兩個av尺度及兩種措辭等權的成本反應差。正值表示LLM高減低的反應較不負，不代表LLM更好。B為八個物理設定等權的資訊條件差；負值表示提供這些預測時較少協助，不代表撤離較差。以30個完整排程區塊重抽5000次，seed2026111662；區間依賴區塊可交換等假設，不保證請求獨立、真人外推或兩區間同時95%涵蓋。沒有確認性p值。

## 抽象報酬：全部12條件

固定X10、τ.4、ω5；β=cv/av。參與承擔cv，拒絕在無人參與時承擔av。原公式為理論參考，並非全域最優解；LLM未獲得混合他人意願的機率，不能將自由選擇判為唯一正確或錯誤。

| av／β | numeric協助數/30 | contextual協助數/30 | 原公式參與機率 |
|---|---:|---:|---:|
| A30_R10 | 30 | 30 | 0.2369 |
| A30_R50 | 30 | 30 | 0.0875 |
| A30_R90 | 30 | 26 | 0.0259 |
| A70_R10 | 30 | 30 | 0.2369 |
| A70_R50 | 30 | 28 | 0.0875 |
| A70_R90 | 22 | 29 | 0.0259 |

## 物理情境：全部16條件

總可移動障礙固定5；B是出口附近參考阻塞位置數，M是工作進度間隔，不能直接說成重量、受傷機率或秒數。預測來自先前固定六個開發種子、兩個他人意願端點，並非本次新跑的物理結果。

| 布局／工作間隔 | 只給布局協助數/30 | 提供時間預測協助數/30 |
|---|---:|---:|
| B2_M1 | 29 | 0 |
| B2_M4 | 27 | 0 |
| B3_M1 | 30 | 0 |
| B3_M4 | 30 | 3 |
| B4_M1 | 30 | 0 |
| B4_M4 | 30 | 0 |
| B5_M1 | 30 | 30 |
| B5_M4 | 30 | 30 |

這個對比同時改變可用資訊與提示內容。因此可描述「提供個人時間代價資訊後，選擇分布改變」，不能證明單一心理機制。物理時間沒有被轉成原Eq20的av/cv，兩層不混作同一效用檢驗。

## 陳述理由與品質

以下是全量覆核後的多標籤數目，不是獨立人類意見、隱藏思考或已驗證的因果動機。每個標籤以原文完整理由作精確Unicode片段證據；助理逐筆閱讀並明列批次判斷，再由離線工具組裝。沒有第二位人類評分者、kappa或分類準確率保證。

| 任務／資訊 | 分母 | 個人代價／自身結果 | 無人協助損失 | 使用預測 | 理由不足 | 動作理由不明 |
|---|---:|---:|---:|---:|---:|---:|
| abstract_choice / contextual_equivalent | 180 | 180 | 180 | 0 | 0 | 0 |
| abstract_choice / numeric | 180 | 180 | 178 | 0 | 0 | 0 |
| physical_choice / calibrated_forecast | 240 | 240 | 60 | 240 | 0 | 0 |
| physical_choice / geometry_only | 240 | 6 | 0 | 0 | 199 | 199 |

共有204筆含品質不明、錯誤或明確問題的註記，逐筆保留於QUALITY_ANNOTATIONS.json；它們仍在協助率分母中，沒有修正raw action或挑選排除。各品質欄位的完整分布見QUALITY_BY_TASK.json。未標成錯誤不等於已證明語意完全正確。布局組本來沒有預測可用，其forecast_use必須為0；不能把此結構性差異當成另一個認知發現。

同一助理在初次逐筆判讀後，另做編碼一致性覆核；例如只重述沒有時間資料，不等於已使用個人代價權衡。122筆最終編碼修訂與原始判斷均保留，手冊未改、原始動作未改。布局組199/240筆被保守標為理由不足，表示文字不足以支持具體決策解釋，不表示已證明模型沒有任何內在理由。另有一筆明確人數條件誤讀：P030_SV3_20261116_b030_AC_A70_R50_contextual_equivalent把「包含自己的10人」寫成「其他10人」；仍保留於正式分母。三筆端點平均比較及六筆B5規則適用有不明註記，不能包裝為全量語意正確。

## 可支持的貢獻與限制

本研究提供可追溯的情境比較：在原報酬規則下量化LLM與原調整行為公式的成本反應差，再在隔離的物理擴充任務中觀察資訊條件及陳述理由。資料顯示的選擇差異應以全表、固定分母與品質註記共同解讀，不能只挑代表句。

不能據此宣稱LLM更有效率、已模擬真人、原公式是撤離全域最優，或時間預測的差異等於真實救援因果效益。僅單一模型／參數、固定八格布局、每條件30次，模型別名後端及請求相關性仍有限制。P-029只作先導與放行，本次正式資料不能倒過來作新的獨立校準。

下一步以本次正式結果整合研究問題、方法及討論，整理供教授檢視的結果表與例子。如要測實際群體後果或新增模型／提示，先另訂設計及新的資料邊界，不為追求協助率而調整本批。

## 資料與稽核

- 原始資料：experiment_records/data/scenario_formal_v1_20261116（每筆CLAIM、response.raw、result.json；coding.json與review_evidence）
- 分析：experiment_records/data/analysis/scenario_formal_v1_20261116（主要描述量、區塊對比、840筆來源目錄、28格表、理由摘要、品質註記與SHA256清單）
- 設計：FORMAL_DESIGN.zh-TW.md；有效鎖定為scenario_formal_v1_20261116_r2；鎖定ID eb5b35d6f58193969a45216669c0aa5d25425794134a12da7b7fc766c732d716
- P-028封存及生產數學／移動程式不變；本次沒有新Unity執行或新獎勵設定。


## 理由例子（討論用）

每類依符合任務、動作及標籤的trialID排序選第一筆；屬事後討論輔助，不代替全量比例。完整預定分組標籤例子索引另見reason-summary.json。

**抽象層協助 — P030_SV3_20261116_b001_AC_A30_R10_contextual_equivalent（A30_R10 / contextual_equivalent）**

> The personal burden of participating is low (0.03), while the loss if nobody volunteers is higher (0.3). I am willing to assist, though others’ choices are unknown.

**抽象層拒絕的反例 — P030_SV3_20261116_b001_AC_A30_R90_contextual_equivalent（A30_R90 / contextual_equivalent）**

> The personal burden of participating is 0.27. If everyone declines, the loss is 0.3; otherwise declining avoids that burden. With others’ choices unknown, I prefer not to take on the burden.

**布局組理由不足 — P030_SV3_20261116_b001_PC_B2_M1_geometry_only（B2_M1 / geometry_only）**

> I’m willing to assist with a movable obstacle. The exit is partially blocked, but evacuation remains possible without handling, and the information gives no forecast that helping would improve my evacuation time.

**時間預測組拒絕 — P030_SV3_20261116_b001_PC_B2_M1_calibrated_forecast（B2_M1 / calibrated_forecast）**

> I would decline assistance because the forecasts show fewer mean exit steps for me when I decline if others decline, and a slightly lower mean when others are willing. The forecasts are limited estimates, but they do not suggest a personal time benefit from participating.

**時間預測組協助 — P030_SV3_20261116_b001_PC_B5_M1_calibrated_forecast（B5_M1 / calibrated_forecast）**

> I am willing to help move an obstacle. In both hypothetical endpoint profiles, the forecasts show fewer mean capped exit steps for me when participating; these are estimates, not guarantees, and I cannot infer which profile applies.
