using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

// Exercises the actual FinalTest lock and all group/calibration branches without a simulation step.
public static class ClosedLoopFinalPreflight
{
    public static void Run()
    {
        try
        {
            var args=Environment.GetCommandLineArgs();Func<string,string> option=n=>{int i=Array.IndexOf(args,n);return i>=0&&i+1<args.Length?args[i+1]:null;};
            string path=option("-groupLock"),output=option("-preflightOutput"),root=option("-credentialRoot");
            if(string.IsNullOrEmpty(output)||Directory.Exists(output))throw new Exception("New explicit preflight output required");
            var locked=ClosedLoopStudyGuard.Verify(path);string bundle=Path.GetDirectoryName(Path.GetFullPath(path));
            var p=JsonUtility.FromJson<ClosedLoopCampaign>(File.ReadAllText(Path.Combine(bundle,"formal-plan.json")));
            if(p.phase!="FinalTest"||p.paidFinalExecutionByDefault)throw new Exception("Invalid final defaults");
            Directory.CreateDirectory(output);int first=p.jobs.Min(j=>j.seed),last=p.jobs.Max(j=>j.seed),count=0;
            foreach(var job in p.jobs.Where(j=>j.seed==first||j.seed==last))
            {
                string folder=Path.Combine(output,job.id);Directory.CreateDirectory(folder);
                var m=ClosedLoopCampaignRunner.Make(job,p,folder,root,true,path);m.recordExperimentsAutomatically=false;
                ResearchValidation.Begin(m);
                if(!m.closedLoopZeroStepValidation || m.closedLoopInitialState.Identity!=job.initialStateSHA)throw new Exception("Zero-step state drift");
                typeof(SimulationManager).GetMethod("ExportFinishedRun",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(m,new object[]{"formal_zero_step_preflight"});
                m.ResetSimulation();ResearchValidation.Cleanup();count++;
            }
            if(Directory.Exists(Path.Combine(root,"experiment_records","group_execution",locked.lockID,"claims")))throw new Exception("Final jobs were claimed during preparation");
            File.WriteAllText(Path.Combine(output,"result.json"),"{\"passed\":true,\"lockID\":\""+locked.lockID+"\",\"cases\":"+count+",\"remoteRequests\":0,\"simulationSteps\":0,\"formalJobsClaimed\":0}");
            Debug.Log("CLOSED_LOOP_FINAL_PREFLIGHT_PASSED: "+count+" actual lock/initialization cases, zero requests/steps/claims");EditorApplication.Exit(0);
        }
        catch(Exception e){ResearchValidation.Cleanup();Debug.LogError(e);EditorApplication.Exit(1);}
    }
}
