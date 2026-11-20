using UnityEngine;

public class HeatmapRenderer : MonoBehaviour
{
    public SimulationManager simulationManager;
    public GridWorld world;
    public Color minColor = Color.green;
    public Color maxColor = Color.red;

    void OnDrawGizmos()
    {
        if (simulationManager == null || world == null)
            return;

        float maxVal = 0.01f;

        // Evaluate dynamic field as heat intensity
        for (int x = 0; x < world.width; x++)
        {
            for (int y = 0; y < world.height; y++)
            {
                float d = simulationManager.GetDynamicFloorFieldValue(new Vector2Int(x, y));
                if (d > maxVal) maxVal = d;
            }
        }

        for (int x = 0; x < world.width; x++)
        {
            for (int y = 0; y < world.height; y++)
            {
                float d = simulationManager.GetDynamicFloorFieldValue(new Vector2Int(x, y));
                float t = Mathf.InverseLerp(0f, maxVal, d);
                Color color = Color.Lerp(minColor, maxColor, t);
                Vector3 pos = world.GridToWorld(x, y);
                Gizmos.color = color;
                Gizmos.DrawCube(pos, Vector3.one * world.cellSize * 0.9f);
            }
        }
    }
}
