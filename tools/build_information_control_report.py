"""Create concise bilingual study reports only after the complete locked analysis."""
from pathlib import Path
import csv,json
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
R=Path(__file__).resolve().parents[1];A=R/'experiment_records/data/analysis/information_control_v1_20261120';O=R/'report'
def table(d,headers,rows):
    t=d.add_table(rows=1,cols=len(headers));t.style='Table Grid'
    for cell,text in zip(t.rows[0].cells,headers):cell.text=str(text)
    for row in rows:
        for cell,text in zip(t.add_row().cells,row):cell.text=str(text)
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
    for i,row in enumerate(t.rows):
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.keep_with_next=i<len(t.rows)-1
                p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(3)
                for run in p.runs:run.bold=i==0;run.font.size=Pt(12)
    d.add_paragraph()
def build():
    x=json.loads((A/'RESULTS.json').read_text(encoding='utf-8'));assert x['n']==480
    with (A/'TRIALS.csv').open(encoding='utf-8',newline='') as f:trials=list(csv.DictReader(f))
    for chinese in (False,True):
        d=Document();s=d.sections[0];s.page_width=Cm(21);s.page_height=Cm(29.7);s.top_margin=s.bottom_margin=Cm(2);s.left_margin=s.right_margin=Cm(2)
        font='Microsoft JhengHei' if chinese else 'Times New Roman'
        for name in ('Normal','Title','Heading 1','Heading 2'):
            st=d.styles[name];st.font.name=font;st.font.size=Pt(18 if name=='Title' else 12 if name=='Normal' else 14);st.font.color.rgb=RGBColor(0,0,0);st.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),font)
            st.paragraph_format.space_after=Pt(6);st.paragraph_format.line_spacing=1.15
        p=s.footer.paragraphs[0];p.alignment=2;field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');p._p.append(field)
        d.add_paragraph('資訊控制補充實驗' if chinese else 'Information Control Follow-up',style='Title')
        d.add_paragraph('2026年11月20日｜P031｜與原840筆分開分析' if chinese else '20 November 2026 | P031 | Independent analysis of a new batch')
        groups={g['information']:g for g in x['groups']};cons=x['contrasts']
        names={'geometry_only':'僅布局' if chinese else 'Geometry only','length_control':'匹配控制組' if chinese else 'Matched control','calibrated_forecast':'時間預測' if chinese else 'Forecast'}
        rates='、'.join(f"{names[k]} {v['participate']}/160（{v['rate']*100:.2f}%）" for k,v in groups.items()) if chinese else '; '.join(f"{names[k]} {v['participate']}/160 ({v['rate']*100:.2f}%)" for k,v in groups.items())
        d.add_paragraph('摘要' if chinese else 'Summary',style='Heading 1')
        d.add_paragraph(('本批完成480次真實API決策：'+rates+'。預測減控制組差為'+f"{cons['forecast_minus_control']['percentagePoints']:+.2f}"+'個百分點；控制組減僅布局為'+f"{cons['control_minus_geometry']['percentagePoints']:+.2f}"+'點。這批比較特定預測資訊與一種匹配行政資訊控制，沒有與原840份回覆合併，也不將差異解讀為單一內部機制。') if chinese else ('This new batch completed 480 real API choices: '+rates+'. Forecast minus control was '+f"{cons['forecast_minus_control']['percentagePoints']:+.2f}"+' percentage points; control minus geometry was '+f"{cons['control_minus_geometry']['percentagePoints']:+.2f}"+' points. These estimates compare the forecast package with one matched administrative control, without pooling historical responses or identifying one internal mechanism.'))
        d.add_paragraph('選項順序下的選擇' if chinese else 'Choices by instruction order',style='Heading 1')
        order_counts={}
        order_rows=[]
        for info in ('geometry_only','length_control','calibrated_forecast'):
            vals=[]
            for order in ('participate_first','decline_first'):
                n=sum(int(t['participate']) for t in trials if t['information']==info and t['optionOrder']==order);order_counts[info,order]=n
                vals.append(f'{n}/80 ({n/80*100:.2f}%)')
            order_rows.append([names[info]]+vals)
        table(d,['資訊條件','參與先列','拒絕先列'] if chinese else ['Information','Participate first','Decline first'],order_rows)
        pf=(order_counts['calibrated_forecast','participate_first']-order_counts['length_control','participate_first'])/80*100
        df=(order_counts['calibrated_forecast','decline_first']-order_counts['length_control','decline_first'])/80*100
        d.add_paragraph(('兩種順序下的預測減控制組差分別為'+f'{pf:+.2f}、{df:+.2f}'+'個百分點，差的大小會隨順序改變。因此整體平均的−39.38點不能當作跨提示呈現方式固定不變的效果，也不能把控制組的下降單獨歸因於文字長度。') if chinese else (f'Forecast-minus-control was {pf:+.2f} points with participate first and {df:+.2f} points with decline first. Its magnitude depends on presentation order. The pooled -39.38-point contrast is therefore not a presentation-invariant effect, and the control-related decline cannot be attributed to text length alone.'))
        d.add_paragraph('設計與執行' if chinese else 'Design and execution',style='Heading 1')
        d.add_paragraph('設計在看到P030結果後、但任何新回覆之前鎖定。8種物理設定、3個資訊條件、2種選項順序，各10次，共10個完整隨機排程區塊、480份；每資訊條件160份。反轉兩處明列行動的順序，保持代碼、角色及JSON格式不變。沿用gpt-6-luna、temperature=0.15、reasoning=none、輸出上限220 tokens。每試次只允許一次，無重試；沒有更換免費或其他模型。這是API意願決策，不是新Unity撤離模擬。' if chinese else 'The design was locked after inspecting P030 but before any new response. Eight physical settings, three information conditions and two action orders were repeated in ten complete randomized scheduling blocks: 480 requests, 160 per information condition. Both explicit action enumerations were reversed while codes, role and JSON schema stayed fixed. The requested profile remained gpt-6-luna, temperature 0.15, reasoning none and maximum 220 output tokens. Each trial allowed one attempt, without retries or model substitution. These are API willingness choices, not new Unity evacuation runs.')
        d.add_paragraph('控制組保留相同布局，加入與行人、行動或結果無關的印刷目錄紀錄。以o200k_base代理匹配完整使用者訊息token數，與預測組相同；數字個數皆41。字元及詞數仍約多7–8%，供應商實際用量另行保存，不宣稱已確定模型真正的tokenizer。只有一種無關資訊主題，仍可能存在語意、注意力或格式效應。' if chinese else 'The control retained the layout and added printed catalogue records unrelated to pedestrians, actions or outcomes. Entire user-message lengths matched the o200k_base proxy token counts, with 41 numeric literals per full control/forecast message. Control character and lexical-word counts were about 7-8% longer. Actual provider input-token usage is preserved; the provider tokenizer is not independently established. One control topic leaves possible semantic, attention and format effects.')
        d.add_paragraph().add_run().add_picture(str(A/'RESULTS.png'),width=Cm(16.8))
        d.add_paragraph('圖1　三種資訊條件的參與數及描述性差異區間。原英文圖保留。' if chinese else 'Figure 1. Participation counts and pointwise descriptive contrast intervals.')
        d.add_paragraph('完整設定計數' if chinese else 'Counts by physical setting',style='Heading 1')
        table(d,['設定','僅布局','控制組','預測'] if chinese else ['Setting','Geometry','Control','Forecast'],[[r['scenario']]+[f"{r[k]}/20" for k in ('geometry_only','length_control','calibrated_forecast')] for r in x['scenarioCounts']])
        d.add_paragraph('預先指定比較' if chinese else 'Prespecified comparisons',style='Heading 1')
        contrastnames={'forecast_minus_control':('預測減控制組','Forecast minus control'),'forecast_minus_geometry':('預測減僅布局','Forecast minus geometry'),'control_minus_geometry':('控制組減僅布局','Control minus geometry'),'order_difference_geometry_only':('順序差：僅布局','Order effect: geometry'),'order_difference_length_control':('順序差：控制組','Order effect: control'),'order_difference_calibrated_forecast':('順序差：預測','Order effect: forecast'),'order_interaction_forecast_control':('順序交互作用','Order interaction')}
        table(d,['比較','百分點','描述性95%區間'] if chinese else ['Comparison','Points','Descriptive 95% interval'],[[labels[0 if chinese else 1],f"{cons[k]['percentagePoints']:+.2f}",f"[{cons[k]['descriptive95PercentileInterval'][0]*100:.2f}, {cons[k]['descriptive95PercentileInterval'][1]*100:.2f}]"] for k,labels in contrastnames.items()])
        d.add_paragraph('順序差為拒絕先列減參與先列；交互作用為兩種順序的「預測減控制組」差。兩項主要比較是預測減控制組與預測減僅布局，其餘為次要分析。區間使用10個完整區塊的5000次bootstrap，種子2026112002，是逐項描述性區間，不是確認性檢定、同時涵蓋或等效性證據。' if chinese else 'Order effects are decline-first minus participate-first; the interaction is the difference in forecast-minus-control between orders. Forecast-minus-control and forecast-minus-geometry are the two primary comparisons; the rest are secondary. Intervals use 5,000 bootstrap resamples of ten complete scheduling blocks, seed 2026112002. They are pointwise descriptive intervals, not confirmatory tests, simultaneous coverage or equivalence evidence.')
        d.add_paragraph('解讀範圍' if chinese else 'Interpretation limits',style='Heading 1')
        d.add_paragraph('不能因控制組與布局組接近就宣稱完全無影響，也不能把順序差小當作排除所有順從或社會期待偏向。本批只反轉指令中的兩處行動列舉，預測表列序與行動名稱保持固定。每完整條件僅10份，10個區塊的區間穩定性有限；同一模型輸出不是獨立真人。背景機率仍未知，混合意願未校準。理由原文保留，未進行新理由編碼；沒有新真人或群體效率驗證。原P030的−72.08個百分點是歷史結果，本批必須用自己的同期比較解讀。' if chinese else 'A small control-minus-geometry difference does not prove no effect. A small order effect does not rule out semantic compliance or social-desirability bias. Only the two instruction-level action enumerations were reversed; forecast row order and action names stayed fixed. Ten responses per full cell and ten blocks limit precision and interval stability; repeated model outputs are not independent humans. Background probabilities remain unknown and mixed willingness profiles uncalibrated. Reasons are retained without new coding, and no human-behavior or group-efficiency validation is added. The historical P030 difference of -72.08 percentage points is not substituted for this batch\'s concurrent estimates.')
        d.add_paragraph(('API回傳用量：' if chinese else 'Provider-reported usage: ')+json.dumps(x['usage'])+('。實際扣款以供應商帳單為準。' if chinese else '. Actual billing remains provider-side.'))
        d.add_paragraph('資料紀錄' if chinese else 'Study records',style='Heading 1')
        d.add_paragraph('設計、請求順序及來源雜湊封存於information_control_v1_20261120準備資料夾；原始回覆、逐筆宣告與結果保存在同名run資料夾。分析檔含完整480筆回覆、48格摘要、各設定計數、區塊比較與token核對。這些是本機研究紀錄，不是公開文獻或新的人類研究。' if chinese else 'Design, request schedule and source hashes are sealed in the information_control_v1_20261120 preparation folder. Raw replies, dispatch claims and results remain in the matching run folder. Analysis includes all 480 replies, 48 cell summaries, scenario counts, block contrasts and token audits. These are local study records, not an external publication or a new human study.')
        for p in d.paragraphs:
            if chinese:
                snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');p._p.get_or_add_pPr().append(snap)
                if not p._p.xpath('.//w:drawing'):
                    p.paragraph_format.line_spacing=1.0
                    p.paragraph_format.space_after=Pt(4)
            if p._p.xpath('.//w:drawing'):p.paragraph_format.keep_with_next=True
        d.core_properties.language='zh-TW' if chinese else 'en-US'
        name='Followup_Information_Control.zh-TW.docx' if chinese else 'Followup_Information_Control.en.docx';d.save(O/name);print(name)
if __name__=='__main__':build()
