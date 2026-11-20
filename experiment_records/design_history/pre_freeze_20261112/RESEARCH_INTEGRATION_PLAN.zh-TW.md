# 個人 agent 主線：現況、待辦與驗收

日期：2026-11-11。以 [目前研究方案 v0.5](RESEARCH_PROTOCOL.zh-TW.md) 為主。舊全域 S0–S5 已有工程／離線成果，但不能將其完成標記平移成新主線已完成。

## 可沿用的資產

| 元件 | 可沿用內容 | 本次盤點的限制 |
|---|---|---|
| PaperModelEngine / PaperObstaclePlanner | 原觸發、相鄰啟動、物理搬運與障礙狀態 | 主線須選 PaperReference，不能啟用 AllEligibleControl／全域分派 |
| OriginalGameTheoryVolunteerStrategy | 原公式、X=1／tau 邊界分支 | P1 已核對基本效用與修正行為律／單人分支；理論參考，不是人類真值 |
| PaperVolunteerPrompt / AgentObservation | v5 個人任務、Core 五欄、無 benchmark 機率 | 不含歷史；不是人格或人類校準模型 |
| LLMDecisionPolicy 個人介面 | 真實 API 呼叫、action label 檢查、失敗交由 manager invalid | P1 已接入個人 strict schema／StrictJson／envelope；Legacy 舊 parser 不參與主線；live 相容性待測 |
| PaperAgentDecisionJournal | 精確觀測與順序的回放、原始請求回覆 | Replay 不是新實驗複本；新 revision 的完整個人軌跡驗證仍要做 |
| RandomMatched / agent_research.py | 獨立校準平均參與率、seed-block 分析與負擔 | 尚無新主線校準；現有分析不是固定狀態反應曲線工具 |
| research_plan.py / AgentStudyPlan | 原碼雜湊、split、calibration 檢查 | 硬編碼 Core+SharedContext、四種策略與舊對照；新 scope／主要指標／預算需改版 |
| AutomaticExperimentLog | 一般執行／失敗按目的歸檔與英文紀錄 | P2 runner 已接入 assessment 紀錄；合成／理解／撤離結果分開 |
| 全域 Local／Optimal／LLM | 保留完整工程與歷史驗證 | 非主線；舊 S5 封存且排程停用於本研究 |

## 工作順序

| 階段 | 工作 | 驗收 | 狀態 |
|---|---|---|---|
| P0 | 明確角色、整理現況、更新 README／protocol、保存舊設計 | 新舊方向不混淆、舊 lock 在歷史 snapshot 仍可校驗 | 本次完成 |
| P1 | 複核原模型／提示並補強個人介面 | 相同觸發、Core、payoff 與修正假設可對照；共同觸發一致，X=1 原策略分支與 Agent 自主決策分清；拒絕、截斷、缺／多／重複欄位及非法 action 皆不作有效拒絕；有效回覆、失敗與 replay 合約通過 | 已完成：93 個人檢查、144 公式案例、42 理解檢查及 302 共用回歸；沒有真實 API |
| P2 | 固定狀態資料規格與批次採樣 runner | 狀態與來源版本可追溯；觸發域外不呼叫；不洩漏公式機率；有重複、配額、完整 attempt／原始 provider usage（若有）／來源紀錄；合成測試不發 API | 已完成離線：33 採樣檢查、51 Python 測試；情境編輯／額度／續跑／原始回覆與基本摘要，已完成 24 選擇的 live 格式先導；不保證完整語意理解 |
| P3-A | 固定情境個人條件反應分析 | 受控單因素曲線、逐情境機率差、單人分層、缺漏／invalid／no-game 分開、輸入與程式快照、英文報告與紀錄 | 已完成離線：79 Python 測試；17 合成情境、17 曲線、22 對比、PNG／PDF 與雜湊驗證；無真實 API |
| P3-B | 閉迴路群體結果分析 | 個人差異與撤離後果、seed／run 分塊依賴、零貢獻者工作負擔、timeout／invalid 分開；不把解釋文字當因果證據 | 舊分析基礎仍需適配；尚未完成 |
| P4 | 收斂情境、規則與新鎖定工具 | 固定模型、prompt/source、因素、主要對照、層級、H、重複數、種子、預算與失敗規則；新主線不得混入協調組／舊 split；校準前先保存 protocol 草案 | 先導前草案已完成：十情境設定、預算／主要對比與來源 audit，90 Python 測試；固定情境 lock／分段 driver／八題診斷工具已完成；實際正式 lock 仍待新模型證據與設定，閉迴路條件未完成 |
| P5 | 有界 API／理解／個人軌跡回放先導，收集獨立校準 | 參與選擇與理解分開；完整紀錄；RandomMatched 只用 calibration；依先導估變異與工作量，不因合作率或效能不利調參；修改須版本化 | 固定情境真實先導完成：10/10 理解、24 有效選擇、6 no-game、補充診斷 3/3；單人說明與模型停用需審查，群體先導／獨立校準未執行 |
| P6 | 凍結正式個人研究計畫，執行預定比較 | 校準／測試分開、每個計畫工作可追溯、無靜默替換或挑選；配對結果與固定狀態分析各自完成 | 未執行 |
| P7 | 圖表、研究結論、論文與展示 | 條件→決策→群體後果證據鏈；相關工作差異；限制、失敗及負面結果均呈現 | 未完成 |

P4 的預先規格與 P5 的校準互相銜接；若先導要求修改，保留舊草案並在正式資料揭露前以新版本完成 P6 凍結。不能在還沒校準時宣稱 RandomMatched 正式 lock 已可使用。

## 主實驗設定邊界

PaperRelocation + PaperReference + PolicyWillingness，主要比較 OriginalGameTheory 與 LLM；RandomMatched 是輔助控制，NoVolunteers 是物理負對照。Core 為主要資訊條件。共用原觸發、相鄰啟動與搬運，不讓 LLM 接管路徑或其他行人。

現在不執行全域 S5 的 934 個工作，不掛載 lockedCoordinationStudyPlanPath；舊的 lockedStudyPlanPath/template 也不得未改版即當新方案使用。本次 P1 僅改個人決策契約／程序邊界與離線驗證，不改場景或 Inspector／PlayerPrefs，不啟動正式工作。

## 舊設計的保存

原不可變 lock：`research/s5/coordination-study.lock.json`（檔案內容保留）。完整 source/data 舊 snapshot：`experiment_records/data/design_archive/global_coordination_s5_v1/`。目前文件更新後，舊 lock 對現在工作樹不再匹配是預期版本變更；歷史 snapshot 的驗證已通過。

[封存與校驗方式](experiment_records/design_history/global_coordination_s5_v1.md)。舊數據不能合併為新主線正式結果。測試數量及 480／160 等數量是各自版本的證據與素材，不是本方向已完成的實驗樣本數。


P1 保留單人 Agent 自主選擇，以 `referenceKind=ReferenceBoundary` 標記原模型特殊邊界；不強制跟原模型選同一答案。v4 硬覆寫原型封存不用。原 GTheory 單人分支與 RNG 消耗保留，六個固定原模式案例回歸通過。歷史 traces／校準／理解結果不改稱 v5。P2 已完成離線驗證；P3-A 固定情境分析也已完成離線驗證；P3-B、P4–P7、獨立先導校準與正式鎖定仍未完成。
