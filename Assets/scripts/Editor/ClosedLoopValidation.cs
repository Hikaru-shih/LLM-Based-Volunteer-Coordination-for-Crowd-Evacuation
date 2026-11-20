using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

public static class ClosedLoopValidation
{
    private static int checks;
    private static void Check(bool ok,string why){checks++;if(!ok)throw new Exception(why);}
    private static void Reject(Action action,string why){bool rejected=false;try{action();}catch{rejected=true;}Check(rejected,why);}
    public static void Run()
    {
        string folder=Path.GetFullPath("tmp/closed-loop-validation/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff"));Directory.CreateDirectory(folder);
        try
        {
            checks=0;string source=ClosedLoopStudyGuard.ProductionSHA(Path.GetDirectoryName(Application.dataPath));
            foreach(int seed in new[]{41001,41002,41003,41004,41005,41006})foreach(int b in new[]{0,2,5})
            {
                var ten=ClosedLoopInitialState.Build(seed,10,b);var thirty=ClosedLoopInitialState.Build(seed,30,b);
                ten.Validate(10,seed);thirty.Validate(30,seed);Check(ten.agentCells.SequenceEqual(thirty.agentCells.Take(10)),"Nested population drift");
                Check(ten.obstacleCells.SequenceEqual(thirty.obstacleCells) && ten.obstacleCells.Length==5,"Obstacle population changed");
                var job=new ClosedLoopJob {id="geometry_"+seed+"_"+b,seed=seed,agents=30,blocked=b,cv=.05f,policy="OriginalGameTheory"};
                var p=new ClosedLoopCampaign {phase="Geometry",horizon=300,sourceSHA=source,model="gpt-6-luna"};
                var m=ClosedLoopCampaignRunner.Make(job,p,Path.Combine(folder,job.id),Path.GetDirectoryName(Application.dataPath),true);
                ResearchValidation.Begin(m);
                Check(m.GetTotalAgents()==30 && m.PaperModel.Obstacles.Count==5 && m.PaperModel.InitialBlockedTaskCount==b,"Actual task count drift");
                Check(Math.Abs(ResearchEnvironment.PaperExitNonBlockage(m.world,new Vector2Int(10,1))-(1-b/5f))<1e-6,"Actual tau drift");
                Check(m.GetAllAgents().Select(a=>a.gridPos).SequenceEqual(thirty.agentCells),"Actual spawn order drift");
                typeof(SimulationManager).GetMethod("ExportFinishedRun",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(m,new object[]{"geometry_validation_only"});
                m.ResetSimulation();ResearchValidation.Cleanup();
            }
            var changed=ClosedLoopInitialState.Build(41001,10,2);changed.agentCells[0]=changed.obstacleCells[0];Reject(()=>changed.Validate(10,41001),"Tampered geometry accepted");
            var baseState=ClosedLoopInitialState.Build(41001,10,2);
            string cal=Path.Combine(folder,"synthetic-calibration.json");
            var c=new CooperationCalibration {schema="cooperation-calibration-v2",split="Calibration",calibrationID="synthetic-only",conditionKey="test",model="gpt-6-luna",informationCondition="Core",promptVersion=PaperVolunteerPrompt.Version,responseProtocol=PersonalDecisionProtocol.Version,geometryTemplateSHA=baseState.TemplateSHA,productionSourceSHA=source,horizon=300,decisions=2,probability=.5f,seeds=new[]{42001},sourceHashes=new[]{"synthetic-only"}};
            Action save=()=>File.WriteAllText(cal,JsonUtility.ToJson(c));
            Action load=()=>CooperationCalibration.Load(cal,"test","gpt-6-luna",AgentInformationCondition.Core,51001,AgentResearchPhase.FinalTest,true,baseState.TemplateSHA,source,300);
            save();load();Check(true,"v2 load");
            foreach(string field in new[]{"schema","responseProtocol","geometryTemplateSHA","productionSourceSHA"})
            {
                var f=typeof(CooperationCalibration).GetField(field);string old=(string)f.GetValue(c);f.SetValue(c,"changed");save();Reject(load,"Calibration version binding failed: "+field);f.SetValue(c,old);
            }
            c.horizon=301;save();Reject(load,"Calibration horizon drift accepted");c.horizon=300;save();
            Reject(()=>CooperationCalibration.Load(cal,"test","gpt-6-luna",AgentInformationCondition.Core,42001,AgentResearchPhase.FinalTest,true,baseState.TemplateSHA,source,300),"Calibration/test overlap accepted");
            Reject(()=>ClosedLoopStudyGuard.Verify(""),"Final lock optional");
            Check(ClosedLoopStudyGuard.MatchesProvider("{\"model\":\"gpt-6-luna\"}","gpt-6-luna") && !ClosedLoopStudyGuard.MatchesProvider("{\"model\":\"other\"}","gpt-6-luna"),"Provider drift check");
            var noJob=new ClosedLoopJob {id="no_help",seed=41001,agents=10,blocked=5,cv=.05f,policy="NoVolunteers"};
            var noPlan=new ClosedLoopCampaign {phase="Development",horizon=20,sourceSHA=source,model="gpt-6-luna"};
            var no=ClosedLoopCampaignRunner.Make(noJob,noPlan,Path.Combine(folder,"no_help"),Path.GetDirectoryName(Application.dataPath),true);no.recordExperimentsAutomatically=false;
            ResearchValidation.Begin(no);while(no.IsSimulationRunning())ResearchValidation.Step(no);
            Check(no.GetAllAgents().All(a=>!a.IsEvacuated()),"No-help full blockage leaked an escape");no.ResetSimulation();ResearchValidation.Cleanup();
            string claimRoot=Path.Combine(folder,"claims_test");ClosedLoopStudyGuard.ClaimFinal(claimRoot,"synthetic-lock","synthetic-job");
            Reject(()=>ClosedLoopStudyGuard.ClaimFinal(claimRoot,"synthetic-lock","synthetic-job"),"Duplicate final job accepted");
            ClosedLoopStudyGuard.ReserveFinal(folder,"synthetic-budget",3);
            Reject(()=>ClosedLoopStudyGuard.ReserveFinal(folder,"synthetic-budget",3),"Final budget exceeded");
            var zeroJob=new ClosedLoopJob {id="zero_guard",seed=41002,agents=10,blocked=0,cv=.05f,policy="NoVolunteers"};
            var zeroPlan=new ClosedLoopCampaign {phase="Development",horizon=2,sourceSHA=source,model="gpt-6-luna"};
            var zero=ClosedLoopCampaignRunner.Make(zeroJob,zeroPlan,Path.Combine(folder,"zero_guard"),Path.GetDirectoryName(Application.dataPath),true);
            ResearchValidation.Begin(zero);zero.closedLoopZeroStepValidation=true;Reject(()=>ResearchValidation.Step(zero),"Zero-step preflight executed physics");
            typeof(SimulationManager).GetMethod("ExportFinishedRun",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(zero,new object[]{"zero_guard_only"});zero.ResetSimulation();ResearchValidation.Cleanup();
            IndividualDecisionValidation.Run();
            File.WriteAllText(Path.Combine(folder,"result.json"),"{\"passed\":true,\"checks\":"+checks+",\"remoteRequests\":0,\"finalSimulationRuns\":0}");
            Directory.CreateDirectory("tmp/closed-loop-validation");File.WriteAllText("tmp/closed-loop-validation/latest.txt",folder);
            Debug.Log("CLOSED_LOOP_VALIDATION_PASSED: "+checks+" group checks plus individual regressions; zero API");EditorApplication.Exit(0);
        }
        catch(Exception e)
        {File.WriteAllText(Path.Combine(folder,"failure.txt"),e.ToString());ResearchValidation.Cleanup();Debug.LogError(e);EditorApplication.Exit(1);}
    }
}
