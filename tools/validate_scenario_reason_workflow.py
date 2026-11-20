"""Persist a coding workflow using existing synthetic stage3 records; no AI classification."""
import json
import scenario_agent_contract as c
import scenario_reason_coding as s

def main():
    run=c.ROOT/'experiment_records/data/validation/scenario_agent_stage3_20261116/synthetic-roundtrip'
    folder=c.ROOT/'experiment_records/data/validation/scenario_reason_stage4_20261116'
    c.require(not folder.exists(),'Preserve previous validation')
    folder.mkdir(parents=True)
    blank=folder/'coding.unreviewed.json';s.template(run,blank)
    s.summarize(run,blank,folder/'summary.unreviewed.json')
    sheet=c.read(blank)
    for row in sheet['records']:
        c.require(row['execution']=='synthetic_test','Only synthetic fixtures may be hand-coded by this validator')
        text=row['reasonText']
        # The fixture explicitly contains no substantive decision explanation.
        c.require(text=='Synthetic action-mapping fixture. No language model or human was consulted.','Unexpected validation fixture')
        row.update(codingStatus='reviewed',labels=['insufficient_reason'],evidenceSpans=[{'label':'insufficient_reason','quote':text,'start':0,'end':len(text)}],
            actionReasonRelation='unclear',comparisonJudgment='not_applicable',unsupportedInformation='none',arithmeticJudgment='not_applicable',
            reviewer={'name':'Codex synthetic-fixture reviewer','type':'assistant'},
            note='Synthetic placeholder sentence provides no consideration supporting either action. This is a worked coding example, not LLM evidence.',
            uncertaintyNote='No substantive stated consideration exists to assess its relation to the action.')
    coded=folder/'coding.synthetic-worked-example.json';c.write_new(coded,sheet)
    check=s.validate(run,coded,True);c.require(check['reviewed']==16,'Incomplete worked example')
    s.summarize(run,coded,folder/'summary.synthetic-worked-example.json',True)
    receipt={'passed':True,'execution':'synthetic_test','newAPICalls':0,'newUnityRuns':0,'codebookVersion':sheet['codebookVersion'],
        'workedExampleRows':16,'assignedLabel':'insufficient_reason','meaning':'Demonstrates evidence binding and complete coding, not model behavior, human agreement, or semantic-classifier accuracy.',
        'collectionComplete':check['collectionComplete'],'codingCoverageComplete':check['coverageComplete'],'independentHumanReview':False}
    c.write_new(folder/'VALIDATION.json',receipt);print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
