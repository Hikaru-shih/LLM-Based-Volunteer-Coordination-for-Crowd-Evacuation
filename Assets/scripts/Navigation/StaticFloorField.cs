using UnityEngine;
using System.Collections.Generic;

public class StaticFloorField : FloorField
{
    private HashSet<Vector2Int> knownObstacles;
    public StaticFloorField(GridWorld gridWorld, IEnumerable<Vector2Int> rejectedObstacles = null) : base(gridWorld)
    {
        if (rejectedObstacles != null)
        {
            knownObstacles = new HashSet<Vector2Int>(rejectedObstacles);
            ComputeDistances();
        }
    }

    protected override void ComputeDistances()
    {
        if(world.paperNeighborhood)
        {
            var blocked=new HashSet<Vector2Int>(world.immovableObstacles);
            blocked.UnionWith(world.settledObstacles); blocked.UnionWith(world.movingObstacles);
            if(knownObstacles!=null) foreach(var obstacle in knownObstacles)
                if(world.InBounds(obstacle.x,obstacle.y) && world.cells[obstacle.x,obstacle.y]==CellType.Obstacle) blocked.Add(obstacle);
            distances=PaperGrid.ExitField(world,blocked); return;
        }
        for (int x = 0; x < world.width; x++)
        {
            for (int y = 0; y < world.height; y++)
            {
                distances[x, y] = float.MaxValue;
            }
        }

        var directions = new[] { Vector2Int.up, Vector2Int.down, Vector2Int.left, Vector2Int.right };
        var remaining = new HashSet<Vector2Int>(world.exitPositions);
        var groups = new List<List<Vector2Int>>();
        foreach (var exit in world.exitPositions)
        {
            if (!remaining.Remove(exit)) continue;
            var group = new List<Vector2Int> { exit };
            for (int i = 0; i < group.Count; i++)
                foreach (var direction in directions)
                    if (remaining.Remove(group[i] + direction)) group.Add(group[i] + direction);
            groups.Add(group);
        }
        foreach (var group in groups)
        {
            // Eqs. (3)-(6): step cost is lambda / exp(phi), NOT lambda * exp(phi).
            // Cardinal-only movement is the paper's permitted von Neumann variant.
            float cost = Mathf.Exp(-(float)group.Count / Mathf.Max(1, world.exitPositions.Count));
            var steps = new Dictionary<Vector2Int, int>();
            var queue = new Queue<Vector2Int>();
            foreach (var exit in group) { steps[exit] = 0; queue.Enqueue(exit); }
            while (queue.Count > 0)
            {
                var current = queue.Dequeue();
                int step = steps[current];
                distances[current.x, current.y] = Mathf.Min(distances[current.x, current.y], step * cost);
                foreach (var direction in directions)
                {
                    var next = current + direction;
                    if (!world.InBounds(next.x, next.y) || world.cells[next.x, next.y] == CellType.Wall || steps.ContainsKey(next)) continue;
                    if (knownObstacles != null && knownObstacles.Contains(next) && world.cells[next.x, next.y] == CellType.Obstacle) continue;
                    // Base SFF ignores movable obstacles until locally perceived.
                    // A private field additionally excludes its owner's rejected obstacles.
                    steps[next] = step + 1;
                    queue.Enqueue(next);
                }
            }
        }

    }
}
