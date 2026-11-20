from pathlib import Path
import json,hashlib,shutil,zipfile
from docx import Document
R=Path(__file__).resolve().parents[1];O=R/'report';B=O/'.build/author_name_20261120';A=R/'local_archive/20261120_before_author_name';U=O/'upload'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for lang,name in [('en','Report.docx'),('zh-TW','Report.zh-TW.docx')]:
    assert sha(O/name)==sha(B/name)
    d=Document(O/name);old=Document(A/name)
    assert d.core_properties.author=='Pin Kuang Shih'
    assert len(d.paragraphs)==len(old.paragraphs)+1
    assert [p.text for p in d.paragraphs if p.text not in ('Author: Pin Kuang Shih','作者：Pin Kuang Shih')]==[p.text for p in old.paragraphs]
    assert [t._tbl.xml for t in d.tables]==[t._tbl.xml for t in old.tables]
    p=O/'source'/f'Report.{lang}.md';s=p.read_text(encoding='utf-8');needle='Advisor: Sai-Keung Wong' if lang=='en' else '指導教授：Sai-Keung Wong';assert needle in s
    s=s.replace(needle,('Author: Pin Kuang Shih' if lang=='en' else '作者：Pin Kuang Shih')+'\n\n'+needle,1);p.write_text(s,encoding='utf-8')
archivezip=A/'Project_Submission_20261120.zip'
if not archivezip.exists():shutil.copy2(U/'Project_Submission_20261120.zip',archivezip)
p=U/'SUBMISSION_README.txt';s=p.read_text(encoding='utf-8').replace('Advisor: Sai-Keung Wong.','Author: Pin Kuang Shih. Advisor: Sai-Keung Wong.').replace('Check any institution-specific cover, author/student identity and submission requirements','Check any institution-specific cover, student ID and submission requirements');p.write_text(s,encoding='utf-8')
files=[(O/'Report.docx','Report.docx'),(O/'Presentation.en.pptx','Presentation.en.pptx'),(O/'Speaker_Notes.en.md','Speaker_Notes.en.md'),(O/'Report.zh-TW.docx','Chinese/Report.zh-TW.docx'),(U/'SUBMISSION_README.txt','README.txt')]
write(U/'SUBMISSION_MANIFEST.json',{'date':'2026-11-20','author':'Pin Kuang Shih','files':[{'path':rel,'sha256':sha(p),'bytes':p.stat().st_size} for p,rel in files]});files.append((U/'SUBMISSION_MANIFEST.json','MANIFEST.json'))
candidate=B/'Project_Submission_20261120.zip'
with zipfile.ZipFile(candidate,'w',zipfile.ZIP_DEFLATED) as z:
    for p,rel in files:z.write(p,rel)
with zipfile.ZipFile(candidate) as z:
    assert z.testzip() is None
    for p,rel in files:assert hashlib.sha256(z.read(rel)).hexdigest()==sha(p)
shutil.copy2(candidate,U/'Project_Submission_20261120.zip')
p=O/'README.md';s=p.read_text(encoding='utf-8').replace('Author/student identity, institution and institution-specific submission rules have not been invented. Those fields should be checked before school submission.','Author: Pin Kuang Shih (user supplied). Institution, student ID and institution-specific submission rules remain to be checked before school submission.');s+='\nThe author name now appears on both report covers and in document properties. Submission ZIP and its checksums were refreshed. Only cover pages changed in rendering; all body pages match the prior checked edition.\n';p.write_text(s,encoding='utf-8')
p=O/'PACKAGE_COMPLETE.json';x=json.loads(p.read_text(encoding='utf-8'));x.update(authorDisplayName='Pin Kuang Shih');x['authorUpdate']={'reportCovers':True,'documentProperties':True,'sourceCopies':True,'submissionZIPRefreshed':True,'bodyUnchanged':True,'pages':{'en':21,'zh':24}};x['files']=[{'path':f.relative_to(O).as_posix(),'sha256':sha(f)} for f in sorted(O.rglob('*')) if f.is_file() and '.build' not in f.parts and f.name!='PACKAGE_COMPLETE.json' and not f.name.startswith('~$')];write(p,x)
p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-068 ' not in s
entry='## V-068 — Author name on report covers (2026-11-20, Asia/Taipei)\n\nAdded the user-supplied author name Pin Kuang Shih to the English and Chinese covers and DOCX author properties. All body paragraphs, numerical tables and figures unchanged. Rendered21/24-page reports using background Word after missing LibreOffice. Only cover renders changed; all body pages hash-match the previously inspected edition. Checked both covers. Updated editable source copies, submission readme, manifest and document submission ZIP. Prior reports and ZIP retained in local_archive/20261120_before_author_name/. Source-only GitHub ZIP remains the earlier source snapshot, with no report files included. No experiment, API call, upload, commit or push.\n\n';p.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8')
write(B/'QA.json',{'status':'complete','author':'Pin Kuang Shih','onlyCoverPagesChanged':True,'bodyPagesHashMatched':True,'submissionZIPSHA256':sha(U/'Project_Submission_20261120.zip')})
print('Author name added to both reports and the submission ZIP refreshed.')
