using System.Collections.Generic;
using UnityEngine;

public class DynamicFloorField
{
    private GridWorld world;
    private float[,] values;

    public float decayRate = 0.1f;
    public float diffusionRate = 0.3f;
    public float trailStrength = 1.0f;

    public DynamicFloorField(GridWorld world)
    {
        this.world = world;
        values = new float[world.width, world.height];
        ResetField();
    }

    public void ResetField()
    {
        for (int x = 0; x < world.width; x++)
        {
            for (int y = 0; y < world.height; y++)
            {
                values[x, y] = 0f;
            }
        }
    }

    public void UpdateField(IEnumerable<PedestrianAgent> agents)
    {
        var occupied=new HashSet<Vector2Int>();
        if(world.paperNeighborhood) foreach(var agent in agents) if(!agent.IsEvacuated()) occupied.Add(agent.gridPos);
        foreach (var agent in agents)
            if (agent.ConsumeTrace(out var departed))
                values[departed.x, departed.y] += trailStrength;
        // decay and diffusion
        float[,] newValues = new float[world.width, world.height];

        for (int x = 0; x < world.width; x++)
        {
            for (int y = 0; y < world.height; y++)
            {
                float current = values[x, y];
                if (!world.IsWalkable(x, y))
                {
                    newValues[x, y] = (1f - Mathf.Clamp01(decayRate)) * current;
                    continue;
                }
                float neighborSum = 0f;
                int neighborCount = 0;

                foreach (Vector2Int dir in world.paperNeighborhood ? PaperGrid.Moore : PaperGrid.Cardinal)
                {
                    int nx = x + dir.x;
                    int ny = y + dir.y;
                    if (world.InBounds(nx, ny) && world.IsWalkable(nx, ny) && (!world.paperNeighborhood || !occupied.Contains(new Vector2Int(nx,ny))))
                    {
                        neighborSum += values[nx, ny];
                        neighborCount++;
                    }
                }

                float diffusionTerm = neighborCount > 0 ? neighborSum / neighborCount : current;
                float alpha = Mathf.Clamp01(diffusionRate);
                // Paper Eqs. (7)-(9), supported von Neumann neighborhood.
                newValues[x, y] = (1f - Mathf.Clamp01(decayRate)) *
                    ((1f - alpha) * current + alpha * diffusionTerm);
            }
        }

        values = newValues;

    }

    public float GetValue(int x, int y)
    {
        if (!world.InBounds(x, y))
            return 0f;
        return values[x, y];
    }

    public float GetValue(Vector2Int pos)
    {
        return GetValue(pos.x, pos.y);
    }
}
