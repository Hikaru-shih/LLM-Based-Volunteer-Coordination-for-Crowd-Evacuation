from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];B=R/'report/.build/delivery_20261119';src=[json.loads(x) for x in (B/'source-slides/inspect.ndjson').read_text(encoding='utf-8').splitlines()]
groups=[]
for x in src:
    if x.get('position',{}).get('top')==45:groups.append([])
    groups[-1].append(x)
assert len(groups)==13
updates=[]
def settext(old,new,size=None,position=None):
    match=[x for x in src if x.get('text','').startswith(old)];assert len(match)==1,old
    updates.append({'id':match[0]['id'],'text':new,'size':size,'position':position})
settext('840 fresh choices','840 fresh choices across 28 conditions\n48 responses reviewed by the author after AI-label access')
settext('Research report · 17','Advisor: Sai-Keung Wong  |  19 November 2026')
settext('Abstract utility task:','Payoff task: how does the LLM cost response differ from the adjusted volunteer-game reference?')
settext('Physical extension:','Physical task: how do information conditions change choices, and when do those choices agree with supplied personal mean outcomes?')
settext('Related work and study positioning','How one personal decision is produced')
settext('Participate: utility','Participate: utility 1 - cv. Decline: 1 if another person participates; otherwise 1 - av. No extra reward for helping.')
settext('0 < cv < av < 1.','Adjusted reference: p_ref = 1 - (1 - exp(-omega*tau))^(1/X) * (cv/av)^(1/(X-1)). This differs from the base mixed equilibrium.',27)
settext('Unknown beliefs about others','API choice frequencies at temperature 0.15 are not evidence of deliberate mixed-strategy play. Unknown beliefs prevent a unique best action.')
settext('Stated reasons require cautious interpretation','Personal mean outcomes help interpret choices')
settext('Geometry-only: 199/240','Post hoc analysis: B2_M1 and B4_M1 favour declining at both supplied mean endpoints; B5_M1 and B5_M4 favour participating.')
settext('One explicit population misread','All 120 choices in those four settings agree with the endpoint-invariant preference. The other four settings reverse preference across endpoints.')
settext('All 840 reasons were assistant-reviewed.','Assuming only two endpoints: q* = 0.2397, 0.0294, 0.0941, 0.0069. These are belief-sensitivity thresholds, not estimated beliefs.',27)
settext('What the findings support','Author review shows field-dependent agreement')
settext('The LLM showed a weaker cost decline','Reason insufficient        45/48 (93.75%)   kappa .854\nAction-reason relation    41/48 (85.42%)   kappa .580\nComparison judgment    32/48 (66.67%)   kappa .400\nUnsupported information 47/48 (97.92%)   kappa .000\nArithmetic judgment      48/48 (100%)      undefined',27,{'left':72,'top':165,'width':1130,'height':260})
settext('Choices varied across physical settings','27 field differences across 25 responses: 16 comparison, 7 action-reason, 3 insufficient-reason, 1 unsupported-information.',25,{'left':72,'top':442,'width':1120,'height':90})
settext('Forecast content, numerical detail','48-response author review after AI-label access; not independent blind validation. Arithmetic was not applicable throughout.',25,{'left':72,'top':550,'width':1120,'height':85})
settext('A traceable comparison','Contribution: a weaker cost decline, a large information-condition difference, and a conditional personal-utility interpretation.')
settext('Single model, fixed scenarios','Main limitations: one model configuration; forecast content, detail and prompt length changed together; only six development seeds.')
settext('Scope: the sealed P030 evidence.','No human-behavior benchmark or new group-efficiency test. Author coding review is non-blind; the reference is not a global optimum.')
# Seven concise references in five existing text boxes, with full citations in notes/report.
refs=[
'[1] Lin & Wong (2018). Evacuation simulation with obstacle removal and game theory. Physical Review E 97, 062303. doi:10.1103/PhysRevE.97.062303',
'[2] Park et al. (2023). Generative Agents. arXiv:2304.03442v2.\n[3] Aher et al. (2023). Simulating multiple humans. ICML, PMLR 202:337-371.',
'[4] Turpin et al. (2023). Unfaithful explanations in chain-of-thought prompting. arXiv:2305.04388v2. NeurIPS 2023.',
"[5] Diekmann (1985). Volunteer's Dilemma. Journal of Conflict Resolution 29(4):605-610. doi:10.1177/0022002785029004003",
'[6] Horton (2023). Homo Silicus. arXiv:2301.07543v1.\n[7] Akata et al. (2025). Playing repeated games with LLMs. arXiv:2305.16867v2.'
]
for old,new in zip([x['text'] for x in groups[12][2:]],refs):settext(old,new,22)
notes=[
"I study one pedestrian's willingness, not a global evacuation controller. The dataset has 840 API choices. Advisor: Sai-Keung Wong. The new author review was completed after AI-example access; it is disclosed non-blind quality review.",
"The questions concern cost response and information-conditioned individual choices. The later endpoint analysis asks where higher own conditional mean utility has the same sign across supplied backgrounds. It is post hoc and separate from the registered contrasts. Related work: Lin and Wong (2018); Diekmann (1985); Horton arXiv:2301.07543v1; Akata arXiv:2305.16867v2; Park, Aher and Turpin as cited in the report.",
"Each request has a fresh context and controls only willingness. Payoff inputs yield both a separate reference calculation and the LLM prompt. Physical forecasts are fixed from six earlier development seeds. Technical failure stops collection; valid weak reasons are retained. The formal batch measured API choices, not new Unity outcomes. Sources: locked registration.snapshot.json, scenario_agent_contract.py, scenario_formal.py; report Figure 1.",
"Payoffs use 0<cv<av<1 and no participation bonus. The base symmetric equilibrium is 1-(cv/av)^(1/(X-1)); the evacuation reference contains an additional tau/omega adjustment. q*av-cv is the action utility difference if q is the chance all others decline. q is not supplied in free-choice prompts. Reference: Lin & Wong, doi:10.1103/PhysRevE.97.062303; Diekmann, doi:10.1177/0022002785029004003.",
"There are 12 payoff and 16 physical conditions, each repeated 30 times in randomized scheduling blocks. Model gpt-6-luna, temperature .15, reasoning none, maximum 220 tokens. One attempt per trial, no retries. 208 pilot replies and 174 development physical runs remain separate. API frequency is not mixed-strategy intent; low-cost participation has a ceiling.",
"B counts blocked reference positions near the relevant exit, not all obstacles or all possible routes. M is ticks per work unit, not seconds, weight or risk. Fixed forecasts use six development seeds, capped at 300 ticks. The endpoints are all other nine declining or all willing; mixed profiles and endpoint probabilities are unknown. Willingness does not guarantee handling.",
"All plotted data match the 12 sealed payoff cells. Across loss scales and wordings, participation is 120/120, 118/120, 107/120 for low, medium and high cost. LLM decline is 10.83 percentage points; the reference decline is about 21.10 points. Lines only connect tested beta values. Source: CELL_SUMMARY.csv.",
"Geometry participation is 236/240 and forecast participation 63/240. In B2-B4 forecast participation is only 3/180, whereas both B5 settings have 30/30. The information package changes text length, detail and numerical content together, so the result is not an isolated forecast effect. Source: CELL_SUMMARY.csv.",
"Contrast A is +10.27 percentage points, descriptive 95% interval [5.27,15.27]; B is -72.08 points [-74.17,-69.58]. Intervals use 5,000 whole scheduling-block bootstrap resamples, seed 2026111662. These are pointwise descriptive intervals under conditional assumptions, not confirmatory tests, proof of independent requests or simultaneous coverage. Source: primary-results.json.",
"For each endpoint, time gain d=Tdecline-Tparticipate and utility gain d/301. All 120 choices in the four endpoint-invariant settings agree. At the two separate endpoints, agreement counts are 237/240 and 123/240; do not pool as a single accuracy rate. Four sign-changing settings are B2_M4, B3_M1, B3_M4, B4_M4. Under the restrictive two-endpoint mixture, participation is favoured below q*. Beliefs were not elicited, mixed backgrounds not calibrated, and tiny 0.5-tick advantages are not robust dominance. Source: posthoc_utility_20261119/ANALYSIS.json.",
"The author personally completed 48 sampled responses and had prior access to the AI-filled demonstration and Chinese reading translations. This is not independent blind validation. Agreement is descriptive. The 27 field differences span 25 distinct responses and were not adjudicated. Unsupported-information assistant margins are all none; arithmetic margins are all not_applicable, making kappa undefined. The original assistant dataset is unchanged. Sources: human_review_return_20261119/AGREEMENT.json and DISAGREEMENT_TAXONOMY.json. All 840 original reasons are assistant coded; 199/240 geometry explanations were conservatively insufficient. Three unclear endpoint comparisons, six unclear B5 rule applications and one population misread remain in the data.",
"The contribution is a source-checkable comparison under controlled stated conditions, not proof of LLM superiority or human realism. The strongest limits are the bundled information manipulation and single-model scope. A second model and length-matched control are future work, not completed experiments. Individual willingness is not group evacuation efficiency.",
"Complete version-specific bibliographic entries and the four verbatim prompt examples appear in the report. References [5]-[7] were checked against publisher/arXiv metadata on 19 November 2026. Local registration and analysis artifacts are project evidence, not academic publications or a public release. No new experiment was conducted for this writing revision."
]
(B/'slide_updates.json').write_text(json.dumps({'updates':updates,'workflowDeleteIDs':[x['id'] for x in groups[2][2:]],'notes':notes},indent=2)+'\n',encoding='utf-8')
(R/'report/Speaker_Notes.en.md').write_text('# English presentation notes\n\n'+''.join(f'## Slide {i+1}\n\n{n}\n\n' for i,n in enumerate(notes)),encoding='utf-8')
print('Prepared 13-slide synchronization and matching English speaking notes.')
