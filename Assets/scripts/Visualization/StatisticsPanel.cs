using UnityEngine;

public class StatisticsPanel : MonoBehaviour
{
    public SimulationManager simulationManager;

    void OnGUI()
    {
        if (simulationManager == null)
            return;

        int totalAgents = simulationManager.GetTotalAgents();
        int evacuated = simulationManager.GetEvacuatedCount();
        int volunteers = simulationManager.GetVolunteerCount();
        int evacuees = simulationManager.GetEvacueeCount();
        int obstacles = simulationManager.GetObstacleCount();
        int step = simulationManager.GetCurrentStep();

        GUILayout.BeginArea(new Rect(10, 10, 280, 190), "Simulation Stats", GUI.skin.window);
        GUILayout.Label("Step: " + step);
        GUILayout.Label("Evacuated: " + evacuated + " / " + totalAgents);
        GUILayout.Label("Volunteers: " + volunteers);
        GUILayout.Label("Evacuees: " + evacuees);
        GUILayout.Label("Obstacles: " + obstacles);
        GUILayout.Label("Running: " + simulationManager.IsSimulationRunning());
        GUILayout.Label("Conflict Strategy: " + simulationManager.GetConflictStrategyName());
        GUILayout.EndArea();
    }
}
