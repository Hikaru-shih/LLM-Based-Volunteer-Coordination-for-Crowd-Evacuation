using UnityEngine;
using System.Collections.Generic;

public class GridWorld : MonoBehaviour
{
    public int width = 30;
    public int height = 30;
    public float cellSize = 1f;
    public Vector3 origin = Vector3.zero;
    public CellType[,] cells;
    public List<Vector2Int> exitPositions = new List<Vector2Int>();
    public void Init()
    {
        cells = new CellType[width, height];
        for(int i=0; i<width; i++)
        {
            for(int j=0; j<height; j++)
            {
                cells[i, j] = CellType.Empty;
            }
        }

        for(int i=0; i<width; i++)
        {
            cells[i, 0] = CellType.Wall;
            cells[i, height - 1] = CellType.Wall;
        }
        for(int i=0; i<height; i++)
        {
            cells[0, i] = CellType.Wall;
            cells[width - 1, i] = CellType.Wall;
        }
        int exitWidth = 3;
        exitPositions.Clear();
        // Bottom edge (y=0)
        int startX = (width - exitWidth) / 2;
        for (int x = startX; x < startX + exitWidth; x++)
            AddExit(x, 0);
        // Top edge (y=height-1)
        int startXTop = (width - exitWidth) / 2;
        for (int x = startXTop; x < startXTop + exitWidth; x++)
            AddExit(x, height - 1);
        // Left edge (x=0)
        int startY = (height - exitWidth) / 2;
        for (int y = startY; y < startY + exitWidth; y++)
            AddExit(0, y);
        // Right edge (x=width-1)
        int startYRight = (height - exitWidth) / 2;
        for (int y = startYRight; y < startYRight + exitWidth; y++)
            AddExit(width - 1, y);
    }

    // Add an exit at (x, y) and register it
    void AddExit(int x, int y)
    {
        if (!InBounds(x, y)) return;
        cells[x, y] = CellType.Exit;
        if (!exitPositions.Contains(new Vector2Int(x, y)))
            exitPositions.Add(new Vector2Int(x, y));
    }

    // 設定出口開啟的邊（下、上、左、右），可指定寬度
    public void SetExits(bool bottom, bool top, bool left, bool right, int exitWidth = 3)
    {
        exitPositions.Clear();
        // Bottom edge (y=0)
        if (bottom)
        {
            int startX = (width - exitWidth) / 2;
            for (int x = startX; x < startX + exitWidth; x++)
                AddExit(x, 0);
        }
        // Top edge (y=height-1)
        if (top)
        {
            int startX = (width - exitWidth) / 2;
            for (int x = startX; x < startX + exitWidth; x++)
                AddExit(x, height - 1);
        }
        // Left edge (x=0)
        if (left)
        {
            int startY = (height - exitWidth) / 2;
            for (int y = startY; y < startY + exitWidth; y++)
                AddExit(0, y);
        }
        // Right edge (x=width-1)
        if (right)
        {
            int startY = (height - exitWidth) / 2;
            for (int y = startY; y < startY + exitWidth; y++)
                AddExit(width - 1, y);
        }
    }
    public bool InBounds(int x, int y)
    {
        return x >= 0 && x < width && y >= 0 && y < height;
    }

    public Vector2Int GetNearestExit(Vector2Int pos)
    {
        Vector2Int nearest = exitPositions.Count > 0 ? exitPositions[0] : new Vector2Int(width / 2, 0);
        float minDist = float.MaxValue;

        foreach (Vector2Int exit in exitPositions)
        {
            float dist = Mathf.Abs(exit.x - pos.x) + Mathf.Abs(exit.y - pos.y);
            if (dist < minDist)
            {
                minDist = dist;
                nearest = exit;
            }
        }

        return nearest;
    }
    public Vector2 WorldToGrid(Vector3 worldPos)
    {
        int x = Mathf.FloorToInt((worldPos.x - origin.x) / cellSize);
        int y = Mathf.FloorToInt((worldPos.z - origin.z) / cellSize);
        return new Vector2Int(x, y);
    }
    public Vector3 GridToWorld(int x, int y)
    {
        Vector3 Pos = new Vector3(origin.x + (x+0.5f)*cellSize,
                                    origin.y,
                                    origin.z + (y+0.5f)*cellSize); 
        return Pos;
    }
    public bool IsWalkable(int x, int y)
    {
        if (!InBounds(x, y))
        {
            return false;
        } 
        if(cells[x, y] != CellType.Wall && cells[x, y] != CellType.Obstacle)
        {
            return true;
        }
        return false;
    }
    public void SetCellType(int x, int y, CellType type)
    {
        if (!InBounds(x, y))
        {
            return;
        }
        cells[x, y] = type;
    }

    public bool RemoveObstacleAt(int x, int y)
    {
        if (!InBounds(x, y))
            return false;

        if (cells[x, y] == CellType.Obstacle)
        {
            cells[x, y] = CellType.Empty;
            return true;
        }

        return false;
    }

    public bool RemoveNearestObstacle(Vector2Int center, int radius = 2)
    {
        int bestX = -1;
        int bestY = -1;
        float bestDist = float.MaxValue;

        for (int dx = -radius; dx <= radius; dx++)
        {
            for (int dy = -radius; dy <= radius; dy++)
            {
                int nx = center.x + dx;
                int ny = center.y + dy;
                if (!InBounds(nx, ny))
                    continue;

                if (cells[nx, ny] == CellType.Obstacle)
                {
                    float dist = Mathf.Abs(dx) + Mathf.Abs(dy);
                    if (dist < bestDist)
                    {
                        bestDist = dist;
                        bestX = nx;
                        bestY = ny;
                    }
                }
            }
        }

        if (bestX >= 0 && bestY >= 0)
        {
            cells[bestX, bestY] = CellType.Empty;
            return true;
        }

        return false;
    }

    public void SetRandomObstacles(int obstacleCount)
    {
        int placed = 0;
        int attempts = 0;
        while (placed < obstacleCount && attempts < obstacleCount * 20)
        {
            attempts++;
            int x = Random.Range(1, width - 1);
            int y = Random.Range(1, height - 1);
            if (cells[x, y] != CellType.Empty) continue;

            bool isExit = false;
            foreach (Vector2Int exit in exitPositions)
            {
                if (exit.x == x && exit.y == y)
                {
                    isExit = true;
                    break;
                }
            }
            if (isExit) continue;

            cells[x, y] = CellType.Obstacle;
            placed++;
        }
    }

    public List<Vector2Int> GetObstaclePositions()
    {
        List<Vector2Int> obstacles = new List<Vector2Int>();
        for (int x = 0; x < width; x++)
        {
            for (int y = 0; y < height; y++)
            {
                if (cells[x, y] == CellType.Obstacle)
                {
                    obstacles.Add(new Vector2Int(x, y));
                }
            }
        }
        return obstacles;
    }

    void OnDrawGizmos() 
    {
        if(cells == null)
        {
            Debug.Log("null - GridWorld cells not initialized");
            return;
        }
        DrawGrid();
    }

    void OnDrawGizmosSelected()
    {
        if(cells == null)
            return;
        DrawGrid();
    }

    void DrawGrid()
    {
        for (int x = 0; x < width; x++)
        {
            for (int y = 0; y < height; y++)
            {
                Vector3 center = GridToWorld(x, y);

                if (cells[x, y] == CellType.Empty)
                {
                    Gizmos.color = new Color(1, 1, 1, 0.05f);
                }
                else if (cells[x, y] == CellType.Wall)
                {
                    Gizmos.color = new Color(0, 0, 0, 0.4f);
                }   
                else if (cells[x, y] == CellType.Exit)
                {
                    Gizmos.color = new Color(0, 1, 0, 0.4f);
                }                   
                else if (cells[x, y] == CellType.Obstacle)
                {
                    Gizmos.color = new Color(1, 0.5f, 0, 0.4f);
                }            
                else if (cells[x, y] == CellType.Pedestrian)
                {
                    Gizmos.color = new Color(0, 0.5f, 1, 0.4f);
                }
                Gizmos.DrawCube(
                    center,
                    new Vector3(cellSize * 0.95f, 0.05f, cellSize * 0.95f)
                );
            }
        }
    }
    void OnValidate()
    {
        if (!Application.isPlaying)
        {
            Init();
        }
    }

}
