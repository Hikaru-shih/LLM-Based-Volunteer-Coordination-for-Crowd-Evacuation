using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;

/// <summary>Explicit live functional test. Never invoked by contract tests.</summary>
public static class LLMLiveSmokeTest
{
    private const string Root="D:/LLM-Based-Volunteer-Coordination-for-Crowd-Evacuation";
    private static SimulationManager manager;
    private static readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();
    private static AsyncOperation waiting;
    private static string output;
    private static double deadline;
    private const BindingFlags Private=BindingFlags.NonPublic|BindingFlags.Instance;

    public static void Run()
    {
        // Use -executeMethod without -quit; asynchronous requests must finish before exiting.
        output=Path.Combine(Root,"tmp/llm-smoke-tests",DateTime.UtcNow.ToString("yyyyMMdd_HHmmss"));
        Directory.CreateDirectory(output);
        try
        {
            string key=File.ReadAllText(Path.Combine(Root,"openai-key.local.txt")).Trim().TrimStart('\uFEFF');
            if(string.IsNullOrEmpty(key) || !LocalOpenAIKey.HasValidLocalFormat(key))
                throw new InvalidOperationException("A valid-format local credential is required");
            manager=ResearchValidation.CreateManager(output);
            manager.recordExperimentsAutomatically=true;
            manager.experimentPurpose="Blocked-exit functional comparison: LLMLiveSmokeTest";
            manager.experimentRecordsRootOverride="D:/LLM-Based-Volunteer-Coordination-for-Crowd-Evacuation/experiment_records";
            manager.obstacleHandlingMode=ObstacleHandlingMode.PaperRelocation;
            manager.volunteerDecisionMode=SimulationManager.VolunteerDecisionMode.LLM;
            manager.researchScenario=ResearchScenario.SingleBlockedExit;
            manager.world.cellSize=0.4f;manager.agentCount=2;manager.obstacleCount=5;
            manager.researchExitWidth=3;manager.obstacleVisibilityRange=20;
            manager.kStatic=3;manager.kDynamic=1;manager.kAnticipation=5;
            manager.movementTemperature=1;manager.volunteerCost=0.005f;manager.failureCost=0.5f;manager.unwillingnessOmega=5;
            manager.conflictStrategy=Decision.YielderGame.Strategy.PaperYielder;
            manager.movementStrategy=PedestrianAgent.MovementStrategy.Combined;
            manager.paperManipulationSteps=1;manager.paperDiffusion=0.3f;manager.paperDecay=0.1f;manager.paperAnticipationRadius=6;
            manager.yielderDefectionCost=1;manager.yielderFriction=0;
            manager.batchRunCount=1;manager.maxSimulationSteps=40;manager.maxAgentRequestsPerRun=12;
            manager.allowMockFallback=false;manager.openAIModel="gpt-4o-mini";manager.openAIKey=key;
            manager.agentResearchPhase=AgentResearchPhase.Development;
            ResearchValidation.Begin(manager);
            deadline=EditorApplication.timeSinceStartup+600;
            EditorApplication.update+=Tick;
            Debug.Log("LLM_LIVE_SMOKE_STARTED: 2 pedestrians, 5 exit obstacles, at most 12 logical calls, 40 steps");
        }
        catch(Exception error) {Finish(error);}
    }

    private static void Tick()
    {
        try
        {
            if(EditorApplication.timeSinceStartup>deadline) throw new TimeoutException("Live functional-test wall-clock limit");
            if(waiting!=null) {if(!waiting.isDone) return;waiting=null;}
            if(stack.Count==0)
            {
                if(!manager.IsSimulationRunning()) {Finish(null);return;}
                stack.Push((IEnumerator)typeof(SimulationManager).GetMethod("SimulationStepCoroutine",Private).Invoke(manager,null));
            }
            // Advance one yield per editor tick; never busy-spin a UnityWebRequest.
            var routine=stack.Peek();
            if(!routine.MoveNext()) {stack.Pop();return;}
            if(routine.Current is IEnumerator nested) stack.Push(nested);
            else if(routine.Current is AsyncOperation operation) waiting=operation;
        }
        catch(Exception error) {Finish(error);}
    }

    private static void Finish(Exception error)
    {
        EditorApplication.update-=Tick;
        if(error!=null && manager!=null)
            typeof(SimulationManager).GetMethod("ExportFinishedRun",Private).Invoke(manager,new object[]{"invalid_smoke_test_abort"});
        if(output!=null) File.WriteAllText(Path.Combine(output,"smoke_status.json"),
            JsonUtility.ToJson(new Status {runnerCompleted=error==null,error=error?.GetType().Name,steps=manager!=null?manager.GetCurrentStep():0},true));
        if(manager!=null) manager.ResetSimulation();
        ResearchValidation.Cleanup();
        Debug.Log("LLM_LIVE_SMOKE_FINISHED: "+(error==null ? "inspect exported results" : error.GetType().Name));
        EditorApplication.Exit(error==null?0:1);
    }
    [Serializable] private class Status {public bool runnerCompleted;public string error;public int steps;}
}
