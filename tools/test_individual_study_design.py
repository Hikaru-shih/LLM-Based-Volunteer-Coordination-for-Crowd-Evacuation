import copy
import json
import tempfile
import unittest
from pathlib import Path

from individual_study_design import audit, primary, seal, verify


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[1]
        (self.root/'tmp').mkdir(exist_ok=True)
        self.draft=json.loads((self.root/'research/individual_agent_v1/study-design.draft.json').read_text(encoding='utf-8-sig'))
        self.pilot=json.loads((self.root/'research/individual_agent_v1/pilot.sampling.json').read_text(encoding='utf-8-sig'))
    def test_counts_and_precision(self):
        result=audit(self.draft,self.pilot)
        self.assertEqual((result['pilotEligibleChoices'],result['pilotNoGameRecords'],result['plannedPilotMaxHttpAttempts']),(24,6,102))
        self.assertEqual((result['candidateMainStates'],result['candidateBoundaryStates'],result['candidateEligibleCalls']),(27,3,3000))
        self.assertLess(result['worstCaseWilsonHalfwidthIfAllValid'],.1)
        self.assertFalse(result['formalLocked'])
    def test_bad_budget(self):
        self.pilot['maxHttpAttempts']=71
        with self.assertRaises(ValueError):audit(self.draft,self.pilot)
    def test_model_mismatch(self):
        self.pilot['model']='different'
        with self.assertRaises(ValueError):audit(self.draft,self.pilot)
    def test_changed_primary_condition(self):
        self.draft['primaryContrast']['fixed']['exitNonBlockage']=.3
        with self.assertRaises(ValueError):audit(self.draft,self.pilot)
    def test_confounded_contrast(self):
        self.draft['primaryContrast']['fixed']['volunteerCost']=.005
        with self.assertRaises(ValueError):audit(self.draft,self.pilot)
    def test_no_live_authorization(self):
        self.draft['pilotLimits']['paidExecutionAuthorized']=True
        with self.assertRaises(ValueError):audit(self.draft,self.pilot)
    def test_old_comprehension_rejected(self):
        self.draft['pilotComprehension']['questions']=8
        with self.assertRaises(ValueError):audit(self.draft,self.pilot)
    def test_controls_required(self):
        self.draft['noGameControls']=self.draft['noGameControls'][:1]
        with self.assertRaises(ValueError):audit(self.draft,self.pilot)
    def test_boundary_not_mixed(self):
        self.draft['singlePlayer']['nearbyAgentCount']=2
        with self.assertRaises(ValueError):audit(self.draft,self.pilot)
    def test_audit_tampering_and_source_change(self):
        with tempfile.TemporaryDirectory(dir=self.root/'tmp',prefix='p4-test-') as tmp:
            root=Path(tmp)
            files=['research/individual_agent_v1/study-design.draft.json','research/individual_agent_v1/pilot.sampling.json','tools/individual_study_design.py','tools/individual_analysis.py','tools/individual_sampling.py','Assets/scripts/Editor/IndividualSamplingRunner.cs','Assets/scripts/Editor/LLMComprehensionRunner.cs','Assets/scripts/Decision/PaperVolunteerPrompt.cs']
            for name in files:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((self.root/name).read_bytes())
            out=root/'audit.json';record=seal(root,root/files[0],out);self.assertEqual(verify(root,out),record['auditID'])
            with self.assertRaises(ValueError):seal(root,root/files[0],out)
            changed=copy.deepcopy(record);changed['pilotEligibleChoices']=999;out.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):verify(root,out)
            out.write_text(json.dumps(record));(root/'Assets/scripts/Decision/PaperVolunteerPrompt.cs').write_text('changed')
            with self.assertRaises(ValueError):verify(root,out)
    def test_declared_nonadjacent_primary(self):
        from test_individual_analysis import fixture
        from individual_analysis import analyze, probability
        with tempfile.TemporaryDirectory(dir=self.root/'tmp',prefix='p4-primary-test-') as tmp:
            root=Path(tmp);scenarios=[dict(id=name,nearbyAgentCount=5,exitNonBlockage=.5,volunteerCost=cv,failureCost=.5,unwillingness=5) for name,cv in [('low',.005),('center',.05),('high',.2)]]
            fixture(root/'run',scenarios);analyze(root/'run',root/'report',True)
            draft=copy.deepcopy(self.draft);draft['model']='offline-analysis-fixture'
            with self.assertRaises(ValueError):primary(draft,root/'report')
            result=primary(draft,root/'report',True)['estimate']
            self.assertEqual((result['scenario_a'],result['scenario_b']),('low','high'))
            self.assertEqual(result['observed_change'],0)
            self.assertAlmostEqual(result['response_deviation'],probability(scenarios[0])-probability(scenarios[2]))
            draft['primaryContrast']['fixed']['exitNonBlockage']=.3
            with self.assertRaises(ValueError):primary(draft,root/'report',True)


if __name__=='__main__':unittest.main()
