using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Coordination;
using Decision;
using UnityEngine;
using UnityEditor;

public static class StudyDatasetBuilder
{
    public static readonly string[] Groups={"A1","A2","A3","W1","W2","R0","R1"};
    [Serializable] public sealed class Cell {public string cellId,scenario;public int agents;}
    [Serializable] public sealed class Condition
    {public string cellId,groupId,conditionKey,executionMode,availabilityMode,policy,information;}
    [Serializable] public sealed class Inventory
    {public string schema="s5-condition-inventory-v1",model="gpt-4o-mini";public int horizon=200;public Cell[] cells;public Condition[] conditions;}
    [Serializable] private sealed class Capture
    {public string recordId,split,cellId,sourcePolicy,conditionKey,stateHash;public int seed,checkpoint,referenceLocalCount,referenceOptimalCount;public double referenceLocalCost,referenceOptimalCost;public bool absorbingTerminal;public Snapshot snapshot;}
    [Serializable] private sealed class Willingness
    {public string recordId,promptVersion,observation,prompt;public int nearbyAgentCount;public float exitNonBlockage,volunteerCost,failureCost,unwillingness,referenceProbability;}
    public static void Configure(SimulationManager m,Cell cell,string group)
    {
        m.obstacleHandlingMode=ObstacleHandlingMode.PaperRelocation;m.researchScenario=(ResearchScenario)Enum.Parse(typeof(ResearchScenario),cell.scenario);
        m.world.width=m.world.height=11;m.world.cellSize=.4f;m.agentCount=cell.agents;m.agentSpawnAreaSize=new Vector2Int(7,7);
        m.obstacleCount=5;m.exitCount=1;m.researchExitWidth=3;m.exitApproachDepth=2;
        m.maxSimulationSteps=200;m.stepInterval=.2f;m.movementStrategy=PedestrianAgent.MovementStrategy.Combined;
        m.kStatic=3;m.kDynamic=1;m.kAnticipation=5;m.movementTemperature=1;
        m.volunteerCost=.005f;m.failureCost=.5f;m.unwillingnessOmega=5;m.obstacleVisibilityRange=20;
        m.conflictStrategy=YielderGame.Strategy.PaperYielder;m.yielderDefectionCost=1;m.yielderFriction=0;
        m.paperDiffusion=.3f;m.paperDecay=.1f;m.paperAnticipationRadius=6;m.paperManipulationSteps=1;
        m.paperDestinationRule=PaperDestinationRule.NextToWallsOrObstacles;m.paperDestinationExitDistance=2;
        m.paperAbandonDensity=.01f;m.paperDensityWindow=10;m.paperReplanAfterSteps=10;m.paperExitWidthWeighting=true;m.paperSigmaMetric=PaperSigmaMetric.GridDistance;
        m.paperExecutionMode=group=="A1"?ExecutionMode.CoordinatedExtension:group=="A3"?ExecutionMode.LLMExtension:
            group=="R0" || group=="R1"?ExecutionMode.PaperReference:ExecutionMode.OptimizedExtension;
        m.coordinationAvailability=group.StartsWith("A",StringComparison.Ordinal)?AvailabilityMode.AllEligibleControl:AvailabilityMode.PolicyWillingness;
        m.volunteerDecisionMode=group=="W2"?SimulationManager.VolunteerDecisionMode.LLM:group=="R0"?SimulationManager.VolunteerDecisionMode.NoVolunteers:SimulationManager.VolunteerDecisionMode.OriginalGameTheory;
        m.agentInformation=AgentInformationCondition.Core;m.agentPromptWording=AgentPromptWording.Standard;m.openAIModel="gpt-4o-mini";
        m.maxAgentRequestsPerRun=100;m.maxCoordinationRequestsPerRun=20;m.coordinationMaxOutputTokens=1024;m.coordinationMaxPromptChars=60000;
        m.coordinationIdleSteps=30;m.coordinationCooldownSteps=5;m.allowMockFallback=false;m.batchRunCount=1;
        m.paperDecisionReplayPath="";m.coordinationReplayPath="";m.enableCoordinationLiveRequests=false;
    }
    public static Cell[] Cells() => new[]{"SingleBlockedExit","TwoExitsOneBlocked","RandomRoom"}
        .SelectMany(s=>new[]{8,16}.Select(n=>new Cell {cellId=s+"_n"+n,scenario=s,agents=n})).ToArray();
    public static void Build()
    {
        string output=Path.GetFullPath("research/s5/datasets");
        if(Directory.Exists(output))throw new IOException("Dataset output already exists; do not overwrite a study dataset");
        Directory.CreateDirectory(output);var conditions=new List<Condition>();
        foreach(var cell in Cells())foreach(string group in Groups)
        {
            var m=ResearchValidation.CreateManager(Path.GetFullPath("tmp/s5collector/config"));
            try{Configure(m,cell,group);conditions.Add(new Condition {cellId=cell.cellId,groupId=group,conditionKey=m.AgentConditionKey,
                executionMode=m.paperExecutionMode.ToString(),availabilityMode=m.coordinationAvailability.ToString(),policy=m.volunteerDecisionMode.ToString(),information=m.agentInformation.ToString()});}
            finally{ResearchValidation.Cleanup();}
        }
        File.WriteAllText(Path.Combine(output,"conditions.json"),JsonUtility.ToJson(new Inventory {cells=Cells(),conditions=conditions.ToArray()},true));
        using(var writer=new StreamWriter(Path.Combine(output,"snapshots.raw.jsonl")))
        foreach(string split in new[]{"Development","Calibration","FinalTest"})
        foreach(int seed in Enumerable.Range(split=="Development"?410001:split=="Calibration"?420001:430001,split=="FinalTest"?12:4))
        foreach(var cell in Cells())foreach(string source in new[]{"A1","A2"})
        {
            var m=ResearchValidation.CreateManager(Path.GetFullPath("tmp/s5collector/"+split+"_"+seed+"_"+cell.cellId+"_"+source));
            try
            {
                Configure(m,cell,source);m.baseSeed=seed;ResearchValidation.Begin(m);
                foreach(int checkpoint in new[]{1,10})
                {
                    while(m.IsSimulationRunning() && m.GetCurrentStep()<checkpoint)ResearchValidation.Step(m);
                    // Capture the actual pre-proposal decision state, not the empty graph after committing reservations.
                    var snapshot=m.GetCurrentStep()==checkpoint?m.PaperModel.LastCoordinationSnapshot:m.PaperModel.BuildCoordinationSnapshot(checkpoint,true);
                    var local=LocalDispatcher.Propose(snapshot);var optimal=OptimalDispatcher.Propose(snapshot);
                    string id=split+"_"+seed+"_"+cell.cellId+"_"+source+"_t"+checkpoint;
                    writer.WriteLine(JsonUtility.ToJson(new Capture {recordId=id,split=split,seed=seed,cellId=cell.cellId,sourcePolicy=source,
                        checkpoint=checkpoint,conditionKey=m.AgentConditionKey,absorbingTerminal=m.GetCurrentStep()<checkpoint,snapshot=snapshot,stateHash=CoordinationStudyPlan.Digest(JsonUtility.ToJson(snapshot)),
                        referenceLocalCount=local.assignments.Length,referenceOptimalCount=optimal.assignments.Length,referenceLocalCost=CoordinationSnapshotReplay.Cost(snapshot,local),referenceOptimalCost=CoordinationSnapshotReplay.Cost(snapshot,optimal)}));
                }
            }
            finally{m.ResetSimulation();ResearchValidation.Cleanup();}
        }
        using(var writer=new StreamWriter(Path.Combine(output,"willingness.raw.jsonl")))
        foreach(int n in new[]{1,2,4,8,16})foreach(float tau in new[]{0f,.25f,.5f,.75f})
        foreach(float cv in new[]{.005f,.1f})foreach(float av in new[]{.5f,.8f})foreach(float omega in new[]{1f,5f})
        {
            var context=new VolunteerDecisionContext {nearbyAgentCount=n,exitNonBlockage=tau,volunteerCost=cv,failureCost=av,unwillingness=omega};
            string observation=AgentObservation.Serialize(context,AgentInformationCondition.Core);
            writer.WriteLine(JsonUtility.ToJson(new Willingness {recordId="w_"+CoordinationStudyPlan.Digest(observation).Substring(0,20),
                promptVersion=AgentObservation.PromptVersion,observation=observation,prompt=PaperVolunteerPrompt.Build(observation,AgentInformationCondition.Core.ToString(),AgentPromptWording.Standard),
                nearbyAgentCount=n,exitNonBlockage=tau,volunteerCost=cv,failureCost=av,unwillingness=omega,
                referenceProbability=new OriginalGameTheoryVolunteerStrategy().CalculateVolunteerProbability(context)}));
        }
        Debug.Log("S5_DATASET_CAPTURED: 480 snapshots from predeclared short offline rollouts; 160 analytical willingness contexts; no APIs, no formal comparative runs");
    }
}

public sealed class CoordinationStudySetup : EditorWindow
{
    private string planPath="research/s5/coordination-study.lock.json",jobID="";
    [MenuItem("Research/Coordination/Configure scheduled study job (no run)")]
    public static void Open() => GetWindow<CoordinationStudySetup>("Study setup");
    private void OnGUI()
    {
        planPath=EditorGUILayout.TextField("Locked plan",planPath);jobID=EditorGUILayout.TextField("Job ID",jobID);
        EditorGUILayout.HelpBox("Use a closed-loop job ID from schedule.jsonl. This only configures the open scene; it does not run or enable API requests.",MessageType.Info);
        if(!GUILayout.Button("Apply scheduled job to scene"))return;
        string id;var plan=CoordinationStudyPlan.Read(planPath,out id);var job=plan.jobs.Single(j=>j.jobID==jobID && j.kind=="closed_loop");
        var m=UnityEngine.Object.FindFirstObjectByType<SimulationManager>();if(m==null)throw new InvalidOperationException("Open the simulation scene first");
        if(m.IsSimulationRunning())throw new InvalidOperationException("Stop the current simulation before configuration");
        Undo.RecordObject(m,"Configure study job");Undo.RecordObject(m.world,"Configure study world");
        StudyDatasetBuilder.Configure(m,StudyDatasetBuilder.Cells().Single(c=>c.cellId==job.cellId),job.groupId);
        m.baseSeed=job.seed;m.agentResearchPhase=(AgentResearchPhase)Enum.Parse(typeof(AgentResearchPhase),job.phase);
        m.lockedStudyPlanPath="";m.lockedCoordinationStudyPlanPath=planPath;m.recordExperimentsAutomatically=true;
        m.experimentPurpose="Locked S5 "+job.groupId+" / "+job.cellId+" / "+job.phase;
        EditorUtility.SetDirty(m);EditorUtility.SetDirty(m.world);
        Debug.Log("Scheduled study job configured without running: "+job.jobID+". Live dispatch remains disabled.");
    }
}
