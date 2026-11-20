"""Extract JSON literals only from a returned HTML; never execute uploaded scripts."""
import re,json,hashlib,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[1];src=Path('C:/Users/Pin Guang/Downloads/Review_filled.html')
out=R/'experiment_records/data/analysis/human_review_return_20261119';out.mkdir(parents=True,exist_ok=True)
text=src.read_text(encoding='utf-8-sig');decoder=json.JSONDecoder();states=[]
for m in re.finditer(r'\bstate\s*=\s*(?=\{)',text):
    try:x,n=decoder.raw_decode(text,m.end())
    except ValueError:continue
    if isinstance(x,dict) and x.get('schema')=='human-quality-review-48-v1':states.append(x)
assert len(states)==1,'Need exactly one saved review-state JSON literal'
x=states[0];public=json.loads((R/'report/human_review/sample.public.json').read_text(encoding='utf-8'));pmap={r['id']:r for r in public['items']}
assert len(x['items'])==48 and len({r['id'] for r in x['items']})==48
errors=[]
for r in x['items']:
    p=pmap[r['id']];assert r['caseID']==p['caseID']
    assert set(r['ratings'])==set(public['fields'])
    for k,v in r['ratings'].items():assert v in public['fields'][k]
    if not r['quote'].strip() or r['quote'] not in p['explanation']:errors.append({'id':r['id'],'issue':'quote_not_exact_substring','quote':r['quote']})
    assert r['note'].strip()
raw=src.read_bytes();sha=hashlib.sha256(raw).hexdigest()
dest=out/'Review_filled.submitted.html'
if dest.exists():assert dest.read_bytes()==raw,'Preserve earlier submission'
else:shutil.copyfile(src,dest)
(out/'ratings.extracted.pending.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt={'status':'awaiting_reviewer_provenance_confirmation','sourceSHA256':sha,'savedStateCount':1,'items':48,'qualityFieldsComplete':240,'notesComplete':48,'invalidQuotes':errors,'blankReviewerMetadata':[k for k in ('reviewer','role','exposure') if not x.get(k)],'htmlScriptsExecuted':False,'humanCompletionConfirmed':False,'independentBlindReviewClaimed':False,'formalLabelsChanged':False}
(out/'INTAKE.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False))
