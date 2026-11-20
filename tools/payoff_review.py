"""Keep protocol validity and manually reviewed explanation claims separate. No API."""
import argparse
import csv
import json
from pathlib import Path
from individual_analysis import audit, read, require, write_csv, write_json


def review(folder,output,annotations=None,synthetic=False):
    folder=Path(folder);output=Path(output);require(not output.exists(),'Choose a new review directory')
    data=audit(folder,synthetic);labels={}
    if annotations:
        with Path(annotations).open(encoding='utf-8-sig',newline='') as stream:
            for a in csv.DictReader(stream):
                index=int(a['index']);require(index not in labels and a['judgment'] in ('consistent','inconsistent','not_assessable','unreviewed') and (a['judgment']=='unreviewed' or a['reviewer'].strip() and a['note'].strip()),'Invalid/duplicate manual review');labels[index]=a
    rows=[]
    for trace in data['trace']:
        t=read(folder/'trials'/f"{trace['index']:06d}.json")
        if not t['valid']:continue
        c=json.loads(t['observation']);a=labels.pop(t['index'],None)
        if a:require(a.get('raw_sha256')==trace['raw_sha256'],'Review annotation belongs to a different/modified raw trial')
        rows.append(dict(index=t['index'],scenario=t['scenario'],players=c['nearbyAgentCount'],tau=c['exitNonBlockage'],
                         help_payoff=1-c['volunteerCost'],decline_if_others_help_payoff=1 if c['nearbyAgentCount']>1 else None,
                         decline_if_nobody_helps_payoff=1-c['failureCost'],protocol_valid=True,willing=t['willing'],explanation=t['explanation'],
                         judgment=a['judgment'] if a else 'unreviewed',reviewer=a['reviewer'] if a else '',note=a['note'] if a else '',
                         raw_file=trace['raw_file'],raw_sha256=trace['raw_sha256']))
    require(not labels,'Annotation refers to missing/non-valid choice')
    output.mkdir(parents=True);write_csv(output/'explanation_review.csv',rows,fields=list(rows[0]) if rows else ['index','judgment'])
    write_json(output/'summary.json',dict(schema='payoff-explanation-review-v1',validChoices=len(rows),reviewed=sum(r['judgment']!='unreviewed' for r in rows),
        inconsistent=sum(r['judgment']=='inconsistent' for r in rows),unreviewed=sum(r['judgment']=='unreviewed' for r in rows),
        actionRatesChanged=False,automaticSemanticJudge=False,note='Manual statement review is exploratory, not internal causal evidence. Unreviewed is not correct. No choice is excluded or forced.'))
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--annotations',type=Path);p.add_argument('--allow-synthetic',action='store_true');a=p.parse_args();print('Reviewed rows:',len(review(a.folder,a.output,a.annotations,a.allow_synthetic)))
