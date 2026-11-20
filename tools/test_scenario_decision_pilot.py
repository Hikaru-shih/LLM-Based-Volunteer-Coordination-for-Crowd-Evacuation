"""Offline scientific-contract checks, without network/provider mocking as evidence."""
import copy,json,tempfile,unittest
from pathlib import Path
import scenario_decision_pilot as s

class PilotContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads((s.DESIGN/'pilot-plan.draft.json').read_text())
        cls.prompt=(s.DESIGN/'PROMPT_CANDIDATE.en.md').read_text()
        cls.trials=s.build(cls.plan,cls.prompt)
    def test_counts_and_balanced_gate(self):
        gate=[t for t in self.trials if t['phase']=='gate']
        self.assertEqual(len(gate),36)
        self.assertEqual(sum(t['expectedDiagnosticAction'] is None for t in gate),4)
        self.assertEqual(sum(t['expectedDiagnosticAction']=='participate' for t in gate),16)
        self.assertEqual(sum(t['expectedDiagnosticAction']=='decline_assistance' for t in gate),16)
        self.assertEqual(len(self.trials)-len(gate),120)
    def test_gate_precedes_free_and_reproducible(self):
        self.assertTrue(all(t['phase']=='gate' for t in self.trials[:36]))
        self.assertEqual(self.trials,s.build(self.plan,self.prompt))
    def test_no_answer_or_belief_leakage(self):
        for t in self.trials:
            txt=t['payload']['messages'][1]['content']
            self.assertNotIn('referenceProbability',txt)
            self.assertNotIn('expectedDiagnosticAction',txt)
            if t['phase']=='free':
                self.assertNotIn('q=',txt);self.assertIn('probabilities are unknown',txt)
                self.assertNotIn('risk-neutral',txt)
            else:
                self.assertNotIn('probabilities are unknown',txt);self.assertIn('joint probability',txt)
    def test_v3_schema_and_fresh_context(self):
        for t in self.trials:
            p=t['payload'];sch=p['response_format']['json_schema']['schema']
            self.assertEqual(list(sch['properties']),['explanation','decision'])
            self.assertNotIn('enum',sch['properties']['decision'])
            self.assertEqual([m['role'] for m in p['messages']],['system','user'])
            self.assertEqual(p['max_completion_tokens'],220)
            self.assertEqual(p['temperature'],.15)
    def envelope(self,content,**extra):
        return json.dumps({'id':'synthetic-offline-only','model':'gpt-6-luna','choices':[{'message':{'role':'assistant','content':content},'finish_reason':'stop'}],**extra})
    def test_decline_is_not_overridden_by_explanation(self):
        result=s.audit_reply(self.trials[0],self.envelope(json.dumps({'explanation':'Helping could improve passage, but I decline.','decision':'decline_assistance'})))
        self.assertFalse(result['willing']);self.assertEqual(result['rawAction'],'decline_assistance')
    def test_conflicting_reason_never_relabels_action(self):
        result=s.audit_reply(self.trials[0],self.envelope(json.dumps({'explanation':'I prefer to decline.','decision':'participate'})))
        self.assertTrue(result['willing']);self.assertFalse(result['reasonReviewed'])
    def test_invalids_fail_closed(self):
        contents=['{"explanation":"x","decision":"participate","decision":"decline_assistance"}',json.dumps({'explanation':'x','decision':'decline'}),json.dumps({'explanation':'','decision':'participate'}),json.dumps({'explanation':'x','decision':'participate','extra':1})]
        for content in contents:
            with self.subTest(content=content),self.assertRaises(ValueError):s.audit_reply(self.trials[0],self.envelope(content))
    def test_provider_and_truncation_fail_closed(self):
        raw=self.envelope(json.dumps({'explanation':'x','decision':'participate'}))
        for mutated in [raw.replace('gpt-6-luna','different-model'),raw.replace('"stop"','"length"')]:
            with self.assertRaises(ValueError):s.audit_reply(self.trials[0],mutated)
    def test_domain_and_ratio_drift_rejected(self):
        for field,value in [('volunteerCost',.9),('costRatio',.2),('exitNonBlockage',0)]:
            p=copy.deepcopy(self.plan);p['cells'][0][field]=value
            with self.assertRaises(ValueError):s.build(p,self.prompt)
    def test_export_tamper_detection_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'export';self.assertTrue(s.export(out)['passed'])
            with self.assertRaises(ValueError):s.export(out)
            f=out/'trials.json';f.write_bytes(f.read_bytes()+b' ')
            with self.assertRaises(ValueError):s.verify(out)
    def test_review_sheet_is_explicitly_unobserved(self):
        import csv
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'export';s.export(out);target=Path(tmp)/'review.csv'
            result=s.review_sheet(out,target);self.assertEqual(result['observedResponses'],0)
            with target.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),156)
            self.assertTrue(all(row['reviewStatus']=='not_collected' and not row['rawAction'] for row in rows))
            with self.assertRaises(ValueError):s.review_sheet(out,target)

if __name__=='__main__':unittest.main()
