using System;
using System.IO;
using System.Linq;
using Coordination;
using UnityEngine;

public static class CoordinationStudyValidation
{
    private static int checks;
    private static void Check(bool ok,string why){checks++;if(!ok)throw new Exception(why);}
    private static void Reject(Action action,string why)
    {bool rejected=false;try{action();}catch(Exception){rejected=true;}Check(rejected,why);}
    public static void Run()
    {
        checks=0;string stamp=DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff"),folder=Path.GetFullPath("tmp/s5-validation/"+stamp);Directory.CreateDirectory(folder);
        string root=Path.GetFullPath(Path.Combine(Application.dataPath,"..")),source=Path.Combine(folder,"source.txt"),data=Path.Combine(folder,"data.jsonl"),path=Path.Combine(folder,"lock.json");
        File.WriteAllText(source,"synthetic source fixture");File.WriteAllText(data,"synthetic dataset fixture");
        var m=ResearchValidation.CreateManager(Path.Combine(folder,"unused"));StudyDatasetBuilder.Configure(m,StudyDatasetBuilder.Cells().First(),"A2");
        m.recordExperimentsAutomatically=true;m.agentResearchPhase=AgentResearchPhase.FinalTest;m.baseSeed=430001;
        var job=new CoordinationStudyPlan.Job {jobID="synthetic_job",kind="closed_loop",phase="FinalTest",seed=430001,cellId="SingleBlockedExit_n8",groupId="A2",conditionKey=m.AgentConditionKey,
            executionMode=m.paperExecutionMode.ToString(),availabilityMode=m.coordinationAvailability.ToString(),policy=m.volunteerDecisionMode.ToString(),information=m.agentInformation.ToString(),
            maxAgentRequests=100,maxDispatchRequests=20,maxOutputTokens=1024,maxPromptChars=60000,maxHttpAttempts=0};
        var p=new CoordinationStudyPlan.Payload {schema="coordination-study-v1",model="gpt-4o-mini",horizon=200,dispatchVersion=LLMDispatchProtocol.Version,willingnessVersion=AgentObservation.PromptVersion,
            primaryContrast="synthetic validation only",multiplicityTreatment="no inferential study",developmentSeeds=new[]{410001},calibrationSeeds=new[]{420001},testSeeds=new[]{430001},jobs=new[]{job},
            sourceFiles=new[]{new AgentStudyPlan.SourceFile {path=Path.GetRelativePath(root,source),sha256=AgentStudyPlan.Hash(source)}},
            datasetFiles=new[]{new AgentStudyPlan.SourceFile {path=Path.GetRelativePath(root,data),sha256=AgentStudyPlan.Hash(data)}}};
        var files=Directory.GetFiles(Path.Combine(root,"Assets/scripts"),"*.cs",SearchOption.AllDirectories)
            .Concat(Directory.GetFiles(Path.Combine(root,"Assets/Scenes"),"*.unity"))
            .Concat(Directory.GetFiles(Path.Combine(root,"tools"),"*.py"));
        p.sourceFiles=p.sourceFiles.Concat(files.Select(f=>new AgentStudyPlan.SourceFile {path=Path.GetRelativePath(root,f).Replace('\\','/'),sha256=AgentStudyPlan.Hash(f)})).ToArray();
        Action save=()=>{string payload=JsonUtility.ToJson(p);File.WriteAllText(path,JsonUtility.ToJson(new CoordinationStudyPlan {schema="coordination-study-lock-v1",locked=true,payloadJson=payload,planID=CoordinationStudyPlan.Digest(payload)}));};
        save();m.lockedCoordinationStudyPlanPath=path;
        try
        {
            m.ValidateAgentResearchSettings(430001);Check(true,"valid plan");
            Reject(()=>m.ValidateAgentResearchSettings(420001),"Wrong seed accepted");
            m.openAIModel="changed";Reject(()=>m.ValidateAgentResearchSettings(430001),"Changed model accepted");m.openAIModel="gpt-4o-mini";
            m.maxCoordinationRequestsPerRun=21;Reject(()=>m.ValidateAgentResearchSettings(430001),"Changed cap accepted");m.maxCoordinationRequestsPerRun=20;
            m.agentCount=9;Reject(()=>m.ValidateAgentResearchSettings(430001),"Changed physical cell accepted");m.agentCount=8;
            m.recordExperimentsAutomatically=false;Reject(()=>m.ValidateAgentResearchSettings(430001),"Unrecorded formal job accepted");m.recordExperimentsAutomatically=true;
            m.coordinationReplayPath="some replay";Reject(()=>m.ValidateAgentResearchSettings(430001),"Replay admitted to study");m.coordinationReplayPath="";
            File.WriteAllText(source,"changed");Reject(()=>m.ValidateAgentResearchSettings(430001),"Source drift accepted");File.WriteAllText(source,"synthetic source fixture");
            File.WriteAllText(data,"changed");Reject(()=>m.ValidateAgentResearchSettings(430001),"Dataset drift accepted");File.WriteAllText(data,"synthetic dataset fixture");
            File.WriteAllText(path,File.ReadAllText(path).Replace("synthetic validation only","tampered"));Reject(()=>m.ValidateAgentResearchSettings(430001),"Payload checksum ignored");save();
            p.testSeeds=new[]{410001};save();Reject(()=>m.ValidateAgentResearchSettings(410001),"Overlapping seeds accepted");p.testSeeds=new[]{430001};save();
            p.jobs=new[]{job,job};save();Reject(()=>m.ValidateAgentResearchSettings(430001),"Duplicate jobs accepted");p.jobs=new[]{job};save();
            string id;CoordinationStudyPlan.Read(path,out id);
            string ledger=Path.GetFullPath(Path.Combine(Application.dataPath,"../../..","tmp/s5ledger",stamp));
            Reject(()=>CoordinationStudyPlan.Claim(ledger,id,job),"FinalTest admitted before pilot gate");job.phase="Development";
            string claim=CoordinationStudyPlan.Claim(ledger,id,job);Check(File.Exists(claim),"Budget claim missing");
            Reject(()=>CoordinationStudyPlan.Claim(ledger,id,job),"Repeated budget claim accepted");
            File.WriteAllText(Path.Combine(folder,"ledger_location.txt"),ledger);
            job.jobID="../escape";Reject(()=>CoordinationStudyPlan.Claim(ledger,id,job),"Unsafe job ID accepted");job.jobID="synthetic_job";
        }
        finally{ResearchValidation.Cleanup();}
        // Exercise the old reference/Local/optimizer/LLM paths after study-lock integration.
        LLMCoordinationValidation.Run();
        File.WriteAllText(Path.Combine(folder,"result.json"),"{\"passed\":true,\"checks\":"+checks+",\"remoteRequests\":0,\"formalJobsExecuted\":0}");
        File.WriteAllText("tmp/s5-validation/latest.txt",folder);
        Debug.Log("S5_STUDY_VALIDATION_PASSED: "+checks+" lock/ledger checks plus full S4 regression; zero APIs or formal trials");
    }
    public static void VerifyLocked()
    {
        string path=Path.GetFullPath("research/s5/coordination-study.lock.json"),id;var p=CoordinationStudyPlan.Read(path,out id);int checkedJobs=0;
        foreach(var job in p.jobs.Where(j=>j.kind=="closed_loop").GroupBy(j=>j.phase+"/"+j.cellId+"/"+j.groupId).Select(g=>g.First()))
        {
            var m=ResearchValidation.CreateManager(Path.GetFullPath("tmp/s5-final-preflight"));
            try
            {
                StudyDatasetBuilder.Configure(m,StudyDatasetBuilder.Cells().Single(c=>c.cellId==job.cellId),job.groupId);
                m.recordExperimentsAutomatically=true;m.agentResearchPhase=(AgentResearchPhase)Enum.Parse(typeof(AgentResearchPhase),job.phase);
                m.lockedCoordinationStudyPlanPath=path;m.ValidateAgentResearchSettings(job.seed);checkedJobs++;
            }
            finally{ResearchValidation.Cleanup();}
        }
        Directory.CreateDirectory("tmp/s5-final-preflight");
        File.WriteAllText("tmp/s5-final-preflight/result.json","{\"passed\":true,\"conditionPhaseChecks\":"+checkedJobs+",\"planID\":\""+id+"\",\"remoteRequests\":0,\"claimsMade\":0}");
        Debug.Log("S5_REAL_LOCK_PREFLIGHT_PASSED: "+checkedJobs+" condition/phase checks; no run, no claims, no API");
    }
}
