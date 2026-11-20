using System.Collections.Generic;
using UnityEngine;

/// <summary>Section II.B.4 and Fig.6. All operations preserve obstacle count.</summary>
public static class PaperObstaclePlanner
{
    public static HashSet<Vector2Int> OtherObstacles(GridWorld world, Vector2Int own)
    {
        var result=new HashSet<Vector2Int>(world.GetObstaclePositions()); result.Remove(own); return result;
    }
    public static bool Empty(GridWorld world, Vector2Int cell, HashSet<Vector2Int> occupied, Vector2Int ownAgent)
        => world.InBounds(cell.x,cell.y) && world.cells[cell.x,cell.y]==CellType.Empty &&
            (cell==ownAgent || occupied==null || !occupied.Contains(cell));

    public static bool ChooseDestination(GridWorld world, PaperObstacle obstacle, PedestrianAgent worker,
        HashSet<Vector2Int> reserved, PaperDestinationRule rule, float sigma, int minimumStableNeighbors=3,
        PaperSigmaMetric sigmaMetric=PaperSigmaMetric.GridDistance)
    {
        var field=PaperGrid.Field(world,new[]{obstacle.position},OtherObstacles(world,obstacle.position));
        Vector2 facing=obstacle.position-worker.gridPos;
        float[,] exitField=null;
        if(sigmaMetric==PaperSigmaMetric.ExitFloorField)
        {
            var globalBlocks=new HashSet<Vector2Int>(world.immovableObstacles);
            globalBlocks.UnionWith(world.settledObstacles);globalBlocks.UnionWith(world.movingObstacles);globalBlocks.Remove(obstacle.position);
            exitField=PaperGrid.ExitField(world,globalBlocks);
        }
        float best=float.PositiveInfinity;Vector2Int destination=obstacle.position;
        // Compare nearest forward/backward choices; prefer forward on ties.
        for(int pass=0;pass<2;pass++)
        {
            for(int x=1;x<world.width-1;x++) for(int y=1;y<world.height-1;y++)
            {
                var cell=new Vector2Int(x,y);
                if(cell==worker.gridPos || world.cells[x,y]!=CellType.Empty || reserved.Contains(cell) || obstacle.rejectedDestinations.Contains(cell)) continue;
                bool forward=Vector2.Dot(facing,(Vector2)(cell-worker.gridPos))>=0;
                if((pass==0)!=forward) continue;
                float exitDistance=float.PositiveInfinity;
                if(exitField!=null) exitDistance=exitField[x,y];
                else foreach(var exit in world.exitPositions) exitDistance=Mathf.Min(exitDistance,PaperGrid.Distance(cell,exit));
                if(float.IsPositiveInfinity(exitDistance)) continue;
                if(exitDistance<sigma) continue;
                int stableNeighbors=0;
                foreach(var direction in PaperGrid.Moore)
                {
                    var next=cell+direction;
                    if(world.InBounds(next.x,next.y) && (world.cells[next.x,next.y]==CellType.Wall ||
                        world.immovableObstacles.Contains(next) || world.settledObstacles.Contains(next))) stableNeighbors++;
                }
                if(rule==PaperDestinationRule.NextToWallsOrObstacles && stableNeighbors<Mathf.Max(1,minimumStableNeighbors)) continue;
                if(field[x,y]>=best) continue;
                best=field[x,y]; destination=cell;
            }
        }
        if(!float.IsPositiveInfinity(best))
        { obstacle.destination=destination; obstacle.hasDestination=true; return true; }
        return false;
    }

    public static PaperMove Plan(GridWorld world, PaperObstacle obstacle, PedestrianAgent worker,
        HashSet<Vector2Int> occupied, bool preferPull=true)
    {
        var plan=new PaperMove { agent=worker,obstacle=obstacle,agentFrom=worker.gridPos,agentTo=worker.gridPos,
            obstacleFrom=obstacle.position,obstacleTo=obstacle.position,kind=PaperManipulation.Wait };
        if(!obstacle.hasDestination || !PaperGrid.Adjacent(worker.gridPos,obstacle.position)) return plan;
        var blocked=OtherObstacles(world,obstacle.position);
        var field=PaperGrid.Field(world,new[]{obstacle.destination},blocked);
        var pv=worker.gridPos; var po=obstacle.position;
        float agentValue=field[pv.x,pv.y], obstacleValue=field[po.x,po.y];
        if(float.IsPositiveInfinity(obstacleValue)) return plan;
        var choices=new List<Vector2Int>();
        foreach(var direction in PaperGrid.Moore)
        { var cell=po+direction; if(world.InBounds(cell.x,cell.y) && field[cell.x,cell.y]<obstacleValue) choices.Add(cell); }
        choices.Sort((a,b)=>field[a.x,a.y].CompareTo(field[b.x,b.y]));

        if(agentValue<obstacleValue)
        {
            if(preferPull)
            {
                Vector2Int best=pv; float bestValue=agentValue;
                foreach(var direction in PaperGrid.Moore)
                {
                    var cell=pv+direction;
                    if(cell==po || !Empty(world,cell,occupied,pv) || field[cell.x,cell.y]>=bestValue) continue;
                    best=cell; bestValue=field[cell.x,cell.y];
                }
                if(best!=pv) { plan.agentTo=best; plan.obstacleTo=pv; plan.kind=PaperManipulation.Pull; return plan; }
            }
            // Fig.6(d): move around the obstacle first; retain adjacency so a
            // subsequent push/rotation can transfer it into the departed cell.
            float bestReposition=float.PositiveInfinity;
            foreach(var direction in PaperGrid.Moore)
            {
                var cell=pv+direction;
                if(!PaperGrid.Adjacent(cell,po) || !Empty(world,cell,occupied,pv) || field[cell.x,cell.y]>=bestReposition) continue;
                bestReposition=field[cell.x,cell.y]; plan.agentTo=cell; plan.kind=PaperManipulation.Reposition;
            }
            return plan;
        }
        foreach(var target in choices)
        {
            Vector2 n=po-pv, f=target-po;
            if(Vector2.Dot(n.normalized,f.normalized)>=Mathf.Cos(Mathf.PI/4)-0.00001f)
            {
                if(!Empty(world,target,occupied,pv)) continue;
                plan.agentTo=po; plan.obstacleTo=target; plan.kind=PaperManipulation.Push; return plan;
            }
            var rotated=pv+PaperGrid.Rotate45(po-pv,target-po);
            if(rotated==po || !PaperGrid.Adjacent(rotated,po) || !Empty(world,rotated,occupied,pv)) continue;
            if(float.IsPositiveInfinity(field[rotated.x,rotated.y])) continue;
            plan.obstacleTo=rotated; plan.kind=PaperManipulation.Rotate; return plan;
        }
        return plan;
    }
}
