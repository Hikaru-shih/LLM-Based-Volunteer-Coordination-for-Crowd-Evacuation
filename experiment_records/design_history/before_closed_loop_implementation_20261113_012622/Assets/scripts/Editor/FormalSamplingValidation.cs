using System;
using System.IO;
using System.Linq;
using System.Collections;
using UnityEngine;

public static class FormalSamplingValidation
{
    private static int checks,calls;
    private static void Check(bool pass,string why){checks++;if(!pass)throw new Exception(why);}
    private static void Reject(Action action,string why){bool rejected=false;try{action();}catch(Exception){rejected=true;}Check(rejected && !IndividualSamplingRunner.Running,why);}
    private static IEnumerator Reply(Action<string,string> callback,string provider)
    {callback(IndividualDecisionValidation.Envelope("{\"decision\":\"participate\",\"explanation\":\"Synthetic formal validation only\"}").Replace("offline-personal-fixture",provider),"");yield break;}
    private static LLMDecisionPolicy Client(string provider="offline-provider-v1")
    {var client=new LLMDecisionPolicy("synthetic-not-a-key","offline-analysis-fixture");client.testTransport=(payload,callback)=>{calls++;return Reply(callback,provider);};return client;}
    private static void Drain(){int n=0;while(IndividualSamplingRunner.Running && n++<20000)IndividualSamplingRunner.TickForValidation();Check(!IndividualSamplingRunner.Running,"Runner did not finish");}
    public static void Run()
    {
        checks=calls=0;PayoffDiagnosticSuite.ValidateOffline();
        var args=Environment.GetCommandLineArgs();int i=Array.IndexOf(args,"-formalFixture");if(i<0)throw new ArgumentException("Explicit synthetic fixture required");
        string bundle=Path.GetFullPath(args[i+1]),lockPath=Path.Combine(bundle,"lock.json");
        string output=Path.GetFullPath("tmp/fv_"+Guid.NewGuid().ToString("N").Substring(0,8));Directory.CreateDirectory(output);
        var p=IndividualSamplingRunner.Load(Path.Combine(bundle,"plan.json"));string folder=Path.Combine(output,"capture");
        Reject(()=>IndividualSamplingRunner.Start(p,folder,Client()),"Formal run did not require a lock");
        Reject(()=>IndividualSamplingRunner.Start(p,folder,new LLMDecisionPolicy("synthetic-not-key","offline-analysis-fixture"),studyLockPath:lockPath),"Synthetic lock accepted a client without fake transport");
        Reject(()=>IndividualSamplingRunner.Start(p,folder,studyLockPath:lockPath),"Synthetic lock accepted live mode");
        Reject(()=>IndividualSamplingRunner.Start(p,folder,Client(),sessionChoices:3,studyLockPath:lockPath),"Locked session cap bypassed");
        for(int session=0;session<4;session++)
        {
            IndividualSamplingRunner.Start(p,folder,Client(),sessionChoices:1,studyLockPath:lockPath);Drain();
            Check(calls==session+1,"Resume repeated/skipped completed calls");
            if(session<3)Check(IndividualSamplingRunner.Status.StartsWith("session_choice_limit"),"Session did not pause at choice boundary");
        }
        Check(IndividualSamplingRunner.Status.StartsWith("completed:"),"Final segment did not complete");
        Check(!File.Exists(Path.Combine(folder,"interruptions.jsonl")),"Clean segment invented an interrupted request");
        var lockInfo=JsonUtility.FromJson<IndividualSamplingLock.Document>(File.ReadAllText(lockPath));
        foreach(string file in Directory.GetFiles(Path.Combine(folder,"trials"),"*.json"))
        {var t=JsonUtility.FromJson<IndividualSamplingRunner.Trial>(File.ReadAllText(file));Check(t.valid && t.studyLockID==lockInfo.lockID && t.attempts==0,"Locked trace provenance failed");}
        IndividualSamplingRunner.Start(p,folder,Client(),studyLockPath:lockPath);Drain();Check(calls==4,"Completed resume called provider again");
        string stored=Directory.GetFiles(Path.Combine(folder,"trials"),"*.json")[0];byte[] storedBytes=File.ReadAllBytes(stored);
        try
        {
            var changed=JsonUtility.FromJson<IndividualSamplingRunner.Trial>(File.ReadAllText(stored));changed.response=changed.response.Replace("offline-provider-v1","changed-provider-version");File.WriteAllText(stored,JsonUtility.ToJson(changed,true));
            IndividualSamplingRunner.Start(p,folder,Client(),studyLockPath:lockPath);Drain();Check(calls==4 && IndividualSamplingRunner.Status.StartsWith("invalid_runner"),"Changed stored model accepted on resume");
        }
        finally{File.WriteAllBytes(stored,storedBytes);}
        string bad=Path.Combine(output,"provider_drift");IndividualSamplingRunner.Start(p,bad,Client("wrong-provider-version"),studyLockPath:lockPath);Drain();
        var failed=JsonUtility.FromJson<IndividualSamplingRunner.Trial>(File.ReadAllText(Directory.GetFiles(Path.Combine(bad,"trials"),"*.json").Single()));
        Check(!failed.valid && failed.error=="provider_model_drift","Provider drift became an accepted choice");
        byte[] design=File.ReadAllBytes(Path.Combine(bundle,"design.json"));
        try{File.AppendAllText(Path.Combine(bundle,"design.json")," ");Reject(()=>IndividualSamplingRunner.Start(p,Path.Combine(output,"tamper"),Client(),studyLockPath:lockPath),"Changed artifact accepted");}
        finally{File.WriteAllBytes(Path.Combine(bundle,"design.json"),design);}
        byte[] original=File.ReadAllBytes(lockPath);
        try
        {
            var altered=JsonUtility.FromJson<IndividualSamplingLock.Document>(File.ReadAllText(lockPath));altered.sourceFiles[0].sha256=new string('0',64);altered.lockID=IndividualSamplingLock.Identity(altered);File.WriteAllText(lockPath,JsonUtility.ToJson(altered,true));
            Reject(()=>IndividualSamplingRunner.Start(p,Path.Combine(output,"source_change"),Client(),studyLockPath:lockPath),"Changed source digest accepted");
        }
        finally{File.WriteAllBytes(lockPath,original);}
        Check(IndividualSamplingLock.Verify(lockPath,p,true).lockID==lockInfo.lockID,"Python/C# lock identity mismatch");
        File.WriteAllText(Path.Combine(output,"result.json"),"{\"passed\":true,\"checks\":"+checks+",\"syntheticCalls\":"+calls+",\"remoteRequests\":0}");
        File.WriteAllText("tmp/formal-validation-latest.txt",output);Debug.Log("FORMAL_SAMPLING_VALIDATION_PASSED: "+checks+" checks; zero API");
        IndividualSamplingValidation.Run();
    }
}
