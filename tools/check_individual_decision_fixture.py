"""Independently inspect synthetic P1 exports. Does not run Unity or an API."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def check(folder):
    def one(case,suffix):
        paths=list(case.glob('*'+suffix))
        assert len(paths)==1,(case.name,suffix,len(paths))
        return paths[0]
    def csvrows(case,suffix,optional=False):
        if optional and not list(case.glob('*'+suffix)):return []
        with one(case,suffix).open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))
    cases=[]
    for case in sorted(p for p in folder.iterdir() if p.is_dir() and list(p.glob('*_global.csv'))):
        total=csvrows(case,'_global.csv')[0];config=json.loads(one(case,'_config.json').read_text(encoding='utf-8-sig'))
        assert config['paperPromptVersion']=='paper-agent-v5' and config['personalResponseVersion'] in {'paper-choice-response-v1','paper-choice-response-v2','paper-choice-response-v3'}
        assert config['executionMode']=='PaperReference' and config['availabilityMode']=='PolicyWillingness'
        assert int(total['ApiRequests'])==0
        observations=csvrows(case,'_agent_observations.csv',optional=True)
        rules=sum(json.loads(row['ObservationJSON'])['nearbyAgentCount']==1 for row in observations)
        assert all(row['Source']!='reference_rule' for row in observations)
        trace=list(case.glob('*_agent_trace.jsonl'));attempts=0
        if trace:
            assert len(trace)==1
            for raw in trace[0].read_text(encoding='utf-8-sig').splitlines():
                entry=json.loads(raw);c=json.loads(entry['observation']);payload=json.loads(entry['payload'])
                assert entry['promptVersion']=='paper-agent-v5' and entry['responseValidationVersion']==config['personalResponseVersion']
                assert entry['promptTemplateHash']==config['paperPromptTemplateSHA256']
                assert entry['execution']=='synthetic_test' and entry['attempts']==0 and not entry['attemptAudit']
                assert c['nearbyAgentCount']>=1 and 0<=c['exitNonBlockage']<1
                assert set(c)=={'nearbyAgentCount','exitNonBlockage','volunteerCost','failureCost','unwillingness'}
                assert payload['response_format']['json_schema']['strict'] is True
                assert payload['max_tokens']==220 and payload['model']=='offline-personal-fixture'
                schema=payload['response_format']['json_schema']['schema']
                assert ('enum' not in schema['properties']['decision']) if config['personalResponseVersion'] in {'paper-choice-response-v2','paper-choice-response-v3'} else schema['properties']['decision']['enum']==['participate','decline_assistance']
                assert schema['additionalProperties'] is False and set(schema['required'])=={'decision','explanation'}
                assert payload['messages'][1]['content'].endswith(entry['observation'])
                assert 'exp(' not in entry['payload'] and 'synthetic-no-network' not in entry['payload']
                if entry['succeeded']:
                    envelope=json.loads(entry['response']);choice=envelope['choices'][0]
                    assert len(envelope['choices'])==1 and choice['finish_reason']=='stop'
                    assert choice['message']['role']=='assistant' and not choice['message'].get('refusal')
                    answer=json.loads(choice['message']['content'])
                    assert set(answer)=={'decision','explanation'}
                    assert answer['decision'] in {'participate','decline_assistance'}
                    assert entry['willing']==(answer['decision']=='participate') and entry['explanation']==answer['explanation'] and not entry['error']
                else:
                    assert entry['error'] and total['Termination'].startswith('invalid_llm_')
        if case.name=='single_autonomous':assert trace and rules>0
        if case.name=='matched_no_override':assert not trace and total['Termination']=='timeout'
        if total['Termination'].startswith('invalid_'):
            assert all(r['Decision']=='error' for r in csvrows(case,'_llm_decisions.csv'))
            assert not any(r['Action']=='activate' for r in csvrows(case,'_obstacle_events.csv',optional=True))
            assert all(r['Step']=='0' for r in csvrows(case,'_trajectories.csv'))
        elif case.name!='matched_no_override':
            assert total['Termination']=='completed' and int(total['EvacuatedCount'])==config['actualAgents']
            positions=csvrows(case,'_trajectories.csv');obstacles=csvrows(case,'_obstacles.csv');by_step=defaultdict(list)
            for obstacle in obstacles:by_step[int(obstacle['Step'])].append(obstacle)
            identities={o['ObstacleID'] for o in by_step[0]}
            for step,state in by_step.items():
                blocks={(o['X'],o['Y']) for o in state};live=[(a['X'],a['Y']) for a in positions if int(a['Step'])==step and a['Evacuated'].lower()!='true']
                assert len(blocks)==len(state)==len(identities) and {o['ObstacleID'] for o in state}==identities
                assert len(live)==len(set(live)) and not set(live)&blocks
            coordinates={(int(a['Step']),a['AgentID']):(int(a['X']),int(a['Y'])) for a in positions}
            for event in csvrows(case,'_obstacle_events.csv',optional=True):
                if event['Action']=='activate':
                    actor=coordinates[int(event['Step'])-1,event['AgentID']]
                    assert max(abs(actor[0]-int(event['X'])),abs(actor[1]-int(event['Y'])))==1
        cases.append(dict(case=case.name,termination=total['Termination'],step=int(total['TotalSteps']),singlePlayerRecords=rules,httpAttempts=attempts))
    for suffix in ('_trajectories.csv','_obstacles.csv','_obstacle_events.csv','_volunteer_work.csv','_diagnostics.csv'):
        assert one(folder/'synthetic_capture',suffix).read_bytes()==one(folder/'strict_replay',suffix).read_bytes()
    return dict(passed=True,cases=cases,replayPhysicalFilesIdentical=5,remoteRequests=0,formalTrials=0,syntheticNotModelEvidence=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=check(a.folder);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
