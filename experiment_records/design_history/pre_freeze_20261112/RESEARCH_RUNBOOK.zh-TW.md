# 個人 agent 主線操作入口（v0.5 草案）

目前請先閱讀 [README](README.md)、[研究方案](RESEARCH_PROTOCOL.zh-TW.md) 與 [實作清單](RESEARCH_INTEGRATION_PLAN.zh-TW.md)。主線是個人 LLM vs 原賽局的情境比較，不是全域分派。

- 主模式固定 PaperRelocation + PaperReference + PolicyWillingness；Core 為主要資訊。選 LLM 只替換個人意願，不改為 LLM Coordination。
- RandomMatched 需重新收集獨立校準；目前沒有新主線可用的實證校準值或正式 lock。
- 全域 S5 及舊個人 template 的組別／主指標不能直接沿用。開發檢查不要掛載舊 lockedStudyPlanPath 或 lockedCoordinationStudyPlanPath；正式階段須等新方案完成。
- Apply Paper Reference Parameters 會重設策略且 H=0；不要把這個值當已鎖定的正式期限。Development 的舊 PlayerPrefs 也可能覆蓋設定。
- P1 已完成 v5 個人結構／refusal／truncation 與回放檢查；P2 固定狀態 runner 已完成離線驗證；P3-A 固定情境分析已完成離線驗證；P3-B 閉迴路分析與 P4 鎖定仍待完成。已完成 24 次選擇的真實固定情境先導，正式採樣尚未開始。
- P1 改版未改場景、偏好或 key，新增合成與離線驗證；沒有真實 API。下方保留的操作屬不同歷史設計；只在對應技術用途下參考，研究設計以目前方案為準。

遊戲 Settings 已有情境／效用／模型與採樣設定，執行時自動建立欄位。Save Sampling Plan 只匯出設定；停止 Play 後重新開啟採樣視窗會讀取最新檔案。固定情境工具：**Research → Individual sampling → Open runner (no call)**；[參數、獎懲、預算及續跑操作](research/individual_agent_v1/SAMPLING_GUIDE.zh-TW.md)。

採樣後可用 [固定情境分析工具](research/individual_agent_v1/ANALYSIS_GUIDE.zh-TW.md) 匯出圖表／品質／英文摘要並自動登錄。它不呼叫 API；沒有真人或模型實證結論。

---

## 歷史操作說明（保留技術細節，不是目前正式實驗流程）

# 新版研究系統操作說明

本次只完成程式與合成資料檢查，沒有執行撤離實驗、真人行為驗證或遠端 API。`reports` 不重建，歷史結果仍封存。正式結論需等待新版實驗。

## 系統提供的條件

主選單的 Volunteer Decision 現有 OriginalGameTheory、LLM、NoVolunteers、Heuristic、RandomMatched。Heuristic 的 enum 仍保留舊名稱 MockHeuristic，避免破壞既有序列化；它是真正的規則策略，並非假冒 API 回答。

Agent Information 選單可選 Shared Context／Core (Game Inputs)。Core 只序列化公式需要的五個欄位；SharedContext 包含既有完整觀測。這是 LLM 資訊消融，原賽局公式仍只讀其所需欄位。Heuristic 本來就使用距離與全域數量，所以不能將 Core LLM vs Heuristic 解讀為「相同實際使用資訊」的純推理比較。主要機制比較與資訊消融應分開解釋。

實際搬運仍是 PaperRelocation；LegacyClearance 不參與本研究。不得啟用 LLM 中央分派。歷史記憶屬後續延伸。Inspector 的 agentPromptWording 提供 Standard／Alternate 兩個中性、語義相近的開頭，可用於措辭敏感度實驗；它不代表已證明對所有提示穩健。措辭版本納入條件 key，須各自匯出、校準與比較。

## 開發、校準與正式測試

SimulationManager Inspector 新欄位：

| 欄位 | 用途 |
|---|---|
| agentInformation | SharedContext 或 Core |
| agentPromptWording | Standard 或 Alternate 中性開頭，作措辭敏感度檢查 |
| agentResearchPhase | Development、Calibration、FinalTest |
| cooperationCalibrationPath | RandomMatched 所需的校準 JSON 路徑 |
| lockedStudyPlanPath | FinalTest 必填的鎖定方案路徑 |
| maxAgentRequestsPerRun | 0 不限；正數為總請求安全上限，達限記 invalid，不跳過行人 |
| paperDecisionReplayPath | 單次 LLM 執行的 JSONL 回放，不發 API |

Development 使用主選單偏好設定。Calibration／FinalTest 使用 Inspector 研究設定，避免舊偏好覆蓋。實驗前選取 SimulationManager，使用 **Research > Agent study > Check selected settings (no run)** 檢查，或 **Export selected condition (no run)** 匯出實體條件識別字串。這些入口不啟動模擬。

校準與測試都要求有限 maxSimulationSteps=H、PaperRelocation、無 mock fallback。FinalTest 額外檢查鎖定方案、資訊條件、策略、模型、種子、物理參數與原始碼 SHA-256。批次是 baseSeed 起算的連續種子，開始前先檢查整批資格；不在此工具替你決定適當樣本數。

正式研究中途修改參數會在下一步檢查時標記 invalid_settings_changed；請勿在 API 等待期間修改 Inspector。API 請求上限不等於美元預算，單次請求仍可能重試。

## 待授權開始實驗後的順序

1. 用 Development 的獨立開發種子做先導，確認 API 相容性、完整軌跡回放、H、成本與變異。先導不得混入最終測試。
2. 為每個物理條件與資訊條件，以 Calibration 階段執行 LLM，保存所有執行與失敗；先確定統一的重試／排除規則。
3. 以離線工具產生校準檔。單一輸入目錄必須只有一種物理條件、模型及資訊條件，且只含校準 LLM；有 invalid 時工具會拒絕，不會悄悄排除。

```powershell
py tools/agent_research.py calibrate study/calibration/core_case1 --output study/calibrations/core_case1.json
```

4. 複製 `study_plan.template.json` 為工作草案，填入已決定的模型、H、互不重疊的種子、Unity 匯出的 conditionKeys，以及所有對應 calibrationFiles。範本故意留空，不能直接執行，避免虛構校準與樣本數。
5. 鎖定方案：

```powershell
py tools/research_plan.py study/plan.draft.json --root . --output study/plan.locked.json
```

鎖定檔包含研究程式、場景、工具、套件版本、研究方案與校準檔的雜湊。改碼後需新版本方案，不能混稱同一版本結果；鎖定工具拒絕覆蓋既有輸出。

6. 在 FinalTest 分別執行各策略與資訊條件，使用相同物理條件、同一批測試種子；RandomMatched 載入對應校準檔。這是目前的手動 Unity 執行流程，並非自動付費的批次 API 管線。
7. 離線分析：

```powershell
py tools/agent_research.py analyze study/final --output study/analysis.v1.json
```

分析以條件、階段、資訊、模型與策略分組。輸出每次執行、失敗數、完成率、min(T100,H)、合作率、工時及運算紀錄；以共同種子比較差值並產生種子區塊 bootstrap 區間。重複種子、回放資料會拒絕當作獨立樣本；多次遠端重複需另定巢狀分析。

## 解讀限制

- `_agent_effort.csv` 是實際搬運者每步的投入，含等待與準備，**不含成為搬運者前的接近路程**。它不是原操作進度欄位的加總。
- 個人負擔包含所有初始行人，未協助者為零。每次執行輸出個人工時分布、最大值與平均值。
- API usage 取回應實際提供的數值；失敗請求的未知計費不自行補成零成本。現在不估算金額，費用換算需另提供有日期的價格。
- 工具提供描述性 95% 區間，沒有自動實作多重比較校正；主比較已指定，其餘標探索性，方案需如實記載。
- RandomMatched 的校準機率不保證測試軌跡合作率精確相同；需檢查實際差距，不能過度宣稱因果排除。
- 完整閉迴路驗證與 API 相容性需要之後執行功能先導。現在的通過結果只是非網路介面／資料處理檢查。

## 本次完成檢查

Unity 編譯、決策 RNG 隔離、Core 欄位隔離、校準資料不相容／種子重疊拒絕、隨機策略邊界、嚴格回放與尾端檢查、實際 MainMenu 選單接線及儲存載入檢查。Python 使用臨時合成資料測試，沒有產生新實驗結果。

## 志工沒有出現時的診斷

2026-11-09 讀取使用者執行的 82e8ac0e 批次：run001 為 RandomRoom，初始障礙沒有緊鄰出口，69 步全員撤離且 API 次數為 0；run002 有出口相鄰障礙，第 1 步送出請求後收到 401，標記 invalid_llm_api_failure。後者不是 LLM 回答不願意。歷史紀錄保留，未修改。

本次修正：401／403 等不可重試錯誤不再重送，金鑰含內部空白或包覆引號時停用遠端決策並警告；錯誤停止不再顯示成 Paused。研究模式不讀選單偏好時仍會載入本機金鑰。初始沒有出口受阻任務時，Console 會給出招募不觸發的提醒；不強制修改場景或放寬論文條件。

隔離 Unity 的 VolunteerFlowDiagnostic.Run 通過一個單步接線檢查：用注入的願意回答，驗證候選知識、正式搬運者、障礙 worker 與 UI 計數。這不是遠端 LLM 成功證明，也不是完整撤離實驗；未發 API 或輸出研究 CSV。之後需要以有效金鑰與 SingleBlockedExit 等受阻場景做真實連線確認。

測試的英文紀錄與分類資料入口已統一為 `experiment_records/EXPERIMENT_LOG.md` 及 `experiment_records/RUN_CATALOG.csv`。舊封存已移入 `experiment_records/data/historical_archive`；已完成的 tmp 功能測試與 Assets/data 執行已依目的移入同一資料根目錄。原檔名保留，搬移清單記錄來源與目的地。未完成的執行留在 Assets/data，避免搬動仍在寫入的資料。

自動英文實驗紀錄已啟用：每輪匯出後會追加至 experiment_records/EXPERIMENT_LOG.md 與 RUN_CATALOG.csv，預設原始資料直接存入 data/auto 的目的分類資料夾。Inspector 的 experimentPurpose 可填測試目的；留空時以階段、策略、場景產生客觀預設。手動重設及可正常執行退出回呼的中斷也會記錄。原手寫段落保留；系統不自動推測因果結論。

決策規格已核對並升至 paper-agent-v3：收益、觸發與邊界見 PAPER_DECISION_SPEC.md；輸出為 participate／decline_assistance。舊版記錄保留，不能直接重用為 v3 回放或校準。舊偏好值不會自動覆寫，請套用論文參考設定並選 Core。正式理解測試尚未進行。

理解測試工具已完成：停止 Play，開啟 Research > LLM comprehension > Open runner (no call)，設定模型與題數，再按 Start bounded API check 才會呼叫。8 題全部答對才通過；部分測試、取消與 API 失敗不算通過。資料與英文紀錄自動保存，使用 ASSESSMENT_CATALOG.csv，與撤離 RUN_CATALOG.csv 分開。操作說明見 COMPREHENSION_TEST_GUIDE.md。目前僅離線驗證工具，未執行真實理解測試。

研究方向已更新至 v0.4，嫁接設計見 RESEARCH_INTEGRATION_PLAN.zh-TW.md。原論文流程保留；新的意願／分派分離模式尚未啟用。這次只加入純資料契約與驗證器，不把舊 LegacyClearance 分派誤稱為新全域協調。

## S1–S2：Local 協調驗證（2026-11-10）

在 Settings 的 Coordination Mode 選 Paper Reference 或 Local Coordination；Local 必須搭配 PaperRelocation 物理模式。先選 Original Game Theory 可在不呼叫 API 下檢查流程。Apply Paper Reference Parameters 會重設回原模式。

Local 對同意且合資格的可達候選邊按接近成本貪婪配對；成本是避開障礙、走到合法相鄰格的場成本，不是秒數。預約不等於開始搬運，仍需相鄰與合法放置。撤離、任務失效、同意失效或長時間沒有改善最佳接近成本時釋放；超時後有短暫配對冷卻。預設 30／5 步，不代表保證完成。Inspector 的 AllEligibleControl 是所有合資格人可接受任務的控制假設，不能當成 LLM 或人類自願結果。

匯出新增 coordination_snapshots.jsonl、coordination_proposals.jsonl、reservation_events.csv。條件識別包含模式與預約設定，舊條件鍵不可直接沿用。驗證資料見 experiment_records/data/validation/local_coordination_v1；正式實驗尚未啟動。

## S3：最佳化分派（2026-11-11）

Coordination Mode 新增 Optimal Coordination，須搭配 PaperRelocation。它與 Local 共用快照、同意／資格、預約與物理執行。先最大化當下未預約任務的配對數，再最小化總接近成本；既有預約不被搶占，不保證整場最快。

版本 max-cardinality-min-cost-v1 寫入設定與 proposal。可用 Original Game Theory 做無 API 檢查。離線驗證入口 OptimalCoordinationValidation.Run；資料在 experiment_records/data/validation/optimal_coordination_v1。尚未開始正式比較。

## S4：LLM 分派與離線回放（2026-11-11）

Settings → Coordination Mode 現有四種選擇；LLM Coordination 須搭配 PaperRelocation。Volunteer Decision 仍控制個人意願，選擇 LLM Coordination 不會自動把意願改為 LLM。開發檢查可用 Original Game Theory；AllEligibleControl 為 Inspector 中明示的可用性控制假設。

SimulationManager Inspector 的 LLM Coordination 區塊設定 enableCoordinationLiveRequests、maxCoordinationRequestsPerRun（預設 20）、coordinationMaxOutputTokens（1024）、coordinationMaxPromptChars（60000，限制整份 payload 字元）、coordinationReplayPath。live 預設關閉。Open AI Model 沿用目前配置，不自動替換；沒有 key、被拒絕或超限都會標記 invalid，不補用 Local。個人意願的呼叫上限與分派分開計算。

離線嚴格回放：使用同一條件、種子、model、預算及 protocol，填入原本的 coordination_trace.jsonl 路徑，單次執行；不需開啟 live。回放將核對每步完整快照與 payload，遺漏、不符或多餘紀錄均使執行無效。API 延遲不算 CA 行走時間。

Research → Coordination 的 Compare recorded snapshots (offline) 可比較同一快照下 Local／最佳化／記錄中的 LLM 提案；Compare audit snapshots including failures (offline) 包含失敗步驟。兩者不呼叫 API，並自動歸檔與寫入英文 assessment 紀錄。成本差距僅在 sameCoverage=true 時有意義；缺漏／非法提案保留為失敗，合法空配對保留為覆蓋差距。

新增 coordination_requests.jsonl（開始）、coordination_trace.jsonl（輸入與回覆驗證）、coordination_application.jsonl（是否實際套用）。accepted 不等於 applied；usageReported=false 不代表測得零 tokens。中斷可能留下 pending 而沒有最終結果，不能當成功或零成本。一般自動歸檔會一起保存；測試用隔離 notebook 不會混入正式 run catalog。

本輪僅用合成回覆，未測真實 API 連線或模型分派品質。沒有新的協調 study lock 時只允許 Development；S5 鎖定流程見下節。完整規格見 COORDINATION_DISPATCH_SPEC.md。

## S5：輸入與工作鎖定（2026-11-11）

先閱讀 S5_STUDY_PROTOCOL.zh-TW.md。資料位於 research/s5/datasets，design.json 為可讀規格，schedule.jsonl 每行是一個未執行工作，coordination-study.lock.json 是不可變鎖定包。用 `python tools/coordination_study.py verify` 核對程式／場景／工具集合、內容與資料雜湊。模型名稱依目前設定固定 gpt-4o-mini；本輪沒有 API 請求或正式資料。

閉迴路使用 Research → Coordination → Configure scheduled study job (no run)，填入 lock 路徑與 schedule 中的 closed_loop jobID。它設定開啟的 SampleScene，不執行、不開啟 live。Unity 會核對每個條件、phase、seed、cap，要求自動紀錄；開始前以一次性 claim 登記。API 工作必須先配置 key／必要的 live 開關，否則拒絕開始且不 claim。不要為了試按開始而消耗正式工作槽位。

固定輸入工作可先用 `python tools/coordination_study.py claim --job JOB_ID` 登記；工具本身沒有 API client。固定分派、意願與閉迴路結果分別由 analyze-fixed、analyze-willingness、analyze-runs 讀取，均須指定 plan、phase、results；缺少預定工作時不輸出完整主要估計。比較輸入須附 jobID 並保留實際 live／no_eligible_edges 來源，不可把合成或 replay 標為模型測量。

完整 Calibration 資料齊全後，以 `pilot-gate --dispatch-results PATH --willingness-results PATH --runtime-results FOLDER` 產生 gate。預設寫入 experiment_records/study_ledgers/<planID>/pilot-gate.json；模型品質、輸入或來源不符、缺資料或 gate 未通過時，不允許 FinalTest claim／Unity 執行。Gate 驗證也會重查先導證據雜湊。尚未產生任何真實 gate。

改模型、prompt、程式、場景、期限或上限時，應保存原計畫與結果、更新設計理由並以新檔名 freeze；不覆寫已鎖定計畫。claim 過的工作即使失敗或中斷也不得偷偷重跑。現階段下一步是 S6 有界連線／先導，尚未開始正式比較。

第2／3項已實作：[單人／多人效用診斷、獨立說明審查、正式來源鎖定與分段續跑](research/individual_agent_v1/DIAGNOSTICS_AND_FORMAL.zh-TW.md)。新模型實際診斷／先導仍待執行，範本不是正式結果。
