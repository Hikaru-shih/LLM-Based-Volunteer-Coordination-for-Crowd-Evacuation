"""Prospective formal-design invariants and offline adapter checks, no API."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import scenario_agent_contract as c
import scenario_agent_transport as t
import scenario_formal as f
import scenario_formal_analysis as a

class FormalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=c.read(f.BUNDLE/'cases.json');cls.d=f.design();cls.trials=f.make_trials(cls.cases,cls.d)
        cls.reference={x['cell']:x['referenceProbability'] for x in c.read(c.DESIGN/'pilot-plan.draft.json')['cells']}
    def setUp(self):self.temp=tempfile.TemporaryDirectory(dir=c.ROOT/'tmp',prefix='formal-guard-test-');self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def lock(self):folder=self.root/'lock';f.freeze(folder);return folder
    def test_all_conditions_in_every_block_and_new_ids(self):
        self.assertEqual(len(self.trials),840);self.assertEqual(len({x['trialID'] for x in self.trials}),840)
        for b in range(1,31):self.assertEqual(len({x['case']['caseID'] for x in self.trials if x['block']==b}),28)
        self.assertTrue(all(x['trialID'].startswith(f.CAMPAIGN) for x in self.trials))
    def test_reproducible_order(self):self.assertEqual(self.trials,f.make_trials(self.cases,self.d))
    def test_primary_sign_and_reference_adjustment(self):
        y={x['trialID']:int(x['case']['information']!='calibrated_forecast') for x in self.trials}
        blocks=a.contrasts(self.trials,y,self.reference)
        delta=self.reference['A30_R10']-self.reference['A30_R90']
        self.assertTrue(all(abs(x['primaryA']-delta)<1e-12 and x['primaryB']==-1 for x in blocks))
    def test_intervals_are_reproducible_and_constant_when_constant(self):
        blocks=[{'block':i,'primaryA':.25,'primaryB':-.5} for i in range(30)]
        r=a.intervals(blocks);self.assertEqual(r,a.intervals(blocks));self.assertEqual(r['primaryB']['pointwiseDescriptive95'],[-.5,-.5])
    def test_incomplete_blocks_rejected(self):
        with self.assertRaises(ValueError):a.contrasts(self.trials[:-1],{x['trialID']:1 for x in self.trials[:-1]},self.reference)
    def test_freeze_and_verify_never_read_keys_or_network(self):
        with patch.object(t,'credential',side_effect=AssertionError('No credential access')),patch.object(t,'_http',side_effect=AssertionError('No network')):
            folder=self.lock();self.assertEqual(len(f.verify(folder/'registration.json')['trials']),840)
    def test_no_overwrite(self):
        folder=self.lock()
        with self.assertRaises(ValueError):f.freeze(folder)
    def test_tampered_registration_rejected(self):
        folder=self.lock();p=folder/'registration.json';v=c.read(p);v['trials'][0]['block']=99;p.write_bytes(c.data(v))
        with self.assertRaises(ValueError):f.verify(p)
    def test_tampered_analysis_design_rejected(self):
        folder=self.lock();p=folder/'design.json';v=c.read(p);v['intervals']['iterations']=50;p.write_bytes(c.data(v))
        with self.assertRaises(ValueError):f.verify(folder/'registration.json')
    def test_adapter_restores_original_reader_even_on_error(self):
        original=t.verify_registration
        with self.assertRaises(RuntimeError):
            with f.bound_verifier():
                self.assertIsNot(t.verify_registration,original);raise RuntimeError('fixture')
        self.assertIs(t.verify_registration,original)
    def test_pilot_reader_still_works_inside_adapter(self):
        with f.bound_verifier():reg=t.verify_registration(f.PILOT/'abstract_diagnostic/registration.snapshot.json')
        self.assertEqual(reg['phase'],'abstract_diagnostic')
    def test_formal_run_requires_opt_in_before_key_or_output(self):
        folder=self.lock()
        with patch.object(t,'credential',side_effect=AssertionError('No key')):
            with self.assertRaises(ValueError):f.run(folder/'registration.json',self.root/'out')
        self.assertFalse((self.root/'out').exists())
    def test_synthetic_formal_stop_preserves_all_planned_reason_rows(self):
        folder=self.root/'synthetic-lock';f.freeze(folder,validation_only=True);out=self.root/'synthetic-output';calls=[]
        def failure(*args):calls.append(1);return 429,b'{"error":"formal adapter fixture"}','fixture'
        import scenario_reason_coding as reason
        with f.bound_verifier():
            result=t.run(folder/'registration.json',out,transport=failure)
            reason.template(out,self.root/'review.json')
        self.assertEqual(result['reason'],'http_429');self.assertEqual(len(calls),1)
        sheet=c.read(self.root/'review.json');self.assertEqual(len(sheet['records']),840)
        self.assertTrue(all(not x['reasonEligible'] for x in sheet['records']))
        self.assertEqual(c.read(out/'registration.snapshot.json')['execution'],'synthetic_test')
        with self.assertRaises(ValueError):a.analyze(out,self.root/'invalid-analysis')
        self.assertFalse((self.root/'invalid-analysis').exists())
    def test_validation_only_lock_cannot_be_run_live(self):
        folder=self.root/'synthetic-lock';f.freeze(folder,validation_only=True)
        with patch.object(t,'credential',side_effect=AssertionError('No key')):
            with self.assertRaises(ValueError):f.run(folder/'registration.json',self.root/'out',True)
    def test_campaign_claim_prevents_resend_to_another_output(self):
        folder=self.lock();calls=[]
        def fake_run(path,out,confirm_live):
            calls.append(1);out.mkdir();return {'outcome':'stopped','completed':0,'reason':'synthetic fixture'}
        with patch.object(f,'CLAIMS_ROOT',self.root/'claims'),patch.object(t,'run',side_effect=fake_run):
            f.run(folder/'registration.json',self.root/'first-output',True)
            with self.assertRaises(FileExistsError):f.run(folder/'registration.json',self.root/'different-output',True)
        self.assertEqual(len(calls),1)
        self.assertFalse((self.root/'different-output').exists())

if __name__=='__main__':unittest.main()
