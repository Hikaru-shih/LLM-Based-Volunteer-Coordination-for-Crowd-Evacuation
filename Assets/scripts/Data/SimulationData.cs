using UnityEngine;
using System.Collections.Generic;
using System.IO;

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
    }

    private List<AgentEvacuationRecord> agentRecords = new List<AgentEvacuationRecord>();
    private List<StepDiagnostic> diagnostics = new List<StepDiagnostic>();
    private List<LLMDecisionRecord> llmDecisionRecords = new List<LLMDecisionRecord>();
    private string strategy;
    private int runID;
    private int totalSteps;
    private float totalTime;
    private string dataFolderPath;
    
    private float paramKStatic;
    private float paramKDynamic;
    private float paramKAnticipation;
    private float paramTemperature;
    private int initialAgentCount;
    private int initialObstacleCount;

    public SimulationData(string strategy, int runID = 1)
    {
        this.strategy = strategy;
        this.runID = runID;
        this.dataFolderPath = Path.Combine(Application.dataPath, "data");

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

    public void RecordLLMDecision(int step, int agentID, string decision, string explanation)
    {
        LLMDecisionRecord record = new LLMDecisionRecord
        {
            step = step,
            agentID = agentID,
            decision = decision,
            explanation = explanation
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
        if (agentRecords.Count == 0)
        {
            Debug.LogWarning("No evacuation records to export");
            return;
        }

        ExportParameterSnapshot();
        ExportAgentData();
        ExportGlobalStats();
        ExportDiagnostics();
        ExportLLMDecisions();

        Debug.Log($"Data exported to {dataFolderPath}");
    }

    private void ExportParameterSnapshot()
    {
        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        string fileName = $"{timestamp}_run{runID:D3}_{strategy}_params.csv";
        string filePath = Path.Combine(dataFolderPath, fileName);

        using (StreamWriter writer = new StreamWriter(filePath))
        {
            writer.WriteLine("RunID,Strategy,kStatic,kDynamic,kAnticipation,Temperature,InitialAgents,InitialObstacles");
            string line = $"run{runID:D3},{strategy},{paramKStatic:F4},{paramKDynamic:F4},{paramKAnticipation:F4}," +
                          $"{paramTemperature:F4},{initialAgentCount},{initialObstacleCount}";
            writer.WriteLine(line);
        }

        Debug.Log($"Parameter snapshot exported to {fileName}");
    }

    private void ExportAgentData()
    {
        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        string fileName = $"{timestamp}_run{runID:D3}_{strategy}_agents.csv";
        string filePath = Path.Combine(dataFolderPath, fileName);

        using (StreamWriter writer = new StreamWriter(filePath))
        {
            writer.WriteLine("RunID,AgentID,EvacuationStep,EvacuationTime");

            foreach (var record in agentRecords)
            {
                string line = $"run{runID:D3},{record.agentID},{record.evacuationStep},{record.evacuationTime:F2}";
                writer.WriteLine(line);
            }
        }

        Debug.Log($"Agent data exported to {fileName}");
    }

    private void ExportGlobalStats()
    {
        float avgTime = agentRecords.Count > 0 ? totalTime / agentRecords.Count : 0;
        float maxTime = 0;
        float minTime = float.MaxValue;

        foreach (var record in agentRecords)
        {
            if (record.evacuationTime > maxTime)
                maxTime = record.evacuationTime;
            if (record.evacuationTime < minTime)
                minTime = record.evacuationTime;
        }

        float variance = 0f;
        if (agentRecords.Count > 0)
        {
            foreach (var record in agentRecords)
            {
                float diff = record.evacuationTime - avgTime;
                variance += diff * diff;
            }
            variance /= agentRecords.Count;
        }
        float stdTime = Mathf.Sqrt(variance);

        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        string fileName = $"{timestamp}_run{runID:D3}_{strategy}_global.csv";
        string filePath = Path.Combine(dataFolderPath, fileName);

        using (StreamWriter writer = new StreamWriter(filePath))
        {
            writer.WriteLine("RunID,Strategy,TotalSteps,TotalTime,AvgTimePerAgent,MaxTime,MinTime,StdTime,EvacuatedCount");
            string line = $"run{runID:D3},{strategy},{totalSteps},{totalTime:F2},{avgTime:F2},{maxTime:F2},{minTime:F2},{stdTime:F2},{agentRecords.Count}";
            writer.WriteLine(line);
        }

        Debug.Log($"Global stats exported to {fileName}");
    }

    private void ExportDiagnostics()
    {
        if (diagnostics.Count == 0)
            return;

        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        string fileName = $"{timestamp}_run{runID:D3}_{strategy}_diagnostics.csv";
        string filePath = Path.Combine(dataFolderPath, fileName);

        using (StreamWriter writer = new StreamWriter(filePath))
        {
            writer.WriteLine("Step,AgentsRemaining,ConflictCount,VolunteerActions,ObstaclesRemaining,AvgDFF,AvgAFF");

            foreach (var diag in diagnostics)
            {
                string line = $"{diag.step},{diag.agentsRemaining},{diag.conflictCount},{diag.volunteerActions}," +
                              $"{diag.obstaclesRemaining},{diag.avgDFFValue:F4},{diag.avgAFFValue:F4}";
                writer.WriteLine(line);
            }
        }

        Debug.Log($"Diagnostics exported to {fileName}");
    }

    private void ExportLLMDecisions()
    {
        if (llmDecisionRecords.Count == 0)
            return;

        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        string fileName = $"{timestamp}_run{runID:D3}_{strategy}_llm_decisions.csv";
        string filePath = Path.Combine(dataFolderPath, fileName);

        using (StreamWriter writer = new StreamWriter(filePath))
        {
            writer.WriteLine("Step,AgentID,Decision,Explanation");
            foreach (var record in llmDecisionRecords)
            {
                string line = $"{record.step},{record.agentID},{record.decision},\"{record.explanation.Replace("\"", "''")}\"";
                writer.WriteLine(line);
            }
        }

        Debug.Log($"LLM decisions exported to {fileName}");
    }
}
