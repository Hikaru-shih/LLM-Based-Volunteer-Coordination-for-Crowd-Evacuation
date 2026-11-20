from pathlib import Path
import shutil
from docx import Document
R=Path(__file__).resolve().parents[1];O=R/'report';A=R/'local_archive/20261120_before_neutral_cost_wording';B=O/'.build/neutral_cost_20261120'
A.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
changes={
 'Report.docx':[
 ('These primary findings show a weaker cost response and sensitivity to presentation order.','These primary findings show a smaller participation decline than the reference and sensitivity to presentation order.'),
 ('Near-universal participation at low cost means the flatter decline can reflect both a high baseline tendency to help and cost sensitivity.','Near-universal participation at low cost means the smaller decline can reflect a high baseline tendency to help as well as cost sensitivity. This design does not separate their contributions.'),
 ('The model showed a flatter cost response than the adjusted game reference,','The observed participation decline from low to high cost was smaller than the adjusted game reference,')],
 'Report.zh-TW.docx':[
 ('這些主要結果顯示較弱的成本反應與呈現順序敏感性','這些主要結果顯示參與率下降幅度小於參考公式，且選擇對呈現順序敏感'),
 ('模型在低成本時已接近全數參與，因此較平緩的下降同時反映基準傾向與成本敏感度。','模型在低成本時已接近全數參與，因此較小的下降幅度可能受高基準協助傾向與成本敏感度影響，本設計無法分離兩者的貢獻。'),
 ('本研究發現，LLM成本反應較調整賽局參考平緩','本研究觀察到，LLM從低至高成本的參與率下降幅度小於調整賽局參考')]}
for name,replacements in changes.items():
    if not (A/name).exists():shutil.copy2(O/name,A/name)
    d=Document(A/name)
    for old,new in replacements:
        ps=[p for p in d.paragraphs if old in p.text];assert len(ps)==1,old
        ps[0].text=ps[0].text.replace(old,new)
    assert not any('weaker cost response' in p.text or 'flatter cost response' in p.text or '較弱的成本反應' in p.text for p in d.paragraphs)
    d.save(B/name)
    print(name)
