"""Check exported synthetic S4 fixtures independently; never invokes Unity or an API."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def check(folder):
    def single(case, suffix):
        paths = list(case.glob('*' + suffix))
        assert len(paths) == 1, (case.name, suffix, len(paths))
        return paths[0]

    def lines(case, suffix):
        return [json.loads(line) for line in single(case, suffix).read_text(encoding='utf-8-sig').splitlines()]

    def rows(case, suffix):
        with single(case, suffix).open(encoding='utf-8-sig', newline='') as stream:
            return list(csv.DictReader(stream))

    report = {'syntheticNotLiveLLM': True, 'cases': [], 'httpAttempts': 0}
    for case in sorted(p for p in folder.iterdir() if p.is_dir()):
        if not list(case.glob('*_global.csv')):
            continue  # A synthetic automatic-notebook archive is nested separately.
        total = rows(case, '_global.csv')[0]
        audit = lines(case, '_coordination_trace.jsonl')
        starts = lines(case, '_coordination_requests.jsonl')
        applications = lines(case, '_coordination_application.jsonl')
        assert len(audit) == len(starts) == len(applications)
        assert int(total['ApiRequests']) == 0 and all(a['attempts'] == 0 for a in audit)
        applied = 0
        for decision, start, application in zip(audit, starts, applications):
            snapshot = json.loads(decision['snapshot'])
            payload = json.loads(decision['payload'])
            assert start['snapshot'] == decision['snapshot']
            assert decision['protocol'] == 'coordination-dispatch-v1'
            assert payload['response_format']['json_schema']['strict'] is True
            schema = payload['response_format']['json_schema']['schema']
            assert schema['additionalProperties'] is False
            assert set(schema['required']) == {'snapshotId', 'assignments', 'explanation'}
            assert payload['model'] == 'offline-fixture' and payload['max_completion_tokens'] == 1024
            assert payload['messages'][1]['content'].endswith(decision['snapshot'])
            assert application['step'] == decision['step'] == snapshot['step']
            assert application['snapshotId'] == snapshot['snapshotId']
            if application['applied']:
                assert decision['accepted'] and not decision['error']
                proposal = json.loads(decision['content'])
                assert set(proposal) == {'snapshotId', 'assignments', 'explanation'}
                assert proposal['snapshotId'] == snapshot['snapshotId']
                agents = {a['agentId'] for a in snapshot['candidates'] if not a['evacuated'] and not a['handling']}
                tasks = {t['obstacleId'] for t in snapshot['tasks'] if not t['settled'] and not t['handled']}
                pairs = {(e['agentId'], e['obstacleId']) for e in snapshot['edges'] if e['eligible'] and e['consented']}
                assigned = proposal['assignments']
                assert len({a['agentId'] for a in assigned}) == len(assigned)
                assert len({a['obstacleId'] for a in assigned}) == len(assigned)
                assert all(a['agentId'] in agents and a['obstacleId'] in tasks and (a['agentId'], a['obstacleId']) in pairs for a in assigned)
                applied += 1
            else:
                assert application['error']
        if total['Termination'] == 'completed':
            assert applied == len(audit) == int(total['TotalSteps'])
            positions = rows(case, '_trajectories.csv')
            obstacles = rows(case, '_obstacles.csv')
            by_step = defaultdict(list)
            for obstacle in obstacles:
                by_step[int(obstacle['Step'])].append(obstacle)
            identities = {o['ObstacleID'] for o in by_step[0]}
            for step, state in by_step.items():
                blocks = {(int(o['X']), int(o['Y'])) for o in state}
                assert len(state) == len(blocks) == len(identities)
                assert {o['ObstacleID'] for o in state} == identities
                live = [(int(a['X']), int(a['Y'])) for a in positions if int(a['Step']) == step and a['Evacuated'].lower() != 'true']
                assert len(live) == len(set(live)) and not set(live) & blocks
            coordinates = {(int(a['Step']), int(a['AgentID'])): (int(a['X']), int(a['Y'])) for a in positions}
            for event in rows(case, '_obstacle_events.csv'):
                if event['Action'] == 'activate':
                    actor = coordinates[int(event['Step']) - 1, int(event['AgentID'])]
                    assert max(abs(actor[0] - int(event['X'])), abs(actor[1] - int(event['Y']))) == 1
        report['cases'].append({'case': case.name, 'termination': total['Termination'], 'stopStep': int(total['TotalSteps']), 'auditRows': len(audit), 'appliedRows': applied})

    for suffix in ('_trajectories.csv', '_obstacles.csv', '_obstacle_events.csv', '_paper_decisions.csv', '_volunteer_work.csv', '_diagnostics.csv'):
        assert single(folder / 'synthetic_capture', suffix).read_bytes() == single(folder / 'strict_replay', suffix).read_bytes()
    report['replayPhysicalFilesIdentical'] = 6
    quality = json.loads((folder / 'empty_proposal_quality.jsonl').read_text(encoding='utf-8-sig'))
    assert quality['llmValid'] and quality['coverageGap'] == 1 and not quality['sameCoverage']
    report['emptyProposalLegalitySeparatedFromQuality'] = True
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = check(args.folder)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
