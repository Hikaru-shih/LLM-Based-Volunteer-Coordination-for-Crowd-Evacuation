"""Rebuild only the source ZIP after explicit private-file exclusions."""
from pathlib import Path
import subprocess,json,hashlib,zipfile,shutil,re
R=Path(__file__).resolve().parents[1];O=R/'report';U=O/'upload';B=O/'.build/source_exclusions_20261120';A=R/'local_archive/20261120_before_source_exclusions'
B.mkdir(parents=True,exist_ok=True);A.mkdir(parents=True,exist_ok=True)
def git(*args):return subprocess.check_output(['git',*args],cwd=R).decode('utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
excluded_prefixes=('.vscode/','research/s5/datasets/','Assets/data/','experiment_records/data/','report/','local_archive/','research/scenario_decisions_v2/poststudy_20261117/')
tracked=set(git('ls-files','-z').split('\0'))
assert 'openai-key.local.txt' not in tracked
assert not any(p.startswith('.vscode/') for p in tracked)
assert all((R/'.vscode'/n).exists() for n in ('extensions.json','launch.json','settings.json'))
checks=['openai-key.local.txt','.vscode/settings.json','research/s5/datasets/snapshots.raw.jsonl','experiment_records/.notebook.lock','report/Report.docx','Assets/data/example.csv']
ignored={p:subprocess.run(['git','check-ignore','--no-index','-q',p],cwd=R).returncode==0 for p in checks};assert all(ignored.values())
# Record the source-package correction before exporting the English notebook.
p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-070 ' not in s
entry='## V-070 — Explicit source upload exclusions and credential protection (2026-11-20, Asia/Taipei)\n\nAfter the author approved all identified exclusions, added Git ignore rules for .vscode/, research/s5/datasets/ and experiment_records/.notebook.lock. Removed the three previously tracked .vscode files from the Git index with --cached, retaining local copies. All existing source/data and earlier Git changes preserved. The ignored openai-key.local.txt remains local and was not read or exported. The tracked openai-key.example.txt contains a placeholder only. Rebuilt the source-only GitHub ZIP from current existing source candidates with explicit exclusions for runtime/raw data, historical datasets, editor settings, locks, Word documents, reports, archives and credentials. Previous ZIP retained in the ignored archive. Scanned exported text for credential/private-key patterns without emitting matched values. Verified ZIP entries and per-file SHA-256 values. The audit covers the current source export, not past Git history. No API calls, simulations, commit, push or publication.\n\n'
p.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8')
paths=git('ls-files','--cached','--others','--exclude-standard','-z').split('\0')
roots={'Assets','Packages','ProjectSettings','tools','research','experiment_records'}
rootfiles={'.gitignore','README.md','openai-key.example.txt','study_plan.template.json'}
files=[];scanned=0;hits=[]
text_ext={'.cs','.py','.mjs','.js','.json','.md','.txt','.yaml','.yml','.unity','.asset','.html','.xml','.csv','.meta','.jsonl','.pem','.key','.env'}
pattern=re.compile(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
for logical in sorted(set(paths)):
    if not logical:continue
    rel=Path(logical);p=R/rel
    if rel.parts[0] not in roots and logical not in rootfiles:continue
    if logical.startswith(excluded_prefixes):continue
    if rel.name=='openai-key.local.txt' or rel.name.endswith('.lock') or rel.suffix.lower() in {'.doc','.docx','.docm','.dotx','.dotm'}:continue
    if not p.is_file():continue
    assert p.resolve().is_relative_to(R.resolve())
    if p.suffix.lower() in text_ext:
        scanned+=1
        if pattern.search(p.read_text(encoding='utf-8',errors='ignore')):hits.append(rel.as_posix())
    files.append((p,rel.as_posix()))
assert not hits,{'possibleCredentialFiles':hits}
for name in ('GitHub_Source_20261120.zip','GITHUB_SOURCE_MANIFEST.json'):
    if not (A/name).exists():shutil.copy2(U/name,A/name)
manifest={'date':'2026-11-20','kind':'source-only-working-tree-export','rawDataIncluded':False,'historicalDatasetsIncluded':False,'editorSettingsIncluded':False,'lockFilesIncluded':False,'wordFilesIncluded':False,'reportsIncluded':False,'credentialsIncluded':False,'gitHistoryIncluded':False,'textFilesScanned':scanned,'ignoreChecks':ignored,'files':[{'path':rel,'sha256':sha(p),'bytes':p.stat().st_size} for p,rel in files]}
write(U/'GITHUB_SOURCE_MANIFEST.json',manifest);files.append((U/'GITHUB_SOURCE_MANIFEST.json','SOURCE_MANIFEST.json'))
candidate=B/'GitHub_Source_20261120.zip'
with zipfile.ZipFile(candidate,'w',zipfile.ZIP_DEFLATED) as z:
    for p,rel in files:z.write(p,rel)
with zipfile.ZipFile(candidate) as z:
    assert z.testzip() is None
    assert not any(n.startswith(excluded_prefixes) or n.endswith('.lock') or Path(n).suffix.lower() in {'.doc','.docx','.docm','.dotx','.dotm'} or Path(n).name=='openai-key.local.txt' for n in z.namelist())
    assert z.read('openai-key.example.txt').decode('utf-8-sig').strip()=='PASTE_YOUR_OPENAI_API_KEY_HERE'
    for p,rel in files:assert hashlib.sha256(z.read(rel)).hexdigest()==sha(p)
shutil.copy2(candidate,U/'GitHub_Source_20261120.zip')
write(B/'AUDIT.json',{'status':'complete','sourceFiles':len(files),'sourceTextFilesScanned':scanned,'credentialPatternFindings':hits,'ignoredLocalKeyExists':(R/'openai-key.local.txt').is_file(),'localKeyRead':False,'localKeyTracked':False,'ignoreChecks':ignored,'editorFilesKeptLocally':True,'sourceZIPSHA256':sha(U/'GitHub_Source_20261120.zip'),'sourceZIPBytes':(U/'GitHub_Source_20261120.zip').stat().st_size,'committed':False,'pushed':False,'historyScanned':False})
p=O/'README.md';s=p.read_text(encoding='utf-8').replace('The source-only GitHub ZIP remains its earlier source snapshot and excludes report documents.','The source-only GitHub ZIP has been rebuilt from the current source tree, excluding report documents, research/s5/datasets/, .vscode/, notebook locks and credentials.');p.write_text(s,encoding='utf-8')
p=O/'PACKAGE_COMPLETE.json';x=json.loads(p.read_text(encoding='utf-8'));x['sourceExclusionCorrection']={'completed':True,'sourceFiles':len(files),'textFilesScanned':scanned,'localKeyIgnoredAndNotRead':True,'editorFilesUntrackedAndKeptLocally':True,'historicalDatasetsExcluded':True,'lockFilesExcluded':True,'sourceZIPRebuilt':True};x['files']=[{'path':f.relative_to(O).as_posix(),'sha256':sha(f)} for f in sorted(O.rglob('*')) if f.is_file() and '.build' not in f.parts and f.name!='PACKAGE_COMPLETE.json' and not f.name.startswith('~$')];write(p,x)
print(json.dumps({'status':'complete','sourceFiles':len(files),'textFilesScanned':scanned,'localKeyIgnored':ignored['openai-key.local.txt'],'localKeyRead':False,'credentialPatternFindings':hits,'sourceZIP':str(U/'GitHub_Source_20261120.zip'),'sourceZIPBytes':(U/'GitHub_Source_20261120.zip').stat().st_size,'committed':False,'pushed':False}))
