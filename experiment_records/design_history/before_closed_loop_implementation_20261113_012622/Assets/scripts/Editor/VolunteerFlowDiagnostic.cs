using System;
using System.Collections;
using System.IO;
using UnityEngine;

/// <summary>Single-step integration fixture; injected decision, no network and no research exports.</summary>
public static class VolunteerFlowDiagnostic
{
    private static int calls;
    private static IEnumerator Participate(PedestrianAgent agent,PaperObstacle obstacle,
        Decision.VolunteerDecisionContext context,Action<bool?,string,string> callback)
    { calls++;callback(true,"injected functional-test answer","test_fixture");yield break; }

    public static void Run()
    {
        PaperAgentContractValidation.Run();
        var randomState=UnityEngine.Random.state;
        SimulationManager manager=null;
        try
        {
            manager=ResearchValidation.CreateManager(Path.GetFullPath("tmp/volunteer-flow-diagnostic"));
            manager.obstacleHandlingMode=ObstacleHandlingMode.PaperRelocation;
            manager.volunteerDecisionMode=SimulationManager.VolunteerDecisionMode.LLM;
            manager.researchScenario=ResearchScenario.SingleBlockedExit;
            manager.obstacleCount=1;manager.obstacleVisibilityRange=20;manager.paperManipulationSteps=2;
            ResearchValidation.Begin(manager);
            var agent=manager.GetAllAgents()[0];agent.Init(manager.world,new Vector2Int(3,2));
            var engine=new PaperModelEngine(manager,manager.world,manager.GetAllAgents(),
                new DynamicFloorField(manager.world),new AnticipationFloorField(manager.world),
                new Decision.YielderGame(Decision.YielderGame.Strategy.PaperYielder),Participate);
            if(engine.InitialBlockedTaskCount!=1) throw new Exception("Blocked-exit fixture did not expose one recruitment task");
            calls=0;
            var data=new SimulationData("functional-test-only",1,Path.GetFullPath("tmp/volunteer-flow-diagnostic"));
            ResearchValidation.Drain(engine.PrepareStep(1,data));
            if(calls!=1 || !engine.Knowledge[agent.AgentID].willing.Contains(0) ||
                !agent.IsActiveVolunteer() || engine.Obstacles[0].worker!=agent.AgentID || manager.GetVolunteerCount()!=1)
                throw new Exception("Willing decision did not reach an active volunteer");
            Debug.Log("VOLUNTEER_FLOW_DIAGNOSTIC_PASSED: one injected decision -> willing list -> active handler; no API, no research export");
        }
        finally
        {
            if(manager!=null) manager.ResetSimulation();
            ResearchValidation.Cleanup();UnityEngine.Random.state=randomState;
        }
    }
}
