"""Locked descriptive analysis of the independent information-control follow-up."""
from pathlib import Path
import collections,csv,json,sys,hashlib
import information_control_experiment as e
import scenario_agent_contract as c
R=e.R;A=R/'experiment_records/data/analysis/information_control_v1_20261120'
def write(p,x):c.write_new(p,x)
def csvfile(path,rows):
    with path.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def analyze():
    e.verify();assert (e.OUT/'COMPLETE.json').exists(),'Incomplete campaign: do not publish full-batch estimates'
    assert not A.exists(),'Preserve prior analysis';A.mkdir(parents=True)
    reg=e.read(e.OUT/'registration.snapshot.json');assert len(reg['trials'])==480
    assert e.sha(e.OUT/'registration.snapshot.json')==e.sha(e.PRE/'registration.json')
    rows=[];ids=set();models=collections.Counter();fingerprints=collections.Counter();tokens=collections.Counter()
    for t in reg['trials']:
        folder=e.OUT/'trials'/t['trialID'];r=e.read(folder/'result.json');raw=(folder/'response.raw').read_bytes();case=t['case']
        assert r['valid'] and r['execution']=='live' and r['httpStatus']==200 and c.sha(raw)==r['responseSHA256']
        p=c.parse_reply(case,raw.decode('utf-8'));assert p==r['parsed'] and p['providerID'] not in ids;ids.add(p['providerID'])
        env=json.loads(raw);models[env['model']]+=1;fingerprints[str(env.get('system_fingerprint'))]+=1;u=env.get('usage',{})
        for k in ('prompt_tokens','completion_tokens','total_tokens'):tokens[k]+=int(u.get(k,0))
        rows.append({'trialID':t['trialID'],'block':t['block'],'scenario':case['scenario'],'information':case['information'],'optionOrder':case['optionOrder'],'participate':int(p['willing']),'decision':p['rawAction'],'explanation':p['explanation'],'providerID':p['providerID'],'model':env['model'],'systemFingerprint':env.get('system_fingerprint'),'promptTokens':u.get('prompt_tokens'),'completionTokens':u.get('completion_tokens'),'responseSHA256':r['responseSHA256']})
    assert len(rows)==len(ids)==480
    cells=[]
    for scenario in sorted({r['scenario'] for r in rows}):
        for info in e.INFOS:
            for order in e.ORDERS:
                rr=[r for r in rows if (r['scenario'],r['information'],r['optionOrder'])==(scenario,info,order)];assert len(rr)==10
                cells.append({'scenario':scenario,'information':info,'optionOrder':order,'n':10,'participate':sum(r['participate'] for r in rr),'rate':sum(r['participate'] for r in rr)/10})
    csvfile(A/'TRIALS.csv',rows);csvfile(A/'CELLS.csv',cells)
    groups=[{'information':info,'n':160,'participate':sum(r['participate'] for r in rows if r['information']==info),'rate':sum(r['participate'] for r in rows if r['information']==info)/160} for info in e.INFOS]
    pooled=[]
    for s in sorted({r['scenario'] for r in rows}):
        z={'scenario':s}
        for info in e.INFOS:z[info]=sum(r['participate'] for r in rows if r['scenario']==s and r['information']==info)
        pooled.append(z)
    csvfile(A/'SCENARIO_COUNTS.csv',pooled)
    import numpy as np
    rng=np.random.default_rng(2026112002);draw=rng.integers(0,10,(5000,10));block=[]
    def mean(blockid,info,order=None,subgroup=None):
        rr=[r['participate'] for r in rows if r['block']==blockid and r['information']==info and (order is None or r['optionOrder']==order) and (subgroup is None or (r['scenario'].startswith('B5') if subgroup=='B5' else not r['scenario'].startswith('B5')))];return sum(rr)/len(rr)
    for b in range(1,11):
        g,l,f=(mean(b,x) for x in e.INFOS)
        z={'block':b,'forecast_minus_control':f-l,'forecast_minus_geometry':f-g,'control_minus_geometry':l-g}
        for info in e.INFOS:z['order_difference_'+info]=mean(b,info,'decline_first')-mean(b,info,'participate_first')
        z['order_interaction_forecast_control']=(mean(b,'calibrated_forecast','decline_first')-mean(b,'length_control','decline_first'))-(mean(b,'calibrated_forecast','participate_first')-mean(b,'length_control','participate_first'))
        for subgroup in ('B2-B4','B5'):z['forecast_minus_control_'+subgroup]=mean(b,'calibrated_forecast',subgroup=subgroup)-mean(b,'length_control',subgroup=subgroup)
        block.append(z)
    contrasts={}
    for k in block[0]:
        if k=='block':continue
        a=np.array([z[k] for z in block]);est=float(a.mean());boot=a[draw].mean(axis=1);lo,hi=np.quantile(boot,[.025,.975]);contrasts[k]={'estimate':est,'percentagePoints':est*100,'descriptive95PercentileInterval':[float(lo),float(hi)],'primary':k in ('forecast_minus_control','forecast_minus_geometry')}
    write(A/'BLOCK_CONTRASTS.json',block)
    actual=[]
    for r in pooled:
        rr=[x for x in rows if x['scenario']==r['scenario']];f=[x['promptTokens'] for x in rr if x['information']=='calibrated_forecast'];l=[x['promptTokens'] for x in rr if x['information']=='length_control']
        actual.append({'scenario':r['scenario'],'forecastPromptTokens':sorted(set(f),key=str),'controlPromptTokens':sorted(set(l),key=str)})
    result={'status':'complete_prospectively_locked_followup','campaignID':e.CAMPAIGN,'n':480,'groups':groups,'scenarioCounts':pooled,'contrasts':contrasts,'modelCounts':dict(models),'systemFingerprintCounts':dict(fingerprints),'usage':dict(tokens),'actualPromptTokenAudit':actual,'promptMatching':e.read(e.PRE/'PROMPT_MATCH_AUDIT.json'),'historicalP030Pooled':False,'newUnityRuns':0,'reasonCodingPerformed':False,'independentHumanValidation':False,'interpretation':'Contrasts isolate the forecast package relative to this one matched administrative control under a crossed presentation-order factor. They do not isolate one semantic mechanism, prove irrelevant information equivalence, elicit beliefs, identify hidden reasoning, or generalize to other models/temperatures. Intervals are pointwise descriptive across ten scheduling blocks.'}
    write(A/'RESULTS.json',result)
    lines=['# Information-control follow-up results','','Campaign '+e.CAMPAIGN+'. The design was locked after observing the historical P030 results but before any new response. These 480 new choices are analysed separately from the earlier 840.','','## Participation','', '| Information | Participate | Rate |','|---|---:|---:|']
    for g in groups:lines.append(f"| {g['information']} | {g['participate']}/160 | {g['rate']*100:.2f}% |")
    lines+=['','## Prespecified contrasts','','| Contrast | Percentage points | Descriptive 95% interval |','|---|---:|---|']
    for k,x in contrasts.items():lines.append(f"| {k} | {x['percentagePoints']:+.2f} | [{x['descriptive95PercentileInterval'][0]*100:.2f}, {x['descriptive95PercentileInterval'][1]*100:.2f}] |")
    lines+=['','## Scope and reproducibility','','All 480 responses passed technical format/model/ID checks; no response was excluded because of its action or reason. Ten blocks, 48 factor combinations per block, one attempt, zero retries. Both explicit action enumerations were reversed in the order factor. This tests order sensitivity, not all semantic compliance or social desirability.','','Control and forecast inputs were matched with the o200k_base proxy to within one user-message token, not an independently verified provider tokenizer. Numeric literal counts were matched; characters and lexical words were approximately matched. Returned actual token counts are retained in RESULTS.json. One administrative control topic cannot eliminate all semantic/attention differences. A null control-minus-geometry estimate is not an equivalence test.','','Intervals use 5000 bootstrap resamples of ten complete scheduling blocks, seed 2026112002. They are pointwise descriptive, not confirmatory p-values, proof of request independence, simultaneous coverage or population inference. The 30-trial historical cells are not pooled with these 10-per-order cells.','','The requested and returned model and system fingerprints are recorded; no free-model fallback, new Unity run or human-behavior validation. Full raw replies and source-bound prompts remain in the run folder. Reasons are retained verbatim; no new reason-quality coding is claimed.','','Usage: '+json.dumps(dict(tokens))+'. Billing remains provider-side.','']
    (A/'RESULTS.en.md').write_text('\n'.join(lines),encoding='utf-8')
    # Standard plotting library, isolated workspace dependency directory.
    sys.path.insert(0,str(R/'report/.build/api_plotting'));import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.3),layout='constrained');colors=['#426D86','#9A9A9A','#C9893A']
    axes[0].bar(['Geometry','Matched control','Forecast'],[g['rate']*100 for g in groups],color=colors)
    for i,g in enumerate(groups):axes[0].text(i,g['rate']*100+1.5,f"{g['participate']}/160",ha='center',fontsize=10)
    axes[0].set_ylim(0,110);axes[0].set_ylabel('Participation (%)');axes[0].set_title('New concurrent information conditions')
    names=['Forecast - control','Forecast - geometry','Control - geometry'];keys=['forecast_minus_control','forecast_minus_geometry','control_minus_geometry']
    for i,k in enumerate(keys):
        z=contrasts[k];lo,hi=[v*100 for v in z['descriptive95PercentileInterval']];axes[1].errorbar(z['percentagePoints'],i,xerr=[[z['percentagePoints']-lo],[hi-z['percentagePoints']]],fmt='o',color='#426D86',capsize=4)
    axes[1].set_yticks(range(3),names);axes[1].invert_yaxis();axes[1].axvline(0,color='gray',lw=1);axes[1].set_xlabel('Difference (percentage points)');axes[1].set_title('Pointwise descriptive block-bootstrap intervals')
    fig.suptitle('P031 follow-up | 480 API choices | no historical pooling',fontsize=12)
    fig.savefig(A/'RESULTS.png',dpi=200);fig.savefig(A/'RESULTS.svg');plt.close(fig)
    manifests=[p for p in A.iterdir() if p.is_file()];write(A/'ARTIFACTS.json',{'files':[{'path':p.name,'sha256':e.sha(p)} for p in manifests],'runRegistrationSHA256':e.sha(e.OUT/'registration.snapshot.json'),'designSHA256':e.sha(e.PRE/'design.json')})
    print(json.dumps({'n':480,'groups':groups,'primaryContrasts':{k:v for k,v in contrasts.items() if v['primary']},'usage':dict(tokens)}));return result
if __name__=='__main__':analyze()
