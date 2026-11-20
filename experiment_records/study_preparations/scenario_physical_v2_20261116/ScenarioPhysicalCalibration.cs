// Calibration-only Editor entry point. Copied to an isolated project, never production Assets.
using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Globalization;
using UnityEditor;
using UnityEngine;

public static class ScenarioPhysicalCalibration
{
    [Serializable] public class Job {public string id,policy;public int seed,blocked,manipulationSteps;}
    [Serializable] public class Plan {public string schema,baseSourceSHA;public int horizon;public Job[] jobs;}
    [Serializable] public class AgentRow {public int id,cappedExitStep,approachTicks,approachMoves;public float approachDistance;public bool evacuated;}
    [Serializable] public class Result {public string id,policy,initialStateSHA,termination,instrumentedSourceSHA;public int seed,blocked,manipulationSteps,steps,apiCalls;public float initialTau;public AgentRow[] agents;}
    static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
    static HashSet<int> approaching=new HashSet<int>();
    static string policy;
    public static void NoteApproach(int agent){approaching.Add(agent);}
    static IEnumerator Controlled(PedestrianAgent agent,PaperObstacle obstacle,Decision.VolunteerDecisionContext context,Action<bool?,string,string> callback)
    {callback(policy=="AllHelp" || (policy=="Focal0" && agent.AgentID==0),"Deterministic physical calibration intervention, not an LLM choice","calibration_"+policy);yield break;}
    public static void Run()
    {
        string output=null;SimulationManager m=null;
        try
        {
            string[] args=Environment.GetCommandLineArgs();Func<string,string> opt=n=>{int i=Array.IndexOf(args,n);return i>=0&&i+1<args.Length?args[i+1]:null;};
            output=opt("-physicalOutput");string file=opt("-physicalPlan");
            if(string.IsNullOrEmpty(output)||Directory.Exists(output))throw new Exception("New explicit output required");
            var plan=JsonUtility.FromJson<Plan>(File.ReadAllText(file));
            if(plan.schema!="scenario-physical-calibration-v1"||plan.horizon!=300||plan.jobs.Length!=66)throw new Exception("Plan mismatch");
            Directory.CreateDirectory(output);File.Copy(file,Path.Combine(output,"registered-plan.json"));
            string project=Path.GetDirectoryName(Application.dataPath);string actualSHA=ClosedLoopStudyGuard.ProductionSHA(project);
            int count=0;
            foreach(var job in plan.jobs)
            {
                if(job.seed<71001||job.seed>71006||!new[]{"None","Focal0","AllHelp"}.Contains(job.policy)||!new[]{1,4}.Contains(job.manipulationSteps))throw new Exception("Cell drift");
                policy=job.policy;string folder=Path.Combine(output,job.id);Directory.CreateDirectory(folder);
                var cj=new ClosedLoopJob {id=job.id,seed=job.seed,agents=10,blocked=job.blocked,cv=.05f,policy="OriginalGameTheory"};
                var cp=new ClosedLoopCampaign {phase="Development",horizon=plan.horizon,model="gpt-6-luna",sourceSHA=actualSHA};
                m=ClosedLoopCampaignRunner.Make(cj,cp,folder,output,true);
                m.recordExperimentsAutomatically=false;m.paperManipulationSteps=job.manipulationSteps;m.openAIKey="";
                m.closedLoopBeforeApiRequest=()=>{throw new Exception("API forbidden in physical calibration");};
                ResearchValidation.Begin(m);
                // Override the decision callback only; common movement and placement remain unchanged.
                typeof(PaperModelEngine).GetField("decision",Private).SetValue(m.PaperModel,new PaperDecisionHandler(Controlled));
                float tau=ResearchEnvironment.PaperExitNonBlockage(m.world,new Vector2Int(10,1));
                if(Math.Abs(tau-(1-job.blocked/5f))>1e-6)throw new Exception("Geometry drift");
                File.WriteAllText(Path.Combine(folder,"initial-state.json"),JsonUtility.ToJson(m.closedLoopInitialState,true));
                var rows=m.GetAllAgents().ToDictionary(a=>a.AgentID,a=>new AgentRow {id=a.AgentID,cappedExitStep=300});
                while(m.IsSimulationRunning())
                {
                    var positions=m.GetAllAgents().ToDictionary(a=>a.AgentID,a=>a.gridPos);approaching.Clear();
                    ResearchValidation.Step(m);
                    foreach(var a in m.GetAllAgents())
                    {
                        var row=rows[a.AgentID];
                        if(approaching.Contains(a.AgentID))
                        {
                            row.approachTicks++;var old=positions[a.AgentID];var now=a.gridPos;
                            if(old!=now){row.approachMoves++;row.approachDistance+=PaperGrid.Distance(old,now);}
                        }
                        if(a.IsEvacuated()&&!row.evacuated){row.evacuated=true;row.cappedExitStep=m.GetCurrentStep();}
                    }
                }
                string termination=(string)typeof(SimulationManager).GetField("currentTermination",Private).GetValue(m);
                int calls=(int)typeof(SimulationManager).GetField("llmApiDecisionCallsThisRun",Private).GetValue(m);
                if(calls!=0 || (termination!="completed"&&termination!="timeout"))throw new Exception("Invalid or network execution");
                var result=new Result {id=job.id,policy=job.policy,initialStateSHA=m.closedLoopInitialState.Identity,seed=job.seed,blocked=job.blocked,manipulationSteps=job.manipulationSteps,steps=m.GetCurrentStep(),apiCalls=calls,initialTau=tau,termination=termination,instrumentedSourceSHA=actualSHA,agents=rows.Values.OrderBy(a=>a.id).ToArray()};
                File.WriteAllText(Path.Combine(folder,"physical-result.json"),JsonUtility.ToJson(result,true));
                m.ResetSimulation();m=null;ResearchValidation.Cleanup();count++;
                File.WriteAllText(Path.Combine(output,"progress.txt"),count+"/"+plan.jobs.Length);
            }
            File.WriteAllText(Path.Combine(output,"COMPLETE.json"),"{\"runs\":"+count+",\"apiCalls\":0,\"formalRuns\":0,\"purpose\":\"physical calibration only\"}");
            Debug.Log("PHYSICAL_CALIBRATION_COMPLETE "+count);EditorApplication.Exit(0);
        }
        catch(Exception e)
        {
            if(output!=null&&Directory.Exists(output))File.WriteAllText(Path.Combine(output,"STOPPED.txt"),e.ToString());
            if(m!=null)m.ResetSimulation();ResearchValidation.Cleanup();Debug.LogError(e);EditorApplication.Exit(1);
        }
    }
}
