"""Preserve prior deliverables and categorise disagreements without adjudication."""
from pathlib import Path
from collections import Counter
import json,shutil
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
R=Path(__file__).resolve().parents[1];O=R/'report';AR=R/'local_archive/20261119_final_delivery';AR.mkdir(parents=True,exist_ok=True)
for name in ('Report.docx','Report.formal.en.docx','Report.zh-TW.docx','Presentation.en.pptx','Speaker_Notes.en.md','Oral_Defense.zh-TW.md','README.md','PACKAGE_COMPLETE.json'):
    p=O/name
    if p.exists() and not (AR/name).exists():shutil.copyfile(p,AR/name)
diff=json.loads((R/'experiment_records/data/analysis/human_review_return_20261119/DISAGREEMENTS.json').read_text(encoding='utf-8'))['differences']
counts=Counter(x['field'] for x in diff);assert list(sorted(counts.values()))==[1,3,7,16]
categories={'comparisonJudgment':('Scope of comparison','All 16: author correct versus assistant not_applicable. The submitted notes count correctly stated conditional payoff contrasts as comparisons. This does not establish an expected-utility optimum without beliefs.'),'actionReasonRelation':('Support versus absence of contradiction','Six author consistent / assistant unclear, one reverse. Submitted notes often distinguish weak support from an explicit opposite-action claim; the assistant used unclear when a supporting link was missing.'),'insufficient_reason':('Threshold for a substantive reason','Two author yes / assistant no; one author unclear / assistant no. H25, H31 and H40 differ in how weak layout/work-interval statements count as supporting considerations.'),'unsupportedInformation':('Cautious wording versus unsupported inference','One author unclear / assistant none, H25. The ambiguity concerns treating a short M interval as evidence about total handling burden.')}
groups=[]
lines=['# Classification of author-AI coding differences','','This is an assistant-produced post hoc description of differences, not a new human adjudication or corrected codebook. The author had prior AI-label access. All original ratings remain unchanged.','',f'{len(diff)} field differences across {len({x["id"] for x in diff})} distinct responses. One response can differ on multiple fields. These counts are not 27 model errors.','','| Quality field | Differences | Description |','|---|---:|---|']
for field,(title,description) in categories.items():
    ids=[x['id'] for x in diff if x['field']==field];groups.append({'field':field,'count':len(ids),'ids':ids,'category':title,'interpretation':description,'adjudicated':False});lines.append(f'| {field} | {len(ids)} | {description} |')
lines+=['','## Retention decision','','No consensus labels are substituted. No formal response is removed. The 840 original actions and assistant-coded dataset remain the basis of the existing analyses. Future recoding would require a new codebook version and separate records; it has not been performed.','']
A=R/'experiment_records/data/analysis/human_review_return_20261119'
(A/'DISAGREEMENT_TAXONOMY.en.md').write_text('\n'.join(lines),encoding='utf-8')
(A/'DISAGREEMENT_TAXONOMY.json').write_text(json.dumps({'status':'assistant_posthoc_taxonomy_not_adjudication','fieldDifferences':27,'distinctResponses':25,'groups':groups},indent=2)+'\n',encoding='utf-8')
d=Document(AR/'Report.formal.en.docx');p=next(p for p in d.paragraphs if p.text.startswith('Unsupported-information agreement'))
p.insert_paragraph_before('A post hoc grouping of the 27 field differences spans 25 distinct responses: 16 concern what counts as a comparison, seven concern supportive reasoning versus mere absence of contradiction, three concern the threshold for a substantive reason, and one concerns an uncertain inference from work interval to burden. This grouping is an assistant interpretation of the submitted notes, not a human adjudication. All original judgments are retained.')
for p in d.paragraphs:
    if p.text=='18 November 2026':p.text='19 November 2026'
d.save(O/'Report.formal.en.docx')
def markdown(doc):
    lines=[]
    for el in doc.element.body:
        if el.tag==qn('w:p'):
            p=Paragraph(el,doc)
            if p.text:lines += [('## ' if p.style.name.startswith('Heading') else '# ' if p.style.name=='Title' else '')+p.text,'']
        elif el.tag==qn('w:tbl'):
            rr=[[c.text.replace('|','/') for c in row.cells] for row in Table(el,doc).rows];lines+=['| '+' | '.join(rr[0])+' |','| '+' | '.join(['---']*len(rr[0]))+' |']+['| '+' | '.join(row)+' |' for row in rr[1:]]+['']
    return '\n'.join(lines)
(O/'source/Report.en.md').write_text(markdown(d),encoding='utf-8')
print('Archived prior deliverables; classified 27 differences across 25 responses without recoding.')
