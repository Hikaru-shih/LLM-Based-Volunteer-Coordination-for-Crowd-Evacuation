using System;
using System.Collections.Generic;
using UnityEngine;

public enum ObstacleHandlingMode { PaperRelocation, LegacyClearance }
public enum PaperDestinationRule { NextToWallsOrObstacles, AwayFromExit }
public enum PaperSigmaMetric { GridDistance, ExitFloorField }
public enum PaperObstacleStatus { Unmoved, Moving, Settled, Abandoned }
public enum PaperManipulation { Wait, Push, Pull, Rotate, Reposition }

public static class PaperGrid
{
    public static readonly Vector2Int[] Cardinal = { Vector2Int.down, Vector2Int.up, Vector2Int.left, Vector2Int.right };
    public static readonly Vector2Int[] Moore = {
        Vector2Int.down, Vector2Int.up, Vector2Int.left, Vector2Int.right,
        new Vector2Int(-1,-1), new Vector2Int(1,-1), new Vector2Int(-1,1), new Vector2Int(1,1) };
    public static float Distance(Vector2Int a, Vector2Int b) => AnticipationFloorField.PaperDistance(a, b);
    public static bool Adjacent(Vector2Int a, Vector2Int b) => a != b && Mathf.Max(Mathf.Abs(a.x-b.x), Mathf.Abs(a.y-b.y)) == 1;
    public static Vector2Int Rotate45(Vector2Int facing, Vector2Int desired)
    {
        float angle = facing.x * desired.y - facing.y * desired.x <= 0 ? -Mathf.PI/4 : Mathf.PI/4;
        return new Vector2Int((int)Math.Round(Mathf.Cos(angle)*facing.x-Mathf.Sin(angle)*facing.y, MidpointRounding.AwayFromZero),
            (int)Math.Round(Mathf.Sin(angle)*facing.x+Mathf.Cos(angle)*facing.y, MidpointRounding.AwayFromZero));
    }

    // Dijkstra with a binary heap. Distances are independent of current pedestrian
    // occupancy; occupancy is applied to transition probabilities at each step.
    public static float[,] Field(GridWorld world, IEnumerable<Vector2Int> goals, HashSet<Vector2Int> blocked, bool diagonal = true, float scale = 1f)
    {
        var distances = new float[world.width,world.height];
        for (int x=0;x<world.width;x++) for(int y=0;y<world.height;y++) distances[x,y]=float.PositiveInfinity;
        var heap = new List<KeyValuePair<Vector2Int,float>>();
        Action<Vector2Int,float> push = (cell,cost) => {
            heap.Add(new KeyValuePair<Vector2Int,float>(cell,cost));
            int i=heap.Count-1;
            while(i>0) { int parent=(i-1)/2; if(heap[parent].Value<=cost) break; heap[i]=heap[parent]; i=parent; }
            heap[i]=new KeyValuePair<Vector2Int,float>(cell,cost);
        };
        foreach(var goal in goals)
            if(world.InBounds(goal.x,goal.y) && world.cells[goal.x,goal.y]!=CellType.Wall && (blocked==null || !blocked.Contains(goal)))
            { distances[goal.x,goal.y]=0; push(goal,0); }
        while(heap.Count>0)
        {
            var item=heap[0]; var last=heap[heap.Count-1]; heap.RemoveAt(heap.Count-1);
            if(heap.Count>0)
            {
                int i=0;
                while(i*2+1<heap.Count)
                { int child=i*2+1; if(child+1<heap.Count && heap[child+1].Value<heap[child].Value) child++;
                    if(last.Value<=heap[child].Value) break; heap[i]=heap[child]; i=child; }
                heap[i]=last;
            }
            var cell=item.Key; if(item.Value>distances[cell.x,cell.y]) continue;
            foreach(var direction in diagonal ? Moore : Cardinal)
            {
                var next=cell+direction;
                if(!world.InBounds(next.x,next.y) || world.cells[next.x,next.y]==CellType.Wall || (blocked!=null && blocked.Contains(next))) continue;
                float value=item.Value+scale*(direction.x!=0 && direction.y!=0 ? 1.5f : 1f);
                if(value>=distances[next.x,next.y]) continue;
                distances[next.x,next.y]=value; push(next,value);
            }
        }
        return distances;
    }

    public static float[,] ExitField(GridWorld world, HashSet<Vector2Int> blocked, bool weightByWidth=true)
    {
        var result=new float[world.width,world.height];
        for(int x=0;x<world.width;x++) for(int y=0;y<world.height;y++) result[x,y]=float.PositiveInfinity;
        var remaining=new HashSet<Vector2Int>(world.exitPositions);
        foreach(var exit in world.exitPositions)
        {
            if(!remaining.Remove(exit)) continue;
            var group=new List<Vector2Int>{exit};
            for(int i=0;i<group.Count;i++) foreach(var direction in Cardinal)
                if(remaining.Remove(group[i]+direction)) group.Add(group[i]+direction);
            var field=Field(world,group,blocked,true,weightByWidth ? Mathf.Exp(-(float)group.Count/Mathf.Max(1,world.exitPositions.Count)) : 1f);
            for(int x=0;x<world.width;x++) for(int y=0;y<world.height;y++) result[x,y]=Mathf.Min(result[x,y],field[x,y]);
        }
        return result;
    }
}

public class PaperObstacle
{
    public int id;
    public Vector2Int origin, position, destination;
    public bool hasDestination;
    public int worker = -1, stalled,workProgress;
    public PaperObstacleStatus status;
    public readonly HashSet<int> candidates = new HashSet<int>();
    public readonly Queue<float> recentDensity = new Queue<float>();
    public readonly HashSet<Vector2Int> rejectedDestinations = new HashSet<Vector2Int>();
}

public class PaperKnowledge
{
    public readonly HashSet<int> willing = new HashSet<int>();
    public readonly HashSet<int> refused = new HashSet<int>();
    public int version, fieldVersion = -1, obstacleRevision = -1;
    public float[,] exitField;
    public void Decide(int obstacle, bool cooperate)
    {
        bool changed=cooperate ? willing.Add(obstacle) | refused.Remove(obstacle) : refused.Add(obstacle) | willing.Remove(obstacle);
        if(changed) version++;
    }
}

public class PaperMove
{
    public PedestrianAgent agent;
    public PaperObstacle obstacle;
    public Vector2Int agentFrom, agentTo, obstacleFrom, obstacleTo;
    public PaperManipulation kind;
    public bool preparingWork;
}
