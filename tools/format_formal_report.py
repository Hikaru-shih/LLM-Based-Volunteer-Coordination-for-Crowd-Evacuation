"""Add a formal title page and advisor metadata to the existing English report."""
import json,argparse
from pathlib import Path
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'report'
parser=argparse.ArgumentParser();parser.add_argument('--metadata',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--input',type=Path,default=OUT/'Report.docx');args=parser.parse_args()
meta=json.loads(args.metadata.read_text(encoding='utf-8'));advisor=meta.get('advisorDisplayName')
draft=not advisor
doc=Document(args.input)
for name in ('Normal','Title','Heading 1','Heading 2'):
    style=doc.styles[name];style.font.name='Times New Roman';style.font.color.rgb=RGBColor(0,0,0)
    style.font.size=Pt(18 if name=='Title' else 12 if name=='Normal' else 14)
    fonts=style.element.get_or_add_rPr().rFonts
    for key in ('asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme'):
        if fonts.get(qn('w:'+key)) is not None:del fonts.attrib[qn('w:'+key)]
    for key in ('ascii','hAnsi','eastAsia','cs'):fonts.set(qn('w:'+key),'Times New Roman')
    style.paragraph_format.page_break_before=False
for section in doc.sections:
    section.page_height=Cm(29.7);section.page_width=Cm(21)
    section.top_margin=section.bottom_margin=section.left_margin=section.right_margin=Cm(2.54)
paras=doc.paragraphs
assert paras[0].text.startswith('Comparing LLM Volunteer Decisions')
assert paras[1].text=='Research report for supervisor review'
abstract=next(p for p in paras if p.text=='Abstract')
title=paras[0];subtitle=paras[1];date=paras[2]
title.alignment=1;title.paragraph_format.space_before=Pt(112);title.paragraph_format.space_after=Pt(28)
subtitle.text='Graduation Project Report';subtitle.alignment=1;subtitle.paragraph_format.space_after=Pt(64)
advisor_p=date.insert_paragraph_before('Advisor: '+(advisor or '[Advisor name required]'))
advisor_p.alignment=1;advisor_p.paragraph_format.space_after=Pt(24)
date.text=meta.get('dateDisplay','18 November 2026');date.alignment=1
for p in (subtitle,advisor_p,date):
    p.style=doc.styles['Normal']
    for run in p.runs:run.font.size=Pt(12);run.font.name='Times New Roman'
title.paragraph_format.keep_with_next=True;subtitle.paragraph_format.keep_with_next=True;advisor_p.paragraph_format.keep_with_next=True
# Put the cover before the body without adding a decorative divider line.
doc.add_section(WD_SECTION_START.NEW_PAGE)
break_p=doc.paragraphs[-1]._p;abstract._p.addprevious(break_p)
assert len(doc.sections)==2
cover,body=doc.sections
body.footer.is_linked_to_previous=False
for section in (cover,body):
    section.different_first_page_header_footer=False
    for p in section.footer.paragraphs:p.clear()
pg=OxmlElement('w:pgNumType');pg.set(qn('w:start'),'1');body._sectPr.append(pg)
p=body.footer.paragraphs[0];p.alignment=2
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');p._p.append(field)
for table in doc.tables:
    for i,row in enumerate(table.rows):
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.keep_with_next=i<len(table.rows)-1
                p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(3)
for root in (doc.styles.element,doc.element):
    for border in list(root.iter(qn('w:pBdr'))):border.getparent().remove(border)
doc.core_properties.language='en-US';doc.core_properties.subject='Graduation project report'
args.output.parent.mkdir(parents=True,exist_ok=True);doc.save(args.output)
print({'output':str(args.output),'advisorProvided':not draft,'coverPage':True,'bodyPaginationStartsAt':1})
