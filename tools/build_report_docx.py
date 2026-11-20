"""Build the current local-only report with requested 14/12 typography."""
from pathlib import Path
import argparse
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'report'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--language',choices=('en','zh-TW'),default='en')
args=parser.parse_args();chinese=args.language=='zh-TW'
source=OUT/f'source/Report.{args.language}.md'
doc=Document();sec=doc.sections[0];sec.page_height=Cm(29.7);sec.page_width=Cm(21)
sec.top_margin=sec.bottom_margin=sec.left_margin=sec.right_margin=Cm(2)
for name in ('Normal','Title','Heading 1','Heading 2'):
    style=doc.styles[name];style.font.name='Microsoft JhengHei' if chinese else 'Times New Roman';style.font.size=Pt(12 if name=='Normal' else 14);style.font.color.rgb=RGBColor(0,0,0)
    style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Microsoft JhengHei' if chinese else 'Times New Roman')
    pf=style.paragraph_format;pf.line_spacing=1.2;pf.space_after=Pt(6);pf.page_break_before=False
    if name!='Normal':style.font.bold=True;pf.keep_with_next=True;pf.space_before=Pt(10)
doc.styles['Title'].font.size=Pt(18)
footer=sec.footer.paragraphs[0];footer.alignment=2
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
lines=source.read_text(encoding='utf-8').splitlines();i=0
while i<len(lines):
    text=lines[i].strip();i+=1
    if not text:continue
    if text.startswith('|'):
        raw=[text]
        while i<len(lines) and lines[i].strip().startswith('|'):raw.append(lines[i].strip());i+=1
        values=[[x.strip() for x in line.strip('|').split('|')] for line in raw if line.replace('|','').replace('-','').replace(':','').strip()]
        table=doc.add_table(rows=1,cols=len(values[0]));table.autofit=False
        widths=[1.4,1.4,4.4,5.5,3.8] if len(values[0])==5 else [4.4,6.1,6.1]
        for k,width in enumerate(widths):table.columns[k].width=Cm(width)
        for rownum,row in enumerate(values):
            cells=table.rows[0].cells if rownum==0 else table.add_row().cells
            for k,value in enumerate(row):
                cell=cells[k];cell.width=Cm(widths[k]);cell.text=value;cell.vertical_alignment=1
                for p in cell.paragraphs:
                    p.alignment=1;p.paragraph_format.space_before=Pt(5);p.paragraph_format.space_after=Pt(5)
                    for run in p.runs:run.font.size=Pt(12);run.font.bold=rownum==0
                pr=cell._tc.get_or_add_tcPr();borders=OxmlElement('w:tcBorders')
                for edge in ('top','left','bottom','right'):
                    e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
                pr.append(borders)
                if rownum==0:
                    fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'E9EFF3');pr.append(fill)
            pr=table.rows[rownum]._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
            if rownum==0:pr.append(OxmlElement('w:tblHeader'))
        doc.add_paragraph();continue
    if text.startswith('# '):doc.add_paragraph(text[2:],style='Title')
    elif text.startswith('## '):
        doc.add_paragraph(text[3:],style='Heading 1')
        if text==('## 5 研究結果' if chinese else '## 5 Results'):
            doc.add_paragraph().add_run().add_picture(str(ROOT/'experiment_records/data/analysis/scenario_formal_v1_20261116/SCENARIO_RESULTS.png'),width=Cm(16.8))
            doc.add_paragraph('圖1　報酬與物理條件的參與分布。每條件30份回覆，連線僅連接測試過的成本水準。' if chinese else 'Figure 1. Participation across payoff and physical conditions. Each condition has 30 responses. Lines connect only the tested cost levels.')
    else:
        p=doc.add_paragraph(text)
        if text.startswith('['):p.paragraph_format.keep_together=True
        if text.startswith(('Table ','表1','表2')):p.paragraph_format.keep_with_next=True
for root in (doc.styles.element,doc.element):
    for border in list(root.iter(qn('w:pBdr'))):border.getparent().remove(border)
doc.core_properties.title=lines[0].removeprefix('# ')
doc.core_properties.subject='P030 individual decision study'
doc.core_properties.language='zh-TW' if chinese else 'en-US'
assert (ROOT/'local_archive/20261118_english_report/Report.docx').exists()
target=OUT/('Report.zh-TW.docx' if chinese else 'Report.docx')
doc.save(target);print(target)
