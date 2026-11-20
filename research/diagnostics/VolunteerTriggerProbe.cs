using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;

// Diagnostic harness only. Copy into an isolated Editor folder; never part of the frozen study.
public static class VolunteerTriggerProbe
{
    private static readonly BindingFlags Private=BindingFlags.NonPublic|BindingFlags.Instance;
    private static readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();
    private static SimulationManager manager;
    private static AsyncOperation waiting;
    private static string root,output;
    private static double deadline;
    private static bool done;
    [Serializable] private class Geometry {public string name;public int blockedTasks,agents,obstacles;public float[] tau;public int[] eligible;}
    [Serializable] private class Status {public bool runnerCompleted;public string error;public int maxLogicalRequests=12,maxHttpAttempts=36,maxStepsPerBlockedCase=60;}
    public static void Run()
    {
        try
        {
            var args=Environment.GetCommandLineArgs();
            Func<string,string> option=name=>{int i=Array.IndexOf(args,name);return i>=0 && i+1<args.Length?args[i+1]:null;};
            root=option("-credentialRoot");output=option("-probeOutput");
            if(string.IsNullOrEmpty(root) || string.IsNullOrEmpty(output) || Directory.Exists(output))throw new ArgumentException("Explicit original credential root and new output required");
            Directory.CreateDirectory(output);
            VolunteerFlowDiagnostic.Run(); // Separate injected consent-to-handler check, zero API.
            File.WriteAllText(Path.Combine(output,"offline-handler-check.json"),"{\"passed\":true,\"remoteRequests\":0,\"source\":\"injected functional fixture\"}");
            stack.Push(Cases());deadline=EditorApplication.timeSinceStartup+600;
            EditorApplication.update+=Tick;
        }
        catch(Exception e){Finish(e);}
    }
    private static IEnumerator Cases()
    {
        foreach(string name in new[]{"random500_no_game","blocked_original","blocked_luna"})
        {
            string folder=Path.Combine(output,name);Directory.CreateDirectory(folder);
            manager=ResearchValidation.CreateManager(folder);
            bool random=name.StartsWith("random"), live=name=="blocked_luna";
            manager.recordExperimentsAutomatically=true;
            manager.experimentRecordsRootOverride=Path.Combine(root,"experiment_records");
            manager.experimentPurpose="Functional trigger diagnosis / "+name+" / not formal comparison or empirical calibration";
            manager.obstacleHandlingMode=ObstacleHandlingMode.PaperRelocation;
            manager.paperExecutionMode=Coordination.ExecutionMode.PaperReference;
            manager.coordinationAvailability=Coordination.AvailabilityMode.PolicyWillingness;
            manager.volunteerDecisionMode=name=="blocked_original"?SimulationManager.VolunteerDecisionMode.OriginalGameTheory:SimulationManager.VolunteerDecisionMode.LLM;
            manager.researchScenario=random?ResearchScenario.RandomRoom:ResearchScenario.SingleBlockedExit;
            manager.world.width=manager.world.height=random?50:11;
            manager.agentCount=random?50:2;manager.obstacleCount=random?500:3;
            manager.agentSpawnAreaSize=new Vector2Int(random?30:5,random?30:5);
            manager.researchExitWidth=random?3:1;manager.exitCount=1;manager.exitApproachDepth=3;
            manager.obstacleVisibilityRange=20;manager.baseSeed=2026;
            manager.kStatic=3;manager.kDynamic=1;manager.kAnticipation=5;manager.movementTemperature=1;
            manager.movementStrategy=PedestrianAgent.MovementStrategy.Combined;
            manager.conflictStrategy=Decision.YielderGame.Strategy.PaperYielder;
            manager.volunteerCost=.005f;manager.failureCost=.5f;manager.unwillingnessOmega=5;
            manager.paperManipulationSteps=1;manager.paperDiffusion=.3f;manager.paperDecay=.1f;
            manager.paperAnticipationRadius=6;manager.yielderDefectionCost=1;manager.yielderFriction=0;
            manager.agentInformation=AgentInformationCondition.Core;manager.agentPromptWording=AgentPromptWording.Standard;
            manager.agentResearchPhase=AgentResearchPhase.Development;
            manager.batchRunCount=1;manager.maxSimulationSteps=random?20:60;
            manager.maxAgentRequestsPerRun=12;manager.allowMockFallback=false;manager.openAIModel="gpt-6-luna";
            // The negative control must prove zero tasks before any live client credential is loaded.
            manager.openAIKey=live?File.ReadAllText(Path.Combine(root,"openai-key.local.txt")).Trim().TrimStart('\uFEFF'):"";
            ResearchValidation.Begin(manager);
            var engine=manager.PaperModel;
            var obstacles=engine.Obstacles;
            File.WriteAllText(Path.Combine(folder,"initial-trigger-geometry.json"),JsonUtility.ToJson(new Geometry {
                name=name,blockedTasks=engine.InitialBlockedTaskCount,agents=manager.GetTotalAgents(),obstacles=obstacles.Count,
                tau=obstacles.Select(o=>ResearchEnvironment.PaperExitNonBlockage(manager.world,o.position)).ToArray(),
                eligible=obstacles.Select(o=>manager.GetAllAgents().Count(a=>!a.IsEvacuated() && !a.IsActiveVolunteer() && PaperGrid.Distance(a.gridPos,o.position)<=manager.obstacleVisibilityRange)).ToArray()},true));
            if(random && engine.InitialBlockedTaskCount!=0)throw new Exception("Negative control unexpectedly blocked; no request sent");
            if(!random && engine.InitialBlockedTaskCount!=3)throw new Exception("Controlled blocked layout not created");
            while(manager.IsSimulationRunning())
                yield return (IEnumerator)typeof(SimulationManager).GetMethod("SimulationStepCoroutine",Private).Invoke(manager,null);
            manager.ResetSimulation();manager=null;ResearchValidation.Cleanup();
        }
        done=true;
    }
    private static void Tick()
    {
        try
        {
            if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException("Probe wall-clock ceiling");
            if(waiting!=null){if(!waiting.isDone)return;waiting=null;}
            if(stack.Count==0){Finish(done?null:new Exception("Unexpected empty diagnostic stack"));return;}
            var routine=stack.Peek();
            if(!routine.MoveNext()){stack.Pop();return;}
            if(routine.Current is IEnumerator nested)stack.Push(nested);
            else if(routine.Current is AsyncOperation operation)waiting=operation;
        }
        catch(Exception e){Finish(e);}
    }
    private static void Finish(Exception error)
    {
        EditorApplication.update-=Tick;
        if(error!=null)Debug.LogError("TRIGGER_PROBE_FAILED: "+error);
        while(stack.Count>0){try{(stack.Pop() as IDisposable)?.Dispose();}catch{}}
        if(manager!=null)
        {
            if(manager.IsSimulationRunning())typeof(SimulationManager).GetMethod("ExportFinishedRun",Private).Invoke(manager,new object[]{"invalid_probe_abort"});
            manager.ResetSimulation();manager=null;
        }
        ResearchValidation.Cleanup();
        if(output!=null)File.WriteAllText(Path.Combine(output,"probe-status.json"),JsonUtility.ToJson(new Status {runnerCompleted=error==null,error=error?.ToString()},true));
        Debug.Log("TRIGGER_PROBE_FINISHED: "+(error==null?"inspect raw functional results":"failed; retain evidence"));
        EditorApplication.Exit(error==null?0:1);
    }
}
