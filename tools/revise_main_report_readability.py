from pathlib import Path
import re,shutil
from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
R=Path(__file__).resolve().parents[1];O=R/'report';A=R/'local_archive/20261120_before_readability_revision';A.mkdir(exist_ok=True,parents=True)
for name in ['Report.docx','Report.zh-TW.docx','README.md','PACKAGE_COMPLETE.json']:
    if not (A/name).exists():shutil.copy2(O/name,A/name)
for zh,name in [(False,'Report.docx'),(True,'Report.zh-TW.docx')]:
    d=Document(A/name);oldtables=[[[c.text for c in r.cells] for r in t.rows] for t in d.tables]
    def find(prefix):
        ps=[p for p in d.paragraphs if p.text.startswith(prefix)];assert len(ps)==1,prefix;return ps[0]
    def setp(prefix,text):find(prefix).text=text
    setp('本專題研究個人LLM' if zh else 'This project studies individual LLM',
      '本專題比較個人LLM志工選擇與撤離賽局參考，發現其協助意願取決於成本、所提供的資訊及選項順序。原研究收集840份回覆，參與率從低成本的100%降至高成本的89.17%，下降小於參考公式。另一次480份回覆的資訊控制實驗中，僅布局、匹配無關資訊及時間預測組的參與率分別為88.13%、72.50%及33.13%。預測組比控制組低39.38個百分點，但參與先列與拒絕先列時的差距分別為60.00與18.75點，顯示此差距依賴提示呈現方式。原資料的效用與理由分析提供探索性解讀，其中48則作者評分為非盲評。兩批資料分開分析，結果限於單一模型設定下的個人選擇，尚未驗證真人行為或群體撤離效率。' if zh else
      'This project compares individual LLM volunteering choices with an evacuation-game reference and finds that willingness depends on cost, information and option order. In the original 840-response study, participation fell from 100% at low cost to 89.17% at high cost, a smaller decline than the reference formula. In a separate 480-response information-control experiment, participation was 88.13% with layout alone, 72.50% with matched unrelated information and 33.13% with forecasts. Forecast participation was 39.38 percentage points below control, but the difference was 60.00 points with participate first and 18.75 with decline first, showing dependence on prompt presentation. Utility and explanation analyses provide exploratory interpretation of the original choices, including a non-blind author review of 48 responses. The batches remain separate, and the findings concern one model configuration without validation of human behavior or group evacuation efficiency.')
    setp('原研究（資料代號' if zh else 'The original study (dataset',
      '原研究包含840份回覆，後續資訊控制實驗另收集480份，檢查額外無關資訊與行動列舉順序的影響。兩批均於各自收集前鎖定設計，並分別分析及報告參與率。' if zh else
      'The original study contains 840 responses. A later information-control experiment adds 480 new responses to examine unrelated added information and action-option order. Each batch has its own design locked before collection, and their participation rates are analysed separately.')
    setp('控制組保留布局' if zh else 'The control retained the layout',
      '控制組保留相同布局，加入與行人、行動及結果無關的印刷目錄紀錄。控制與預測訊息匹配輸入token數與數字個數，但控制組的字元及詞數仍約多7–8%。因此這是針對部分文字量與數字差異的控制，不是完全相同的提示。只有一種無關資訊主題，語意、格式與注意力差異仍未排除；完整配對檢查保留於英文實驗紀錄。' if zh else
      'The control retained the layout and added printed catalogue records unrelated to pedestrians, actions or outcomes. Control and forecast messages matched input token counts and the number of numerical entries, although control character and word counts were about 7–8% greater. This addresses part of the text-and-number difference without making the prompts identical. One unrelated topic still leaves semantic, formatting and attention differences. Full matching checks are retained in the English experiment records.')
    # Remove internal bookkeeping identifiers and reproducibility constants from reader prose.
    for p in d.paragraphs:
        s=p.text
        if not s:continue
        s=s.replace('（封存代號P028）','').replace(' (archive ID P028)','')
        s=s.replace('（版本scenario-reasons-v3）','').replace(' (version scenario-reasons-v3)','')
        s=s.replace('例如H03作者','例如一則回應中，作者').replace('H02作者','另一則回應中，作者')
        s=s.replace('in H03 the author','in one response the author').replace('In H02 the author','In another response the author')
        s=re.sub(r',? with (?:order shuffled using )?seed 2026111661','',s)
        s=s.replace('with order shuffled using seed 2026111661','with randomized order')
        s=s.replace('Each block contained all 28 conditions once.','Each block contained all 28 conditions once in randomized order.')
        s=s.replace('using seed 2026112001','using a fixed randomization schedule')
        s=re.sub(r',? (?:with )?seed 202611(?:1662|2002)','',s)
        s=s.replace('以種子2026111661打亂順序','以固定隨機排程打亂順序')
        s=s.replace('排程種子為2026112001','排程於收集前固定')
        s=re.sub(r'，種子202611(?:1662|2002)','',s)
        if s!=p.text:p.text=s
    setp('5 原研究結果' if zh else '5 Original study results','5 研究結果' if zh else '5 Results')
    # Place the summary before the existing overview figure, preserving all evidence.
    result=find('5 研究結果' if zh else '5 Results')
    image=Paragraph(result._p.getnext(),d)
    image.insert_paragraph_before('5.1 主要發現' if zh else '5.1 Main findings',style='Heading 2')
    image.insert_paragraph_before(
      'LLM會隨協助成本上升而減少參與，但反應較賽局參考平緩。新實驗中，預測組比匹配無關資訊組少參與39.38個百分點；無關資訊組本身也低於僅布局組，因此原資訊差不能全部歸因於預測內容。預測減控制的差距在參與先列為−60.00點，拒絕先列為−18.75點，表示呈現順序也影響比較。這些是個人意願的條件差異，尚未證明對真人行為或撤離效率的影響。' if zh else
      'Participation declined as helping became more costly, but less than the game reference predicted. In the new experiment, forecast participation was 39.38 percentage points below matched unrelated information, while the control itself was below layout alone. The forecast-control difference was -60.00 points with participate first and -18.75 with decline first, showing that presentation order also matters. These findings describe individual willingness under stated conditions, without establishing effects on human behavior or evacuation efficiency.')
    find('報酬任務360份' if zh else 'The payoff task produced').insert_paragraph_before('5.2 協助成本與參與率' if zh else '5.2 Assistance cost and participation',style='Heading 2')
    find('物理任務僅幾何' if zh else 'In the physical task, participation').insert_paragraph_before('5.3 原物理任務的資訊比較' if zh else '5.3 Information comparison in the original physical task',style='Heading 2')
    setp('5.1 與個人' if zh else '5.1 Exploratory consistency','5.4 與個人預測效用的一致性探索' if zh else '5.4 Exploratory consistency with personal forecast utility')
    setp('5.2 理由品質' if zh else '5.2 Non-blind author','5.5 理由品質的作者非盲評' if zh else '5.5 Non-blind author review of explanation quality')
    setp('5.3 資訊控制' if zh else '5.3 Information control','5.6 資訊控制實驗結果' if zh else '5.6 Information control results')
    for p in d.paragraphs:
        if p.style.name.startswith('Heading'):p.paragraph_format.keep_with_next=True
        if p.text and not p._p.xpath('.//w:drawing'):
            snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');p._p.get_or_add_pPr().append(snap)
            if zh:p.paragraph_format.line_spacing=1.15
    for i,row in enumerate(d.tables[0].rows):
        for c in row.cells:
            for p in c.paragraphs:p.paragraph_format.keep_with_next=i<len(d.tables[0].rows)-1
    txt='\n'.join(p.text for p in d.paragraphs)
    assert not any(x in txt for x in ['P030','P031','P028','o200k_base','41 numeric literals','scenario-reasons-v3','2026111661','2026112001'])
    assert oldtables==[[[c.text for c in r.cells] for r in t.rows] for t in d.tables]
    assert len(d.sections)==2 and len(d.inline_shapes)==2
    staged=O/'.build/readability_20261120';staged.mkdir(parents=True,exist_ok=True)
    d.save(staged/name)
    md=[]
    for el in d.element.body:
        if el.tag==qn('w:p'):
            p=Paragraph(el,d)
            if p.text:md.extend([('## ' if p.style.name.startswith('Heading') else '# ' if p.style.name=='Title' else '')+p.text,''])
        elif el.tag==qn('w:tbl'):
            rows=[[c.text.replace('|','/') for c in row.cells] for row in Table(el,d).rows];md.extend(['| '+' | '.join(rows[0])+' |','| '+' | '.join(['---']*len(rows[0]))+' |']+['| '+' | '.join(r)+' |' for r in rows[1:]]+[''])
    (O/'source'/('Report.zh-TW.md' if zh else 'Report.en.md')).write_text('\n'.join(md),encoding='utf-8')
    print(name)
