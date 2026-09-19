using UnityEngine;
using System.Collections;
using System.Collections.Generic;

public class VolunteerDilemma
{
    public enum DecisionMode
    {
        Probabilistic,
        LLM
    }

    public enum CooperationLevel
    {
        Selfish,
        Neutral,
        Cooperative
    }

    private AgentManager agentManager;
    private GridWorld world;
    private StaticFloorField floorField;

    public DecisionMode decisionMode = DecisionMode.Probabilistic;
    public LLMDecisionPolicy llmPolicy;

    public float volunteerCost = 1.0f;
    public float volunteerBenefit = 2.0f;

    private int helpActions = 0;
    private int cooperativeCount = 0;

    public VolunteerDilemma(AgentManager agentManager, GridWorld world, StaticFloorField floorField)
    {
        this.agentManager = agentManager;
        this.world = world;
        this.floorField = floorField;
    }

    public void SetLLMPolicy(LLMDecisionPolicy policy)
    {
        llmPolicy = policy;
    }

    public IEnumerator DecideVolunteerActionAsync(PedestrianAgent volunteer, System.Action<CooperationLevel, string> callback)
    {
        Vector2Int defaultObstacle = new Vector2Int(-1, -1);
        yield return DecideVolunteerActionAsync(volunteer, defaultObstacle, -1f, 0, 0f, callback);
    }

    public IEnumerator DecideVolunteerActionAsync(
        PedestrianAgent volunteer,
        Vector2Int targetObstacle,
        float targetObstacleToExitDistance,
        int evacueesNearTargetObstacle,
        float estimatedEvacuationImpact,
        System.Action<CooperationLevel, string> callback)
    {
        if (decisionMode != DecisionMode.LLM || llmPolicy == null)
        {
            callback?.Invoke(DecideVolunteerAction(volunteer), string.Empty);
            yield break;
        }

        Vector2Int volunteerPos = volunteer.GetGridPos();
        List<PedestrianAgent> nearbyAgents = agentManager.GetAgentsNearPosition(volunteerPos, 3);

        int activeAgents = 0;
        foreach (PedestrianAgent agent in nearbyAgents)
        {
            if (!agent.IsEvacuated() && agent.GetRole() == PedestrianAgent.Role.Evacuee)
            {
                activeAgents++;
            }
        }

        LLMDecisionPolicy.VolunteerContext context = new LLMDecisionPolicy.VolunteerContext
        {
            agentId = volunteer.gameObject.GetInstanceID(),
            role = volunteer.GetRole().ToString(),
            positionX = volunteerPos.x,
            positionY = volunteerPos.y,
            nearbyAgents = Mathf.Max(0, activeAgents),
            distanceToExit = floorField.GetDistance(volunteerPos),
            currentVolunteers = agentManager.GetAgentsByRole(PedestrianAgent.Role.Volunteer).Count,
            nearbyObstacles = world.GetObstaclePositions().Count,
            nearbyObstaclePositions = GetNearbyObstaclePositions(volunteerPos, 5),
            mapWidth = world.width,
            mapHeight = world.height,
            targetObstacleX = targetObstacle.x,
            targetObstacleY = targetObstacle.y,
            targetObstacleToExitDistance = targetObstacleToExitDistance,
            evacueesNearTargetObstacle = Mathf.Max(0, evacueesNearTargetObstacle),
            estimatedEvacuationImpact = Mathf.Clamp01(estimatedEvacuationImpact)
        };

        yield return llmPolicy.RequestVolunteerDecision(context, (decision, explanation) =>
        {
            callback?.Invoke(decision, explanation);
        });
    }

    public CooperationLevel DecideVolunteerAction(PedestrianAgent volunteer)
    {
        if (volunteer.GetRole() != PedestrianAgent.Role.Volunteer)
            return CooperationLevel.Selfish;

        Vector2Int volunteerPos = volunteer.GetGridPos();
        List<PedestrianAgent> nearbyAgents = agentManager.GetAgentsNearPosition(volunteerPos, 3);

        int activeAgents = 0;
        foreach (PedestrianAgent agent in nearbyAgents)
        {
            if (!agent.IsEvacuated() && agent.GetRole() == PedestrianAgent.Role.Evacuee)
            {
                activeAgents++;
            }
        }

        if (activeAgents == 0)
        {
            return CooperationLevel.Selfish;
        }

        // Volunteer dilemma probability model: q = (c/a)^(1/(N-1))
        int N = Mathf.Max(2, activeAgents + 1);
        float q;
        if (N <= 2)
        {
            q = 1f;
        }
        else
        {
            q = Mathf.Pow(volunteerCost / Mathf.Max(volunteerBenefit, 0.001f), 1f / (N - 1));
            q = Mathf.Clamp01(q);
        }

        float sample = Random.value;
        if (sample <= q)
        {
            return CooperationLevel.Cooperative;
        }
        else if (sample <= q + (1f - q) * 0.5f)
        {
            return CooperationLevel.Neutral;
        }
        else
        {
            return CooperationLevel.Selfish;
        }
    }

    public void ExecuteVolunteerAction(PedestrianAgent volunteer, CooperationLevel level)
    {
        if (level == CooperationLevel.Selfish)
        {
            return;
        }

        Vector2Int targetObstacle;
        if (!TryGetNearestRemovableObstacle(volunteer.GetGridPos(), 2, out targetObstacle))
        {
            return;
        }

        ExecuteVolunteerActionAtObstacle(volunteer, level, targetObstacle);
    }

    public bool TryGetNearestRemovableObstacle(Vector2Int center, int radius, out Vector2Int obstaclePos)
    {
        obstaclePos = new Vector2Int(-1, -1);
        List<Vector2Int> obstacles = world.GetObstaclePositions();
        float bestDist = float.MaxValue;

        foreach (Vector2Int obstacle in obstacles)
        {
            float dist = Mathf.Abs(obstacle.x - center.x) + Mathf.Abs(obstacle.y - center.y);
            if (dist <= radius && dist < bestDist)
            {
                bestDist = dist;
                obstaclePos = obstacle;
            }
        }

        return obstaclePos.x >= 0;
    }

    public void ExecuteVolunteerActionAtObstacle(PedestrianAgent volunteer, CooperationLevel level, Vector2Int obstaclePos)
    {
        if (level == CooperationLevel.Selfish)
        {
            return;
        }

        Vector2Int volunteerPos = volunteer.GetGridPos();
        List<PedestrianAgent> nearbyAgents = agentManager.GetAgentsNearPosition(volunteerPos, 2);

        foreach (PedestrianAgent agent in nearbyAgents)
        {
            if (!agent.IsEvacuated() && agent.GetRole() == PedestrianAgent.Role.Evacuee)
            {
                if (level == CooperationLevel.Cooperative)
                {
                    agent.ReceiveHelp();
                    helpActions++;
                    cooperativeCount++;
                }
                else if (level == CooperationLevel.Neutral)
                {
                    if (Random.value < 0.5f)
                    {
                        agent.ReceiveHelp();
                        helpActions++;
                    }
                }
            }
        }

        if (level == CooperationLevel.Cooperative || level == CooperationLevel.Neutral)
        {
            bool removedObstacle = world.RemoveObstacleAt(obstaclePos.x, obstaclePos.y);
            if (removedObstacle)
            {
                Debug.Log("Volunteer removed obstacle at " + obstaclePos);
            }
        }
    }

    public int GetHelpActionsCount()
    {
        return helpActions;
    }

    public int GetCooperativeVolunteers()
    {
        return cooperativeCount;
    }

    public void Reset()
    {
        helpActions = 0;
        cooperativeCount = 0;
    }

    private string[] GetNearbyObstaclePositions(Vector2Int center, int radius)
    {
        List<string> positions = new List<string>();
        List<Vector2Int> obstacles = world.GetObstaclePositions();
        
        foreach (Vector2Int obstacle in obstacles)
        {
            int distance = Mathf.Abs(obstacle.x - center.x) + Mathf.Abs(obstacle.y - center.y);
            if (distance <= radius)
            {
                positions.Add($"({obstacle.x},{obstacle.y})");
            }
        }
        
        return positions.ToArray();
    }
}
