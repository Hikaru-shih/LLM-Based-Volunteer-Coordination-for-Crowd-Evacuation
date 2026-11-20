using System;
using System.IO;
using UnityEngine;

// Same fixture and initial seed, with volunteering disabled; no network calls.
public static class NoVolunteersSmokeTest
{
    public static void Run()
    {
        string output=Path.Combine("D:/LLM-Based-Volunteer-Coordination-for-Crowd-Evacuation/tmp/no-volunteers-smoke-tests",DateTime.UtcNow.ToString("yyyyMMdd_HHmmss"));
        Directory.CreateDirectory(output);
        SimulationManager manager=null;
        try
        {
            manager=ResearchValidation.CreateManager(output);
            manager.recordExperimentsAutomatically=true;
            manager.experimentPurpose="Blocked-exit functional comparison: NoVolunteersSmokeTest";
            manager.experimentRecordsRootOverride="D:/LLM-Based-Volunteer-Coordination-for-Crowd-Evacuation/experiment_records";
            manager.obstacleHandlingMode=ObstacleHandlingMode.PaperRelocation;
            manager.volunteerDecisionMode=SimulationManager.VolunteerDecisionMode.NoVolunteers;
            manager.researchScenario=ResearchScenario.SingleBlockedExit;
            manager.world.cellSize=0.4f;manager.agentCount=2;manager.obstacleCount=5;
            manager.researchExitWidth=3;manager.obstacleVisibilityRange=20;
            manager.kStatic=3;manager.kDynamic=1;manager.kAnticipation=5;
            manager.movementTemperature=1;manager.volunteerCost=0.005f;manager.failureCost=0.5f;manager.unwillingnessOmega=5;
            manager.conflictStrategy=Decision.YielderGame.Strategy.PaperYielder;
            manager.movementStrategy=PedestrianAgent.MovementStrategy.Combined;
            manager.paperManipulationSteps=1;manager.paperDiffusion=0.3f;manager.paperDecay=0.1f;manager.paperAnticipationRadius=6;
            manager.yielderDefectionCost=1;manager.yielderFriction=0;
            manager.batchRunCount=1;manager.maxSimulationSteps=40;manager.maxAgentRequestsPerRun=12;
            manager.allowMockFallback=false;manager.openAIModel="gpt-4o-mini";manager.openAIKey="";
            manager.agentResearchPhase=AgentResearchPhase.Development;
            ResearchValidation.Begin(manager);
            int peakVolunteers=0;
            while(manager.IsSimulationRunning())
            {
                ResearchValidation.Step(manager);
                peakVolunteers=Math.Max(peakVolunteers,manager.GetVolunteerCount());
            }
            File.WriteAllText(Path.Combine(output,"smoke_status.json"),JsonUtility.ToJson(new Status {
                steps=manager.GetCurrentStep(),peakVolunteers=peakVolunteers,evacuated=manager.GetEvacuatedCount()},true));
            Debug.Log("NO_VOLUNTEERS_SMOKE_FINISHED: "+output);
        }
        finally {if(manager!=null) manager.ResetSimulation();ResearchValidation.Cleanup();}
    }
    [Serializable] private class Status {public int steps,peakVolunteers,evacuated;}
}
