using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// Development pilot harness. Not part of the production simulator or frozen formal study.
public static class BoundedGamePilot
{
    [Serializable] public class Job {public string id,policy;public int seed,obstacles;public float expectedTau;}
    [Serializable] public class Plan {public string schema,model;public int width,height,agents,spawn,exitWidth,visibility,maxSteps,maxRequestsPerRun,wallSeconds;public float cv,av,omega;public Job[] jobs;}
    [Serializable] public class Geometry {public string id,policy;public int seed,blockedTasks,agents,obstacles;public float exitTau;public Vector2Int[] exitCells,obstacleCells,agentCells;public int[] eligible;}
    [Serializable] public class Progress {public string outcome,error;public int completed,total;public bool geometryOnly;}
    private static Plan plan;
    private static string root,output;
    private static bool geometryOnly,done;
    private static SimulationManager manager;
    private static AsyncOperation waiting;
    private static readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();
    private static readonly BindingFlags Private=BindingFlags.NonPublic|BindingFlags.Instance;
    private static double deadline;
    private static int completed;
    public static void Run()
    {
        try
        {
            var args=Environment.GetCommandLineArgs();
            Func<string,string> option=name=>{int i=Array.IndexOf(args,name);return i>=0 && i+1<args.Length?args[i+1]:null;};
            root=option("-credentialRoot");output=option("-pilotOutput");geometryOnly=option("-geometryOnly")=="true";
            string file=option("-pilotPlan");
            if(string.IsNullOrEmpty(root)||string.IsNullOrEmpty(output)||string.IsNullOrEmpty(file)||Directory.Exists(output))throw new ArgumentException("Explicit plan, original key root and new output required");
            plan=JsonUtility.FromJson<Plan>(File.ReadAllText(file));
            if(plan.schema!="bounded-game-pilot-v1" || plan.model!="gpt-6-luna" || plan.jobs.Length!=12 || plan.jobs.Select(j=>j.id).Distinct().Count()!=12 || plan.maxRequestsPerRun!=100 || plan.maxSteps!=150)throw new ArgumentException("Unexpected registered pilot");
            Directory.CreateDirectory(output);File.Copy(file,Path.Combine(output,"registered-plan.json"));
            stack.Push(Cases());deadline=EditorApplication.timeSinceStartup+plan.wallSeconds;
            EditorApplication.update+=Tick;
        }
        catch(Exception e){Finish(e);}
    }
    private static IEnumerator Cases()
    {
        foreach(var job in plan.jobs)
        {
            string folder=Path.Combine(output,job.id);Directory.CreateDirectory(folder);
            manager=ResearchValidation.CreateManager(folder);
            manager.recordExperimentsAutomatically=!geometryOnly;
            manager.experimentRecordsRootOverride=Path.Combine(root,"experiment_records");
            manager.experimentPurpose="Bounded game pilot / "+job.id+" / development only; not formal inference or calibration";
            manager.obstacleHandlingMode=ObstacleHandlingMode.PaperRelocation;
            manager.paperExecutionMode=Coordination.ExecutionMode.PaperReference;
            manager.coordinationAvailability=Coordination.AvailabilityMode.PolicyWillingness;
            manager.volunteerDecisionMode=job.policy=="LLM"?SimulationManager.VolunteerDecisionMode.LLM:SimulationManager.VolunteerDecisionMode.OriginalGameTheory;
            manager.researchScenario=job.obstacles==0?ResearchScenario.OpenRoom:ResearchScenario.SingleBlockedExit;
            manager.world.width=plan.width;manager.world.height=plan.height;
            manager.agentCount=plan.agents;manager.agentSpawnAreaSize=new Vector2Int(plan.spawn,plan.spawn);
            manager.obstacleCount=job.obstacles;manager.researchExitWidth=plan.exitWidth;manager.exitCount=1;
            manager.exitApproachDepth=3;manager.obstacleVisibilityRange=plan.visibility;manager.baseSeed=job.seed;
            manager.kStatic=3;manager.kDynamic=1;manager.kAnticipation=5;manager.movementTemperature=1;
            manager.movementStrategy=PedestrianAgent.MovementStrategy.Combined;
            manager.conflictStrategy=Decision.YielderGame.Strategy.PaperYielder;
            manager.volunteerCost=plan.cv;manager.failureCost=plan.av;manager.unwillingnessOmega=plan.omega;
            manager.paperManipulationSteps=1;manager.paperDiffusion=.3f;manager.paperDecay=.1f;manager.paperAnticipationRadius=6;
            manager.paperAbandonDensity=.01f;manager.paperDensityWindow=10;manager.paperReplanAfterSteps=10;
            manager.paperDestinationRule=PaperDestinationRule.NextToWallsOrObstacles;manager.paperDestinationExitDistance=2;
            manager.yielderDefectionCost=1;manager.yielderFriction=0;
            manager.agentInformation=AgentInformationCondition.Core;manager.agentPromptWording=AgentPromptWording.Standard;
            manager.agentResearchPhase=AgentResearchPhase.Development;manager.batchRunCount=1;
            manager.maxSimulationSteps=plan.maxSteps;manager.maxAgentRequestsPerRun=plan.maxRequestsPerRun;
            manager.allowMockFallback=false;manager.openAIModel=plan.model;
            manager.openAIKey=!geometryOnly && job.policy=="LLM"?File.ReadAllText(Path.Combine(root,"openai-key.local.txt")).Trim().TrimStart('\uFEFF'):"";
            ResearchValidation.Begin(manager);
            var obstacles=manager.PaperModel.Obstacles;var agents=manager.GetAllAgents();
            float tau=obstacles.Count>0?ResearchEnvironment.PaperExitNonBlockage(manager.world,obstacles[0].position):1f;
            if(manager.GetTotalAgents()!=plan.agents || obstacles.Count!=job.obstacles || Math.Abs(tau-job.expectedTau)>1e-6 || manager.PaperModel.InitialBlockedTaskCount!=job.obstacles)throw new Exception("Actual geometry differs from registered case");
            var geometry=new Geometry {id=job.id,policy=job.policy,seed=job.seed,blockedTasks=manager.PaperModel.InitialBlockedTaskCount,
                agents=agents.Count,obstacles=obstacles.Count,exitTau=tau,exitCells=manager.world.exitPositions.ToArray(),
                obstacleCells=obstacles.Select(o=>o.position).ToArray(),agentCells=agents.Select(a=>a.gridPos).ToArray(),
                eligible=obstacles.Select(o=>agents.Count(a=>!a.IsEvacuated() && !a.IsActiveVolunteer() && PaperGrid.Distance(a.gridPos,o.position)<=plan.visibility)).ToArray()};
            File.WriteAllText(Path.Combine(folder,"initial-geometry.json"),JsonUtility.ToJson(geometry,true));
            if(geometryOnly)typeof(SimulationManager).GetMethod("ExportFinishedRun",Private).Invoke(manager,new object[]{"geometry_preflight_only"});
            else while(manager.IsSimulationRunning())yield return (IEnumerator)typeof(SimulationManager).GetMethod("SimulationStepCoroutine",Private).Invoke(manager,null);
            string termination=(string)typeof(SimulationManager).GetField("currentTermination",Private).GetValue(manager);
            manager.ResetSimulation();manager=null;ResearchValidation.Cleanup();completed++;
            File.WriteAllText(Path.Combine(output,"progress.json"),JsonUtility.ToJson(new Progress {outcome=termination,completed=completed,total=plan.jobs.Length,geometryOnly=geometryOnly},true));
            if(termination.StartsWith("invalid"))throw new Exception("Registered stop on invalid run: "+job.id+": "+termination);
        }
        done=true;
    }
    private static void Tick()
    {
        try
        {
            if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException("Pilot wall-clock ceiling");
            if(waiting!=null){if(!waiting.isDone)return;waiting=null;}
            if(stack.Count==0){Finish(done?null:new Exception("Unexpected empty pilot stack"));return;}
            var routine=stack.Peek();if(!routine.MoveNext()){stack.Pop();return;}
            if(routine.Current is IEnumerator nested)stack.Push(nested);
            else if(routine.Current is AsyncOperation operation)waiting=operation;
        }
        catch(Exception e){Finish(e);}
    }
    private static void Finish(Exception error)
    {
        EditorApplication.update-=Tick;
        while(stack.Count>0){try{(stack.Pop() as IDisposable)?.Dispose();}catch{}}
        if(manager!=null)
        {
            if(manager.IsSimulationRunning())typeof(SimulationManager).GetMethod("ExportFinishedRun",Private).Invoke(manager,new object[]{"invalid_pilot_abort"});
            manager.ResetSimulation();manager=null;
        }
        ResearchValidation.Cleanup();
        if(output!=null && Directory.Exists(output))File.WriteAllText(Path.Combine(output,"runner-status.json"),JsonUtility.ToJson(new Progress {outcome=error==null?"completed":"stopped",error=error?.ToString(),completed=completed,total=plan?.jobs?.Length??0,geometryOnly=geometryOnly},true));
        if(error!=null)Debug.LogError("BOUNDED_GAME_PILOT_STOPPED: "+error);else Debug.Log("BOUNDED_GAME_PILOT_COMPLETED: "+completed+" cases; geometryOnly="+geometryOnly);
        EditorApplication.Exit(error==null?0:1);
    }
}
