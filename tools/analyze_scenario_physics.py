"""Audit zero-API physical calibration and derive explicitly bounded time proxies."""
from pathlib import Path
import csv,json,hashlib,statistics,sys,collections
sys.path.insert(0,str(Path(__file__).parent))
from closed_loop_study import source_sha,ROOT

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def mean(xs):return statistics.mean(list(xs))
def rows(folder,suffix):
    fs=list(folder.glob('*'+suffix));assert len(fs)<=1,(folder,suffix)
    return list(csv.DictReader(fs[0].open(encoding='utf-8-sig',newline=''))) if fs else []
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def csvsave(path,data):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)

def analyze(include_intermediate=False,include_counterfactual=False):
    data=ROOT/'experiment_records/data/scenario_physical_v2_20261116_r2'
    reg=ROOT/'experiment_records/study_preparations/scenario_physical_v2_20261116_r2'
    out=ROOT/('experiment_records/data/analysis/scenario_physical_v2_20261116_final' if include_counterfactual else 'experiment_records/data/analysis/scenario_physical_v2_20261116_complete' if include_intermediate else 'experiment_records/data/analysis/scenario_physical_v2_20261116')
    assert not out.exists(),'Preserve completed analysis'
    plan=read(reg/'plan.json');binding=read(reg/'source-binding.json')
    assert read(data/'COMPLETE.json')['runs']==66
    assert (data/'registered-plan.json').read_bytes()==(reg/'plan.json').read_bytes()
    assert source_sha()==plan['baseSourceSHA']==binding['baseProductionSHA'],'Original production changed'
    batches=[(data,reg)];items=[(j,data,binding) for j in plan['jobs']]
    if include_intermediate:
        d3=ROOT/'experiment_records/data/scenario_physical_v2_20261116_r3';r3=ROOT/'experiment_records/study_preparations/scenario_physical_v2_20261116_r3'
        p3=read(r3/'plan.json');b3=read(r3/'source-binding.json')
        assert read(d3/'COMPLETE.json')['runs']==60 and (d3/'registered-plan.json').read_bytes()==(r3/'plan.json').read_bytes()
        assert p3['baseSourceSHA']==b3['baseProductionSHA']==plan['baseSourceSHA']
        batches.append((d3,r3));items += [(j,d3,b3) for j in p3['jobs']]
    if include_counterfactual:
        assert include_intermediate
        d4=ROOT/'experiment_records/data/scenario_physical_v2_20261116_r4';r4=ROOT/'experiment_records/study_preparations/scenario_physical_v2_20261116_r4'
        p4=read(r4/'plan.json');b4=read(r4/'source-binding.json')
        assert read(d4/'COMPLETE.json')['runs']==48 and (d4/'registered-plan.json').read_bytes()==(r4/'plan.json').read_bytes()
        assert p4['baseSourceSHA']==b4['baseProductionSHA']==plan['baseSourceSHA']
        batches.append((d4,r4));items += [(j,d4,b4) for j in p4['jobs']]
    rr=[];aa=[];lookup={}
    for j,data,binding in items:
        folder=data/j['id'];v=read(folder/'physical-result.json');assert all(v[k]==j[k] for k in ['id','seed','blocked','policy','manipulationSteps'])
        assert v['instrumentedSourceSHA']==binding['instrumentedProjectSHA'] and v['apiCalls']==0 and v['termination'] in ['completed','timeout']
        assert len(v['agents'])==10 and len({a['id'] for a in v['agents']})==10
        initial=read(folder/'initial-state.json');assert initial['seed']==j['seed'] and initial['agents']==10 and initial['blocked']==j['blocked']
        assert len(initial['obstacleCells'])==5 and len(initial['agentCells'])==10
        assert abs(v['initialTau']-(1-j['blocked']/5))<1e-6
        globalRows=rows(folder,'_global.csv');assert len(globalRows)==1
        total=globalRows[0];assert total['Termination']==v['termination'] and int(total['ApiRequests'])==0 and int(total['MockDecisions'])==0
        exits={int(e['AgentID']):int(e['EvacuationStep']) for e in rows(folder,'_agents.csv')}
        assert len(exits)==int(total['EvacuatedCount'])
        for a in v['agents']:
            assert a['evacuated']==(a['id'] in exits)
            assert a['cappedExitStep']==exits.get(a['id'],300)
        decisions=rows(folder,'_paper_decisions.csv');effort=rows(folder,'_agent_effort.csv');events=rows(folder,'_obstacle_events.csv')
        assert all(x['Source']=='calibration_'+j['policy'] for x in decisions),set(x.keys() for x in decisions[:1])
        for d in decisions:assert (d['Willing']=='True')==(j['policy']=='AllHelp' or j['policy']=='Focal0' and int(d['AgentID'])==0 or j['policy']=='OthersHelp' and int(d['AgentID'])!=0)
        counts=collections.Counter(int(x['AgentID']) for x in effort)
        assert len({(x['Step'],x['AgentID']) for x in effort})==len(effort)
        if j['policy']=='None':assert not effort and not events
        if j['policy']=='Focal0':assert set(counts)<={0}
        if j['policy']=='OthersHelp':assert 0 not in counts
        for a in v['agents']:
            assert 0<=a['approachMoves']<=a['approachTicks']<=300
            assert a['approachTicks']+counts[a['id']]<=a['cappedExitStep']<=300
            if not a['evacuated']:assert a['cappedExitStep']==300
            aa.append(dict(job=j['id'],seed=j['seed'],blocked=j['blocked'],policy=j['policy'],manipulationSteps=j['manipulationSteps'],agent=a['id'],cappedExit=a['cappedExitStep'],evacuated=a['evacuated'],approachTicks=a['approachTicks'],approachMoves=a['approachMoves'],approachDistance=a['approachDistance'],handlerTicks=counts[a['id']],burdenTicks=a['approachTicks']+counts[a['id']]))
        row=dict(job=j['id'],seed=j['seed'],blocked=j['blocked'],policy=j['policy'],manipulationSteps=j['manipulationSteps'],initialStateSHA=v['initialStateSHA'],initialTau=v['initialTau'],termination=v['termination'],evacuated=sum(a['evacuated'] for a in v['agents']),A_H=mean(a['cappedExitStep'] for a in v['agents']),focalExit=v['agents'][0]['cappedExitStep'],approachTicks=sum(a['approachTicks'] for a in v['agents']),handlerTicks=len(effort),activations=sum(e['Action']=='activate' for e in events),settled=sum(e['Action']=='settle' for e in events))
        rr.append(row);lookup[(j['seed'],j['blocked'],j['policy'],j['manipulationSteps'])]=row
    pairs=[]
    for row in rr:
        if row['policy'] in ['None','OthersHelp']:continue
        base=lookup[(row['seed'],row['blocked'],'None',1)];opened=lookup[(row['seed'],0,'None',1)]
        assert base['initialStateSHA']==row['initialStateSHA']
        own=[a for a in aa if a['job']==row['job']]
        for a in own:
            b=next(z for z in aa if z['job']==base['job'] and z['agent']==a['agent'])
            o=next(z for z in aa if z['job']==opened['job'] and z['agent']==a['agent'])
            a['deltaOwnExit']=a['cappedExit']-b['cappedExit']
            a['rawNoHelpLoss']=b['cappedExit']-o['cappedExit']
        selected=[a for a in own if a['agent']==0] if row['policy']=='Focal0' else own
        burden=mean(a['burdenTicks'] for a in selected)
        loss=mean(a['rawNoHelpLoss'] for a in selected)
        cv=burden/301;av=max(0,loss)/301
        pairs.append(dict(job=row['job'],seed=row['seed'],blocked=row['blocked'],policy=row['policy'],manipulationSteps=row['manipulationSteps'],groupBenefit=base['A_H']-row['A_H'],focalDelay=row['focalExit']-base['focalExit'],othersBenefit=mean(-a['deltaOwnExit'] for a in own if a['agent']!=0),burdenTicks=burden,rawNoHelpLoss=loss,timeProxyCV=cv,timeProxyAV=av,paperDomainEligible=0<cv<av<1,timeoutBase=base['termination']=='timeout',selectedAgents=sum(a['handlerTicks']>0 for a in selected),approachTicks=mean(a['approachTicks'] for a in selected),handlerTicks=mean(a['handlerTicks'] for a in selected)))
    # Consistent records for control agents as well.
    for a in aa:
        a.setdefault('deltaOwnExit',None);a.setdefault('rawNoHelpLoss',None)
    summaries=[]
    for blocked in ([2,3,4,5] if include_intermediate else [2,5]):
        for policy in ['Focal0','AllHelp']:
            for work in [1,4]:
                subset=[x for x in pairs if x['blocked']==blocked and x['policy']==policy and x['manipulationSteps']==work]
                assert len(subset)==6
                summary=dict(blocked=blocked,policy=policy,manipulationSteps=work,seeds=6,meanGroupBenefit=mean(x['groupBenefit'] for x in subset),meanFocalDelay=mean(x['focalDelay'] for x in subset),meanOthersBenefit=mean(x['othersBenefit'] for x in subset),meanBurden=mean(x['burdenTicks'] for x in subset),meanApproach=mean(x['approachTicks'] for x in subset),meanHandling=mean(x['handlerTicks'] for x in subset),meanRawNoHelpLoss=mean(x['rawNoHelpLoss'] for x in subset),negativeGroupBenefitSeeds=sum(x['groupBenefit']<0 for x in subset),focalDelayedSeeds=sum(x['focalDelay']>0 for x in subset),validPaperProxySeeds=sum(x['paperDomainEligible'] for x in subset))
                summary['timeProxyCV']=summary['meanBurden']/301
                summary['timeProxyAV']=max(0,summary['meanRawNoHelpLoss'])/301
                summary['paperDomainEligible']=0<summary['timeProxyCV']<summary['timeProxyAV']<1
                summaries.append(summary)
    out.mkdir(parents=True);csvsave(out/'runs.csv',rr);csvsave(out/'agent-costs.csv',aa);csvsave(out/'paired-effects.csv',pairs);csvsave(out/'scenario-summary.csv',summaries)
    counterfactual=[]
    if include_counterfactual:
        for seed in range(71001,71007):
            for b in [2,3,4,5]:
                for m in [1,4]:
                    for context,c,d in [('others_decline','Focal0','None'),('others_willing','AllHelp','OthersHelp')]:
                        yes=lookup[(seed,b,c,m)];no=lookup[(seed,b,d,1 if d=='None' else m)]
                        assert yes['initialStateSHA']==no['initialStateSHA']
                        ownY=[a for a in aa if a['job']==yes['job']];ownN=[a for a in aa if a['job']==no['job']]
                        delta=yes['focalExit']-no['focalExit'];benefit=mean(a['cappedExit'] for a in ownN if a['agent']!=0)-mean(a['cappedExit'] for a in ownY if a['agent']!=0)
                        counterfactual.append(dict(seed=seed,blocked=b,manipulationSteps=m,others=context,focalDelay=delta,othersBenefit=benefit,groupBenefit=no['A_H']-yes['A_H'],personalSacrificePublicBenefit=delta>0 and benefit>0))
        csvsave(out/'own-action-counterfactuals.csv',counterfactual)
    save(out/'results.json',dict(runs=len(items),agentRecords=len(aa),pairedInterventions=len(pairs),ownActionCounterfactuals=len(counterfactual),sacrificePublicBenefitCases=sum(x['personalSacrificePublicBenefit'] for x in counterfactual),apiCalls=0,completed=sum(x['termination']=='completed' for x in rr),validTimeouts=sum(x['termination']=='timeout' for x in rr),invalid=0,summaries=summaries,baseSourceSHA=plan['baseSourceSHA'],instrumentedSourceSHAs=sorted({b['instrumentedProjectSHA'] for _,_,b in items}),scope='Exploratory physical development calibration; effects conditional on controlled policies and six seeds; no LLM or human data; time proxy is not identified Eq20 utility.'))
    manifest=[dict(path=str(f.relative_to(ROOT)).replace('\\','/'),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for batch in batches for folder in batch for f in sorted(folder.rglob('*')) if f.is_file()]
    save(out/'source-manifest.json',manifest)
    print(json.dumps(read(out/'results.json'),indent=2))
if __name__=='__main__':analyze('--include-intermediate' in sys.argv,'--include-counterfactual' in sys.argv)
