using System.Collections.Generic;
using UnityEngine;

public class AStarPathfinding
{
    private GridWorld world;

    public AStarPathfinding(GridWorld world)
    {
        this.world = world;
    }

    private int Heuristic(Vector2Int a, Vector2Int b)
    {
        return Mathf.Abs(a.x - b.x) + Mathf.Abs(a.y - b.y);
    }

    public List<Vector2Int> FindPath(Vector2Int start, Vector2Int goal)
    {
        List<Vector2Int> path = new List<Vector2Int>();

        if (!world.InBounds(start.x, start.y) || !world.InBounds(goal.x, goal.y))
            return path;

        if (!world.IsWalkable(goal.x, goal.y) && world.cells[goal.x, goal.y] != CellType.Exit)
            return path;

        Dictionary<Vector2Int, Vector2Int> cameFrom = new Dictionary<Vector2Int, Vector2Int>();
        Dictionary<Vector2Int, int> gScore = new Dictionary<Vector2Int, int>();
        Dictionary<Vector2Int, int> fScore = new Dictionary<Vector2Int, int>();

        PriorityQueue<Vector2Int> openSet = new PriorityQueue<Vector2Int>();

        gScore[start] = 0;
        fScore[start] = Heuristic(start, goal);
        openSet.Enqueue(start, fScore[start]);

        int[] dx = {0, 0, -1, 1};
        int[] dy = {-1, 1, 0, 0};

        while (openSet.Count > 0)
        {
            Vector2Int current = openSet.Dequeue();

            if (current == goal)
            {
                Vector2Int node = current;
                while (!node.Equals(start))
                {
                    path.Add(node);
                    node = cameFrom[node];
                }
                path.Add(start);
                path.Reverse();
                return path;
            }

            for (int i = 0; i < 4; i++)
            {
                Vector2Int neighbor = new Vector2Int(current.x + dx[i], current.y + dy[i]);

                if (!world.InBounds(neighbor.x, neighbor.y))
                    continue;
                if (!world.IsWalkable(neighbor.x, neighbor.y) && world.cells[neighbor.x, neighbor.y] != CellType.Exit)
                    continue;

                int tentativeG = gScore[current] + 1;

                if (!gScore.ContainsKey(neighbor) || tentativeG < gScore[neighbor])
                {
                    cameFrom[neighbor] = current;
                    gScore[neighbor] = tentativeG;
                    int f = tentativeG + Heuristic(neighbor, goal);
                    fScore[neighbor] = f;

                    if (!openSet.Contains(neighbor))
                    {
                        openSet.Enqueue(neighbor, f);
                    }
                }
            }
        }

        return path;
    }
}

public class PriorityQueue<T>
{
    private List<KeyValuePair<T, int>> elements = new List<KeyValuePair<T, int>>();

    public int Count
    {
        get { return elements.Count; }
    }

    public void Enqueue(T item, int priority)
    {
        elements.Add(new KeyValuePair<T, int>(item, priority));
    }

    public T Dequeue()
    {
        int bestIndex = 0;

        for (int i = 1; i < elements.Count; i++)
        {
            if (elements[i].Value < elements[bestIndex].Value)
            {
                bestIndex = i;
            }
        }

        T bestItem = elements[bestIndex].Key;
        elements.RemoveAt(bestIndex);
        return bestItem;
    }

    public bool Contains(T item)
    {
        foreach (var element in elements)
        {
            if (EqualityComparer<T>.Default.Equals(element.Key, item))
                return true;
        }
        return false;
    }
}
