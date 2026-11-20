"""Validate actual human ratings and compare with frozen assistant labels; no inferred entries."""
import argparse,collections,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
FIELDS={'insufficient_reason':['yes','no','unclear'],'actionReasonRelation':['consistent','conflict','unclear'],'comparisonJudgment':['correct','incorrect','not_applicable','unclear'],'unsupportedInformation':['none','present','unclear'],'arithmeticJudgment':['correct','incorrect','not_applicable','unclear']}
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def metrics(pairs):
    n=len(pairs);cats=sorted({v for pair in pairs for v in pair});conf={a:{b:0 for b in cats} for a in cats}
    for human,ai in pairs:conf[human][ai]+=1
    same=sum(a==b for a,b in pairs);po=same/n if n else None
    hm=collections.Counter(a for a,b in pairs);am=collections.Counter(b for a,b in pairs)
    pe=sum(hm[c]*am[c] for c in cats)/(n*n) if n else None
    return {'n':n,'agree':same,'agreement':po,'kappa':(po-pe)/(1-pe) if n and pe<1 else None,'kappaUndefinedReason':'constant matching categories' if n and pe==1 else 'no observations' if not n else None,'confusionRowsHumanColumnsAI':conf,'humanMargins':dict(hm),'assistantMargins':dict(am)}
def score(path):
    x=read(path);public=read(R/'report/human_review/sample.public.json');key=read(R/'local_archive/20261119_review_key/baseline.json')
    assert x['schema']=='human-quality-review-48-v1'
    assert x.get('reviewer','').strip() and x.get('role') in ('author','classmate','other') and x.get('exposure') in ('yes','no'),'Reviewer metadata required'
    assert len(x['items'])==48 and len({r['id'] for r in x['items']})==48,'All 48 ratings required'
    lookup={r['id']:r for r in x['items']};base={r['id']:r for r in key['records']}
    for p in public['items']:
        row=lookup[p['id']];assert row['caseID']==p['caseID'],'Case binding changed'
        assert set(row['ratings'])==set(FIELDS),'Incomplete quality fields'
        for k,v in row['ratings'].items():assert v in FIELDS[k],f'Invalid {k}'
        assert row['quote'].strip() and row['quote'] in p['explanation'],'Evidence must be an exact original explanation quote'
        assert row['note'].strip(),'Human justification required'
    result={'status':'actual_human_file_scored_not_adjudicated','reviewer':x['reviewer'],'role':x['role'],'priorAIExposure':x['exposure'],'scope':'Five quality fields; stratified sample, not population coding validity. Human-AI agreement, not independent human-human reliability. NA and unclear kept as explicit nominal categories.','sourceSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'n':48,'fields':{}}
    result['translationAssistance']=x.get('translationAssistance',{'declared':False})
    for k in FIELDS:
        result['fields'][k]=metrics([(lookup[p['id']]['ratings'][k],base[p['id']]['assistant'][k]) for p in public['items']])
        result['fields'][k]['byStratum']={group:metrics([(lookup[p['id']]['ratings'][k],base[p['id']]['assistant'][k]) for p in public['items'] if ('payoff' if p['caseID'].startswith('AC_') else 'forecast' if 'calibrated_forecast' in p['caseID'] else 'geometry')==group]) for group in ('payoff','geometry','forecast')}
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('ratings',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=score(a.ratings)
    assert not a.output.exists(),'Preserve prior scoring; choose a new output path'
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Scored 48 actual supplied ratings. No adjudication or formal-label overwrite.')
