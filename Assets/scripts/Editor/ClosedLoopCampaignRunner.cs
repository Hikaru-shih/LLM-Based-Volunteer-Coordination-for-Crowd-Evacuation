using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

// Explicit command only. FinalTest requires an additional opt-in and the new group lock.
public static class ClosedLoopCampaignRunner
{
    [Serializable] public sealed class Status
    {public string outcome,error,currentJob,sourceSHA;public int completed,total,reservedHttp;public bool geometryOnly;}
    private static ClosedLoopCampaign plan;private static SimulationManager manager;
    private static string output,root,stopFile,lockPath;private static bool geometry,done;
    private static int completed,reserved;private static double deadline;
    private static readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();private static AsyncOperation waiting;
    private static readonly BindingFlags Private=BindingFlags.NonPublic|BindingFlags.Instance;
    public static void Run()
    {
        try
        {
            string[] args=Environment.GetCommandLineArgs();Func<string,string> option=n=>{int i=Array.IndexOf(args,n);return i>=0&&i+1<args.Length?args[i+1]:null;};
            string file=option("-groupPlan");output=option("-groupOutput");root=option("-credentialRoot");stopFile=option("-groupStopFile");lockPath=option("-groupLock");geometry=option("-geometryOnly")=="true";
            if(string.IsNullOrEmpty(file)||string.IsNullOrEmpty(root)||string.IsNullOrEmpty(output)||Directory.Exists(output))throw new ArgumentException("Explicit new output, plan and credential root required");
            string text=File.ReadAllText(file);plan=JsonUtility.FromJson<ClosedLoopCampaign>(text);
            if(plan==null || plan.schema!="closed-loop-campaign-v1" || plan.model!="gpt-6-luna" || plan.jobs==null || plan.jobs.Length<1 || plan.jobs.Length>2000 || plan.jobs.Select(j=>j.id).Distinct().Count()!=plan.jobs.Length || plan.horizon<1 || plan.wallSeconds<1 || plan.maxReservedHttp<0 || plan.jobs.Any(j=>!Regex.IsMatch(j.id??"","^[A-Za-z0-9_]+$")))
                throw new ArgumentException("Invalid campaign plan");
            if(ClosedLoopStudyGuard.ProductionSHA(Path.GetDirectoryName(Application.dataPath))!=plan.sourceSHA)throw new Exception("Production source drift");
            if(plan.phase=="FinalTest")
            {
                if(geometry || option("-confirmFinalExecution")!="true")throw new Exception("Final execution is separately opt-in; use FinalGeometry for zero-step preflight");
                var locked=ClosedLoopStudyGuard.Verify(lockPath);
                if(locked.formalPlanSHA!=ClosedLoopInitialState.Hash(text))throw new Exception("Final plan not frozen");
            }
            else if(!new[]{"Geometry","FinalGeometry","Development","Calibration","RandomControlPreflight","Replay"}.Contains(plan.phase))throw new ArgumentException("Unknown group phase");
            if((plan.phase=="Geometry"||plan.phase=="FinalGeometry")!=geometry)throw new Exception("Geometry phase must not execute simulation steps");
            if(plan.phase=="Calibration" && plan.jobs.Any(j=>j.policy!="LLM"||j.seed<42001||j.seed>42010))throw new Exception("Calibration split drift");
            if(!geometry && plan.phase!="FinalTest" && plan.jobs.Any(j=>j.seed>=51001&&j.seed<=51030))throw new Exception("Reserved final seeds cannot run during preparation");
            Directory.CreateDirectory(output);File.Copy(file,Path.Combine(output,"registered-plan.json"));
            string partition=option("-groupPartition");
            if(!string.IsNullOrEmpty(partition))
            {
                var pieces=partition.Split('/');int index=int.Parse(pieces[0]),count=int.Parse(pieces[1]);
                if(plan.phase!="FinalTest"||count<1||count>4||index<0||index>=count)throw new Exception("Invalid final job partition");
                plan.jobs=plan.jobs.Where((job,i)=>i%count==index).ToArray();
            }
            File.WriteAllText(Path.Combine(output,"executed-plan.json"),JsonUtility.ToJson(plan,true));Save("starting","");
            deadline=EditorApplication.timeSinceStartup+plan.wallSeconds;stack.Push(Cases());EditorApplication.update+=Tick;
        }
        catch(Exception e){Finish(e);}
    }
    public static SimulationManager Make(ClosedLoopJob job,ClosedLoopCampaign p,string folder,string credentialRoot,bool geometryOnly,string groupLock="")
    {
        var m=ResearchValidation.CreateManager(folder);
        m.closedLoopZeroStepValidation=geometryOnly && p.phase=="FinalTest";
        m.closedLoopInitialState=ClosedLoopInitialState.Build(job.seed,job.agents,job.blocked);m.closedLoopSourceSHA=p.sourceSHA;m.closedLoopJobID=job.id;m.closedLoopLockPath=groupLock;
        m.recordExperimentsAutomatically=!geometryOnly;m.experimentRecordsRootOverride=Path.Combine(credentialRoot,"experiment_records");m.experimentPurpose="Closed-loop "+p.phase+" / "+job.id+" / separate group-study workflow";
        m.obstacleHandlingMode=ObstacleHandlingMode.PaperRelocation;m.paperExecutionMode=Coordination.ExecutionMode.PaperReference;m.coordinationAvailability=Coordination.AvailabilityMode.PolicyWillingness;
        m.volunteerDecisionMode=(SimulationManager.VolunteerDecisionMode)Enum.Parse(typeof(SimulationManager.VolunteerDecisionMode),job.policy);
        m.researchScenario=job.blocked==0?ResearchScenario.OpenRoom:ResearchScenario.SingleBlockedExit;
        m.world.width=m.world.height=21;m.world.cellSize=1;m.agentCount=job.agents;m.agentSpawnAreaSize=new Vector2Int(8,8);m.obstacleCount=5;m.researchExitWidth=3;m.exitCount=1;m.exitApproachDepth=3;m.obstacleVisibilityRange=20;m.baseSeed=job.seed;
        m.kStatic=3;m.kDynamic=1;m.kAnticipation=5;m.movementTemperature=1;m.movementStrategy=PedestrianAgent.MovementStrategy.Combined;m.conflictStrategy=Decision.YielderGame.Strategy.PaperYielder;
        m.volunteerCost=job.cv;m.failureCost=.5f;m.unwillingnessOmega=5;m.paperManipulationSteps=1;m.paperDiffusion=.3f;m.paperDecay=.1f;m.paperAnticipationRadius=6;
        m.paperAbandonDensity=.01f;m.paperDensityWindow=10;m.paperReplanAfterSteps=10;m.paperDestinationRule=PaperDestinationRule.NextToWallsOrObstacles;m.paperDestinationExitDistance=2;m.yielderDefectionCost=1;m.yielderFriction=0;
        m.agentInformation=AgentInformationCondition.Core;m.agentPromptWording=AgentPromptWording.Standard;m.agentResearchPhase=p.phase=="FinalTest"?AgentResearchPhase.FinalTest:p.phase=="Calibration"?AgentResearchPhase.Calibration:AgentResearchPhase.Development;
        m.maxSimulationSteps=p.horizon;m.maxAgentRequestsPerRun=checked(p.horizon*job.agents*5);m.allowMockFallback=false;m.batchRunCount=1;m.openAIModel=p.model;
        m.cooperationCalibrationPath=string.IsNullOrEmpty(job.calibrationFile)?"":Path.GetFullPath(Path.IsPathRooted(job.calibrationFile)?job.calibrationFile:Path.Combine(Path.GetDirectoryName(groupLock),job.calibrationFile));
        m.paperDecisionReplayPath=p.phase=="Replay"?job.replayFile:"";
        if(!geometryOnly && job.policy=="LLM" && p.phase!="Replay")
        {
            m.openAIKey=File.ReadAllText(Path.Combine(credentialRoot,"openai-key.local.txt")).Trim().TrimStart('\uFEFF');
            if(!LocalOpenAIKey.HasValidLocalFormat(m.openAIKey))throw new Exception("Invalid local credential format");
        }
        else m.openAIKey="";
        return m;
    }
    private static void Reserve()
    {
        if(!string.IsNullOrEmpty(stopFile)&&File.Exists(stopFile))throw new Exception("Campaign stop marker");
        if(reserved+3>plan.maxReservedHttp)throw new Exception("Registered campaign HTTP reservation ceiling");
        if(plan.phase=="FinalTest")ClosedLoopStudyGuard.ReserveFinal(root,ClosedLoopStudyGuard.Verify(lockPath).lockID,plan.maxReservedHttp);
        reserved+=3;Save("request_reserved","");
    }
    private static IEnumerator Cases()
    {
        foreach(var job in plan.jobs)
        {
            if(!string.IsNullOrEmpty(stopFile)&&File.Exists(stopFile))throw new Exception("Campaign stop marker");
            if(!new[]{"OriginalGameTheory","LLM","NoVolunteers","RandomMatched"}.Contains(job.policy)||job.cv<=0||job.cv>=.5f)throw new Exception("Unsupported policy/cost");
            string folder=Path.Combine(output,job.id);Directory.CreateDirectory(folder);manager=Make(job,plan,folder,root,geometry,lockPath);manager.closedLoopBeforeApiRequest=Reserve;
            Save("job_start","");ResearchValidation.Begin(manager);
            var state=manager.closedLoopInitialState;float tau=ResearchEnvironment.PaperExitNonBlockage(manager.world,new Vector2Int(10,1));
            if(manager.GetTotalAgents()!=job.agents || manager.PaperModel.Obstacles.Count!=5 || manager.PaperModel.InitialBlockedTaskCount!=job.blocked || Math.Abs(tau-(1-job.blocked/5f))>1e-6 ||
                !manager.GetAllAgents().Select(a=>a.gridPos).SequenceEqual(state.agentCells) || !new HashSet<Vector2Int>(manager.world.GetObstaclePositions()).SetEquals(state.obstacleCells))throw new Exception("Initial geometry differs from manifest");
            File.WriteAllText(Path.Combine(folder,"initial-state.json"),JsonUtility.ToJson(state,true));
            File.WriteAllText(Path.Combine(folder,"binding.json"),"{\"conditionKey\":\""+manager.AgentConditionKey+"\",\"initialStateSHA\":\""+state.Identity+"\",\"templateSHA\":\""+state.TemplateSHA+"\",\"sourceSHA\":\""+plan.sourceSHA+"\"}");
            if(geometry)typeof(SimulationManager).GetMethod("ExportFinishedRun",Private).Invoke(manager,new object[]{"geometry_only"});
            else while(manager.IsSimulationRunning())yield return (IEnumerator)typeof(SimulationManager).GetMethod("SimulationStepCoroutine",Private).Invoke(manager,null);
            string termination=(string)typeof(SimulationManager).GetField("currentTermination",Private).GetValue(manager);
            manager.ResetSimulation();manager=null;ResearchValidation.Cleanup();completed++;Save(termination,"");
            if(termination.StartsWith("invalid"))throw new Exception("Stop on invalid: "+job.id+": "+termination);
        }
        done=true;
    }
    private static void Save(string outcome,string error)
    {
        if(string.IsNullOrEmpty(output)||!Directory.Exists(output))return;
        var status=new Status {outcome=outcome,error=error,completed=completed,total=plan?.jobs?.Length??0,reservedHttp=reserved,geometryOnly=geometry,sourceSHA=plan?.sourceSHA,currentJob=manager?.closedLoopJobID};
        string file=Path.Combine(output,"progress.json"),temp=file+".tmp";File.WriteAllText(temp,JsonUtility.ToJson(status,true));
        if(File.Exists(file))File.Replace(temp,file,null);else File.Move(temp,file);
    }
    private static void Tick()
    {
        try
        {
            if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException("Registered campaign wall-clock ceiling");
            if(!string.IsNullOrEmpty(stopFile)&&File.Exists(stopFile))throw new Exception("Campaign stop marker");
            if(waiting!=null){if(!waiting.isDone)return;waiting=null;}
            if(stack.Count==0){Finish(done?null:new Exception("Unexpected empty stack"));return;}
            var e=stack.Peek();if(!e.MoveNext()){stack.Pop();return;}
            if(e.Current is IEnumerator nested)stack.Push(nested);else if(e.Current is AsyncOperation operation)waiting=operation;
        }
        catch(Exception e){Finish(e);}
    }
    private static void Finish(Exception error)
    {
        EditorApplication.update-=Tick;
        while(stack.Count>0){try{(stack.Pop() as IDisposable)?.Dispose();}catch{}}
        if(manager!=null)
        {
            if(manager.IsSimulationRunning())typeof(SimulationManager).GetMethod("ExportFinishedRun",Private).Invoke(manager,new object[]{"invalid_group_campaign_abort"});
            manager.ResetSimulation();manager=null;
        }
        ResearchValidation.Cleanup();Save(error==null?"completed":"stopped",error?.ToString());
        if(error!=null && !string.IsNullOrEmpty(stopFile) && !File.Exists(stopFile))File.WriteAllText(stopFile,error.ToString());
        if(error!=null)Debug.LogError("CLOSED_LOOP_CAMPAIGN_STOPPED: "+error);else Debug.Log("CLOSED_LOOP_CAMPAIGN_COMPLETED: "+completed+"; geometryOnly="+geometry);
        EditorApplication.Exit(error==null?0:1);
    }
}
