import copy
import json
import tempfile
import unittest
from pathlib import Path
from formal_sampling import BASE,FULL,assessment,freeze,verify
from individual_analysis import write_json
from payoff_review import review
from test_individual_analysis import fixture


class FormalTests(unittest.TestCase):
    def setUp(self):
        project=Path(__file__).resolve().parents[1];(project/'tmp').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=project/'tmp',prefix='formal-test-');self.root=Path(self.temp.name)
        self.pilot=self.root/'pilot';p=fixture(self.pilot,repetitions=2,outcomes={'low':[True],'high':[False]})
        for path in (self.pilot/'trials').glob('*.json'):
            t=json.loads(path.read_text());r=json.loads(t['response']);r['model']='offline-provider-v1';t['response']=json.dumps(r);write_json(path,t)
        self.plan=self.root/'plan.json';write_json(self.plan,dict(p,purpose='Formal: offline fixture',maxHttpAttempts=12))
        self.design=self.root/'design.json';write_json(self.design,dict(schema='individual-formal-design-v1',model=p['model'],promptVersion=p['promptVersion'],primaryContrast={'factor':'volunteerCost','fromValue':.05,'toValue':.1,'fixed':{'nearbyAgentCount':2,'exitNonBlockage':.5,'failureCost':.5,'unwillingness':5}},failurePolicy='retain',multiplicityPolicy='descriptive',pilotExcluded=True,modelLifecycleReviewed=True))
        for name,version,key in [('comp','paper-comprehension-v3',BASE),('diag','paper-payoff-diagnostic-v2',FULL)]:
            folder=self.root/name;folder.mkdir();(folder/'public_rules.txt').write_bytes((self.pilot/'instructions.txt').read_bytes())
            write_json(folder/'summary.json',dict(suiteVersion=version,specVersion='paper-agent-v5',model=p['model'],passed=True,totalQuestions=len(key),correct=len(key),attempted=len(key),invalid=0))
            write_json(folder/'suite_key.json',dict(questions=[]))
            rows=[]
            for identity,answer in key.items():
                body=json.dumps(dict(question_id=identity,answer=answer));r=json.dumps(dict(model='offline-provider-v1',choices=[dict(finish_reason='stop',message=dict(role='assistant',content=body))]))
                rows.append(json.dumps(dict(questionID=identity,response=r,transportSucceeded=True,requestError='')))
            (folder/'trace.jsonl').write_text('\n'.join(rows)+'\n',encoding='utf-8')
        for name in ('formal_sampling.py','individual_analysis.py','individual_sampling.py','payoff_review.py','run_formal_sampling.py','individual_study_design.py','individual_readiness.py','run_individual_study.ps1'):
            path=self.root/'tools'/name;path.parent.mkdir(exist_ok=True);path.write_bytes((project/'tools'/name).read_bytes())
        source=self.root/'Assets/scripts/Fixture.cs';source.parent.mkdir(parents=True);source.write_text('// offline fixture')
    def tearDown(self):self.temp.cleanup()
    def build(self):return freeze(self.root,self.plan,self.design,self.root/'comp',self.root/'diag',self.pilot,self.root/'bundle',2,True)
    def test_immutable_bundle_and_source(self):
        value=self.build();self.assertEqual(verify(self.root/'bundle',self.root)['lockID'],value['lockID'])
        with self.assertRaises(ValueError):self.build()
        (self.root/'Assets/scripts/Fixture.cs').write_text('changed')
        with self.assertRaises(ValueError):verify(self.root/'bundle',self.root)
    def test_undeclared_source(self):
        self.build();(self.root/'Assets/scripts/New.cs').write_text('// extra')
        with self.assertRaises(ValueError):verify(self.root/'bundle',self.root)
    def test_tampered_artifact(self):
        self.build();(self.root/'bundle/design.json').write_text('{}')
        with self.assertRaises(ValueError):verify(self.root/'bundle')
    def test_cannot_use_synthetic_pilot_for_api_lock(self):
        with self.assertRaises(ValueError):freeze(self.root,self.plan,self.design,self.root/'comp',self.root/'diag',self.pilot,self.root/'bundle',2,False)
    def test_wrong_diagnostic_answer(self):
        p=self.root/'diag/trace.jsonl';rows=[json.loads(line) for line in p.read_text().splitlines()];r=json.loads(rows[0]['response']);body=json.loads(r['choices'][0]['message']['content']);body['answer']='1';r['choices'][0]['message']['content']=json.dumps(body);rows[0]['response']=json.dumps(r);p.write_text('\n'.join(json.dumps(v) for v in rows)+'\n')
        with self.assertRaises(ValueError):self.build()
    def test_old_diagnostic_not_sufficient(self):
        p=self.root/'diag/summary.json';v=json.loads(p.read_text());v['suiteVersion']='paper-single-payoff-diagnostic-v1';write_json(p,v)
        with self.assertRaises(ValueError):self.build()
    def test_budget_and_purpose(self):
        p=json.loads(self.plan.read_text());p['maxHttpAttempts']=3;write_json(self.plan,p)
        with self.assertRaises(ValueError):self.build()
    def test_review_does_not_change_rates(self):
        before=(self.pilot/'trials/000000.json').read_bytes();rows=review(self.pilot,self.root/'review',synthetic=True)
        self.assertEqual(len(rows),4);self.assertTrue(all(r['judgment']=='unreviewed' for r in rows));self.assertEqual((self.pilot/'trials/000000.json').read_bytes(),before)
    def test_annotations_must_match_valid_trial(self):
        p=self.root/'annotations.csv';p.write_text('index,judgment,reviewer,note\n999,inconsistent,test,known mismatch\n')
        with self.assertRaises(ValueError):review(self.pilot,self.root/'review',p,True)
    def test_bad_primary_endpoint(self):
        d=json.loads(self.design.read_text());d['primaryContrast']['toValue']=.4;write_json(self.design,d)
        with self.assertRaises(ValueError):self.build()
    def test_driver_preview_and_synthetic_live_block(self):
        from run_formal_sampling import run
        self.build();args=(self.root/'bundle',self.root,self.root/'run',self.root/'unity.exe',self.root,self.root/'records')
        result=run(*args);self.assertEqual(result['estimatedSessions'],2);self.assertFalse((self.root/'run').exists())
        with self.assertRaises(ValueError):run(*args,execute=True)
    def test_review_cannot_reuse_other_run_annotation(self):
        p=self.root/'annotations.csv';p.write_text('index,judgment,reviewer,note,raw_sha256\n0,inconsistent,test,statement mismatch,'+'0'*64+'\n')
        with self.assertRaises(ValueError):review(self.pilot,self.root/'review',p,True)


if __name__=='__main__':unittest.main()
