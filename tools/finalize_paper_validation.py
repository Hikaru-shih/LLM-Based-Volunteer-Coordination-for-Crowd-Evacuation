"""Record verified source hashes and a human-readable reproduction report.

Run from the repository root after PaperModelValidation.RunCompleteAudit and plotting.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from analyze_experiments import bootstrap_mean, load_run, mean


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def finalize(snapshot, output):
    audit = snapshot / "tmp/paper-validation"
    result = json.loads((audit / "result.json").read_text())
    legacy = json.loads((snapshot / "tmp/research-validation/result.json").read_text())
    if not result["passed"] or not legacy["passed"]:
        raise ValueError("Unity validation did not pass")
    matrix_paths = sorted(audit.glob("runs*/matrix_result.json"))
    matrix_path = matrix_paths[-1]
    matrix = json.loads(matrix_path.read_text())
    if matrix["completed100"] != matrix["runs"]:
        raise ValueError("Incomplete paper-model runs")
    hashes = {}
    for path in sorted(Path("Assets/scripts").rglob("*.cs")):
        clone = snapshot / path
        if path.read_bytes() != clone.read_bytes():
            raise ValueError(f"Source differs from tested snapshot: {path}")
        hashes[path.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        meta = Path(str(path) + ".meta")
        clone_meta = Path(str(clone) + ".meta")
        if not meta.exists() and clone_meta.exists():
            meta.write_bytes(clone_meta.read_bytes())
    curves = read(output / "figure7_analytic.csv")
    weighted = read(output / "figure3_exit_width.csv")
    control = read(output / "figure3_exit_width_unweighted.csv")
    if len(curves) != 54 or len(weighted) != 100 or len(control) != 100:
        raise ValueError("Incomplete figure data")
    figure_summary = json.loads((output / "figure3_summary.json").read_text())
    runs = [load_run(path) for path in sorted(matrix_path.parent.glob("*_config.json"))]
    grouped = {}
    for run in runs:
        grouped.setdefault(run["scenario"], []).append(run)
    delta = [int(a["T100"]) - int(b["T100"]) for a, b in zip(weighted, control)]
    if any(a["Seed"] != b["Seed"] for a, b in zip(weighted, control)):
        raise ValueError("Figure controls are not paired by seed")
    low, high = bootstrap_mean(delta)
    verification = dict(date="2026-11-09", unity_validation=result, legacy_regression=legacy, matrix=matrix,
                        figure3_weighted_runs=100, figure3_unweighted_runs=100, figure7_points=54,
                        python_analysis_tests=8, remote_requests=0, source_matches_tested_snapshot=True,
                        source_sha256=hashes, figure3=figure_summary,
                        weighted_minus_unweighted_t100=dict(mean=mean(delta), ci95_low=low, ci95_high=high))
    (output / "verification.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
    rows = []
    names = {"OpenRoom": "單出口無障礙", "SingleBlockedExit": "單出口全堵（5 障礙）",
             "TwoExitsOneBlocked": "雙出口一堵（5 障礙）", "RandomRoom": "四出口、40 障礙"}
    for key in ["OpenRoom", "SingleBlockedExit", "TwoExitsOneBlocked", "RandomRoom"]:
        group = grouped[key]
        rows.append(f"| {names[key]} | {len(group)}/{len(group)} | {mean([r['t100_steps'] for r in group]):.2f} | {max(r['t100_steps'] for r in group):.0f} |")
    wide = figure_summary["Width-weighted SFF"]
    simple = figure_summary["Unweighted SFF"]
    text = f"""# 原模型驗證與部分圖表對照

日期：2026-11-09。Unity 6000.0.59f2。這些是重新實作模型的離線結果，不是真實人群校準或 LLM 效果證據。

## 核心模型

四種情境各 30 個配對初始種子（2026–2055），每次 50 人。PaperRelocation、Combined、PaperYielder、kS=3、kD=1、kA=5、alpha=0.3、delta=0.1、rv=6、ro=20、beta=0.01、omega=5；sigma=2（GridDistance）、tv=1，0.4 公尺格、0.3 秒一步。單／雙出口的寬度為 3，5 個前鄰格障礙完整封住八鄰域通路。

| 情境 | 全員撤離 | 平均 T100（步） | 最慢 T100（步） |
| --- | ---: | ---: | ---: |
{chr(10).join(rows)}

共 **{matrix['runs']}/{matrix['runs']} 次全員撤離**，{matrix['steps']:,} 個步驟、{matrix['obstacleMoves']:,} 次實體障礙移動。看門狗設 1,000 步，但實際最慢僅 {max(r['t100_steps'] for r in runs):.0f} 步；沒有靠放寬限制把卡死當成功。每步檢查障礙守恆、固定 ID、格子唯一性、人與障礙不重疊及移動局部性。

Unity 核對 {result['checks']:,} 項斷言（含逐代理人／逐步不變量），另通過 {legacy['assertions']} 項清除模型回歸斷言。負對照確認禁止協助的完全堵塞單出口無法撤離；工時與放棄後恢復有專門測試。Python 分析 8 項測試通過。此處的逐步斷言數量不是獨立實驗樣本數。

## Fig.3：出口寬度

50×50 格、750 人，兩個出口寬度 2 與 4；種子 2026–2125，加權與未加權各 100 次，共 200 次全員撤離。kS=3、kD=1、沒有障礙／AFF。未取得作者原始逐輪資料與種子，因此這是條件對照，不是原始數據重算。

| SFF | 寬出口 B 使用比例 | 跨輪 bootstrap 95% 區間 | 平均 T100 |
| --- | ---: | ---: | ---: |
| 未加權 | {100*simple['mean_wide_exit_share']:.2f}% | {100*simple['ci95_low']:.2f}–{100*simple['ci95_high']:.2f}% | {simple['mean_t100']:.2f} |
| 出口寬度加權 | {100*wide['mean_wide_exit_share']:.2f}% | {100*wide['ci95_low']:.2f}–{100*wide['ci95_high']:.2f}% | {wide['mean_t100']:.2f} |

原文 Fig.3 描述加權後約 61% 使用寬出口；本實作約 {100*wide['mean_wide_exit_share']:.2f}%，差約 {100*wide['mean_wide_exit_share']-61:.2f} 個百分點。這支持分流方向與接近的比例，但不證明統計等價。原文未提供該比例的信賴區間。

時間結果也須保留：本實作加權後平均 T100 比未加權多 {mean(delta):.2f} 步（配對 95% 區間 {low:.2f}–{high:.2f}）。因此不能只憑約 61% 就宣稱 Fig.3 的全部時間統計完全重現。

![出口寬度對照](figure3_exit_width.png)

## Fig.7：旁觀者效應

依式 (24)/(25)，對 X=2–10、tau=0.1/0.9、beta=0.1/0.5/0.9、omega=5 產生 54 個解析點，檢查 C# 實作與公式誤差低於 1e-5，並檢查 q 與 q* 的單調性。

![旁觀者效應解析曲線](figure7_analytic.png)

CSV 的 ExpectedWaitSteps 使用幾何分布推導的 1/(1-q*)。原文式 (26) 印成 1/q*，與其前面的級數不一致；此欄不是直接照印刷右式產生，也沒有宣稱查得正式勘誤。

## 重跑與來源

Unity 完整入口：`PaperModelValidation.RunCompleteAudit`。原始模型矩陣：`{matrix_path.parent.as_posix()}`。大型逐輪圖表研究與全部原始軌跡在同一暫存驗證專案中；本目錄保留聚合結果、圖表、逐輪 CSV 與 source SHA256。

```powershell
py tools/analyze_experiments.py <audit-output>/runs_<timestamp> --output reports/paper-reproduction/model-runs
py tools/plot_paper_validation.py <audit-output> --output reports/paper-reproduction
```

實作與模型選擇見[原模型補齊](../PAPER_MODEL_IMPLEMENTATION.zh-TW.md)。已驗證 Section II 主要機制及上述部分結果，尚未逐項重現全篇所有參數掃描、延伸跨障礙實驗或真實場域行為。
"""
    (output / "RESULTS.zh-TW.md").write_text(text, encoding="utf-8")
    return verification


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/paper-reproduction"))
    args = parser.parse_args()
    value = finalize(args.snapshot, args.output)
    print(f"Verified source snapshot, {value['matrix']['runs']} model runs and 200 figure runs")
