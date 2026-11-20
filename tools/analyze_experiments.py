"""Analyze full evacuation (T100); T90 is a secondary progress measure.

Python 3.10+, standard library only. Example:
  py tools/analyze_experiments.py tmp/offline-experiments/<timestamp> --output reports/offline-validation
"""
import argparse
import csv
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def load_run(config_path):
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    if config.get("schemaVersion") not in {"2-clearance", "3-clearance-completion", "4-paper-relocation"}:
        raise ValueError(f"Unsupported schema: {config_path}")
    prefix = str(config_path)[:-len("_config.json")]
    totals = read_csv(Path(prefix + "_global.csv"))
    if len(totals) != 1:
        raise ValueError(f"Expected one global record: {config_path}")
    total = totals[0]
    agents = read_csv(Path(prefix + "_agents.csv"))
    count = int(config["actualAgents"])
    horizon = int(config["maxSteps"])
    steps = sorted(int(row["EvacuationStep"]) for row in agents)
    ids = [int(row["AgentID"]) for row in agents]
    if len(set(ids)) != len(ids) or len(ids) > count or len(ids) != int(total["EvacuatedCount"]):
        raise ValueError(f"Inconsistent evacuation records: {config_path}")
    if any(step < 1 or (horizon > 0 and step > horizon) for step in steps):
        raise ValueError(f"Out-of-range evacuation step: {config_path}")
    valid = total["Termination"] in {"completed", "timeout"} and count > 0
    if total["Termination"] == "completed" and len(ids) != count:
        raise ValueError(f"Completed run is missing evacuees: {config_path}")
    threshold = math.ceil(count * 0.9)
    t90 = steps[threshold - 1] if threshold and len(steps) >= threshold else math.nan
    decisions_path = Path(prefix + "_llm_decisions.csv")
    decisions = read_csv(decisions_path) if decisions_path.exists() else []
    mocks = sum(row.get("Source") == "mock" for row in decisions)
    api_decisions = sum(row.get("Source") == "api" for row in decisions)
    obstacles_path=Path(prefix+"_obstacles.csv")
    states=read_csv(obstacles_path) if obstacles_path.exists() else []
    last_states=[]
    if states:
        by_step=defaultdict(list)
        for state in states:
            by_step[int(state["Step"])].append(state)
        expected=int(config.get("movableObstacles",len(by_step[min(by_step)])))
        identities={r["ObstacleID"] for r in by_step[min(by_step)]}
        for frame in by_step.values():
            if len(frame)!=expected or {r["ObstacleID"] for r in frame}!=identities or len({(r["X"],r["Y"]) for r in frame})!=expected:
                raise ValueError(f"Obstacle conservation/identity failure: {config_path}")
        last_states=by_step[max(by_step)]
    elif config.get("schemaVersion")=="4-paper-relocation" and int(config.get("movableObstacles",0))>0:
        raise ValueError(f"Missing physical obstacle history: {config_path}")
    events_path=Path(prefix+"_obstacle_events.csv")
    events=read_csv(events_path) if events_path.exists() else []
    policy = config["volunteerPolicy"]
    if policy == "LLM" and mocks:
        policy = "LLM+Mock"
    # Average individual evacuation time capped at a common fixed horizon.
    # Unfinished pedestrians contribute horizon, rather than disappearing.
    restricted_mean = (sum(steps) + (count - len(steps)) * horizon) / count if count and horizon > 0 else math.nan
    ignored = {"experimentID", "runID", "seed", "volunteerPolicy", "model", "hasApiKey", "allowMockFallback"}
    comparable = {k: v for k, v in config.items() if k not in ignored}
    signature = json.dumps(comparable, sort_keys=True, ensure_ascii=True)
    row = dict(scenario=config["scenario"], policy=policy, model=config.get("model", "") if policy.startswith("LLM") else "",
               seed=int(config["seed"]), run_id=int(config["runID"]), valid=valid, termination=total["Termination"],
               agents=count, evacuated=len(steps), evacuation_fraction=len(steps) / count if count else math.nan,
               t90_steps=t90, t100_steps=int(total["TotalSteps"]) if total["Termination"] == "completed" else math.nan,
               restricted_mean_steps=restricted_mean, api_decisions=api_decisions, mock_decisions=mocks,
               relocation_moves=sum(r["Action"] in {"push","pull","rotate"} for r in events),
               settled_obstacles=sum(r["Status"]=="Settled" for r in last_states),
               abandoned_obstacles=sum(r["Status"]=="Abandoned" for r in last_states),
               config_path=str(config_path), signature=signature)
    return row


def mean(values):
    return statistics.fmean(values) if values else math.nan


def wilson(successes, count):
    if not count:
        return math.nan, math.nan
    z = 1.959963984540054
    rate = successes / count
    denominator = 1 + z * z / count
    center = (rate + z * z / (2 * count)) / denominator
    half = z * math.sqrt(rate * (1 - rate) / count + z * z / (4 * count * count)) / denominator
    return max(0, center - half), min(1, center + half)


def bootstrap_mean(values, iterations=4000):
    if len(values) < 2:
        return math.nan, math.nan
    rng = random.Random(2026)
    estimates = sorted(mean(rng.choices(values, k=len(values))) for _ in range(iterations))
    return estimates[int(0.025 * iterations)], estimates[int(0.975 * iterations) - 1]


def summarize(runs):
    groups = defaultdict(list)
    for run in runs:
        groups[(run["scenario"], run["policy"], run["model"], run["signature"])].append(run)
    summary = []
    for (scenario, policy, model, signature), group in sorted(groups.items()):
        valid = [r for r in group if r["valid"]]
        t90 = [r["t90_steps"] for r in valid if math.isfinite(r["t90_steps"])]
        t100 = [r["t100_steps"] for r in valid if math.isfinite(r["t100_steps"])]
        low100, high100 = wilson(len(t100), len(valid))
        low, high = wilson(len(t90), len(valid))
        summary.append(dict(scenario=scenario, policy=policy, model=model, runs=len(group), valid_runs=len(valid),
                            invalid_runs=len(group) - len(valid), success90=len(t90), censored90=len(valid) - len(t90),
                            completed100=len(t100), incomplete100=len(valid) - len(t100),
                            completion100_rate=len(t100) / len(valid) if valid else math.nan,
                            completion100_ci_low=low100, completion100_ci_high=high100,
                            mean_t100_success_steps=mean(t100), sd_t100_success_steps=statistics.stdev(t100) if len(t100) > 1 else math.nan,
                            success90_rate=len(t90) / len(valid) if valid else math.nan, success90_ci_low=low, success90_ci_high=high,
                            mean_t90_success_steps=mean(t90), sd_t90_success_steps=statistics.stdev(t90) if len(t90) > 1 else math.nan,
                            mean_restricted_steps=mean([r["restricted_mean_steps"] for r in valid]),
                            mean_evacuated_fraction=mean([r["evacuation_fraction"] for r in valid]),
                            api_decisions=sum(r["api_decisions"] for r in group), mock_decisions=sum(r["mock_decisions"] for r in group),
                            signature=signature))
    return summary


def paired_comparisons(runs, baseline="OriginalGameTheory"):
    groups = defaultdict(dict)
    for run in runs:
        if not run["valid"]:
            continue
        key = (run["scenario"], run["signature"], run["seed"], run["policy"], run["model"])
        if key in groups["seen"]:
            raise ValueError("Duplicate scenario/config/seed/policy: analyze independent experiment folders separately")
        groups["seen"][key] = True
        groups[(run["scenario"], run["signature"], run["policy"], run["model"])][run["seed"]] = run
    seen = groups.pop("seen", {})
    comparisons = []
    for (scenario, signature, policy, model), group in sorted(groups.items()):
        if policy == baseline:
            continue
        control = groups.get((scenario, signature, baseline, ""), {})
        seeds = sorted(seed for seed in set(group) & set(control)
                       if math.isfinite(group[seed]["restricted_mean_steps"]) and math.isfinite(control[seed]["restricted_mean_steps"]))
        deltas = [group[seed]["restricted_mean_steps"] - control[seed]["restricted_mean_steps"] for seed in seeds]
        low, high = bootstrap_mean(deltas)
        comparisons.append(dict(scenario=scenario, policy=policy, model=model, baseline=baseline, pairs=len(seeds),
                                mean_delta_restricted_steps=mean(deltas), ci95_low=low, ci95_high=high,
                                interpretation="negative favors policy; paired percentile bootstrap; exploratory",
                                signature=signature))
    return comparisons


def write_table(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def analyze(source, output):
    files = sorted(source.rglob("*_config.json"))
    if not files:
        raise ValueError("No schema-v2 run configuration files found")
    runs = [load_run(path) for path in files]
    summary = summarize(runs)
    paired = paired_comparisons(runs)
    output.mkdir(parents=True, exist_ok=True)
    write_table(output / "runs.csv", runs)
    write_table(output / "summary.csv", summary)
    write_table(output / "paired_comparisons.csv", paired)
    title="Paper relocation-model validation" if any("4-paper-relocation" in r["signature"] for r in runs) else "Offline clearance-model validation"
    lines = ["# "+title, "",
             "These are simulation outputs, not evidence of LLM effectiveness or real-world evacuation safety.", "",
             f"Source: `{source.resolve()}`. Runs: {len(runs)}. Invalid: {sum(not r['valid'] for r in runs)}.", "",
             "Completion means ALL agents evacuated. T90 is secondary and never counts as a completed run.",
             "Restricted mean includes unfinished agents at the common maximum-step horizon; lower is better.", "",
             "| Scenario | Policy | Valid runs | All evacuated | Mean T100 (completed only) | Reached 90% | Restricted mean steps |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in summary:
        lines.append(f"| {row['scenario']} | {row['policy']} | {row['valid_runs']} | {row['completed100']} | {row['mean_t100_success_steps']:.2f} | {row['success90']} | {row['mean_restricted_steps']:.2f} |")
    lines.extend(["", "Paired comparisons match seed and physical configuration. Bootstrap intervals are exploratory; they do not correct for multiple comparisons.",
                  "No token usage or monetary API cost is inferred. Real LLM runs and robustness experiments remain necessary.", ""])
    (output / "analysis.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/experiment-analysis"))
    args = parser.parse_args()
    analyze(args.source, args.output)
    print(f"Analysis saved to {args.output}")
