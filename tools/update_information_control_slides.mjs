import fs from 'node:fs/promises';
const root='D:/LLM-Based-Volunteer-Coordination-for-Crowd-Evacuation';
export async function updateDeck({presentation}) {
  if(presentation.slides.items.length!==13)throw Error('Expected historical 13-slide deck');
  const set=(id,text)=>{presentation.resolve(id).text=text;};
  set('sh/rm1ozm98','Original study: 840 choices across 28 conditions\nFollow-up: 480 new choices with matched control and option order');
  set('sh/snap8rqt','Advisor: Sai-Keung Wong     20 November 2026');
  set('sh/83ydkjix','Physical task: how do supplied forecasts change willingness relative to layout alone and matched unrelated information?');
  set('sh/fm50zqt0','Separate comparisons after collection\nPayoff choices vs p_ref, physical information conditions and option order\nOriginal 840 and follow-up 480 choices remain separate datasets');
  set('sh/xkfel43e','Original study: 840 API choices');
  set('sh/7ap4vadc','Original physical-task results');
  set('sh/7ehgbyls','Original descriptive contrasts');
  set('sh/rqxg3ytk','The matched control also reduced participation. Forecast participation remained 39.38 points lower than control in the new batch.');
  set('sh/4n6h83at','Option order changed the forecast-control difference: -60.00 points with participate first and -18.75 with decline first.');
  set('sh/pofy18be','Scope: one model at temperature 0.15, one control topic and six forecast seeds. Human realism and group efficiency remain untested.');
  presentation.slides.getItem(0).speakerNotes.text='The original study collected 840 fresh API choices. A separately locked follow-up collected 480 new choices. These datasets are analysed separately, never pooled. Both use gpt-6-luna at temperature 0.15. Advisor: Sai-Keung Wong. The 48-response author review applies only to the original study and followed access to AI examples.';
  presentation.slides.getItem(11).speakerNotes.text='The follow-up addresses the bundled-information concern with one matched administrative control, and counterbalances two instruction-level action enumerations. Its forecast-minus-control difference is -39.375 percentage points, descriptive 95% interval [-42.50,-36.25]. Control minus geometry is -15.625 points [-21.875,-10.625]. Strong order dependence limits any presentation-invariant interpretation. This does not identify a pure text-length or internal mechanism effect. Reason coding remains exploratory and non-blind. No human benchmark, second model, temperature test or new Unity outcomes were added. Source: P031 RESULTS.json and VERIFICATION.json.';
  presentation.slides.getItem(12).speakerNotes.text='Bibliographic references remain unchanged from the original report. P030 and P031 registrations, raw responses and analyses are local research evidence, not academic publications. Full follow-up methods and results are in the separate English information-control report. The main report remains the P030 edition.';
  function text(s,name,value,top,height=100,size=29){const sh=s.shapes.add({geometry:'textbox',name,position:{left:72,top,width:1120,height},fill:'none',line:{fill:'none',width:0}});sh.text=value;sh.text.style={fontSize:size,typeface:'Arial',color:'#172B3A'};return sh;}
  function slide(title,index){const s=presentation.slides.add();s.background.fill='#FAFBFC';text(s,'title',title,45,90,38).text.style={bold:true};s.moveTo(index);return s;}
  const a=slide('Follow-up design: matched information control',11);
  text(a,'factorial','8 physical settings × 3 information conditions\n× 2 instruction option orders × 10 repeats = 480 choices',160,120);
  text(a,'matching','Control: unrelated printed catalogue records. Control and forecast matched proxy input tokens and 41 numeric literals.',310,120);
  text(a,'execution','Same model and temperature. Ten randomized complete blocks.\n480 valid replies, no retries. No new Unity runs.',460,120);
  a.speakerNotes.text='P031 was locked after observing P030 but before any new P031 response. Geometry-only, length_control and calibrated_forecast each have 160 replies. Participate-first and decline-first each have 80 replies per information group. The control preserves geometry and adds administrative catalogue records unrelated to actions and outcomes. Whole user-message proxy token counts match using o200k_base. Actual provider input-token sets also match in all 16 setting-order pairs. All 41 numeric literals match in count. Control character and word counts are about 7–8% greater. One control topic leaves semantic, attention and format differences. Requested and returned model gpt-6-luna, temperature .15, reasoning none, 220 output tokens maximum. 480 distinct provider IDs, HTTP 200, zero retries. Prior and new datasets remain separate. Source: P031 design.json, RESULTS.json, VERIFICATION.json.';
  function chart(s,series,legend=false){s.charts.add('bar',{position:{left:90,top:155,width:1100,height:350},categories:['Geometry','Matched control','Forecast'],series,barOptions:{direction:'column',grouping:'clustered'},hasLegend:legend,legend:{position:'bottom'},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.00"%"'},yAxis:{minimumScale:0,maximumScale:100,numberFormatCode:'0"%"',majorGridlines:{fill:'#DAE1E6',width:1}},chartFill:'#FAFBFC',plotAreaFill:'#FAFBFC'});}
  const b=slide('Forecast participation remained below control',12);
  chart(b,[{name:'Participation',values:[88.125,72.5,33.125],fill:'#447C96'}]);
  text(b,'counts','Geometry 141/160     Control 116/160     Forecast 53/160',525,55,27);
  text(b,'contrast','Forecast minus control: -39.38 percentage points [-42.50, -36.25]\nControl minus geometry: -15.63 points [-21.88, -10.62]',590,66,24);
  b.speakerNotes.text='Concurrent P031 comparisons only. Geometry is 141/160 (88.125%), control 116/160 (72.5%) and forecast 53/160 (33.125%). Forecast minus geometry is -55.00 points, interval [-59.375,-50.625]. The matched control itself differs from geometry. The forecast-control difference remains, but one control cannot isolate length, numeric detail or attention mechanisms. Intervals use 5000 bootstrap resamples of ten whole scheduling blocks, seed 2026112002. Pointwise descriptive intervals, not confirmatory tests or simultaneous coverage. No historical pooling. Counts and source: experiment_records/data/analysis/information_control_v1_20261120/RESULTS.json.';
  const c=slide('Option order changed the size of the difference',13);
  chart(c,[{name:'Participate first',values:[98.75,91.25,31.25],fill:'#447C96'},{name:'Decline first',values:[77.5,53.75,35],fill:'#CE8A35'}],true);
  text(c,'order-counts','Each bar: 80 choices. Forecast minus control: -60.00 vs -18.75 points.',530,65,27);
  text(c,'boundary','Only instruction option order changed. Forecast row order and action names stayed fixed, leaving semantic response bias unresolved.',605,60,24);
  c.speakerNotes.text='Participate-first counts are geometry 79/80, control 73/80, forecast 25/80. Decline-first counts are 62/80, 43/80, 28/80. Decline-first minus participate-first differences are -21.25, -37.50, +3.75 percentage points respectively. Forecast-control differences are -60.00 and -18.75 points, giving an order interaction of +41.25 points [32.50,50.00]. Only two explicit instruction action enumerations reverse. Forecast table row order and action names remain fixed. This is not a complete counterbalance of social desirability, semantic labels or compliance. Ten observations per full cell and ten blocks limit stability. Source: P031 TRIALS.csv and RESULTS.json.';
  // Preserve each original footer and update its position number after insertion.
  for(let i=0;i<presentation.slides.items.length;i++){
    const s=presentation.slides.getItem(i);
    const footer=s.shapes.items.find(sh=>sh.position.top===672);
    const label=(i>=11&&i<=13)?'P031 follow-up':(i===0||i===14||i===15?'P030 and P031':'P030 original study');
    if(footer)footer.text=label+'    '+(i+1);
    else {const f=text(s,'footer',label+'    '+(i+1),672,26,16);f.text.style={color:'#607281'};}
  }
  await presentation.render();
  return {slides:presentation.slides.items.length,newCharts:2,separateBatches:true};
}
