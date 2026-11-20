using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;

[Serializable]
public sealed class AutomaticExperimentRecord
{
    public string recordID,purpose,recordedAtUtc,termination,dataDirectory,interpretation;
    public ResearchRunConfiguration configuration;
    public int stopStep,evacuated,apiLogicalCalls,willingDecisions,refusalDecisions,activations,settled,push,pull,rotate;
}

[Serializable]
public sealed class AutomaticAssessmentRecord
{
    public string recordID,purpose,recordedAtUtc,kind,model,specVersion,promptHash,dataDirectory,outcome,summary;
    public int logicalCalls,httpAttempts,passedChecks,totalChecks;
}

/// <summary>Local, idempotent run archival and English notebook publication. No network.</summary>
public static class AutomaticExperimentLog
{
    private const string Marker="<!-- AUTO-RECORDED RUNS -->";
    public static string DefaultRoot => Path.Combine(Application.isEditor ? Path.GetDirectoryName(Application.dataPath) :
        Application.persistentDataPath,"experiment_records");
    private static string Hash(string value)
    {using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
    private static string FileHash(string path)
    {using(var sha=SHA256.Create()) using(var file=File.OpenRead(path)) return BitConverter.ToString(sha.ComputeHash(file));}
    public static string RunFolder(string root,string purpose,string recordID)
    {
        string slug=Regex.Replace(purpose.ToLowerInvariant(),"[^a-z0-9]+","-").Trim('-');
        if(slug.Length==0) slug="unspecified";
        if(slug.Length>24) slug=slug.Substring(0,24);
        return Path.Combine(Path.GetFullPath(root),"data","auto",slug,Hash(recordID).Substring(0,12));
    }
    private static void AtomicWrite(string path,string contents)
    {
        string temporary=path+"."+Guid.NewGuid().ToString("N")+".tmp";
        File.WriteAllText(temporary,contents,new UTF8Encoding(false));
        if(File.Exists(path)) File.Replace(temporary,path,null);else File.Move(temporary,path);
    }
    public static int RecoverPending(string root)
    {
        string auto=Path.Combine(root,"data","auto");
        if(!Directory.Exists(auto)) return 0;
        int recovered=0;
        foreach(string path in Directory.GetFiles(auto,"*_notebook_pending.json",SearchOption.AllDirectories))
        {
            var record=JsonUtility.FromJson<AutomaticExperimentRecord>(File.ReadAllText(path));
            Publish(root,Path.GetDirectoryName(path),record);
            File.Delete(path);recovered++;
        }
        return recovered;
    }
    public static string Publish(string root,string sourceFolder,AutomaticExperimentRecord record)
    {
        root=Path.GetFullPath(root);Directory.CreateDirectory(root);
        string entries=Path.Combine(root,"entries");Directory.CreateDirectory(entries);
        // Keep IDs safe even if an external test supplied a custom experiment identifier.
        string id=Hash(record.recordID);
        string eventPath=Path.Combine(entries,id+".json");
        using(var gate=new FileStream(Path.Combine(root,".notebook.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None))
        {
            if(!File.Exists(eventPath))
            {
                string destination=RunFolder(root,record.purpose,record.recordID);
                record.dataDirectory=Path.GetRelativePath(root,destination).Replace('\\','/');
                Directory.CreateDirectory(destination);
                // Copy first: an I/O failure never removes the only raw-data copy.
                foreach(string file in Directory.GetFiles(sourceFolder))
                {
                    if(!Path.GetFileName(file).StartsWith(record.recordID+"_",StringComparison.Ordinal)) continue;
                    string target=Path.Combine(destination,Path.GetFileName(file));
                    if(Path.GetFullPath(file)==Path.GetFullPath(target)) continue;
                    if(!File.Exists(target)) File.Copy(file,target);
                    if(FileHash(file)!=FileHash(target)) throw new IOException("Archived artifact checksum mismatch");
                }
                AtomicWrite(eventPath,JsonUtility.ToJson(record,true));
            }
            else record=JsonUtility.FromJson<AutomaticExperimentRecord>(File.ReadAllText(eventPath));
            RebuildNotebook(root,entries);
            UpdateCatalog(root,record);
            // Retain staging files as a recovery copy. New runs can write directly to canonical folders.
            return Path.Combine(root,record.dataDirectory);
        }
    }
    public static void PublishAssessment(string root,AutomaticAssessmentRecord record)
    {
        root=Path.GetFullPath(root);Directory.CreateDirectory(root);
        string directory=Path.Combine(root,"assessments");Directory.CreateDirectory(directory);
        using(var gate=new FileStream(Path.Combine(root,".notebook.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None))
        {
            string path=Path.Combine(directory,Hash(record.recordID)+".json");
            if(!File.Exists(path)) AtomicWrite(path,JsonUtility.ToJson(record,true));
            var text=new StringBuilder("record_id,purpose,kind,model,spec_version,outcome,passed_checks,total_checks,logical_calls,http_attempts,data_directory\n");
            foreach(string file in Directory.GetFiles(directory,"*.json").OrderBy(f=>f,StringComparer.Ordinal))
            {
                var r=JsonUtility.FromJson<AutomaticAssessmentRecord>(File.ReadAllText(file));
                object[] row={r.recordID,r.purpose,r.kind,r.model,r.specVersion,r.outcome,r.passedChecks,r.totalChecks,r.logicalCalls,r.httpAttempts,r.dataDirectory};
                text.AppendLine(string.Join(",",row.Select(v=>SimulationData.Csv(Convert.ToString(v,System.Globalization.CultureInfo.InvariantCulture)))));
            }
            AtomicWrite(Path.Combine(root,"ASSESSMENT_CATALOG.csv"),text.ToString());
            string entries=Path.Combine(root,"entries");Directory.CreateDirectory(entries);
            RebuildNotebook(root,entries);
        }
    }
    public static int RecoverAssessments(string root)
    {
        int count=0;
        foreach(string kind in new[]{"comprehension","individual_sampling"})
        {
            string data=Path.Combine(root,"data",kind);if(!Directory.Exists(data))continue;
            foreach(string file in Directory.GetFiles(data,"*_assessment_pending.json",SearchOption.AllDirectories))
            {PublishAssessment(root,JsonUtility.FromJson<AutomaticAssessmentRecord>(File.ReadAllText(file)));File.Delete(file);count++;}
        }
        return count;
    }
    private static void RebuildNotebook(string root,string entries)
    {
        string path=Path.Combine(root,"EXPERIMENT_LOG.md");
        string existing=File.Exists(path) ? File.ReadAllText(path) : "# Experiment and Validation Notebook\n\n";
        int marker=existing.IndexOf(Marker,StringComparison.Ordinal);
        string manual=marker>=0 ? existing.Substring(0,marker) : existing;
        var text=new StringBuilder(manual.TrimEnd()+"\n\n"+Marker+"\n\n## Automatically recorded runs\n\n");
        foreach(var r in Directory.GetFiles(entries,"*.json")
            .Select(file=>JsonUtility.FromJson<AutomaticExperimentRecord>(File.ReadAllText(file)))
            .OrderBy(r=>r.recordedAtUtc,StringComparer.Ordinal).ThenBy(r=>r.recordID,StringComparer.Ordinal))
        {
            var c=r.configuration;
            text.Append("### ").Append(r.recordID).Append("\n\nRecorded (UTC): ").Append(r.recordedAtUtc)
                .Append("\n\nPurpose: ").Append(r.purpose.Replace("\r"," ").Replace("\n"," "))
                .Append("\n\nSettings: ").Append(c.scenario).Append("; policy ").Append(c.volunteerPolicy)
                .Append("; information ").Append(c.observationScope).Append("; model ").Append(c.model)
                .Append("; seed ").Append(c.seed).Append("; agents ").Append(c.actualAgents)
                .Append("; obstacles ").Append(c.actualObstacles).Append("; horizon ").Append(c.maxSteps)
                .Append(". Full settings are in the linked raw configuration.\n\nOutcome: ").Append(r.termination)
                .Append("; stop step ").Append(r.stopStep).Append("; evacuated ").Append(r.evacuated).Append('/').Append(c.actualAgents)
                .Append("; T100 ").Append(r.termination=="completed" ? r.stopStep.ToString() : "not observed")
                .Append("; API logical calls ").Append(r.apiLogicalCalls)
                .Append("; willing decisions ").Append(r.willingDecisions).Append("; refusals ").Append(r.refusalDecisions)
                .Append("; handler activations ").Append(r.activations).Append("; settled obstacles ").Append(r.settled)
                .Append("; push/pull/rotate ").Append(r.push).Append('/').Append(r.pull).Append('/').Append(r.rotate)
                .Append(".\n\nInterpretation: ").Append(r.interpretation)
                .Append("\n\nData: [raw run artifacts](").Append(r.dataDirectory).Append("/).\n\n");
        }
        string assessments=Path.Combine(root,"assessments");
        if(Directory.Exists(assessments))
        {
            text.Append("## Automatically recorded assessments\n\n");
            foreach(var r in Directory.GetFiles(assessments,"*.json").Select(file=>JsonUtility.FromJson<AutomaticAssessmentRecord>(File.ReadAllText(file)))
                .OrderBy(r=>r.recordedAtUtc,StringComparer.Ordinal))
                text.Append("### ").Append(r.recordID).Append("\n\nRecorded (UTC): ").Append(r.recordedAtUtc)
                    .Append("\n\nPurpose: ").Append(r.purpose).Append("\n\nType: ").Append(r.kind)
                    .Append("; model: ").Append(r.model).Append("; specification: ").Append(r.specVersion)
                    .Append("\n\nOutcome: ").Append(r.outcome).Append("; correct checks ").Append(r.passedChecks).Append('/').Append(r.totalChecks)
                    .Append("; logical calls ").Append(r.logicalCalls).Append("; HTTP attempts ").Append(r.httpAttempts)
                    .Append(".\n\n").Append(r.summary).Append("\n\nData: [assessment artifacts](").Append(r.dataDirectory).Append("/).\n\n");
        }
        AtomicWrite(path,text.ToString());
    }
    private static void UpdateCatalog(string root,AutomaticExperimentRecord r)
    {
        string path=Path.Combine(root,"RUN_CATALOG.csv");
        const string header="record_id,purpose,data_directory,scenario,policy,seed,agents,obstacles,configured_horizon,stop_step,termination,evacuated,t100_steps,api_logical_calls,willing_decisions,refusal_decisions,activations,settled,push,pull,rotate,initial_state_sha256,condition_key,interpretation";
        string existing=File.Exists(path) ? File.ReadAllText(path) : header+"\n";
        if(existing.Split('\n').Any(line=>line.StartsWith(r.recordID+",",StringComparison.Ordinal) || line.StartsWith(SimulationData.Csv(r.recordID)+",",StringComparison.Ordinal))) return;
        var c=r.configuration;
        object[] values={r.recordID,r.purpose,r.dataDirectory,c.scenario,c.volunteerPolicy,c.seed,c.actualAgents,c.actualObstacles,
            c.maxSteps,r.stopStep,r.termination,r.evacuated,r.termination=="completed" ? r.stopStep.ToString() : "",
            r.apiLogicalCalls,r.willingDecisions,r.refusalDecisions,r.activations,r.settled,r.push,r.pull,r.rotate,"",c.conditionKey,r.interpretation};
        AtomicWrite(path,existing.TrimEnd()+"\n"+string.Join(",",values.Select(v=>SimulationData.Csv(Convert.ToString(v,System.Globalization.CultureInfo.InvariantCulture))))+"\n");
    }
}
