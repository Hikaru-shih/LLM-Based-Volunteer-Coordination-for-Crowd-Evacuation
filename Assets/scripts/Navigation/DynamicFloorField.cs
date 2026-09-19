using System.Collections.Generic;
using UnityEngine;

public class DynamicFloorField
{
    private GridWorld world;
    private float[,] values;

    public float decayRate = 0.95f;
    public float diffusionRate = 0.2f;
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
                values[x, y] = 1f; // neutral value
            }
        }
    }

    public void UpdateField(IEnumerable<PedestrianAgent> agents)
    {
        // decay and diffusion
        float[,] newValues = new float[world.width, world.height];

        for (int x = 0; x < world.width; x++)
        {
            for (int y = 0; y < world.height; y++)
            {
                float current = values[x, y];
                float neighborSum = 0f;
                int neighborCount = 0;

                foreach (Vector2Int dir in new Vector2Int[] { new Vector2Int(0, -1), new Vector2Int(0, 1), new Vector2Int(-1, 0), new Vector2Int(1, 0) })
                {
                    int nx = x + dir.x;
                    int ny = y + dir.y;
                    if (world.InBounds(nx, ny) && world.IsWalkable(nx, ny))
                    {
                        neighborSum += values[nx, ny];
                        neighborCount++;
                    }
                }

                float diffusionTerm = neighborCount > 0 ? neighborSum / neighborCount : 0f;
                newValues[x, y] = Mathf.Clamp01((1 - decayRate) * current + diffusionRate * diffusionTerm);
            }
        }

        values = newValues;

        // add trails where agents currently are
        foreach (var agent in agents)
        {
            if (!agent.IsEvacuated())
            {
                Vector2Int p = agent.GetGridPos();
                if (world.InBounds(p.x, p.y))
                {
                    values[p.x, p.y] *= 0.5f; // lower means more attractive
                }
            }
        }
    }

    public float GetValue(int x, int y)
    {
        if (!world.InBounds(x, y))
            return 1f;
        return values[x, y];
    }

    public float GetValue(Vector2Int pos)
    {
        return GetValue(pos.x, pos.y);
    }
}
