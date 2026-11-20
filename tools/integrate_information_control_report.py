"""Integrate completed evidence in the main reports without pooling batches."""
from pathlib import Path
from copy import deepcopy
import json,shutil
from docx import Document
from docx.shared import Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.enum.section import WD_SECTION_START
R=Path(__file__).resolve().parents[1];O=R/'report';A=R/'local_archive/20261120_before_main_report_integration';A.mkdir(parents=True,exist_ok=True)
X=json.loads((R/'experiment_records/data/analysis/information_control_v1_20261120/RESULTS.json').read_text())
for name in ['Report.docx','Report.zh-TW.docx','README.md','PACKAGE_COMPLETE.json']:
    if not (A/name).exists():shutil.copy2(O/name,A/name)
def replace(d,prefix,value):
    found=[p for p in d.paragraphs if p.text.startswith(prefix)];assert len(found)==1,(prefix,len(found));found[0].text=value
def before(anchor,value,style=None):return anchor.insert_paragraph_before(value,style=style)
def table_before(d,anchor,headers,rows):
    t=d.add_table(rows=1,cols=len(headers));t.style='Table Grid'
    for c,v in zip(t.rows[0].cells,headers):c.text=v
    for row in rows:
        for c,v in zip(t.add_row().cells,row):c.text=str(v)
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
    for i,row in enumerate(t.rows):
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(3)
                p.paragraph_format.keep_with_next=i<len(t.rows)-1
                for run in p.runs:run.font.size=Pt(12);run.bold=i==0
    anchor._p.addprevious(t._tbl)
for zh,name in [(False,'Report.docx'),(True,'Report.zh-TW.docx')]:
    d=Document(A/name)
    replace(d,'19 November 2026','20 November 2026') if not zh else None
    if zh:
        for p in d.paragraphs:
            if '2026年11月19日' in p.text:p.text=p.text.replace('2026年11月19日','2026年11月20日')
    abstract=next(p for p in d.paragraphs if p.text==('摘要' if zh else 'Abstract'))
    nxt=Paragraph(abstract._p.getnext(),d)
    nxt.text=('本專題研究個人LLM在協助成本與資訊條件改變時的志工選擇，並與撤離模型的賽局參考比較。原研究收集840份回覆：低至高成本的參與率從100%降至89.17%，下降小於參考公式；物理任務僅布局與時間預測組分別為98.33%及26.25%。另於收集前鎖定一批480份的資訊控制實驗，兩批分開分析。新批僅布局、匹配無關資訊及時間預測組的參與率分別為88.13%、72.50%及33.13%；預測減控制組為−39.38個百分點，描述性95%區間[−42.50,−36.25]。但同一差距在參與先列時為−60.00點，拒絕先列時為−18.75點，顯示資訊比較依賴呈現順序。控制條件處理部分原有混淆，但不能識別單一機制。原資料的端點效用分析提供有條件的選擇解讀，48則作者非盲評則顯示理由品質一致程度隨欄位而異。結果適用於單一模型設定下的個人意願，未驗證真人行為或群體撤離效率。' if zh else 'This project studies individual LLM volunteering choices under different assistance costs and information conditions, using an evacuation game as a reference. The original study collected 840 responses. Participation fell from 100% at low cost to 89.17% at high cost, a smaller decline than the reference formula. In its physical task, participation was 98.33% with layout information and 26.25% with forecasts. A separately locked information-control experiment collected 480 further responses, analysed without pooling the batches. In the new batch, participation was 88.13% with layout alone, 72.50% with matched unrelated information and 33.13% with forecasts. Forecast minus control was -39.38 percentage points, with a descriptive 95% interval of [-42.50, -36.25]. This difference was -60.00 points when participation appeared first and -18.75 when declining appeared first. The comparison therefore depends on presentation order. The control addresses part of the original confound but does not identify one mechanism. An exploratory endpoint-utility analysis helps interpret the original choices. A non-blind author review of 48 explanations found field-dependent agreement. These findings concern individual willingness in one model configuration, with no validation of human behavior or group evacuation efficiency.')
    intro=next(p for p in d.paragraphs if p.text.startswith('每個請求代表' if zh else 'Each request represents'))
    before(intro,'原研究（資料代號P030）包含840份回覆；後續資訊控制實驗（P031）包含480份新回覆。後者檢查原預測比較是否也受到額外無關資訊與行動列舉順序影響。兩批分別鎖定、分析及報告，不合併為單一參與率。' if zh else 'The original study (dataset P030) contains 840 responses. A later information-control experiment (P031) adds 480 new responses to examine unrelated added information and action-option order. Each batch has its own locked design and analysis. Their participation rates are reported separately.')
    replace(d,'物理任務有10位' if zh else 'The physical task has 10','物理任務有10位行人及5個可搬移障礙物。B2至B5代表相關出口附近受阻的參考位置數，並非障礙物總數。M1與M4是每單位搬移工作的進度間隔，不是總時間、重量或受傷風險。原研究八種設定各測布局與時間預測兩組；資訊控制實驗則另加入匹配無關資訊組與兩種指令選項順序。' if zh else 'The physical task has 10 pedestrians and five movable obstacles. B2 through B5 count blocked reference positions near the relevant exit, not the total obstacles. M1 and M4 are progress intervals per manipulation unit, not total handling time, weight or injury risk. The original study tests each of eight settings with layout alone and with forecasts. The information-control experiment adds a matched unrelated-information group and two instruction option orders.')
    replace(d,'正式設計、提示' if zh else 'The formal design, prompts','原研究的正式設計、提示、模型設定、試次清單與停止規則均於該批收集前鎖定。使用gpt-6-luna，temperature=0.15、reasoning=none、輸出上限220 tokens。每次回覆包含簡短理由及participate或decline_assistance。願意協助不保證行人會被啟用或搬移使撤離更快。後續資訊控制實驗沿用相同模型設定，另行鎖定設計。' if zh else 'The original study locked its design, prompts, model settings, trial list and stopping rules before its collection. The model was gpt-6-luna, with temperature 0.15, reasoning none and a maximum output of 220 tokens. Each response contained a short explanation and either participate or decline_assistance. Willingness did not guarantee activation or faster evacuation. The later information-control experiment used the same model profile under a separately locked design.')
    method=next(p for p in d.paragraphs if p.text==('5 研究結果' if zh else '5 Results'))
    before(method,'4.1 資訊控制實驗設計' if zh else '4.1 Information control design','Heading 2')
    methods=[
    ('資訊控制設計在看過原研究結果後、任何新回覆之前鎖定。八種物理設定各有僅布局、匹配無關資訊、時間預測三組，交叉參與先列與拒絕先列兩種指令順序，每格10份，共48格、480次請求。十個完整隨機排程區塊各包含48格一次，排程種子為2026112001。此設計是針對既有發現提出的新實驗，不是原研究的事前假設。','The information-control design was locked after inspecting the original results but before any new response. Eight physical settings were crossed with three information groups (layout only, matched unrelated information and forecasts) and two instruction orders (participate first and decline first). Ten responses per full cell gave 48 cells and 480 requests. Ten randomized complete scheduling blocks each contained all 48 cells once, using seed 2026112001. This is a new experiment motivated by earlier findings, not an original-study hypothesis.'),
    ('控制組保留布局，加入與行人、行動及結果無關的印刷目錄紀錄。其完整使用者訊息以o200k_base代理匹配預測組token數，數字個數均為41；字元與詞數仍約多7–8%。供應商實際回傳的輸入token集合在全部16個設定與順序配對皆相符，但這不等於獨立驗證供應商tokenizer。只有一種無關資訊主題，仍可能有語意、格式與注意力差異。','The control retained the layout and added printed catalogue records unrelated to pedestrians, actions or outcomes. Complete user messages matched forecast-group token counts under the o200k_base proxy and both contained 41 numeric literals. Control character and word counts were still about 7–8% greater. Actual provider input-token sets matched in all 16 setting-order pairs. This does not independently establish the provider tokenizer. One unrelated topic leaves semantic, formatting and attention differences.'),
    ('兩處指令行動列舉反轉順序，角色、行動名稱、JSON結構與預測表列序保持固定，因此未完整排除語意順從或社會期待偏向。全部480次均由設定的付費API回傳指定gpt-6-luna，有效且ID唯一，無重試或替換模型。新增回應保留理由原文，但未進行新理由編碼或Unity模擬。','Two instruction-level action enumerations reversed order. Role, action names, JSON structure and forecast row order stayed fixed, leaving semantic compliance and social-desirability bias unresolved. All 480 requests returned the requested gpt-6-luna through the configured paid API, with valid replies and unique IDs, no retries and no model substitution. New explanations were retained verbatim without additional reason coding or Unity simulations.'),
    ('主要比較為新批內的預測減控制組及預測減布局組；控制減布局、順序差、交互作用及B2–B4與B5分組為預先指定的次要分析。每完整區塊先對設定及順序平均，再估計整體差。區間以5000次完整區塊bootstrap計算，種子2026112002，為逐項描述性95%區間，不是確認性檢定、等效性證據或同時涵蓋保證。','The primary comparisons were forecast minus control and forecast minus layout within the new batch. Prespecified secondary analyses covered control minus layout, order differences, their interaction and B2–B4 versus B5 subgroups. Contrasts averaged settings and orders within each complete block. Intervals used 5,000 whole-block bootstrap resamples, seed 2026112002. They are pointwise descriptive 95% intervals, not confirmatory tests, equivalence evidence or simultaneous coverage guarantees.')]
    for z,e in methods:before(method,z if zh else e)
    method.text='5 原研究結果' if zh else '5 Original study results'
    disc=next(p for p in d.paragraphs if p.text==('6 討論' if zh else '6 Discussion'))
    before(disc,'5.3 資訊控制實驗結果' if zh else '5.3 Information control results','Heading 2')
    before(disc,'新批480份回覆中，僅布局141/160（88.125%）參與，控制組116/160（72.5%），預測組53/160（33.125%）。表6列各物理設定的參與數，已合併兩種順序，每格分母為20。此處僅比較新批，不能把原研究的−72.08點直接當作新批預測效果。' if zh else 'Among the 480 new replies, layout-only participation was 141/160 (88.125%), control was 116/160 (72.5%) and forecast was 53/160 (33.125%). Table 6 gives participation counts by physical setting, combining orders with 20 replies per cell. These are concurrent comparisons within the new batch. The original -72.08-point difference does not substitute for the new estimates.')
    table_before(d,disc,['設定','布局','控制','預測'] if zh else ['Setting','Layout','Control','Forecast'],[[r['scenario']]+[f"{r[k]}/20" for k in ('geometry_only','length_control','calibrated_forecast')] for r in X['scenarioCounts']])
    before(disc,'預測減控制組為−39.375個百分點，描述性95%區間[−42.50,−36.25]；預測減布局為−55.00點[−59.375,−50.625]。控制減布局亦為−15.625點[−21.875,−10.625]。額外無關資訊也伴隨較低參與率，因此原差距不宜全歸因於決策預測；但這個控制也不能單獨識別文字長度的影響。' if zh else 'Forecast minus control was -39.375 percentage points, with a descriptive 95% interval of [-42.50, -36.25]. Forecast minus layout was -55.00 points [-59.375, -50.625]. Control minus layout was also negative, at -15.625 points [-21.875, -10.625]. Added unrelated information therefore accompanied lower participation too. The original difference cannot all be assigned to decision forecasts, while this one control does not isolate text length.')
    before(disc,'表7依指令選項順序列參與數，每格80份。拒絕先列減參與先列的順序差，在布局、控制與預測組分別為−21.25、−37.50、+3.75點。' if zh else 'Table 7 separates instruction orders, with 80 replies per cell. Decline-first minus participate-first differences were -21.25 points for layout, -37.50 for control and +3.75 for forecasts.')
    table_before(d,disc,['資訊','參與先列','拒絕先列'] if zh else ['Information','Participate first','Decline first'],[['布局' if zh else 'Layout','79/80 (98.75%)','62/80 (77.50%)'],['控制' if zh else 'Control','73/80 (91.25%)','43/80 (53.75%)'],['預測' if zh else 'Forecast','25/80 (31.25%)','28/80 (35.00%)']])
    before(disc,'預測減控制組在參與先列為−60.00點，拒絕先列為−18.75點；交互作用為+41.25點[32.50,50.00]，表示整體−39.375點不是跨呈現方式不變的效果。預先指定的B2–B4預測減控制差為−62.50點[−65.833,−59.167]，B5則為+30.00點[25.00,37.50]。兩個B5預測設定均20/20參與，但控制組未全數參與，呈現情境與順序的異質性。每完整條件僅10份，區間只依十個排程區塊估計，需保留精確度限制。' if zh else 'Forecast minus control was -60.00 points with participate first and -18.75 with decline first. The interaction was +41.25 points [32.50, 50.00], so the pooled -39.375-point contrast is not stable across presentation orders. The prespecified B2–B4 subgroup difference was -62.50 points [-65.833, -59.167], compared with +30.00 [25.00, 37.50] for B5. Both B5 forecast settings had 20/20 participation, while their controls did not, showing heterogeneity across settings as well as order. Each full condition has only ten replies, and intervals rely on ten scheduling blocks.')
    replace(d,'物理任務說明早期' if zh else 'The physical task also shows','資訊控制實驗改變了原物理結果的解讀：匹配無關資訊組也比布局組少參與15.625點，預測組則仍比控制少39.375點。時間結果資訊可能與選擇有關，但單一控制未識別內部原因，而且兩種順序的預測減控制差相差41.25點。比起把LLM描述為固定偏好協助，更合理的結論是其意願取決於情境、資訊內容與指令呈現。' if zh else 'The information-control experiment changes the interpretation of the original physical result. Matched unrelated information accompanied a 15.625-point decline from layout alone, while forecasts remained 39.375 points below control. Outcome information may matter for choices, but one control does not identify an internal cause, and the forecast-control difference varied by 41.25 points across orders. Willingness depends on the setting and prompt presentation, making a fixed preference for helping an incomplete description.')
    replace(d,'貢獻是在明確條件下' if zh else 'The contribution is a measured','本研究的貢獻是把與數學參考的成本反應比較，連結至物理資訊與呈現順序下的個人選擇。新控制讓原本整包資訊差的主張更具體，也顯示無關資訊與順序不能忽略。原理由品質與效用分析仍提供探索性解讀，不把新批未編碼的理由當作額外驗證。這些發現不需要以LLM優於原撤離政策為前提。' if zh else 'The contribution connects a cost-response comparison against a mathematical reference with individual choices under physical information and option order. The new control narrows the original information-package claim and shows why unrelated content and presentation matter. Original reason-quality and utility analyses remain exploratory, without treating uncoded new explanations as further validation. These findings do not depend on showing that the LLM improves an evacuation policy.')
    replace(d,'物理任務最大的設計限制' if zh else 'The largest design limitation','匹配控制處理原預測提示同時增加文字與數字的部分混淆，卻只有一種無關主題，未完全匹配字元、詞數、語意或注意力。順序操弄僅反轉兩處指令列舉，未改預測表列序及行動名稱，故不能宣稱排除所有順從偏向。研究只測單一模型與temperature=0.15，未驗證後端版本一致性或其他模型。原研究每格30份、新實驗每完整條件10份；十區塊的新區間穩定性有限。請求相依與時間效應仍未排除。預測僅六組開發種子，截尾及標準化是研究選擇，非經驗驗證的人類量測。' if zh else 'The matched control addresses part of the original text-and-number confound but uses only one unrelated topic. Character counts, word counts, semantics and attention are not fully matched. Counterbalancing reverses only two instruction enumerations, leaving forecast row order and action names fixed. It cannot rule out all compliance bias. The study tests one model at temperature 0.15, without establishing a constant backend version or testing other models. The original cells have 30 replies and the new full cells ten. New intervals based on ten blocks have limited stability. Request dependence and timing remain unresolved. Forecasts use six development seeds, and their capping and normalization remain research choices rather than validated human measurements.')
    replace(d,'本研究提供可重現的' if zh else 'The contribution is a reproducible','本研究發現，LLM成本反應較調整賽局參考平緩；其物理選擇則隨資訊、情境與選項順序改變。新控制下預測與控制仍有差距，但差的大小不具呈現不變性。端點分析指出哪些原選擇可用跨背景穩定的自身平均效用解讀，哪些需要未知信念。兩批資料分開支持這些範圍有限的結果。後續可檢查其他模型、多種控制主題與群體結果，而不預設LLM是更好的策略。' if zh else 'The model showed a flatter cost response than the adjusted game reference, while physical choices varied with information, setting and option order. Forecast and control participation still differed in the new experiment, but the size of that difference depended on presentation. Endpoint analysis identifies which original choices agree with stable personal mean-utility preferences and which require unknown beliefs. The two separately analysed batches support these bounded findings. Other models, multiple control topics and group outcomes remain useful extensions without assuming the LLM is a better policy.')
    for style in ('Normal','Heading 1','Heading 2'):
        d.styles[style].font.size=Pt(12 if style=='Normal' else 14);d.styles[style].font.color.rgb=RGBColor(0,0,0)
    for p in d.paragraphs:
        if p.style.name.startswith('Heading'):p.paragraph_format.keep_with_next=True
        if p._p.xpath('.//w:drawing'):p.paragraph_format.line_spacing=None
        elif p.text:
            snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');p._p.get_or_add_pPr().append(snap)
            if zh:p.paragraph_format.line_spacing=1.15
        if p.text.startswith('Table 6 ') or p.text.startswith('Table 7 ') or p.text.startswith('表6') or p.text.startswith('表7'):p.paragraph_format.keep_with_next=True
        if p.text.startswith('Figure 1.'):
            p.text='Figure 1. Original study workflow. The information-control experiment uses the same individual request and validation process with a separately locked 480-trial design (Section 4.1). Activation and movement remain simulator responsibilities.'
        if p.text.startswith('圖1'):
            p.text='圖1 原研究流程。資訊控制實驗沿用個人請求與驗證程序，另鎖定480次設計（第4.1節）。啟用與移動仍由模擬器負責，圖內保留英文。'
    for row in d.tables[0].rows:
        for c in row.cells:
            for p in c.paragraphs:p.paragraph_format.space_before=Pt(1);p.paragraph_format.space_after=Pt(1)
    # Keep the existing title/advisor block as a separate unnumbered cover.
    d.add_section(WD_SECTION_START.NEW_PAGE)
    boundary=d.paragraphs[-1]._p;abstract._p.addprevious(boundary)
    cover,body=d.sections
    body.footer.is_linked_to_previous=False
    for sec in (cover,body):
        for p in sec.footer.paragraphs:p.clear()
    pg=OxmlElement('w:pgNumType');pg.set(qn('w:start'),'1');body._sectPr.append(pg)
    footer=body.footer.paragraphs[0];footer.alignment=2
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
    assert len(d.tables)==7 and len(d.inline_shapes)==2
    assert [p.text for p in d.paragraphs if p.text.strip()][-1].startswith('[7]')
    d.save(O/name)
    md=[]
    for el in d.element.body:
        if el.tag==qn('w:p'):
            p=Paragraph(el,d)
            if p.text:md.extend([('## ' if p.style.name.startswith('Heading') else '# ' if p.style.name=='Title' else '')+p.text,''])
        elif el.tag==qn('w:tbl'):
            rows=[[c.text.replace('|','/') for c in row.cells] for row in Table(el,d).rows];md.extend(['| '+' | '.join(rows[0])+' |','| '+' | '.join(['---']*len(rows[0]))+' |']+['| '+' | '.join(row)+' |' for row in rows[1:]]+[''])
    (O/'source'/('Report.zh-TW.md' if zh else 'Report.en.md')).write_text('\n'.join(md),encoding='utf-8')
    print(name)
