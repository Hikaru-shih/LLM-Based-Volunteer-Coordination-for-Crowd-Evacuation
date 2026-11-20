using System;
using System.IO;
using System.Linq;
using System.Reflection;
using Decision;
using UnityEditor;
using UnityEngine;

/// <summary>Offline validation matrix. Never sends requests or reads API credentials/PlayerPrefs.</summary>
public static class ResearchExperimentRunner
{
    public static void RunVerifiedOffline()
    {
        ResearchValidation.RunAll();
        RunOffline();
    }
    [MenuItem("Research/Run offline validation matrix (270 runs)")]
    public static void RunOffline()
    {
        string output = Path.GetFullPath(Path.Combine("tmp", "offline-experiments", DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")));
        Directory.CreateDirectory(output);
        var policies = new[] { SimulationManager.VolunteerDecisionMode.NoVolunteers,
            SimulationManager.VolunteerDecisionMode.OriginalGameTheory, SimulationManager.VolunteerDecisionMode.MockHeuristic };
        var scenarios = new[] { ResearchScenario.OpenRoom, ResearchScenario.SingleBlockedExit, ResearchScenario.TwoExitsOneBlocked };
        int runs = 0, checkedSteps = 0, originalCompletedRuns = 0;
        try
        {
            foreach (var scenario in scenarios)
            foreach (var policy in policies)
            {
                var manager = ResearchValidation.CreateManager(output);
                manager.world.width = manager.world.height = 30;
                manager.agentCount = 50;
                manager.agentSpawnAreaSize = new Vector2Int(24, 24);
                manager.researchScenario = scenario;
                manager.volunteerDecisionMode = policy;
                manager.obstacleCount = 3;
                manager.baseSeed = 2026;
                manager.maxSimulationSteps = 200; // Watchdog retained to expose regressions, not increased to pass.
                manager.kStatic = 3; manager.kDynamic = 1; manager.kAnticipation = 5;
                manager.movementStrategy = PedestrianAgent.MovementStrategy.Combined;
                manager.conflictStrategy = YielderGame.Strategy.PaperYielder;
                manager.volunteerCost = 0.005f; manager.failureCost = 0.5f; manager.unwillingnessOmega = 5;
                manager.volunteerSelectionInterval = 1; manager.obstacleActionRange = 1;
                manager.obstacleVisibilityRange = 20;
                for (int run = 1; run <= 30; run++)
                {
                    ResearchValidation.Begin(manager, run);
                    if (manager.GetTotalAgents() != manager.agentCount) throw new Exception("Spawn capacity invalidates matrix");
                    while (manager.IsSimulationRunning())
                    {
                        var before = manager.GetAllAgents().ToDictionary(a => a.AgentID, a => a.gridPos);
                        ResearchValidation.Step(manager);
                        checkedSteps++;
                        var agents = manager.GetAllAgents();
                        var live = agents.Where(a => !a.IsEvacuated()).ToArray();
                        if (policy == SimulationManager.VolunteerDecisionMode.OriginalGameTheory)
                            foreach (var active in live.Where(a => a.IsActiveVolunteer()))
                            {
                                var target = active.GetAssignedObstacle();
                                if (Mathf.Abs(active.gridPos.x - target.x) + Mathf.Abs(active.gridPos.y - target.y) != 1)
                                    throw new Exception("Paper volunteer activated before adjacency");
                            }
                        if (live.Select(a => a.gridPos).Distinct().Count() != live.Length)
                            throw new Exception("Duplicate occupancy in offline experiment");
                        foreach (var agent in agents)
                        {
                            var old = before[agent.AgentID];
                            if (Mathf.Abs(old.x - agent.gridPos.x) + Mathf.Abs(old.y - agent.gridPos.y) > 1)
                                throw new Exception("Nonlocal move in offline experiment");
                        }
                        var data = (SimulationData)typeof(SimulationManager).GetField("simulationData", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(manager);
                        if (data.EvacuationRecordCount != agents.Count(a => a.IsEvacuated()))
                            throw new Exception("Evacuation export count mismatch");
                        if (manager.currentStep > manager.maxSimulationSteps) throw new Exception("Step limit exceeded");
                    }
                    if (policy == SimulationManager.VolunteerDecisionMode.OriginalGameTheory)
                    {
                        if (manager.GetEvacuatedCount() != manager.GetTotalAgents())
                            throw new Exception($"Full evacuation regression: {scenario} seed={manager.baseSeed + run - 1}, evacuated={manager.GetEvacuatedCount()}/{manager.GetTotalAgents()}");
                        originalCompletedRuns++;
                    }
                    runs++;
                }
                manager.ResetSimulation();
                ResearchValidation.Cleanup();
            }
            File.WriteAllText(Path.Combine(output, "matrix_result.json"),
                $"{{\"passed\":true,\"runs\":{runs},\"checkedSteps\":{checkedSteps},\"originalCompletedRuns\":{originalCompletedRuns},\"watchdogSteps\":200,\"remoteRequests\":0,\"purpose\":\"full evacuation regression for original policy; not full paper relocation reproduction\"}}");
            Debug.Log($"OFFLINE_MATRIX_PASSED: {runs} runs, {checkedSteps} checked steps. Output: {output}");
        }
        finally { ResearchValidation.Cleanup(); }
    }
}
