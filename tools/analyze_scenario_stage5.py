"""Audit P029 against its prospective matrix and summarize the bounded live pilot."""
import csv,json,collections
from pathlib import Path
import scenario_agent_contract as c
import scenario_agent_transport as t
import scenario_reason_coding as s

def main():
    regroot=c.ROOT/'experiment_records/study_preparations/scenario_pilot_v1_20261116'
    rawroot=c.ROOT/'experiment_records/data/scenario_pilot_v1_20261116'
    out=c.ROOT/'experiment_records/data/analysis/scenario_pilot_v1_20261116'
    c.require(not out.exists(),'Preserve prior pilot analysis')
    plan=c.read(regroot/'plan.json');receipt=c.read(regroot/'REGISTRATION.json')
    c.require(c.sha((regroot/'plan.json').read_bytes())==receipt['planSHA256'],'Prospective master changed')
    for name,digest in plan['sourceSHA256'].items():c.require(c.sha((c.ROOT/name).read_bytes())==digest,'Registered source/codebook drift')
    rows=[];coding=[];ids=set();usage=collections.Counter();phase_counts={}
    for phase in plan['phases']:
        folder=rawroot/phase['phase'];registered=c.read(folder/'registration.snapshot.json')
        c.require(registered['trials']==phase['trials'] and registered['execution']=='live','Trial order/payload differs from prospective master')
        complete=c.read(folder/'COMPLETE.json');c.require(complete['completed']==phase['count'] and complete['execution']=='live','Incomplete phase')
        checked=s.validate(folder,folder/'coding.json',True);coding+=checked['records']
        s.summarize(folder,folder/'coding.json',folder/'reason-summary.json',True) if not (folder/'reason-summary.json').exists() else None
        phase_counts[phase['phase']]=complete['completed']
        for trial in registered['trials']:
            file=folder/'trials'/trial['trialID']/'result.json';result=c.read(file);raw=(file.parent/'response.raw').read_bytes()
            c.require(result['valid'] and result['execution']=='live' and result['httpStatus']==200 and not result['secretRedacted'],'Invalid pilot trial')
            c.require(c.sha(raw)==result['responseSHA256'],'Response hash drift')
            parsed=c.parse_reply(trial['case'],raw.decode());c.require(parsed==result['parsed'],'Parsed action drift')
            c.require(parsed['providerID'] not in ids,'Provider ID reused across phases');ids.add(parsed['providerID'])
            envelope=c.strict_json(raw.decode());tokens=envelope.get('usage',{})
            for key in ('prompt_tokens','completion_tokens','total_tokens'):
                value=tokens.get(key);c.require(type(value) is int and value>=0,'Missing provider usage');usage[key]+=value
            rows.append(dict(trialID=trial['trialID'],phase=phase['phase'],scenario=trial['case']['scenario'],information=trial['case']['information'],action=parsed['rawAction'],willing=parsed['willing'],diagnosticCorrect=parsed['diagnosticActionCorrect'],tie=parsed['tie'],providerID=parsed['providerID'],responseSHA256=result['responseSHA256'],promptTokens=tokens['prompt_tokens'],completionTokens=tokens['completion_tokens'],purpose='P029 development scenario pilot, not formal/human data'))
    c.require(len(rows)==len(ids)==208 and phase_counts=={'abstract_diagnostic':36,'physical_diagnostic':32,'abstract_choice':60,'physical_choice':80},'Pilot incomplete')
    bundle=Path(plan['bundlePath']);a=rawroot/'abstract_diagnostic';p=rawroot/'physical_diagnostic'
    gates=[t.gate_evidence(a,a/'gate-review.json',bundle),t.gate_evidence(p,p/'gate-review.json',bundle)]
    abstract={x['cell']:x for x in c.read(c.DESIGN/'pilot-plan.draft.json')['cells']}
    groups=[];reason_groups=[]
    codes={x['trialID']:x for x in coding}
    for phase in ('abstract_choice','physical_choice'):
        keys=sorted({(x['scenario'],x['information']) for x in rows if x['phase']==phase})
        for scenario,info in keys:
            selected=[x for x in rows if x['phase']==phase and x['scenario']==scenario and x['information']==info];n=len(selected);willing=sum(x['willing'] for x in selected)
            c.require(n==5,'Unexpected free-choice denominator')
            groups.append(dict(phase=phase,scenario=scenario,information=info,n=n,participate=willing,decline=n-willing,rate=willing/n,referenceProbability=abstract[scenario]['referenceProbability'] if phase=='abstract_choice' else None))
            labels=collections.Counter(tag for x in selected for tag in codes[x['trialID']]['labels'])
            reason_groups.append(dict(phase=phase,scenario=scenario,information=info,n=n,labelCounts=dict(labels)))
    out.mkdir(parents=True)
    def csvsave(path,data):
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    csvsave(out/'TRIAL_CATALOG.csv',rows);csvsave(out/'choice-summary.csv',groups)
    reason_rows=[dict(trialID=x['trialID'],phase=x['phase'],scenario=x['scenario'],information=x['information'],rawAction=x['rawAction'],labels=';'.join(x['labels']),comparison=x['comparisonJudgment'],actionReasonRelation=x['actionReasonRelation'],unsupportedInformation=x['unsupportedInformation'],arithmetic=x['arithmeticJudgment'],reason=x['reasonText'],note=x['note']) for x in coding]
    csvsave(out/'reason-coding.csv',reason_rows)
    quality={'reviewed':len(coding),'explicitActionReasonConflicts':sum(x['actionReasonRelation']=='conflict' for x in coding),'unsupportedInformationPresent':sum(x['unsupportedInformation']=='present' for x in coding),'incorrectComparisons':sum(x['comparisonJudgment']=='incorrect' for x in coding),'unclearComparisons':sum(x['comparisonJudgment']=='unclear' for x in coding),'incorrectArithmetic':sum(x['arithmeticJudgment']=='incorrect' for x in coding),'insufficientReasons':sum('insufficient_reason' in x['labels'] for x in coding),'independentHumanReview':False}
    summary={'registration':'P-029','schema':'scenario-pilot-summary-v1','status':'complete_reviewed_development_pilot','date':'2026-11-16','trials':208,'actualHTTPAttempts':208,'retries':0,'invalid':0,'apiModel':c.MODEL,'phases':phase_counts,'gateReviews':gates,'usage':dict(usage),'quality':quality,'groups':groups,'reasonGroups':reason_groups,'scope':'Small pilot, five free-choice responses per condition, not formal power/precision/human validation. Fixed own forecasts are six earlier development seeds, not observed future group outcomes. Same-model requests are not independent human participants.'}
    c.write_new(out/'summary.json',summary)
    c.write_new(out/'SOURCE_MANIFEST.json',[{'path':str(f.relative_to(c.ROOT)).replace('\\','/'),'sha256':c.sha(f.read_bytes())} for folder in [rawroot,regroot] for f in sorted(folder.rglob('*')) if f.is_file()])
    c.write_new(out/'COMPLETE.json',{'status':'all208_collected_and_reviewed','registration':'P-029','summarySHA256':c.sha((out/'summary.json').read_bytes()),'sourceManifestSHA256':c.sha((out/'SOURCE_MANIFEST.json').read_bytes()),'newUnityRuns':0,'formalRuns':0,'reasonReviewCompleted':True})
    print(json.dumps({'trials':208,'groups':groups,'quality':quality,'usage':dict(usage)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
