from pathlib import Path
import shutil
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
R=Path(__file__).resolve().parents[1];O=R/'report';A=R/'local_archive/20261120_before_separate_supplement';B=O/'.build/separate_supplement_20261120'
A.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
for name in ('Report.docx','Report.zh-TW.docx','README.md','PACKAGE_COMPLETE.json'):
    if not (A/name).exists():shutil.copy2(O/name,A/name)
shutil.copy2(O/'upload/Project_Submission_20261120.zip',A/'Project_Submission_20261120.zip') if not (A/'Project_Submission_20261120.zip').exists() else None
for zh,name,suppname in [(False,'Report.docx','Supplement.en.docx'),(True,'Report.zh-TW.docx','Supplement.zh-TW.docx')]:
    main=Document(A/name);supp=Document(A/name)
    def appendix(d):return next(p for p in d.paragraphs if p.text.startswith(('Appendix A','附錄A')))
    node=appendix(main)._p
    while node is not None:
        nxt=node.getnext()
        if node.tag!=qn('w:sectPr'):node.getparent().remove(node)
        node=nxt
    for p in main.paragraphs:
        if 'Appendix A gives the matching method, audit counts and verbatim prompt examples.' in p.text:
            p.text=p.text.replace('Appendix A gives the matching method, audit counts and verbatim prompt examples.','The separate supplement, Reproduction Details and Prompt Examples (Supplement.en.docx), provides the matching method, audit counts and prompt examples.')
        if '附錄A提供配對方法、核對數據及提示原文' in p.text:
            p.text=p.text.replace('附錄A提供配對方法、核對數據及提示原文','另附《重現細節與提示範例》（Supplement.zh-TW.docx），提供配對方法、核對數據及提示內容')
    first=appendix(supp)._p
    for el in list(supp.element.body):
        if el is first:break
        supp.element.body.remove(el)
    title=supp.paragraphs[0];title.text='重現細節與提示範例' if zh else 'Reproduction Details and Prompt Examples';title.style=supp.styles['Title'];title.alignment=0
    title.paragraph_format.page_break_before=False;title.paragraph_format.space_before=Pt(0);title.paragraph_format.space_after=Pt(12)
    anchor=supp.paragraphs[1]
    for text in [
      'Supplement to Comparing LLM Volunteer Decisions with a Game Theory Model' if not zh else '《LLM 志工決策與賽局模型的比較》補充文件',
      'Author: Pin Kuang Shih   Advisor: Sai-Keung Wong' if not zh else '作者：Pin Kuang Shih　指導教授：Sai-Keung Wong',
      '20 November 2026' if not zh else '2026年11月20日',
      'This companion document supplies reproducibility details for the main report. Read the main report for the research questions, methods, results and limitations. This document retains the scheduling seeds, token-matching audit, actual prompt content and JSON schema. JSON indentation is for display only. Submit it alongside the main report so reviewers can inspect these details.' if not zh else '本文件提供主報告的重現明細。研究問題、方法、結果與限制仍請閱讀主報告；本文件保留排程種子、token配對檢查、實際提示內容及JSON格式。JSON縮排僅供閱讀。建議與主報告一併提供，方便審查者核對。']:
        p=anchor.insert_paragraph_before(text);p.paragraph_format.space_after=Pt(8)
        if zh:p.paragraph_format.line_spacing=1.15
    for p in supp.paragraphs:
        if p.style.name.startswith('Heading'):
            for old,new in [('A1 ','1 '),('A2 ','2 '),('A3 ','3 '),('A4 ','4 ')]:
                if p.text.startswith(old):p.text=new+p.text[len(old):]
        if 'Table A1' in p.text:p.text=p.text.replace('Table A1','Table S1')
        if '表A1' in p.text or '表 A1' in p.text:p.text=p.text.replace('表A1','表S1').replace('表 A1','表S1')
        if 'corresponding suffix in A3' in p.text:p.text=p.text.replace('corresponding suffix in A3','corresponding suffix in Section 3')
        if 'each condition suffix in A3' in p.text:p.text=p.text.replace('each condition suffix in A3','each condition suffix in Section 3')
        if '各條件後段列於A3' in p.text or '各條件後段列於 A3' in p.text:p.text=p.text.replace('各條件後段列於A3','各條件後段列於第3節').replace('各條件後段列於 A3','各條件後段列於第3節')
    for d,out in [(main,name),(supp,suppname)]:
        if out==name:
            assert len(d.tables)==7 and len(d.inline_shapes)==2
            assert [p.text for p in d.paragraphs if p.text.strip()][-1].startswith('[7]')
        else:assert len(d.tables)==1 and len(d.inline_shapes)==0 and len(d.sections)==1
        d.save(B/out)
        md=[]
        for el in d.element.body:
            if el.tag==qn('w:p'):
                p=Paragraph(el,d)
                if p.text:md.extend([('## ' if p.style.name.startswith('Heading') else '# ' if p.style.name=='Title' else '')+p.text,''])
            elif el.tag==qn('w:tbl'):
                rows=[[c.text.replace('|','/') for c in r.cells] for r in Table(el,d).rows];md.extend(['| '+' | '.join(rows[0])+' |','| '+' | '.join(['---']*len(rows[0]))+' |']+['| '+' | '.join(r)+' |' for r in rows[1:]]+[''])
        (B/out.replace('.docx','.md').replace('Report.docx','Report.en.md')).write_text('\n'.join(md),encoding='utf-8')
        print(out)
