from pathlib import Path
import json,shutil
from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
R=Path(__file__).resolve().parents[1];O=R/'report';B=O/'.build/json_polish_20261120';B.mkdir(parents=True,exist_ok=True)
A=R/'local_archive/20261120_before_json_polish';A.mkdir(parents=True,exist_ok=True)
for name in ('Report.docx','Report.zh-TW.docx','README.md','PACKAGE_COMPLETE.json'):
    if not (A/name).exists():shutil.copy2(O/name,A/name)
def pretty(v,level=0,extra=0):
    flat=json.dumps(v,ensure_ascii=False)
    if len(flat)+2*level+extra<=60:return flat
    pad='  '*level;child='  '*(level+1)
    if isinstance(v,dict):return '{\n'+',\n'.join(child+json.dumps(k)+': '+pretty(x,level+1,len(json.dumps(k))+2) for k,x in v.items())+'\n'+pad+'}'
    if isinstance(v,list):return '[\n'+',\n'.join(child+pretty(x,level+1) for x in v)+'\n'+pad+']'
    return flat
for zh,name in [(False,'Report.docx'),(True,'Report.zh-TW.docx')]:
    d=Document(A/name);tables=[[[c.text for c in r.cells] for r in t.rows] for t in d.tables]
    start=next(p for p in d.paragraphs if p.text==('6 討論' if zh else '6 Discussion'))
    end=next(p for p in d.paragraphs if p.text.startswith('7 限制' if zh else '7 Limitations'))
    node=start._p.getnext()
    while node is not end._p:
        nxt=node.getnext();node.getparent().remove(node);node=nxt
    texts=[
      ('成本反應與參考公式的差異，必須連同參與率水準解讀。模型在低成本時已接近全數參與，因此較平緩的下降同時反映基準傾向與成本敏感度。參考另含提示未提供的撤離行為調整，偏離公式不能直接當作不理性或較符合人類的證據。','The cost-response difference needs to be read alongside the participation level. Near-universal participation at low cost means the flatter decline can reflect both a high baseline tendency to help and cost sensitivity. The reference also includes evacuation adjustments absent from the prompt, so departures from it do not directly establish irrationality or human realism.'),
      ('資訊控制實驗顯示，原差距不能全歸因於有用的時間預測：無關資訊本身也伴隨不同選擇。預測與控制仍有差距，但差的大小依賴選項順序。這支持在比較代理決策時控制提示呈現，而不是把高協助率視為固定的合作特質；單一控制主題仍未識別內部機制。','The control experiment shows why the original information difference cannot be assigned entirely to useful forecasts: unrelated information also accompanied different choices. Forecast and control participation still differed, but the size depended on option order. Agent comparisons therefore need to control presentation rather than treat high assistance as a fixed cooperative trait. One control topic still leaves the internal mechanism unresolved.'),
      ('效用分析只在已提供的條件平均值下協助解讀選擇，沒有量測模型信念；理由品質分析則檢查文字能支持多少推論，並受AI編碼與作者先前接觸標籤限制。兩者都是輔助分析。這項研究的貢獻，是在共同任務下明確呈現數學參考、資訊條件與呈現順序的差異，而非證明LLM改善群體撤離；其他模型、多種控制主題與較大樣本仍是後續工作。','The utility analysis interprets choices only under the supplied conditional means, without eliciting beliefs. Explanation analysis checks how much the text supports an interpretation, with limits from AI coding and prior author exposure. Both are supporting analyses. The contribution is a controlled comparison with a mathematical reference that makes information and presentation differences explicit. Whether these choices improve group evacuation, persist across models or generalize beyond one control topic remains for later work.')]
    for z,e in texts:
        p=end.insert_paragraph_before(z if zh else e)
        if zh:p.paragraph_format.line_spacing=1.15
        snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');p._p.get_or_add_pPr().append(snap)
    appendix=False;blocks=0
    for p in d.paragraphs:
        if p.text.startswith(('Appendix A','附錄A')):appendix=True
        if not appendix:continue
        if p.text.startswith('A2 Verbatim'):p.text='A2 Prompt example'
        if p.text.startswith('These texts come from locked'):
            p.text='These examples come from locked B2_M1, participate-first requests. The shared prefix is printed once, followed by each condition suffix in A3. Natural-language wording is unchanged. JSON blocks use added indentation and line breaks for reading, so their displayed whitespace differs from the actual input used for token counts in Table A1. Field names, order and values are unchanged. The original prefix ends without a newline, layout/control suffixes start with a space, and the forecast suffix starts with a newline.'
        if p.text.startswith('以下取自鎖定'):
            p.text='以下取自鎖定的B2_M1、參與先列請求，共用前段只印一次，各條件後段列於A3。自然語言措辭不變；JSON另加縮排換行方便閱讀，顯示的空白不同於表A1計算token時的實際輸入，但欄位、順序與數值不變。原始共用前段結尾無換行，布局與控制後段以空格開始，預測後段以換行開始。'
        if p.text.startswith('The example messages and schema come'):
            p.text='The example content and schema come from sealed requests rather than post-outcome rewriting. JSON indentation is for display only. The token audit uses the original serialized inputs. All 480 request payloads, source hashes and per-request usage remain in project records, which have not been publicly deposited.'
        if p.text.startswith('本附錄的三組訊息'):
            p.text='範例內容及格式來自封存請求，而非依結果重寫。JSON縮排僅供顯示，token核對使用原始序列化輸入。完整480筆請求、來源雜湊與逐次用量仍保留於專案紀錄，目前尚未公開存放。'
        s=p.text
        if s.startswith(('{','[')):
            try:value=json.loads(s)
            except ValueError:continue
            p.text=pretty(value);blocks+=1
            p.paragraph_format.line_spacing=1.0
            p.paragraph_format.space_before=Pt(5);p.paragraph_format.space_after=Pt(7)
            p.paragraph_format.widow_control=True
            p.paragraph_format.keep_together=False
            for run in p.runs:
                run.font.name='Consolas';run.font.size=Pt(12)
                fonts=run._r.get_or_add_rPr().rFonts
                for key in ('ascii','hAnsi','eastAsia','cs'):fonts.set(qn('w:'+key),'Consolas')
                for key in ('asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme'):
                    if qn('w:'+key) in fonts.attrib:del fonts.attrib[qn('w:'+key)]
    assert blocks==4 and tables==[[[c.text for c in r.cells] for r in t.rows] for t in d.tables]
    d.save(B/name)
    md=[]
    for el in d.element.body:
        if el.tag==qn('w:p'):
            p=Paragraph(el,d)
            if p.text:md.extend([('## ' if p.style.name.startswith('Heading') else '# ' if p.style.name=='Title' else '')+p.text,''])
        elif el.tag==qn('w:tbl'):
            rows=[[c.text.replace('|','/') for c in r.cells] for r in Table(el,d).rows];md.extend(['| '+' | '.join(rows[0])+' |','| '+' | '.join(['---']*len(rows[0]))+' |']+['| '+' | '.join(r)+' |' for r in rows[1:]]+[''])
    (B/('Report.zh-TW.md' if zh else 'Report.en.md')).write_text('\n'.join(md),encoding='utf-8')
    print(name)
