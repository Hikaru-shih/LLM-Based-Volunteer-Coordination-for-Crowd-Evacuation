"""Revise the English report using verified existing evidence and exact locked prompts."""
import json,shutil
from pathlib import Path
from docx import Document
from docx.shared import Pt,Cm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
R=Path(__file__).resolve().parents[1];O=R/'report';archive=R/'local_archive/20261119_report_revision';archive.mkdir(parents=True,exist_ok=True)
src=O/'Report.formal.en.docx'
for p in (src,O/'Report.docx',O/'PACKAGE_COMPLETE.json',O/'README.md',O/'source/Report.en.md'):
    dest=archive/p.name
    if p.exists() and not dest.exists():shutil.copyfile(p,dest)
d=Document(archive/src.name)
def replace(start,text):
    p=next(p for p in d.paragraphs if p.text.startswith(start));p.text=text;return p
def before(target,text,style=None):
    p=target.insert_paragraph_before(text)
    if style:p.style=style
    return p
def table_before(target,headers,rows):
    t=d.add_table(rows=1,cols=len(headers));t.style='Table Grid'
    for c,text in zip(t.rows[0].cells,headers):c.text=str(text)
    for row in rows:
        for c,text in zip(t.add_row().cells,row):c.text=str(text)
    target._p.addprevious(t._tbl)
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for i,row in enumerate(t.rows):
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(3)
                for r in p.runs:r.font.size=Pt(12);r.bold=i==0
    return t
abstract=replace('This project studies whether','This project studies how an individual large language model changes its willingness to help when assistance becomes costly or personal outcome information is supplied. I compare its choices with a volunteer-game reference from an evacuation model. The formal dataset contains 840 responses across 28 conditions, with 30 responses per condition. In the payoff task, participation fell from 100% at low relative cost to 89.17% at high cost, a smaller decline than the reference formula. In the physical task, participation was 98.33% with layout information and 26.25% with time forecasts. Both settings with all five reference exit positions blocked retained full participation. A post hoc analysis of the supplied forecast means found four settings with the same preferred personal action at both background endpoints; all 120 choices in those settings agreed with that action. The remaining settings depended on beliefs about others. The study identifies differences in cost response and information-conditioned choices in one model configuration. Reason coding is AI-assisted; human review is pending.')
p=next(p for p in d.paragraphs if p.text.startswith('The starting point'))
before(p,'LLMs offer a way to study how a verbal decision rule responds to a stated burden, uncertainty and information about others. Evacuation volunteering is a useful test because offering help may improve passage while delaying the helper. I use a controlled individual decision task so that changes in willingness can be examined without giving the LLM authority over routes or other pedestrians. The question is when its choices depart from the mathematical reference and when they agree with the personal outcome information it receives.')
target=next(p for p in d.paragraphs if p.text=='3 Reference model and task settings')
before(target,"The volunteer's dilemma provides the basic cooperation problem: one person can bear a cost to supply a collective benefit, while others may prefer to rely on someone else [5]. This project uses that structure through the evacuation model rather than treating helping as an externally rewarded action.")
before(target,"Horton explores language models as simulated economic agents whose endowments, information and preferences can be supplied in prompts [6]. Akata et al. examine LLM cooperation and coordination in repeated games [7]. These studies motivate testing decisions under explicit conditions. The present task is narrower: requests have fresh contexts and no repeated interaction or learned history. It therefore examines fixed-scenario choices rather than strategic adaptation over a game.")
for p in d.paragraphs:
    if '[1,5]' in p.text:p.text=p.text.replace('[1,5]','[1]')
    if 'locked before collection [6]' in p.text:p.text=p.text.replace('locked before collection [6]','locked before collection (project records in Appendix B)')
    if 'Both B5 settings' in p.text:pass
    if 'earlier P028 group study' in p.text:p.text=p.text.replace('earlier P028 group study','earlier group-evacuation study (archive ID P028)')
    if 'scenario-reasons-v3 codebook' in p.text:p.text=p.text.replace('scenario-reasons-v3 codebook','a fixed multi-label codebook for stated reasons and four quality judgments (version scenario-reasons-v3)')
target=next(p for p in d.paragraphs if p.text.startswith('It is also useful to separate'))
before(target,'The base symmetric mixed-strategy probability for the volunteer game is 1 - (cv/av)^(1/(X-1)). The reference used here also contains the evacuation model\'s tau/omega adjustment. It is a behavioral reference derived from the game, not simply the unadjusted mixed equilibrium of the payoff table. Repeated LLM outputs are compared with this reference without assuming that the LLM implements either strategy.')
target=next(p for p in d.paragraphs if p.text.startswith('The forecasts come from'))
before(target,'Table 1 summarises the physical configuration. B counts blocked reference positions, not the total number of movable obstacles. M changes the simulator\'s progress interval for a unit of work. It is not a human time or danger scale.')
table_before(target,['Item','Values','Meaning'],[['Pedestrians','10','One focal pedestrian plus nine others'],['Movable obstacles','5','Fixed total in this layout family'],['Blocked positions B','2, 3, 4, 5','Relevant exit reference positions blocked'],['Work interval M','1 or 4','Simulation ticks per manipulation work unit'],['Information','Geometry / forecast','Same layout; additional fixed time estimates'],['Forecast source','6 seeds','Earlier development simulations; two endpoint backgrounds']])
target=next(p for p in d.paragraphs if p.text.startswith('Two main contrasts'))
before(target,'At temperature 0.15, repeated responses may be concentrated on one action. I report empirical choice frequencies under this prompt and sampling configuration, not evidence that the model deliberately randomises according to a mixed strategy. Variation across requests can arise from response generation; its mechanism was not identified. The 100% low-cost ceiling also limits how Contrast A can distinguish a high baseline tendency to help from sensitivity to cost.')
target=next(p for p in d.paragraphs if p.text=='5 Results')
before(target,'A later exploratory analysis compares the focal pedestrian\'s mean time utility under the two actions at each supplied background endpoint. It uses the exact rounded means in the locked prompts. Let d_D and d_W be T_decline - T_participate when all other nine decline and when all are willing. Then DeltaU_D = d_D/301 and DeltaU_W = d_W/301. Positive values favour participating. These are comparisons of conditional development means, not guaranteed or seed-by-seed advantages.')
before(target,'For sensitivity analysis only, assume those two endpoints exhaust the possible backgrounds, and let q be the probability of the all-decline endpoint. Then DeltaU(q) = [q*d_D + (1-q)*d_W]/301. If the signs differ, q* = -d_W/(d_D-d_W) is the indifference threshold. This q is an assumed two-endpoint belief, not an estimated belief or a probability over uncalibrated mixed profiles. This post hoc analysis does not alter the registered primary contrasts.')
before(target,'A separate 48-response human quality-review packet was prepared after the study: 16 payoff responses, 16 geometry responses and 16 forecast responses, selected without using the AI quality labels. The packet hides those labels and asks for five judgments with evidence. Ratings are not yet available. Human-AI agreement and nominal Cohen\'s kappa will be reported by field and task after completion, with not-applicable and unclear retained as categories. The balanced sample does not estimate coding validity across all 840 responses. Prior exposure and the reviewer\'s relationship to the project will be disclosed.')
target=next(p for p in d.paragraphs if p.text=='6 Discussion')
before(target,'5.1 Exploratory consistency with personal forecast utility','Heading 2')
before(target,'Table 4 shows the mean time advantage of participating (decline time minus participate time). Dividing either time column by 301 gives the corresponding utility difference. The q* column applies only to the hypothetical two-endpoint mixture; participating is preferred below that threshold in the four sign-changing settings.')
rows=json.loads((R/'experiment_records/data/analysis/posthoc_utility_20261119/ANALYSIS.json').read_text(encoding='utf-8'))['rows']
table_before(target,['Setting','Gain D','Gain W','q*','Participate'],[[r['scenario'],f"{r['others_decline_time_gain']:.3f}",f"{r['others_willing_time_gain']:.3f}",f"{r['q_star']:.4f}" if r['q_star'] is not None else 'n/a',f"{r['forecast_participate']}/30"] for r in rows])
before(target,'B2_M1 and B4_M1 favour declining at both supplied mean endpoints, and both B5 settings favour participating at both. All 120 forecast choices in these four settings agreed with those endpoint-invariant preferences. The other four settings reverse preference across endpoints; they cannot be assigned one correct action without a belief or decision criterion. At the all-decline endpoint, 237/240 choices agree with the higher own mean utility, compared with 123/240 at the all-willing endpoint. These conditional counts are not a single accuracy score and do not show what belief the LLM used.')
before(target,'The four thresholds are approximately 0.2397, 0.0294, 0.0941 and 0.0069 for B2_M4, B3_M1, B3_M4 and B4_M4. For example, in B4_M4 participation has a 0.5-tick mean advantage if all others are willing but a 71.5-tick disadvantage if all decline. Under the restrictive two-endpoint assumption, even a small all-decline probability changes the preferred action. The small positive endpoint differences and six-seed forecasts warrant caution; no uncertainty test or general dominance claim is made.')
replace('The two tasks should not be combined','The endpoint analysis adds a more specific interpretation of the forecast choices. The model agreed with the same-direction personal mean-utility preference in four settings; in the others, actions were often compatible with placing weight on the all-decline endpoint. The experiment did not elicit beliefs or identify the decision rule, so this is a consistency description. The payoff and physical tasks remain separate: the time forecasts have not been calibrated to the original game\'s cv and av, and the data do not measure resulting group evacuation performance.')
replace('This study uses one model configuration','The largest design limitation in the physical task is that the forecast condition adds numerical content, detail and text length at the same time as decision-relevant outcome information. The observed contrast is an information-package difference, not an isolated causal effect of forecasts. A length-matched, decision-irrelevant control condition would address part of this confound, but it has not been run. This study also uses one model configuration and fixed scenarios. Thirty requests per condition give limited precision; other models, temperatures, prompts and backend versions were not tested. Request dependence and timing effects remain unresolved. Forecasts come from six development seeds; the capping and normalization are research choices rather than validated human measurements.')
replace('There are no human evacuation observations','There are no human evacuation observations or new group evacuation outcomes in this batch. The 48-response quality-review packet awaits actual human completion; all currently reported reason judgments remain assistant-generated. That review will evaluate five quality fields, not validate all reason themes or model behavior. Earlier qualification checks address specific comprehension tasks rather than every free-choice explanation.')
replace('Within those limits, the results show','The contribution is a reproducible comparison of cost response, information-conditioned choices and their agreement with supplied personal mean outcomes. The model\'s payoff response was flatter than the reference, while its physical choices depended strongly on the information package and setting. The endpoint analysis shows where personal mean-utility preferences are stable across supplied backgrounds and where beliefs are needed to interpret an action. Additional models, a prompt-length control and group outcome tests would extend these findings through separately designed studies.')
# Keep four original academic citations; replace local paths with actual related literature.
replace('[5] Project model correspondence',"[5] A. Diekmann. Volunteer's Dilemma. Journal of Conflict Resolution, 29(4), pp. 605-610, 1985. https://doi.org/10.1177/0022002785029004003")
replace('[6] P030 registration','[6] J. J. Horton. Large Language Models as Simulated Economic Agents: What Can We Learn from Homo Silicus? arXiv:2301.07543v1, 2023. https://arxiv.org/abs/2301.07543v1')
d.add_paragraph('[7] E. Akata, L. Schulz, J. Coda-Forno, S. J. Oh, M. Bethge, and E. Schulz. Playing repeated games with Large Language Models. arXiv:2305.16867v2, 2025. https://arxiv.org/abs/2305.16867v2')
p=d.add_paragraph('Appendix A Complete prompt examples','Heading 1');p.paragraph_format.page_break_before=False
d.add_paragraph('The following are verbatim system and user messages from the locked request snapshot. One example is included for each prompt type. Forecast values and uncertainty statements are retained in full. The API requested a strict JSON object with explanation and decision; the decision was restricted by post-response validation to participate or decline_assistance. The model settings are specified in Method. These examples document the measured intervention, including differences in length and numerical content.')
reg=json.loads((R/'experiment_records/data/scenario_formal_v1_20261116/registration.snapshot.json').read_text(encoding='utf-8'))
cases={t['case']['caseID']:t['case'] for t in reg['trials']}
for name in ('AC_A30_R50_numeric','AC_A30_R50_contextual_equivalent','PC_B3_M4_geometry_only','PC_B3_M4_calibrated_forecast'):
    c=cases[name];d.add_paragraph(name.replace('_',' '),'Heading 2')
    for m in c['payload']['messages']:
        d.add_paragraph(m['role'].capitalize(),'Heading 2')
        # Preserve exact content, but split original newline boundaries into paragraphs.
        for line in m['content'].split('\n'):
            if line:d.add_paragraph(line)
    d.add_paragraph('Response format schema','Heading 2')
    d.add_paragraph(json.dumps(c['payload']['response_format'],ensure_ascii=False))
d.add_paragraph('Appendix B Study records and data access','Heading 1')
d.add_paragraph('P030 is the internal archive identifier for the present 840-choice study; P028 identifies the earlier, separate group-evacuation study. The version name scenario-reasons-v3 identifies the fixed codebook for stated reason themes and quality fields. These identifiers are not additional published studies.')
d.add_paragraph('The project package retains the locked registration, exact request payloads, raw responses, assistant labels, condition summary and analysis manifests. The archive identifiers are scenario_formal_v1_20261116 for response data and its matching analysis folder. The new endpoint analysis is separately stored as posthoc_utility_20261119. Local paths identify project evidence, not public references or a public data release. Exact example prompts are reproduced in Appendix A; a public repository URL or DOI has not been assigned.')
for name in ('Normal','Heading 1','Heading 2'):d.styles[name].font.size=Pt(12 if name=='Normal' else 14)
for table in d.tables:
    for row in table.rows:
        pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
for p in d.paragraphs:
    if p.style.name.startswith('Heading'):p.paragraph_format.keep_with_next=True
    if p.text.startswith('Table 1 shows all 12'):p.text=p.text.replace('Table 1','Table 2')
    if 'Table 2 gives the full counts' in p.text:p.text=p.text.replace('Table 2 gives','Table 3 gives')
dest=O/'Report.formal.en.docx';d.save(dest)
# Serialize editable research text, including all new tables, in document order.
from docx.text.paragraph import Paragraph
from docx.table import Table
md=[]
for el in d.element.body:
    if el.tag==qn('w:p'):
        p=Paragraph(el,d);text=p.text
        if text:md+= [('## ' if p.style.name.startswith('Heading') else '# ' if p.style.name=='Title' else '')+text,'']
    elif el.tag==qn('w:tbl'):
        t=Table(el,d);rr=[[c.text.replace('|','/') for c in r.cells] for r in t.rows]
        md+=['| '+' | '.join(rr[0])+' |','| '+' | '.join(['---']*len(rr[0]))+' |']+['| '+' | '.join(r)+' |' for r in rr[1:]]+['']
(O/'source/Report.en.md').write_text('\n'.join(md),encoding='utf-8')
print('Revised English report; 7 academic references; 4 exact prompt examples; human ratings pending.')
