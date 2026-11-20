"""Apply explicit, hash-bound assistant/human judgments, never infer labels from keywords."""
import argparse
from pathlib import Path
import scenario_agent_contract as c
import scenario_reason_coding as s

def apply(run,judgments_path,target):
    reg,records=s.source(run)
    packet=[{k:x[k] for k in ('trialID','rawSHA256','rawAction','reasonText')} for x in records]
    judgments=c.read(judgments_path)
    c.require(judgments['reviewPacketSHA256']==c.sha(c.data(packet)),'Reviewed text packet changed')
    c.require(set(judgments['judgments'])=={x['trialID'] for x in records if x['reasonEligible']},'Explicit judgment required for every readable reason')
    s.template(run,target);sheet=c.read(target)
    for row in sheet['records']:
        if not row['reasonEligible']:continue
        decision=judgments['judgments'][row['trialID']]
        spans=[]
        for label,quotes in decision['evidence'].items():
            c.require(label in decision['labels'] and quotes,'Missing evidence quotes')
            for quote in quotes:
                start=row['reasonText'].find(quote);c.require(start>=0,'Judgment quote missing from raw reason')
                spans.append({'label':label,'quote':quote,'start':start,'end':start+len(quote)})
        row.update(codingStatus='reviewed',labels=decision['labels'],evidenceSpans=spans,
            actionReasonRelation=decision['actionReasonRelation'],comparisonJudgment=decision['comparisonJudgment'],
            unsupportedInformation=decision['unsupportedInformation'],arithmeticJudgment=decision['arithmeticJudgment'],
            errorEvidence=decision.get('errorEvidence',[]),reviewer=judgments['reviewer'],note=decision['note'],uncertaintyNote=decision.get('uncertaintyNote',''))
    # Preserve the blank template as a separate artifact; never overwrite an existing coded sheet.
    blank=target.with_name(target.stem+'.blank'+target.suffix)
    c.require(not blank.exists(),'Blank review snapshot already exists');target.rename(blank)
    c.write_new(target,sheet)
    result=s.validate(run,target)
    return {k:result[k] for k in ('valid','planned','eligible','reviewed','coverageComplete','collectionComplete')}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);parser.add_argument('judgments',type=Path);parser.add_argument('target',type=Path);a=parser.parse_args()
    print(__import__('json').dumps(apply(a.run,a.judgments,a.target),indent=2))
