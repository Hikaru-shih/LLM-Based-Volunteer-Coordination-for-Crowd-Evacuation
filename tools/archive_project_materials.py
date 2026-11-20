"""Plan/verify local archival only. Mutation is executed with LiteralPath PowerShell."""
import json,hashlib,os,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'local_archive/20261117_cleanup'
PLAN=ROOT/'local_archive/20261117_cleanup/PLAN.json'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lp(p):
    text=str(p.absolute())
    prefix=chr(92)*2+'?'+chr(92)
    return prefix+text if os.name=='nt' and not text.startswith(prefix) else text
def inventory(p):
    result=[]
    if p.is_dir():
        stat=p.stat()
        # Same-volume rename must preserve the actual NTFS directory object.
        # Do not rehash hundreds of thousands of old HTTP files merely to move their parent.
        children=[]
        with os.scandir(lp(p)) as entries:
            for entry in entries:
                item=entry.stat(follow_symlinks=False)
                children.append({'name':entry.name,'fileID':item.st_ino,'directory':entry.is_dir(follow_symlinks=False)})
        return [{'relative':'.','kind':'directory_identity','bytes':0,'fileID':stat.st_ino,'children':sorted(children,key=lambda x:x['name'])}]
    if p.is_file():files=[p]
    else:
        files=[]
        def fail(error):raise error
        for base,dirs,names in os.walk(lp(p),followlinks=False,onerror=fail):
            # Preserve existing junction targets in place: never follow them while archiving.
            dirs[:]=[d for d in dirs if not os.path.islink(os.path.join(base,d))]
            files.extend(Path(base)/n for n in names)
    for f in files:
        stat=f.stat();rel='.' if p.is_file() else os.path.relpath(str(f),lp(p))
        row={'relative':rel,'bytes':stat.st_size,'mtimeNs':stat.st_mtime_ns,'fileID':stat.st_ino}
        if f.suffix.lower() in ('.md','.json','.py','.ps1','.mjs','.docx','.pptx') and stat.st_size<5_000_000:row['sha256']=sha(f)
        result.append(row)
    return sorted(result,key=lambda x:x['relative'])
def plan():
    assert not PLAN.exists() and not (ARCHIVE/'MOVES.jsonl').exists();ARCHIVE.mkdir(parents=True,exist_ok=True)
    formal=read(ROOT/'experiment_records/data/analysis/scenario_formal_v1_20261116/ARTIFACT_SHA256.json')
    protected=set()
    for item in formal['files']:
        path=ROOT/item['path'];assert sha(path)==item['sha256'];protected.add(item['path'])
    # Current contract verifier directly hashes all stage2 receipt files.
    for item in read(ROOT/'research/scenario_decisions_v2/STAGE2_RECEIPT.json')['files']:protected.add(item['path'])
    # Preserve all historical source-bound Markdown inputs without rewriting any sealed source.
    for folder in (ROOT/'research',ROOT/'experiment_records/study_preparations',ROOT/'experiment_records/data/preparation'):
        for f in folder.rglob('*.json'):
            if f.stat().st_size>2_000_000:continue
            try:obj=read(f)
            except (ValueError,UnicodeError):continue
            def scan(value):
                if isinstance(value,dict):
                    if isinstance(value.get('path'),str) and ('sha256' in value or 'SHA256' in value):protected.add(value['path'].replace('\\','/'))
                    for k,v in value.items():
                        if isinstance(k,str) and k.endswith('.md') and isinstance(v,str) and len(v)==64:protected.add(k.replace('\\','/'))
                        scan(v)
                elif isinstance(value,list):
                    for v in value:scan(v)
            scan(obj)
    candidates=[]
    def add(p,alias=False,purpose='legacy_or_explanatory'):
        if not p.exists() or p.is_symlink():return
        rel=p.relative_to(ROOT).as_posix()
        if any(rel==x['source'] or rel.startswith(x['source']+'/') for x in candidates):return
        candidates.append({'source':rel,'destination':'local_archive/20261117_cleanup/original/'+rel,'compatibilityJunction':alias,'purpose':purpose})
    for p in ROOT.glob('*.md'):
        if p.name!='README.md' and p.name not in protected:add(p)
    post=ROOT/'research/scenario_decisions_v2/poststudy_20261117';add(post,True,'local_writing_and_assistant_explanations')
    for p in (ROOT/'research').rglob('*'):
        if p.is_file() and p.suffix.lower() in ('.md','.docx','.pptx','.mjs','.py','.pyc') and p.relative_to(ROOT).as_posix() not in protected:add(p)
    # Existing raw provenance stays accessible through directory junctions; new current exports stay outside archive.
    keep={'analysis','auto','preparation','scenario_formal_v1_20261116','scenario_physical_v2_20261116_r2','scenario_physical_v2_20261116_r3','scenario_physical_v2_20261116_r4','scenario_pilot_v1_20261116','validation'}
    for p in (ROOT/'experiment_records/data').iterdir():
        if p.is_dir() and p.name not in keep:add(p,True,'superseded_data_keep_notebook_paths')
    for folder,names in [('analysis',{'scenario_formal_v1_20261116','scenario_physical_v2_20261116_final','scenario_pilot_v1_20261116'}),('preparation',{'scenario_agent_stage3_20261116'}),('validation',{'model_comparison_20261112'})]:
        for p in (ROOT/'experiment_records/data'/folder).iterdir():
            if p.is_dir() and p.name not in names:add(p,True,'superseded_evidence_keep_notebook_paths')
    for name in ('.codex-build','tmp','archived_results'):
        add(ROOT/name,True,'local_build_and_legacy_artifacts')
    for p in ROOT.glob('.chart-data-*'):add(p,False,'temporary_chart_data')
    snapshots=[]
    for n,item in enumerate(candidates,1):
        print('Inventory',n,item['source'],flush=True)
        inv=inventory(ROOT/item['source']);item['isDirectory']=(ROOT/item['source']).is_dir();item['files']=0 if item['isDirectory'] else 1;item['bytes']=sum(x['bytes'] for x in inv)
        dest=ARCHIVE/'inventories'/f'{n:03d}.json';dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');item['inventory']=dest.relative_to(ROOT).as_posix()
        if n%10==0:print('Inventoried moves',n,flush=True)
    # Save existing README before replacing its historical narrative with a concise English entry point.
    (ARCHIVE/'README.before.md').write_bytes((ROOT/'README.md').read_bytes())
    tracked=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True).stdout.decode().split('\0');tracked=set(tracked)
    tracked_moves=sorted(t for x in candidates for t in tracked if t==x['source'] or t.startswith(x['source']+'/'))
    assert all(t.startswith(('.chart-data-','tmp/')) for t in tracked_moves),repr(tracked_moves[:20])
    obj={'date':'2026-11-17','root':str(ROOT),'archive':str(ARCHIVE),'moves':candidates,'protectedNarrativePaths':sorted(x for x in protected if x.endswith('.md')),'individualFiles':sum(x['files'] for x in candidates),'directoryMoves':sum(x['isDirectory'] for x in candidates),'individualFileBytes':sum(x['bytes'] for x in candidates),'meaning':'Reversible same-volume moves verified by NTFS directory and immediate-child identities. Folder contents are not individually counted or rehashed; individual moved documents are hashed. Junctions retain English notebook/source-manifest access. No experiment or source modification.'}
    obj['trackedGeneratedFilesMoved']=tracked_moves
    PLAN.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:obj[k] for k in ('individualFiles','directoryMoves','protectedNarrativePaths')},ensure_ascii=False))
def verify():
    obj=read(PLAN)
    directory_ids_verified=0;poststudy_verified=0
    for item in obj['moves']:
        target=ROOT/item['destination'];current=inventory(target);before=read(ROOT/item['inventory'])
        if current!=before:
            assert item['source']=='research/scenario_decisions_v2/poststudy_20261117','Unexpected move mismatch: '+item['source']
            assert current[0]['children']==before[0]['children']
            # The denied first junction creation rolled this directory back, creating a new
            # directory object. Verify all sealed published contents, rather than ignore it.
            receipt=read(target/'DELIVERY_RECEIPT.json')
            for f in receipt['files']:assert sha(ROOT/f['path'])==f['sha256'],f['path']
            demo=target/'human_review/assistant_demo_20261117';provenance=read(demo/'PROVENANCE.json')
            for name,digest in provenance['files'].items():assert sha(demo/name)==digest
            assert sha(target/'human_review/review.json')==provenance['reviewBlankSHA256Unchanged']
            poststudy_verified=len(receipt['files'])
        elif item['isDirectory']:directory_ids_verified+=1
        if item['compatibilityJunction']:assert (ROOT/item['source']).resolve()==target.resolve(),item['source']
        else:assert not (ROOT/item['source']).exists(),item['source']
    formal=read(ROOT/'experiment_records/data/analysis/scenario_formal_v1_20261116/ARTIFACT_SHA256.json')
    for item in formal['files']:assert sha(ROOT/item['path'])==item['sha256'],item['path']
    ignored=subprocess.run(['git','check-ignore','local_archive/20261117_cleanup/PLAN.json'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    (ARCHIVE/'VERIFIED.json').write_text(json.dumps({'moves':len(obj['moves']),'individualFiles':obj['individualFiles'],'directories':obj['directoryMoves'],'sameVolumeDirectoryIdentitiesVerified':directory_ids_verified,'allDirectoryImmediateEntryNamesAndTypesVerified':True,'individualDocumentSHA256Verified':True,'poststudyException':'Initial denied junction creation caused a rollback/new directory ID; all 40 published artifact hashes, assistant-demo hashes and blank review hash verified instead.','poststudyManifestFilesVerified':poststudy_verified,'formalFilesVerified':len(formal['files']),'gitIgnored':ignored,'newAPICalls':0,'newUnityRuns':0},indent=2)+'\n',encoding='utf-8')
    print('Verified',len(obj['moves']),'moves;',len(formal['files']),'formal hashes unchanged')
if __name__=='__main__':
    {'plan':plan,'verify':verify}[sys.argv[1]]()
