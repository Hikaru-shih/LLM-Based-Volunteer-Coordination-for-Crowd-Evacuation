"""Offline coding-provenance tests. Hand-authored fixtures are not model findings."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import scenario_agent_contract as c
import scenario_agent_transport as t
import scenario_reason_coding as s

class CodingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=c.ROOT/'tmp',prefix='reason-coding-test-');self.root=Path(self.temp.name)
        self.bundle=c.ROOT/'experiment_records/data/preparation/scenario_agent_stage3_20261116'
    def tearDown(self):self.temp.cleanup()
    def fixture(self,phase='physical_choice',mode='valid'):
        registration=self.root/'registration.json';t.register(self.bundle,registration,phase,1,2026111641,synthetic=True)
        by_payload={c.data(x['case']['payload']):x['case'] for x in c.read(registration)['trials']};counter=[0]
        def fake(payload,*_):
            counter[0]+=1;case=by_payload[payload]
            if mode=='http':return 429,b'{"error":"Synthetic rate limit"}','fixture'
            action='decline_assistance';reason='Helping costs me time, so I decline.'
            if 'diagnostic' in phase:
                action=case['diagnosticExpectedAction'] or 'participate';reason='The supplied comparison supports this choice.'
                if mode=='wrong' and case['diagnosticExpectedAction'] is not None:action='decline_assistance' if action=='participate' else 'participate'
            envelope={'id':('same' if mode=='duplicate' else 'synthetic-coding-'+str(counter[0])),'model':c.MODEL,'choices':[{'message':{'role':'assistant','content':json.dumps({'explanation':reason,'decision':action})},'finish_reason':'stop'}]}
            return 200,json.dumps(envelope).encode(),'fixture-request'
        run=self.root/'run';t.run(registration,run,transport=fake);sheet=self.root/'coding.json';s.template(run,sheet)
        return run,sheet
    def save(self,sheet,value):sheet.write_bytes(c.data(value))
    def code(self,row,label='personal_cost',quote=None):
        quote=quote or ('costs me time' if 'costs me time' in row['reasonText'] else 'supplied comparison')
        start=row['reasonText'].index(quote)
        row.update(codingStatus='reviewed',labels=[label],evidenceSpans=[{'label':label,'quote':quote,'start':start,'end':start+len(quote)}],
            actionReasonRelation='consistent',comparisonJudgment='correct' if 'diagnostic' in row['phase'] else 'not_applicable',
            unsupportedInformation='none',arithmeticJudgment='not_applicable',reviewer={'name':'Offline test fixture author','type':'assistant'},
            note='Hand-authored software validation example, not human/model research evidence.')
    def test_template_never_assigns_labels(self):
        run,sheet=self.fixture();v=c.read(sheet)
        self.assertEqual(len(v['records']),16);self.assertTrue(all(x['labels']==[] and x['codingStatus']=='unreviewed' for x in v['records']))
        self.assertEqual(s.validate(run,sheet)['reviewed'],0)
    def test_missing_and_invalid_preserved(self):
        run,sheet=self.fixture(mode='http');v=c.read(sheet)
        self.assertEqual(len(v['records']),16)
        self.assertEqual(sum(x['recordClass']=='technical_invalid' for x in v['records']),1)
        self.assertEqual(sum(x['recordClass']=='not_attempted' for x in v['records']),15)
        self.assertTrue(all(x['codingStatus']=='not_applicable' for x in v['records']))
        check=s.validate(run,sheet);self.assertFalse(check['coverageComplete']);self.assertFalse(check['collectionComplete'])
    def test_semantic_failure_reason_is_not_discarded(self):
        run,sheet=self.fixture('abstract_diagnostic','wrong');v=c.read(sheet)
        bad=[x for x in v['records'] if x['recordClass']=='semantic_failure']
        self.assertEqual(len(bad),1);self.assertTrue(bad[0]['reasonEligible']);self.assertTrue(bad[0]['reasonText'])
        self.assertEqual(len(v['records']),18)
    def test_duplicate_not_counted_as_new_reason(self):
        run,sheet=self.fixture(mode='duplicate');v=c.read(sheet)
        self.assertEqual(sum(x['reasonEligible'] for x in v['records']),1)
        self.assertEqual(sum(x['recordClass']=='duplicate_response' for x in v['records']),1)
    def test_bound_raw_text_cannot_be_edited(self):
        run,sheet=self.fixture();v=c.read(sheet);v['records'][0]['reasonText']='Changed';self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_bound_action_cannot_be_repaired(self):
        run,sheet=self.fixture();v=c.read(sheet);v['records'][0]['rawAction']='participate';self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_unknown_labels_rejected(self):
        run,sheet=self.fixture();v=c.read(sheet);self.code(v['records'][0]);v['records'][0]['labels']=['altruistic_personality'];self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_fabricated_quote_rejected(self):
        run,sheet=self.fixture();v=c.read(sheet);self.code(v['records'][0]);v['records'][0]['evidenceSpans'][0]['quote']='I will save everyone';self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_missing_label_evidence_rejected(self):
        run,sheet=self.fixture();v=c.read(sheet);self.code(v['records'][0]);v['records'][0]['evidenceSpans']=[];self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_quality_conflict_requires_matching_label(self):
        run,sheet=self.fixture();v=c.read(sheet);self.code(v['records'][0]);v['records'][0]['actionReasonRelation']='conflict';self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_unknown_information_requires_matching_label(self):
        run,sheet=self.fixture();v=c.read(sheet);self.code(v['records'][0]);v['records'][0]['unsupportedInformation']='present';self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_partial_coverage_explicit_and_cannot_require_complete(self):
        run,sheet=self.fixture();v=c.read(sheet);self.code(v['records'][0]);self.save(sheet,v)
        check=s.validate(run,sheet);self.assertEqual(check['reviewed'],1);self.assertEqual(check['unreviewed'],15)
        with self.assertRaises(ValueError):s.validate(run,sheet,True)
        target=self.root/'summary.json';s.summarize(run,sheet,target);report=c.read(target);self.assertFalse(report['coverageComplete'])
        self.assertEqual(sum(x['planned'] for x in report['groups']),16)
    def test_empty_review_rates_are_null_not_zero(self):
        run,sheet=self.fixture();target=self.root/'summary.json';s.summarize(run,sheet,target);report=c.read(target)
        self.assertTrue(all(value is None for group in report['groups'] for value in group['labelRatesAmongReviewed'].values()))
    def test_missing_planned_rows_rejected(self):
        run,sheet=self.fixture();v=c.read(sheet);v['records'].pop();self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_duplicate_coding_ids_rejected(self):
        run,sheet=self.fixture();v=c.read(sheet);v['records'][0]=copy.deepcopy(v['records'][1]);self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_forecast_label_cannot_appear_when_no_forecasts_supplied(self):
        run,sheet=self.fixture();v=c.read(sheet);row=next(x for x in v['records'] if x['information']=='geometry_only');self.code(row,'forecast_use');self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_unclear_quality_needs_note(self):
        run,sheet=self.fixture();v=c.read(sheet);self.code(v['records'][0]);v['records'][0]['actionReasonRelation']='unclear';self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
        v['records'][0]['uncertaintyNote']='Phrase is ambiguous.';self.save(sheet,v);self.assertEqual(s.validate(run,sheet)['reviewed'],1)
    def test_arithmetic_error_needs_quote(self):
        run,sheet=self.fixture();v=c.read(sheet);self.code(v['records'][0]);v['records'][0]['arithmeticJudgment']='incorrect';self.save(sheet,v)
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_codebook_drift_requires_recode(self):
        run,sheet=self.fixture();fake=self.root/'book.json';fake.write_bytes(s.CODEBOOK.read_bytes()+b' ')
        with patch.object(s,'CODEBOOK',fake),self.assertRaises(ValueError):s.validate(run,sheet)
    def test_gate_export_requires_diagnostic_not_free_choice(self):
        run,sheet=self.fixture();v=c.read(sheet)
        for row in v['records']:self.code(row)
        self.save(sheet,v)
        with self.assertRaises(ValueError):s.gate_review(run,sheet,self.root/'gate.json')
    def test_full_synthetic_gate_review_still_cannot_qualify_live(self):
        run,sheet=self.fixture('physical_diagnostic');v=c.read(sheet)
        for row in v['records']:self.code(row,'forecast_use')
        self.save(sheet,v);target=self.root/'gate.json';s.gate_review(run,sheet,target)
        self.assertEqual(c.read(target)['execution'],'synthetic_test')
        with self.assertRaises(ValueError):t.gate_evidence(run,target,self.bundle)
    def test_raw_file_tamper_rejected(self):
        run,sheet=self.fixture();raw=next((run/'trials').glob('*/response.raw'));raw.write_bytes(raw.read_bytes()+b' ')
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_summary_separates_information_conditions(self):
        run,sheet=self.fixture();v=c.read(sheet)
        for row in v['records']:self.code(row)
        self.save(sheet,v);target=self.root/'summary.json';s.summarize(run,sheet,target,True);report=c.read(target)
        self.assertEqual(len(report['groups']),16);self.assertTrue(report['coverageComplete'])
        self.assertEqual({x['information'] for x in report['groups']},{'geometry_only','calibrated_forecast'})
    def test_result_without_claim_rejected(self):
        run,sheet=self.fixture();next((run/'trials').glob('*/CLAIM.json')).unlink()
        with self.assertRaises(ValueError):s.validate(run,sheet)
    def test_unicode_offsets_are_codepoints(self):
        s.span_valid({'quote':'協助','start':1,'end':3},'我協助🙂')
        with self.assertRaises(ValueError):s.span_valid({'quote':'🙂','start':3,'end':5},'我協助🙂')

if __name__=='__main__':unittest.main()
