using System;
using System.IO;
using UnityEditor;
using UnityEngine;

// Explicit entry point only. Never runs merely by loading the project.
public static class IndividualSamplingBatch
{
    public static void Run()
    {
        try
        {
            var args=Environment.GetCommandLineArgs();
            Func<string,string> option=name=>{int i=Array.IndexOf(args,name);return i>=0 && i+1<args.Length?args[i+1]:null;};
            string plan=option("-samplingPlan"),output=option("-samplingOutput");
            if(string.IsNullOrWhiteSpace(plan) || string.IsNullOrWhiteSpace(output))throw new ArgumentException("Explicit plan/output required");
            IndividualSamplingRunner.Start(IndividualSamplingRunner.Load(plan),output,credentialRoot:option("-credentialRoot"),recordsRoot:option("-recordsRoot"),sessionChoices:int.Parse(option("-sessionChoices")??"0"),studyLockPath:option("-studyLock"));
            EditorApplication.update+=ExitWhenDone;
        }
        catch(Exception error)
        {
            Debug.LogWarning("[SAMPLING BATCH] Preflight failed: "+error.GetType().Name);
            EditorApplication.Exit(1);
        }
    }
    private static void ExitWhenDone()
    {
        if(IndividualSamplingRunner.Running)return;
        EditorApplication.update-=ExitWhenDone;
        Debug.Log("[SAMPLING BATCH] "+IndividualSamplingRunner.Status+". Data: "+IndividualSamplingRunner.Output);
        EditorApplication.Exit((IndividualSamplingRunner.Status.StartsWith("completed:",StringComparison.Ordinal) || IndividualSamplingRunner.Status.StartsWith("session_choice_limit:",StringComparison.Ordinal))?0:1);
    }
}
