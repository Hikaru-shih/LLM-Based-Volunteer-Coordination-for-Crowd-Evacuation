using System.Collections.Generic;
using UnityEngine;

public class AnticipationFloorField
{
    private GridWorld world;
    private float[,] values;

    public float influenceRadius = 6;
    public float baseValue = 3f;

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
            if (volunteer.IsEvacuated() || !volunteer.IsActiveVolunteer() || !volunteer.HasAssignedObstacle())
                continue;

            Vector2Int center = volunteer.GetGridPos();

            int extent = Mathf.CeilToInt(influenceRadius) + 2;
            for (int dx = -extent; dx <= extent; dx++)
            {
                for (int dy = -extent; dy <= extent; dy++)
                {
                    int nx = center.x + dx;
                    int ny = center.y + dy;

                    if (!world.InBounds(nx, ny))
                        continue;

                    values[nx, ny] += Contribution(center, volunteer.GetAssignedObstacle(),
                        new Vector2Int(nx, ny), influenceRadius);
                }
            }
        }
    }

    public static float PaperDistance(Vector2Int a, Vector2Int b)
    {
        int dx = Mathf.Abs(a.x - b.x), dy = Mathf.Abs(a.y - b.y);
        return 1.5f * Mathf.Min(dx, dy) + Mathf.Abs(dx - dy);
    }

    private static float Level(float distance, float radius)
    {
        if (radius <= 0f || distance > radius) return 0f;
        if (distance <= radius / 3f) return 3f;
        return distance <= 2f * radius / 3f ? 2f : 1f;
    }

    // Paper Eqs. (10)-(14): obstacle-facing fan plus rear circle, summed.
    public static float Contribution(Vector2Int volunteer, Vector2Int obstacle, Vector2Int cell, float radius)
    {
        Vector2 facing = obstacle - volunteer;
        Vector2 offset = cell - volunteer;
        bool inFan = facing.sqrMagnitude > 0f && offset.sqrMagnitude > 0f &&
            Vector2.Dot(facing.normalized, offset.normalized) >= Mathf.Cos(Mathf.PI / 4f) - 0.00001f;
        return inFan ? Level(PaperDistance(obstacle, cell), radius)
            : Level(PaperDistance(volunteer, cell), Mathf.Ceil(radius / 2f));
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
