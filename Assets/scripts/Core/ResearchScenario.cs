using System.Collections.Generic;
using UnityEngine;

public enum ResearchScenario { RandomRoom, OpenRoom, SingleBlockedExit, TwoExitsOneBlocked, AsymmetricOpenExits }

public static class ResearchEnvironment
{
    public static void Configure(GridWorld world, ResearchScenario scenario, int obstacleCount, int exitWidth, int depth, int exitCount=0)
    {
        // Zero preserves the historical preset behavior for existing direct callers.
        if(exitCount>0 && (scenario==ResearchScenario.RandomRoom || scenario==ResearchScenario.OpenRoom))
        {
            int count=Mathf.Clamp(exitCount,1,4);
            world.SetExits(true,count>=2,count>=3,count>=4,exitWidth);
            if(scenario==ResearchScenario.RandomRoom) world.SetRandomObstacles(obstacleCount);
            return;
        }
        if (scenario == ResearchScenario.RandomRoom) { world.SetRandomObstacles(obstacleCount); return; }
        if(scenario==ResearchScenario.AsymmetricOpenExits)
        {
            world.SetExits(true,false,false,false,2);
            int start=(world.width-4)/2;
            for(int x=start;x<start+4;x++)
            {world.SetCellType(x,world.height-1,CellType.Exit);world.exitPositions.Add(new Vector2Int(x,world.height-1));}
            return;
        }
        world.SetExits(true, scenario == ResearchScenario.TwoExitsOneBlocked, false, false, exitWidth);
        if (scenario == ResearchScenario.OpenRoom) return;
        // Place the first layer across the bottom exit, then additional layers.
        // This is a controlled clearance scenario, not the paper's relocation model.
        int placed = 0;
        if(world.paperNeighborhood)
        {
            // Moore predecessors of an exit of width W span W+2 cells.
            // The paper's width-four/six-obstacle layout uses this geometry.
            int first=(world.width-exitWidth)/2-1;
            for(int y=1;y<=Mathf.Min(depth,world.height-2);y++)
            for(int x=Mathf.Max(1,first);x<=Mathf.Min(world.width-2,first+exitWidth+1);x++)
                if(placed<obstacleCount) {world.SetCellType(x,y,CellType.Obstacle);placed++;}
            return;
        }
        for (int y = 1; y <= Mathf.Min(depth, world.height - 2); y++)
            foreach (var exit in world.exitPositions)
            {
                if (exit.y != 0 || placed >= obstacleCount) continue;
                world.SetCellType(exit.x, y, CellType.Obstacle);
                placed++;
            }
    }

    public static int CountExitGroups(GridWorld world)
    {
        var remaining=new HashSet<Vector2Int>(world.exitPositions);int count=0;
        while(remaining.Count>0)
        {
            Vector2Int first=default(Vector2Int);foreach(var cell in remaining) {first=cell;break;}
            remaining.Remove(first);count++;
            var queue=new Queue<Vector2Int>();queue.Enqueue(first);
            while(queue.Count>0)
            {var cell=queue.Dequeue();foreach(var direction in PaperGrid.Cardinal) if(remaining.Remove(cell+direction)) queue.Enqueue(cell+direction);}
        }
        return count;
    }

    // Explicit operationalization of tau for this simplified model: fraction of
    // clear straight lanes across the nearest contiguous exit's approach strip.
    // A lane is blocked if any obstacle/wall is present within `depth` cells.
    public static float ExitNonBlockage(GridWorld world, Vector2Int obstacle, int depth)
    {
        if(world.paperNeighborhood) return PaperExitNonBlockage(world,obstacle);
        if (world.exitPositions.Count == 0) return 1f;
        Vector2Int nearest = world.GetNearestExit(obstacle);
        bool horizontal = nearest.y == 0 || nearest.y == world.height - 1;
        Vector2Int tangent = horizontal ? Vector2Int.right : Vector2Int.up;
        Vector2Int inward = horizontal ? (nearest.y == 0 ? Vector2Int.up : Vector2Int.down)
            : (nearest.x == 0 ? Vector2Int.right : Vector2Int.left);
        var exitSet = new HashSet<Vector2Int>(world.exitPositions);
        Vector2Int start = nearest;
        while (exitSet.Contains(start - tangent)) start -= tangent;
        int total = 0, clear = 0;
        for (Vector2Int cell = start; exitSet.Contains(cell); cell += tangent)
        {
            total++;
            bool blocked = false;
            for (int i = 0; i <= Mathf.Max(1, depth); i++)
            {
                Vector2Int lane = cell + inward * i;
                if (!world.IsWalkable(lane.x, lane.y)) { blocked = true; break; }
            }
            if (!blocked) clear++;
        }
        return total == 0 ? 1f : (float)clear / total;
    }

    // Geometry corroborated against the author's calcBlockedProportion: unique
    // occupiable Moore neighbors of the associated exit, excluding exit cells
    // and immovable cells. Paper tau is the complement of that blocked ratio.
    public static float PaperExitNonBlockage(GridWorld world,Vector2Int obstacle)
    {
        var remaining=new HashSet<Vector2Int>(world.exitPositions);
        foreach(var exit in world.exitPositions)
        {
            if(!remaining.Remove(exit)) continue;
            var group=new List<Vector2Int>{exit};
            for(int i=0;i<group.Count;i++) foreach(var direction in PaperGrid.Cardinal)
                if(remaining.Remove(group[i]+direction)) group.Add(group[i]+direction);
            bool associated=false;
            foreach(var cell in group) if(cell==obstacle || PaperGrid.Adjacent(cell,obstacle)) associated=true;
            if(!associated) continue;
            var neighbors=new HashSet<Vector2Int>();
            foreach(var cell in group) foreach(var direction in PaperGrid.Moore)
            {
                var next=cell+direction;
                if(world.InBounds(next.x,next.y) && world.cells[next.x,next.y]!=CellType.Wall &&
                    !world.immovableObstacles.Contains(next) && !group.Contains(next)) neighbors.Add(next);
            }
            int blocked=0;
            foreach(var cell in neighbors) if(world.cells[cell.x,cell.y]==CellType.Obstacle) blocked++;
            return neighbors.Count>0 ? 1f-(float)blocked/neighbors.Count : 1f;
        }
        return 1f;
    }
}

[System.Serializable]
public class ResearchRunConfiguration
{
    public string geometryTemplateSHA,initialStateSHA,closedLoopSourceSHA;
    public int initialBlockedObstacles;public bool mirrored,zeroStepValidation;
    public string obstacleHandling,destinationRule;
    public float destinationExitDistance,abandonDensity;
    public int densityWindow,replanAfterSteps;
    public int movableObstacles,immovableObstacles;
    public Vector2Int[] fixedObstaclePositions;
    public float cellSize;
    public bool exitWidthWeighted;
    public int manipulationSteps;
    public string sigmaMetric;
    public string schemaVersion = "3-clearance-completion";
    public string modelScope = "Simplified obstacle clearance; not full Lin-Wong relocation reproduction";
    public string experimentID, unityVersion, scenario, movement, conflict, volunteerPolicy, model;
    public string personalResponseVersion;
    public string paperPromptVersion, decisionExecution, paperPromptTemplateSHA256;
    public string decisionRandomAlgorithm, observationScope;
    public int decisionSeed;
    public string executionMode,availabilityMode,dispatcher,coordinationProtocol,coordinationExecution;
    public int coordinationRequestLimit,coordinationOutputTokenLimit,coordinationPromptCharLimit;
    public int reservationIdleSteps,reservationCooldownSteps;
    public string coordinationStudyCell,coordinationStudyGroup,coordinationStudyJob;
    public string researchPhase,conditionKey,calibrationID,studyPlanID,promptWording,experimentPurpose;
    public float calibratedProbability;
    public int maxAgentRequestsPerRun;
    public int runID, seed, width, height, requestedAgents, actualAgents, requestedObstacles, actualObstacles;
    public int maxSteps, visibilityRange, actionRange, selectionInterval, maxRequestsPerStep, approachDepth;
    public int spawnWidth, spawnHeight, exitWidth, requestedExitCount, actualExitCount;
    public int removalWorkSteps;
    public bool hasApiKey, allowMockFallback, llmAssignment;
    public float stepInterval, kStatic, kDynamic, kAnticipation, temperature, volunteerCost, failureCost, omega;
    public float dffDecay, dffDiffusion, anticipationRadius, defectionCost, friction;
}
