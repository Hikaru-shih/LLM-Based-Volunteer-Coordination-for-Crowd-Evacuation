using UnityEngine;
using System.Collections.Generic;

public class StaticFloorField : FloorField
{
    public StaticFloorField(GridWorld gridWorld) : base(gridWorld)
    {
    }

    protected override void ComputeDistances()
    {
        for (int x = 0; x < world.width; x++)
        {
            for (int y = 0; y < world.height; y++)
            {
                distances[x, y] = float.MaxValue;
            }
        }

        Queue<Vector2Int> queue = new Queue<Vector2Int>();

        for (int x = 0; x < world.width; x++)
        {
            for (int y = 0; y < world.height; y++)
            {
                if (world.cells[x, y] == CellType.Exit)
                {
                    distances[x, y] = 0;
                    queue.Enqueue(new Vector2Int(x, y));
                }
            }
        }

        int[] dx = { 0, 0, -1, 1 };
        int[] dy = { -1, 1, 0, 0 };

        while (queue.Count > 0)
        {
            Vector2Int current = queue.Dequeue();
            float currentDist = distances[current.x, current.y];

            for (int i = 0; i < 4; i++)
            {
                int nx = current.x + dx[i];
                int ny = current.y + dy[i];

                if (nx < 0 || nx >= world.width || ny < 0 || ny >= world.height)
                    continue;

                if (!world.IsWalkable(nx, ny))
                    continue;

                if (distances[nx, ny] > currentDist + 1)
                {
                    distances[nx, ny] = currentDist + 1;
                    queue.Enqueue(new Vector2Int(nx, ny));
                }
            }
        }

        Debug.Log("StaticFloorField computed");
    }
}
