"""Summarize fixed-state personal samples; synthetic data require explicit opt-in."""
import argparse
import csv
import json
import math
from pathlib import Path


def wilson(k, n):
    if not n:
        return None, None
    z = 1.959963984540054
    center = (k/n + z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt(k/n*(1-k/n)/n + z*z/(4*n*n))/(1+z*z/n)
    # Floating cancellation can put the bound just above p=0 (or below p=1).
    # Include the observed rate exactly so zero/all-success plots never get negative error lengths.
    return max(0, min(k/n, center-half)), min(1, max(k/n, center+half))


def probability(s):
    x, tau = s['nearbyAgentCount'], s['exitNonBlockage']
    if x == 0 or tau == 1:
        return 0.0
    if x == 1:
        return float(tau == 0)
    return 1-(-math.expm1(-s['unwillingness']*tau))**(1/x)*(s['volunteerCost']/s['failureCost'])**(1/(x-1))


def summarize(folder, allow_synthetic=False):
    plan = json.loads((folder/'plan.json').read_text(encoding='utf-8-sig'))
    assert plan['schema'] == 'individual-sampling-v1' and plan['promptVersion'] == 'paper-agent-v5'
    count = plan['repetitions']
    by_id = {s['id']: [] for s in plan['scenarios']}
    seen = set()
    synthetic = False
    for path in sorted((folder/'trials').glob('*.json')):
        t = json.loads(path.read_text(encoding='utf-8-sig'))
        i = t['index']
        assert type(i) is int and 0 <= i < len(plan['scenarios'])*count and i not in seen
        assert path.name == f'{i:06d}.json'
        seen.add(i)
        s = plan['scenarios'][i//count]
        obs = {k: v for k, v in s.items() if k != 'id'}
        assert t['scenario'] == s['id'] and t['repetition'] == i % count
        assert json.loads(t['observation']) == obs
        assert math.isclose(t['referenceProbability'], probability(s), abs_tol=2e-6)
        no_game = obs['nearbyAgentCount'] == 0 or obs['exitNonBlockage'] == 1
        assert (t['execution'] == 'no_game') == no_game
        if no_game:
            assert not t['valid'] and not t.get('payload')
        else:
            assert t['execution'] in ('api', 'synthetic_test', 'live')
            if t['execution'] == 'synthetic_test':
                synthetic = True
                if not allow_synthetic:
                    raise ValueError('Synthetic data are not model evidence; use --allow-synthetic for validation only')
            if t['valid']:
                payload = json.loads(t['payload'])
                assert payload['model'] == plan['model']
                assert payload['messages'][1]['content'].endswith(t['observation'])
                envelope = json.loads(t['response'])
                assert len(envelope['choices']) == 1
                choice = envelope['choices'][0]
                assert choice['finish_reason'] == 'stop' and not choice['message'].get('refusal')
                answer = json.loads(choice['message']['content'])
                assert set(answer) == {'decision', 'explanation'} and isinstance(answer['explanation'], str)
                assert answer['decision'] in ('participate', 'decline_assistance')
                assert t['willing'] == (answer['decision'] == 'participate') and not t.get('error')
        by_id[s['id']].append(t)
    rows = []
    for s in plan['scenarios']:
        trials = by_id[s['id']]
        valid = [t for t in trials if t['valid'] and t['execution'] != 'no_game']
        k = sum(t['willing'] for t in valid)
        low, high = wilson(k, len(valid))
        rate = k/len(valid) if valid else None
        rows.append(dict(scenario=s['id'], **{k:v for k,v in s.items() if k!='id'},
                         planned=count, saved=len(trials), missing=count-len(trials),
                         no_game=sum(t['execution']=='no_game' for t in trials),
                         invalid=sum(not t['valid'] and t['execution']!='no_game' for t in trials),
                         valid=len(valid), willing=k, rate=rate, wilson95_low=low, wilson95_high=high,
                         reference_probability=probability(s), difference=None if rate is None else rate-probability(s),
                         synthetic_validation=synthetic))
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--allow-synthetic', action='store_true')
    a = p.parse_args()
    rows = summarize(a.folder, a.allow_synthetic)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f'Saved {len(rows)} scenario rows; intervals describe repeated model outputs, not human behavior.')
