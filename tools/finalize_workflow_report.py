from pathlib import Path
import json,hashlib,shutil,msvcrt,os
R=Path(__file__).resolve().parents[1];o=R/'report'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
synced=False
try:
    with (o/'Report.docx').open('r+b'):pass
    shutil.copyfile(o/'Report.formal.en.docx',o/'Report.docx');synced=True
except PermissionError:pass
readme=o/'README.md'
readme.write_text(readme.read_text(encoding='utf-8')+'\n## Model workflow added 19 November 2026\n\nReport.formal.en.docx now includes the English model decision workflow as Figure 1 before Method; the previous results plot is Figure 2. Nine pages were rendered and inspected. Existing research text and tables are preserved from local_archive/20261119_workflow/Report.formal.en.docx. The latest input had cover and abstract on the same page, and that existing layout is retained. Reproducible diagram builder: tools/add_report_workflow.py. Standalone image: assets/model_workflow.en.png. The Chinese translation and presentation were not edited in this step. No new experiments.\n',encoding='utf-8')
p=o/'PACKAGE_COMPLETE.json';a=json.loads(p.read_text(encoding='utf-8'))
a.update(date='2026-11-19',reportPages=9,primaryReport='Report.docx' if synced else 'Report.formal.en.docx',canonicalReportSynchronized=synced,modelWorkflowIncluded=True,figureCount=2,existingResearchTextPreserved=True,visualQACompleted=True)
a['files']=[{'path':x.relative_to(o).as_posix(),'sha256':sha(x)} for x in sorted(o.rglob('*')) if x.is_file() and '.build' not in x.parts and x!=p and not x.name.startswith('~$')]
p.write_text(json.dumps(a,indent=2)+'\n',encoding='utf-8')
p=R/'research/scenario_decisions_v2/WORKFLOW_STATUS.json';w=json.loads(p.read_text(encoding='utf-8'));w.update(date='2026-11-19',primaryReport='report/'+a['primaryReport'],canonicalReportSynchronized=synced,modelWorkflowIncluded=True);p.write_text(json.dumps(w,indent=2)+'\n',encoding='utf-8')
with (R/'experiment_records/.notebook.lock').open('a+b') as f:
    f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    try:
        p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8')
        entry='''## V-052 — English model decision workflow added to report (2026-11-19, Asia/Taipei)

Purpose: document the implemented individual-decision pipeline. Checked scenario_agent_contract.py and scenario_formal.py against the report. Figure 1 separates the 12-condition payoff/reference comparison and 16-condition physical-information task, then shows fresh-context LLM willingness choice, response validation, preservation, contrast analysis and assistant reason coding. Forecasts are fixed estimates from six development seeds; p_ref is calculated separately and not supplied as the LLM answer. The diagram does not represent global LLM control or a new Unity run loop.

Output: report/Report.formal.en.docx (nine pages), with standalone image report/assets/model_workflow.en.png. Existing paragraphs and table content were preserved; the former results figure was renumbered to Figure 2. All pages were rendered and visually inspected; the diagram was adjusted to keep its last line inside the frame. Native Word PDF export was used after the bundled renderer reported missing LibreOffice. Pre-edit input retained in local_archive/20261119_workflow. No new API calls, Unity runs or formal evidence changes. Chinese translation and presentation unchanged.

'''
        assert '## V-052 ' not in s
        t=p.with_suffix('.workflow.tmp');t.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8');os.replace(t,p)
    finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
print({'primary':a['primaryReport'],'pages':9,'synced':synced})
