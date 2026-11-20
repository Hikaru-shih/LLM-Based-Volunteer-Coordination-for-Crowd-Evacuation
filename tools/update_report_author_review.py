"""Integrate disclosed, non-blind author review without changing original coding."""
from pathlib import Path
import json,shutil
from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
R=Path(__file__).resolve().parents[1];O=R/'report';AR=R/'local_archive/20261119_author_review_report';AR.mkdir(parents=True,exist_ok=True)
for p in (O/'Report.formal.en.docx',O/'Report.docx',O/'source/Report.en.md',O/'PACKAGE_COMPLETE.json',O/'README.md'):
    dest=AR/p.name
    if p.exists() and not dest.exists():shutil.copyfile(p,dest)
d=Document(AR/'Report.formal.en.docx')
for p in d.paragraphs:
    if 'Reason coding is AI-assisted; human review is pending.' in p.text:p.text=p.text.replace('Reason coding is AI-assisted; human review is pending.','Reason coding is AI-assisted; a disclosed, non-blind author review of 48 responses found field-dependent agreement.')
    if 'using the a fixed' in p.text:p.text=p.text.replace('using the a fixed','using a fixed')
    if p.text.startswith('A separate 48-response human quality-review packet'):
        p.text='After the study, the project author completed five quality judgments for 48 sampled responses: 16 payoff, 16 geometry and 16 forecast responses. Selection did not use AI quality labels. The author had access to the assistant-filled example and Chinese reading translations before submission. This is non-blind author review, not independent validation. All 240 judgments, 48 notes and exact English evidence quotes were checked for completeness. The original submitted HTML is preserved; blank identity/exposure metadata were completed separately from the author\'s conversation confirmation, without changing the submitted ratings. Nominal Cohen\'s kappa, raw agreement, category margins and confusion tables were calculated by field and task, keeping not-applicable and unclear as categories. The balanced sample does not estimate coding validity across all 840 responses.'
    if p.text.startswith('There are no human evacuation observations'):
        p.text='There are no human evacuation observations or new group evacuation outcomes in this batch. The 48-response author review supplies a human quality check, but prior access to AI labels, author involvement and translation assistance limit its independence. It covers five quality fields, not all reason themes or model behavior. Agreement cannot establish ground-truth coding accuracy, and small stratum samples limit precision. Earlier qualification checks address specific comprehension tasks rather than every free-choice explanation.'
target=next(p for p in d.paragraphs if p.text=='6 Discussion')
p=target.insert_paragraph_before('5.2 Non-blind author review of explanation quality');p.style='Heading 2'
target.insert_paragraph_before('Table 5 reports descriptive agreement between the author\'s submitted judgments and the frozen assistant labels. The author had already been given the assistant example, so these statistics describe an exposed author review rather than independent inter-rater validation. There were 27 differing judgments across the 240 field entries; original labels and model decisions were not changed.')
results=json.loads((R/'experiment_records/data/analysis/human_review_return_20261119/AGREEMENT.json').read_text(encoding='utf-8'))
names={'insufficient_reason':'Reason insufficient','actionReasonRelation':'Action-reason relation','comparisonJudgment':'Comparison judgment','unsupportedInformation':'Unsupported information','arithmeticJudgment':'Arithmetic judgment'}
t=d.add_table(rows=1,cols=3);t.style='Table Grid'
for cell,v in zip(t.rows[0].cells,['Quality field','Agreement','Kappa']):cell.text=v
for k,x in results['fields'].items():
    values=[names[k],f"{x['agree']}/48 ({x['agreement']*100:.2f}%)",f"{x['kappa']:.3f}" if x['kappa'] is not None else 'Undefined']
    for cell,v in zip(t.add_row().cells,values):cell.text=v
target._p.addprevious(t._tbl)
t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
for i,row in enumerate(t.rows):
    row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
    for cell in row.cells:
        for p in cell.paragraphs:
            p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(3)
            for run in p.runs:run.font.size=Pt(12);run.bold=i==0
target.insert_paragraph_before('The lowest agreement was for comparison judgments (32/48). For example, in H03 the author treated the contrast between participation cost and conditional no-volunteer loss as a correct comparison, whereas the assistant labelled comparison not applicable. In H02 the author marked action-reason consistency while noting the lack of a substantive supporting reason; the assistant marked the relation unclear. These examples show differences in applying the quality categories, not necessarily errors in the LLM\'s action. No adjudication has been performed.')
target.insert_paragraph_before('Unsupported-information agreement was 47/48, but kappa was 0 because the assistant used only the none category. Arithmetic agreement was 48/48, with both reviewers assigning not applicable throughout; kappa is therefore undefined. These high raw agreements do not demonstrate an ability to detect diverse unsupported claims or arithmetic mistakes. Category imbalance and prior AI-label access must be considered alongside the percentages.')
d.save(O/'Report.formal.en.docx')
md=[]
for el in d.element.body:
    if el.tag==qn('w:p'):
        p=Paragraph(el,d)
        if p.text:md += [('## ' if p.style.name.startswith('Heading') else '# ' if p.style.name=='Title' else '')+p.text,'']
    elif el.tag==qn('w:tbl'):
        rr=[[c.text.replace('|','/') for c in row.cells] for row in Table(el,d).rows]
        md+=['| '+' | '.join(rr[0])+' |','| '+' | '.join(['---']*len(rr[0]))+' |']+['| '+' | '.join(row)+' |' for row in rr[1:]]+['']
(O/'source/Report.en.md').write_text('\n'.join(md),encoding='utf-8')
assert len(d.tables)==5
assert 'human review is pending' not in '\n'.join(p.text for p in d.paragraphs)
print('Integrated disclosed author review and retained all original formal judgments.')
