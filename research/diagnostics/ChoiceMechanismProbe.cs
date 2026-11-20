using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// Separate prompt/known-belief diagnostic. Never alters the production prompt or policy.
public static class ChoiceMechanismProbe
{
    [Serializable] public class Trial {public string id,condition,payload;public int repetition;}
    [Serializable] public class Plan {public string schema,model;public int maxHttpAttempts;public Trial[] trials;}
    [Serializable] public class Record {public string id,condition,payload,response,error,explanation;public int repetition,attempts;public bool valid,willing;public long httpStatus;public LLMDecisionPolicy.AttemptAudit[] attemptAudit;}
    [Serializable] public class Status {public string outcome,error;public int saved,total,httpAttempts;}
    private static Plan plan;private static string output,key;
    private static int saved,http;private static bool done;private static double deadline;
    private static readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();private static AsyncOperation waiting;
    public static void Run()
    {
        try
        {
            var args=Environment.GetCommandLineArgs();Func<string,string> option=name=>{int i=Array.IndexOf(args,name);return i>=0 && i+1<args.Length?args[i+1]:null;};
            output=option("-diagnosticOutput");string file=option("-diagnosticPlan"),root=option("-credentialRoot");
            if(string.IsNullOrEmpty(output)||string.IsNullOrEmpty(file)||string.IsNullOrEmpty(root)||Directory.Exists(output))throw new ArgumentException("Explicit plan, key root and new output required");
            plan=JsonUtility.FromJson<Plan>(File.ReadAllText(file));
            if(plan.schema!="choice-mechanism-diagnostic-v1"||plan.model!="gpt-6-luna"||plan.trials.Length!=50||plan.maxHttpAttempts!=150||plan.trials.Select(t=>t.id).Distinct().Count()!=50)throw new ArgumentException("Unexpected registration");
            Directory.CreateDirectory(output);Directory.CreateDirectory(Path.Combine(output,"trials"));File.Copy(file,Path.Combine(output,"registered-plan.json"));
            key=File.ReadAllText(Path.Combine(root,"openai-key.local.txt")).Trim().TrimStart('\uFEFF');
            if(!LocalOpenAIKey.HasValidLocalFormat(key))throw new ArgumentException("Invalid local credential format");
            stack.Push(Cases());deadline=EditorApplication.timeSinceStartup+600;EditorApplication.update+=Tick;
        }
        catch(Exception e){Finish(e);}
    }
    private static IEnumerator Cases()
    {
        foreach(var trial in plan.trials)
        {
            if(http+3>plan.maxHttpAttempts)throw new Exception("Registered request ceiling");
            var client=new LLMDecisionPolicy(key,plan.model);client.ResetRequestAudit();string raw=null,error="";
            var send=typeof(LLMDecisionPolicy).GetMethod("SendPayloadWithRetry",BindingFlags.NonPublic|BindingFlags.Instance);
            yield return (IEnumerator)send.Invoke(client,new object[]{trial.payload,new Action<string>(v=>raw=v),new Action<string>(v=>error=v)});
            LLMDecisionPolicy.DecisionResult decision=null;string validation="";
            bool valid=raw!=null && PersonalDecisionProtocol.Response(raw,out decision,out validation);
            if(valid && JsonUtility.FromJson<LLMDecisionPolicy.ChatResponse>(raw).model!=plan.model){valid=false;validation="provider_model_drift";}
            var record=new Record {id=trial.id,condition=trial.condition,repetition=trial.repetition,payload=client.LastPayload,response=client.LastResponse,
                error=valid?"":string.IsNullOrEmpty(error)?validation:error,explanation=decision?.explanation,valid=valid,willing=valid && decision.decision=="participate",
                attempts=client.LastAttempts,httpStatus=client.LastHttpStatus,attemptAudit=client.LastAttemptAudit};
            File.WriteAllText(Path.Combine(output,"trials",trial.id+".json"),JsonUtility.ToJson(record,true));saved++;http+=record.attempts;
            File.WriteAllText(Path.Combine(output,"progress.json"),JsonUtility.ToJson(new Status {outcome=valid?"running":"invalid_response",saved=saved,total=plan.trials.Length,httpAttempts=http},true));
            if(!valid)throw new Exception("Diagnostic transport/schema failure; preserve raw response");
        }
        done=true;
    }
    private static void Tick()
    {
        try
        {
            if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException("Diagnostic wall-clock ceiling");
            if(waiting!=null){if(!waiting.isDone)return;waiting=null;}
            if(stack.Count==0){Finish(done?null:new Exception("Unexpected empty stack"));return;}
            var routine=stack.Peek();if(!routine.MoveNext()){stack.Pop();return;}
            if(routine.Current is IEnumerator nested)stack.Push(nested);else if(routine.Current is AsyncOperation operation)waiting=operation;
        }
        catch(Exception e){Finish(e);}
    }
    private static void Finish(Exception error)
    {
        EditorApplication.update-=Tick;while(stack.Count>0){try{(stack.Pop() as IDisposable)?.Dispose();}catch{}}
        if(output!=null && Directory.Exists(output))File.WriteAllText(Path.Combine(output,"summary.json"),JsonUtility.ToJson(new Status {outcome=error==null?"completed":"stopped",error=error?.ToString(),saved=saved,total=plan?.trials?.Length??0,httpAttempts=http},true));
        if(error!=null)Debug.LogError("CHOICE_MECHANISM_PROBE_STOPPED: "+error);else Debug.Log("CHOICE_MECHANISM_PROBE_COMPLETED: "+saved+" valid records");
        EditorApplication.Exit(error==null?0:1);
    }
}
