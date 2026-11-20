"""Stage3 integration tests with explicitly synthetic transports; no API or credential reads."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import scenario_agent_contract as c
import scenario_agent_transport as t

class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.inputs=c.load_inputs();cls.cases=c.build_cases(*cls.inputs)
    def case(self,phase):return next(x for x in self.cases if x['phase']==phase)
    def raw(self,action='participate',explanation='Synthetic contract fixture.',id='offline-fixture',**overrides):
        body={'explanation':explanation,'decision':action}
        envelope={'model':c.MODEL,'id':id,'choices':[{'message':{'role':'assistant','content':json.dumps(body)},'finish_reason':'stop'}]}
        envelope.update(overrides);return json.dumps(envelope)
    def test_phase_counts(self):
        self.assertEqual({phase:sum(x['phase']==phase for x in self.cases) for phase in c.PHASES},{'abstract_diagnostic':18,'physical_diagnostic':16,'abstract_choice':12,'physical_choice':16})
    def test_original_six_are_legal_and_reference_only(self):
        self.assertEqual(len(self.inputs[1]),6)
        for cell in self.inputs[1]:self.assertTrue(0<cell['volunteerCost']<cell['failureCost']<1)
        for x in self.cases:
            text=x['payload']['messages'][1]['content']
            if x['phase'].startswith('abstract'):self.assertNotIn('Forecasts:',text)
            else:self.assertNotIn('volunteerCost',text);self.assertNotIn('referenceProxy',text)
    def test_no_gate_or_forecast_leakage(self):
        for x in self.cases:
            text=x['payload']['messages'][1]['content']
            self.assertNotIn('referenceProbability',text);self.assertNotIn('diagnosticExpectedAction',text)
            if x['phase']=='abstract_choice':self.assertNotIn('q=',text);self.assertNotIn('risk-neutral',text)
            if x['information']=='geometry_only':self.assertNotIn('Forecasts:',text);self.assertNotIn('meanCappedOwnExitStep',text)
    def test_abstract_gate_balanced_and_ties(self):
        gate=[x['diagnosticExpectedAction'] for x in self.cases if x['phase']=='abstract_diagnostic']
        self.assertEqual(gate.count('participate'),8);self.assertEqual(gate.count('decline_assistance'),8);self.assertEqual(gate.count(None),2)
        self.assertIsNone(c.expected_utility(.15,.3,.5))
        self.assertEqual(c.expected_utility(.15,.3,.95),'participate')
    def test_physical_forecasts_bind_actual_agents(self):
        spec,_,agents=self.inputs
        for cell in spec['cells']:
            f=c.forecasts(cell,agents);self.assertEqual(len(f),4)
            for row in f:
                for k in ('ownCappedExitSteps','otherNineMeanCappedExitSteps'):
                    v=row[k];self.assertLessEqual(v['observedMin']-1e-6,v['mean']);self.assertLessEqual(v['mean'],v['observedMax']+1e-6)
                self.assertEqual(row['developmentSeedCount'],6)
    def test_forecast_tamper_rejected(self):
        spec,_,agents=self.inputs;cell=copy.deepcopy(spec['cells'][0]);cell['empiricalConditionalPayoffs']['others_decline']['participate']['meanCappedOwnExitStep']+=1
        with self.assertRaises(ValueError):c.forecasts(cell,agents)
    def test_diagnostics_use_displayed_mean_not_hidden_answer(self):
        for x in self.cases:
            if x['phase']!='physical_diagnostic':continue
            f=json.loads(x['payload']['messages'][1]['content'].split('Forecasts:\n')[1]);a=next(r['ownCappedExitSteps']['mean'] for r in f if r['ownChoice']=='participate');d=next(r['ownCappedExitSteps']['mean'] for r in f if r['ownChoice']=='decline_assistance')
            self.assertEqual(x['diagnosticExpectedAction'],c.expected_time(a,d))
    def test_schema_history_and_token_profile(self):
        for x in self.cases:
            p=x['payload'];self.assertEqual(p['model'],c.MODEL);self.assertEqual(p['max_completion_tokens'],220)
            self.assertEqual([m['role'] for m in p['messages']],['system','user'])
            schema=p['response_format']['json_schema']['schema'];self.assertEqual(list(schema['properties']),['explanation','decision']);self.assertNotIn('enum',schema['properties']['decision'])
    def test_adapter_preserves_decline(self):
        result=c.consume(self.case('physical_choice'),self.raw('decline_assistance','Helping may benefit others, but I decline.'))
        self.assertFalse(result['willing']);self.assertFalse(result['controlsOtherAgents']);self.assertEqual(result['action'],'decline_assistance')
    def test_no_action_repair_from_reason(self):
        result=c.parse_reply(self.case('abstract_choice'),self.raw('participate','Declining would be better.'))
        self.assertTrue(result['willing']);self.assertFalse(result['reasonReviewed'])
    def test_bad_raw_envelopes_fail_closed(self):
        case=self.case('physical_choice');base=json.loads(self.raw())
        for mutate in ['duplicate','action','blank','refusal','length','tool','model','id','nonfinite']:
            v=copy.deepcopy(base)
            if mutate=='duplicate':v['choices'][0]['message']['content']='{"explanation":"x","decision":"participate","decision":"decline_assistance"}'
            if mutate=='action':v['choices'][0]['message']['content']='{"explanation":"x","decision":"maybe"}'
            if mutate=='blank':v['choices'][0]['message']['content']='{"explanation":" ","decision":"participate"}'
            if mutate=='refusal':v['choices'][0]['message']['refusal']='No.'
            if mutate=='length':v['choices'][0]['finish_reason']='length'
            if mutate=='tool':v['choices'][0]['message']['tool_calls']=[{}]
            if mutate=='model':v['model']='different'
            if mutate=='id':v.pop('id')
            raw=json.dumps(v)
            if mutate=='nonfinite':raw=raw[:-1]+',"extra":NaN}'
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):c.parse_reply(case,raw)

class TransportTests(unittest.TestCase):
    raw=ContractTests.raw
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=c.ROOT/'tmp',prefix='scenario-stage3-test-');self.root=Path(self.temp.name)
        self.bundle=self.root/'bundle';c.prepare(self.bundle)
    def tearDown(self):self.temp.cleanup()
    def registration(self,phase='abstract_diagnostic',synthetic=True):
        path=self.root/(phase+'.json');t.register(self.bundle,path,phase,1,123,synthetic=synthetic);return path
    def fake(self,registration,callback=None):
        lookup={c.data(x['case']['payload']):x['case'] for x in c.read(registration)['trials']};counter=[0]
        def dispatch(payload,key,client_id,timeout):
            counter[0]+=1;self.assertEqual(key,'');self.assertEqual(timeout,60)
            if callback:return callback(counter[0],lookup[payload])
            case=lookup[payload];action=case['diagnosticExpectedAction'] or 'participate'
            return 200,self.raw(action,id='synthetic-'+str(counter[0])).encode(),'synthetic-request-id'
        return dispatch,counter
    def test_bundle_tamper_and_no_overwrite(self):
        self.assertTrue(c.verify(self.bundle)['passed'])
        with self.assertRaises(ValueError):c.prepare(self.bundle)
        f=self.bundle/'cases.json';f.write_bytes(f.read_bytes()+b' ')
        with self.assertRaises(ValueError):c.verify(self.bundle)
    def test_registration_tamper(self):
        reg=self.registration();v=c.read(reg);v['trials'][0]['case']['payload']['temperature']=1
        reg.write_bytes(c.data(v))
        with self.assertRaises(ValueError):t.verify_registration(reg)
    def test_no_dispatch_without_live_opt_in(self):
        reg=self.registration(synthetic=False)
        with patch.object(t,'credential',side_effect=AssertionError('key must not be read')):
            with self.assertRaises(ValueError):t.run(reg,self.root/'out')
        self.assertFalse((self.root/'out').exists())
    def test_synthetic_complete_and_durable_no_resume(self):
        reg=self.registration();fake,count=self.fake(reg)
        result=t.run(reg,self.root/'out',transport=fake);self.assertEqual(result['completed'],18);self.assertEqual(count[0],18)
        self.assertEqual(c.read(self.root/'out/COMPLETE.json')['execution'],'synthetic_test')
        with self.assertRaises(ValueError):t.run(reg,self.root/'out',transport=fake)
    def test_mock_cannot_be_labeled_live(self):
        reg=self.registration(synthetic=False);fake,_=self.fake(reg)
        with self.assertRaises(ValueError):t.run(reg,self.root/'out',True,transport=fake)
    def test_http_failure_preserved_and_not_retried(self):
        reg=self.registration();fake,count=self.fake(reg,lambda *_:(429,b'{"error":{"message":"fixture rate limit"}}','fixture'))
        result=t.run(reg,self.root/'out',transport=fake)
        self.assertEqual(result['reason'],'http_429');self.assertEqual(count[0],1)
        folder=next((self.root/'out/trials').iterdir());self.assertEqual((folder/'response.raw').read_bytes(),b'{"error":{"message":"fixture rate limit"}}')
        self.assertFalse((self.root/'out/COMPLETE.json').exists())
    def test_ambiguous_network_failure_claim_preserved(self):
        reg=self.registration()
        def fail(*_):raise TimeoutError('sensitive exception detail must not be copied')
        result=t.run(reg,self.root/'out',transport=fail);self.assertEqual(result['completed'],0)
        folder=next((self.root/'out/trials').iterdir());self.assertTrue((folder/'CLAIM.json').exists())
        self.assertNotIn('sensitive exception', (folder/'result.json').read_text())
    def test_duplicate_provider_id_stops(self):
        reg=self.registration();fake,count=self.fake(reg,lambda _,case:(200,self.raw(case['diagnosticExpectedAction'] or 'participate',id='same').encode(),'fixture'))
        result=t.run(reg,self.root/'out',transport=fake);self.assertEqual(result['reason'],'duplicate_provider_id');self.assertEqual(count[0],2)
    def test_wrong_diagnostic_action_stops(self):
        reg=self.registration()
        def wrong(_,case):
            action='decline_assistance' if case['diagnosticExpectedAction']=='participate' else 'participate'
            if case['diagnosticExpectedAction'] is None:return 200,self.raw(id=str(_)).encode(),'fixture'
            return 200,self.raw(action,id=str(_)).encode(),'fixture'
        fake,count=self.fake(reg,wrong);result=t.run(reg,self.root/'out',transport=fake)
        self.assertEqual(result['reason'],'diagnostic_wrong_action');self.assertLessEqual(count[0],3)
    def test_reason_sheet_starts_unreviewed_and_synthetic_cannot_qualify(self):
        reg=self.registration();fake,_=self.fake(reg);out=self.root/'out';t.run(reg,out,transport=fake)
        sheet=self.root/'review.json';t.review_template(out,sheet);review=c.read(sheet)
        self.assertEqual(len(review['records']),18);self.assertTrue(all(x['comparisonCorrect'] is None for x in review['records']))
        with self.assertRaises(ValueError):t.gate_evidence(out,sheet,self.bundle)
    def test_live_free_registration_requires_qualified_gates(self):
        for phase in ('abstract_choice','physical_choice'):
            with self.assertRaises(ValueError):t.register(self.bundle,self.root/(phase+'.json'),phase,1,1)
    def test_physical_adapter_round_trip_all_conditions(self):
        reg=self.registration('physical_choice');fake,count=self.fake(reg);result=t.run(reg,self.root/'out',transport=fake)
        self.assertEqual(result['completed'],16);self.assertEqual(count[0],16)
        for folder in (self.root/'out/trials').iterdir():
            record=c.read(folder/'result.json');self.assertEqual(record['parsed']['rawAction'],record['parsed']['parsedAction'])
    def test_physical_diagnostic_round_trip(self):
        reg=self.registration('physical_diagnostic');fake,count=self.fake(reg);result=t.run(reg,self.root/'out',transport=fake)
        self.assertEqual(result['completed'],16);self.assertEqual(count[0],16)
    def test_http_uses_fixed_endpoint_once_without_sdk_retry(self):
        class Response:
            status=400
            def read(self,limit):self.limit=limit;return b'{"error":"unsupported profile fixture"}'
            def getheader(self,name):return 'fixture-id'
        class Connection:
            def __init__(self):self.calls=[];self.closed=False
            def request(self,*args,**kwargs):self.calls.append((args,kwargs))
            def getresponse(self):return Response()
            def close(self):self.closed=True
        connection=Connection()
        with patch.object(t.http.client,'HTTPSConnection',return_value=connection) as factory:
            status,raw,_=t._http(b'{}','fixture-not-a-real-key','fixture-client',60)
        factory.assert_called_once_with('api.openai.com',timeout=60)
        self.assertEqual(status,400);self.assertEqual(len(connection.calls),1);self.assertTrue(connection.closed)
        self.assertEqual(connection.calls[0][0],('POST','/v1/chat/completions'))
    def test_registration_does_not_access_credentials_or_network(self):
        with patch.object(t,'credential',side_effect=AssertionError('No key reads during registration')),patch.object(t,'_http',side_effect=AssertionError('No network during registration')):
            path=self.registration(synthetic=False)
        self.assertEqual(t.verify_registration(path)['phase'],'abstract_diagnostic')
    def test_semantic_gate_tampered_resource_limit_rejected(self):
        path=self.registration();registration=c.read(path);registration['maxGeneratedTokens']+=220
        path.write_bytes(c.data(registration))
        with self.assertRaises(ValueError):t.verify_registration(path)

if __name__=='__main__':unittest.main()
