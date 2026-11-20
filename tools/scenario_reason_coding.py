"""Provenance-bound, multi-label reason coding and coverage reports. No LLM calls."""
import argparse
from collections import Counter,defaultdict
import csv
import json
from pathlib import Path
import scenario_agent_contract as c
import scenario_agent_transport as t

CODEBOOK=c.DESIGN/'reason-codebook.v3.json'

def source(run):
    registration_path=run/'registration.snapshot.json'
    reg=t.verify_registration(registration_path)
    records=[];seen=set()
    for trial in reg['trials']:
        folder=run/'trials'/trial['trialID'];rawfile=folder/'response.raw';resultfile=folder/'result.json'
        result=c.read(resultfile) if resultfile.exists() else None
        raw=rawfile.read_bytes() if rawfile.exists() else None
        parsed=None;classification='not_attempted'
        if (folder/'CLAIM.json').exists():classification='claimed_no_result'
        if result is not None:
            c.require((folder/'CLAIM.json').exists(),'Result has no durable pre-dispatch claim')
            claim=c.read(folder/'CLAIM.json')
            c.require(claim['payloadSHA256']==trial['case']['payloadSHA256'] and claim['execution']==reg['execution'] and claim['attempt']==1,'Claim/payload/execution drift')
            c.require(result['trialID']==trial['trialID'] and result['execution']==reg['execution'],'Result trial/execution mismatch')
            c.require(result['payloadSHA256']==trial['case']['payloadSHA256'],'Changed result payload')
            if raw is not None:c.require(c.sha(raw)==result['responseSHA256'],'Raw response hash drift')
            c.require(not result['valid'] or raw is not None,'Valid response missing raw file')
            classification='technical_invalid'
            if raw is not None and result['httpStatus']==200 and not result['secretRedacted']:
                try:parsed=c.parse_reply(trial['case'],raw.decode('utf-8'))
                except (ValueError,UnicodeError):parsed=None
            if parsed is not None:
                c.require(parsed==result['parsed'],'Raw explanation/action differs from result')
                if parsed['providerID'] in seen or result.get('errorCode')=='duplicate_provider_id':classification='duplicate_response'
                elif parsed['diagnosticActionCorrect'] is False:
                    c.require(not result['valid'] and result['errorCode']=='diagnostic_wrong_action','Semantic-failure result drift')
                    classification='semantic_failure'
                else:
                    c.require(result['valid'],'Readable response has unexplained invalid result')
                    classification='readable'
                seen.add(parsed['providerID'])
        eligible=classification in ('readable','semantic_failure')
        records.append({'trialID':trial['trialID'],'phase':trial['case']['phase'],'scenario':trial['case']['scenario'],'information':trial['case']['information'],
            'recordClass':classification,'reasonEligible':eligible,'rawSHA256':c.sha(raw) if raw is not None else None,
            'rawAction':parsed['rawAction'] if eligible else None,'reasonText':parsed['explanation'] if eligible else None,
            'diagnosticActionCorrect':parsed['diagnosticActionCorrect'] if eligible else None,'execution':reg['execution']})
    return reg,records

def template(run,target):
    reg,records=source(run);book=c.read(CODEBOOK)
    for row in records:
        row.update(codingStatus='unreviewed' if row['reasonEligible'] else 'not_applicable',labels=[],evidenceSpans=[],
            actionReasonRelation=None,comparisonJudgment=None,unsupportedInformation=None,arithmeticJudgment=None,
            errorEvidence=[],reviewer={'name':'','type':''},note='',uncertaintyNote='')
    sheet={'schema':'scenario-reason-coding-v3','codebookVersion':book['version'],'codebookSHA256':c.sha(CODEBOOK.read_bytes()),
        'registrationSHA256':c.sha((run/'registration.snapshot.json').read_bytes()),'execution':reg['execution'],
        'independentHumanReview':False,'records':records}
    target.parent.mkdir(parents=True,exist_ok=True);c.write_new(target,sheet)
    return {'plannedRows':len(records),'eligibleReasons':sum(x['reasonEligible'] for x in records),'reviewed':0,'newAPICalls':0}

def span_valid(span,text):
    c.require(isinstance(span,dict) and set(span)=={'quote','start','end'},'Evidence must have exact quote/start/end fields')
    c.require(type(span['start']) is int and type(span['end']) is int and 0<=span['start']<span['end']<=len(text),'Invalid evidence offsets')
    c.require(isinstance(span['quote'],str) and text[span['start']:span['end']]==span['quote'],'Evidence is not an exact raw-explanation span')

def validate(run,sheet_path,require_complete=False):
    reg,base=source(run);sheet=c.read(sheet_path);book=c.read(CODEBOOK)
    c.require(sheet['schema']=='scenario-reason-coding-v3' and sheet['codebookVersion']==book['version'],'Coding version mismatch')
    c.require(sheet['codebookSHA256']==c.sha(CODEBOOK.read_bytes()),'Codebook drift; create a new version and recode affected records')
    c.require(sheet['registrationSHA256']==c.sha((run/'registration.snapshot.json').read_bytes()),'Unbound registration')
    c.require(sheet['execution']==reg['execution'] and sheet['independentHumanReview'] is False,'Execution or review-scope claim changed')
    records=sheet['records'];c.require(len(records)==len(base),'Missing planned rows, including missing/invalid trials')
    mapped={row['trialID']:row for row in records};c.require(len(mapped)==len(base),'Duplicate coding trial IDs')
    reviewed=0
    for original in base:
        c.require(original['trialID'] in mapped,'Missing trial ID')
        row=mapped[original['trialID']]
        c.require(all(row.get(k)==v for k,v in original.items()),'Bound raw text, action, scenario or validity changed')
        c.require(row['codingStatus'] in ('unreviewed','reviewed','not_applicable'),'Unknown coding status')
        if not original['reasonEligible']:
            c.require(row['codingStatus']=='not_applicable' and not row['labels'] and not row['evidenceSpans'],'Cannot turn missing/invalid/duplicate response into observed reason')
            continue
        c.require(row['codingStatus']!='not_applicable','Readable reason cannot disappear as not applicable')
        if row['codingStatus']=='unreviewed':
            c.require(not row['labels'] and not row['evidenceSpans'],'Unreviewed row must not masquerade as coded evidence')
            continue
        c.require(isinstance(row['labels'],list) and len(row['labels'])==len(set(row['labels'])) and set(row['labels'])<=set(book['labels']),'Unknown or duplicate reason labels')
        c.require(bool(row['labels']),'Use insufficient_reason when no substantive consideration is identifiable')
        c.require(isinstance(row['reviewer'],dict) and isinstance(row['reviewer'].get('name'),str) and row['reviewer']['name'].strip() and row['reviewer'].get('type') in book['reviewerTypes'],'Missing reviewer identity/type')
        c.require(isinstance(row['note'],str) and row['note'].strip(),'Missing coding note')
        for key,allowed in book['qualityFields'].items():c.require(row[key] in allowed,'Missing/invalid '+key)
        supported=set()
        for span in row['evidenceSpans']:
            c.require(isinstance(span,dict) and set(span)=={'label','quote','start','end'} and span['label'] in row['labels'],'Evidence label mismatch')
            span_valid({k:v for k,v in span.items() if k!='label'},original['reasonText']);supported.add(span['label'])
        c.require(supported==set(row['labels']),'Every assigned label requires raw evidence')
        c.require((row['actionReasonRelation']=='conflict')==('action_reason_conflict' in row['labels']),'Conflict flag and label disagree')
        c.require((row['unsupportedInformation']=='present')==('unsupported_assumption' in row['labels']),'Unsupported-information flag and label disagree')
        if 'forecast_use' in row['labels']:
            c.require(original['phase']=='physical_diagnostic' or original['phase']=='physical_choice' and original['information']=='calibrated_forecast','Cannot use supplied forecasts where none were supplied')
        if 'diagnostic' in original['phase']:c.require(row['comparisonJudgment']!='not_applicable','Diagnostic comparison must be assessed or marked unclear')
        if 'unclear' in (row['actionReasonRelation'],row['comparisonJudgment'],row['unsupportedInformation'],row['arithmeticJudgment']):
            c.require(isinstance(row['uncertaintyNote'],str) and row['uncertaintyNote'].strip(),'Unclear judgments need an uncertainty note')
        for span in row['errorEvidence']:span_valid(span,original['reasonText'])
        if 'incorrect' in (row['comparisonJudgment'],row['arithmeticJudgment']):c.require(bool(row['errorEvidence']),'Arithmetic/comparison errors require evidence, not a silent failing flag')
        reviewed+=1
    eligible=sum(x['reasonEligible'] for x in base);complete=eligible>0 and reviewed==eligible
    completed=run/'COMPLETE.json';collection_complete=False
    if completed.exists():
        receipt=c.read(completed)
        collection_complete=receipt['execution']==reg['execution'] and receipt['completed']==len(base) and all(x['recordClass']=='readable' for x in base)
    c.require(not require_complete or complete and collection_complete,'Reason coding or planned collection incomplete')
    return {'valid':True,'planned':len(base),'eligible':eligible,'reviewed':reviewed,'unreviewed':eligible-reviewed,
            'coverageComplete':complete,'collectionComplete':collection_complete,'execution':reg['execution'],'records':records}

def summarize(run,sheet_path,target,require_complete=False):
    checked=validate(run,sheet_path,require_complete);book=c.read(CODEBOOK)
    groups=defaultdict(list)
    for row in checked['records']:groups[(row['phase'],row['scenario'],row['information'])].append(row)
    results=[];examples=[]
    for key,group in sorted(groups.items()):
        eligible=[x for x in group if x['reasonEligible']];coded=[x for x in eligible if x['codingStatus']=='reviewed']
        counts=Counter(tag for x in coded for tag in x['labels'])
        result={'phase':key[0],'scenario':key[1],'information':key[2],'planned':len(group),'recordClasses':dict(Counter(x['recordClass'] for x in group)),
            'readableNonduplicate':len(eligible),'reviewed':len(coded),'unreviewed':len(eligible)-len(coded),
            'observedParticipate':sum(x['rawAction']=='participate' for x in eligible),
            'labelCounts':{tag:counts[tag] for tag in book['labels']},
            'labelRatesAmongReviewed':{tag:counts[tag]/len(coded) if coded else None for tag in book['labels']}}
        results.append(result)
        for tag in book['labels']:
            positive=sorted((x for x in coded if tag in x['labels']),key=lambda x:x['trialID'])
            negative=sorted((x for x in coded if tag not in x['labels']),key=lambda x:x['trialID'])
            if positive:examples.append({'group':list(key),'label':tag,'firstPositiveID':positive[0]['trialID'],'firstNegativeID':negative[0]['trialID'] if negative else None,'selectionRule':'Lexicographically first reviewed positive and first reviewed label-absent record. Absence is not proof of an opposite motive.'})
    report={'schema':'scenario-reason-summary-v3','execution':checked['execution'],'newAPICalls':0,'codebookSHA256':c.sha(CODEBOOK.read_bytes()),
        'codingSheetSHA256':c.sha(sheet_path.read_bytes()),'coverageComplete':checked['coverageComplete'],'collectionComplete':checked['collectionComplete'],'groups':results,'examples':examples,
        'interpretation':'Multi-label proportions among reviewed eligible reasons, not independent humans or causal/hidden reasoning. Partial coverage must not be reported as all responses.'}
    target.parent.mkdir(parents=True,exist_ok=True);c.write_new(target,report);return {k:report[k] for k in ('execution','coverageComplete','newAPICalls')}

def gate_review(run,sheet_path,target):
    checked=validate(run,sheet_path,True);reg,_=source(run)
    c.require(reg['phase'] in ('abstract_diagnostic','physical_diagnostic'),'Free choices have no unique expected-utility correctness grade')
    c.require(checked['eligible']==checked['planned'],'All diagnostic replies must be readable and nonduplicated')
    records=[]
    for row in checked['records']:
        c.require(row['recordClass']=='readable' and row['diagnosticActionCorrect'] is not False,'Failed diagnostic action cannot be qualified by coding')
        c.require(row['comparisonJudgment']=='correct' and row['actionReasonRelation']=='consistent' and row['unsupportedInformation']=='none','Unresolved/incorrect reason cannot pass gate')
        c.require(row['arithmeticJudgment'] in ('correct','not_applicable'),'Unresolved arithmetic cannot pass gate')
        c.require('insufficient_reason' not in row['labels'],'Empty reasoning cannot qualify gate')
        records.append({'trialID':row['trialID'],'rawSHA256':row['rawSHA256'],'rawAction':row['rawAction'],'reasonText':row['reasonText'],
            'comparisonCorrect':True,'explicitActionReasonConflict':False,'reviewer':row['reviewer']['name']+' ('+row['reviewer']['type']+')','note':row['note']})
    c.write_new(target,{'registrationSHA256':checked_registration_sha(run),'records':records,'codingSheetSHA256':c.sha(sheet_path.read_bytes()),
        'codebookSHA256':c.sha(CODEBOOK.read_bytes()),'execution':reg['execution'],'independentHumanReview':False})
    return {'rows':len(records),'execution':reg['execution'],'liveQualified':False,'note':'Transport must revalidate live raw evidence; synthetic files never qualify.'}

def checked_registration_sha(run):return c.sha((run/'registration.snapshot.json').read_bytes())

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('template');p.add_argument('run',type=Path);p.add_argument('target',type=Path)
    for command in ('validate','summarize','gate-review'):
        p=sub.add_parser(command);p.add_argument('run',type=Path);p.add_argument('sheet',type=Path)
        if command in ('summarize','gate-review'):p.add_argument('target',type=Path)
        if command!='gate-review':p.add_argument('--require-complete',action='store_true')
    args=parser.parse_args()
    if args.command=='template':result=template(args.run,args.target)
    elif args.command=='validate':result=validate(args.run,args.sheet,args.require_complete);result.pop('records')
    elif args.command=='summarize':result=summarize(args.run,args.sheet,args.target,args.require_complete)
    else:result=gate_review(args.run,args.sheet,args.target)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
