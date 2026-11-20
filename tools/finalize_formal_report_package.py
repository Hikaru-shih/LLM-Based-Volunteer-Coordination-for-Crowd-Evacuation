import hashlib,json,shutil,os,msvcrt
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'report'; archive=ROOT/'local_archive/20261118_formal_report'
formal=out/'Report.formal.en.docx'; old=Document(archive/'Report.docx'); new=Document(formal)
def body(d):
    p=[p.text for p in d.paragraphs if p.text.strip()]
    return p[p.index('Abstract'):]
assert body(old)==body(new)
assert [[[c.text for c in r.cells] for r in t.rows] for t in old.tables]==[[[c.text for c in r.cells] for r in t.rows] for t in new.tables]
assert 'Advisor: Sai-Keung Wong' in [p.text for p in new.paragraphs]
assert not list(new.element.iter(qn('w:pBdr')))
assert new.styles['Normal'].font.size.pt==12
assert new.styles['Heading 1'].font.size.pt==14
assert len(new.sections)==2
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((out/'PACKAGE_COMPLETE.json').read_text(encoding='utf-8'))
for name in ('Report.zh-TW.docx','Presentation.en.pptx'):
    assert sha(out/name)==next(x['sha256'] for x in receipt['files'] if x['path']==name)
synced=False
try:
    with (out/'Report.docx').open('r+b'):pass
    shutil.copyfile(formal,out/'Report.docx');synced=True
except PermissionError:pass
shutil.copyfile(ROOT/'tools/format_formal_report.py',out/'source/format_formal_report.py')
primary='Report.docx' if synced else 'Report.formal.en.docx'
(out/'README.md').write_text(f'''# P030 report package

Updated 18 November 2026. The English report now has a formal cover naming Advisor: Sai-Keung Wong, as supplied by the user.

- [{primary}]({primary}): primary English report, eight pages including the cover. A4, Times New Roman, 14 pt section headings, 12 pt body, 2.54 cm margins. The cover is unnumbered; body numbering begins at 1. No paragraph divider rules. Both results tables remain together.
- [Report.formal.en.docx](Report.formal.en.docx): formal English edition.
- [Report.zh-TW.docx](Report.zh-TW.docx): unchanged eight-page Traditional Chinese translation of the English research content before the formal cover was added. It does not include the new advisor cover.
- [Presentation.en.pptx](Presentation.en.pptx): unchanged thirteen-slide English presentation.
- [Speaker_Notes.en.md](Speaker_Notes.en.md): English speaking script.
- [Oral_Defense.zh-TW.md](Oral_Defense.zh-TW.md): oral-defense preparation.

The scientific paragraphs, tables, results, references and limitations are unchanged. No new API requests or Unity runs were made. Independent human validation remains unavailable.

The advisor's name is user supplied. Institution, department, student name/ID and institution-specific submission rules have not been supplied, so this is a general formal research report rather than a verified institutional thesis template.

Editable research text is in source/Report.en.md. Cover metadata is in source/front-matter.json. Rebuild the formal edition using tools/format_formal_report.py with --input local_archive/20261118_formal_report/Report.docx, --metadata report/source/front-matter.json and --output report/Report.formal.en.docx from the project root. The archived input is the pre-formatting edition.

Visual QA: all eight pages were rendered through native Microsoft Word and inspected. The packaged renderer could not run because LibreOffice was unavailable. Internal QA files remain in .build/. Prior files are preserved in local_archive/20261118_formal_report. This folder is ignored by Git.
''',encoding='utf-8')
receipt.update(reportPages=8,primaryReport=primary,canonicalReportSynchronized=synced,advisorDisplayName='Sai-Keung Wong',advisorNameSource='User supplied',formalCover=True,bodyTextAndTablesUnchanged=True,priorFormattingPackage='local_archive/20261118_formal_report',renderBackend='Microsoft Word PDF export; pdf2image page rendering')
receipt['translations']['zh-TW']['researchContentUnchangedWithFormalEdition']=True
receipt['files']=[{'path':p.relative_to(out).as_posix(),'sha256':sha(p)} for p in sorted(out.rglob('*')) if p.is_file() and '.build' not in p.parts and p.name!='PACKAGE_COMPLETE.json' and not p.name.startswith('~$')]
(out/'PACKAGE_COMPLETE.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
wp=ROOT/'research/scenario_decisions_v2/WORKFLOW_STATUS.json'; w=json.loads(wp.read_text(encoding='utf-8'))
w.update(primaryReport='report/'+primary,canonicalReportSynchronized=synced,advisorDisplayName='Sai-Keung Wong',next='Review the formal English report. Institution-specific format and author metadata remain to be supplied before institutional submission. No new experiments launched.')
wp.write_text(json.dumps(w,indent=2)+'\n',encoding='utf-8')
entry='''## V-051 — Formal English report cover and layout (2026-11-18, Asia/Taipei)

Purpose: format the existing English report and add the user-supplied advisor name, Sai-Keung Wong. No academic rank, institution or author identity was inferred. The report has an unnumbered cover and seven numbered body pages, Times New Roman, 14 pt section headings and 12 pt body text, with no paragraph divider rules. Both results tables are kept together.

Verification: all eight pages were exported by native Microsoft Word and visually inspected after the bundled renderer failed because LibreOffice was unavailable. Scientific body paragraphs and all table cells exactly match the archived pre-formatting report. The Chinese translation and English presentation hashes are unchanged. No new API calls, Unity runs or formal-data changes. Files: report/Report.formal.en.docx, report/source/front-matter.json and report/PACKAGE_COMPLETE.json. Previous package: local_archive/20261118_formal_report.

'''
with (ROOT/'experiment_records/.notebook.lock').open('a+b') as lock:
    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    try:
        log=ROOT/'experiment_records/EXPERIMENT_LOG.md'; text=log.read_text(encoding='utf-8')
        assert '## V-051 ' not in text
        marker='<!-- AUTO-RECORDED RUNS -->';assert marker in text
        tmp=log.with_suffix('.formal.tmp');tmp.write_text(text.replace(marker,entry+marker,1),encoding='utf-8');os.replace(tmp,log)
    finally:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
print(json.dumps({'primary':primary,'canonicalSynchronized':synced,'pages':8,'scientificBodyUnchanged':True}))
