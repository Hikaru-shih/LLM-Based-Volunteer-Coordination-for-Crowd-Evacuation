"""Offline checks only; mock envelopes are never saved as experimental records."""
import copy,json,unittest
from collections import Counter
import information_control_experiment as e
import scenario_agent_contract as c
class InformationControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cases,cls.audit=e.build_cases(e.encoding())
    def test_unchanged_concurrent_reference_prompts(self):
        old={t['case']['caseID']:t['case'] for t in e.read(e.OLD)['trials']}
        for x in self.cases:
            if x['information']!='length_control' and x['optionOrder']=='participate_first':self.assertEqual(x['payload'],old[f"PC_{x['scenario']}_{x['information']}"]['payload'])
    def test_order_reverses_exactly_two_action_enumerations(self):
        byid={(x['scenario'],x['information'],x['optionOrder']):x for x in self.cases}
        for x in self.cases:
            if x['optionOrder']=='participate_first':
                y=byid[x['scenario'],x['information'],'decline_first'];want=copy.deepcopy(x['payload']);want['messages'][1]['content']=e.reverse(want['messages'][1]['content']);self.assertEqual(want,y['payload'])
    def test_proxy_length_and_number_matching(self):
        for a in self.audit:
            self.assertLessEqual(abs(a['length_control']['proxyTokens']-a['forecast']['proxyTokens']),1)
            self.assertEqual(a['length_control']['numericLiterals'],a['forecast']['numericLiterals'])
            self.assertTrue(.90<=a['characterRatio']<=1.10)
            self.assertTrue(.90<=a['wordRatio']<=1.10)
    def test_factorial_cell_balance(self):
        self.assertEqual(len(self.cases),48)
        self.assertEqual(len({x['caseID'] for x in self.cases}),48)
        self.assertEqual(Counter(x['information'] for x in self.cases),dict.fromkeys(e.INFOS,16))
        for x in self.cases:self.assertEqual(c.sha(c.data(x['payload'])),x['payloadSHA256'])
    def test_control_has_no_decision_forecast_table(self):
        for x in self.cases:
            if x['information']=='length_control':
                text=x['payload']['messages'][1]['content'];extra=text.split('The following printed catalogue records',1)[1]
                self.assertNotIn('ownCappedExitSteps',extra);self.assertNotIn('others_willing',extra);self.assertNotIn('others_decline',extra)
                self.assertIn('unrelated administrative examples',text)
    def envelope(self,body,**kw):
        d={'id':'synthetic_fixture_not_evidence','model':'gpt-6-luna','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(body)}}]};d.update(kw);return json.dumps(d)
    def test_strict_parsing_retains_decline(self):
        r=c.parse_reply(self.cases[0],self.envelope({'decision':'decline_assistance','explanation':'No supplied personal gain.'}));self.assertFalse(r['willing'])
    def test_model_drift_refusal_and_invalid_action_rejected(self):
        for raw in [self.envelope({'decision':'yes','explanation':'fixture'}),self.envelope({'decision':'participate','explanation':'fixture'},model='different-model'),json.dumps({'model':'gpt-6-luna','id':'fixture','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'{}','refusal':'refused'}}]})]:
            with self.assertRaises(ValueError):c.parse_reply(self.cases[0],raw)
if __name__=='__main__':unittest.main()
