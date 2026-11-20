import json
import tempfile
import unittest
from pathlib import Path
from individual_sampling import summarize, probability, wilson


class SamplingTests(unittest.TestCase):
    def test_reference_boundaries(self):
        s = dict(nearbyAgentCount=1, exitNonBlockage=0, volunteerCost=.005, failureCost=.5, unwillingness=5)
        self.assertEqual(probability(s), 1)
        s['exitNonBlockage'] = .5
        self.assertEqual(probability(s), 0)
        s['nearbyAgentCount'] = 2
        s['exitNonBlockage'] = 0
        self.assertEqual(probability(s), 1)

    def test_interval(self):
        self.assertEqual(wilson(0, 0), (None, None))
        lo, hi = wilson(5, 10)
        self.assertAlmostEqual(lo, 1-hi)
        self.assertLess(lo, .5)
        self.assertEqual(wilson(0,3)[0],0)
        self.assertEqual(wilson(3,3)[1],1)

    def test_missing_invalid_and_synthetic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'trials').mkdir()
            scenario = dict(id='one', nearbyAgentCount=1, exitNonBlockage=0, volunteerCost=.005, failureCost=.5, unwillingness=5)
            (root/'plan.json').write_text(json.dumps(dict(schema='individual-sampling-v1', promptVersion='paper-agent-v5', model='fixture', repetitions=3, scenarios=[scenario])))
            observation = {k:v for k,v in scenario.items() if k!='id'}
            t = dict(index=0, repetition=0, scenario='one', observation=json.dumps(observation), referenceProbability=1, valid=False, execution='synthetic_test', error='invalid_decision_json')
            (root/'trials'/'000000.json').write_text(json.dumps(t))
            with self.assertRaises(ValueError):
                summarize(root)
            row = summarize(root, True)[0]
            self.assertEqual((row['invalid'], row['missing'], row['valid']), (1, 2, 0))
            self.assertIsNone(row['rate'])
            self.assertIsNone(row['difference'])
            t['index'] = 9
            (root/'trials'/'000000.json').write_text(json.dumps(t))
            with self.assertRaises(AssertionError):
                summarize(root, True)


if __name__ == '__main__':
    unittest.main()
