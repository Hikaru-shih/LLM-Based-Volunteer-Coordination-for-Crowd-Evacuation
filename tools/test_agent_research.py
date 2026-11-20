import csv
import json
import tempfile
import unittest
from pathlib import Path

import agent_research as ar
import research_plan as rp


class AgentResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def csv(self, path, fields, rows):
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def fixture(self, name='a', seed=1, policy='LLM', phase='Calibration', termination='completed'):
        prefix = self.root/name
        c = dict(schemaVersion='4-paper-relocation', obstacleHandling='PaperRelocation', conditionKey='physical',
                 researchPhase=phase, volunteerPolicy=policy, decisionExecution='live', paperPromptVersion='paper-agent-v5',
                 model='model', observationScope='Core', studyPlanID='synthetic-plan', seed=seed, actualAgents=2, maxSteps=10, runID=1,
                 movableObstacles=0, scenario='SingleBlockedExit')
        path = Path(str(prefix)+'_config.json')
        path.write_text(json.dumps(c))
        evacuated = 2 if termination == 'completed' else 1
        self.csv(Path(str(prefix)+'_global.csv'), ['Termination', 'EvacuatedCount', 'TotalSteps'],
                 [dict(Termination=termination, EvacuatedCount=evacuated, TotalSteps=4 if evacuated == 2 else 10)])
        self.csv(Path(str(prefix)+'_agents.csv'), ['AgentID', 'EvacuationStep'],
                 [dict(AgentID=i, EvacuationStep=2+i*2) for i in range(evacuated)])
        self.csv(Path(str(prefix)+'_trajectories.csv'), ['Step', 'AgentID'], [dict(Step=0, AgentID=i) for i in range(2)])
        self.csv(Path(str(prefix)+'_agent_observations.csv'), ['Step', 'AgentID', 'ObstacleID', 'Willing', 'Source'],
                 [dict(Step=1, AgentID=i, ObstacleID=0, Willing=str(i == 0), Source='api' if policy == 'LLM' else 'game_theory') for i in range(2)])
        self.csv(Path(str(prefix)+'_agent_effort.csv'), ['Step', 'AgentID', 'ObstacleID'], [dict(Step=1, AgentID=0, ObstacleID=0)])
        return path

    def test_calibration_uses_only_separate_valid_llm_data(self):
        self.fixture()
        result = ar.calibrate(self.root, self.root/'calibration.json')
        self.assertEqual(result['probability'], .5)
        self.assertEqual(result['seeds'], [1])
        self.fixture('b', seed=2, phase='FinalTest')
        with self.assertRaises(ValueError):
            ar.calibrate(self.root, self.root/'bad.json')

    def test_invalid_calibration_is_not_silently_dropped(self):
        self.fixture(termination='invalid_llm_api_failure')
        with self.assertRaises(ValueError):
            ar.calibrate(self.root, self.root/'bad.json')

    def test_calibration_rejects_overridden_reference_rule(self):
        self.fixture()
        path=self.root/'a_agent_observations.csv'
        rows=ar.read_csv(path)
        for row in rows:row['ObservationJSON']='{}'
        rows.append(dict(Step=2,AgentID=0,ObstacleID=1,Willing='True',Source='reference_rule',ObservationJSON=json.dumps(dict(nearbyAgentCount=1,exitNonBlockage=0))))
        self.csv(path,list(rows[0]),rows)
        with self.assertRaises(ValueError):ar.calibrate(self.root,self.root/'cal.json')

    def test_reference_rule_cannot_disguise_multiplayer_choice(self):
        self.fixture();path=self.root/'a_agent_observations.csv';rows=ar.read_csv(path)
        for row in rows:row['ObservationJSON']=json.dumps(dict(nearbyAgentCount=2,exitNonBlockage=0))
        rows[0]['Source']='reference_rule';self.csv(path,list(rows[0]),rows)
        with self.assertRaises(ValueError):ar.calibrate(self.root,self.root/'bad.json')

    def test_synthetic_transport_not_model_measurement(self):
        config=self.fixture();path=self.root/'a_agent_observations.csv';rows=ar.read_csv(path)
        rows[0]['Source']='synthetic_test';self.csv(path,list(rows[0]),rows)
        with self.assertRaises(ValueError):ar.calibrate(self.root,self.root/'bad.json')
        with self.assertRaises(ValueError):ar.run_metrics(config)

    def test_old_prompt_cannot_calibrate_v5(self):
        path=self.fixture();value=json.loads(path.read_text());value['paperPromptVersion']='paper-agent-v3';path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):ar.calibrate(self.root,self.root/'bad.json')

    def test_timeout_and_invalid_have_different_endpoints(self):
        timeout = ar.run_metrics(self.fixture('timeout', termination='timeout'))
        invalid = ar.run_metrics(self.fixture('invalid', termination='invalid_llm_api_failure'))
        self.assertEqual(timeout['capped_t100'], 10)
        self.assertEqual(timeout['completed'], 0)
        self.assertIsNone(invalid['capped_t100'])
        self.assertEqual(timeout['individual_work_ticks'], {'0': 1, '1': 0})

    def test_pairing_and_invalid_counts(self):
        self.fixture('l1', phase='FinalTest')
        self.fixture('g1', policy='OriginalGameTheory', phase='FinalTest')
        self.fixture('l2', seed=2, phase='FinalTest', termination='invalid_llm_api_failure')
        self.fixture('g2', seed=2, policy='OriginalGameTheory', phase='FinalTest')
        result = ar.analyze(self.root, self.root/'analysis.json')
        self.assertEqual(result['comparisons'][0]['paired_valid_seeds'], 1)
        self.assertEqual(result['comparisons'][0]['invalid_pairs'], 1)
        self.assertIsNone(result['comparisons'][0]['interval95'])

    def test_duplicate_replicates_require_explicit_analysis(self):
        self.fixture('a')
        self.fixture('b')
        with self.assertRaises(ValueError):
            ar.analyze(self.root, self.root/'bad.json')

    def test_bootstrap_blocks(self):
        self.assertEqual(ar.block_interval([2, 2, 2]), [2, 2])
        self.assertIsNone(ar.block_interval([2]))

    def test_calibration_rejects_different_information(self):
        self.fixture('a', seed=1)
        other=self.fixture('b', seed=2)
        config=json.loads(other.read_text())
        config['observationScope']='SharedContext'
        other.write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            ar.calibrate(self.root, self.root/'bad.json')

    def test_analysis_does_not_mix_study_versions(self):
        self.fixture('a', phase='FinalTest')
        other=self.fixture('b', policy='OriginalGameTheory', phase='FinalTest')
        config=json.loads(other.read_text());config['studyPlanID']='different-study'
        other.write_text(json.dumps(config))
        result=ar.analyze(self.root,self.root/'separate.json')
        self.assertEqual(result['comparisons'], [])

    def test_analysis_does_not_mix_prompt_versions(self):
        self.fixture('a',phase='FinalTest')
        other=self.fixture('b',policy='OriginalGameTheory',phase='FinalTest')
        config=json.loads(other.read_text());config['paperPromptVersion']='paper-agent-v3';other.write_text(json.dumps(config))
        result=ar.analyze(self.root,self.root/'separate.json')
        self.assertEqual(result['comparisons'],[])

    def test_replay_is_not_a_research_replicate(self):
        path=self.fixture()
        config=json.loads(path.read_text());config['decisionExecution']='strict_replay'
        path.write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            ar.analyze(self.root,self.root/'bad.json')

    def test_plan_split_validation(self):
        plan = dict(schema='agent-study-plan-v1', horizon=100, model='model', promptVersion='paper-agent-v5',
                    developmentSeeds=[1], calibrationSeeds=[2], testSeeds=[3], conditionKeys=['physical'],
                    informationConditions=['Core', 'SharedContext'],
                    policies=['LLM', 'OriginalGameTheory', 'MockHeuristic', 'RandomMatched'],
                    primaryContrast='SharedContext LLM vs GameTheory', multiplicityTreatment='descriptive')
        rp.validate(plan)
        plan['testSeeds'] = [2]
        with self.assertRaises(ValueError):
            rp.validate(plan)

    def test_freeze_records_sources_and_both_calibrations(self):
        for name in ('Packages/manifest.json', 'ProjectSettings/ProjectVersion.txt', 'RESEARCH_PROTOCOL.zh-TW.md', 'Assets/scripts/example.cs'):
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic')
        plan=dict(schema='agent-study-plan-v1',horizon=100,model='model',promptVersion='paper-agent-v5',
                  developmentSeeds=[1],calibrationSeeds=[2],testSeeds=[3],conditionKeys=['physical'],
                  informationConditions=['Core','SharedContext'],policies=['OriginalGameTheory','LLM','MockHeuristic','RandomMatched'],
                  primaryContrast='test',multiplicityTreatment='descriptive',calibrationFiles=[])
        for info in plan['informationConditions']:
            name=info+'.json';plan['calibrationFiles'].append(name)
            (self.root/name).write_text(json.dumps(dict(schema='cooperation-calibration-v1',conditionKey='physical',
                model='model',promptVersion='paper-agent-v5',seeds=[2],informationCondition=info)))
        frozen=rp.freeze(plan,self.root)
        self.assertTrue(frozen['locked'])
        self.assertTrue(any(source['path']=='Assets/scripts/example.cs' for source in frozen['sourceFiles']))
        plan['calibrationFiles'].pop()
        with self.assertRaises(ValueError):
            rp.freeze(plan,self.root)


if __name__ == '__main__':
    unittest.main()
