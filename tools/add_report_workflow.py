"""Add a source-checked workflow diagram without changing existing research text."""
from pathlib import Path
import shutil,json
from PIL import Image,ImageDraw,ImageFont
from docx import Document
from docx.shared import Inches,Pt
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'report'
archive=ROOT/'local_archive/20261119_workflow';archive.mkdir(parents=True,exist_ok=True)
src=out/'Report.formal.en.docx';backup=archive/src.name
if not backup.exists():shutil.copyfile(src,backup)
d=Document(backup)
assets=out/'assets';assets.mkdir(exist_ok=True)
im=Image.new('RGB',(1800,2040),'white');draw=ImageDraw.Draw(im)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',32)
bold=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',34)
def box(rect,title,lines,fill='#f1f4f6'):
    draw.rounded_rectangle(rect,radius=15,fill=fill,outline='#354755',width=3)
    x0,y0,x1,y1=rect; y=y0+24
    for text,f in [(title,bold)]+[(line,font) for line in lines]:
        bb=draw.textbbox((0,0),text,font=f);draw.text(((x0+x1-bb[2])/2,y),text,font=f,fill='#101820');y+=45
def arrow(a,b):
    draw.line([a,b],fill='#354755',width=4)
    import math
    ang=math.atan2(b[1]-a[1],b[0]-a[0]);size=17
    pts=[b,(b[0]-size*math.cos(ang-.5),b[1]-size*math.sin(ang-.5)),(b[0]-size*math.cos(ang+.5),b[1]-size*math.sin(ang+.5))]
    draw.polygon(pts,fill='#354755')
box((340,10,1460,155),'Lock conditions and request schedule',['28 conditions x 30 blocks = 840 requests'])
arrow((900,155),(900,195));draw.line([(450,195),(1350,195)],fill='#354755',width=4)
arrow((450,195),(450,235));arrow((1350,195),(1350,235))
box((35,235,865,455),'A  Payoff task',['12 conditions: cost, loss and wording','Original volunteer-game payoff rules','No additional reward for helping'])
box((935,235,1765,455),'B  Physical-information task',['16 conditions: B2-B5, M1/M4','Geometry alone or with fixed forecasts','Forecasts from 6 development seeds'])
arrow((450,455),(450,505));arrow((1350,455),(1350,505))
box((35,505,865,685),'Calculate reference separately',['Compute p_ref from X, tau, omega, cv/av','Do not give p_ref to the LLM'],fill='#e8eef4')
box((935,505,1765,685),'Prepare physical observations',['Own and others\' estimated exit times','No conversion of time into cv or av'],fill='#e8eef4')
arrow((450,685),(450,735));arrow((1350,685),(1350,735));draw.line([(450,735),(1350,735)],fill='#354755',width=4);arrow((900,735),(900,780))
box((240,780,1560,1010),'One LLM request represents one pedestrian',['Fresh context; only that pedestrian\'s willingness is decided','Return explanation + participate / decline_assistance','No route planning, assignment of others or movement control'])
arrow((900,1010),(900,1060))
box((240,1060,1560,1240),'Validate and preserve the response',['Check response format, action and transport integrity','Technical failure: stop campaign; retain partial records'])
arrow((900,1240),(900,1290))
box((240,1290,1560,1470),'Record every valid choice and explanation',['Retain weak or incorrect explanations in the dataset','Continue the locked schedule until all 840 trials finish'])
arrow((900,1470),(900,1520))
box((35,1520,865,1740),'A  Compare cost responses',['LLM participation versus p_ref','Primary contrast A: difference in','high-minus-low cost changes'])
box((935,1520,1765,1740),'B  Compare information conditions',['Forecast versus geometry participation','Primary contrast B: mean difference','across the 8 physical settings'])
arrow((450,1740),(450,1785));arrow((1350,1740),(1350,1785));draw.line([(450,1785),(1350,1785)],fill='#354755',width=4);arrow((900,1785),(900,1825))
box((180,1825,1620,2025),'Interpret choices and stated reasons',['Whole-block descriptive bootstrap; AI-assisted reason coding','Formal observations are API choices, not new Unity evacuation runs'])
image=assets/'model_workflow.en.png';im.save(image,dpi=(300,300))
target=next(p for p in d.paragraphs if p.text=='4 Method')
p=target.insert_paragraph_before('Model decision workflow');p.style='Heading 2';p.paragraph_format.page_break_before=True
p=target.insert_paragraph_before();p.paragraph_format.space_after=Pt(6);p.paragraph_format.keep_with_next=True
p.add_run().add_picture(str(image),width=Inches(6.15))
cap=target.insert_paragraph_before('Figure 1. Decision workflow for the formal study. The payoff comparison and physical-information comparison are analysed separately. The LLM makes an individual willingness choice; the simulator remains responsible for activation and movement.')
cap.paragraph_format.keep_with_next=False
target.paragraph_format.page_break_before=True
for p in d.paragraphs:
    if p.text.startswith('Figure 1. Participation across payoff'):
        for r in p.runs:r.text=r.text.replace('Figure 1.','Figure 2.',1)
dest=out/'Report.formal.en.docx';d.save(dest)
assert len(d.inline_shapes)==2
old=[p.text for p in Document(backup).paragraphs if p.text.strip()]
new=[p.text.replace('Figure 2. Participation','Figure 1. Participation') for p in d.paragraphs if p.text.strip() and not p.text.startswith(('Model decision workflow','Figure 1. Decision workflow'))]
assert old==new
print(json.dumps({'output':str(dest),'existingParagraphsPreserved':True,'figures':2}))

