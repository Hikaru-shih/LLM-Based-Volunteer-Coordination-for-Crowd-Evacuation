using System.Collections.Generic;
using UnityEngine;

public class AnticipationFloorField
{
    private GridWorld world;
    private float[,] values;

    public float influenceRadius = 3;
    public float baseValue = 0.2f;

    public AnticipationFloorField(GridWorld world)
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

    public void UpdateField(IEnumerable<PedestrianAgent> volunteers)
    {
        ResetField();

        foreach (var volunteer in volunteers)
        {
            if (volunteer.IsEvacuated())
                continue;

            Vector2Int center = volunteer.GetGridPos();

            for (int dx = -Mathf.RoundToInt(influenceRadius); dx <= Mathf.RoundToInt(influenceRadius); dx++)
            {
                for (int dy = -Mathf.RoundToInt(influenceRadius); dy <= Mathf.RoundToInt(influenceRadius); dy++)
                {
                    int nx = center.x + dx;
                    int ny = center.y + dy;

                    if (!world.InBounds(nx, ny))
                        continue;

                    float dist = Mathf.Sqrt(dx * dx + dy * dy);
                    if (dist <= influenceRadius)
                    {
                        float influence = Mathf.Lerp(baseValue, 0f, dist / influenceRadius);
                        values[nx, ny] = Mathf.Max(values[nx, ny], influence);
                    }
                }
            }
        }
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
