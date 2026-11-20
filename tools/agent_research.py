"""Offline calibration and seed-block analysis. Never starts Unity or calls an API."""
import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from analyze_experiments import load_run, read_csv


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(folder):
    paths = sorted(Path(folder).rglob('*_config.json'))
    if not paths:
        raise ValueError('No run configurations found')
    return paths


def load(path):
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    if config.get('obstacleHandling') != 'PaperRelocation' or not config.get('conditionKey'):
        raise ValueError(f'New agent research metadata required: {path}')
    if config.get('researchPhase') == 'FinalTest' and not config.get('studyPlanID'):
        raise ValueError('FinalTest record is missing its locked study plan ID')
    row = load_run(path)  # Includes physical conservation and evacuation consistency checks.
    prefix = str(path)[:-len('_config.json')]
    return config, row, prefix


def calibrate(folder, output):
    records = []
    seeds = set()
    hashes = []
    signature = None
    invalid = []
    for path in inputs(folder):
        c, run, prefix = load(path)
        if c.get('researchPhase') != 'Calibration' or c['volunteerPolicy'] != 'LLM':
            raise ValueError('Calibration input must contain only Calibration-phase LLM runs')
        if c.get('decisionExecution') != 'live' or c.get('paperPromptVersion') != 'paper-agent-v5':
            raise ValueError('Calibration requires live v3 observations, not replay duplicates')
        key = (c['conditionKey'], c['model'], c['observationScope'], c['paperPromptVersion'])
        if signature is not None and signature != key:
            raise ValueError('One calibration file must describe exactly one condition/model/information setting')
        signature = key
        if c['seed'] in seeds:
            raise ValueError('Duplicate calibration seed; aggregate replicates explicitly before calibration')
        seeds.add(c['seed'])
        if not run['valid']:
            invalid.append(str(path))
            continue
        obs_path = Path(prefix + '_agent_observations.csv')
        observations = read_csv(obs_path) if obs_path.exists() else []
        if any(r['Source']!='api' for r in observations):
            raise ValueError('Calibration includes overridden/synthetic/non-API decisions')
        records.extend(observations)
        hashes.extend([digest(path), digest(obs_path)] if obs_path.exists() else [digest(path)])
    if invalid:
        raise ValueError(f'{len(invalid)} invalid runs present: resolve and disclose before calibration; no silent exclusion')
    if not records:
        raise ValueError('No actual participation decisions available for calibration')
    probability = sum(r['Willing'].lower() == 'true' for r in records) / len(records)
    result = dict(schema='cooperation-calibration-v1', split='Calibration', conditionKey=signature[0],
                  model=signature[1], informationCondition=signature[2], promptVersion=signature[3],
                  decisions=len(records), probability=probability, seeds=sorted(seeds), sourceHashes=hashes)
    result['calibrationID'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    write_json(output, result)
    return result


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def optional_rows(prefix, suffix):
    path = Path(prefix + suffix)
    return read_csv(path) if path.exists() else []


def run_metrics(path):
    c, run, prefix = load(path)
    horizon = int(c['maxSteps'])
    if horizon <= 0:
        raise ValueError('Agent research analysis requires a fixed positive horizon')
    valid = run['valid']
    completed = run['termination'] == 'completed'
    observations = optional_rows(prefix, '_agent_observations.csv')
    effort = optional_rows(prefix, '_agent_effort.csv')
    if len({(r['Step'], r['AgentID']) for r in effort}) != len(effort):
        raise ValueError('Duplicate active-handler effort ticks')
    # Include all initially present agents, including zero contributors and non-evacuees.
    initial = [r for r in optional_rows(prefix, '_trajectories.csv') if int(r['Step']) == 0]
    ids = {r['AgentID'] for r in initial}
    if len(ids) != int(c['actualAgents']):
        raise ValueError('Initial trajectories do not identify the full population')
    counts = Counter(r['AgentID'] for r in effort)
    if set(counts) - ids:
        raise ValueError('Effort record contains unknown agent')
    tokens = attempts = successes = 0
    latency = 0.0
    returned_models = set()
    trace = Path(prefix + '_agent_trace.jsonl')
    if trace.exists():
        for line in trace.read_text(encoding='utf-8-sig').splitlines():
            entry = json.loads(line)
            latency += entry['elapsedSeconds']
            attempts += entry['attempts']
            if entry['succeeded']:
                successes += 1
            response = json.loads(entry['response']) if entry.get('response') else {}
            tokens += (response.get('usage') or {}).get('total_tokens', 0)
            if response.get('model'):
                returned_models.add(response['model'])
    if c['volunteerPolicy']=='LLM' and any(r['Source'] not in {'api','replay'} for r in observations):
        raise ValueError('Synthetic/non-policy observations cannot be model measurements')
    policy = 'Heuristic' if c['volunteerPolicy'] == 'MockHeuristic' else c['volunteerPolicy']
    return dict(condition=c['conditionKey'], scenario=c['scenario'], phase=c['researchPhase'], study_plan=c.get('studyPlanID', ''),
                prompt_version=c.get('paperPromptVersion','unknown'),
                information=c['observationScope'], model=c.get('model', ''), policy=policy, seed=c['seed'],
                horizon=horizon, valid=valid, termination=run['termination'],
                completed=int(completed) if valid else None,
                capped_t100=(run['t100_steps'] if completed else horizon) if valid else None,
                reference_rule_decisions=sum(r['Source']=='reference_rule' for r in observations),
                api_choice_count=sum(r['Source']=='api' for r in observations),
                decision_count=len(observations),
                cooperation_rate=(sum(r['Willing'].lower() == 'true' for r in observations) / len(observations)) if observations else None,
                active_work_ticks=len(effort), max_individual_work_ticks=max(counts.values(), default=0),
                mean_individual_work_ticks=len(effort)/len(ids),
                individual_work_ticks={agent: counts[agent] for agent in sorted(ids)},
                api_attempts=attempts, successful_responses=successes, returned_models=sorted(returned_models),
                reported_total_tokens=tokens, api_wait_seconds=latency,
                calibrated_probability=c.get('calibratedProbability'), calibration_id=c.get('calibrationID', ''),
                replay=c.get('decisionExecution') == 'strict_replay', source=str(path))


def block_interval(differences, iterations=4000):
    """Input contains exactly one mean difference per seed block."""
    if len(differences) < 2:
        return None
    rng = random.Random(2026)
    samples = sorted(statistics.fmean(rng.choices(differences, k=len(differences))) for _ in range(iterations))
    return [samples[int(.025*iterations)], samples[int(.975*iterations)-1]]


def analyze(folder, output):
    rows = [run_metrics(path) for path in inputs(folder)]
    if any(r['replay'] for r in rows):
        raise ValueError('Replay records are validation, not independent research replicates')
    groups = defaultdict(list)
    for row in rows:
        groups[(row['condition'], row['phase'], row['information'], row['model'], row['study_plan'], row['prompt_version'], row['policy'])].append(row)
    summaries = []
    blocks = {}
    for key, group in sorted(groups.items()):
        by_seed = defaultdict(list)
        for row in group:
            by_seed[row['seed']].append(row)
        if any(len(values) != 1 for values in by_seed.values()):
            raise ValueError('Duplicate seed within policy/condition; nested repeats require a separate explicit analysis')
        valid = [r for r in group if r['valid']]
        summary = dict(condition=key[0], phase=key[1], information=key[2], model=key[3], study_plan=key[4], prompt_version=key[5], policy=key[6],
                       runs=len(group), invalid_runs=len(group)-len(valid),
                       terminations=dict(Counter(r['termination'] for r in group)))
        for metric in ('completed', 'capped_t100', 'active_work_ticks', 'cooperation_rate', 'api_wait_seconds', 'reported_total_tokens'):
            values = [r[metric] for r in valid if r[metric] is not None]
            summary[metric] = statistics.fmean(values) if values else None
        summaries.append(summary)
        blocks[key] = by_seed
    comparisons = []
    for key, by_seed in blocks.items():
        if key[-1] != 'LLM':
            continue
        for control in ('OriginalGameTheory', 'Heuristic', 'RandomMatched'):
            other = blocks.get((*key[:-1], control))
            if not other:
                continue
            common = sorted(set(by_seed) & set(other))
            usable = [seed for seed in common if by_seed[seed][0]['valid'] and other[seed][0]['valid']]
            for metric in ('completed', 'capped_t100', 'active_work_ticks'):
                delta = [by_seed[s][0][metric]-other[s][0][metric] for s in usable]
                comparisons.append(dict(condition=key[0], phase=key[1], information=key[2], model=key[3], study_plan=key[4], prompt_version=key[5],
                    comparison='LLM minus '+control, metric=metric, paired_valid_seeds=len(usable),
                    invalid_pairs=len(common)-len(usable), unpaired_seeds=len(set(by_seed)^set(other)),
                    mean_difference=statistics.fmean(delta) if delta else None, interval95=block_interval(delta),
                    interpretation='Conditional on both runs valid; descriptive intervals, no multiplicity correction'))
    result = dict(runs=rows, summaries=summaries, comparisons=comparisons,
                  limits=['Active work excludes walking to a task; tokens count reported successful response usage only, not unknown failed-attempt billing.',
                          'No cost in currency is estimated without dated provider pricing.',
                          'Cooperation rates may differ on test trajectories; calibrated random is not exact matching.',
                          'Intervals are descriptive. Lock primary contrasts and multiplicity treatment before final testing.'])
    write_json(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['calibrate', 'analyze'])
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite an existing output; use a new versioned path')
    try:
        (calibrate if args.command == 'calibrate' else analyze)(args.input, args.output)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
