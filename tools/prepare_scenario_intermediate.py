"""Systematic intermediate geometry coverage after the first physical calibration; no API."""
from pathlib import Path
import json,hashlib,shutil,sys
sys.path.insert(0,str(Path(__file__).parent))
from closed_loop_study import ROOT,source_sha

target=ROOT/'tmp/closed-loop-runtime-b'
oldreg=ROOT/'experiment_records/study_preparations/scenario_physical_v2_20261116_r2'
reg=ROOT/'experiment_records/study_preparations/scenario_physical_v2_20261116_r3'
out=ROOT/'experiment_records/data/scenario_physical_v2_20261116_r3'
assert not out.exists() and not reg.exists()
assert (ROOT/'experiment_records/data/scenario_physical_v2_20261116_r2/COMPLETE.json').exists()
assert not (target/'Temp/UnityLockfile').exists(),'Isolated editor must finish shutdown'
previous=target/'Assets/scripts/Editor/ScenarioPhysicalCalibration.cs'
assert previous.read_bytes()==(oldreg/'ScenarioPhysicalCalibration.cs').read_bytes()
previous.unlink()
base=source_sha()
for f in (ROOT/'Assets/scripts').rglob('*.cs'):shutil.copyfile(f,target/f.relative_to(ROOT))
assert source_sha(target)==base
engine=target/'Assets/scripts/Core/PaperModelEngine.cs';text=engine.read_text(encoding='utf-8-sig')
needle='agent.desiredPos=SampleEvacuee(agent,field,occupied); continue;';assert text.count(needle)==1
text=text.replace(needle,'CalibrationApproachObserver?.Invoke(agent.AgentID); '+needle)
text=text.replace('public sealed class PaperModelEngine\n{','public sealed class PaperModelEngine\n{\n    public static System.Action<int> CalibrationApproachObserver;')
engine.write_text(text,encoding='utf-8')
geometry=target/'Assets/scripts/Core/ClosedLoopInitialState.cs';text=geometry.read_text(encoding='utf-8-sig')
old='(blocked!=0 && blocked!=2 && blocked!=5)';assert text.count(old)==1
text=text.replace(old,'(blocked<0 || blocked>5 || blocked==1)')
needle='if(blocked==5)for(int x=8;x<=12;x++)obstacles.Add(new Vector2Int(x,1));';assert text.count(needle)==1
text=text.replace(needle,'if(blocked==3)for(int x=9;x<=11;x++)obstacles.Add(new Vector2Int(x,1));\n        if(blocked==4)for(int x=8;x<=11;x++)obstacles.Add(new Vector2Int(x,1));\n        '+needle)
geometry.write_text(text,encoding='utf-8')
runner=target/'Assets/scripts/Editor/ScenarioPhysicalCalibration.cs';shutil.copyfile(ROOT/'tools/ScenarioPhysicalCalibration.cs',runner)
jobs=[]
for seed in range(71001,71007):
    for blocked in [3,4]:
        jobs.append(dict(id=f'B{blocked}_None_s{seed}',seed=seed,blocked=blocked,policy='None',manipulationSteps=1))
        for work in [1,4]:
            for policy in ['Focal0','AllHelp']:jobs.append(dict(id=f'B{blocked}_M{work}_{policy}_s{seed}',seed=seed,blocked=blocked,policy=policy,manipulationSteps=work))
assert len(jobs)==60
reg.mkdir(parents=True)
plan=json.loads((oldreg/'plan.json').read_text(encoding='utf-8'));plan.update(jobs=jobs,purpose='Complete intermediate geometry span B3/B4 after first development calibration, not formal selection',baseSourceSHA=base,geometryExtension='Isolated Build supports3,4; B3 x9..11 and B4 x8..11 at y1, mirror by seed parity; total5 unchanged. Open/B2/B5 generator unchanged.',selectionRule='Include BOTH intermediate blockage counts, all seeds and policies regardless of benefit signs; not a prospectively registered formal hypothesis test.',openControls='Reuse same-seed B0 None raw baseline from completed r2; no duplication or new independent sample claim')
plan['sourceFiles']={str(f.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in [ROOT/'tools/ScenarioPhysicalCalibration.cs',ROOT/'tools/prepare_scenario_intermediate.py']}
(reg/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for f in [engine,geometry,runner]:shutil.copyfile(f,reg/f.name)
(reg/'source-binding.json').write_text(json.dumps(dict(baseProductionSHA=base,instrumentedProjectSHA=source_sha(target),instrumentation='Same approach observer, isolated callback intervention, systematic B3/B4 geometry extension; production unchanged'),indent=2)+'\n')
assert source_sha()==base
print('Prepared60 intermediate zero-API calibration runs, separate r3 registration.')
