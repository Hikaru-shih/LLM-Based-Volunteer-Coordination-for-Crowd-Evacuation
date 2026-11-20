"""Prepare local, explicit upload packages. Never commits, pushes or publishes."""
from pathlib import Path
import json,hashlib,subprocess,zipfile,shutil,re,collections
from docx import Document
R=Path(__file__).resolve().parents[1];O=R/'report';OUT=O/'upload';B=O/'.build/submission_20261120';A=R/'local_archive/20261120_upload_cleanup';A.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def git(*args):return subprocess.check_output(['git',*args],cwd=R).decode('utf-8')
def package(path,files):
    assert not path.exists(),'Preserve previous upload package'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for p,relative in files:z.write(p,relative)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for p,relative in files:assert hashlib.sha256(z.read(relative)).hexdigest()==sha(p)
for name in ['Defense_QA.en.md','Oral_Defense.zh-TW.md','Review_Differences.en.md']:
    src=(O/name).resolve();dst=(A/name).resolve();assert src.is_relative_to(R) and dst.is_relative_to(R)
    if src.exists():assert not dst.exists();shutil.move(str(src),str(dst))
for name in ['Report.docx','Report.zh-TW.docx']:
    d=Document(O/name);assert len(d.tables)==8 and len(d.inline_shapes)==2
    assert any(p.text.startswith('5.4 Information control' if name=='Report.docx' else '5.4 資訊控制') for p in d.paragraphs)
    assert not any('weaker cost response' in p.text or 'flatter cost response' in p.text for p in d.paragraphs)
    assert any(p.text.startswith(('Appendix A','附錄A')) for p in d.paragraphs)
with zipfile.ZipFile(O/'Presentation.en.pptx') as z:
    assert len([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)])==16
    assert b'Section 5.4' in z.read('ppt/notesSlides/notesSlide16.xml')
notes=(O/'Speaker_Notes.en.md').read_text(encoding='utf-8')
assert len(re.findall(r'^## Slide \d+$',notes,re.M))==16
for item in read(R/'experiment_records/data/analysis/information_control_v1_20261120/SEALED_ARTIFACTS.json')['files']:assert sha(R/item['path'])==item['sha256']
ignored=['openai-key.local.txt','report/Report.docx','local_archive/','experiment_records/data/','Library/','Assets/data/2026-11-09_145821_228_889d142d_run013_Random_agent_trace.jsonl']
ignore_checks={p:subprocess.run(['git','check-ignore','-q',p],cwd=R).returncode==0 for p in ignored};assert all(ignore_checks.values()),ignore_checks
tracked=git('ls-files','-z').split('\0');assert 'openai-key.local.txt' not in tracked
# Limit the source export to existing source candidates. Do not read the ignored credential.
paths=git('ls-files','--cached','--others','--exclude-standard','-z').split('\0')
roots={'Assets','Packages','ProjectSettings','tools','research','experiment_records'}
rootfiles={'.gitignore','README.md','openai-key.example.txt','study_plan.template.json'}
source=[];suspicious=[];scanned=0
text_ext={'.cs','.py','.mjs','.js','.json','.md','.txt','.yaml','.yml','.unity','.asset','.html','.xml','.csv','.meta'}
for logical in sorted(set(paths)):
    if not logical:continue
    rel=Path(logical);p=R/rel
    if rel.parts[0] not in roots and logical not in rootfiles:continue
    if logical.startswith(('Assets/data/','experiment_records/data/','research/scenario_decisions_v2/poststudy_20261117/')):continue
    if not p.is_file():continue
    assert p.resolve().is_relative_to(R.resolve())
    assert p.name!='openai-key.local.txt'
    source.append((p,rel.as_posix()))
    if p.suffix.lower() in text_ext:
        text=p.read_text(encoding='utf-8',errors='ignore');scanned+=1
        if re.search(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}',text) or re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',text):suspicious.append(rel.as_posix())
assert not suspicious,{'possibleCredentialFiles':suspicious} # Never print a matched value.
docreadme=OUT/'SUBMISSION_README.txt'
docreadme.write_text('Research submission package\n20 November 2026\n\nReport.docx is the primary English report (21 pages).\nPresentation.en.pptx is the 16-slide English presentation.\nSpeaker_Notes.en.md is the English speaking script.\nChinese/Report.zh-TW.docx is an optional Traditional Chinese reading translation (24 pages).\n\nThe original 840 choices and later 480 choices are separately analysed.\nSection5.4 reports the information-control experiment. AppendixA gives seeds, matching checks and prompt examples. JSON indentation is for readability, with token counts based on original serialized inputs.\n\nAdvisor: Sai-Keung Wong. Check any institution-specific cover, author/student identity and submission requirements before final school submission. No student/institution details were guessed.\nThis package excludes raw API replies, credentials, review forms, previous drafts and private build outputs.\n',encoding='utf-8')
docfiles=[(O/'Report.docx','Report.docx'),(O/'Presentation.en.pptx','Presentation.en.pptx'),(O/'Speaker_Notes.en.md','Speaker_Notes.en.md'),(O/'Report.zh-TW.docx','Chinese/Report.zh-TW.docx'),(docreadme,'README.txt')]
write(OUT/'SUBMISSION_MANIFEST.json',{'date':'2026-11-20','files':[{'path':rel,'sha256':sha(p),'bytes':p.stat().st_size} for p,rel in docfiles]})
docfiles.append((OUT/'SUBMISSION_MANIFEST.json','MANIFEST.json'))
# Record the preparation itself in English before exporting the notebook.
log=R/'experiment_records/EXPERIMENT_LOG.md';s=log.read_text(encoding='utf-8');assert '## V-067 ' not in s
entry='## V-067 — Local submission and source upload preparation (2026-11-20, Asia/Taipei)\n\nPrepared separate document and source-only upload packages at the author’s request. Document allowlist: English main report, English presentation and notes, optional Chinese translation, readme and SHA-256 manifest. Source allowlist: existing version-controlled/untracked source candidates in Assets (excluding runtime data), Packages, ProjectSettings, tools, research and experiment_records (excluding raw data), plus root README, .gitignore, key placeholder and study-plan template. Reports, key, raw responses, runtime exports, local archives, editor settings and build outputs excluded. Verified ignore rules and absence of a tracked local key. Scanned source candidate text for OpenAI-style credentials and private-key headers without reading ignored credentials or emitting values. This checks the exported working tree, not Git history or a public-data release. Original sealed evidence hashes unchanged. Archived obsolete defense/review helper documents locally. Updated root README and record index for the480-choice control study, corrected a report-navigation note in the16-slide deck, and validated the PowerPoint package. All original study data and earlier Git changes retained. No experiments, network model calls, commit, push or publication. Public raw-data deposition remains an author/supervisor decision. Packages remain ignored under report/upload/.\n\n'
log.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8')
manifest={'date':'2026-11-20','kind':'source-only-working-tree-export','rawDataIncluded':False,'gitHistoryIncluded':False,'reportsIncluded':False,'credentialsIncluded':False,'textFilesScanned':scanned,'files':[{'path':rel,'sha256':sha(p),'bytes':p.stat().st_size} for p,rel in source]}
write(OUT/'GITHUB_SOURCE_MANIFEST.json',manifest)
source.append((OUT/'GITHUB_SOURCE_MANIFEST.json','SOURCE_MANIFEST.json'))
package(OUT/'Project_Submission_20261120.zip',docfiles)
package(OUT/'GitHub_Source_20261120.zip',source)
status=collections.Counter(line[:2] for line in git('status','--porcelain').splitlines())
write(B/'UPLOAD_AUDIT.json',{'status':'complete','ignoreChecks':ignore_checks,'sourceFiles':len(source),'sourceTextFilesScanned':scanned,'credentialPatternFindings':suspicious,'trackedLocalKey':False,'sourceZIPBytes':(OUT/'GitHub_Source_20261120.zip').stat().st_size,'submissionZIPBytes':(OUT/'Project_Submission_20261120.zip').stat().st_size,'gitStatusCounts':dict(status),'gitHistoryScanned':False,'sealedEvidenceUnchanged':True,'uploaded':False,'committed':False,'pushed':False})
(O/'README.md').write_text('''# Final local reporting package

Updated20November2026. Start with Report.docx, the integrated21-page English main report. Its24-page Traditional Chinese translation is Report.zh-TW.docx. Presentation.en.pptx contains16 English slides and four editable charts. Speaker_Notes.en.md follows the same slide order.

## Upload packages

- upload/Project_Submission_20261120.zip: English report, English deck, notes, optional Chinese translation, readme and checksums. Suitable for sending to the supervisor after checking institution-specific submission metadata.
- upload/GitHub_Source_20261120.zip: source-only working-tree export, English experiment notebook, prospective designs and a per-file manifest. Excludes reports, raw data, credentials, archives, runtime exports, editor settings and build outputs. It does not include Git history.

No upload, commit or push has been performed. report/ remains Git ignored. The raw dataset has not been publicly deposited. Public deposition remains for author/supervisor review.

## Research and verification

The original840 and new480 responses remain separately analysed. Section5.4 contains information-control results, followed by exploratory utility5.5 and author review5.6. AppendixA supplies seeds, matching checks, actual prompt examples and response schema. Formatted JSON changes display whitespace only. Cost conclusions describe a smaller observed decline than the reference without identifying underlying cost sensitivity.

Reports retain14pt headings,12pt body and separate covers. Final report pages were rendered with background Word after unavailable LibreOffice. Changed pages were inspected and unchanged renders matched prior reviewed pages. Current deck geometry, charts, workbooks, fonts and package checks passed. Native PowerPoint rendering of this deck edition was not tested.

Eight numerical tables and both figures are unchanged. Original and new sealed evidence remain hash-matched. Detailed English study history is in experiment_records/EXPERIMENT_LOG.md. Raw evidence remains under experiment_records/data/. Complete local writing sources and build QA remain under source/ and .build/. Earlier defense/review helper documents are archived in local_archive/20261120_upload_cleanup/.

Advisor Sai-Keung Wong is user supplied. Author/student identity, institution and institution-specific submission rules have not been invented. Those fields should be checked before school submission.
''',encoding='utf-8')
p=O/'PACKAGE_COMPLETE.json';x=read(p);x['uploadPreparation']={'date':'2026-11-20','submissionZIP':'upload/Project_Submission_20261120.zip','sourceZIP':'upload/GitHub_Source_20261120.zip','sourceFiles':len(source),'sourceTextFilesScanned':scanned,'sealedEvidenceUnchanged':True,'uploaded':False,'committed':False,'pushed':False,'noNewExperiments':True};x['files']=[{'path':p.relative_to(O).as_posix(),'sha256':sha(p)} for p in sorted(O.rglob('*')) if p.is_file() and '.build' not in p.parts and p.name!='PACKAGE_COMPLETE.json' and not p.name.startswith('~$')];write(O/'PACKAGE_COMPLETE.json',x)
print(json.dumps({'submissionZIP':str(OUT/'Project_Submission_20261120.zip'),'sourceZIP':str(OUT/'GitHub_Source_20261120.zip'),'sourceFiles':len(source),'sourceTextScanned':scanned,'uploaded':False,'gitStatusCounts':dict(status)}))
if __name__=='__main__':pass
