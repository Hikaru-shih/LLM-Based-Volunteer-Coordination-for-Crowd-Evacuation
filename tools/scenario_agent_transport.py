"""Explicit, one-attempt transport for stage-3 contracts. Default commands never call API."""
import argparse
import csv
import datetime
import http.client
import json
import os
from pathlib import Path
import random
import time
import uuid
import scenario_agent_contract as c

ENDPOINT='https://api.openai.com/v1/chat/completions'
MAX_BODY=1024*1024

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def notebook_event(reg,output,event,details):
    """Automatically record real campaigns, without logging credentials or synthetic fixtures."""
    import msvcrt
    log=c.ROOT/'experiment_records/EXPERIMENT_LOG.md'
    token=c.sha((output/'registration.snapshot.json').read_bytes())[:16]
    title=f"## S3-{token}-{event} — Scenario decision {event}"
    relative=str(output.resolve().relative_to(c.ROOT)).replace('\\','/')
    entry=title+'\n\nUTC: '+now()+'. Purpose: '+reg['purpose']+'. Phase: '+reg['phase']+'.\n\n'+details+' Artifacts: '+relative+'. No human-validity claim.\n\n'
    with (c.ROOT/'experiment_records/.notebook.lock').open('a+b') as gate:
        gate.seek(0)
        if not gate.read(1):gate.write(b'0');gate.flush()
        gate.seek(0);msvcrt.locking(gate.fileno(),msvcrt.LK_NBLCK,1)
        try:
            text=log.read_text(encoding='utf-8');marker='<!-- AUTO-RECORDED RUNS -->'
            c.require(marker in text,'Notebook publication marker missing')
            if title not in text:
                tail=text.split(marker,1)[1];text=text.replace(marker,entry+marker,1)
                c.require(text.split(marker,1)[1]==tail,'Automatic notebook tail changed')
                temporary=log.with_suffix('.scenario-stage3.tmp')
                with temporary.open('w',encoding='utf-8',newline='') as f:f.write(text);f.flush();os.fsync(f.fileno())
                os.replace(temporary,log)
        finally:gate.seek(0);msvcrt.locking(gate.fileno(),msvcrt.LK_UNLCK,1)

def gate_evidence(run_folder,review_file,bundle):
    """Recheck raw live responses and every manual reason judgment, not a user-set pass flag."""
    registration=verify_registration(run_folder/'registration.snapshot.json',bundle)
    c.require(registration['phase'] in ('abstract_diagnostic','physical_diagnostic'),'Not a diagnostic registration')
    complete=c.read(run_folder/'COMPLETE.json')
    c.require(complete['execution']=='live' and complete['completed']==len(registration['trials']),'Gate incomplete or synthetic')
    review=c.read(review_file)
    c.require(review['registrationSHA256']==c.sha((run_folder/'registration.snapshot.json').read_bytes()),'Unbound reason review')
    records=review['records'];c.require(len(records)==len(registration['trials']),'Incomplete reason review')
    by_id={r['trialID']:r for r in records};c.require(len(by_id)==len(records),'Duplicate reason review')
    provider_ids=set()
    for trial in registration['trials']:
        folder=run_folder/'trials'/trial['trialID'];record=c.read(folder/'result.json');raw=(folder/'response.raw').read_bytes()
        c.require(record['execution']=='live' and record['httpStatus']==200 and record['valid'] and not record['secretRedacted'],'Invalid gate record')
        c.require(record['payloadSHA256']==trial['case']['payloadSHA256'] and record['responseSHA256']==c.sha(raw),'Raw/payload binding mismatch')
        parsed=c.parse_reply(trial['case'],raw.decode('utf-8'))
        c.require(parsed==record['parsed'],'Gate action mapping drift')
        c.require(parsed['providerID'] not in provider_ids,'Repeated provider response ID');provider_ids.add(parsed['providerID'])
        c.require(parsed['diagnosticActionCorrect'] is not False,'Diagnostic wrong action')
        row=by_id[trial['trialID']]
        c.require(row['rawSHA256']==c.sha(raw) and isinstance(row.get('reviewer'),str) and row['reviewer'].strip(),'Missing reviewer or raw binding')
        c.require(row['rawAction']==parsed['rawAction'] and row['reasonText']==parsed['explanation'],'Review text/action differs from bound raw response')
        c.require(row.get('comparisonCorrect') is True and row.get('explicitActionReasonConflict') is False,'Reason comparison failed/unreviewed')
        c.require(isinstance(row.get('note'),str) and row['note'].strip(),'Missing review note')
    return {'phase':registration['phase'],'registrationSHA256':review['registrationSHA256'],'reviewSHA256':c.sha(review_file.read_bytes()),'completed':len(records),'humanIndependentReview':False,'runPath':str(run_folder.resolve()),'reviewPath':str(review_file.resolve())}

def register(bundle,target,phase,repetitions,order_seed,gate_reviews=(),synthetic=False):
    c.verify(bundle);c.require(phase in c.PHASES,'Unknown phase')
    c.require(type(repetitions) is int and 1<=repetitions<=100,'Invalid repetition count')
    c.require(not target.exists(),'Preserve prior registration')
    evidence=[]
    if phase.endswith('_choice') and not synthetic:
        for folder,review in gate_reviews:evidence.append(gate_evidence(Path(folder),Path(review),bundle))
        needed={'abstract_diagnostic'} if phase=='abstract_choice' else {'abstract_diagnostic','physical_diagnostic'}
        c.require({e['phase'] for e in evidence}==needed,'Free phase requires matching complete live semantic gates and reason reviews')
    selected=[x for x in c.read(bundle/'cases.json') if x['phase']==phase]
    trials=[{'trialID':f"{x['caseID']}_r{i:03d}",'case':x,'repetition':i} for x in selected for i in range(1,repetitions+1)]
    random.Random(order_seed).shuffle(trials)
    c.require(0<len(trials)<=1000,'Invalid campaign size')
    registration={'schema':'scenario-interface-registration-v1','registeredAtUtc':now(),'purpose':'Stage3 isolated development/pilot, not formal or human evidence',
        'bundlePath':str(bundle.resolve()),'bundleSHA256':c.sha((bundle/'INTERFACE.json').read_bytes()),'phase':phase,'repetitions':repetitions,'orderSeed':order_seed,
        'execution':'synthetic_test' if synthetic else 'live','providerAvailabilityVerified':False,'model':c.MODEL,'endpoint':ENDPOINT,'attemptsPerTrial':1,
        'maxAttempts':len(trials),'maxGeneratedTokens':220*len(trials),'maxPayloadBytes':sum(len(c.data(t['case']['payload'])) for t in trials),
        'timeoutSeconds':60,'wallSeconds':max(120,65*len(trials)),'automaticRetries':0,'stopRule':'Stop on first invalid/network/model/duplicate-ID error. No automatic resume, refill or overwrite.',
        'costDisclosure':'Fixed request and output ceilings, not a dollar-price guarantee. Input usage and account pricing remain provider-side.',
        'gateEvidence':evidence,'trials':trials}
    target.parent.mkdir(parents=True,exist_ok=True);c.write_new(target,registration)
    return {'registered':True,'phase':phase,'trials':len(trials),'execution':registration['execution'],'newAPICalls':0,'registrationSHA256':c.sha(target.read_bytes())}

def verify_registration(path,bundle=None):
    reg=c.read(path);bundle=Path(reg['bundlePath']) if bundle is None else bundle
    c.require(bundle.resolve().is_relative_to(c.ROOT),'Bundle must remain in workspace')
    c.verify(bundle)
    c.require(reg['bundleSHA256']==c.sha((bundle/'INTERFACE.json').read_bytes()),'Registration bundle drift')
    c.require(reg['schema']=='scenario-interface-registration-v1' and reg['endpoint']==ENDPOINT and reg['model']==c.MODEL,'Transport identity drift')
    c.require(reg['attemptsPerTrial']==1 and reg['automaticRetries']==0 and reg['timeoutSeconds']==60,'Transport policy drift')
    c.require(reg['phase'] in c.PHASES and type(reg['repetitions']) is int and 1<=reg['repetitions']<=100,'Invalid registered phase/count')
    selected=[x for x in c.read(bundle/'cases.json') if x['phase']==reg['phase']]
    expected=[{'trialID':f"{x['caseID']}_r{i:03d}",'case':x,'repetition':i} for x in selected for i in range(1,reg['repetitions']+1)]
    random.Random(reg['orderSeed']).shuffle(expected)
    c.require(reg['trials']==expected and len(expected)==reg['maxAttempts']<=1000,'Registered payload/order drift')
    c.require(reg['maxGeneratedTokens']==220*len(expected) and reg['maxPayloadBytes']==sum(len(c.data(t['case']['payload'])) for t in expected),'Resource bound drift')
    c.require(reg['wallSeconds']==max(120,65*len(expected)),'Wall budget drift')
    if reg['execution']=='live' and reg['phase'].endswith('_choice'):
        needed={'abstract_diagnostic'} if reg['phase']=='abstract_choice' else {'abstract_diagnostic','physical_diagnostic'}
        c.require(len(reg['gateEvidence'])==len(needed) and {x['phase'] for x in reg['gateEvidence']}==needed,'Missing or duplicate live gate qualifications')
    return reg

def _http(request,key,client_id,timeout):
    # No SDK retries, environment proxies, redirect following, or dynamic endpoints.
    connection=http.client.HTTPSConnection('api.openai.com',timeout=timeout)
    try:
        connection.request('POST','/v1/chat/completions',body=request,
            headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','X-Client-Request-Id':client_id})
        response=connection.getresponse();body=response.read(MAX_BODY+1)
        return response.status,body,response.getheader('x-request-id')
    finally:connection.close()

def credential():
    key=os.environ.get('OPENAI_API_KEY','').strip()
    if not key:
        path=c.ROOT/'openai-key.local.txt'
        c.require(path.resolve().is_relative_to(c.ROOT),'Credential path escaped workspace')
        key=path.read_text(encoding='utf-8-sig').strip()
    c.require(key.startswith('sk-') and len(key)>20 and not any(x.isspace() for x in key),'Local credential unavailable or invalid')
    return key

def run(registration_file,output,confirm_live=False,transport=None):
    reg=verify_registration(registration_file)
    synthetic=transport is not None
    c.require(reg['execution']==('synthetic_test' if synthetic else 'live'),'Injected transport cannot be represented as live')
    c.require(synthetic or confirm_live,'Live dispatch requires --confirm-live')
    c.require(output.resolve().is_relative_to(c.ROOT),'Campaign output must stay in workspace')
    c.require(not output.exists(),'Output already exists: inspect, never automatically rerun or resume')
    if not synthetic and reg['phase'].endswith('_choice'):
        # Revalidate qualification files at dispatch, not merely a pass flag copied into JSON.
        for evidence in reg['gateEvidence']:
            c.require('runPath' in evidence and 'reviewPath' in evidence,'Missing durable gate evidence paths')
            current=gate_evidence(Path(evidence['runPath']),Path(evidence['reviewPath']),Path(reg['bundlePath']))
            c.require(all(current[k]==evidence[k] for k in current),'Gate evidence changed before dispatch')
    key='' if synthetic else credential()
    output.mkdir(parents=True);(output/'trials').mkdir()
    # Existing directory is a durable claim, including after a crash before an HTTP response.
    with (output/'registration.snapshot.json').open('xb') as f:f.write(registration_file.read_bytes());f.flush();os.fsync(f.fileno())
    c.write_new(output/'STARTED.json',{'atUtc':now(),'execution':reg['execution'],'registrationSHA256':c.sha(registration_file.read_bytes()),'maxAttempts':reg['maxAttempts']})
    if not synthetic:notebook_event(reg,output,'started','Prospective phase registration preserved; no retries or automatic resume. Request claims are reservations, not confirmed provider dispatches.')
    started=time.monotonic();ids=set();completed=0
    for index,trial in enumerate(reg['trials']):
        if time.monotonic()-started>reg['wallSeconds']:
            c.write_new(output/'STOPPED.json',{'reason':'wall_limit','completed':completed,'atUtc':now()})
            if not synthetic:notebook_event(reg,output,'stopped',f'Wall limit. Completed {completed}. All recorded trials retained; no refill.')
            return {'outcome':'stopped','completed':completed}
        folder=output/'trials'/trial['trialID'];folder.mkdir()
        client_id=str(uuid.uuid4());request=c.data(trial['case']['payload'])
        c.write_new(folder/'CLAIM.json',{'index':index,'atUtc':now(),'payloadSHA256':trial['case']['payloadSHA256'],'clientRequestID':client_id,'execution':reg['execution'],'attempt':1})
        begin=time.monotonic();status=0;raw=b'';provider_request_id=None;parsed=None;error=None;redacted=False
        try:
            status,raw,provider_request_id=(transport or _http)(request,key,client_id,reg['timeoutSeconds'])
            c.require(isinstance(raw,bytes),'Transport must preserve response bytes')
            if key and key.encode() in raw:
                raw=raw.replace(key.encode(),b'[REDACTED_CREDENTIAL]');redacted=True
            with (folder/'response.raw').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            c.require(len(raw)<=MAX_BODY,'oversize_response')
            c.require(not redacted,'credential_echo_redacted')
            c.require(status==200,'http_'+str(status))
            parsed=c.parse_reply(trial['case'],raw.decode('utf-8'))
            c.require(parsed['providerID'] not in ids,'duplicate_provider_id')
            ids.add(parsed['providerID'])
            # A diagnostic failure stops immediately; ties remain valid choices.
            c.require(parsed['diagnosticActionCorrect'] is not False,'diagnostic_wrong_action')
        except Exception as exc:
            # Never serialize arbitrary exception text which may contain authorization material.
            error=type(exc).__name__
            if isinstance(exc,ValueError) and str(exc) in {'invalid_response_contract','missing_or_oversize_explanation','provider_model_drift','missing_provider_id','duplicate_provider_id','diagnostic_wrong_action','oversize_response','credential_echo_redacted'}:error=str(exc)
            elif status!=200 and status!=0:error='http_'+str(status)
        result={'execution':reg['execution'],'trialID':trial['trialID'],'atUtc':now(),'httpStatus':status,
                'payloadSHA256':trial['case']['payloadSHA256'],'responseSHA256':c.sha(raw),'providerRequestID':provider_request_id,
                'clientElapsedSeconds':time.monotonic()-begin,'secretRedacted':redacted,'valid':error is None,'errorCode':error,'parsed':parsed}
        c.write_new(folder/'result.json',result)
        if error is not None:
            c.write_new(output/'STOPPED.json',{'reason':error,'failedTrial':trial['trialID'],'completed':completed,'reservedAttempts':index+1,'atUtc':now()})
            if not synthetic:notebook_event(reg,output,'stopped',f'Completed {completed}; reservations {index+1}; stop code {error}. Raw invalid/error records retained. No automatic rerun.')
            return {'outcome':'stopped','completed':completed,'reason':error}
        completed+=1
    c.write_new(output/'COMPLETE.json',{'execution':reg['execution'],'completed':completed,'reservedAttempts':len(reg['trials']),'atUtc':now(),'reasonReviewCompleted':False})
    if not synthetic:notebook_event(reg,output,'completed',f'Completed {completed}; reservations {len(reg["trials"])}. Reason review remains pending. Completion alone does not qualify a semantic gate.')
    return {'outcome':'completed','completed':completed,'execution':reg['execution'],'reasonReviewCompleted':False}

def review_template(run_folder,target):
    c.require(not target.exists(),'Preserve existing reason review')
    reg=verify_registration(run_folder/'registration.snapshot.json');records=[]
    for trial in reg['trials']:
        folder=run_folder/'trials'/trial['trialID']
        if not (folder/'result.json').exists():continue
        result=c.read(folder/'result.json')
        if not result['valid']:continue
        parsed=result['parsed']
        records.append({'trialID':trial['trialID'],'phase':trial['case']['phase'],'scenario':trial['case']['scenario'],'information':trial['case']['information'],'rawSHA256':result['responseSHA256'],'rawAction':parsed['rawAction'],
            'reasonText':parsed['explanation'],'labels':[],'evidenceSpans':{},'comparisonCorrect':None,
            'explicitActionReasonConflict':None,'reviewer':'','note':'','codebookVersion':'scenario-reasons-v2-draft','reviewStatus':'unreviewed'})
    c.write_new(target,{'registrationSHA256':c.sha((run_folder/'registration.snapshot.json').read_bytes()),'records':records,'independentHumanReview':False})
    return {'rows':len(records),'reviewed':0}

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('register');p.add_argument('bundle',type=Path);p.add_argument('target',type=Path);p.add_argument('--phase',choices=c.PHASES,required=True);p.add_argument('--repetitions',type=int,required=True);p.add_argument('--order-seed',type=int,required=True);p.add_argument('--gate-review',nargs=2,action='append',default=[])
    p=sub.add_parser('run');p.add_argument('registration',type=Path);p.add_argument('output',type=Path);p.add_argument('--confirm-live',action='store_true')
    p=sub.add_parser('review-template');p.add_argument('run',type=Path);p.add_argument('target',type=Path)
    args=parser.parse_args()
    if args.command=='register':result=register(args.bundle,args.target,args.phase,args.repetitions,args.order_seed,args.gate_review)
    elif args.command=='run':result=run(args.registration,args.output,args.confirm_live)
    else:result=review_template(args.run,args.target)
    print(json.dumps(result,indent=2))
    if result.get('outcome')=='stopped':raise SystemExit(1)
if __name__=='__main__':main()
