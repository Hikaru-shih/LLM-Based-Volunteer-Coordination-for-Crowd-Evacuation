using UnityEngine;
using System.Collections.Generic;
using System.IO;
using System;
using System.Globalization;
using System.Linq;

public class SimulationData
{
    public struct AgentEvacuationRecord
    {
        public int agentID;
        public int evacuationStep;
        public float evacuationTime;
    }

    public struct StepDiagnostic
    {
        public int step;
        public int agentsRemaining;
        public int conflictCount;
        public int volunteerActions;
        public int obstaclesRemaining;
        public float avgDFFValue;
        public float avgAFFValue;
    }

    public struct LLMDecisionRecord
    {
        public int step;
        public int agentID;
        public string decision;
        public string explanation;
        public string source;
        public string fallbackReason;
    }

    private List<AgentEvacuationRecord> agentRecords = new List<AgentEvacuationRecord>();
    private List<StepDiagnostic> diagnostics = new List<StepDiagnostic>();
    private List<LLMDecisionRecord> llmDecisionRecords = new List<LLMDecisionRecord>();
    private string strategy;
    private int runID;
    private int totalSteps;
    private float totalTime;
    private string dataFolderPath;
    private string exportPrefix;
    private string runMetadata = "{}";
    private string automaticRecordRoot, automaticRecordPurpose;
    public void EnableAutomaticLogging(string root,string purpose)
    {automaticRecordRoot=Path.GetFullPath(root);automaticRecordPurpose=purpose;}
    private string termination = "unknown";
    private double wallClockSeconds;
    private int apiRequests, mockDecisions;
    public void SetRuntimeMetrics(double seconds, int requests, int mocks)
    { wallClockSeconds = seconds; apiRequests = requests; mockDecisions = mocks; }
    private List<string> trajectories = new List<string>();
    private List<string> volunteerWork = new List<string>();
    private readonly List<string> obstacleStates=new List<string>();
    private readonly List<string> obstacleEvents=new List<string>();
    private readonly List<string> paperDecisions=new List<string>();
    private readonly List<string> coordinationSnapshots=new List<string>(),coordinationProposals=new List<string>(),reservationEvents=new List<string>();
    public void RecordCoordination(Coordination.Snapshot snapshot,Coordination.Proposal proposal)
    {coordinationSnapshots.Add(JsonUtility.ToJson(snapshot));coordinationProposals.Add(JsonUtility.ToJson(proposal));}
    public string CoordinationTracePath => Path.Combine(dataFolderPath,exportPrefix+"_coordination_trace.jsonl");
    [Serializable] private sealed class DispatchApplication {public int step;public string snapshotId,error;public bool applied;}
    public void RecordDispatchApplication(Coordination.Snapshot snapshot,bool applied,string error)
    {File.AppendAllText(Path.Combine(dataFolderPath,exportPrefix+"_coordination_application.jsonl"),
        JsonUtility.ToJson(new DispatchApplication {step=snapshot.step,snapshotId=snapshot.snapshotId,applied=applied,error=error})+Environment.NewLine);}
    public void RecordDispatchAudit(Coordination.DispatchAudit audit)
    {File.AppendAllText(CoordinationTracePath,JsonUtility.ToJson(audit)+Environment.NewLine);}
    public void RecordDispatchStart(Coordination.Snapshot snapshot,string payload)
    {File.AppendAllText(Path.Combine(dataFolderPath,exportPrefix+"_coordination_requests.jsonl"),
        JsonUtility.ToJson(new Coordination.DispatchAudit {protocol=Coordination.LLMDispatchProtocol.Version,step=snapshot.step,snapshot=JsonUtility.ToJson(snapshot),payload=payload,execution="pending"})+Environment.NewLine);}
    public void RecordReservation(int step,Coordination.ReservationEvent e)
    {reservationEvents.Add($"{step},{e.agentId},{e.obstacleId},{Csv(e.action)},{Csv(e.reason)}");}
    private readonly List<string> agentEffort=new List<string>();
    public void RecordAgentEffort(int step,int agent,int obstacle) { agentEffort.Add($"{step},{agent},{obstacle}"); }
    private readonly List<string> agentObservations=new List<string>();
    public void RecordAgentObservation(int step,int agent,int obstacle,string observation,bool willing,string source)
    { agentObservations.Add($"{step},{agent},{obstacle},{Csv(observation)},{willing},{Csv(source)}"); }
    public void RecordObstacleState(int step,PaperObstacle obstacle)
    { obstacleStates.Add($"{step},{obstacle.id},{obstacle.position.x},{obstacle.position.y},{obstacle.status},{obstacle.worker},{obstacle.hasDestination},{obstacle.destination.x},{obstacle.destination.y}"); }
    public void RecordObstacleEvent(int step,PaperObstacle obstacle,string action,int agent)
    { obstacleEvents.Add($"{step},{obstacle.id},{agent},{obstacle.position.x},{obstacle.position.y},{Csv(action)},{obstacle.destination.x},{obstacle.destination.y}"); }
    public void RecordPaperDecision(int step,int agent,int obstacle,int players,float tau,bool willing,string source)
    { paperDecisions.Add(FormattableString.Invariant($"{step},{agent},{obstacle},{players},{tau:F6},{willing},{Csv(source)}")); }
    private void ExportRows(string suffix,string header,List<string> rows)
    {
        if(rows.Count==0) return;
        using(var writer=new StreamWriter(Path.Combine(dataFolderPath,exportPrefix+suffix)))
        {writer.WriteLine(header);foreach(var row in rows) writer.WriteLine(row);}
    }
    public void RecordVolunteerWork(int step, int agentID, int obstacleID, int work, bool completed)
    { volunteerWork.Add($"{step},{agentID},{obstacleID},{work},{completed}"); }
    public int EvacuationRecordCount => agentRecords.Count;
    public string DataFolderPath => dataFolderPath;
    public string DecisionTracePath => Path.Combine(dataFolderPath,exportPrefix+"_agent_trace.jsonl");

    public void SetRunMetadata(string json) { runMetadata = json; }
    public void SetTermination(string reason) { termination = reason; }
    public void RecordPosition(int step, int agentID, Vector2Int position, string role, bool evacuated)
    {
        trajectories.Add($"{step},{agentID},{position.x},{position.y},{role},{evacuated}");
    }
    public static string Csv(string value) => "\"" + (value ?? "").Replace("\"", "\"\"") + "\"";
    public static double Mean(IReadOnlyList<float> values)
    {
        if (values.Count == 0) return double.NaN;
        double sum = 0;
        foreach (float value in values) sum += value;
        return sum / values.Count;
    }
    public static double PopulationStd(IReadOnlyList<float> values)
    {
        double mean = Mean(values), sum = 0;
        foreach (float value in values) sum += (value - mean) * (value - mean);
        return values.Count == 0 ? double.NaN : Math.Sqrt(sum / values.Count);
    }
    
    private float paramKStatic;
    private float paramKDynamic;
    private float paramKAnticipation;
    private float paramTemperature;
    private int initialAgentCount;
    private int initialObstacleCount;

    public SimulationData(string strategy, int runID = 1, string outputFolder = null, string experimentID = null,
        string automaticRoot=null,string purpose=null)
    {
        this.strategy = strategy;
        this.runID = runID;
        this.dataFolderPath = outputFolder ?? Path.Combine(Application.isEditor ? Application.dataPath : Application.persistentDataPath, "data");
        exportPrefix = $"{experimentID ?? DateTime.UtcNow.ToString("yyyy-MM-dd_HHmmss_fff") + "_" + Guid.NewGuid().ToString("N").Substring(0, 8)}_run{runID:D3}_{strategy}";
        if(automaticRoot!=null)
        {
            EnableAutomaticLogging(automaticRoot,purpose??"Unspecified test purpose");
            if(outputFolder==null) dataFolderPath=AutomaticExperimentLog.RunFolder(automaticRoot,automaticRecordPurpose,exportPrefix);
        }

        if (!Directory.Exists(dataFolderPath))
        {
            Directory.CreateDirectory(dataFolderPath);
            Debug.Log("Data folder created at: " + dataFolderPath);
        }
    }

    public void SetSimulationParameters(float ks, float kd, float ka, float temp, int agentCount, int obstacleCount)
    {
        paramKStatic = ks;
        paramKDynamic = kd;
        paramKAnticipation = ka;
        paramTemperature = temp;
        initialAgentCount = agentCount;
        initialObstacleCount = obstacleCount;
    }

    public void RecordStepDiagnostics(int step, int agentsRemaining, int conflictCount, int volunteerActions, 
                                      int obstaclesRemaining, float avgDFF, float avgAFF)
    {
        StepDiagnostic diag = new StepDiagnostic
        {
            step = step,
            agentsRemaining = agentsRemaining,
            conflictCount = conflictCount,
            volunteerActions = volunteerActions,
            obstaclesRemaining = obstaclesRemaining,
            avgDFFValue = avgDFF,
            avgAFFValue = avgAFF
        };
        diagnostics.Add(diag);
    }

    public void RecordAgentEvacuation(int agentID, int step, float time)
    {
        AgentEvacuationRecord record = new AgentEvacuationRecord
        {
            agentID = agentID,
            evacuationStep = step,
            evacuationTime = time
        };
        agentRecords.Add(record);
    }

    public void RecordLLMDecision(int step, int agentID, string decision, string explanation, string source = "api", string fallbackReason = "")
    {
        LLMDecisionRecord record = new LLMDecisionRecord
        {
            step = step,
            agentID = agentID,
            decision = decision,
            explanation = explanation,
            source = source,
            fallbackReason = fallbackReason
        };
        llmDecisionRecords.Add(record);
    }

    public void SetSimulationStats(int totalSteps, float totalTime)
    {
        this.totalSteps = totalSteps;
        this.totalTime = totalTime;
    }

    public void ExportData()
    {
        if(coordinationSnapshots.Count>0) File.WriteAllLines(Path.Combine(dataFolderPath,exportPrefix+"_coordination_snapshots.jsonl"),coordinationSnapshots);
        if(coordinationProposals.Count>0) File.WriteAllLines(Path.Combine(dataFolderPath,exportPrefix+"_coordination_proposals.jsonl"),coordinationProposals);
        ExportRows("_reservation_events.csv","Step,AgentID,ObstacleID,Action,Reason",reservationEvents);
        ExportRows("_agent_effort.csv","Step,AgentID,ObstacleID",agentEffort);
        ExportRows("_agent_observations.csv","Step,AgentID,ObstacleID,ObservationJSON,Willing,Source",agentObservations);
        ExportRows("_obstacles.csv","Step,ObstacleID,X,Y,Status,WorkerID,HasDestination,DestinationX,DestinationY",obstacleStates);
        ExportRows("_obstacle_events.csv","Step,ObstacleID,AgentID,X,Y,Action,DestinationX,DestinationY",obstacleEvents);
        ExportRows("_paper_decisions.csv","Step,AgentID,ObstacleID,Players,ExitNonBlockage,Willing,Source",paperDecisions);
        File.WriteAllText(Path.Combine(dataFolderPath, exportPrefix + "_config.json"), runMetadata);
        using (var writer = new StreamWriter(Path.Combine(dataFolderPath, exportPrefix + "_volunteer_work.csv")))
        {
            writer.WriteLine("Step,AgentID,ObstacleID,AccumulatedWorkSteps,Completed");
            foreach (string row in volunteerWork) writer.WriteLine(row);
        }
        using (var writer = new StreamWriter(Path.Combine(dataFolderPath, exportPrefix + "_trajectories.csv")))
        {
            writer.WriteLine("Step,AgentID,X,Y,Role,Evacuated");
            foreach (string row in trajectories) writer.WriteLine(row);
        }
        ExportParameterSnapshot();
        ExportAgentData();
        ExportGlobalStats();
        ExportDiagnostics();
        ExportLLMDecisions();
        if(automaticRecordRoot!=null)
        {
            var record=new AutomaticExperimentRecord {recordID=exportPrefix,purpose=automaticRecordPurpose,
                recordedAtUtc=DateTime.UtcNow.ToString("o"),configuration=JsonUtility.FromJson<ResearchRunConfiguration>(runMetadata),
                termination=termination,stopStep=totalSteps,evacuated=agentRecords.Count,apiLogicalCalls=apiRequests,
                willingDecisions=paperDecisions.Count(row=>row.Split(',')[5]=="True"),
                refusalDecisions=llmDecisionRecords.Count(row=>row.decision=="selfish"),
                activations=obstacleEvents.Count(row=>row.Contains(",\"activate\",")),
                settled=obstacleEvents.Count(row=>row.Contains(",\"settle\",")),
                push=obstacleEvents.Count(row=>row.Contains(",\"push\",")),pull=obstacleEvents.Count(row=>row.Contains(",\"pull\",")),
                rotate=obstacleEvents.Count(row=>row.Contains(",\"rotate\",")),
                interpretation=termination=="completed" ? "Full evacuation observed. A single run is not a statistical policy comparison." :
                    "Full evacuation was not observed. Stop step is not T100; preserve the termination reason when analyzing this run."};
            try
            {
                string destination=AutomaticExperimentLog.Publish(automaticRecordRoot,dataFolderPath,record);
                Debug.Log("[EXPERIMENT LOG] Automatically recorded "+exportPrefix+" at "+destination);
            }
            catch(Exception error) when(error is IOException || error is UnauthorizedAccessException)
            {
                File.WriteAllText(Path.Combine(dataFolderPath,exportPrefix+"_notebook_pending.json"),JsonUtility.ToJson(record,true));
                Debug.LogError("[EXPERIMENT LOG] Notebook publication pending ("+error.GetType().Name+"). Raw data and a retry record were preserved.");
            }
        }

        Debug.Log($"Data exported to {dataFolderPath}");
    }

    private void ExportParameterSnapshot()
    {
        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        string fileName = $"{exportPrefix}_params.csv";
        string filePath = Path.Combine(dataFolderPath, fileName);

        using (StreamWriter writer = new StreamWriter(filePath))
        {
            writer.WriteLine("RunID,Strategy,kStatic,kDynamic,kAnticipation,Temperature,InitialAgents,InitialObstacles");
            FormattableString formattedLine = $"run{runID:D3},{strategy},{paramKStatic:F4},{paramKDynamic:F4},{paramKAnticipation:F4},{paramTemperature:F4},{initialAgentCount},{initialObstacleCount}";
            writer.WriteLine(formattedLine.ToString(CultureInfo.InvariantCulture));
        }

        Debug.Log($"Parameter snapshot exported to {fileName}");
    }

    private void ExportAgentData()
    {
        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        string fileName = $"{exportPrefix}_agents.csv";
        string filePath = Path.Combine(dataFolderPath, fileName);

        using (StreamWriter writer = new StreamWriter(filePath))
        {
            writer.WriteLine("RunID,AgentID,EvacuationStep,EvacuationTime");

            foreach (var record in agentRecords)
            {
                FormattableString formattedLine = $"run{runID:D3},{record.agentID},{record.evacuationStep},{record.evacuationTime:F2}";
                writer.WriteLine(formattedLine.ToString(CultureInfo.InvariantCulture));
            }
        }

        Debug.Log($"Agent data exported to {fileName}");
    }

    private void ExportGlobalStats()
    {
        var times = new List<float>();
        foreach (var record in agentRecords) times.Add(record.evacuationTime);
        double avgTime = Mean(times);
        double stdTime = PopulationStd(times);
        float maxTime = times.Count == 0 ? float.NaN : Mathf.Max(times.ToArray());
        float minTime = times.Count == 0 ? float.NaN : Mathf.Min(times.ToArray());

        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        string fileName = $"{exportPrefix}_global.csv";
        string filePath = Path.Combine(dataFolderPath, fileName);

        using (StreamWriter writer = new StreamWriter(filePath))
        {
            writer.WriteLine("RunID,Strategy,TotalSteps,TotalTime,AvgTimePerAgent,MaxTime,MinTime,StdTime,EvacuatedCount,Termination,WallClockSeconds,ApiRequests,MockDecisions");
            FormattableString formattedLine = $"run{runID:D3},{strategy},{totalSteps},{totalTime:F2},{avgTime:F2},{maxTime:F2},{minTime:F2},{stdTime:F2},{agentRecords.Count},{termination},{wallClockSeconds:F4},{apiRequests},{mockDecisions}";
            writer.WriteLine(formattedLine.ToString(CultureInfo.InvariantCulture));
        }

        Debug.Log($"Global stats exported to {fileName}");
    }

    private void ExportDiagnostics()
    {
        if (diagnostics.Count == 0)
            return;

        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        string fileName = $"{exportPrefix}_diagnostics.csv";
        string filePath = Path.Combine(dataFolderPath, fileName);

        using (StreamWriter writer = new StreamWriter(filePath))
        {
            writer.WriteLine("Step,AgentsRemaining,ConflictCount,VolunteerActions,ObstaclesRemaining,AvgDFF,AvgAFF");

            foreach (var diag in diagnostics)
            {
                FormattableString formattedLine = $"{diag.step},{diag.agentsRemaining},{diag.conflictCount},{diag.volunteerActions},{diag.obstaclesRemaining},{diag.avgDFFValue:F4},{diag.avgAFFValue:F4}";
                writer.WriteLine(formattedLine.ToString(CultureInfo.InvariantCulture));
            }
        }

        Debug.Log($"Diagnostics exported to {fileName}");
    }

    private void ExportLLMDecisions()
    {
        if (llmDecisionRecords.Count == 0)
            return;

        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        string fileName = $"{exportPrefix}_llm_decisions.csv";
        string filePath = Path.Combine(dataFolderPath, fileName);

        using (StreamWriter writer = new StreamWriter(filePath))
        {
            writer.WriteLine("Step,AgentID,Decision,Explanation,Source,FallbackReason");
            foreach (var record in llmDecisionRecords)
            {
                FormattableString formattedLine = $"{record.step},{record.agentID},{Csv(record.decision)},{Csv(record.explanation)},{Csv(record.source)},{Csv(record.fallbackReason)}";
                writer.WriteLine(formattedLine.ToString(CultureInfo.InvariantCulture));
            }
        }

        Debug.Log($"LLM decisions exported to {fileName}");
    }
}
