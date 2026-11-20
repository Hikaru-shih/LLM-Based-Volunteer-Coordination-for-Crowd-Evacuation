using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

[Serializable] public sealed class CoordinationStudyPlan
{
    public string schema,planID,payloadJson;public bool locked;
    [Serializable] public sealed class Payload
    {
        public string schema,model,dispatchVersion,willingnessVersion,primaryContrast,multiplicityTreatment;
        public int horizon;public int[] developmentSeeds,calibrationSeeds,testSeeds;
        public AgentStudyPlan.SourceFile[] sourceFiles,datasetFiles;
        public Job[] jobs;
    }
    [Serializable] public sealed class Job
    {
        public string jobID,kind,phase,cellId,groupId,conditionKey,executionMode,availabilityMode,policy,information;
        public int seed,maxAgentRequests,maxDispatchRequests,maxOutputTokens,maxPromptChars,maxHttpAttempts;
    }
    public static string Digest(string text)
    {using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-","").ToLowerInvariant();}
    public static Payload Read(string path,out string id)
    {
        var envelope=JsonUtility.FromJson<CoordinationStudyPlan>(File.ReadAllText(path));
        if(envelope==null || !envelope.locked || envelope.schema!="coordination-study-lock-v1" || string.IsNullOrEmpty(envelope.payloadJson) || Digest(envelope.payloadJson)!=envelope.planID)
            throw new InvalidDataException("Invalid coordination study checksum/schema");
        id=envelope.planID;var p=JsonUtility.FromJson<Payload>(envelope.payloadJson);
        if(p==null || p.schema!="coordination-study-v1" || p.horizon<=0 || p.dispatchVersion!=Coordination.LLMDispatchProtocol.Version ||
            p.willingnessVersion!=AgentObservation.PromptVersion || string.IsNullOrEmpty(p.model) || string.IsNullOrEmpty(p.primaryContrast) ||
            string.IsNullOrEmpty(p.multiplicityTreatment) || p.jobs==null || p.jobs.Length==0 || p.sourceFiles==null || p.sourceFiles.Length==0 || p.datasetFiles==null || p.datasetFiles.Length==0)
            throw new InvalidDataException("Incomplete coordination study payload");
        var groups=new[]{p.developmentSeeds,p.calibrationSeeds,p.testSeeds};
        if(groups.Any(g=>g==null || g.Length==0 || g.Distinct().Count()!=g.Length) || groups.SelectMany(g=>g).Distinct().Count()!=groups.Sum(g=>g.Length))
            throw new InvalidDataException("Overlapping/duplicate/missing study seeds");
        if(p.jobs.Select(j=>j.jobID).Distinct().Count()!=p.jobs.Length)throw new InvalidDataException("Duplicate planned jobs");
        string root=Path.GetFullPath(Path.Combine(Application.dataPath,".."));
        var current=Directory.GetFiles(Path.Combine(root,"Assets/scripts"),"*.cs",SearchOption.AllDirectories)
            .Concat(Directory.GetFiles(Path.Combine(root,"Assets/Scenes"),"*.unity"))
            .Concat(Directory.GetFiles(Path.Combine(root,"tools"),"*.py"))
            .Select(f=>Path.GetRelativePath(root,f).Replace('\\','/')).OrderBy(f=>f,StringComparer.Ordinal).ToArray();
        var frozen=p.sourceFiles.Select(f=>f.path).Where(f=>f.EndsWith(".cs",StringComparison.Ordinal) || f.EndsWith(".unity",StringComparison.Ordinal) || f.EndsWith(".py",StringComparison.Ordinal)).OrderBy(f=>f,StringComparer.Ordinal).ToArray();
        if(!current.SequenceEqual(frozen))throw new InvalidDataException("Frozen source file set changed");
        foreach(var file in p.sourceFiles.Concat(p.datasetFiles))
        {
            string full=Path.GetFullPath(Path.Combine(root,file.path));
            if(!full.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase) || AgentStudyPlan.Hash(full)!=file.sha256)
                throw new InvalidDataException("Frozen source/dataset changed: "+file.path);
        }
        return p;
    }
    public static Job Validate(string path,SimulationManager m,int seed,out string id)
    {
        var p=Read(path,out id);
        if(!m.recordExperimentsAutomatically || m.batchRunCount!=1 || m.maxSimulationSteps!=p.horizon || m.openAIModel!=p.model || m.obstacleHandlingMode!=ObstacleHandlingMode.PaperRelocation ||
            m.allowMockFallback || m.agentPromptWording!=AgentPromptWording.Standard || !string.IsNullOrEmpty(m.coordinationReplayPath) || !string.IsNullOrEmpty(m.paperDecisionReplayPath))
            throw new InvalidDataException("Run differs from coordination study configuration");
        string phase=m.agentResearchPhase.ToString();int[] seeds=phase=="FinalTest"?p.testSeeds:phase=="Calibration"?p.calibrationSeeds:p.developmentSeeds;
        if(!seeds.Contains(seed))throw new InvalidDataException("Seed not in selected split");
        var matches=p.jobs.Where(j=>j.kind=="closed_loop" && j.phase==phase && j.seed==seed && j.conditionKey==m.AgentConditionKey &&
            j.executionMode==m.paperExecutionMode.ToString() && j.availabilityMode==m.coordinationAvailability.ToString() && j.policy==m.volunteerDecisionMode.ToString() && j.information==m.agentInformation.ToString()).ToArray();
        if(matches.Length!=1)throw new InvalidDataException("Run is not a unique scheduled study job");
        var job=matches[0];
        if(job.maxAgentRequests!=m.maxAgentRequestsPerRun || job.maxDispatchRequests!=m.maxCoordinationRequestsPerRun || job.maxOutputTokens!=m.coordinationMaxOutputTokens || job.maxPromptChars!=m.coordinationMaxPromptChars)
            throw new InvalidDataException("Run request/token limits differ from study lock");
        return job;
    }
    public static string Claim(string root,string planID,Job job)
    {
        if(job==null || string.IsNullOrEmpty(job.jobID) || job.jobID.Any(c=>!char.IsLetterOrDigit(c) && c!='_' && c!='-'))throw new InvalidDataException("Invalid job ID");
        string folder=Path.Combine(root,"study_ledgers",planID);Directory.CreateDirectory(folder);
        if(job.phase=="FinalTest")VerifyPilotGate(Path.Combine(folder,"pilot-gate.json"),planID);
        string file=Path.Combine(folder,job.jobID+".claim.json");
        // A failed/interrupted run keeps its reservation. Retries require a disclosed amendment.
        using(var stream=new FileStream(file,FileMode.CreateNew,FileAccess.Write,FileShare.None))
        using(var writer=new StreamWriter(stream))writer.Write(JsonUtility.ToJson(job,true));
        return file;
    }
    [Serializable] private sealed class GateEnvelope {public string schema,gateID,payloadJson;}
    [Serializable] private sealed class GatePayload {public string schema,planID;public bool passed;public AgentStudyPlan.SourceFile[] inputFiles;}
    public static void VerifyPilotGate(string path,string planID)
    {
        var gate=JsonUtility.FromJson<GateEnvelope>(File.ReadAllText(path));
        if(gate==null || gate.schema!="coordination-pilot-gate-lock-v1" || string.IsNullOrEmpty(gate.payloadJson) || Digest(gate.payloadJson)!=gate.gateID)
            throw new InvalidDataException("Invalid pilot gate checksum");
        var p=JsonUtility.FromJson<GatePayload>(gate.payloadJson);
        if(p==null || p.schema!="coordination-pilot-gate-v1" || p.planID!=planID || !p.passed || p.inputFiles==null || p.inputFiles.Length==0)
            throw new InvalidDataException("Pilot gate has not passed for this plan");
        string root=Path.GetFullPath(Path.Combine(Application.dataPath,".."));
        foreach(var f in p.inputFiles)
        {
            string full=Path.GetFullPath(Path.Combine(root,f.path));
            if(!full.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase) || AgentStudyPlan.Hash(full)!=f.sha256)
                throw new InvalidDataException("Pilot evidence changed");
        }
    }
}
