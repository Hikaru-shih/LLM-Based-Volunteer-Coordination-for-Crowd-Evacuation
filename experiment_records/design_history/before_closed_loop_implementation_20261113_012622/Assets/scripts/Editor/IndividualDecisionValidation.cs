using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

public static class IndividualDecisionValidation
{
    private static int checks;private static string output;
    private static void Check(bool ok,string why){checks++;if(!ok)throw new Exception(why);}
    private static void Drain(IEnumerator value){while(value.MoveNext())if(value.Current is IEnumerator nested)Drain(nested);}
    public static string Envelope(string content,string finish="stop",string refusal=null)
    {
        string message=JsonUtility.ToJson(new LLMDecisionPolicy.LLMMessage("assistant",content));
        if(refusal!=null)message=message.Substring(0,message.Length-1)+",\"refusal\":"+JsonUtility.ToJson(new TextValue {value=refusal}).Substring(9).TrimEnd('}')+"}";
        return "{\"model\":\"offline-personal-fixture\",\"choices\":[{\"finish_reason\":\""+finish+"\",\"message\":"+message+"}]}";
    }
    [Serializable] private sealed class TextValue {public string value;}
    private static string Choice(string action="participate") => JsonUtility.ToJson(new LLMDecisionPolicy.DecisionResult {decision=action,explanation="Synthetic fixture, not a model measurement."});
    private static Decision.VolunteerDecisionContext Context(int n=2,float tau=.5f) => new Decision.VolunteerDecisionContext {nearbyAgentCount=n,exitNonBlockage=tau,volunteerCost=.005f,failureCost=.5f,unwillingness=5};
    private static LLMDecisionPolicy.VolunteerContext Request(int n=2,float tau=.5f) => new LLMDecisionPolicy.VolunteerContext {sharedObservationJson=AgentObservation.Serialize(Context(n,tau),AgentInformationCondition.Core),informationCondition="Core"};
    private static IEnumerator Reply(Action<string,string> callback,string body,string error=""){callback(body,error);yield break;}
    private static void Protocol()
    {
        LLMDecisionPolicy.DecisionResult result;string error;
        foreach(string action in new[]{"participate","decline_assistance"})Check(PersonalDecisionProtocol.Response(Envelope(Choice(action)),out result,out error) && result.decision==action,"Valid personal response rejected");
        string good=Choice();
        foreach(string bad in new[]{"", "{}", "null", "[]", "```json\n"+good+"\n```", "prose "+good,good+" trailing",good+good,
            "{\"decision\":\"participate\"}","{\"decision\":\"participate\",\"explanation\":null}",
            "{\"decision\":false,\"explanation\":\"x\"}","{\"decision\":\"participate\",\"explanation\":{}}",
            "{\"decision\":\"participate\",\"explanation\":\"x\",}",
            "{\"decision\":\"participate\",\"decision\":\"decline_assistance\",\"explanation\":\"x\"}",
            "{\"decision\":\"participate\",\"dec\\u0069sion\":\"participate\",\"explanation\":\"x\"}",
            good.Replace("\"explanation\":","\"extra\":1,\"explanation\":"),
            "{\"decision\":\"participate\",\"explanation\":\"\\ud800\"}"})
            Check(!PersonalDecisionProtocol.Content(bad,out result,out error),"Malformed choice accepted");
        foreach(string action in new[]{"volunteer","selfish","continue_evacuation","PARTICIPATE"," participate",""})
            Check(!PersonalDecisionProtocol.Content(Choice(action),out result,out error),"Legacy/unknown action accepted");
        foreach(string finish in new[]{"length","content_filter","tool_calls","function_call",""})
            Check(!PersonalDecisionProtocol.Response(Envelope(good,finish),out result,out error) && error=="incomplete_response","Incomplete response salvaged");
        Check(!PersonalDecisionProtocol.Response(Envelope(good,refusal:"Refused."),out result,out error) && error=="provider_refusal","Refusal treated as choice");
        foreach(string body in new[]{"{}","not-json",Envelope(good).Replace("\"assistant\"","\"user\""),Envelope(good).Replace("\"choices\":[","\"choices\":[],\"choices\":["),
            Envelope(good).Replace("\"stop\"","null"),Envelope(good).Replace("\"message\":","\"message\":null,\"message\":"),
            "{\"choices\":[{\"finish_reason\":\"stop\",\"message\":{\"role\":\"assistant\",\"content\":[]}}]}"})
            Check(!PersonalDecisionProtocol.Response(body,out result,out error),"Invalid envelope accepted");
        Dictionary<string,object> json;
        Check(!StrictJson.TryObject("{\"x\":01}",out json) && !StrictJson.TryObject("{\"x\":NaN}",out json) && !StrictJson.TryObject("{\"x\":1e999}",out json),"Non-JSON number accepted");
        Check(StrictJson.TryObject("{\"x\":-1.25e2,\"a\":[true,false,null,\"\\ud83d\\ude00\"]}",out json),"Valid JSON grammar rejected");
        Check(PersonalDecisionProtocol.Content("{\"explanation\":\"\",\"decision\":\"decline_assistance\"}",out result,out error),"Empty explanation or property order changed action validity");
        string payload=PersonalDecisionProtocol.Payload("offline-personal-fixture",Request().sharedObservationJson,"Core",AgentPromptWording.Standard);
        Check(StrictJson.TryObject(payload,out json) && payload.Contains("\"strict\":true") && payload.Contains("paper-agent-v5") && !payload.Contains("exp(") && !payload.Contains("Authorization"),"Payload schema/version/no-answer-leak failed");
        Check(PersonalDecisionProtocol.Version=="paper-choice-response-v3" && !PersonalDecisionProtocol.ResponseFormat.Contains("\"enum\"") && PersonalDecisionProtocol.ResponseFormat.Contains("\"type\":\"string\""),"v3 schema contract changed");
        Check(PersonalDecisionProtocol.ResponseFormat.IndexOf("\"explanation\"")<PersonalDecisionProtocol.ResponseFormat.IndexOf("\"decision\""),"v3 schema must request explanation before action");
        File.WriteAllText(Path.Combine(output,"payload.json"),payload);
    }
    private static void CasesAndClient()
    {
        bool rule;Check(PaperDecisionSpecification.Classify(Context(1,0),out rule)==PaperDecisionSpecification.DecisionKind.ReferenceBoundary && rule,"Single fully blocked rule");
        Check(PaperDecisionSpecification.Classify(Context(1,.5f),out rule)==PaperDecisionSpecification.DecisionKind.ReferenceBoundary && !rule,"Single partial blockage rule");
        Check(PaperDecisionSpecification.Classify(Context(0,0),out rule)==PaperDecisionSpecification.DecisionKind.NoGame,"Zero players rule");
        Check(PaperDecisionSpecification.Classify(Context(2,1),out rule)==PaperDecisionSpecification.DecisionKind.NoGame,"Unblocked gate");
        Check(PaperDecisionSpecification.Classify(Context(2,0),out rule)==PaperDecisionSpecification.DecisionKind.Choice,"Full blockage incorrectly forced LLM action");
        var policy=new LLMDecisionPolicy("synthetic-no-network","offline-personal-fixture");int calls=0;
        policy.testTransport=(payload,callback)=>{calls++;return Reply(callback,Envelope(Choice()));};
        foreach(var request in new[]{Request(1,0),Request(1,.5f)})
        {Drain(policy.RequestVolunteerDecision(request,(action,why)=>{}));Check(policy.LastRequestSucceeded && policy.LastExecution=="synthetic_test" && policy.LastPayload!="" && policy.LastAttempts==0,"Single-player autonomous request failed");}
        policy.testTransport=(payload,callback)=>Reply(callback,Envelope(Choice("decline_assistance")));
        VolunteerDilemma.CooperationLevel selected=default;
        Drain(policy.RequestVolunteerDecision(Request(1,0),(action,why)=>selected=action));
        Check(policy.LastRequestSucceeded && selected==VolunteerDilemma.CooperationLevel.Selfish,"Single-player refusal overridden by reference rule");
        policy.testTransport=(payload,callback)=>{calls++;return Reply(callback,Envelope(Choice()));};
        foreach(var request in new[]{Request(0,0),Request(2,1)})
        {Drain(policy.RequestVolunteerDecision(request,(action,why)=>{}));Check(!policy.LastRequestSucceeded && policy.LastRequestError=="no_game_state","No-game state became model decision");}
        Check(calls==2,"No-game gate called transport");
        Drain(policy.RequestVolunteerDecision(Request(),(action,why)=>{}));Check(policy.LastRequestSucceeded && policy.LastExecution=="synthetic_test" && calls==3 && policy.LastAttempts==0,"Synthetic success failed");
        foreach(string body in new[]{"{}",Envelope(Choice(),"length"),Envelope(Choice(),refusal:"refusal")})
        {policy.testTransport=(payload,callback)=>Reply(callback,body);Drain(policy.RequestVolunteerDecision(Request(),(action,why)=>{}));Check(!policy.LastRequestSucceeded && policy.LastRequestError!="","Bad response retained successful status");}
        policy.testTransport=(payload,callback)=>Reply(callback,null,"http_429_rate_limit_exceeded");
        Drain(policy.RequestVolunteerDecision(Request(),(action,why)=>{}));Check(policy.LastRequestError=="http_429_rate_limit_exceeded" && !policy.LastRequestSucceeded,"Transport failure hidden");
        var missing=new LLMDecisionPolicy("");Drain(missing.RequestVolunteerDecision(Request(),(action,why)=>{}));Check(!missing.LastRequestSucceeded && missing.LastRequestError=="missing_api_key" && missing.LastAttempts==0,"Missing key not separated");
        Drain(policy.RequestVolunteerDecision(null,(action,why)=>{}));Check(policy.LastRequestError=="invalid_observation" && policy.LastPayload=="","Null request/stale audit");
        var malformed=Request();malformed.sharedObservationJson="{\"nearbyAgentCount\":2}";
        Drain(policy.RequestVolunteerDecision(malformed,(action,why)=>{}));Check(policy.LastRequestError=="invalid_observation","Incomplete observation sent");
        foreach(string field in new[]{"exitNonBlockage","unwillingness"})
        {
            Decision.VolunteerDecisionContext c;
            string json=Request().sharedObservationJson;
            string invalid=field=="exitNonBlockage"?json.Replace("\"exitNonBlockage\":0.5","\"exitNonBlockage\":-1e-60"):json.Replace("\"unwillingness\":5","\"unwillingness\":-1e-60");
            Check(invalid!=json && !PaperDecisionSpecification.Observation(invalid,"Core",out c),"Tiny negative input rounded into valid domain");
        }
    }
    private static void Journal()
    {
        string path=Path.Combine(output,"synthetic_journal.jsonl"),obs=Request().sharedObservationJson,payload=PersonalDecisionProtocol.Payload("offline-personal-fixture",obs,"Core",AgentPromptWording.Standard),hash=PaperVolunteerPrompt.Hash("Core",AgentPromptWording.Standard);
        var journal=new PaperAgentDecisionJournal();journal.Record(path,1,2,3,obs,true,"Synthetic fixture, not a model measurement.",true,"offline-personal-fixture",payload,Envelope(Choice()),0,0,"condition",promptHash:hash,execution:"synthetic_test");
        Check(!new PaperAgentDecisionJournal().ReplayFullyConsumed(Path.Combine(output,"nonexistent-trace.jsonl")),"Missing replay treated as fully consumed");
        bool willing;string why,error;
        Check(!journal.TryReplay(path,1,2,3,obs,out willing,out why,out error,"condition","offline-personal-fixture","wrong-hash",payload),"Prompt mismatch replayed");
        Check(!journal.TryReplay(path,1,2,3,obs,out willing,out why,out error,"condition","offline-personal-fixture",hash,"changed-payload"),"Payload mismatch replayed");
        Check(journal.TryReplay(path,1,2,3,obs,out willing,out why,out error,"condition","offline-personal-fixture",hash,payload) && willing && journal.ReplayFullyConsumed(path),"Exact replay failed");
        var entry=JsonUtility.FromJson<PaperAgentDecisionJournal.Entry>(File.ReadAllLines(path)[0]);
        foreach(string change in new[]{"old_version","wrong_willingness","truncation"})
        {
            var value=JsonUtility.FromJson<PaperAgentDecisionJournal.Entry>(JsonUtility.ToJson(entry));
            if(change=="old_version")value.promptVersion="paper-agent-v3";
            if(change=="wrong_willingness")value.willing=false;
            if(change=="truncation")value.response=Envelope(Choice(),"length");
            string changed=Path.Combine(output,change+".jsonl");File.WriteAllText(changed,JsonUtility.ToJson(value)+Environment.NewLine);
            Check(!new PaperAgentDecisionJournal().TryReplay(changed,1,2,3,obs,out willing,out why,out error),"Unvalidated trace replayed: "+change);
        }
    }
    private static string Fixture(string name,int agents,string response,string expected,string replay="",bool matched=false)
    {
        string folder=Path.Combine(output,name);var make=typeof(LocalCoordinationValidation).GetMethod("Make",BindingFlags.Static|BindingFlags.NonPublic);
        var m=(SimulationManager)make.Invoke(null,new object[]{folder,ResearchScenario.SingleBlockedExit,2026});m.agentCount=agents;
        m.paperExecutionMode=Coordination.ExecutionMode.PaperReference;m.coordinationAvailability=Coordination.AvailabilityMode.PolicyWillingness;
        m.volunteerDecisionMode=SimulationManager.VolunteerDecisionMode.LLM;m.openAIModel="offline-personal-fixture";m.openAIKey="synthetic-no-network";m.paperDecisionReplayPath=replay;
        if(matched)
        {
            Directory.CreateDirectory(folder);m.volunteerDecisionMode=SimulationManager.VolunteerDecisionMode.RandomMatched;
            m.cooperationCalibrationPath=Path.Combine(folder,"synthetic_calibration.json");
            File.WriteAllText(m.cooperationCalibrationPath,JsonUtility.ToJson(new CooperationCalibration {schema="cooperation-calibration-v1",split="Calibration",calibrationID="synthetic-not-empirical",
                conditionKey=m.AgentConditionKey,model=m.openAIModel,informationCondition="Core",promptVersion=PaperVolunteerPrompt.Version,decisions=1,probability=0,seeds=new[]{987654},sourceHashes=new[]{"synthetic-contract"}}));
        }
        int calls=0;
        try
        {
            ResearchValidation.Begin(m);var policy=new LLMDecisionPolicy("synthetic-no-network","offline-personal-fixture");
            policy.testTransport=(payload,callback)=>{calls++;return Reply(callback,response);};
            typeof(SimulationManager).GetField("llmDecisionPolicy",BindingFlags.Instance|BindingFlags.NonPublic).SetValue(m,policy);
            while(m.IsSimulationRunning())ResearchValidation.Step(m);
            string total=File.ReadAllText(Directory.GetFiles(folder,"*_global.csv").Single());Check(total.Contains(","+expected+","),"Unexpected runtime outcome "+name);
            if(matched)Check(calls==0 && !Directory.GetFiles(folder,"*_agent_trace.jsonl").Any(),"RandomMatched queried a model");
            else if(string.IsNullOrEmpty(replay))Check(calls>0,"No personal transport path exercised");
            else Check(calls==0,"Replay called transport");
            if(expected!="completed")Check(!m.PaperModel.Reservations.Entries.Any() && m.PaperModel.Manipulations==0,"Invalid response changed assignment/physics");
        }
        finally{m.ResetSimulation();ResearchValidation.Cleanup();}
        return folder;
    }
    public static void Run()
    {
        checks=0;output=Path.GetFullPath("tmp/individual-p1-validation/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff"));Directory.CreateDirectory(output);
        Protocol();CasesAndClient();Journal();PaperDecisionSpecificationValidation.Run();LLMComprehensionValidation.Run();
        Fixture("single_autonomous",1,Envelope(Choice()),"completed");
        Fixture("matched_no_override",1,"{}","timeout",matched:true);
        string capture=Fixture("synthetic_capture",2,Envelope(Choice()),"completed");
        string replay=Fixture("strict_replay",2,"{}","completed",Directory.GetFiles(capture,"*_agent_trace.jsonl").Single());
        foreach(string suffix in new[]{"_trajectories.csv","_obstacles.csv","_obstacle_events.csv","_volunteer_work.csv","_diagnostics.csv"})
            Check(File.ReadAllText(Directory.GetFiles(capture,"*"+suffix).Single())==File.ReadAllText(Directory.GetFiles(replay,"*"+suffix).Single()),"Individual replay diverged: "+suffix);
        Fixture("invalid_json",2,Envelope("{}"),"invalid_llm_invalid_decision_json");
        Fixture("truncated",2,Envelope(Choice(),"length"),"invalid_llm_incomplete_response");
        Fixture("refusal",2,Envelope(Choice(),refusal:"No."),"invalid_llm_provider_refusal");
        LocalCoordinationValidation.Run();
        File.WriteAllText(Path.Combine(output,"result.json"),"{\"passed\":true,\"checks\":"+checks+",\"promptVersion\":\""+PaperVolunteerPrompt.Version+"\",\"responseProtocol\":\""+PersonalDecisionProtocol.Version+"\",\"remoteRequests\":0,\"formalTrials\":0}");
        File.WriteAllText("tmp/individual-p1-validation/latest.txt",output);
        Debug.Log("INDIVIDUAL_P1_VALIDATION_PASSED: "+checks+" checks plus specification/comprehension/reference/runtime regressions; synthetic only, zero API");
    }
}

