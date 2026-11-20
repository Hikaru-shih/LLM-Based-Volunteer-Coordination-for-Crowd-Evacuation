using System;
using System.Collections.Generic;
using System.Linq;

namespace Coordination
{
    public enum ExecutionMode {PaperReference,CoordinatedExtension,OptimizedExtension,LLMExtension}
    public enum AvailabilityMode {PolicyWillingness,AllEligibleControl}
    public static class LocalDispatcher
    {
        public const string Version="local-greedy-v1";
        public static Proposal Propose(Snapshot snapshot)
        {
            var usedAgents=new HashSet<int>();var usedTasks=new HashSet<int>();var assignments=new List<Assignment>();
            // Deterministic greedy baseline, not a maximum-cardinality/optimal solver.
            foreach(var edge in snapshot.edges.Where(e=>e.eligible && e.consented)
                .OrderBy(e=>e.approachCost).ThenBy(e=>e.obstacleId).ThenBy(e=>e.agentId))
            {
                if(usedAgents.Contains(edge.agentId) || usedTasks.Contains(edge.obstacleId)) continue;
                usedAgents.Add(edge.agentId);usedTasks.Add(edge.obstacleId);
                assignments.Add(new Assignment {agentId=edge.agentId,obstacleId=edge.obstacleId});
            }
            return new Proposal {snapshotId=snapshot.snapshotId,source=Version,assignments=assignments.ToArray()};
        }
    }
    [Serializable] public sealed class Reservation
    {public int agentId,obstacleId,createdStep,lastProgressStep;public float bestCost;}
    public sealed class ReservationEvent
    {public int agentId,obstacleId;public string action,reason;}
    public sealed class ReservationBook
    {
        private readonly Dictionary<int,Reservation> byAgent=new Dictionary<int,Reservation>();
        private readonly Dictionary<string,int> cooldown=new Dictionary<string,int>();
        public IEnumerable<Reservation> Entries => byAgent.Values.OrderBy(r=>r.agentId);
        public bool HasAgent(int id) => byAgent.ContainsKey(id);
        public bool HasTask(int id) => byAgent.Values.Any(r=>r.obstacleId==id);
        public Reservation ForAgent(int id) => byAgent.TryGetValue(id,out var r) ? r : null;
        public bool Cooling(int agent,int obstacle,int step) => cooldown.TryGetValue(agent+":"+obstacle,out var until) && step<until;
        public ReservationEvent Release(int agent,string reason,int step,int cooldownSteps=0)
        {
            if(!byAgent.TryGetValue(agent,out var r)) return null;
            byAgent.Remove(agent);
            if(cooldownSteps>0) cooldown[agent+":"+r.obstacleId]=step+cooldownSteps;
            return new ReservationEvent {agentId=agent,obstacleId=r.obstacleId,action="release",reason=reason};
        }
        public List<ReservationEvent> Reconcile(Snapshot snapshot,int idleSteps,int cooldownSteps)
        {
            var events=new List<ReservationEvent>();
            foreach(var r in Entries.ToArray())
            {
                var agent=snapshot.candidates.FirstOrDefault(a=>a.agentId==r.agentId);
                var task=snapshot.tasks.FirstOrDefault(t=>t.obstacleId==r.obstacleId);
                var edge=snapshot.edges.FirstOrDefault(e=>e.agentId==r.agentId && e.obstacleId==r.obstacleId);
                string reason=agent==null || agent.evacuated ? "agent_unavailable" : agent.handling ? "agent_handling" :
                    task==null || task.settled || task.handled ? "task_unavailable" : edge==null ? "unreachable_or_out_of_scope" :
                    !edge.eligible || !edge.consented ? "eligibility_or_consent_lost" : null;
                if(reason==null && edge.approachCost<r.bestCost-0.0001f)
                {r.bestCost=edge.approachCost;r.lastProgressStep=snapshot.step;}
                if(reason==null && snapshot.step-r.lastProgressStep>=idleSteps) reason="no_progress";
                if(reason!=null) events.Add(Release(r.agentId,reason,snapshot.step,reason=="no_progress"?cooldownSteps:0));
            }
            foreach(var key in cooldown.Where(pair=>pair.Value<=snapshot.step).Select(pair=>pair.Key).ToArray()) cooldown.Remove(key);
            return events;
        }
        public List<ReservationEvent> Commit(Snapshot snapshot,Proposal proposal)
        {
            string error;
            if(!ProposalValidator.Validate(snapshot,proposal,snapshot.step,snapshot.worldRevision,out error))
                throw new InvalidOperationException("Invalid proposal: "+error);
            foreach(var a in proposal.assignments)
                if(HasAgent(a.agentId) || HasTask(a.obstacleId) || Cooling(a.agentId,a.obstacleId,snapshot.step))
                    throw new InvalidOperationException("Proposal conflicts with existing reservation/cooldown");
            var events=new List<ReservationEvent>();
            foreach(var a in proposal.assignments)
            {
                float cost=snapshot.edges.First(e=>e.agentId==a.agentId && e.obstacleId==a.obstacleId).approachCost;
                byAgent.Add(a.agentId,new Reservation {agentId=a.agentId,obstacleId=a.obstacleId,createdStep=snapshot.step,lastProgressStep=snapshot.step,bestCost=cost});
                events.Add(new ReservationEvent {agentId=a.agentId,obstacleId=a.obstacleId,action="reserve",reason=proposal.source});
            }
            return events;
        }
    }
}
