import fs from 'node:fs/promises';
const cfg=JSON.parse(await fs.readFile('D:/LLM-Based-Volunteer-Coordination-for-Crowd-Evacuation/report/.build/delivery_20261119/slide_updates.json','utf8'));
export async function updateDeck({presentation}) {
  for (const u of cfg.updates) {
    const shape=presentation.resolve(u.id);shape.text=u.text;
    if(u.size)shape.text.style={fontSize:u.size,typeface:'Arial',color:'#172B3A'};
    if(u.position)shape.position=u.position;
  }
  for(let i=0;i<13;i++)presentation.slides.getItem(i).speakerNotes.text=cfg.notes[i];
  for(const id of cfg.workflowDeleteIDs)presentation.resolve(id).delete();
  const s=presentation.slides.getItem(2);
  function box(name,text,left,top,width,height) {
    const sh=s.shapes.add({geometry:'roundRect',name,position:{left,top,width,height},fill:'#E8EFF4',line:{fill:'#607281',width:1}});
    sh.text=text;sh.text.style={fontSize:27,typeface:'Arial',color:'#172B3A',alignment:'center'};
  }
  box('workflow-input','Locked inputs\nPayoff rules or physical\nlayout / fixed forecasts',65,185,330,165);
  box('workflow-llm','One fresh LLM request\nOne pedestrian chooses\nparticipate or decline',480,185,330,165);
  box('workflow-record','Validate and record\nAction + explanation\nTechnical failure: stop',895,185,320,165);
  for(const left of [415,830])s.shapes.add({geometry:'rightArrow',name:'workflow-arrow',position:{left,top:247,width:45,height:35},fill:'#607281',line:{fill:'none',width:0}});
  s.shapes.add({geometry:'downArrow',name:'workflow-down',position:{left:1035,top:370,width:35,height:45},fill:'#607281',line:{fill:'none',width:0}});
  box('workflow-analysis','Separate comparisons after collection\nPayoff choices vs separately calculated p_ref; forecast vs geometry choices\n840 valid choices retained; simulator activation and movement are separate',110,450,1060,150);
  await presentation.render();
  return {slides:13,changes:cfg.updates.length,notesUpdated:13,workflowEditable:true};
}
