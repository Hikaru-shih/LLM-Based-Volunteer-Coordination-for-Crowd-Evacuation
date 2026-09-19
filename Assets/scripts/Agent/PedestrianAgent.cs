using UnityEngine;
using System.Collections.Generic;

public class PedestrianAgent : MonoBehaviour
{
    public Vector2Int gridPos;
    public Vector2Int desiredPos;
    public Vector2Int moveDirection = Vector2Int.zero;
    
    public enum Role { Evacuee, Volunteer }
    public Role role = Role.Evacuee;

    public enum VolunteerState { None, PotentialVolunteer, ActiveVolunteer }
    [HideInInspector] public VolunteerState volunteerState = VolunteerState.None;

    public enum MovementStrategy { Static, Dynamic, Anticipation, Combined, AStar }
    public MovementStrategy movementStrategy = MovementStrategy.Combined;

    public float kStatic = 1.0f;
    public float kDynamic = 1.0f;
    public float kAnticipation = 1.0f;
    public float temperature = 1.0f;

    [HideInInspector] public bool evacuated = false;
    [HideInInspector] public int evacuationStep = -1;
    [HideInInspector] public int helpReceived = 0;
    private GridWorld world;
    private StaticFloorField floorField;
    private DynamicFloorField dynamicField;
    private AnticipationFloorField anticipationField;
    private AStarPathfinding pathfinder;
    private List<Vector2Int> path = new List<Vector2Int>();
    private int pathIndex = 0;
    private HashSet<int> evaluatedObstacleIds = new HashSet<int>();
    private bool hasAssignedObstacle = false;
    private Vector2Int assignedObstaclePos = new Vector2Int(-1, -1);
    private int assignedObstacleId = -1;
    private int volunteerActionRange = 2;

    public void Init(GridWorld world, Vector2Int startPos)
    {
        this.world = world;
        gridPos = startPos;
        desiredPos = startPos;
        moveDirection = Vector2Int.zero;
        evaluatedObstacleIds.Clear();
        hasAssignedObstacle = false;
        assignedObstaclePos = new Vector2Int(-1, -1);
        assignedObstacleId = -1;
        
        if (world != null)
        {
            transform.position = world.GridToWorld(gridPos.x, gridPos.y);
        }
    }

    public void SetFloorField(StaticFloorField floorField)
    {
        this.floorField = floorField;
    }

    public void SetDynamicField(DynamicFloorField dynamicField)
    {
        this.dynamicField = dynamicField;
    }

    public void SetAnticipationField(AnticipationFloorField anticipationField)
    {
        this.anticipationField = anticipationField;
    }

    public void SetPathfinder(AStarPathfinding pathfinder)
    {
        this.pathfinder = pathfinder;
    }

    public void SetMovementStrategy(MovementStrategy strategy)
    {
        movementStrategy = strategy;
    }

    public void SetMovementCoefficients(float ks, float kd, float ka, float temp = 1f)
    {
        kStatic = ks;
        kDynamic = kd;
        kAnticipation = ka;
        temperature = Mathf.Max(temp, 0.01f);
    }

    public void SetVolunteerActionRange(int range)
    {
        volunteerActionRange = Mathf.Max(1, range);
    }

    public bool HasEvaluatedObstacle(int obstacleId)
    {
        return evaluatedObstacleIds.Contains(obstacleId);
    }

    public void MarkObstacleEvaluated(int obstacleId)
    {
        evaluatedObstacleIds.Add(obstacleId);
    }

    public bool HasAssignedObstacle()
    {
        return hasAssignedObstacle;
    }

    public Vector2Int GetAssignedObstacle()
    {
        return assignedObstaclePos;
    }

    public int GetAssignedObstacleId()
    {
        return assignedObstacleId;
    }

    public void AssignObstacle(int obstacleId, Vector2Int obstaclePos)
    {
        hasAssignedObstacle = true;
        assignedObstacleId = obstacleId;
        assignedObstaclePos = obstaclePos;
    }

    public void ClearAssignedObstacle()
    {
        hasAssignedObstacle = false;
        assignedObstacleId = -1;
        assignedObstaclePos = new Vector2Int(-1, -1);
    }

    public Vector2Int ProposeMove()
    {
        if (evacuated || world == null)
        {
            desiredPos = gridPos;
            return gridPos;
        }

        if (IsActiveVolunteer() && hasAssignedObstacle)
        {
            int distToTarget = Mathf.Abs(gridPos.x - assignedObstaclePos.x) + Mathf.Abs(gridPos.y - assignedObstaclePos.y);
            if (distToTarget <= volunteerActionRange)
            {
                desiredPos = gridPos;
                moveDirection = Vector2Int.zero;
                return desiredPos;
            }

            List<Vector2Int> volunteerNeighbors = new List<Vector2Int>
            {
                gridPos,
                gridPos + new Vector2Int(0, -1),
                gridPos + new Vector2Int(0, 1),
                gridPos + new Vector2Int(-1, 0),
                gridPos + new Vector2Int(1, 0)
            };

            Vector2Int bestPos = gridPos;
            float bestDist = distToTarget;
            for (int i = 0; i < volunteerNeighbors.Count; i++)
            {
                Vector2Int nextPos = volunteerNeighbors[i];
                if (!world.InBounds(nextPos.x, nextPos.y))
                    continue;
                if (!world.IsWalkable(nextPos.x, nextPos.y) && world.cells[nextPos.x, nextPos.y] != CellType.Exit)
                    continue;

                float nextDist = Mathf.Abs(nextPos.x - assignedObstaclePos.x) + Mathf.Abs(nextPos.y - assignedObstaclePos.y);
                if (nextDist < bestDist)
                {
                    bestDist = nextDist;
                    bestPos = nextPos;
                }
            }

            desiredPos = bestPos;
            moveDirection = desiredPos - gridPos;
            return desiredPos;
        }

        if (movementStrategy == MovementStrategy.AStar && pathfinder != null)
        {
            Vector2Int target = world.GetNearestExit(gridPos);
            if (path == null || path.Count == 0 || pathIndex >= path.Count || path[path.Count - 1] != target)
            {
                path = pathfinder.FindPath(gridPos, target);
                pathIndex = 1;
            }

            if (path != null && path.Count > 1 && pathIndex < path.Count)
            {
                Vector2Int nextPos = path[pathIndex];
                if (world.IsWalkable(nextPos.x, nextPos.y) || world.cells[nextPos.x, nextPos.y] == CellType.Exit)
                {
                    moveDirection = nextPos - gridPos;
                    desiredPos = nextPos;
                    pathIndex++;
                    return desiredPos;
                }
            }
        }

        List<Vector2Int> neighbors = new List<Vector2Int>()
        {
            gridPos,
            gridPos + new Vector2Int(0, -1),
            gridPos + new Vector2Int(0, 1),
            gridPos + new Vector2Int(-1, 0),
            gridPos + new Vector2Int(1, 0)
        };


        List<Vector2Int> walkableNeighbors = new List<Vector2Int>();
        List<float> scores = new List<float>();

        float ks = kStatic;
        float kd = kDynamic;
        float ka = kAnticipation;

        switch (movementStrategy)
        {
            case MovementStrategy.Static:
                kd = 0f; ka = 0f;
                break;
            case MovementStrategy.Dynamic:
                ks = 0f; ka = 0f;
                break;
            case MovementStrategy.Anticipation:
                ks = 0f; kd = 0f;
                break;
            case MovementStrategy.Combined:
            default:
                break;
        }

        float totalScore = 0f;

        // 先檢查鄰居是否有出口格，有的話直接進去
        foreach (Vector2Int nextPos in neighbors)
        {
            if (!world.InBounds(nextPos.x, nextPos.y))
                continue;
            if (world.cells[nextPos.x, nextPos.y] == CellType.Exit)
            {
                desiredPos = nextPos;
                return desiredPos;
            }
        }

        // 沒有出口才走原本的分數選擇
        foreach (Vector2Int nextPos in neighbors)
        {
            if (!world.InBounds(nextPos.x, nextPos.y))
                continue;

            if (!world.IsWalkable(nextPos.x, nextPos.y) && world.cells[nextPos.x, nextPos.y] != CellType.Exit)
                continue;

            float staticDist = floorField != null ? floorField.GetDistance(nextPos) : 0f;
            float dynamicVal = dynamicField != null ? dynamicField.GetValue(nextPos) : 0f;
            float anticipationVal = anticipationField != null ? anticipationField.GetValue(nextPos) : 0f;

            float exponent = -ks * staticDist + kd * dynamicVal - ka * anticipationVal;
            float score = Mathf.Exp(exponent / temperature);

            walkableNeighbors.Add(nextPos);
            scores.Add(score);
            totalScore += score;
        }

        Vector2Int chosenPos = gridPos;

        if (walkableNeighbors.Count > 0 && totalScore > 0f)
        {
            float r = Random.value * totalScore;
            float cum = 0f;
            for (int i = 0; i < walkableNeighbors.Count; i++)
            {
                cum += scores[i];
                if (r <= cum)
                {
                    chosenPos = walkableNeighbors[i];
                    break;
                }
            }

            if (chosenPos != gridPos)
            {
                moveDirection = chosenPos - gridPos;
            }
            else
            {
                moveDirection = Vector2Int.zero;
            }
        }
        else
        {
            moveDirection = Vector2Int.zero;
        }

        if (role == Role.Volunteer && helpReceived > 0)
        {
            helpReceived = Mathf.Max(0, helpReceived - 1);
        }

        desiredPos = chosenPos;
        return desiredPos;
    }

    public void CommitMove()
    {
        if (evacuated || world == null)
            return;

        if (!world.InBounds(desiredPos.x, desiredPos.y))
        {
            desiredPos = gridPos;
            return;
        }

        if (world.cells[desiredPos.x, desiredPos.y] == CellType.Exit)
        {
            evacuated = true;
            gameObject.SetActive(false);
            return;
        }

        if (world.IsWalkable(desiredPos.x, desiredPos.y))
        {
            gridPos = desiredPos;
            transform.position = world.GridToWorld(gridPos.x, gridPos.y);
        }
        else
        {
            desiredPos = gridPos;
        }

        moveDirection = Vector2Int.zero;
    }

    public bool IsEvacuated()
    {
        return evacuated;
    }

    public Vector2Int GetGridPos()
    {
        return gridPos;
    }

    public Vector2Int GetDesiredPos()
    {
        return desiredPos;
    }

    public Role GetRole()
    {
        return role;
    }

    public void SetRole(Role newRole)
    {
        role = newRole;

        if (role == Role.Evacuee)
        {
            volunteerState = VolunteerState.None;
        }
        else if (volunteerState == VolunteerState.None)
        {
            volunteerState = VolunteerState.PotentialVolunteer;
        }

        UpdateVisualByState();
    }

    public VolunteerState GetVolunteerState()
    {
        return volunteerState;
    }

    public void SetVolunteerState(VolunteerState newState)
    {
        volunteerState = newState;
        role = newState == VolunteerState.None ? Role.Evacuee : Role.Volunteer;
        if (newState == VolunteerState.None)
        {
            ClearAssignedObstacle();
        }
        UpdateVisualByState();
    }

    public bool IsPotentialVolunteer()
    {
        return volunteerState == VolunteerState.PotentialVolunteer;
    }

    public bool IsActiveVolunteer()
    {
        return volunteerState == VolunteerState.ActiveVolunteer;
    }

    private void UpdateVisualByState()
    {

        Renderer renderer = GetComponentInChildren<Renderer>();
        if (renderer != null)
        {
            if (volunteerState == VolunteerState.ActiveVolunteer)
            {
                renderer.material.color = Color.green;
            }
            else if (volunteerState == VolunteerState.PotentialVolunteer)
            {
                renderer.material.color = new Color(1.0f, 0.8f, 0.2f);
            }
            else
            {
                renderer.material.color = new Color(0.2f, 0.6f, 1f);
            }
        }
    }

    public void ReceiveHelp()
    {
        helpReceived += 2;
    }
}
