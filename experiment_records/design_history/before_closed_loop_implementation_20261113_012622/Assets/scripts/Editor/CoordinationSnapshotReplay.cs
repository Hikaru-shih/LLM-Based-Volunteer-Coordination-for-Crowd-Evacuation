using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Coordination;
using UnityEngine;
using UnityEditor;

// Offline fixed-snapshot comparison. Never constructs a transport or requests credentials.
public static class CoordinationSnapshotReplay
{
    [MenuItem("Research/Coordination/Compare audit snapshots including failures (offline)")]
    public static void OpenAuditComparison()
    {
        string audit=EditorUtility.OpenFilePanel("Select coordination_trace.jsonl","","jsonl");if(string.IsNullOrEmpty(audit))return;
        string output=EditorUtility.SaveFilePanel("Save audit snapshot comparison",Path.GetDirectoryName(audit),"audit_snapshot_comparison","jsonl");if(string.IsNullOrEmpty(output))return;
        CompareAudit(audit,output);PublishComparison(output+".snapshots.jsonl",audit,output);Debug.Log("Offline audit comparison saved: "+output);
    }
    public static void CompareAudit(string auditPath,string outputPath)
    {
        string snapshots=outputPath+".snapshots.jsonl";
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath)));
        File.WriteAllLines(snapshots,File.ReadAllLines(auditPath).Select(line=>JsonUtility.FromJson<DispatchAudit>(line).snapshot));
        Compare(snapshots,auditPath,outputPath);
    }
    [MenuItem("Research/Coordination/Compare recorded snapshots (offline)")]
    public static void OpenComparison()
    {
        string snapshots=EditorUtility.OpenFilePanel("Select coordination_snapshots.jsonl","","jsonl");if(string.IsNullOrEmpty(snapshots))return;
        string audits=EditorUtility.OpenFilePanel("Select coordination_trace.jsonl",Path.GetDirectoryName(snapshots),"jsonl");if(string.IsNullOrEmpty(audits))return;
        string output=EditorUtility.SaveFilePanel("Save fixed-snapshot comparison",Path.GetDirectoryName(snapshots),"snapshot_comparison","jsonl");if(string.IsNullOrEmpty(output))return;
        Compare(snapshots,audits,output);PublishComparison(snapshots,audits,output);Debug.Log("Offline snapshot comparison saved: "+output);
    }
    // Interactive analysis is archived and published just like other research actions.
    // The pure Compare methods used by synthetic fixtures do not publish production records.
    private static void PublishComparison(string snapshots,string audit,string output)
    {
        string root=AutomaticExperimentLog.DefaultRoot,id="coordination_snapshot_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")+"_"+Guid.NewGuid().ToString("N").Substring(0,6);
        string folder=AutomaticExperimentLog.RunFolder(root,"coordination_snapshot_comparison",id);Directory.CreateDirectory(folder);
        File.Copy(snapshots,Path.Combine(folder,"snapshots.jsonl"));File.Copy(audit,Path.Combine(folder,"input_audit.jsonl"));File.Copy(output,Path.Combine(folder,"comparison.jsonl"));
        var rows=File.ReadAllLines(output).Select(line=>JsonUtility.FromJson<Row>(line)).ToArray();
        var record=new AutomaticAssessmentRecord {recordID=id,purpose="Compare dispatch proposals on identical recorded snapshots",kind="coordination_snapshot_comparison",
            recordedAtUtc=DateTime.UtcNow.ToString("o"),model="offline_recorded_inputs",specVersion=LLMDispatchProtocol.Version,promptHash=AgentStudyPlan.Hash(snapshots),
            dataDirectory=folder.Substring(Path.GetFullPath(root).Length+1).Replace('\\','/'),outcome="analysis_complete",passedChecks=rows.Count(r=>r.llmValid),totalChecks=rows.Length,
            logicalCalls=0,httpAttempts=0,summary="Offline descriptive comparison; passed checks count valid recorded proposals, not comprehension or optimality. Missing/invalid proposals are retained. Cost gaps apply only at equal coverage. Snapshots may be dependent; this is not a formal efficacy study. This action made zero API calls; original request audits are preserved as input."};
        string pending=Path.Combine(folder,id+"_assessment_pending.json");File.WriteAllText(pending,JsonUtility.ToJson(record,true));
        try{AutomaticExperimentLog.PublishAssessment(root,record);File.Delete(pending);}
        catch(IOException){Debug.LogWarning("Comparison artifacts saved; notebook publication pending recovery.");}
    }
    [Serializable] public sealed class Row
    {
        public string snapshotId,llmError;public int step,localCount,optimalCount,llmCount,coverageGap;
        public double localCost,optimalCost,llmCost,costGap;public bool llmValid,sameCoverage;
    }
    public static double Cost(Snapshot s,Proposal p) => p.assignments.Sum(a=>(double)s.edges.Single(e=>e.agentId==a.agentId && e.obstacleId==a.obstacleId).approachCost);
    public static void Compare(string snapshotsPath,string auditPath,string outputPath)
    {
        var audits=new Dictionary<string,DispatchAudit>();
        foreach(string line in File.ReadAllLines(auditPath))
        {
            var a=JsonUtility.FromJson<DispatchAudit>(line);
            if(a==null || string.IsNullOrEmpty(a.snapshot) || audits.ContainsKey(a.snapshot))throw new InvalidDataException("Missing/duplicate audit snapshot");
            audits.Add(a.snapshot,a);
        }
        var rows=new List<string>();var ids=new HashSet<string>();
        foreach(string line in File.ReadAllLines(snapshotsPath))
        {
            var s=JsonUtility.FromJson<Snapshot>(line);if(s==null || !ids.Add(s.snapshotId))throw new InvalidDataException("Missing/duplicate snapshot");
            var optimal=OptimalDispatcher.Propose(s);var local=LocalDispatcher.Propose(s);
            var row=new Row {snapshotId=s.snapshotId,step=s.step,localCount=local.assignments.Length,optimalCount=optimal.assignments.Length,
                localCost=Cost(s,local),optimalCost=Cost(s,optimal),llmCount=-1,coverageGap=-1,llmError="missing_audit"};
            DispatchAudit audit;Proposal proposal;string explanation,error;
            if(audits.TryGetValue(JsonUtility.ToJson(s),out audit))
            {
                row.llmError=audit.error;
                row.llmValid=audit.accepted && audit.protocol==LLMDispatchProtocol.Version &&
                    LLMDispatchProtocol.Parse(audit.content,out proposal,out explanation,out error) &&
                    ProposalValidator.Validate(s,proposal,s.step,s.worldRevision,out error);
                if(row.llmValid)
                {
                    LLMDispatchProtocol.Parse(audit.content,out proposal,out explanation,out error);
                    row.llmCount=proposal.assignments.Length;row.llmCost=Cost(s,proposal);
                    row.coverageGap=row.optimalCount-row.llmCount;row.sameCoverage=row.coverageGap==0;
                    if(row.sameCoverage)row.costGap=row.llmCost-row.optimalCost;
                }
                else if(string.IsNullOrEmpty(row.llmError))row.llmError="invalid_protocol_or_proposal";
                audits.Remove(JsonUtility.ToJson(s));
            }
            rows.Add(JsonUtility.ToJson(row));
        }
        if(audits.Count!=0)throw new InvalidDataException("Audit entries do not match snapshot dataset");
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath)));File.WriteAllLines(outputPath,rows);
    }
}
