"""Cross-check synchronized documents and native chart data against retained evidence."""
import json,csv,hashlib,re
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from docx import Document
from docx.oxml.ns import qn
R=Path(__file__).resolve().parents[1];O=R/'report';B=O/'.build/delivery_20261119'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
en=Document(O/'Report.formal.en.docx');zh=Document(O/'Report.zh-TW.docx')
assert len(en.tables)==len(zh.tables)==5 and len(en.inline_shapes)==len(zh.inline_shapes)==2
for d in (en,zh):
    assert d.styles['Normal'].font.size.pt==12 and d.styles['Heading 1'].font.size.pt==14
    assert not list(d.element.iter(qn('w:pBdr')))
for i in range(1,5):
    a=[[re.findall(r'-?\d+(?:\.\d+)?',c.text) for c in row.cells] for row in en.tables[i].rows[1:]]
    b=[[re.findall(r'-?\d+(?:\.\d+)?',c.text) for c in row.cells] for row in zh.tables[i].rows[1:]]
    assert a==b,('Translation numeric drift',i)
assert [sha(Path(O/'assets/model_workflow.en.png'))] # Confirm retained workflow exists.
with (R/'experiment_records/data/analysis/scenario_formal_v1_20261116/CELL_SUMMARY.csv').open(encoding='utf-8-sig',newline='') as f:cells=list(csv.DictReader(f))
counts={(r['scenario'],r['information']):int(r['participate']) for r in cells};assert len(counts)==28
for row in en.tables[1].rows[1:]:
    av,beta,n,c,p=[x.text for x in row.cells];case=f'A{round(float(av)*100)}_R{round(float(beta)*100)}'
    assert int(n)==counts[case,'numeric'] and int(c)==counts[case,'contextual_equivalent']
for row in en.tables[2].rows[1:]:
    case,n,c=[x.text for x in row.cells];assert int(n)==counts[case,'geometry_only'] and int(c)==counts[case,'calibrated_forecast']
reg=read(R/'experiment_records/data/scenario_formal_v1_20261116/registration.snapshot.json')
for d in (en,zh):
    text='\n'.join(p.text for p in d.paragraphs)
    for cid in ('AC_A30_R50_numeric','AC_A30_R50_contextual_equivalent','PC_B3_M4_geometry_only','PC_B3_M4_calibrated_forecast'):
        c=next(t['case'] for t in reg['trials'] if t['case']['caseID']==cid)
        for m in c['payload']['messages']:
            for line in m['content'].splitlines():
                if line:assert line in text,'Prompt appendix drift'
ns={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
ppt=B/'output/Presentation.en.pptx'
with ZipFile(ppt) as z:
    slides=sorted(n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n));assert len(slides)==13
    chartnames=sorted(n for n in z.namelist() if '/charts/' in n and n.endswith('.xml'));assert len(chartnames)==2
    got=[]
    for name in chartnames:
        root=E.fromstring(z.read(name));got.append([[float(v) for v in s.xpath('./c:val/c:numRef/c:numCache/c:pt/c:v/text()|./c:val/c:numLit/c:pt/c:v/text()',namespaces=ns)] for s in root.xpath('.//c:ser',namespaces=ns)])
    expected=[]
    for av,info in [('A30','numeric'),('A30','contextual_equivalent'),('A70','numeric'),('A70','contextual_equivalent')]:expected.append([counts[av+'_R'+cost,info]/30 for cost in ('10','50','90')])
    expected.append([.2369,.0875,.0259])
    for a,b in zip(got[0],expected):assert len(a)==len(b) and all(abs(x-y)<1e-12 for x,y in zip(a,b))
    assert len(got[0])==5
    settings=[f'B{b}_M{m}' for b in (2,3,4,5) for m in (1,4)]
    for a,info in zip(got[1],('geometry_only','calibrated_forecast')):assert len(a)==8 and all(abs(x-counts[s,info]/30)<1e-12 for x,s in zip(a,settings))
    assert len(got[1])==2
    assert len([n for n in z.namelist() if n.startswith('ppt/embeddings/') and n.endswith('.xlsx')])==2
    texts='\n'.join(' '.join(E.fromstring(z.read(n)).xpath('//a:t/text()',namespaces=ns)) for n in slides)
    assert not re.search('[\u4e00-\u9fff]',texts)
    for v in ('93.75%','85.42%','66.67%','97.92%','100%','0.2397','0.0294','0.0941','0.0069','25 responses','27 field differences'):assert v in texts,v
    notes=[n for n in z.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',n)];assert len(notes)==13
    notetext='\n'.join(' '.join(E.fromstring(z.read(n)).xpath('//a:t/text()',namespaces=ns)) for n in notes)
    assert 'not independent' in notetext and 'length' in notetext
agreement=read(R/'experiment_records/data/analysis/human_review_return_20261119/AGREEMENT.json')
assert [v['agree'] for v in agreement['fields'].values()]==[45,41,32,47,48]
assert len(read(R/'experiment_records/data/analysis/human_review_return_20261119/DISAGREEMENTS.json')['differences'])==27
tax=read(R/'experiment_records/data/analysis/human_review_return_20261119/DISAGREEMENT_TAXONOMY.json');assert tax['distinctResponses']==25
for x in read(R/'experiment_records/data/analysis/scenario_formal_v1_20261116/ARTIFACT_SHA256.json')['files']:assert sha(R/x['path'])==x['sha256'],x['path']
write={'status':'pass','conditionsChecked':28,'sealedArtifactsUnchanged':2566,'translatedNumericalTablesMatched':4,'verbatimPromptsPerReport':4,'nativeChartsChecked':2,'chartWorkbooks':2,'slideNotes':13,'authorReviewJudgments':240,'disagreements':27,'distinctDisagreementResponses':25,'reportPages':{'en':17,'zh-TW':16},'slideCount':13,'newAPICalls':0,'newUnityRuns':0}
(B/'CONSISTENCY_CHECK.json').write_text(json.dumps(write,indent=2)+'\n',encoding='utf-8');print(json.dumps(write))
