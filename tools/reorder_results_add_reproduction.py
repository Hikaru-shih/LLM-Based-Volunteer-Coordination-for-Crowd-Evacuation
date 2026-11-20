"""Move primary information-control evidence before exploratory analyses and add a compact audit appendix."""
from pathlib import Path
import json,os,re,shutil,hashlib
from docx import Document
from docx.shared import Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table
R=Path(__file__).resolve().parents[1];O=R/'report';B=O/'.build/reproduction_20261120';B.mkdir(parents=True,exist_ok=True)
A=R/'local_archive/20261120_before_results_reproduction';A.mkdir(parents=True,exist_ok=True)
PRE=R/'experiment_records/study_preparations/information_control_v1_20261120'
reg=json.loads((PRE/'registration.json').read_text());audit=json.loads((PRE/'PROMPT_MATCH_AUDIT.json').read_text());verify=json.loads((R/'experiment_records/data/analysis/information_control_v1_20261120/VERIFICATION.json').read_text())
cases={t['case']['information']:t['case'] for t in reg['trials'] if t['block']==1 and t['case']['scenario']=='B2_M1' and t['case']['optionOrder']=='participate_first'}
users={k:v['payload']['messages'][1]['content'] for k,v in cases.items()};common=os.path.commonprefix(list(users.values()))
assert common.endswith('Make your personal choice.')
for name in ['Report.docx','Report.zh-TW.docx','README.md','PACKAGE_COMPLETE.json','Speaker_Notes.en.md']:
    if not (A/name).exists():shutil.copy2(O/name,A/name)
def addtext(d,s,style=None):
    p=d.add_paragraph(s,style=style)
    snap=OxmlElement('w:snapToGrid');snap.set(qn('w:val'),'0');p._p.get_or_add_pPr().append(snap)
    p.paragraph_format.space_after=Pt(6)
    return p
def quoted(d,s):
    # Each paragraph is an exact contiguous piece of the archived string.
    # Original newlines remain line breaks, and leading spaces remain preserved.
    for line in s.split('\n'):
        p=addtext(d,line);p.paragraph_format.line_spacing=1.0;p.paragraph_format.space_after=Pt(2)
        if not line:p.paragraph_format.keep_with_next=True
        for run in p.runs:run.font.size=Pt(12)
for zh,name in [(False,'Report.docx'),(True,'Report.zh-TW.docx')]:
    d=Document(A/name);originaltables=[[[c.text for c in r.cells] for r in t.rows] for t in d.tables]
    def find(s):
        ps=[p for p in d.paragraphs if p.text.startswith(s)];assert len(ps)==1,s;return ps[0]
    start=find('5.6 資訊控制' if zh else '5.6 Information control')._p
    target=find('5.4 與個人' if zh else '5.4 Exploratory consistency')._p
    end=find('6 討論' if zh else '6 Discussion')._p
    nodes=[];node=start
    while node is not end:nodes.append(node);node=node.getnext()
    for node in nodes:target.addprevious(node)
    find('5.6 資訊控制' if zh else '5.6 Information control').text='5.4 資訊控制實驗結果' if zh else '5.4 Information control results'
    find('5.4 與個人' if zh else '5.4 Exploratory consistency').text='5.5 與個人預測效用的一致性探索' if zh else '5.5 Exploratory consistency with personal forecast utility'
    find('5.5 理由品質' if zh else '5.5 Non-blind author').text='5.6 理由品質的作者非盲評' if zh else '5.6 Non-blind author review of explanation quality'
    # Keep exploratory reason-quality observations with the author-review analysis.
    review=find('5.6 理由品質' if zh else '5.6 Non-blind author')
    review_first=review._p.getnext()
    for prefix in (('理由編碼中','三份預測理由') if zh else ('In the explanation coding','Three forecast explanations')):
        review_first.addprevious(find(prefix)._p)
    # Table sequence follows first appearance after the section move.
    mapping={'4':'6','5':'7','6':'4','7':'5'}
    for p in d.paragraphs:
        s=re.sub(r'Table ([4-7])\b',lambda m:'Table '+mapping[m[1]],p.text)
        s=re.sub(r'表\s*([4-7])(?!\d)',lambda m:'表'+mapping[m[1]],s)
        if s!=p.text:p.text=s
    summary=find('5.1 主要發現' if zh else '5.1 Main findings')
    Paragraph(summary._p.getnext(),d).text=(
      '報酬任務360份回覆中有345份選擇參與；從低至高成本的下降為10.83個百分點，參考公式約下降21.10點，因此Contrast A為+10.27點，描述性95%區間[5.27,15.27]。新資訊控制實驗的預測減控制差為−39.375點[−42.50,−36.25]，但參與先列與拒絕先列分別為−60.00及−18.75點。這些主要結果顯示較弱的成本反應與呈現順序敏感性；後面的效用與作者評分分析只提供輔助性解讀。' if zh else
      'The payoff task produced 345 participation choices out of 360. Participation declined by 10.83 percentage points from low to high cost, compared with about 21.10 points for the reference, giving Contrast A of +10.27 points with a descriptive 95% interval of [5.27, 15.27]. In the new information-control experiment, forecast minus control was -39.375 points [-42.50, -36.25], but the contrast was -60.00 with participate first and -18.75 with decline first. These primary findings show a weaker cost response and sensitivity to presentation order. The later utility and author-review analyses provide supporting interpretation.')
    for p in d.paragraphs:
        if 'Full matching checks are retained in the English experiment records.' in p.text:p.text=p.text.replace('Full matching checks are retained in the English experiment records.','Appendix A gives the matching method, audit counts and verbatim prompt examples.')
        if '完整配對檢查保留於英文實驗紀錄' in p.text:p.text=p.text.replace('完整配對檢查保留於英文實驗紀錄','附錄A提供配對方法、核對數據及提示原文')
    h=addtext(d,'附錄A 重現細節與提示範例' if zh else 'Appendix A Reproduction details and prompt examples','Heading 1');h.paragraph_format.page_break_before=True
    addtext(d,'A1 排程與配對檢查' if zh else 'A1 Scheduling and matching checks','Heading 2')
    addtext(d,'原研究排程種子為2026111661，完整區塊bootstrap種子為2026111662；資訊控制實驗分別為2026112001及2026112002。兩批均使用5000次完整區塊重抽樣。控制文字中的名目數字以Python random.Random產生，種子規則為2026112000+10B+M；例如B2_M1為2026112021。這些種子固定排程、控制建構及分析，不保證API輸出可逐字重現。' if zh else 'Original-study scheduling used seed 2026111661 and whole-block bootstrap used 2026111662. Information-control scheduling used 2026112001 and bootstrap used 2026112002. Both analyses used 5,000 whole-block resamples. Python random.Random generated nominal control numbers with seed 2026112000 + 10B + M (2026112021 for B2_M1). These seeds fix scheduling, control construction and analysis, not word-for-word API outputs.')
    addtext(d,'配對在收集回覆前完成，以tiktoken 0.14.0的o200k_base計算完整使用者訊息token數。控制數字保留預測數字的小數形式，但以無關名目數值取代，並加入完整的中性目錄句子，預先允許token差不超過1、字元比例0.90–1.10及詞數比例0.75–1.25。實際八個設定的token差均為0，兩組完整訊息各有41個數字項目；字元仍約多7%、詞數約多8%。數字項目以阿拉伯數字段落計數，小數視為一項，並非token數。' if zh else 'Matching preceded collection. tiktoken 0.14.0 with o200k_base counted complete user-message tokens. Controls replaced forecast numbers with unrelated nominal values of similar decimal shape and added complete neutral catalogue sentences. Prespecified tolerances were at most one proxy token, a character-count ratio of 0.90–1.10 and a lexical-word ratio of 0.75–1.25. All eight realised proxy differences were zero. Both complete message types contained 41 numeric literals, counting a decimal numeral as one item. Controls still had about 7% more characters and 8% more words.')
    addtext(d,'表A1列參與先列版本的完整使用者訊息代理token數，以及兩種順序下供應商回報的完整請求輸入token數。後者在全部16個設定與順序配對皆完全相等，未依回覆結果修改提示；這仍不等於獨立驗證供應商tokenizer或語意等價。' if zh else 'Table A1 gives proxy counts for complete user messages in the participate-first version, and provider-reported full-request input tokens for both orders. All 16 setting-order pairs matched exactly, without post-outcome prompt edits. This does not independently establish the provider tokenizer or semantic equivalence.')
    table=d.add_table(rows=1,cols=4);table.style='Table Grid'
    for c,s in zip(table.rows[0].cells,['設定','控制代理','預測代理','API兩組各'] if zh else ['Setting','Control proxy','Forecast proxy','API each group']):c.text=s
    for row in audit:
        pv=[p for p in verify['providerInputTokenPairs'] if p['scenario']==row['scenario']];assert len(pv)==2 and all(p['control']==p['forecast']==pv[0]['control'] for p in pv)
        for c,s in zip(table.add_row().cells,[row['scenario'],row['length_control']['proxyTokens'],row['forecast']['proxyTokens'],pv[0]['control'][0]]):c.text=str(s)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
    addtext(d,'A2 實際提示範例' if zh else 'A2 Verbatim prompt example','Heading 2')
    addtext(d,'以下取自鎖定的B2_M1、參與先列請求。為避免重複，只印一次共用前段；共用使用者文字後接A3中對應後段，即為各組完整使用者訊息。共用前段結尾無換行，布局與控制後段以空格開始，預測後段以換行開始。英文原文保留，排版換行不表示額外輸入。' if zh else 'These texts come from locked B2_M1, participate-first requests. The shared prefix is printed once. Concatenating it with the corresponding suffix in A3 gives each complete user message. The prefix ends without a newline. Layout/control suffixes begin with a space and the forecast suffix begins with a newline. English text is verbatim. Visual line wrapping adds no input characters.')
    addtext(d,'System message','Heading 2');quoted(d,cases['geometry_only']['payload']['messages'][0]['content'])
    addtext(d,'Shared user prefix','Heading 2');quoted(d,common)
    addtext(d,'A3 各資訊條件的後段' if zh else 'A3 Information condition suffixes','Heading 2')
    for info,label in [('geometry_only','Layout only suffix'),('calibrated_forecast','Forecast suffix'),('length_control','Matched control suffix')]:
        addtext(d,label,'Heading 2');quoted(d,users[info][len(common):])
    addtext(d,'A4 選項順序與回覆格式' if zh else 'A4 Option order and response format','Heading 2')
    addtext(d,'拒絕先列版本只進行以下兩處文字替換，其他文字、角色與預測表列序不變。模型設定為gpt-6-luna、temperature=0.15、reasoning_effort=none、max_completion_tokens=220；每試次一次嘗試，60秒逾時，首次技術失敗停止，不重試。' if zh else 'The decline-first version makes only these two text substitutions. Other text, roles and forecast row order stay fixed. Settings were gpt-6-luna, temperature 0.15, reasoning_effort none and max_completion_tokens 220. Each trial allowed one attempt with a 60-second timeout. Collection stopped at the first technical failure without retries.')
    quoted(d,'Actions are participate and decline_assistance.\nreplaced by\nActions are decline_assistance and participate.\n\ndecision must be participate or decline_assistance.\nreplaced by\ndecision must be decline_assistance or participate.')
    addtext(d,'JSON response format','Heading 2');quoted(d,json.dumps(cases['geometry_only']['payload']['response_format'],ensure_ascii=False))
    addtext(d,'本附錄的三組訊息與格式均來自已封存請求，而非依結果重寫。表格與原文足以核對這個實際配對；完整480筆請求、來源雜湊與逐次用量仍保留在專案實驗紀錄。這是本機保存資料，尚非公開資料庫。' if zh else 'The example messages and schema come from sealed requests, not a reconstruction fitted to the outcomes. The table and verbatim text support checking this actual matched example. All 480 request payloads, source hashes and per-request usage remain in project records. Those are locally preserved records, not a public dataset.')
    expected=[originaltables[i] for i in [0,1,2,5,6,3,4]]
    assert expected==[[[c.text for c in r.cells] for r in t.rows] for t in d.tables[:7]]
    for p in d.paragraphs:
        if p.style.name.startswith('Heading'):p.paragraph_format.keep_with_next=True
        if zh and p.text and not p._p.xpath('.//w:drawing'):
            # Preserve tight verbatim blocks, while retaining natural Chinese prose spacing.
            if any('\u4e00'<=ch<='\u9fff' for ch in p.text):p.paragraph_format.line_spacing=1.15
    for i,row in enumerate(table.rows):
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.keep_with_next=i<len(table.rows)-1
                p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(3)
                for run in p.runs:run.font.size=Pt(12);run.bold=i==0
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
