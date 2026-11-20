using System;
using System.IO;
using UnityEditor;
using UnityEngine;

// Validates the actual API bundle without constructing a client, reading a key or running a scene.
public static class FormalSamplingPreflight
{
    public static void Run()
    {
        try
        {
            var args=Environment.GetCommandLineArgs();
            Func<string,string> option=name=>{int i=Array.IndexOf(args,name);return i>=0 && i+1<args.Length?args[i+1]:null;};
            string path=option("-studyLock"), output=option("-preflightOutput");
            if(string.IsNullOrWhiteSpace(path) || string.IsNullOrWhiteSpace(output))throw new ArgumentException("Explicit lock/output required");
            if(File.Exists(output))throw new IOException("Keep previous preflight evidence");
            var plan=IndividualSamplingRunner.Load(Path.Combine(Path.GetDirectoryName(path),"plan.json"));
            var locked=IndividualSamplingLock.Verify(path,plan,false);
            int count=IndividualSamplingRunner.Order(plan).Length;
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)));
            File.WriteAllText(output,"{\"passed\":true,\"remoteRequests\":0,\"sceneSteps\":0,\"records\":"+count+",\"lockID\":\""+locked.lockID+"\"}");
            Debug.Log("FORMAL_PREFLIGHT_PASSED: "+count+" planned records; zero API/scene steps");
            EditorApplication.Exit(0);
        }
        catch(Exception error)
        {
            Debug.LogError("FORMAL_PREFLIGHT_FAILED: "+error.GetType().Name+": "+error.Message);
            EditorApplication.Exit(1);
        }
    }
}
