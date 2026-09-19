using UnityEngine;

public abstract class FloorField
{
    protected GridWorld world;
    protected float[,] distances;

    public FloorField(GridWorld gridWorld)
    {
        world = gridWorld;
        distances = new float[world.width, world.height];
        ComputeDistances();
    }

    protected abstract void ComputeDistances();

    public float GetDistance(int x, int y)
    {
        if (x < 0 || x >= world.width || y < 0 || y >= world.height)
            return float.MaxValue;
        return distances[x, y];
    }

    public float GetDistance(Vector2Int pos)
    {
        return GetDistance(pos.x, pos.y);
    }
}
