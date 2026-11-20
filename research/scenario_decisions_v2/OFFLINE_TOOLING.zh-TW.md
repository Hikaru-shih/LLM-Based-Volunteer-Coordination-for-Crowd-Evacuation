# 隔離先導工具與離線驗證

> 2026年11月16日後續更新：原六格為抽象效用候選，物理校準與適用界線以[第2步完成說明](STAGE2_COMPLETE.zh-TW.md)為準。此頁的舊先導不可直接啟動為八格物理實驗。

2026年11月16日。已實作提示匯出、確定性順序、快照雜湊、嚴格解析與原始動作映射。11項離線測試通過，並匯出36筆診斷與120筆自由選擇的候選payload。這些是尚未發送的請求，不是156筆實驗結果。

目前有效匯出為`experiment_records/data/preparation/scenario_v2_20261116_offline_r2`。初版匯出保留為開發快照，因工具加入空白編碼表功能而由r2取代；初版不再對應目前工具SHA，不可當現行鎖定。兩者都未呼叫API。

候選transport沿用既有gpt-6-luna的temperature .15、reasoning_effort none、max_completion_tokens 220及response-v3無enum schema。這是原有設定的離線重建，未驗證目前供應端可用性，也未事前登錄。沒有更改Unity、舊production程式、已封存提示或既有資料。

驗證命令：

```powershell
python -m unittest discover -s tools -p test_scenario_decision_pilot.py -v
python tools/scenario_decision_pilot.py verify experiment_records/data/preparation/scenario_v2_20261116_offline_r2
```

工具無網路模組及API執行命令。解析會拒絕重複JSON鍵、非法動作、空白理由、截斷、工具呼叫或供應模型名稱變動；即使理由與動作矛盾，也只保留原始動作並留待標記，不自動改成另一動作。合成測試只驗證程式，不證明模型已通過語意gate。

空白理由表有156個規劃列，全部標為not_collected。原始理由、動作與標籤均留空，不把空白或預期答案當觀測。診斷q僅進入gate提示，自由選擇提示保留他人機率未知；原公式參與機率與正確動作不進入payload。

下一步仍需完成會保存失敗並停止的live transport、費用上限與事前登錄，才能執行36次理解gate。通過格式及32題非平手動作檢查後，還要覆核36筆理由，才能放行120次自由選擇。此離線交付不代表已達到API執行門檻。
