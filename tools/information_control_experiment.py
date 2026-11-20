"""Prospectively locked information-control follow-up. No implicit API or retries."""
import argparse,copy,csv,datetime,hashlib,json,os,random,re,sys,time,uuid
from pathlib import Path
import scenario_agent_contract as c
import scenario_agent_transport as transport
R=Path(__file__).resolve().parents[1]
PRE=R/'experiment_records/study_preparations/information_control_v1_20261120'
OUT=R/'experiment_records/data/information_control_v1_20261120'
OLD=R/'experiment_records/data/scenario_formal_v1_20261116/registration.snapshot.json'
CAMPAIGN='P031_INFORMATION_CONTROL_20261120'
INFOS=('geometry_only','length_control','calibrated_forecast')
ORDERS=('participate_first','decline_first')
TOKENIZER=R/'report/.build/api_tokenizer';CACHE=R/'report/.build/tokenizer_cache'
def read(p):return c.read(p)
def sha(p):return c.sha(p.read_bytes())
def write(p,x):c.write_new(p,x)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def encoding():
    sys.path.insert(0,str(TOKENIZER));os.environ['TIKTOKEN_CACHE_DIR']=str(CACHE)
    import tiktoken
    return tiktoken.get_encoding('o200k_base')
def metrics(text,enc):
    return {'proxyTokens':len(enc.encode(text)),'characters':len(text),'words':len(re.findall(r"\b[A-Za-z_]+\b",text)),'numericLiterals':len(re.findall(r'(?<![A-Za-z_])\d+(?:\.\d+)?',text))}
def reverse(text):
    assert text.count('Actions are participate and decline_assistance.')==1
    assert text.count('decision must be participate or decline_assistance.')==1
    return text.replace('Actions are participate and decline_assistance.','Actions are decline_assistance and participate.').replace('decision must be participate or decline_assistance.','decision must be decline_assistance or participate.')
def administrative_control(geometry,forecast,enc,seed):
    # Match decimal shapes, not values or conditional advantages. No action/person labels.
    rng=random.Random(seed)
    fs=json.loads(forecast.split('Forecasts:\n',1)[1]);records=[]
    def nominal(v):
        s=str(v);return float(''.join(str(rng.randrange(1,10)) if i==0 else str(rng.randrange(10)) if ch.isdigit() else ch for i,ch in enumerate(s)))
    for i,f in enumerate(fs):
        records.append({'catalogueGroupLabel':'archive_alpha' if i<2 else 'archive_beta','printedRecordPosition':'first_slot' if i%2==0 else 'second_slot',
            'printedCatalogueIndices':{a:nominal(f['ownCappedExitSteps'][b]) for a,b in [('primary','mean'),('secondary','observedMin'),('tertiary','observedMax')]},
            'printedArchiveReference':{a:nominal(f['otherNineMeanCappedExitSteps'][b]) for a,b in [('primary','mean'),('secondary','observedMin'),('tertiary','observedMax')]},'catalogueRecordCount':6})
    control=geometry+'\nThe following printed catalogue records are unrelated administrative examples. They are not observations or predictions about this scenario and provide no information about either action or any pedestrian. Archive labels and record slots are arbitrary identifiers. Decimal strings are catalogue text, not quantities from this simulation. Values and order have no implied ranking. Do not map a record to a person, location, movement or event. These records illustrate a document format for indexing archive labels. Print code: 846. Revision code: 217.\nCatalogue records:\n'+json.dumps(records)
    target=len(enc.encode(forecast))
    # Add neutral archival format prose; choose complete words, never truncate encoded bytes.
    sentences=('The catalogue lists folder labels in print order.','Each entry belongs to this filing example.','Headings identify sections of the paper index.','Printed labels can be copied between archive pages.','Margins are part of the document layout.','The entries use a standard filing format.','These are catalogue labels.','End of catalogue.','File label.','End.')
    control+='\nIndexing note:';used=set()
    while target-len(enc.encode(control))>1:
        options=[(i,s) for i,s in enumerate(sentences) if i not in used and len(enc.encode(control+' '+s))<=target]
        if not options:options=[(i,s) for i,s in enumerate(sentences) if len(enc.encode(control+' '+s))<=target]
        assert options,'No complete neutral sentence fits proxy-token target'
        i,s=options[0];control+=' '+s;used.add(i)
    m=metrics(control,enc);f=metrics(forecast,enc)
    assert abs(m['proxyTokens']-f['proxyTokens'])<=1
    return control
def build_cases(enc):
    reg=read(OLD);old={t['case']['caseID']:t['case'] for t in reg['trials']}
    cases=[];audit=[]
    for b in (2,3,4,5):
        for m in (1,4):
            scenario=f'B{b}_M{m}';g=old[f'PC_{scenario}_geometry_only'];f=old[f'PC_{scenario}_calibrated_forecast']
            gt=g['payload']['messages'][1]['content'];ft=f['payload']['messages'][1]['content']
            ct=administrative_control(gt,ft,enc,2026112000+b*10+m)
            for order in ORDERS:
                for info,text in [('geometry_only',gt),('length_control',ct),('calibrated_forecast',ft)]:
                    payload=copy.deepcopy(g['payload']);payload['messages'][1]['content']=text if order==ORDERS[0] else reverse(text)
                    case={'caseID':f'IC_{scenario}_{info}_{order}','phase':'physical_choice','scenario':scenario,'information':info,'optionOrder':order,'payload':payload,'payloadSHA256':c.sha(c.data(payload)),'diagnosticExpectedAction':None,'metadata':{'priorFormalChoicesNotPooled':True,'matchedProxy':'o200k_base; exact provider tokenizer not independently established'}}
                    cases.append(case)
            cm=metrics(ct,enc);fm=metrics(ft,enc)
            audit.append({'scenario':scenario,'geometry':metrics(gt,enc),'length_control':cm,'forecast':fm,'characterRatio':cm['characters']/fm['characters'],'wordRatio':cm['words']/fm['words']})
    assert len(cases)==48
    return cases,audit
def source_files():return [Path(__file__),R/'tools/test_information_control.py',R/'tools/analyze_information_control.py',R/'tools/scenario_agent_contract.py',R/'tools/scenario_agent_transport.py',R/'tools/individual_analysis.py',OLD]
def freeze():
    assert not PRE.exists(),'Preserve previous preparation'
    enc=encoding();cases,audit=build_cases(enc)
    for a in audit:
        assert .90<=a['characterRatio']<=1.10,('Character mismatch',a)
        assert .75<=a['wordRatio']<=1.25,('Word mismatch',a)
    rng=random.Random(2026112001);trials=[]
    for block in range(1,11):
        batch=[{'trialID':f'{CAMPAIGN}_b{block:03d}_{case["caseID"]}','block':block,'case':case} for case in cases];rng.shuffle(batch);trials+=batch
    PRE.mkdir(parents=True)
    design={'schema':'information-control-followup-v1','campaignID':CAMPAIGN,'registeredAtUtc':now(),'purpose':'Prospective follow-up after observing P030: separate decision-relevant forecasts from a matched administrative information package and test option presentation order. Not a replication independent of prior findings.',
      'model':'gpt-6-luna','temperature':.15,'reasoning_effort':'none','max_completion_tokens':220,'settings':8,'informationConditions':list(INFOS),'orders':list(ORDERS),'completeSchedulingBlocks':10,'trialsPerCell':10,'trialsPerSettingInformation':20,'totalRequests':480,'orderSeed':2026112001,
      'primaryEstimands':['forecast minus length_control willingness, averaged over all eight settings and two orders','forecast minus geometry willingness, averaged over all eight settings and two orders'],
      'secondaryEstimands':['length_control minus geometry','decline_first minus participate_first within each information condition','difference of forecast-control contrast across option orders'],
      'plannedSubgroups':['B2-B4','B5'],'analysis':'Complete-block means; 5000 block-bootstrap percentile resamples, seed 2026112002. Pointwise descriptive 95% intervals; no p-values, power/equivalence claim, independent-person claim or historical pooling. Ten blocks give limited interval stability. All valid free choices retained regardless of reason quality.',
      'control':'Fixed unrelated printed catalogue records. Artificial administrative numbers follow decimal-shape distributions but do not encode the forecast values. Match entire user-message o200k_base proxy tokens to within one; character ratio .90-1.10 and lexical-word ratio .75-1.25. Proxy is not established as the provider tokenizer. Actual returned prompt-token counts audited without post-outcome editing. One control topic only, so residual semantic and attention effects remain.',
      'counterbalance':'Reverse both explicit action enumerations in COMMON; keep action codes, system role, JSON schema, remaining prose and model constant. Tests presentation-order sensitivity, not all semantic/social-desirability bias.',
      'qualification':'Previous successful diagnostic records are context only, not a claim that the new control or current provider passed a fresh semantic gate. New software tests check matching, counterbalance, scheduling and strict parsing before dispatch. No correctness labels are assigned to free choices.',
      'transport':{'endpoint':transport.ENDPOINT,'execution':'live','attemptsPerTrial':1,'automaticRetries':0,'timeoutSeconds':60,'wallSeconds':10800,'workers':1,'maxGeneratedTokens':105600,'failureRule':'Stop on first HTTP/network/unknown-result/schema/refusal/model-identity/duplicate-ID/source-drift error. Preserve partial data; no automatic rerun, refill or resumption. Valid weak explanations do not trigger stopping.'},
      'pricing':'Uses the existing configured OpenAI API credential and frozen requested model. No free-model substitution. Token ceilings are not a dollar-price promise.','oldEvidence':{'campaign':'P030','choices':840,'pooled':False},'newUnityRuns':0,'humanValidation':False,
      'documentationChecked':['https://developers.openai.com/api/docs/guides/structured-outputs','https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create']}
    registration={'schema':'information-control-registration-v1','registeredAtUtc':design['registeredAtUtc'],'campaignID':CAMPAIGN,'purpose':design['purpose'],'execution':'live','phase':'information_control_followup','endpoint':transport.ENDPOINT,'model':design['model'],'maxAttempts':480,'maxGeneratedTokens':105600,'timeoutSeconds':60,'wallSeconds':10800,'trials':trials}
    write(PRE/'design.json',design);write(PRE/'registration.json',registration);write(PRE/'PROMPT_MATCH_AUDIT.json',audit)
    seal={'schema':'information-control-seal-v1','campaignID':CAMPAIGN,'registeredAtUtc':now(),'designSHA256':sha(PRE/'design.json'),'registrationSHA256':sha(PRE/'registration.json'),'matchAuditSHA256':sha(PRE/'PROMPT_MATCH_AUDIT.json'),'sources':{str(p.relative_to(R)).replace('\\','/'):sha(p) for p in source_files()},'tokenizerProxy':'o200k_base; tiktoken 0.14.0','trials':480}
    seal['lockID']=c.sha(c.data(seal));write(PRE/'SEAL.json',seal)
    return verify()
def verify():
    seal=read(PRE/'SEAL.json');unsigned={k:v for k,v in seal.items() if k!='lockID'};assert c.sha(c.data(unsigned))==seal['lockID']
    assert sha(PRE/'design.json')==seal['designSHA256'] and sha(PRE/'registration.json')==seal['registrationSHA256'] and sha(PRE/'PROMPT_MATCH_AUDIT.json')==seal['matchAuditSHA256']
    for name,digest in seal['sources'].items():assert sha(R/name)==digest,('Frozen source drift',name)
    reg=read(PRE/'registration.json');assert len(reg['trials'])==reg['maxAttempts']==480
    assert len({t['trialID'] for t in reg['trials']})==480
    for trial in reg['trials']:assert c.sha(c.data(trial['case']['payload']))==trial['case']['payloadSHA256']
    return {'verified':True,'campaignID':CAMPAIGN,'requests':480,'lockID':seal['lockID'],'newAPICalls':0}
def run(confirm=False):
    assert confirm,'Explicit live flag required';verify();assert not OUT.exists(),'Existing run cannot be resumed or resent'
    claim=R/'experiment_records/scenario_execution_claims'/f'{CAMPAIGN}.json';claim.parent.mkdir(exist_ok=True,parents=True)
    key=transport.credential() # Never print or persist credential contents.
    write(claim,{'campaignID':CAMPAIGN,'lockID':read(PRE/'SEAL.json')['lockID'],'atUtc':now(),'output':str(OUT),'meaning':'Exclusive reservation, not proof of HTTP dispatch; never automatically clear.'})
    OUT.mkdir();(OUT/'trials').mkdir();(OUT/'registration.snapshot.json').write_bytes((PRE/'registration.json').read_bytes());write(OUT/'SEAL.snapshot.json',read(PRE/'SEAL.json'))
    reg=read(PRE/'registration.json');write(OUT/'STARTED.json',{'execution':'live','atUtc':now(),'maxAttempts':480});transport.notebook_event(reg,OUT,'started','Prospectively locked 480-request information-control follow-up; one attempt, same paid API configuration, no historical pooling. Original 840 records remain unchanged.')
    begin=time.monotonic();ids=set();completed=0;tokens={'prompt_tokens':0,'completion_tokens':0,'total_tokens':0}
    for index,trial in enumerate(reg['trials']):
        if time.monotonic()-begin>reg['wallSeconds']:
            error='wall_limit';write(OUT/'STOPPED.json',{'reason':error,'completed':completed,'atUtc':now()});transport.notebook_event(reg,OUT,'stopped',f'Completed {completed}; wall limit; no refill.');return {'outcome':'stopped','completed':completed,'reason':error}
        folder=OUT/'trials'/trial['trialID'];folder.mkdir();request=c.data(trial['case']['payload']);client=str(uuid.uuid4());write(folder/'CLAIM.json',{'atUtc':now(),'index':index,'payloadSHA256':trial['case']['payloadSHA256'],'clientRequestID':client,'attempt':1,'execution':'live'})
        status=0;raw=b'';parsed=None;provider=None;error=None;redacted=False;started=time.monotonic()
        try:
            status,raw,provider=transport._http(request,key,client,60)
            if key.encode() in raw:raw=raw.replace(key.encode(),b'[REDACTED_CREDENTIAL]');redacted=True
            with (folder/'response.raw').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            c.require(len(raw)<=transport.MAX_BODY,'oversize_response');c.require(not redacted,'credential_echo_redacted');c.require(status==200,'http_'+str(status))
            parsed=c.parse_reply(trial['case'],raw.decode('utf-8'));c.require(parsed['providerID'] not in ids,'duplicate_provider_id');ids.add(parsed['providerID'])
            usage=read(folder/'response.raw').get('usage',{})
            for k in tokens:tokens[k]+=int(usage.get(k,0))
        except Exception as exc:
            # Exception text and request headers are never printed: they may contain credentials.
            error='http_'+str(status) if status not in (0,200) else type(exc).__name__
        result={'execution':'live','trialID':trial['trialID'],'atUtc':now(),'httpStatus':status,'valid':error is None,'errorCode':error,'payloadSHA256':trial['case']['payloadSHA256'],'responseSHA256':c.sha(raw),'providerRequestID':provider,'clientElapsedSeconds':time.monotonic()-started,'secretRedacted':redacted,'parsed':parsed}
        write(folder/'result.json',result)
        if error:
            stop={'outcome':'stopped','reason':error,'completed':completed,'failedTrial':trial['trialID'],'reservedAttempts':index+1,'atUtc':now(),'usageSoFar':tokens};write(OUT/'STOPPED.json',stop);transport.notebook_event(reg,OUT,'stopped',f'Completed {completed}; reservations {index+1}; stop code {error}. No retry, refill or automatic restart.');print(json.dumps(stop),flush=True);return stop
        completed+=1
        if completed%12==0:print(json.dumps({'completed':completed,'total':480,'elapsedSeconds':round(time.monotonic()-begin,1),'usage':tokens}),flush=True)
        if completed%48==0:write(OUT/f'CHECKPOINT_{completed:03d}.json',{'completed':completed,'atUtc':now(),'usage':tokens})
    done={'outcome':'completed','execution':'live','completed':480,'reservedAttempts':480,'atUtc':now(),'uniqueProviderIDs':len(ids),'usage':tokens};write(OUT/'COMPLETE.json',done);transport.notebook_event(reg,OUT,'completed','Completed all480 real requests; analysis pending. No retries, free-model fallback, Unity runs or historical pooling.');return done
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','verify','run','preview']);p.add_argument('--confirm-live',action='store_true');a=p.parse_args()
    if a.command=='preview':
        cases,audit=build_cases(encoding());print(json.dumps(audit,indent=2))
    else:print(json.dumps(freeze() if a.command=='freeze' else verify() if a.command=='verify' else run(a.confirm_live),indent=2))
