using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Reflection;
using Coordination;
using UnityEngine;

public static class LLMCoordinationValidation
{
    private static int checks;private static string output;private static SimulationManager activeFixture;
    // Keep the test notebook shallow: long nested fixtures can exceed Windows' path limit.
    private static string Notebook => Path.GetFullPath(Path.Combine(Application.dataPath,"../../..","tmp/s4n",Path.GetFileName(output)));
    private static void Check(bool ok,string text){checks++;if(!ok)throw new Exception(text);}
    private static void Drain(IEnumerator value)
    {while(value.MoveNext())if(value.Current is IEnumerator nested)Drain(nested);}
    private static Snapshot Example() => new Snapshot {snapshotId="snapshot-test",step=1,worldRevision=2,
        candidates=new[]{new Candidate {agentId=1}},tasks=new[]{new Task {obstacleId=2}},
        edges=new[]{new Edge {agentId=1,obstacleId=2,eligible=true,consented=true,approachCost=3}}};
    private static DispatchOptions Options() => new DispatchOptions {model="offline-fixture",conditionKey="fixture",enableLive=true,maxRequests=1};
    private static IEnumerator Synthetic(string payload,Action<DispatchAudit> callback)
    {
        // Obtain the actual serialized snapshot from the request's user message.
        var request=JsonUtility.FromJson<Request>(payload);string content=request.messages[1].content;
        var snapshot=JsonUtility.FromJson<Snapshot>(content.Substring(content.IndexOf("\nSnapshot:\n",StringComparison.Ordinal)+11));
        callback(new DispatchAudit {content=LLMDispatchProtocol.Encode(OptimalDispatcher.Propose(snapshot),"Synthetic optimizer answer; not an LLM result."),error="",execution="synthetic_test",attempts=0});
        yield break;
    }
    [Serializable] private sealed class Request {public LLMDecisionPolicy.LLMMessage[] messages;}
    private static void Pure()
    {
        var s=Example();string good=LLMDispatchProtocol.Encode(OptimalDispatcher.Propose(s),"quote \" and \n newline");
        Proposal p;string why,error;
        Check(LLMDispatchProtocol.Parse(good,out p,out why,out error) && p.assignments.Length==1,"Valid typed output rejected");
        foreach(string bad in new[]{"", "{}", "null", "```json\n"+good+"\n```",good+" trailing",good+good,
            good.Replace("\"assignments\":","\"extra\":1,\"assignments\":"),good.Replace("\"agentId\":1","\"agentId\":\"1\""),
            good.Replace("\"agentId\":1","\"agentId\":1.5"),good.Replace("\"agentId\":1","\"agentId\":01"),
            good.Replace("\"agentId\":1","\"agentId\":2147483648"),good.Replace("\"agentId\":1,",""),
            good.Replace("\"agentId\":1","\"agentId\":1,\"agentId\":1"),
            good.Replace("\"snapshotId\":","\"snapshotId\":\"other\",\"snapshotId\":"),
            "{\"snapshotId\":\"x\",\"assignments\":null,\"explanation\":\"x\"}",
            "{\"snapshotId\":\"x\",\"assignments\":[],\"explanation\":false}",
            "{\"snapshotId\":\"x\",\"assignments\":[{}],\"explanation\":\"x\"}"})
            Check(!LLMDispatchProtocol.Parse(bad,out p,out why,out error),"Malformed output accepted: "+bad);
        foreach(string finish in new[]{"length","content_filter","tool_calls"})
            Check(DispatchHttp.Decode("{\"choices\":[{\"finish_reason\":\""+finish+"\",\"message\":{\"content\":\"{}\"}}]}").error=="incomplete_response","Truncation accepted");
        Check(DispatchHttp.Decode("{\"choices\":[{\"finish_reason\":\"stop\",\"message\":{\"refusal\":\"refused\"}}]}").error=="provider_refusal","Refusal accepted");
        Check(DispatchHttp.Decode("{}").error=="invalid_response_envelope","Missing envelope accepted");
        int calls=0;DispatchTransport fake=(payload,cb)=>Reply(cb,good,()=>calls++);
        var options=Options();var session=new LLMDispatchSession(options,fake);DispatchAudit audit=null;
        Drain(session.Decide(s,(proposal,a)=>audit=a));Check(audit.accepted && calls==1,"Synthetic valid reply failed");
        Drain(session.Decide(s,(proposal,a)=>audit=a));Check(!audit.accepted && audit.error=="dispatch_request_limit" && calls==1,"Quota bypassed");
        options=Options();options.enableLive=false;session=new LLMDispatchSession(options,fake);
        Drain(session.Decide(s,(proposal,a)=>audit=a));Check(audit.error=="live_dispatch_disabled" && calls==1,"Disabled live transport invoked");
        options=Options();options.maxPromptChars=256;session=new LLMDispatchSession(options,fake);
        Drain(session.Decide(s,(proposal,a)=>audit=a));Check(audit.error=="prompt_size_limit" && calls==1,"Prompt limit bypassed");
        options=Options();s.edges[0].consented=false;session=new LLMDispatchSession(options,fake);
        Drain(session.Decide(s,(proposal,a)=>audit=a));Check(audit.accepted && audit.execution=="no_eligible_edges" && calls==1,"No-op issued a request");
        s=Example();session=new LLMDispatchSession(Options(),(payload,cb)=>Reply(cb,good.Replace("\"agentId\":1","\"agentId\":99"),null));
        Drain(session.Decide(s,(proposal,a)=>audit=a));Check(!audit.accepted && audit.error=="unknown_or_unlisted_pair","Illegal reply accepted");
        session=new LLMDispatchSession(Options(),(payload,cb)=>Failure(cb));
        Drain(session.Decide(s,(proposal,a)=>audit=a));Check(audit.error=="http_429_rate_limit_exceeded","Transport failure hidden");
        session=new LLMDispatchSession(Options(),(payload,cb)=>Reply(cb,good.Replace("snapshot-test","old-snapshot"),null));
        Drain(session.Decide(s,(proposal,a)=>audit=a));Check(audit.error=="stale_or_missing_snapshot","Stale snapshot accepted");
        string duplicate=good.Replace("\"assignments\":[{\"agentId\":1,\"obstacleId\":2}]","\"assignments\":[{\"agentId\":1,\"obstacleId\":2},{\"agentId\":1,\"obstacleId\":2}]");
        session=new LLMDispatchSession(Options(),(payload,cb)=>Reply(cb,duplicate,null));
        Drain(session.Decide(s,(proposal,a)=>audit=a));Check(audit.error=="duplicate_assignment","Duplicate assignment accepted");
        s=Example();s.edges[0].eligible=false;
        var payloadJson=LLMDispatchSession.PayloadFor(s,Options());
        Check(payloadJson.Contains("\"strict\":true") && payloadJson.Contains("max_completion_tokens"),"Strict schema/token budget absent");
        s=Example();string empty=LLMDispatchProtocol.Encode(new Proposal {snapshotId=s.snapshotId,assignments=new Assignment[0]},"Choose no assignments.");
        session=new LLMDispatchSession(Options(),(payload,cb)=>Reply(cb,empty,null));
        Drain(session.Decide(s,(proposal,a)=>audit=a));Check(audit.accepted,"Legal empty proposal classified as invalid");
        string qualityInput=Path.Combine(output,"empty_proposal.jsonl"),qualityOutput=Path.Combine(output,"empty_proposal_quality.jsonl");
        File.WriteAllText(qualityInput,JsonUtility.ToJson(audit)+Environment.NewLine);CoordinationSnapshotReplay.CompareAudit(qualityInput,qualityOutput);
        var quality=JsonUtility.FromJson<CoordinationSnapshotReplay.Row>(File.ReadAllLines(qualityOutput)[0]);
        Check(quality.llmValid && quality.coverageGap==1 && !quality.sameCoverage,"Empty proposal quality conflated with invalidity");
    }
    private static IEnumerator Reply(Action<DispatchAudit> callback,string content,Action called)
    {called?.Invoke();callback(new DispatchAudit {content=content,error="",execution="synthetic_test"});yield break;}
    private static IEnumerator Failure(Action<DispatchAudit> callback)
    {callback(new DispatchAudit {error="http_429_rate_limit_exceeded",execution="synthetic_test"});yield break;}
    private static string Fixture(string name,string replay=null,DispatchTransport transport=null,string expected="completed",int limit=100,bool automatic=false)
    {
        string folder=Path.Combine(output,name);
        var method=typeof(LocalCoordinationValidation).GetMethod("Make",BindingFlags.Static|BindingFlags.NonPublic);
        var m=(SimulationManager)method.Invoke(null,new object[]{folder,ResearchScenario.SingleBlockedExit,2026});
        m.paperExecutionMode=ExecutionMode.LLMExtension;m.coordinationAvailability=AvailabilityMode.AllEligibleControl;
        m.openAIModel="offline-fixture";m.enableCoordinationLiveRequests=transport!=null;m.maxCoordinationRequestsPerRun=limit;
        m.coordinationTestTransport=transport;m.coordinationReplayPath=replay??"";
        if(automatic){m.recordExperimentsAutomatically=true;m.experimentRecordsRootOverride=Notebook;m.experimentPurpose="Synthetic S4 archival regression, not a live LLM run";}
        activeFixture=m;
        try
        {
            ResearchValidation.Begin(m);while(m.IsSimulationRunning())ResearchValidation.Step(m);
            string global=File.ReadAllText(Directory.GetFiles(folder,"*_global.csv").Single());
            Check(global.Contains(","+expected+","),"Unexpected termination "+name+": "+global);
            var lines=File.ReadAllLines(Directory.GetFiles(folder,"*_coordination_trace.jsonl").Single());
            Check(lines.Length>0 && lines.Select(l=>JsonUtility.FromJson<DispatchAudit>(l)).All(a=>a.attempts==0),"Unexpected HTTP attempts");
            if(expected=="completed")Check(m.GetEvacuatedCount()==2,"Successful fixture did not evacuate all agents");
            else if(m.GetCurrentStep()==1)Check(m.PaperModel.Reservations.Entries.Count()==0 && m.PaperModel.Manipulations==0,"Invalid response changed assignments/physics");
        }
        finally{m.ResetSimulation();ResearchValidation.Cleanup();}
        return folder;
    }
    public static void Run()
    {
        output=Path.GetFullPath("tmp/llm-coordination-validation/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff"));Directory.CreateDirectory(output);checks=0;
        Pure();
        string capture=Fixture("synthetic_capture",transport:Synthetic),trace=Directory.GetFiles(capture,"*_coordination_trace.jsonl").Single();
        string replay=Fixture("strict_replay",replay:trace);
        foreach(string suffix in new[]{"_trajectories.csv","_obstacles.csv","_obstacle_events.csv","_paper_decisions.csv","_volunteer_work.csv","_diagnostics.csv"})
            Check(File.ReadAllText(Directory.GetFiles(capture,"*"+suffix).Single())==File.ReadAllText(Directory.GetFiles(replay,"*"+suffix).Single()),"Replay diverged: "+suffix);
        var recorded=File.ReadAllLines(trace);string extra=Path.Combine(output,"extra.jsonl");File.WriteAllLines(extra,recorded.Concat(new[]{recorded.Last()}));
        Fixture("unused_replay",replay:extra,expected:"invalid_coordination_replay_unused_entries");
        string altered=Path.Combine(output,"mismatched.jsonl");File.WriteAllText(altered,recorded[0].Replace("offline-fixture","wrong-model")+Environment.NewLine);
        Fixture("mismatch_replay",replay:altered,expected:"invalid_coordination_replay_mismatch_or_exhausted");
        Fixture("disabled",expected:"invalid_coordination_live_dispatch_disabled");
        Fixture("invalid_reply",transport:(payload,cb)=>Reply(cb,"{}",null),expected:"invalid_coordination_invalid_dispatch_json");
        Fixture("transport_failure",transport:(payload,cb)=>Failure(cb),expected:"invalid_coordination_http_429_rate_limit_exceeded");
        Fixture("quota_stop",transport:Synthetic,expected:"invalid_coordination_dispatch_request_limit",limit:1);
        Fixture("stale_world",transport:(payload,cb)=>Synthetic(payload,a=>{activeFixture.GetAllAgents().First().Init(activeFixture.world,new Vector2Int(1,8));cb(a);}),expected:"invalid_coordination_stale_world_after_request");
        Fixture("settings_change",transport:(payload,cb)=>Synthetic(payload,a=>{activeFixture.coordinationMaxOutputTokens++;cb(a);}),expected:"invalid_settings_changed");
        Fixture("auto_invalid_reply",transport:(payload,cb)=>Reply(cb,"{}",null),expected:"invalid_coordination_invalid_dispatch_json",automatic:true);
        string notebook=Notebook;File.WriteAllText(Path.Combine(output,"test_notebook_location.txt"),notebook);
        foreach(string suffix in new[]{"_coordination_trace.jsonl","_coordination_requests.jsonl","_coordination_application.jsonl"})
            Check(Directory.GetFiles(Path.Combine(notebook,"data"),"*"+suffix,SearchOption.AllDirectories).Length==1,"Automatic archive omitted "+suffix);
        Check(File.ReadAllText(Path.Combine(notebook,"EXPERIMENT_LOG.md")).Contains("invalid_coordination_invalid_dispatch_json"),"Automatic notebook omitted failed S4 run");
        CoordinationSnapshotReplay.Compare(Directory.GetFiles(capture,"*_coordination_snapshots.jsonl").Single(),trace,Path.Combine(output,"snapshot_comparison.jsonl"));
        Check(File.ReadAllLines(Path.Combine(output,"snapshot_comparison.jsonl")).All(l=>{var row=JsonUtility.FromJson<CoordinationSnapshotReplay.Row>(l);return row.llmValid && row.coverageGap==0 && row.costGap==0;}),"Snapshot comparison failed");
        string invalidTrace=Directory.GetFiles(Path.Combine(output,"invalid_reply"),"*_coordination_trace.jsonl").Single();
        CoordinationSnapshotReplay.CompareAudit(invalidTrace,Path.Combine(output,"invalid_snapshot_comparison.jsonl"));
        Check(!JsonUtility.FromJson<CoordinationSnapshotReplay.Row>(File.ReadAllLines(Path.Combine(output,"invalid_snapshot_comparison.jsonl"))[0]).llmValid,"Invalid proposal quality counted as valid");
        OptimalCoordinationValidation.Run();
        File.WriteAllText(Path.Combine(output,"result.json"),"{\"passed\":true,\"checks\":"+checks+",\"remoteRequests\":0,\"syntheticNotLiveLLM\":true}");
        File.WriteAllText("tmp/llm-coordination-validation/latest.txt",output);
        Debug.Log("LLM_COORDINATION_VALIDATION_PASSED: "+checks+" checks plus optimizer/reference/runtime/menu suite; synthetic responses only, zero remote requests");
    }
}
