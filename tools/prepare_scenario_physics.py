"""Prepare a registered, zero-API calibration in an existing idle isolated Unity copy."""
from pathlib import Path
import hashlib,json,shutil,sys
sys.path.insert(0,str(Path(__file__).parent))
from closed_loop_study import ROOT,source_sha

target=ROOT/'tmp/closed-loop-runtime-b'
out=ROOT/'experiment_records/data/scenario_physical_v2_20261116_r2'
assert target.resolve().is_relative_to((ROOT/'tmp').resolve())
assert not (target/'Temp/UnityLockfile').exists(),'Isolated editor is open'
assert not out.exists(),'Preserve any existing calibration'
reg=ROOT/'experiment_records/study_preparations/scenario_physical_v2_20261116_r2'
assert not (reg/'plan.json').exists(),'Preserve prior registration'
reg.mkdir(parents=True,exist_ok=True)
previous=target/'Assets/scripts/Editor/ScenarioPhysicalCalibration.cs'
if previous.exists():
    old=ROOT/'experiment_records/study_preparations/scenario_physical_v2_20261116/ScenarioPhysicalCalibration.cs'
    assert previous.read_bytes()==old.read_bytes(),'Unexpected isolated runner change'
    previous.unlink()
base=source_sha()
for f in (ROOT/'Assets/scripts').rglob('*.cs'):
    dest=target/f.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
assert source_sha(target)==base
engine=target/'Assets/scripts/Core/PaperModelEngine.cs'
text=engine.read_text(encoding='utf-8-sig');needle='agent.desiredPos=SampleEvacuee(agent,field,occupied); continue;'
assert text.count(needle)==1
text=text.replace(needle,'CalibrationApproachObserver?.Invoke(agent.AgentID); '+needle)
declaration='public sealed class PaperModelEngine\n{'
assert declaration in text
text=text.replace(declaration,declaration+'\n    public static System.Action<int> CalibrationApproachObserver;')
engine.write_text(text,encoding='utf-8')
runner=target/'Assets/scripts/Editor/ScenarioPhysicalCalibration.cs'
shutil.copyfile(ROOT/'tools/ScenarioPhysicalCalibration.cs',runner)
jobs=[]
for seed in range(71001,71007):
    jobs.append(dict(id=f'O_s{seed}',seed=seed,blocked=0,policy='None',manipulationSteps=1))
    for blocked in [2,5]:
        jobs.append(dict(id=f'B{blocked}_None_s{seed}',seed=seed,blocked=blocked,policy='None',manipulationSteps=1))
        for work in [1,4]:
            for policy in ['Focal0','AllHelp']:
                jobs.append(dict(id=f'B{blocked}_M{work}_{policy}_s{seed}',seed=seed,blocked=blocked,policy=policy,manipulationSteps=work))
assert len(jobs)==66
plan=dict(schema='scenario-physical-calibration-v1',date='2026-11-16',purpose='Stage2 physical interpretation, not new LLM/formal data',baseSourceSHA=base,horizon=300,jobs=jobs,agents=10,apiCallsAllowed=0,randomization='Fixed six fresh development seed blocks; paired initial positions, divergent trajectories need not share future random draws',intervention='Override decision callback; focal ID0 or all willing, others decline. No false Original or LLM policy claims.',factors='B2/B5 layouts and workProgress intervals1/4; total5 obstacles; no pure tau causal claim',units='simulation ticks, not measured human seconds',failureRule='Stop on invalid or unexpected API; retain all timeouts, negative benefits and unsuccessful handling; no automatic rerun',mappingRule={'scale':301,'burden':'per-agent approach-assigned ticks plus active-handler ticks; includes nonworker candidates and failed approach','personalDelta':'capped exit step in intervention minus same-ID None control','othersBenefit':'mean capped exit step in None minus intervention for IDs1..9, focal comparison only','noHelpLoss':'mean capped exit step None blocked minus None open; never use test-future values as LLM observation','projection':'exploratory nonnegative time-burden/301 and nonnegative noHelpLoss/301; report zero/negative raw values and reject cv>=av or av=0, never clip into paper domain'},sourceFiles={str(f.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in [ROOT/'tools/ScenarioPhysicalCalibration.cs',ROOT/'tools/prepare_scenario_physics.py']})
(reg/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for f in [engine,runner]:shutil.copyfile(f,reg/f.name)
(reg/'source-binding.json').write_text(json.dumps(dict(baseProductionSHA=base,instrumentedProjectSHA=source_sha(target),instrumentation='One approach-branch event hook plus isolated Editor runner; original production Assets unchanged'),indent=2)+'\n')
assert source_sha()==base
print(json.dumps(dict(plan=str(reg/'plan.json'),project=str(target),output=str(out),runs=len(jobs),apiCalls=0),indent=2))
