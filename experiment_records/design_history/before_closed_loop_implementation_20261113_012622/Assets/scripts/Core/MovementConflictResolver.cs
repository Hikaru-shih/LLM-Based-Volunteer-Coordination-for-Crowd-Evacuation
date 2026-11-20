using System.Collections.Generic;
using UnityEngine;
using Decision;

/// <summary>Resolve targets, then propagate rejected moves until occupancy is unique.</summary>
public static class MovementConflictResolver
{
    public static int Resolve(List<PedestrianAgent> agents, YielderGame game)
    {
        var targets = new Dictionary<Vector2Int, List<PedestrianAgent>>();
        foreach (var agent in agents)
        {
            if (agent.IsEvacuated()) continue;
            if (!targets.TryGetValue(agent.desiredPos, out var contenders))
                targets[agent.desiredPos] = contenders = new List<PedestrianAgent>();
            contenders.Add(agent);
        }
        int conflicts = 0;
        foreach (var entry in targets)
        {
            if (entry.Value.Count < 2) continue;
            conflicts++;
            var occupant = entry.Value.Find(a => a.gridPos == entry.Key);
            var winner = occupant != null ? occupant : game.ResolveConflict(entry.Value);
            foreach (var agent in entry.Value)
                if (agent != winner) agent.desiredPos = agent.gridPos;
        }

        // A rejected agent now occupies its origin. Reject anyone entering that cell,
        // and repeat because that rejection can block an entire movement chain.
        bool changed;
        do
        {
            changed = false;
            var stationary = new HashSet<Vector2Int>();
            foreach (var agent in agents)
                if (!agent.IsEvacuated() && agent.desiredPos == agent.gridPos)
                    stationary.Add(agent.gridPos);
            foreach (var agent in agents)
            {
                if (agent.IsEvacuated() || agent.desiredPos == agent.gridPos) continue;
                if (!stationary.Contains(agent.desiredPos)) continue;
                agent.desiredPos = agent.gridPos;
                changed = true;
            }
        } while (changed);
        return conflicts;
    }
}
