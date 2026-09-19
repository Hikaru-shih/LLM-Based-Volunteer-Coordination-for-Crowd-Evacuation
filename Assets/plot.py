import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = "data"
OUT_DIR = "figures"
os.makedirs(OUT_DIR, exist_ok=True)


# =========================
# 找 csv
# =========================
def find_csv(folder):
    files = glob.glob(os.path.join(folder, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No csv found in {folder}")
    return files[0]


# =========================
# 讀 batch summary
# =========================
def read_summary(csv_path):
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("BatchSize,Strategy"):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(f"Cannot find summary table in {csv_path}")

    df = pd.read_csv(csv_path, skiprows=header_idx)

    row = df.iloc[0]

    def get_value(possible_cols, default=0.0):
        for col in possible_cols:
            if col in df.columns:
                return row[col]
        return default

    avg_steps = float(get_value(["AvgSteps", "AverageSteps", "avg_steps"]))
    std_steps = float(get_value(["StdSteps", "StepStd", "std_steps"]))

    t90 = float(get_value(["T90", "T90Steps", "EvacuationT90", "T90EvacuationSteps"], avg_steps))
    t95 = float(get_value(["T95", "T95Steps", "EvacuationT95", "T95EvacuationSteps"], avg_steps))

    batch_size = float(get_value(["BatchSize"], 0))

    failed_runs = float(get_value(["FailedRuns", "FailRuns", "FailureCount"], 0))

    failure_rate = get_value(["FailureRate", "FailRate"], None)

    if failure_rate is None:
        failure_rate = failed_runs / batch_size * 100 if batch_size > 0 else 0
    else:
        failure_rate = float(failure_rate)
        if failure_rate <= 1:
            failure_rate *= 100

    return {
        "avg_steps": avg_steps,
        "std_steps": std_steps,
        "t90": t90,
        "t95": t95,
        "failed_runs": failed_runs,
        "failure_rate": failure_rate
    }


# =========================
# 收集資料
# =========================
records = []

folders = [
    f for f in os.listdir(DATA_DIR)
    if os.path.isdir(os.path.join(DATA_DIR, f))
]

for folder_name in folders:
    try:
        exit_count, agent_count, obstacle_count, model_id = map(int, folder_name.split("-"))
    except ValueError:
        continue

    folder = os.path.join(DATA_DIR, folder_name)

    try:
        csv_path = find_csv(folder)
        summary = read_summary(csv_path)
    except Exception as e:
        print(f"Skip {folder_name}: {e}")
        continue

    model = "Original" if model_id == 0 else "LLM"

    records.append({
        "folder": folder_name,
        "exit_count": exit_count,
        "agent_count": agent_count,
        "obstacle_count": obstacle_count,
        "model": model,
        **summary
    })

df = pd.DataFrame(records)

if df.empty:
    raise RuntimeError("No valid experiment data found.")

df = df.sort_values(["exit_count", "agent_count", "obstacle_count", "model"])
df.to_csv(os.path.join(OUT_DIR, "combined_results.csv"), index=False)

print("\nCombined Results:")
print(df)


# =========================
# 圖1：T90 Performance
# =========================
plt.figure(figsize=(8, 5))

for model in ["Original", "LLM"]:
    sub = df[df["model"] == model].sort_values("agent_count")
    plt.plot(
        sub["agent_count"],
        sub["t90"],
        marker="o",
        label=model
    )

plt.xlabel("Agent Count")
plt.ylabel("T90 Evacuation Steps")
plt.title("T90 Evacuation Performance")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "t90_performance.png"), dpi=300)
plt.close()


# =========================
# 圖2：Average Steps Performance
# =========================
plt.figure(figsize=(8, 5))

for model in ["Original", "LLM"]:
    sub = df[df["model"] == model].sort_values("agent_count")
    plt.plot(
        sub["agent_count"],
        sub["avg_steps"],
        marker="o",
        label=model
    )

plt.xlabel("Agent Count")
plt.ylabel("Average Evacuation Steps")
plt.title("Average Evacuation Steps")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "avg_steps_performance.png"), dpi=300)
plt.close()


# =========================
# 圖3：Improvement by T90
# =========================
improve_records = []

group_keys = ["exit_count", "agent_count", "obstacle_count"]

for key, group in df.groupby(group_keys):
    if set(group["model"]) != {"Original", "LLM"}:
        continue

    original = group[group["model"] == "Original"]["t90"].values[0]
    llm = group[group["model"] == "LLM"]["t90"].values[0]

    improvement = (original - llm) / original * 100 if original > 0 else 0

    improve_records.append({
        "exit_count": key[0],
        "agent_count": key[1],
        "obstacle_count": key[2],
        "improvement": improvement
    })

improve_df = pd.DataFrame(improve_records)
improve_df = improve_df.sort_values("agent_count")
improve_df.to_csv(os.path.join(OUT_DIR, "t90_improvement.csv"), index=False)

plt.figure(figsize=(8, 5))

plt.bar(
    improve_df["agent_count"].astype(str),
    improve_df["improvement"]
)

plt.axhline(0, linewidth=1)
plt.xlabel("Agent Count")
plt.ylabel("LLM Improvement over Original (%)")
plt.title("T90 Improvement")
plt.grid(True, axis="y")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "t90_improvement.png"), dpi=300)
plt.close()


# =========================
# 圖4：Stability
# =========================
plt.figure(figsize=(8, 5))

agents = sorted(df["agent_count"].unique())
x = range(len(agents))
width = 0.35

original_std = []
llm_std = []

for a in agents:
    original_row = df[(df["agent_count"] == a) & (df["model"] == "Original")]
    llm_row = df[(df["agent_count"] == a) & (df["model"] == "LLM")]

    original_std.append(original_row["std_steps"].values[0] if not original_row.empty else 0)
    llm_std.append(llm_row["std_steps"].values[0] if not llm_row.empty else 0)

plt.bar([v - width / 2 for v in x], original_std, width, label="Original")
plt.bar([v + width / 2 for v in x], llm_std, width, label="LLM")

plt.xticks(x, [str(a) for a in agents])
plt.xlabel("Agent Count")
plt.ylabel("Std Steps")
plt.title("Stability Comparison")
plt.legend()
plt.grid(True, axis="y")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "stability.png"), dpi=300)
plt.close()


# =========================
# 圖5：Failure Rate
# =========================
plt.figure(figsize=(8, 5))

original_fail = []
llm_fail = []

for a in agents:
    original_row = df[(df["agent_count"] == a) & (df["model"] == "Original")]
    llm_row = df[(df["agent_count"] == a) & (df["model"] == "LLM")]

    original_fail.append(original_row["failure_rate"].values[0] if not original_row.empty else 0)
    llm_fail.append(llm_row["failure_rate"].values[0] if not llm_row.empty else 0)

plt.bar([v - width / 2 for v in x], original_fail, width, label="Original")
plt.bar([v + width / 2 for v in x], llm_fail, width, label="LLM")

plt.xticks(x, [str(a) for a in agents])
plt.xlabel("Agent Count")
plt.ylabel("Failure Rate (%)")
plt.title("Failure Rate Comparison")
plt.legend()
plt.grid(True, axis="y")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "failure_rate.png"), dpi=300)
plt.close()


# =========================
# 圖6：T95 Performance
# =========================
plt.figure(figsize=(8, 5))

for model in ["Original", "LLM"]:
    sub = df[df["model"] == model].sort_values("agent_count")
    plt.plot(
        sub["agent_count"],
        sub["t95"],
        marker="o",
        label=model
    )

plt.xlabel("Agent Count")
plt.ylabel("T95 Evacuation Steps")
plt.title("T95 Evacuation Performance")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "t95_performance.png"), dpi=300)
plt.close()


print("\nDone. Figures saved in 'figures/'")