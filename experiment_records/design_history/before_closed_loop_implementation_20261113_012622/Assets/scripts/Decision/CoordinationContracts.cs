using System;
using System.Collections.Generic;

namespace Coordination
{
    // Contracts shared by the coordinated extension's dispatchers.
    [Serializable] public sealed class Candidate
    {public int agentId,x,y;public bool evacuated,handling;}
    [Serializable] public sealed class Task
    {public int obstacleId,x,y;public bool settled,handled;public string status;}
    [Serializable] public sealed class Edge
    {public int agentId,obstacleId;public bool eligible,consented;public float approachCost;}
    [Serializable] public sealed class Snapshot
    {
        public string snapshotId;
        public int step,worldRevision;
        public Candidate[] candidates;
        public Task[] tasks;
        public Edge[] edges;
    }
    [Serializable] public sealed class Assignment {public int agentId,obstacleId;}
    [Serializable] public sealed class Proposal
    {public string snapshotId,source;public Assignment[] assignments;}

    public static class ProposalValidator
    {
        // Fail the whole proposal on an invalid pair. Do not silently repair LLM output.
        public static bool Validate(Snapshot snapshot,Proposal proposal,int currentStep,int currentRevision,out string error)
        {
            error="";
            if(snapshot==null || proposal==null || string.IsNullOrEmpty(snapshot.snapshotId) ||
                proposal.snapshotId!=snapshot.snapshotId || snapshot.step!=currentStep || snapshot.worldRevision!=currentRevision)
            {error="stale_or_missing_snapshot";return false;}
            if(snapshot.candidates==null || snapshot.tasks==null || snapshot.edges==null || proposal.assignments==null)
            {error="missing_arrays";return false;}
            var agents=new Dictionary<int,Candidate>();var tasks=new Dictionary<int,Task>();
            foreach(var candidate in snapshot.candidates)
            {
                if(candidate==null || agents.ContainsKey(candidate.agentId)) {error="invalid_candidate_snapshot";return false;}
                agents.Add(candidate.agentId,candidate);
            }
            foreach(var task in snapshot.tasks)
            {
                if(task==null || tasks.ContainsKey(task.obstacleId)) {error="invalid_task_snapshot";return false;}
                tasks.Add(task.obstacleId,task);
            }
            var edges=new Dictionary<string,Edge>();
            foreach(var edge in snapshot.edges)
            {
                if(edge==null || !agents.ContainsKey(edge.agentId) || !tasks.ContainsKey(edge.obstacleId) ||
                    float.IsNaN(edge.approachCost) || float.IsInfinity(edge.approachCost) || edge.approachCost<0)
                {error="invalid_edge_snapshot";return false;}
                string key=edge.agentId+":"+edge.obstacleId;
                if(edges.ContainsKey(key)) {error="duplicate_edge_snapshot";return false;}
                edges.Add(key,edge);
            }
            var usedAgents=new HashSet<int>();var usedTasks=new HashSet<int>();
            foreach(var assignment in proposal.assignments)
            {
                Candidate candidate;Task task;Edge edge;
                if(assignment==null || !agents.TryGetValue(assignment.agentId,out candidate) ||
                    !tasks.TryGetValue(assignment.obstacleId,out task) ||
                    !edges.TryGetValue(assignment.agentId+":"+assignment.obstacleId,out edge))
                {error="unknown_or_unlisted_pair";return false;}
                if(candidate.evacuated || candidate.handling || task.settled || task.handled || !edge.eligible || !edge.consented)
                {error="ineligible_or_nonconsenting_pair";return false;}
                if(!usedAgents.Add(assignment.agentId) || !usedTasks.Add(assignment.obstacleId))
                {error="duplicate_assignment";return false;}
            }
            return true;
        }
    }
}
