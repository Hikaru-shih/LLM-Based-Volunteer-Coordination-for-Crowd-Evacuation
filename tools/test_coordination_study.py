import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
import coordination_study as study


class CoordinationStudyTests(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).resolve().parents[1]/'tmp';scratch.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='s5test_',dir=scratch);self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        folder=self.root/'research/s5/datasets';folder.mkdir(parents=True)
        conditions=[dict(cellId='SingleBlockedExit_n8',groupId=g,conditionKey='key_'+g,executionMode='PaperReference',availabilityMode='PolicyWillingness',policy='OriginalGameTheory',information='Core') for g in sorted(study.GROUPS)]
        study.write(folder/'conditions.json',dict(model='fixture',horizon=200,cells=[dict(cellId='SingleBlockedExit_n8')],conditions=conditions))
        snapshots=[]
        for split,seeds in study.SPLITS.items():
            for seed in seeds:
                for source in ('A1','A2'):
                    for checkpoint in (1,10):
                        key=f'{split}_{seed}_{source}_{checkpoint}'
                        snapshots.append(dict(recordId=key,split=split,seed=seed,cellId='SingleBlockedExit_n8',sourcePolicy=source,checkpoint=checkpoint,
                                              referenceLocalCount=1,referenceOptimalCount=1,referenceOptimalCost=1,
                                              snapshot=dict(snapshotId=key,step=checkpoint,candidates=[dict(agentId=0)],tasks=[dict(obstacleId=0)],edges=[dict(agentId=0,obstacleId=0,approachCost=1)])))
        study.jsonl(folder/'snapshots.raw.jsonl',snapshots)
        contexts=[]
        for n in (1,2,4,8,16):
            for tau in (0,.25,.5,.75):
                for cv in (.005,.1):
                    for av in (.5,.8):
                        for omega in (1,5):
                            c=dict(nearbyAgentCount=n,exitNonBlockage=tau,volunteerCost=cv,failureCost=av,unwillingness=omega)
                            observation=study.canonical(c);probability=(1 if tau==0 else 0) if n==1 else 1-(1-math.exp(-omega*tau))**(1/n)*(cv/av)**(1/(n-1))
                            contexts.append(dict(recordId=hashlib.sha256(observation.encode()).hexdigest(),observation=observation,referenceProbability=probability,**c))
        study.jsonl(folder/'willingness.raw.jsonl',contexts)
        for name in ('Assets/scripts/example.cs','Assets/Scenes/test.unity','tools/tool.py','Packages/manifest.json','ProjectSettings/ProjectVersion.txt','RESEARCH_PROTOCOL.zh-TW.md','RESEARCH_INTEGRATION_PLAN.zh-TW.md','COORDINATION_DISPATCH_SPEC.md','S5_STUDY_PROTOCOL.zh-TW.md'):
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture',encoding='utf-8')
        self.design=study.prepare(self.root);self.plan=self.root/'research/s5/lock.json';study.freeze(self.root,self.plan)

    def test_frozen_inputs_and_stratification(self):
        _,p=study.verify(self.plan,self.root);self.assertEqual(p['model'],'fixture')
        groups=[]
        for split,count in (('Development',40),('Calibration',40),('FinalTest',80)):
            rows=study.lines(self.root/f'research/s5/datasets/{split}.willingness.jsonl');self.assertEqual(len(rows),count);groups.append({r['observation'] for r in rows})
        self.assertFalse(groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])

    def test_source_drift(self):
        (self.root/'Assets/scripts/example.cs').write_text('changed');self.assertRaises(ValueError,study.verify,self.plan,self.root)

    def test_new_source_not_silently_allowed(self):
        (self.root/'Assets/scripts/new.cs').write_text('new behavior');self.assertRaises(ValueError,study.verify,self.plan,self.root)

    def test_dataset_drift(self):
        (self.root/'research/s5/datasets/FinalTest.snapshots.jsonl').write_text('changed');self.assertRaises(ValueError,study.verify,self.plan,self.root)

    def test_payload_tamper(self):
        value=study.read(self.plan);value['payloadJson']+=' ';study.write(self.plan,value);self.assertRaises(ValueError,study.verify,self.plan,self.root)

    def test_immutable_lock(self):self.assertRaises(ValueError,study.freeze,self.root,self.plan)

    def test_seed_overlap(self):
        p=copy.deepcopy(self.design);p['testSeeds'][0]=p['developmentSeeds'][0];self.assertRaises(ValueError,study.validate_payload,p)

    def test_duplicate_job(self):
        p=copy.deepcopy(self.design);p['jobs'].append(p['jobs'][0]);self.assertRaises(ValueError,study.validate_payload,p)

    def test_aggregate_budget(self):
        p=copy.deepcopy(self.design);p['budgets']['maxHttpAttempts']+=1;self.assertRaises(ValueError,study.validate_payload,p)

    def test_claim_once(self):
        job=self.design['jobs'][0]['jobID'];study.claim(self.plan,self.root,job,self.root/'ledger');self.assertRaises(FileExistsError,study.claim,self.plan,self.root,job,self.root/'ledger')

    def test_unscheduled_claim(self):self.assertRaises(ValueError,study.claim,self.plan,self.root,'not_scheduled',self.root/'ledger')

    def test_final_claim_requires_pilot(self):
        job=next(j for j in self.design['jobs'] if j['phase']=='FinalTest')
        self.assertRaises(FileNotFoundError,study.claim,self.plan,self.root,job['jobID'],self.root/'ledger')

    def test_gate_checksum_and_evidence(self):
        lock,_=study.verify(self.plan,self.root);source=self.root/'pilot.jsonl';source.write_text('{}')
        payload=study.canonical(dict(schema='coordination-pilot-gate-v1',planID=lock['planID'],passed=True,inputFiles=[dict(path='pilot.jsonl',sha256=study.sha(source))]))
        gate=self.root/'gate.json';study.write(gate,dict(schema='coordination-pilot-gate-lock-v1',gateID=hashlib.sha256(payload.encode()).hexdigest(),payloadJson=payload))
        self.assertTrue(study.verify_gate(gate,lock['planID'],self.root)['passed'])
        source.write_text('changed');self.assertRaises(ValueError,study.verify_gate,gate,lock['planID'],self.root)

    def measurements(self,**override):
        rows=[]
        for j in self.design['jobs']:
            if j['kind']=='fixed_dispatch' and j['phase']=='FinalTest':rows.append(dict(jobID=j['jobID'],execution='live',llmValid=True,llmCount=1,llmCost=1,localCount=1,optimalCount=1,**override))
        return rows

    def analyze(self,rows):
        path=self.root/'results.jsonl';study.jsonl(path,rows);return study.analyze_fixed(self.plan,self.root,path,'FinalTest')

    def test_complete_seed_block_analysis(self):
        r=self.analyze(self.measurements());self.assertEqual(r['seedBlocks'],12);self.assertEqual(r['primaryMeanDifference'],0);self.assertEqual(r['interval95'],[0,0]);self.assertEqual(r['equalCoverageCostGapMean'],0)

    def test_missing_not_silently_excluded(self):
        r=self.analyze(self.measurements()[:-1]);self.assertIsNone(r['primaryMeanDifference']);self.assertEqual(r['missing'],1)

    def test_invalid_operational_coverage(self):
        rows=self.measurements()
        for r in rows:r['llmValid']=False;r['llmCount']=-1
        result=self.analyze(rows);self.assertEqual(result['primaryMeanDifference'],-1);self.assertEqual(result['invalid'],len(rows));self.assertIsNone(result['equalCoverageCostGapMean'])

    def test_synthetic_not_observation(self):
        rows=self.measurements();rows[0]['execution']='synthetic_test';self.assertRaises(ValueError,self.analyze,rows)

    def test_duplicate_result(self):
        rows=self.measurements();self.assertRaises(ValueError,self.analyze,rows+[rows[0]])

    def test_frozen_oracle_cannot_change(self):
        rows=self.measurements();rows[0]['optimalCount']=2;self.assertRaises(ValueError,self.analyze,rows)

    def test_zero_graph_cannot_claim_nonzero_oracle(self):
        rows=self.measurements();rows[0]['execution']='no_eligible_edges';self.assertRaises(ValueError,self.analyze,rows)

    def test_oracle_cost_lower_bound(self):
        rows=self.measurements();rows[0]['llmCost']=0;self.assertRaises(ValueError,self.analyze,rows)

    def test_no_data_not_a_result(self):
        result=self.analyze([]);self.assertFalse(result['complete']);self.assertEqual(result['observed'],0);self.assertIsNone(result['interval95'])

    def test_willingness_invalid_not_decline(self):
        jobs=[j for j in self.design['jobs'] if j['kind']=='fixed_willingness' and j['phase']=='FinalTest']
        path=self.root/'will.jsonl';study.jsonl(path,[dict(jobID=j['jobID'],execution='live',valid=False) for j in jobs]);r=study.analyze_willingness(self.plan,self.root,path,'FinalTest')
        self.assertEqual(r['invalid'],80);self.assertIsNone(r['meanDifferenceFromFormula'])

    def test_runtime_no_data_not_a_result(self):
        r=study.analyze_runs(self.plan,self.root,self.root/'no_runs','FinalTest');self.assertFalse(r['complete']);self.assertTrue(all(c['mean'] is None for c in r['comparisons']))


if __name__=='__main__':unittest.main()
