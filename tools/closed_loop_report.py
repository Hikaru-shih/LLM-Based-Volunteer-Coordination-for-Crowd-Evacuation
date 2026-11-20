"""Offline tables/figures for validated group runs; no simulation or model requests."""
import collections
import csv
import statistics
from pathlib import Path

import closed_loop_study as s
from individual_analysis import require


def summaries(rows):
    groups=collections.defaultdict(list);mapping={}
    for row in rows:
        key=(row['cell'],row['seed'],row['policy']);require(key not in mapping,'Duplicate report run');mapping[key]=row
        groups[(row['cell'],row['policy'])].append(row)
    table=[]
    for (cell,policy),values in sorted(groups.items()):
        total=sum(x['decisions'] for x in values);work=[x['gini'] for x in values if not x['noWork']]
        table.append(dict(cell=cell,policy=policy,runs=len(values),mean_A_H=statistics.fmean(x['A_H'] for x in values),mean_evacuated_fraction=statistics.fmean(x['fraction'] for x in values),completed=sum(x['termination']=='completed' for x in values),timeouts=sum(x['termination']=='timeout' for x in values),mean_handler_steps=statistics.fmean(x['effort'] for x in values),no_work_runs=sum(x['noWork'] for x in values),mean_gini_among_work_runs=statistics.fmean(work) if work else None,decision_weighted_willingness=sum(x['willing'] for x in values)/total if total else None,decisions=total,http_attempts=sum(x['httpAttempts'] for x in values)))
    contrasts=[]
    for cell in sorted({r['cell'] for r in rows}):
        for comparator in ['OriginalGameTheory','NoVolunteers','RandomMatched']:
            a={seed:v for (c,seed,p),v in mapping.items() if c==cell and p=='LLM'}
            b={seed:v for (c,seed,p),v in mapping.items() if c==cell and p==comparator}
            if not a or not b:continue
            require(a.keys()==b.keys(),'Unpaired report seeds')
            values=[]
            for seed in sorted(a):
                require(a[seed]['initialStateSHA']==b[seed]['initialStateSHA'] and a[seed]['horizon']==b[seed]['horizon'],'Unpaired report states')
                values.append(a[seed]['A_H']-b[seed]['A_H'])
            contrasts.append(dict(cell=cell,contrast='LLM minus '+comparator,seed_blocks=len(values),difference=statistics.fmean(values),pointwise95=s.block_interval(values) if len(values)>=2 else None,exploratory=True))
    return table,contrasts


def write(analysis):
    analysis=Path(analysis);summary=s.read(analysis/'summary.json');require(not summary['geometryOnly'],'Geometry is not evacuation evidence')
    rows=s.read(analysis/'runs.json');table,contrasts=summaries(rows)
    s.save(analysis/'scenario-summary.json',table);s.save(analysis/'exploratory-contrasts.json',contrasts)
    with (analysis/'scenario-summary.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    lines=['# Group evacuation analysis','',f"Phase: {summary['phase']}. Valid runs: {len(rows)}. Technical invalids: {summary['invalid']}.",'','A_H includes every initial pedestrian; non-evacuees contribute the common horizon. Lower A_H means lower evacuation burden within H. Legal timeouts remain in all relevant summaries.','']
    if 'primary' in summary:
        p=summary['primary'];lines += [f"Designated descriptive primary: {p['estimate']:.6g} steps, pointwise 95% seed-block bootstrap interval {p['pointwise95']}; {p['seedBlocks']} base-seed blocks. Negative means lower LLM A_H in the registered eight-cell distribution.",'']
    else:lines += ['Preparation data only. These tables are functional/cost evidence, not final policy rankings.','']
    lines += ['| Cell | Policy | Runs | Mean A_H | Mean evacuated fraction | Completed | Timeouts |','|---|---|---:|---:|---:|---:|---:|']
    for t in table:lines.append(f"| {t['cell']} | {t['policy']} | {t['runs']} | {t['mean_A_H']:.3f} | {t['mean_evacuated_fraction']:.3f} | {t['completed']} | {t['timeouts']} |")
    lines += ['','All cell-wise contrasts are exploratory, pointwise and conditional on this seed/scenario/model design; no multiple-comparison or human-validity claim. Geometry changes layout and workload together; N also changes density. Willingness uses decision-weighted denominators, not independent-person sample sizes. Handler steps exclude approach travel. No-work runs are separate from work-conditional Gini. API latency is not physical evacuation time.','']
    (analysis/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    cells=sorted({r['cell'] for r in table});policies=sorted({r['policy'] for r in table});fig,ax=plt.subplots(figsize=(12,5))
    width=.8/len(policies)
    for i,policy in enumerate(policies):
        vals={r['cell']:r['mean_A_H'] for r in table if r['policy']==policy}
        ax.bar([k-.4+width*(i+.5) for k,c in enumerate(cells) if c in vals],[vals[c] for c in cells if c in vals],width,label=policy)
    ax.set_xticks(range(len(cells)),cells,rotation=40,ha='right');ax.set_ylabel('Mean capped evacuation steps A_H');ax.set_title(('Formal' if summary['formalSimulationExecuted'] else 'Preparation only')+' — descriptive scenario means');ax.legend(fontsize=8);fig.tight_layout()
    fig.savefig(analysis/'scenario-A_H.png',dpi=170);fig.savefig(analysis/'scenario-A_H.pdf');plt.close(fig)
    return dict(scenarios=len(cells),tableRows=len(table),exploratoryContrasts=len(contrasts),remoteRequests=0)


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('analysis',type=Path)
    print(json.dumps(write(parser.parse_args().analysis),indent=2))
