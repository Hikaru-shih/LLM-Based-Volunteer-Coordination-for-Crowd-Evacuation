"""Check delivered tables/charts against sealed cells, then record the local report package."""
import json,csv,hashlib,re,shutil,os,msvcrt,subprocess
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'report';ANA=ROOT/'experiment_records/data/analysis/scenario_formal_v1_20261116'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (OUT/'PACKAGE_COMPLETE.json').exists()
for row in read(ANA/'ARTIFACT_SHA256.json')['files']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
with (ANA/'CELL_SUMMARY.csv').open(encoding='utf-8-sig',newline='') as f:cells=list(csv.DictReader(f))
counts={(r['scenario'],r['information']):int(r['participate']) for r in cells}
wn={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(OUT/'Report.docx') as z:
    body=E.fromstring(z.read('word/document.xml'));styles=E.fromstring(z.read('word/styles.xml'))
    assert not body.xpath('//w:pBdr|//w:br[@w:type="page"]',namespaces=wn) and not styles.xpath('//w:pBdr',namespaces=wn)
    for style,size in [('Normal','24'),('Heading1','28')]:assert styles.xpath('//w:style[@w:styleId="'+style+'"]/w:rPr/w:sz/@w:val',namespaces=wn)==[size]
    tables=body.xpath('//w:tbl',namespaces=wn);assert len(tables)==2
    grid=[[''.join(c.xpath('.//w:t/text()',namespaces=wn)) for c in r.xpath('./w:tc',namespaces=wn)] for r in tables[0].xpath('./w:tr',namespaces=wn)]
    assert len(grid)==7
    for row in grid[1:]:
        av,beta,num,context,ref=row;case=f"A{round(float(av)*100)}_R{round(float(beta)*100)}"
        assert int(num)==counts[(case,'numeric')] and int(context)==counts[(case,'contextual_equivalent')]
    grid=[[''.join(c.xpath('.//w:t/text()',namespaces=wn)) for c in r.xpath('./w:tc',namespaces=wn)] for r in tables[1].xpath('./w:tr',namespaces=wn)]
    assert len(grid)==9
    for row in grid[1:]:assert int(row[1])==counts[(row[0],'geometry_only')] and int(row[2])==counts[(row[0],'calibrated_forecast')]
cn={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
with ZipFile(OUT/'Presentation.en.pptx') as z:
    slides=[n for n in z.namelist() if re.fullmatch('ppt/slides/slide[0-9]+.xml',n)];assert len(slides)==13
    chartfiles=sorted(n for n in z.namelist() if '/charts/' in n and n.endswith('.xml'));assert len(chartfiles)==2
    got=[]
    for f in chartfiles:
        e=E.fromstring(z.read(f));got.append([[float(v.text) for v in s.xpath('./c:val/c:numRef/c:numCache/c:pt/c:v|./c:val/c:numLit/c:pt/c:v',namespaces=cn)] for s in e.xpath('.//c:ser',namespaces=cn)])
    expected=[]
    for av,info in [('A30','numeric'),('A30','contextual_equivalent'),('A70','numeric'),('A70','contextual_equivalent')]:expected.append([counts[(av+'_R'+cost,info)]/30 for cost in ('10','50','90')])
    expected.append([.2369,.0875,.0259])
    assert len(got[0])==len(expected)
    for actual,wanted in zip(got[0],expected):assert len(actual)==len(wanted) and all(abs(a-b)<1e-8 for a,b in zip(actual,wanted))
    settings=[f'B{b}_M{m}' for b in (2,3,4,5) for m in (1,4)]
    expected=[[counts[(s,info)]/30 for s in settings] for info in ('geometry_only','calibrated_forecast')]
    for actual,wanted in zip(got[1],expected):assert len(actual)==8 and all(abs(a-b)<1e-8 for a,b in zip(actual,wanted))
ignored=subprocess.run(['git','check-ignore','report/Report.docx','report/Presentation.en.pptx'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.splitlines();assert len(ignored)==2
(OUT/'README.md').write_text('''# P030 report package

Prepared 2026-11-17 from the completed, sealed P030 study. No new experiments, API requests or Unity runs.

- [Report.docx](Report.docx): eight-page Chinese research report with Chinese/English abstracts, focused related work, model boundaries, methods, complete condition tables, discussion and references. Section headings14pt,body12pt; no paragraph divider rules or forced page breaks.
- [Presentation.en.pptx](Presentation.en.pptx): thirteen-slide English presentation with two editable charts and source notes.
- [Speaker_Notes.en.md](Speaker_Notes.en.md): English speaking script in slide order.
- [Oral_Defense.zh-TW.md](Oral_Defense.zh-TW.md): research introduction and likely oral-defense questions with evidence-bounded suggested answers.
- [source/Report.zh-TW.md](source/Report.zh-TW.md) and [source/references.json](source/references.json): editable report text and verified citation metadata.

Institution,department,student name/ID,advisor and institution-specific cover/format have not been supplied. This is a professor-review research package in general A4 format, not a claim of institutionally formatted thesis submission. The four external references provide focused positioning, not a systematic literature review. Human validation and independent human reason coding remain unavailable and are disclosed as limitations.

This entire folder is ignored by Git per the user's local-only writing preference. Older drafts remain in local_archive; sealed experiment evidence is not overwritten. Internal render QA stays in .build/ and is not a deliverable. PACKAGE_COMPLETE.json records hashes and consistency checks.
''',encoding='utf-8')
log=ROOT/'experiment_records/EXPERIMENT_LOG.md';title='## V-047 — Completed P030 local report and English presentation package (2026-11-17, Asia/Taipei)'
entry=title+'''\n\nPurpose: user requested completion of reporting and oral-defense preparation, with report and presentation together in a root report folder. Produced an8-page Chinese report,13-slide English editable presentation,English speaking script,Chinese oral-defense preparation,and source text/reference metadata. Added a focused related-work section using the original Lin–Wong2018 paper,Park et al.2023,Aher et al.ICML2023 and Turpin et al.2023; official author/proceedings metadata and primary abstracts checked. Do not label this a systematic review or first-in-field novelty claim. Separate local source/registration evidence from external literature. No invented institutional or author metadata.\n\nChecks: report's complete12 abstract and16 physical condition counts compared directly with the sealed cell table; both native presentation chart data arrays matched the same source. Main contrasts,descriptive intervals and human-validation limitations retained. All8 report pages and13 slides visually inspected; section headings14pt/body12pt,no paragraph divider rules or forced page breaks. Packaged LibreOffice renderer unavailable; dedicated invisible Word opened the local report read-only for internal PDF/PNG QA. Presentation edited/rendered in Artifact Session and exported to report/Presentation.en.pptx. Internal QA is not shipped as a requested PDF deliverable.\n\nAll2566 sealed formal artifact hashes unchanged. Zero new experiment API requests or Unity runs; no recoding or pooling. Later28-response assistant demonstrations remain assistant-only,not independent human validation. Root report/ added to gitignore consistent with the user's archive preference; older archived drafts left intact. No messages sent externally. Institution-specific cover/layout and personal metadata remain the only document-format inputs to supply before formal submission.\n\nFiles: report/{Report.docx,Presentation.en.pptx,Speaker_Notes.en.md,Oral_Defense.zh-TW.md,README.md}; source text and verified bibliography in report/source/. Receipt: report/PACKAGE_COMPLETE.json.\n\n'''
with (ROOT/'experiment_records/.notebook.lock').open('a+b') as gate:
    gate.seek(0);msvcrt.locking(gate.fileno(),msvcrt.LK_NBLCK,1)
    try:
        old=log.read_text(encoding='utf-8');marker='<!-- AUTO-RECORDED RUNS -->';assert old.count(marker)==1 and title not in old
        new=old.replace(marker,entry+marker,1);assert new.replace(entry,'',1)==old
        tmp=log.with_suffix('.report-package.tmp');tmp.write_text(new,encoding='utf-8');os.replace(tmp,log)
    finally:gate.seek(0);msvcrt.locking(gate.fileno(),msvcrt.LK_UNLCK,1)
workflow=ROOT/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';state=read(workflow)
state.update(currentMilestone='report_package_complete_institution_metadata_pending',writingDeliverables='report/README.md',currentReportPackage='report',newAPICallsThisStep=0,newUnityRunsThisStep=0,next='Review the completed report package; supply institutional format and author/advisor metadata before formal submission. No additional experiment is authorized or launched.')
workflow.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
readme=ROOT/'README.md';s=readme.read_text(encoding='utf-8');s+='\n## Current local reporting package\n\nThe completed professor-review report,English presentation,speaking script and defense notes are together in [report/](report/README.md),which is ignored by Git. Institutional format and personal metadata remain to be supplied before formal submission. No additional experiments were run.\n';readme.write_text(s,encoding='utf-8')
for name in ('prepare_report_package.py','build_report_docx.py','finalize_report_package.py'):shutil.copyfile(ROOT/'tools'/name,OUT/'source'/name)
items=[{'path':p.relative_to(OUT).as_posix(),'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file() and '.build' not in p.parts]
receipt={'date':'2026-11-17','package':'report','reportPages':8,'englishSlides':13,'nativeCharts':2,'conditionCountsChecked':28,'visualQACompleted':True,'formalHashesVerifiedUnchanged':2566,'newAPICalls':0,'newUnityRuns':0,'independentHumanValidation':False,'institutionMetadataProvided':False,'gitIgnored':True,'files':items}
(OUT/'PACKAGE_COMPLETE.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print({'complete':True,'reportPages':8,'englishSlides':13,'conditionCountsChecked':28,'formalHashesUnchanged':2566,'gitIgnored':True})
