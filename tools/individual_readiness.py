"""Read-only preflight for the frozen individual study. Never calls an API or Unity."""
import argparse
import json
import math
from pathlib import Path
from formal_sampling import BASE, FULL, assessment, verify
from individual_analysis import audit, read, require, strict_json


def profile(payload, factual=False):
    p = strict_json(payload)
    require(p.get('model') == 'gpt-6-luna' and p.get('reasoning_effort') == 'none', 'Unexpected model/reasoning profile')
    require('max_tokens' not in p and p.get('max_completion_tokens') == (160 if factual else 220), 'Unexpected output limit')
    require(math.isclose(p.get('temperature', -1), 0 if factual else .15, abs_tol=1e-7), 'Unexpected temperature')
    require(set(p) == {'model', 'messages', 'temperature', 'max_completion_tokens', 'response_format', 'reasoning_effort'}, 'Unexpected transport fields')
    require(len(p['messages']) == 2 and [m['role'] for m in p['messages']] == ['system', 'user'], 'Unexpected history')


def workload(plan):
    n = plan['repetitions']
    require(type(n) is int and n > 0, 'Invalid repetitions')
    eligible = sum(s['nearbyAgentCount'] > 0 and s['exitNonBlockage'] < 1 for s in plan['scenarios']) * n
    total = len(plan['scenarios']) * n
    return dict(totalRecords=total, eligibleChoices=eligible, noGameRecords=total-eligible,
                maxHttpAttempts=plan['maxHttpAttempts'],
                worstCaseWilsonHalfWidth=1.959963984540054/(2*math.sqrt(n+1.959963984540054**2)))


def check(bundle, root, project=None):
    bundle, root = Path(bundle).resolve(), Path(root).resolve()
    lock = verify(bundle, root)
    require(lock['executionMode'] == 'api', 'Synthetic evidence cannot authorize the study')
    if project is not None:
        require(Path(project).resolve() != root, 'Use the isolated runtime project')
        verify(bundle, project)
    design, plan = read(bundle/'design.json'), read(bundle/'plan.json')
    require(design.get('transportProfile') == 'luna-chat-none-v1', 'Missing frozen transport profile')
    require(design.get('scope') == 'Fixed-state only', 'Unexpected study scope')
    require(design.get('analysisMode') == 'descriptive_pointwise_no_confirmatory_tests', 'Analysis policy changed')
    require(design.get('repetitionsLocked') is True and plan['repetitions'] == 100, 'Precision plan not frozen')
    levels = {(s['nearbyAgentCount'], s['exitNonBlockage'], s['volunteerCost'])
              for s in plan['scenarios'] if s['id'].startswith('main_')}
    expected = {(x, t, c) for x in (2, 5, 10) for t in (0, .5, .9) for c in (.005, .05, .2)}
    require(levels == expected and len(plan['scenarios']) == 32, 'Frozen scenario coverage changed')
    require(all(s['failureCost'] == .5 and s['unwillingness'] == 5 for s in plan['scenarios']), 'Fixed factors changed')
    provider = lock['expectedProviderModel']
    for name, version, key in [('comprehension', 'paper-comprehension-v3', BASE), ('diagnostic', 'paper-payoff-diagnostic-v2', FULL)]:
        folder = bundle/'prerequisites'/name
        require(assessment(folder, version, key, plan['model']) == provider, 'Prerequisite provider drift')
        for line in (folder/'trace.jsonl').read_text(encoding='utf-8-sig').splitlines():
            if line.strip():
                profile(strict_json(line)['payload'], factual=True)
    data = audit(bundle/'prerequisites/pilot')
    require(not data['plan']['purpose'].startswith('Formal:'), 'Pilot/test leakage')
    require(all(r['invalid'] == r['missing'] == 0 for r in data['rows']), 'Pilot incomplete')
    for path in (bundle/'prerequisites/pilot/trials').glob('*.json'):
        trial = read(path)
        if trial['execution'] != 'no_game':
            profile(trial['payload'])
    if design.get('transport',{}).get('responseProtocol')=='paper-choice-response-v3':
        from semantic_release_gate import evaluate
        require(evaluate(bundle/'prerequisites/semantic')['passed'], 'Frozen v3 semantic gate failed')
    work = workload(plan)
    require(work['eligibleChoices'] == 3000 and work['noGameRecords'] == 200 and work['maxHttpAttempts'] == 9000, 'Workload changed')
    return dict(schema='individual-preflight-v1', ready=True, readyScope='fixed_state_only',
                closedLoopReady=False, remoteRequests=0, lockID=lock['lockID'], model=plan['model'],
                providerModel=provider, transportProfile=design['transportProfile'],
                aliasSnapshotLimitation=True, sourceVerified=True, runtimeVerified=project is not None,
                rulesCorrect=10, payoffCorrect=8, pilotExcluded=True,
                sessionChoices=lock['sessionChoices'], estimatedSessions=math.ceil(work['eligibleChoices']/lock['sessionChoices']), **work)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--project-root', type=Path)
    p.add_argument('--report', type=Path)
    a = p.parse_args()
    result = check(a.bundle, a.root, a.project_root)
    if a.report:
        require(not a.report.exists(), 'Keep the previous readiness report')
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
