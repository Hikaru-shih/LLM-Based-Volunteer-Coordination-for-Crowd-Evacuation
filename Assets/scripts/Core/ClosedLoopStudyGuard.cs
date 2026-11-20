using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Threading;
using UnityEngine;

[Serializable] public sealed class ClosedLoopJob
{
    public string id,cell,policy,phase,calibrationFile,replayFile,conditionKey,initialStateSHA;
    public int seed,agents,blocked;public float cv;
}
[Serializable] public sealed class ClosedLoopCampaign
{
    public string schema,phase,sourceSHA,model;public int horizon,maxReservedHttp,wallSeconds;
    public bool paidFinalExecutionByDefault;public ClosedLoopJob[] jobs;
}

// The new group gate is separate from the archived coordination/SharedContext design.
public static class ClosedLoopStudyGuard
{
    [Serializable] public sealed class FileRecord {public string path,sha256;}
    [Serializable] public sealed class Document
    {
        public string schema,lockID,productionSourceSHA,formalPlanSHA;
        public FileRecord[] artifacts;
    }
    public static string FileSHA(string path) {using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
    public static bool MatchesProvider(string raw,string expected)
    {System.Collections.Generic.Dictionary<string,object> obj;object value;return StrictJson.TryObject(raw,out obj) && obj.TryGetValue("model",out value) && value is string && (string)value==expected;}
    public static string ProductionSHA(string root)
    {
        string scripts=Path.Combine(root,"Assets","scripts");
        return ClosedLoopInitialState.Hash(string.Join("\n",Directory.GetFiles(scripts,"*.cs",SearchOption.AllDirectories)
            .Select(p=>new{path=Path.GetRelativePath(root,p).Replace('\\','/'),file=p})
            .OrderBy(p=>p.path,StringComparer.Ordinal).Select(p=>p.path+":"+FileSHA(p.file))));
    }
    private static string cachedPath,cachedSHA;private static Document cached;
    public static Document Verify(string path)
    {
        if(string.IsNullOrWhiteSpace(path))throw new InvalidDataException("Closed-loop final lock required");
        string absolute=Path.GetFullPath(path),fingerprint=FileSHA(absolute);bool reuse=cached!=null && cachedPath==absolute && cachedSHA==fingerprint;
        var d=reuse?cached:JsonUtility.FromJson<Document>(File.ReadAllText(path));
        if(d==null || d.schema!="closed-loop-lock-v1" || d.artifacts==null || d.artifacts.Length<5)throw new InvalidDataException("Invalid group lock");
        string identity=d.schema+"\n"+d.productionSourceSHA+"\n"+d.formalPlanSHA+"\n"+string.Join("\n",d.artifacts.OrderBy(f=>f.path,StringComparer.Ordinal).Select(f=>f.path+":"+f.sha256));
        if(d.lockID!=ClosedLoopInitialState.Hash(identity))throw new InvalidDataException("Group lock identity changed");
        string folder=Path.GetDirectoryName(Path.GetFullPath(path));
        if(!reuse)foreach(var f in d.artifacts)
        {
            string resolved=Path.GetFullPath(Path.Combine(folder,f.path));
            if(Path.IsPathRooted(f.path)||!resolved.StartsWith(folder+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)||FileSHA(resolved)!=f.sha256)
                throw new InvalidDataException("Group locked artifact changed");
        }
        string project=Path.GetDirectoryName(Application.dataPath);
        if(ProductionSHA(project)!=d.productionSourceSHA || FileSHA(Path.Combine(folder,"formal-plan.json"))!=d.formalPlanSHA)
            throw new InvalidDataException("Group source/plan drift");
        cached=d;cachedPath=absolute;cachedSHA=fingerprint;return d;
    }
    public static string Validate(string path,SimulationManager manager,int seed)
    {
        var d=Verify(path);string folder=Path.GetDirectoryName(Path.GetFullPath(path));
        var p=JsonUtility.FromJson<ClosedLoopCampaign>(File.ReadAllText(Path.Combine(folder,"formal-plan.json")));
        var job=p.jobs.SingleOrDefault(j=>j.id==manager.closedLoopJobID);
        if(p.schema!="closed-loop-campaign-v1" || p.phase!="FinalTest" || job==null || job.phase!="FinalTest" || job.seed!=seed ||
            job.policy!=manager.volunteerDecisionMode.ToString() || job.agents!=manager.agentCount || job.blocked!=manager.closedLoopInitialState.blocked ||
            Math.Abs(job.cv-manager.volunteerCost)>1e-7 || job.conditionKey!=manager.AgentConditionKey || job.initialStateSHA!=manager.closedLoopInitialState.Identity ||
            p.horizon!=manager.maxSimulationSteps || p.sourceSHA!=d.productionSourceSHA || manager.closedLoopSourceSHA!=d.productionSourceSHA ||
            p.model!=manager.openAIModel || manager.agentInformation!=AgentInformationCondition.Core || manager.agentPromptWording!=AgentPromptWording.Standard ||
            manager.paperExecutionMode!=Coordination.ExecutionMode.PaperReference || manager.coordinationAvailability!=Coordination.AvailabilityMode.PolicyWillingness)
            throw new InvalidDataException("Final group job does not match frozen conditions");
        if(job.policy=="RandomMatched")
        {
            string relative=job.calibrationFile.Replace('\\','/');
            string expected=Path.GetFullPath(Path.Combine(folder,relative));
            var artifact=d.artifacts.SingleOrDefault(f=>f.path==relative);
            if(artifact==null || manager.cooperationCalibrationPath!=expected || FileSHA(expected)!=artifact.sha256)
                throw new InvalidDataException("Final calibration artifact drift");
        }
        if(!manager.closedLoopZeroStepValidation)ClaimFinal(manager.experimentRecordsRootOverride,d.lockID,job.id);
        return d.lockID;
    }

    public static void ClaimFinal(string recordsRoot,string lockID,string jobID)
    {
        string folder=Path.Combine(recordsRoot,"group_execution",lockID,"claims");Directory.CreateDirectory(folder);
        string path=Path.Combine(folder,ClosedLoopInitialState.Hash(jobID)+".json");
        using(var stream=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None))
        using(var writer=new StreamWriter(stream))writer.Write("{\"job\":\""+jobID+"\",\"status\":\"claimed_before_simulation\"}");
    }
    public static void ReserveFinal(string root,string lockID,int maximum)
    {
        string folder=Path.Combine(root,"experiment_records","group_execution",lockID);Directory.CreateDirectory(folder);
        string path=Path.Combine(folder,"reserved-http.bin");
        for(int retry=0;retry<100;retry++)
        {
            try
            {
                bool existed=File.Exists(path);
                using(var file=new FileStream(path,FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None))
                {
                    long value=0;
                    if(existed || file.Length>0)
                    {
                        if(file.Length!=8)throw new InvalidDataException("Final reservation ledger interrupted");
                        byte[] b=new byte[8];if(file.Read(b,0,8)!=8)throw new InvalidDataException("Final ledger truncated");value=BitConverter.ToInt64(b,0);
                    }
                    if(value<0 || value%3!=0 || value+3>maximum)throw new InvalidDataException("Final global reservation ceiling");
                    file.Position=0;byte[] next=BitConverter.GetBytes(value+3);file.Write(next,0,8);file.SetLength(8);file.Flush(true);return;
                }
            }
            catch(IOException) when(retry<99){Thread.Sleep(10);}
        }
        throw new IOException("Cannot reserve final request");
    }
}
