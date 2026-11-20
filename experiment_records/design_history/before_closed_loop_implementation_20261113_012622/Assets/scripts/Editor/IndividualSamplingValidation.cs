using System;
using System.IO;
using System.Linq;
using System.Collections;
using UnityEngine;

public static class IndividualSamplingValidation
{
    private static int checks;
    private static void Check(bool pass,string why){checks++;if(!pass)throw new Exception(why);}
    private static void Reject(Action call,string why){bool rejected=false;try{call();}catch(ArgumentException){rejected=true;}catch(InvalidDataException){rejected=true;}Check(rejected,why);}
    private static IEnumerator Reply(Action<string,string> callback,string response){callback(response,"");yield break;}
    private static IEnumerator Pending(Action<string,string> callback){while(true)yield return null;}
    private static LLMDecisionPolicy Client(Action onCall=null,bool invalid=false,bool pending=false,bool cooperate=false)
    {
        var p=new LLMDecisionPolicy("synthetic-no-network","offline-sampling-fixture");
        p.testTransport=(payload,callback)=>{onCall?.Invoke();return pending ? Pending(callback):Reply(callback,IndividualDecisionValidation.Envelope(invalid ? "{}":"{\"decision\":\""+(cooperate?"participate":"decline_assistance")+"\",\"explanation\":\"Synthetic validation only\"}"));};return p;
    }
    private static void Drain(){int ticks=0;while(IndividualSamplingRunner.Running && ticks++<10000)IndividualSamplingRunner.TickForValidation();Check(!IndividualSamplingRunner.Running,"Runner hung");}
    private static IndividualSamplingRunner.Plan Plan()=>new IndividualSamplingRunner.Plan {model="offline-sampling-fixture",repetitions=2,maxHttpAttempts=12,scenarios=new[]{
        new IndividualSamplingRunner.Scenario {id="one",nearbyAgentCount=1,exitNonBlockage=0},
        new IndividualSamplingRunner.Scenario {id="many",nearbyAgentCount=4},
        new IndividualSamplingRunner.Scenario {id="no_game",nearbyAgentCount=0}}};
    public static void Run()
    {
        checks=0;
        string legacy=PersonalDecisionProtocol.Payload("gpt-4o-mini","{}","Core",AgentPromptWording.Standard);
        string luna=PersonalDecisionProtocol.Payload("gpt-6-luna","{}","Core",AgentPromptWording.Standard);
        Check(!legacy.Contains("reasoning_effort") && legacy.Contains("\"max_tokens\":220"),"Legacy request changed");
        Check(luna.Contains("\"reasoning_effort\":\"none\"") && luna.Contains("\"max_completion_tokens\":220") && !luna.Contains("\"max_tokens\":"),"Luna request profile invalid");
        Check(PersonalDecisionProtocol.TransportPayload("gpt-6-luna",luna)==luna,"Luna profile not idempotent");
        string root=Path.GetFullPath("tmp/individual-sampling-validation/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff"));Directory.CreateDirectory(root);
        var p=Plan();Check(IndividualSamplingRunner.Order(p).SequenceEqual(IndividualSamplingRunner.Order(p)),"Order not deterministic");
        string planFile=Path.Combine(root,"valid_plan.json");File.WriteAllText(planFile,JsonUtility.ToJson(p,true));Check(IndividualSamplingRunner.Load(planFile).scenarios.Length==3,"Valid saved plan failed to load");
        Check(IndividualSamplingRunner.Order(p).Distinct().Count()==6,"Schedule repeats/omits trial");
        var invalid=Plan();invalid.scenarios[0].volunteerCost=.6f;Reject(()=>IndividualSamplingRunner.Validate(invalid),"Bad payoff accepted");
        invalid=Plan();invalid.scenarios[1].id="one";Reject(()=>IndividualSamplingRunner.Validate(invalid),"Duplicate IDs accepted");
        string malformed=Path.Combine(root,"bad.json");File.WriteAllText(malformed,JsonUtility.ToJson(p).Replace("\"repetitions\":2","\"repetitions\":2,\"repetitions\":3"));Reject(()=>IndividualSamplingRunner.Load(malformed),"Duplicate plan key accepted");
        File.WriteAllText(malformed,System.Text.RegularExpressions.Regex.Replace(JsonUtility.ToJson(p),"\"volunteerCost\":[0-9.]+","\"volunteerCost\":-1e-60"));Reject(()=>IndividualSamplingRunner.Load(malformed),"Tiny invalid cost accepted");
        int calls=0;string complete=Path.Combine(root,"complete");IndividualSamplingRunner.Start(p,complete,Client(()=>calls++));Drain();
        Check(calls==4,"No-game dispatch or missing individual choice");
        Check(Directory.GetFiles(Path.Combine(complete,"trials"),"*.json").Length==6,"Missing saved trials");
        foreach(string file in Directory.GetFiles(Path.Combine(complete,"trials"),"*.json"))
        {
            var t=JsonUtility.FromJson<IndividualSamplingRunner.Trial>(File.ReadAllText(file));
            if(t.kind=="NoGame")Check(t.execution=="no_game" && !t.valid,"No-game became response");
            else Check(t.valid && !t.willing && t.execution=="synthetic_test" && t.attempts==0,"Synthetic choice/audit incorrect");
        }
        IndividualSamplingRunner.Start(p,complete,Client(()=>calls++));Drain();Check(calls==4,"Resume repeated saved trials");
        Reject(()=>IndividualSamplingRunner.Start(p,complete),"Synthetic/live outputs mixed");
        string positive=Path.Combine(root,"positive");IndividualSamplingRunner.Start(p,positive,Client(cooperate:true));Drain();
        Check(Directory.GetFiles(Path.Combine(positive,"trials"),"*.json").Select(f=>JsonUtility.FromJson<IndividualSamplingRunner.Trial>(File.ReadAllText(f))).Count(t=>t.valid && t.willing)==4,"Participation conversion failed");
        string customRecords=Path.GetFullPath(Path.Combine("tmp","p5-records-"+Guid.NewGuid().ToString("N").Substring(0,8)));
        File.WriteAllText(Path.Combine(root,"custom_records_path.txt"),customRecords);
        IndividualSamplingRunner.Start(p,Path.Combine(root,"custom_notebook"),Client(),credentialRoot:Path.Combine(root,"nonexistent_credentials"),recordsRoot:customRecords);Drain();
        Check(File.Exists(Path.Combine(customRecords,"EXPERIMENT_LOG.md")) && Directory.GetFiles(Path.Combine(customRecords,"assessments"),"*.json").Length==1,"Custom notebook root did not receive sampling assessment");
        var changed=Plan();changed.scenarios[0].failureCost=.6f;Reject(()=>IndividualSamplingRunner.Prepare(changed,complete),"Changed plan resumed");
        var limited=Plan();limited.maxHttpAttempts=3;string budget=Path.Combine(root,"budget");int bounded=0;
        IndividualSamplingRunner.Start(limited,budget,Client(()=>bounded++));Drain();Check(bounded==1 && IndividualSamplingRunner.Status.StartsWith("budget_exhausted"),"Budget exceeded");
        IndividualSamplingRunner.Start(limited,budget,Client(()=>bounded++));Drain();Check(bounded==1,"Resume reset budget");
        string interrupted=Path.Combine(root,"interrupted");int started=0;IndividualSamplingRunner.Start(p,interrupted,Client(()=>started++,pending:true));
        for(int tick=0;tick<100 && started==0;tick++)IndividualSamplingRunner.TickForValidation();IndividualSamplingRunner.Cancel();
        Check(started==1 && File.Exists(Path.Combine(interrupted,"interruptions.jsonl")),"In-flight interruption not preserved");
        IndividualSamplingRunner.Start(p,interrupted,Client());Drain();Check(IndividualSamplingRunner.Status.StartsWith("budget_exhausted"),"Interrupted reservation lost");
        string bad=Path.Combine(root,"invalid_response");IndividualSamplingRunner.Start(p,bad,Client(invalid:true));Drain();Check(IndividualSamplingRunner.Status.StartsWith("stopped_invalid_response"),"Invalid response not stopped");
        string trial=Directory.GetFiles(Path.Combine(complete,"trials"),"*.json").First(f=>File.ReadAllText(f).Contains("synthetic_test"));
        string original=File.ReadAllText(trial);File.WriteAllText(trial,original.Replace("\"willing\": false","\"willing\": true"));
        IndividualSamplingRunner.Start(p,complete,Client());Drain();Check(IndividualSamplingRunner.Status.StartsWith("invalid_runner"),"Tampered resume accepted");File.WriteAllText(trial,original);
        IndividualDecisionValidation.Run();
        File.WriteAllText(Path.Combine(root,"result.json"),"{\"passed\":true,\"checks\":"+checks+",\"remoteRequests\":0}");
        File.WriteAllText("tmp/individual-sampling-validation/latest.txt",root);Debug.Log("INDIVIDUAL_SAMPLING_VALIDATION_PASSED: "+checks+" offline checks, zero API");
    }
}

