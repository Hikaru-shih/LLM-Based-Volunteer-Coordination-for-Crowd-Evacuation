using System;
using System.Collections.Generic;
using System.Linq;

namespace Coordination
{
    // Successive shortest augmenting paths on a unit-capacity residual network.
    // Augment until no path remains: maximum cardinality first, minimum cost second.
    public static class OptimalDispatcher
    {
        public const string Version="max-cardinality-min-cost-v1";
        private sealed class Arc
        {public int to,reverse,capacity;public double cost;public Assignment assignment;}
        private static Arc Add(List<Arc>[] graph,int from,int to,double cost,Assignment assignment=null)
        {
            var forward=new Arc {to=to,reverse=graph[to].Count,capacity=1,cost=cost,assignment=assignment};
            var backward=new Arc {to=from,reverse=graph[from].Count,capacity=0,cost=-cost};
            graph[from].Add(forward);graph[to].Add(backward);return forward;
        }
        public static Proposal Propose(Snapshot snapshot)
        {
            var empty=new Proposal {snapshotId=snapshot==null?null:snapshot.snapshotId,source=Version,assignments=new Assignment[0]};
            string error;
            if(snapshot==null || !ProposalValidator.Validate(snapshot,empty,snapshot.step,snapshot.worldRevision,out error))
                throw new ArgumentException("Malformed coordination snapshot");
            var agents=snapshot.candidates.Where(a=>!a.evacuated && !a.handling).OrderBy(a=>a.agentId).ToArray();
            var tasks=snapshot.tasks.Where(t=>!t.settled && !t.handled).OrderBy(t=>t.obstacleId).ToArray();
            int sink=1+agents.Length+tasks.Length,n=sink+1;
            var graph=Enumerable.Range(0,n).Select(_=>new List<Arc>()).ToArray();
            var ai=new Dictionary<int,int>();var ti=new Dictionary<int,int>();var pairs=new List<Arc>();
            for(int i=0;i<agents.Length;i++){ai.Add(agents[i].agentId,1+i);Add(graph,0,1+i,0);}
            for(int i=0;i<tasks.Length;i++){ti.Add(tasks[i].obstacleId,1+agents.Length+i);Add(graph,1+agents.Length+i,sink,0);}
            foreach(var e in snapshot.edges.OrderBy(e=>e.agentId).ThenBy(e=>e.obstacleId))
                if(e.eligible && e.consented && ai.ContainsKey(e.agentId) && ti.ContainsKey(e.obstacleId))
                    pairs.Add(Add(graph,ai[e.agentId],ti[e.obstacleId],e.approachCost,new Assignment {agentId=e.agentId,obstacleId=e.obstacleId}));
            while(true)
            {
                var distance=Enumerable.Repeat(double.PositiveInfinity,n).ToArray();distance[0]=0;
                var previous=Enumerable.Repeat(-1,n).ToArray();var via=new int[n];
                // Negative reverse edges allow earlier assignments to be rerouted.
                for(int pass=0;pass<n-1;pass++)
                {
                    bool changed=false;
                    for(int u=0;u<n;u++)
                    for(int k=0;k<graph[u].Count;k++)
                    {
                        var arc=graph[u][k];double next=distance[u]+arc.cost;
                        if(arc.capacity>0 && next<distance[arc.to])
                        {distance[arc.to]=next;previous[arc.to]=u;via[arc.to]=k;changed=true;}
                    }
                    if(!changed) break;
                }
                if(previous[sink]<0) break;
                for(int v=sink;v!=0;v=previous[v])
                {var arc=graph[previous[v]][via[v]];arc.capacity--;graph[v][arc.reverse].capacity++;}
            }
            empty.assignments=pairs.Where(a=>a.capacity==0).Select(a=>a.assignment).OrderBy(a=>a.agentId).ToArray();
            if(!ProposalValidator.Validate(snapshot,empty,snapshot.step,snapshot.worldRevision,out error))
                throw new InvalidOperationException("Optimizer produced invalid proposal: "+error);
            return empty;
        }
    }
}
