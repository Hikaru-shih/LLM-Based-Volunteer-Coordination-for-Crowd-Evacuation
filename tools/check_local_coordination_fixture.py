"""Independently verify exported bounded Local fixtures; never runs Unity or API calls."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def check(folder):
    report={'cases': []}
    initial_states=[]
    for name in ('controlled', 'game_theory', 'no_volunteers'):
        case=folder/name
        def rows(suffix):
            paths=list(case.glob('*'+suffix))
            if len(paths)>1:
                raise ValueError('Mixed run exports in a single fixture')
            if not paths:
                return []
            with paths[0].open(encoding='utf-8-sig',newline='') as stream:
                return list(csv.DictReader(stream))
        trajectories=rows('_trajectories.csv');obstacles=rows('_obstacles.csv');events=rows('_obstacle_events.csv')
        total=rows('_global.csv')[0]
        positions={(int(r['Step']),int(r['AgentID'])):(int(r['X']),int(r['Y'])) for r in trajectories}
        activations=0
        for event in events:
            if event['Action']=='activate':
                agent=positions[int(event['Step'])-1,int(event['AgentID'])]
                assert max(abs(agent[0]-int(event['X'])),abs(agent[1]-int(event['Y'])))==1, 'Nonadjacent activation'
                activations+=1
        frames=defaultdict(list)
        for row in obstacles:
            frames[int(row['Step'])].append(row)
        identities={r['ObstacleID'] for r in frames[0]}
        for step,frame in frames.items():
            assert len(frame)==len(identities) and {r['ObstacleID'] for r in frame}==identities, 'Obstacle count/identity changed'
            occupied={(int(r['X']),int(r['Y'])) for r in frame}
            assert len(occupied)==len(frame), 'Obstacle overlap'
            live=[(int(r['X']),int(r['Y'])) for r in trajectories if int(r['Step'])==step and r['Evacuated'].lower()!='true']
            assert len(set(live))==len(live) and not set(live)&occupied, 'Live occupancy overlap'
        def json_lines(suffix):
            paths=list(case.glob('*'+suffix))
            assert len(paths)==1, 'Missing/mixed snapshot or proposal files'
            return [json.loads(line) for line in paths[0].read_text(encoding='utf-8-sig').splitlines()]
        snapshots=json_lines('_coordination_snapshots.jsonl');proposals=json_lines('_coordination_proposals.jsonl')
        assert len(snapshots)==len(proposals)==int(total['TotalSteps'])
        for snapshot,proposal in zip(snapshots,proposals):
            assert proposal['snapshotId']==snapshot['snapshotId'], 'Wrong snapshot'
            pairs={(e['agentId'],e['obstacleId']) for e in snapshot['edges'] if e['eligible'] and e['consented']}
            assignments=proposal['assignments']
            assert len({a['agentId'] for a in assignments})==len(assignments)
            assert len({a['obstacleId'] for a in assignments})==len(assignments)
            assert all((a['agentId'],a['obstacleId']) in pairs for a in assignments), 'Assignment outside eligible consent graph'
        assert int(total['ApiRequests'])==0
        initial_states.append(([r for r in trajectories if r['Step']=='0'],frames[0]))
        report['cases'].append(dict(name=name,termination=total['Termination'],stopStep=int(total['TotalSteps']),
            evacuated=int(total['EvacuatedCount']),activations=activations,physicalOccupancyChecked=True,
            activationAdjacencyChecked=True,proposalEligibilityChecked=True,apiCalls=0))
    assert initial_states[0]==initial_states[1]==initial_states[2], 'Initial fixtures differ across policies'
    report['initialStatesEqual']=True
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();result=check(args.folder)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
