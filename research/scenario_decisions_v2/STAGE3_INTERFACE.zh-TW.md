# 第3步決策介面與API工具完成說明

2026年11月16日。已完成兩層個人決策介面、提示與觀測、嚴格回覆解析、意願映射、API呼叫工具、逐筆紀錄、理由表與階段放行檢查。本步沒有呼叫API或新增Unity模擬，也未更動原正式系統與P-028封存。

## 兩層任務的區分

| 任務 | 提供資訊 | 不做的推論 |
|---|---|---|
| 原模型抽象效用比較 | 原六格cv及av、X、τ、ω，數值或語意等價措辭 | 不把分數稱為秒數、重量或傷亡機率 |
| 物理情境且只有布局資訊 | 八個B與M設定、人口10、總障礙5、H300 | 不提供或虛構未來時間 |
| 物理情境且提供校準預測 | 相同布局，另提供四個條件的自己及其餘九人時間估計 | 不把估計當本輪確定結果，不套用原公式成本 |

所有任務都只有自己的participate與decline_assistance，不指揮其他人。沒有跨請求記憶或人格。物理任務的ID0固定為焦點行人，不挑選比較容易產生利他結果的人。

物理預測逐格讀取第2步原始1740筆行人紀錄，重新核對各來源job，計算6種子的平均、觀察最小及最大值。自己與其他人的時間分開呈現，沒有公共效益獎金。提示說明八鄰域、M是單位工作進度間隔、時間單位是模擬步數，非真實秒數。第300步仍未撤離者記300；區間是觀察範圍，不是信賴區間。

四個條件為自己願意或拒絕，搭配其他九人全部不願意或全部願意。其他人願意不等於實際搬運，也不等於只有一人願意。混合意願尚未校準，提示不供應其機率，不任意插值。明示這些是較早開發種子的估計，而非目前個案未來資訊。

這是一項資訊條件比較：預測組比布局組多了定量結果資訊。因此不能把兩組差異直接歸因於同資訊下的推理能力。這也不是已證實的人類決策模型。

## 診斷與自由選擇隔離

抽象診斷有18種規格，明確給定其他人全部拒絕的聯合機率，並要求比較風險中性預期效用。其中8題協助較高、8題拒絕較高、2題平手。自由選擇不提供這個機率、不要求重現原公式，也沒有唯一正確選擇標籤。

物理診斷有16種規格，固定一個他人意願背景，要求讀取所提供的自己平均截尾撤離步數並選較低者。這是預測表閱讀與動作映射檢查，不是評分自由選擇的利他性，也不是驗證時間預測能準確外推。

目前匯出62種介面規格：18抽象診斷、16物理診斷、12抽象自由選擇及16物理自由選擇。每種只有一份完整payload供檢查，並未送出，不是62筆模型結果，也不是已凍結的正式樣本數。原156筆舊匯出仍獨立保留，不能冒充新版物理情境。

## API與輸出協定

沿用既有候選設定gpt-6-luna、temperature .15、reasoning_effort none、max_completion_tokens 220及response-v3。schema先explanation再decision，decision在schema中不使用enum，但本地只接受兩個合法動作。每次只有一則system與一則user訊息。

模型目前的帳戶可用性及這組參數的供應端支援尚未以live請求驗證。工具不替換模型、不放寬格式、不在截斷時擴增token重試。若供應端不接受，第一筆失敗會保存並停止，須另記錄版本決策。220是每筆輸出上限，不是費用金額保證。

API格式依[OpenAI Chat Completions文件](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)與[Structured Outputs文件](https://developers.openai.com/api/docs/guides/structured-outputs)核對。研究刻意採單次嘗試與錯誤即停；不使用SDK自動重試。[官方錯誤碼說明](https://developers.openai.com/api/docs/guides/error-codes)列出的錯誤仍需另行處理，不能自行當作拒絕協助。

## 動作與原始紀錄

每筆保存請求payload雜湊、發送前claim、client request ID、HTTP狀態、供應request ID、原始回覆檔、解析動作、理由、willing旗標及本地耗時。耗時不視為純服務端延遲。發送前claim是保留名額，不等於確定收到供應端回覆；網路逾時不自動重送。

重複JSON鍵、非法動作、空白理由、拒答、截斷、工具呼叫、模型名稱變動或同批重複provider ID都不能通過。理由偏向拒絕但動作是協助時，保留協助動作供理由矛盾分析，不推測正確動作來覆寫。型別化的consume介面只輸出個人意願，不執行格網移動。未把新版任務直接塞入舊Unity即時遊玩選單或替換正式策略。

一般回覆原樣保存；若回覆意外包含所用金鑰，會遮蔽敏感字串、標示secretRedacted並判為無效。Authorization標頭與金鑰不進紀錄或控制台。金鑰只在明確live執行時讀取，匯出、登錄、驗證與合成測試均不讀取。

## 登錄與放行

register命令先驗證介面來源、情境、payload及順序，再建立新檔，禁止覆寫；它本身不呼叫API。登錄記錄階段、重複次數、順序種子、精確請求、最多嘗試數、輸出token總上限、payload總bytes及時間上限。費用依供應端計價，不虛構目前美元上限。

run必須指定登錄檔、新輸出資料夾及confirm-live，才可能呼叫。開始後的資料夾與逐筆claim阻止自動恢復、補滿或重跑。失敗與逾時不當成不協助，也不刪除；每個真實campaign開始、完成或停止會自動追加英文研究筆記，保留既有自動紀錄區。突然斷電等情況可能只留下開始與claim，這時須檢查，不能宣稱已送達或自動續跑。

抽象自由選擇需先有同介面版本的live抽象診斷與全部理由覆核；物理自由選擇另需物理診斷。放行會重讀原始回覆、重算動作、檢查每筆review雜湊、原文、動作及比較判斷。單純完成呼叫、不具名的passed旗標、未覆核理由或合成測試都不能代替語意通過。這是助理可執行的覆核程序，不宣稱獨立真人評分。

## 驗證結果

27項新版契約與transport測試、11項舊匯出器回歸通過。測試涵蓋來源篡改、預測重算、答案隔離、平手、解析與動作不修補、HTTP錯誤、網路結果不明、重複ID、停止與不覆寫、禁止合成偽裝live、未通gate不能登錄自由選擇，以及固定endpoint單次請求。

另保存16筆合成回覆的完整round-trip，8協助與8拒絕，驗證consume意願映射；再保存1個合成HTTP429錯誤，確認只嘗試一次並保留錯誤。這些數字全是程式測試，不能算成LLM協助率或模型通過診斷。沒有新增Unity測試。

## 檔案與操作

核心為tools/scenario_agent_contract.py；實際呼叫與登錄為tools/scenario_agent_transport.py；測試為tools/test_scenario_agent_interface.py；持久化合成檢查為tools/validate_scenario_stage3_pipeline.py。

介面匯出在experiment_records/data/preparation/scenario_agent_stage3_20261116；合成驗證在experiment_records/data/validation/scenario_agent_stage3_20261116。兩者都與正式資料分開。

以下命令只驗證，不讀金鑰、不呼叫API：

```powershell
python tools/scenario_agent_contract.py verify experiment_records/data/preparation/scenario_agent_stage3_20261116
python -m unittest discover -s tools -p test_scenario_agent_interface.py -v
```

第3步完成的是決策層工具與介面，不是第5步的live行為驗證。下一步先將第4步理由分類對齊兩層任務，再鎖定先導取樣與登錄；只有之後的實際診斷，才會知道供應端相容性與LLM是否依規則改變選擇。沒有因離線測試成功而宣稱新系統已產生有效LLM研究結果。
