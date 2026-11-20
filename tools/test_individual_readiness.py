import json
import unittest
from individual_readiness import profile, workload


class ReadinessTests(unittest.TestCase):
    def payload(self, factual=False):
        return dict(model='gpt-6-luna', reasoning_effort='none', temperature=0 if factual else .15,
                    max_completion_tokens=160 if factual else 220,
                    messages=[dict(role='system', content='fixture'), dict(role='user', content='fixture')],
                    response_format={})

    def test_choice_and_factual_profiles(self):
        for factual in (False, True):
            profile(json.dumps(self.payload(factual)), factual)

    def test_model_effort_limit_temperature_drift(self):
        for field, value in [('model', 'gpt-4o-mini'), ('reasoning_effort', 'medium'),
                             ('max_completion_tokens', 221), ('temperature', .7)]:
            p = self.payload(); p[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): profile(json.dumps(p))

    def test_legacy_extra_and_history_rejected(self):
        p = self.payload(); p['max_tokens'] = 220
        with self.assertRaises(ValueError): profile(json.dumps(p))
        p = self.payload(); p['messages'].append(dict(role='assistant', content='history'))
        with self.assertRaises(ValueError): profile(json.dumps(p))

    def test_workload_and_precision(self):
        p = dict(repetitions=100, maxHttpAttempts=9000, scenarios=[dict(nearbyAgentCount=5, exitNonBlockage=.5)]*30 + [dict(nearbyAgentCount=0, exitNonBlockage=.5),dict(nearbyAgentCount=5, exitNonBlockage=1)])
        result = workload(p)
        self.assertEqual((result['eligibleChoices'], result['noGameRecords'], result['totalRecords']), (3000, 200, 3200))
        self.assertAlmostEqual(result['worstCaseWilsonHalfWidth'], .0961684696, places=8)


if __name__ == '__main__': unittest.main()
