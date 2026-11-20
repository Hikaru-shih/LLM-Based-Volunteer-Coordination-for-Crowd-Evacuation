"""Complete own-action counterfactual while holding other agents willing; no API."""
from pathlib import Path
import json,hashlib,shutil,sys
sys.path.insert(0,str(Path(__file__).parent))
from closed_loop_study import ROOT,source_sha
project=ROOT/'tmp/closed-loop-runtime-b'
oldreg=ROOT/'experiment_records/study_preparations/scenario_physical_v2_20261116_r3'
reg=ROOT/'experiment_records/study_preparations/scenario_physical_v2_20261116_r4'
out=ROOT/'experiment_records/data/scenario_physical_v2_20261116_r4'
assert not out.exists() and not reg.exists() and not (project/'Temp/UnityLockfile').exists()
assert (ROOT/'experiment_records/data/scenario_physical_v2_20261116_r3/COMPLETE.json').exists()
for name in ['Core/PaperModelEngine.cs','Core/ClosedLoopInitialState.cs','Editor/ScenarioPhysicalCalibration.cs']:
    assert (project/'Assets/scripts'/name).read_bytes()==(oldreg/Path(name).name).read_bytes()
shutil.copyfile(ROOT/'tools/ScenarioPhysicalCalibration.cs',project/'Assets/scripts/Editor/ScenarioPhysicalCalibration.cs')
reg.mkdir(parents=True)
p=json.loads((oldreg/'plan.json').read_text(encoding='utf-8'))
p['jobs']=[dict(id=f'B{b}_M{m}_OthersHelp_s{s}',seed=s,blocked=b,policy='OthersHelp',manipulationSteps=m) for s in range(71001,71007) for b in [2,3,4,5] for m in [1,4]]
p.update(purpose='Complete own-action counterfactual holding others willing; development only',counterfactual='Pair new OthersHelp with existing AllHelp on same seed/layout/work; focal ID0 declines vs participates, everyone else willing. Pair Focal0/None holds others declining. No hand-picked focal or favorable cells.',baseSourceSHA=source_sha())
p['sourceFiles']={str(f.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in [ROOT/'tools/ScenarioPhysicalCalibration.cs',ROOT/'tools/prepare_scenario_counterfactual.py']}
(reg/'plan.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ['Core/PaperModelEngine.cs','Core/ClosedLoopInitialState.cs','Editor/ScenarioPhysicalCalibration.cs']:shutil.copyfile(project/'Assets/scripts'/name,reg/Path(name).name)
(reg/'source-binding.json').write_text(json.dumps(dict(baseProductionSHA=source_sha(),instrumentedProjectSHA=source_sha(project),instrumentation='Same r3 movement/geometry and observer; additional controlled OthersHelp callback only'),indent=2)+'\n')
print('Registered48 OthersHelp physical controls. No API.')
