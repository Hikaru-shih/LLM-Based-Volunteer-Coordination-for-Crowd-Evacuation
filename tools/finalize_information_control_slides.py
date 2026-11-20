from pathlib import Path
import json,hashlib,zipfile,shutil,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[1]; O=R/'report'; B=O/'.build/slides_20261120'
candidate=B/'output/Presentation.en.pptx'
qa=json.loads((B/'PRESENTATION_VALIDATION.json').read_text())
assert qa['packageIntegrity']['slide_count']==16 and qa['nativeChartValidation']['passed']
shutil.copy2(candidate,O/'Presentation.en.pptx')
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
notes=[]
with zipfile.ZipFile(candidate) as z:
    for i in range(1,17):
        x=ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{i}.xml'))
        parts=[]
        for shape in x.findall('.//p:sp',ns):
            ph=shape.find('.//p:ph',ns)
            if ph is not None and ph.get('type') in ('sldNum','hdr','ftr','dt'):continue
            parts.extend(''.join(p.itertext()) for p in shape.findall('.//a:t',ns))
        notes.append(' '.join(parts))
assert all(notes)
(O/'Speaker_Notes.en.md').write_text('# English presentation notes\n\nUpdated 20 November 2026. P030 and P031 remain separate analyses.\n\n'+'\n\n'.join(f'## Slide {i}\n\n{n}' for i,n in enumerate(notes,1))+'\n',encoding='utf-8')
p=O/'README.md';s=p.read_text(encoding='utf-8')
s=s.replace('The original main report and presentation remain the P030 edition','The original main report remains the P030 edition; the presentation now includes the separately analysed P031 follow-up')
s+='\n## Presentation update (20 November 2026)\n\nPresentation.en.pptx now contains 16 English slides, with three added follow-up slides on design, the three concurrent information groups and instruction option order. The conclusion distinguishes both batches and their limits. Speaker_Notes.en.md follows the same 16-slide order. Four native editable charts have embedded workbooks. All slides were visually reviewed in the artifact renderer and the exported package passed structural, geometry, font and chart-workbook checks. Native PowerPoint rendering was not tested. The previous deck and notes are retained in local_archive/20261120_presentation_before_followup/. No new API or Unity runs.\n'
p.write_text(s,encoding='utf-8')
p=R/'experiment_records/EXPERIMENT_LOG.md';s=p.read_text(encoding='utf-8');assert '## V-061 ' not in s
entry='## V-061 — English presentation integration (2026-11-20, Asia/Taipei)\n\nPurpose: integrate the completed P031 information-control follow-up into the existing P030 presentation at the author’s request. Added three slides, bringing the deck to 16 slides, and updated the cover, study labels, workflow and conclusion. The original 840 and follow-up 480 choices remain separate. The new slides report 141/160, 116/160 and 53/160 participation, forecast-minus-control -39.375 pp, and order-specific contrasts -60.00 and -18.75 pp. Notes disclose the single control topic, fixed forecast-row order/action names, single model profile and descriptive block-bootstrap intervals. All 16 slides visually inspected in the artifact renderer; exported PPTX passed package, geometry, font and four native chart/workbook checks. Native PowerPoint execution was not tested. Previous deck and notes backed up under local_archive/20261120_presentation_before_followup/. Updated deliverables: report/Presentation.en.pptx and report/Speaker_Notes.en.md. No API calls, new samples, Unity runs or changes to raw evidence.\n\n'
p.write_text(s.replace('<!-- AUTO-RECORDED RUNS -->',entry+'<!-- AUTO-RECORDED RUNS -->',1),encoding='utf-8')
p=O/'PACKAGE_COMPLETE.json';x=json.loads(p.read_text(encoding='utf-8'));x['presentationUpdate']={'date':'2026-11-20','slides':16,'nativeCharts':4,'studies':['P030','P031'],'pooled':False,'notesSynced':True,'visualQA':'artifact renderer, all slides','nativePowerPointVerified':False,'newAPICalls':0,'newUnityRuns':0}
x['files']=[{'path':f.relative_to(O).as_posix(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(O.rglob('*')) if f.is_file() and '.build' not in f.parts and f.name!='PACKAGE_COMPLETE.json' and not f.name.startswith('~$')]
p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'slides':16,'notes':len(notes),'nativeCharts':4,'saved':str(O/'Presentation.en.pptx')}))
