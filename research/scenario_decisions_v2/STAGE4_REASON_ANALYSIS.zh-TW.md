# 第4步理由分析完成說明

2026年11月16日。已完成雙層任務手冊、可執行的編碼檢查、分組摘要、代表例子規則與第3步診斷覆核的轉接。沒有呼叫LLM，也沒有新增Unity模擬；尚無新模型理由的實證分析。

## 交付內容

- [雙層理由分析手冊](REASON_CODEBOOK_V3.zh-TW.md)
- [機器可讀的十二類標籤與品質欄位](reason-codebook.v3.json)
- [十二個英文教學例子](REASON_CODING_EXAMPLES.en.md)
- 工具tools/scenario_reason_coding.py與測試tools/test_scenario_reason_coding.py

既有九類新增forecast_use、uncertainty_awareness與scale_or_normalization。personal_cost沿用舊代碼，但明確涵蓋自身報酬與較早撤離的比較，避免把只談自身收益的回覆誤判成沒有理由。

## 實際流程

先讀第3步的登錄快照、claim、原始回覆及解析結果，建立全量表。預設不填標籤；可讀且非重複的理由標unreviewed，其餘保留狀態並標not_applicable。逐筆閱讀後，加入標籤、原文片段、四種品質判斷、具名編碼者與註記。工具檢查原文、雜湊、位置、資料來源與欄位一致性，不用關鍵字自動替模型判動機。

診斷動作錯誤但理由可讀時，仍保留分析；HTTP失敗、格式無效、重複回覆及尚未發送的列不從總表消失。摘要區分collectionComplete與coverageComplete：前者檢查計畫收集是否完成，後者檢查目前可分析理由是否全部覆核。零可分析理由不宣稱覆核完成。完整模式須兩者都成立，不能拿中斷批次當完整結果。

分類可並存。摘要分母為每組已覆核的可分析理由，同時報可分析總數與未覆核數。零覆核時比例為null。phase、scenario與information分開，不把診斷與自由選擇或兩個資訊組混合。代表例子固定按trialID排序選第一個正例及第一個標籤缺席例，並保留全量資料，避免事後挑句子。

## 與放行檢查銜接

gate-review命令把完整診斷覆核轉為第3步格式，但不直接宣稱live通過。它要求每筆診斷動作符合題意、理由比較正確、動作一致、沒有未解資訊或算術問題，且不是空泛理由。轉接保留raw雜湊與原文，最終仍由transport檢查實際live證據。合成資料不能放行真實自由選擇收集。

## 操作命令

以下RUN與檔名皆需換成實際已收集批次；命令只讀紀錄與寫分析檔，不呼叫API：

```powershell
python tools/scenario_reason_coding.py template RUN coding.json
python tools/scenario_reason_coding.py validate RUN coding.json
python tools/scenario_reason_coding.py summarize RUN coding.json summary.json --require-complete
python tools/scenario_reason_coding.py gate-review RUN coding.json gate-review.json
```

最後一項只適用診斷。自由選擇沒有唯一正確效用答案，不用gate-review評分其是否合作。若中斷批次仍要做描述性摘要，可以不加require-complete，但須保留兩種未完成旗標與所有缺漏列。

## 測試與適用界線

驗證涵蓋原文與動作不得改寫、每個標籤需證據、錯誤標籤與位置、資訊條件限制、品質欄位一致性、語意失敗保留、缺漏與重複保留、未覆核分母、手冊變動、診斷轉接及合成資料不得冒充live。

另對第3步既有16筆合成佔位回覆，建立空白表與完整worked example。佔位句沒有真正選擇理由，故示範標為insufficient_reason，動作理由關係記unclear；這不代表新LLM的理由都不足，也不代表程式能自動正確分類語意。資料明確位於validation，不納入研究樣本。

目前沒有獨立第二位真人編碼者，不宣稱真人一致性或kappa。這一步完成的是可追溯的分析方法與工具。下一步是第5步先導的取樣、版本鎖定與執行登錄，再實際取得模型回覆；先導後如需改手冊，保留版本並重新編碼受影響資料。
