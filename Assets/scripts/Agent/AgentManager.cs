using UnityEngine;
using System.Collections.Generic;

public class AgentManager
{
    private GridWorld world;
    private GameObject agentPrefab;
    private List<PedestrianAgent> agents = new List<PedestrianAgent>();
    private Transform agentsContainer;

    public AgentManager(GridWorld world, GameObject prefab)
    {
        this.world = world;
        this.agentPrefab = prefab;

        if (agentPrefab == null)
        {
            agentPrefab = CreateDefaultAgentPrefab();
        }

        agentsContainer = new GameObject("Agents").transform;
    }

    public PedestrianAgent SpawnAgent(Vector2Int gridPos)
    {
        if (world == null)
        {
            Debug.LogError("GridWorld not set in AgentManager!");
            return null;
        }

        GameObject agentGO = Object.Instantiate(agentPrefab, agentsContainer);
        agentGO.name = "Agent_" + agents.Count;

        PedestrianAgent agent = agentGO.GetComponent<PedestrianAgent>();
        if (agent == null)
        {
            agent = agentGO.AddComponent<PedestrianAgent>();
        }

        agent.Init(world, gridPos);

        agents.Add(agent);

        return agent;
    }

    public PedestrianAgent SpawnAgent(Vector2Int gridPos, PedestrianAgent.Role role)
    {
        PedestrianAgent agent = SpawnAgent(gridPos);
        if (agent != null)
        {
            agent.SetRole(role);
        }
        return agent;
    }

    public void DestroyAgent(PedestrianAgent agent)
    {
        if (agents.Contains(agent))
        {
            agents.Remove(agent);
            Object.Destroy(agent.gameObject);
        }
    }
    public void DestroyAllAgents()
    {
        foreach (PedestrianAgent agent in agents)
        {
            Object.Destroy(agent.gameObject);
        }
        agents.Clear();
        Debug.Log("All agents destroyed");
    }

    public List<PedestrianAgent> GetAgents()
    {
        return new List<PedestrianAgent>(agents);
    }


    public int GetAgentCount()
    {
        return agents.Count;
    }

    public int GetEvacuatedCount()
    {
        int count = 0;
        foreach (PedestrianAgent agent in agents)
        {
            if (agent.IsEvacuated())
            {
                count++;
            }
        }
        return count;
    }

    public int GetRemainingCount()
    {
        return agents.Count - GetEvacuatedCount();
    }

    public PedestrianAgent GetAgentAtPosition(Vector2Int gridPos)
    {
        foreach (PedestrianAgent agent in agents)
        {
            if (!agent.IsEvacuated() && agent.GetGridPos() == gridPos)
            {
                return agent;
            }
        }
        return null;
    }

    public List<PedestrianAgent> GetAgentsNearPosition(Vector2Int gridPos, int radius)
    {
        List<PedestrianAgent> nearbyAgents = new List<PedestrianAgent>();
        
        foreach (PedestrianAgent agent in agents)
        {
            if (agent.IsEvacuated())
                continue;

            Vector2Int agentPos = agent.GetGridPos();
            int distance = Mathf.Abs(agentPos.x - gridPos.x) + Mathf.Abs(agentPos.y - gridPos.y);  // 曼哈顿距离
            
            if (distance <= radius)
            {
                nearbyAgents.Add(agent);
            }
        }

        return nearbyAgents;
    }


    public List<PedestrianAgent> GetAgentsByRole(PedestrianAgent.Role role)
    {
        List<PedestrianAgent> roleAgents = new List<PedestrianAgent>();
        
        foreach (PedestrianAgent agent in agents)
        {
            if (agent.GetRole() == role)
            {
                roleAgents.Add(agent);
            }
        }

        return roleAgents;
    }

    private GameObject CreateDefaultAgentPrefab()
    {
        GameObject prefab = new GameObject("AgentPrefab");
        
        GameObject visual = GameObject.CreatePrimitive(PrimitiveType.Cube);
        visual.transform.SetParent(prefab.transform);
        visual.transform.localPosition = Vector3.zero;
        visual.transform.localScale = new Vector3(0.8f, 0.8f, 0.8f);
        
        Object.Destroy(visual.GetComponent<Collider>());
        Object.Destroy(visual.GetComponent<Rigidbody>());

        Renderer renderer = visual.GetComponent<Renderer>();
        if (renderer != null)
        {
            Material mat = new Material(Shader.Find("Standard"));
            mat.color = new Color(0.2f, 0.6f, 1f);
            renderer.material = mat;
        }

        prefab.AddComponent<PedestrianAgent>();

        Debug.Log("Created default agent prefab");
        return prefab;
    }

    public void PrintAgentStatistics()
    {
        Debug.Log("=== Agent Statistics ===");
        Debug.Log("Total agents: " + agents.Count);
        Debug.Log("Evacuated: " + GetEvacuatedCount());
        Debug.Log("Remaining: " + GetRemainingCount());
        
        int evacueeCount = GetAgentsByRole(PedestrianAgent.Role.Evacuee).Count;
        int volunteerCount = GetAgentsByRole(PedestrianAgent.Role.Volunteer).Count;
        Debug.Log("Evacuees: " + evacueeCount);
        Debug.Log("Volunteers: " + volunteerCount);
    }
}
