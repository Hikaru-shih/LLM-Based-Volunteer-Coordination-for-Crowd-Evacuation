import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from individual_analysis import (FACTORS, SYSTEM, analyze, answer, audit, contrasts, curves, digest,
                                 kind, probability, publish, strict_json, validate_plan, verify, write_json)


def fixture(folder, scenarios=None, repetitions=4, outcomes=None):
    """Pure synthetic transport records, never a provider request."""
    scenarios = scenarios or [dict(id='low',nearbyAgentCount=2,exitNonBlockage=.5,volunteerCost=.05,failureCost=.5,unwillingness=5),
                              dict(id='high',nearbyAgentCount=2,exitNonBlockage=.5,volunteerCost=.1,failureCost=.5,unwillingness=5)]
    p=dict(schema='individual-sampling-v1',purpose='Synthetic software validation, not empirical evidence',model='offline-analysis-fixture',
           promptVersion='paper-agent-v5',repetitions=repetitions,orderSeed=2026,maxHttpAttempts=len(scenarios)*repetitions*3,scenarios=scenarios)
    folder.mkdir(parents=True,exist_ok=True);(folder/'trials').mkdir()
    instructions='Task specification: paper-agent-v5; information condition: Core.\nSynthetic test rules only.\n'
    (folder/'instructions.txt').write_text(instructions,encoding='utf-8');(folder/'source.sha256').write_text('a'*64,encoding='utf-8')
    write_json(folder/'plan.json',p)
    reserved=0
    for si,s in enumerate(scenarios):
        seq=(outcomes or {}).get(s['id'],[True,False,'invalid','missing'])
        for rep in range(repetitions):
            outcome=seq[rep % len(seq)]
            if outcome=='missing':continue
            no_game=kind(s)=='NoGame'
            observation=json.dumps({f:s[f] for f in FACTORS})
            body=dict(decision='participate' if outcome is True else 'decline_assistance',explanation='Synthetic only')
            schema={'type':'json_schema','json_schema':{'name':'paper_individual_choice','strict':True,'schema':{
                'type':'object','properties':{'decision':{'type':'string','enum':['participate','decline_assistance']},'explanation':{'type':'string'}},
                'required':['decision','explanation'],'additionalProperties':False}}}
            payload=dict(model=p['model'],messages=[dict(role='system',content=SYSTEM),dict(role='user',content=instructions+'Observation:\n'+observation)],temperature=.15,max_tokens=220,response_format=schema)
            response=dict(choices=[dict(finish_reason='stop',message=dict(role='assistant',content=json.dumps({} if outcome=='invalid' else body)))])
            t=dict(index=si*repetitions+rep,repetition=rep,scenario=s['id'],kind=kind(s),observation=observation,
                   payload='' if no_game else json.dumps(payload),response='' if no_game else json.dumps(response),error='invalid_decision_json' if outcome=='invalid' and not no_game else '',
                   execution='no_game' if no_game else 'synthetic_test',valid=not no_game and outcome!='invalid',willing=not no_game and outcome is True,
                   explanation='' if no_game else body['explanation'],referenceProbability=probability(s),attempts=0,attemptAudit=[],elapsedSeconds=0)
            write_json(folder/'trials'/f"{t['index']:06d}.json",t)
            if not no_game:reserved+=3
    write_json(folder/'ledger.json',dict(reservedAttempts=reserved,binding='b'*64,executionMode='synthetic_test'))
    return p


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        scratch=Path(__file__).resolve().parents[1]/'tmp'
        scratch.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='p3-test-',dir=scratch);self.root=Path(self.temp.name);self.run=self.root/'run';fixture(self.run)
    def tearDown(self):self.temp.cleanup()
    def mutate(self,path,fn):
        p=self.run/path;v=json.loads(p.read_text(encoding='utf-8'));fn(v);write_json(p,v)
    def test_luna_transport_profile(self):
        from individual_analysis import validate_payload
        t=json.loads((self.run/'trials/000000.json').read_text())
        payload=json.loads(t['payload']);payload['model']='gpt-6-luna'
        payload['max_completion_tokens']=payload.pop('max_tokens');payload['reasoning_effort']='none'
        instructions=(self.run/'instructions.txt').read_text()
        validate_payload(json.dumps(payload),t['observation'],'gpt-6-luna',instructions)
        for field,value in [('reasoning_effort','medium'),('max_completion_tokens',221)]:
            bad=dict(payload);bad[field]=value
            with self.assertRaises(ValueError):validate_payload(json.dumps(bad),t['observation'],'gpt-6-luna',instructions)
        payload['max_tokens']=220
        with self.assertRaises(ValueError):validate_payload(json.dumps(payload),t['observation'],'gpt-6-luna',instructions)

    def test_strict_json(self):
        for value in ('{"x":1,"x":2}','{"x":1e999}','{"x":NaN}','{"x":"\\ud800"}','{} tail'):
            with self.subTest(value=value),self.assertRaises((ValueError,UnicodeError)):strict_json(value)
    def test_synthetic_opt_in(self):
        with self.assertRaises(ValueError):audit(self.run)
    def test_quality_and_bounds(self):
        row=audit(self.run,True)['rows'][0]
        self.assertEqual((row['valid'],row['invalid'],row['missing']),(2,1,1))
        self.assertEqual((row['rate'],row['unresolved_lower'],row['unresolved_upper']),(.5,.25,.75))
        self.assertAlmostEqual(row['difference95_low'],row['wilson95_low']-row['reference_probability'])
    def test_raw_choice_tamper(self):
        self.mutate('trials/000000.json',lambda t:t.update(willing=False))
        with self.assertRaises(ValueError):audit(self.run,True)
    def test_invalid_not_silently_repaired(self):
        self.mutate('trials/000000.json',lambda t:t.update(valid=False,error='invented_error'))
        with self.assertRaises(ValueError):audit(self.run,True)
    def test_mixed_model(self):
        def mutate(t):
            payload=json.loads(t['payload']);payload['model']='different';t['payload']=json.dumps(payload)
        self.mutate('trials/000000.json',mutate)
        with self.assertRaises(ValueError):audit(self.run,True)
    def test_changed_prompt(self):
        def mutate(t):
            payload=json.loads(t['payload']);payload['messages'][1]['content']='different';t['payload']=json.dumps(payload)
        self.mutate('trials/000000.json',mutate)
        with self.assertRaises(ValueError):audit(self.run,True)
    def test_mixed_execution(self):
        self.mutate('trials/000000.json',lambda t:t.update(execution='live'))
        with self.assertRaises(ValueError):audit(self.run,True)
    def test_boolean_flags(self):
        self.mutate('trials/000000.json',lambda t:t.update(valid=1))
        with self.assertRaises(ValueError):audit(self.run,True)
    def test_ledger_shortfall(self):
        self.mutate('ledger.json',lambda t:t.update(reservedAttempts=0))
        with self.assertRaises(ValueError):audit(self.run,True)
    def test_reference_wrong(self):
        self.mutate('trials/000000.json',lambda t:t.update(referenceProbability=0))
        with self.assertRaises(ValueError):audit(self.run,True)
    def test_duplicate_state(self):
        p=json.loads((self.run/'plan.json').read_text());p['scenarios'][1].update({f:p['scenarios'][0][f] for f in FACTORS})
        with self.assertRaises(ValueError):validate_plan(p)
    def test_one_factor_only(self):
        data=audit(self.run,True);groups=curves(data['rows']);self.assertEqual(len(groups),1)
        self.assertEqual(groups[0]['factor'],'volunteerCost')
        changed=copy.deepcopy(data['rows']);changed[1]['exitNonBlockage']=.2
        self.assertEqual(curves(changed),[])
    def test_single_separate(self):
        rows=audit(self.run,True)['rows'];single=copy.deepcopy(rows[0]);single.update(nearbyAgentCount=1,stratum='ReferenceBoundary',scenario='solo')
        self.assertFalse(any(g['factor']=='nearbyAgentCount' for g in curves(rows+[single])))
    def test_unpaired_contrast(self):
        data=audit(self.run,True);groups=curves(data['rows']);a,b=groups[0]['points'];b.update(rate=1,wilson95_low=.5,wilson95_high=1)
        c=contrasts(groups)[0];self.assertEqual(c['observed_change'],.5)
        self.assertLess(c['change95_low'],c['observed_change']);self.assertGreaterEqual(c['change95_high'],c['observed_change'])
        self.assertAlmostEqual(c['response_deviation'],.5-c['reference_change'])
    def test_all_missing_and_no_game(self):
        run=self.root/'empty';s=dict(id='no_game',nearbyAgentCount=0,exitNonBlockage=.5,volunteerCost=.05,failureCost=.5,unwillingness=5)
        fixture(run,scenarios=[s],outcomes={'no_game':['missing']})
        d=audit(run,True);self.assertIsNone(d['rows'][0]['rate']);self.assertEqual(d['rows'][0]['missing'],4);self.assertEqual(curves(d['rows']),[])
    def test_protocol_refusal_truncation_duplicate(self):
        raw=json.loads((self.run/'trials/000000.json').read_text())['response']
        for changed in (raw.replace('"stop"','"length"'),raw.replace('"role": "assistant"','"role": "user"'),raw.replace('"finish_reason":','"finish_reason":"stop","finish_reason":')):
            self.assertIsNone(answer(changed)[0])
    def test_interruption_count_not_choices(self):
        write_json(self.run/'ledger.json',dict(reservedAttempts=21,binding='b'*64,executionMode='synthetic_test'))
        (self.run/'interruptions.jsonl').write_text(json.dumps(dict(index=0,execution='interrupted_unknown_result'))+'\n')
        data=audit(self.run,True);self.assertEqual(len(data['interruptions']),1);self.assertEqual(data['rows'][0]['valid'],2)
    def test_end_to_end_and_publication(self):
        output=self.root/'report';analyze(self.run,output,True)
        self.assertTrue((output/'REPORT.md').is_file());self.assertTrue(list((output/'figures').glob('*.png')));self.assertTrue(list((output/'figures').glob('*.pdf')))
        manifest=json.loads((output/'manifest.json').read_text());self.assertTrue(all(digest(output/f['path'])==f['sha256'] for f in manifest['files']))
        self.assertIn('SYNTHETIC VALIDATION',(output/'REPORT.md').read_text(encoding='utf-8'))
        records=self.root/'records';records.mkdir();notebook=records/'EXPERIMENT_LOG.md';notebook.write_text('Manual notes\n<!-- AUTO-RECORDED RUNS -->\nAutomatic tail\n')
        self.assertTrue(publish(output,records));self.assertTrue(publish(output,records));text=notebook.read_text(encoding='utf-8');self.assertEqual(text.count('### analysis_'),1);self.assertTrue(text.endswith('Automatic tail\n'))
        with self.assertRaises(ValueError):analyze(self.run,output,True)
    def test_publication_pending_retry(self):
        output=self.root/'report';analyze(self.run,output,True);records=self.root/'records';records.mkdir()
        (records/'EXPERIMENT_LOG.md').write_text('Missing marker')
        self.assertFalse(publish(output,records));self.assertTrue((output/'publication_pending.json').exists())
        (records/'EXPERIMENT_LOG.md').write_text('Preserved\n<!-- AUTO-RECORDED RUNS -->\n')
        self.assertTrue(publish(output,records));self.assertFalse((output/'publication_pending.json').exists())
    def test_failed_render_not_completed_report(self):
        output=self.root/'report'
        with patch('individual_analysis.plots',side_effect=RuntimeError('synthetic render failure')),self.assertRaises(RuntimeError):analyze(self.run,output,True)
        self.assertFalse(output.exists());self.assertTrue(list(self.root.glob('report.pending-*')))
        self.assertEqual(audit(self.run,True)['rows'][0]['rate'],.5)
    def test_no_estimate_contrast(self):
        groups=curves(audit(self.run,True)['rows']);groups[0]['points'][1].update(valid=0,rate=None)
        c=contrasts(groups)[0];self.assertIsNone(c['observed_change']);self.assertIsNone(c['change95_low'])
    def test_existing_unity_exports(self):
        base=Path(__file__).resolve().parents[1]/'experiment_records/data/validation/settings_research_v1/sampling_regression'
        if not base.exists():self.skipTest('Optional preserved Unity validation artifacts unavailable')
        for name in ('complete','positive','budget','interrupted','invalid_response'):
            with self.subTest(name=name):self.assertEqual(len(audit(base/name,True)['rows']),3)
    def test_api_audit_with_unknown_usage(self):
        self.mutate('ledger.json',lambda t:t.update(executionMode='api'))
        for file in (self.run/'trials').glob('*.json'):
            t=json.loads(file.read_text());t.update(execution='live',attempts=1,attemptAudit=[dict(attempt=1,status=200,error='',elapsedSeconds=.1)]);write_json(file,t)
        data=audit(self.run);self.assertEqual(data['rows'][0]['http_attempts'],3);self.assertEqual(data['rows'][0]['usage_records'],0)
    def test_no_game_not_refusal(self):
        folder=self.root/'control';s=dict(id='control',nearbyAgentCount=2,exitNonBlockage=1,volunteerCost=.05,failureCost=.5,unwillingness=5)
        fixture(folder,scenarios=[s],outcomes={'control':[False]})
        data=audit(folder,True);self.assertEqual(data['rows'][0]['no_game'],4);self.assertIsNone(data['rows'][0]['rate']);self.assertEqual(data['rows'][0]['invalid'],0)
    def test_manifest_tamper(self):
        output=self.root/'report';analyze(self.run,output,True)
        (output/'REPORT.md').write_text('changed')
        with self.assertRaises(ValueError):verify(output)
    def test_provider_model_drift(self):
        for i,name in [(0,'provider-version-a'),(1,'provider-version-b')]:
            def mutate(t):
                envelope=json.loads(t['response']);envelope['model']=name;t['response']=json.dumps(envelope)
            self.mutate(f'trials/{i:06d}.json',mutate)
        with self.assertRaises(ValueError):audit(self.run,True)
    def test_reported_usage(self):
        def mutate(t):
            envelope=json.loads(t['response']);envelope.update(model='provider-v1',usage=dict(total_tokens=123));t['response']=json.dumps(envelope)
        self.mutate('trials/000000.json',mutate)
        data=audit(self.run,True);self.assertEqual(data['providerModels'],['provider-v1']);self.assertEqual(data['rows'][0]['provider_tokens_known'],123);self.assertEqual(data['rows'][0]['usage_records'],1)
    def test_three_all_or_none_choices_render(self):
        run=self.root/'boundary_run'
        fixture(run,repetitions=3,outcomes={'low':[True],'high':[False]})
        data,_=analyze(run,self.root/'boundary_report',True)
        self.assertEqual([r['rate'] for r in data['rows']],[1,0])
        self.assertEqual(data['rows'][1]['wilson95_low'],0)
        self.assertTrue(verify(self.root/'boundary_report'))


if __name__=='__main__':unittest.main()
