"""Plot generated Fig.3/Fig.7 comparisons (requires matplotlib).

python tools/plot_paper_validation.py <Unity tmp/paper-validation> --output reports/paper-reproduction
"""
import argparse
import csv
import json
import random
import statistics
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR",str(Path("tmp/matplotlib-cache").resolve()))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def mean_ci(values):
    rng = random.Random(2026)
    estimates = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(5000))
    return statistics.fmean(values), estimates[125], estimates[4874]


def render(source, output):
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none", "savefig.facecolor": "white"})
    curves = read(source / "figure7_analytic.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    colors = ["#2676b5", "#e58224", "#409b52"]
    for index, beta in enumerate([0.1, 0.5, 0.9]):
        for tau in [0.1, 0.9]:
            subset = [r for r in curves if abs(float(r["Beta"]) - beta) < 1e-5 and abs(float(r["Tau"]) - tau) < 1e-5]
            for axis, field in zip(axes, ["Q", "AllDefectProbability"]):
                axis.plot([int(r["X"]) for r in subset], [float(r[field]) for r in subset],
                          color=colors[index], linestyle="-" if tau == 0.1 else "--", marker="o", markersize=3,
                          label=fr"$\tau={tau},\ \beta={beta}$")
    for axis in axes:
        axis.set(xlabel="Number of players X", xlim=(2, 10), ylim=(0, 1))
        axis.grid(alpha=0.18)
    axes[0].set(ylabel="Individual defection probability q", title="Eq. (25)")
    axes[1].set(ylabel="All-defect probability q*", title="Eq. (24)")
    axes[0].legend(fontsize=8, loc="lower right")
    fig.suptitle("Fig.7 analytical reimplementation (omega = 5)")
    for extension in ["svg", "png"]:
        fig.savefig(output / f"figure7_analytic.{extension}", dpi=180)
    plt.close(fig)

    summaries = {}
    groups = [("Unweighted SFF", "figure3_exit_width_unweighted.csv"),
              ("Width-weighted SFF", "figure3_exit_width.csv")]
    for label, filename in groups:
        rows = read(source / filename)
        if len(rows) != 100:
            raise ValueError(f"Expected 100 completed runs: {filename}")
        if any(int(r["ExitAWidth2"]) + int(r["ExitBWidth4"]) != 750 for r in rows):
            raise ValueError("Incomplete Fig.3 run")
        value, low, high = mean_ci([float(r["ExitBShare"]) for r in rows])
        summaries[label] = {"runs": len(rows), "mean_wide_exit_share": value, "ci95_low": low, "ci95_high": high,
                            "mean_t100": statistics.fmean(int(r["T100"]) for r in rows)}
    values = [100 * summaries[label]["mean_wide_exit_share"] for label, _ in groups]
    lower = [values[i] - 100 * summaries[label]["ci95_low"] for i, (label, _) in enumerate(groups)]
    upper = [100 * summaries[label]["ci95_high"] - values[i] for i, (label, _) in enumerate(groups)]
    fig, axis = plt.subplots(figsize=(7, 4.2), layout="constrained")
    bars = axis.bar([label for label, _ in groups], values, color=["#9cb1c7", "#2676b5"], width=0.55,
                    yerr=[lower, upper], capsize=5)
    axis.axhline(61, color="#ba4a3d", linestyle="--", linewidth=1.3, label="Paper: about 61% (weighted)")
    axis.bar_label(bars, labels=[f"{value:.2f}%" for value in values], padding=8)
    axis.set(ylabel="Share using width-four exit B (%)", ylim=(0, 75),
             title="Fig.3 exit-width comparison: 100 runs per metric")
    axis.legend(loc="upper left", fontsize=9)
    axis.text(0.5, -0.15, "50 x 50 grid; 750 agents; exits of width 2 and 4; run-level bootstrap 95% CI",
              transform=axis.transAxes, ha="center", fontsize=8)
    for extension in ["svg", "png"]:
        fig.savefig(output / f"figure3_exit_width.{extension}", dpi=180)
    plt.close(fig)
    (output / "figure3_summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    for filename in ["figure7_analytic.csv", "figure3_exit_width.csv", "figure3_exit_width_unweighted.csv"]:
        (output / filename).write_bytes((source / filename).read_bytes())
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/paper-reproduction"))
    args = parser.parse_args()
    print(json.dumps(render(args.source, args.output), indent=2))
