using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Decision;

public delegate IEnumerator PaperDecisionHandler(PedestrianAgent agent, PaperObstacle obstacle,
    VolunteerDecisionContext context, Action<bool?,string,string> callback);

/// <summary>Five-stage CA update with stable obstacles and atomic agent/obstacle moves.</summary>
public sealed class PaperModelEngine
{
    private readonly SimulationManager settings;
    private readonly GridWorld world;
    private readonly List<PedestrianAgent> agents;
    private readonly DynamicFloorField dynamicField;
    private readonly AnticipationFloorField anticipation;
    private readonly YielderGame game;
    private readonly PaperDecisionHandler decision;
    public readonly List<PaperObstacle> Obstacles=new List<PaperObstacle>();
    public readonly Dictionary<int,PaperKnowledge> Knowledge=new Dictionary<int,PaperKnowledge>();
    private readonly Dictionary<int,PedestrianAgent> byId=new Dictionary<int,PedestrianAgent>();
    private readonly List<int> completedWorkers=new List<int>();
    private readonly Dictionary<string,float[,]> fields=new Dictionary<string,float[,]>();
    private int fieldRevision=-1;
    private readonly Coordination.ReservationBook reservations=new Coordination.ReservationBook();
    public Coordination.Snapshot LastCoordinationSnapshot { get; private set; }
    public Coordination.Proposal LastCoordinationProposal { get; private set; }
    public Coordination.ReservationBook Reservations => reservations;
    private bool Coordinated => settings.paperExecutionMode!=Coordination.ExecutionMode.PaperReference;
    public int Conflicts { get; private set; }
    public int Manipulations { get; private set; }

    public PaperModelEngine(SimulationManager settings, GridWorld world, List<PedestrianAgent> agents,
        DynamicFloorField dynamicField, AnticipationFloorField anticipation, YielderGame game, PaperDecisionHandler decision)
    {
        this.settings=settings; this.world=world; this.agents=agents; this.dynamicField=dynamicField;
        this.anticipation=anticipation; this.game=game; this.decision=decision;
        foreach(var agent in agents) { byId.Add(agent.AgentID,agent); Knowledge.Add(agent.AgentID,new PaperKnowledge()); }
        int id=0;
        foreach(var position in world.GetObstaclePositions())
            if(!world.immovableObstacles.Contains(position)) Obstacles.Add(new PaperObstacle { id=id++,origin=position,position=position });
    }
    public int UnsettledCount => Obstacles.Count(o=>o.status==PaperObstacleStatus.Unmoved || o.status==PaperObstacleStatus.Moving);
    public int InitialBlockedTaskCount => Obstacles.Count(o=>o.status==PaperObstacleStatus.Unmoved &&
        ResearchEnvironment.PaperExitNonBlockage(world,o.position)<1f);

    private HashSet<Vector2Int> GlobalBlocks()
    {
        var blocks=new HashSet<Vector2Int>(world.immovableObstacles);
        blocks.UnionWith(world.settledObstacles); blocks.UnionWith(world.movingObstacles); return blocks;
    }
    private float[,] ExitField(PaperKnowledge knowledge)
    {
        var blocks=GlobalBlocks();
        foreach(var obstacle in Obstacles) if(knowledge.refused.Contains(obstacle.id)) blocks.Add(obstacle.position);
        string key="exit:"+settings.paperExitWidthWeighting+":"+string.Join(";",blocks.OrderBy(p=>p.x).ThenBy(p=>p.y).Select(p=>p.x+","+p.y));
        if(!fields.TryGetValue(key,out var field)) fields[key]=field=PaperGrid.ExitField(world,blocks,settings.paperExitWidthWeighting);
        return field;
    }
    private float[,] ApproachField(PaperObstacle obstacle)
    {
        string key="approach:"+obstacle.id;
        if(fields.TryGetValue(key,out var cached)) return cached;
        var goals=new List<Vector2Int>();
        foreach(var direction in PaperGrid.Moore)
        { var cell=obstacle.position+direction; if(world.IsWalkable(cell.x,cell.y) && world.cells[cell.x,cell.y]!=CellType.Exit) goals.Add(cell); }
        return fields[key]=PaperGrid.Field(world,goals,new HashSet<Vector2Int>(world.GetObstaclePositions()));
    }
    private List<PedestrianAgent> Nearby(PaperObstacle obstacle) => agents.FindAll(a=>!a.IsEvacuated() &&
        !a.IsActiveVolunteer() && PaperGrid.Distance(a.gridPos,obstacle.position)<=settings.obstacleVisibilityRange);

    public IEnumerator PrepareStep(int step, SimulationData data)
    {
        Conflicts=Manipulations=0; completedWorkers.Clear();
        if(fieldRevision!=world.ObstacleRevision) { fields.Clear(); fieldRevision=world.ObstacleRevision; }
        foreach(var obstacle in Obstacles)
        {
            obstacle.candidates.RemoveWhere(id=>!byId.ContainsKey(id) || byId[id].IsEvacuated());
            if(obstacle.worker>=0 && byId[obstacle.worker].IsEvacuated()) obstacle.worker=-1;
            if(obstacle.status==PaperObstacleStatus.Settled) continue;
            UpdateDensity(obstacle);
            if(obstacle.status==PaperObstacleStatus.Abandoned && obstacle.recentDensity.Average()>=settings.paperAbandonDensity &&
                ResearchEnvironment.PaperExitNonBlockage(world,obstacle.position)<1f)
            {obstacle.status=PaperObstacleStatus.Unmoved;obstacle.hasDestination=false;data.RecordObstacleEvent(step,obstacle,"resume",-1);}
            if(obstacle.worker>=0 && ShouldAbandon(obstacle))
            { Finish(obstacle,PaperObstacleStatus.Abandoned); data.RecordObstacleEvent(step,obstacle,"abandon_low_density",-1); }
        }
        RefreshRoles();

        // Stage 1: independently maintain Lw/Lb and each obstacle's Lv. An agent
        // can be willing to help several obstacles but can manipulate only one.
        foreach(var obstacle in Obstacles)
        {
            if(obstacle.status!=PaperObstacleStatus.Unmoved || obstacle.worker>=0 || obstacle.candidates.Count>0) continue;
            float tau=ResearchEnvironment.ExitNonBlockage(world,obstacle.position,settings.exitApproachDepth);
            var eligible=Nearby(obstacle);
            if(settings.volunteerDecisionMode==SimulationManager.VolunteerDecisionMode.NoVolunteers || tau>=1f)
            { foreach(var agent in eligible) Knowledge[agent.AgentID].Decide(obstacle.id,false); continue; }
            foreach(var agent in eligible)
            {
                var context=new VolunteerDecisionContext { nearbyAgentCount=eligible.Count,exitNonBlockage=tau,
                    blockageRatio=1-tau,obstacleCount=UnsettledCount,distanceToObstacle=PaperGrid.Distance(agent.gridPos,obstacle.position),
                    currentVolunteerCount=Obstacles.Count(o=>o.worker>=0),volunteerCost=settings.volunteerCost,
                    failureCost=settings.failureCost,unwillingness=settings.unwillingnessOmega,agentPosition=agent.gridPos };
                bool? cooperate=null; string reason="",source="";
                if(Coordinated && settings.coordinationAvailability==Coordination.AvailabilityMode.AllEligibleControl)
                {cooperate=true;source="controlled_availability";reason="Explicit all-eligible dispatch-study control";}
                else yield return decision(agent,obstacle,context,(value,explanation,origin)=>{cooperate=value;reason=explanation;source=origin;});
                if(!settings.IsSimulationRunning()) yield break;
                if(!cooperate.HasValue) continue;
                Knowledge[agent.AgentID].Decide(obstacle.id,cooperate.Value);
                if(cooperate.Value) obstacle.candidates.Add(agent.AgentID);
                data.RecordPaperDecision(step,agent.AgentID,obstacle.id,eligible.Count,tau,cooperate.Value,source);
                data.RecordAgentObservation(step,agent.AgentID,obstacle.id,AgentObservation.Serialize(context,settings.agentInformation),cooperate.Value,source);
            }
        }

        var reserved=new HashSet<Vector2Int>(Obstacles.Where(o=>o.worker>=0 && o.hasDestination).Select(o=>o.destination));
        if(Coordinated)
        {
            yield return UpdateCoordinationReservations(step,data);
            if(LastCoordinationProposal==null) yield break;
            ActivateReservedHandlers(step,data,reserved);
        }
        else ActivateReferenceHandlers(step,data,reserved);
        if(fieldRevision!=world.ObstacleRevision) {fields.Clear();fieldRevision=world.ObstacleRevision;}
        RefreshRoles(); // Exit-field cache keys also include all moving obstacle positions.
        anticipation.UpdateField(agents); // Stage 3, before movement sampling.
        var occupied=new HashSet<Vector2Int>(agents.Where(a=>!a.IsEvacuated()).Select(a=>a.gridPos));
        var plans=new Dictionary<int,PaperMove>();
        foreach(var agent in agents)
        {
            if(agent.IsEvacuated()) continue;
            agent.desiredPos=agent.gridPos;
            var obstacle=Obstacles.Find(o=>o.worker==agent.AgentID);
            if(obstacle!=null)
            {
                data.RecordAgentEffort(step,agent.AgentID,obstacle.id);
                obstacle.workProgress=Mathf.Min(Mathf.Max(1,settings.paperManipulationSteps),obstacle.workProgress+1);
                if(obstacle.workProgress<Mathf.Max(1,settings.paperManipulationSteps))
                {
                    plans[agent.AgentID]=new PaperMove {agent=agent,obstacle=obstacle,agentFrom=agent.gridPos,agentTo=agent.gridPos,
                        obstacleFrom=obstacle.position,obstacleTo=obstacle.position,kind=PaperManipulation.Wait,preparingWork=true};
                    continue;
                }
                if(obstacle.stalled>=settings.paperReplanAfterSteps)
                {
                    obstacle.rejectedDestinations.Add(obstacle.destination); reserved.Remove(obstacle.destination);
                    if(PaperObstaclePlanner.ChooseDestination(world,obstacle,agent,reserved,settings.paperDestinationRule,settings.paperDestinationExitDistance,3,settings.paperSigmaMetric))
                    { obstacle.stalled=0; data.RecordObstacleEvent(step,obstacle,"replan",agent.AgentID); }
                    reserved.Add(obstacle.destination);
                }
                var plan=PaperObstaclePlanner.Plan(world,obstacle,agent,occupied);
                plans[agent.AgentID]=plan; agent.desiredPos=plan.agentTo;
                continue;
            }
            if(agent.IsPotentialVolunteer())
            {
                float best=float.PositiveInfinity; PaperObstacle target=null; float[,] field=null;
                foreach(var candidate in Obstacles)
                {
                    if(candidate.worker>=0 || candidate.status!=PaperObstacleStatus.Unmoved || !candidate.candidates.Contains(agent.AgentID)) continue;
                    if(Coordinated && (reservations.ForAgent(agent.AgentID)==null || reservations.ForAgent(agent.AgentID).obstacleId!=candidate.id)) continue;
                    var approach=ApproachField(candidate); float value=approach[agent.gridPos.x,agent.gridPos.y];
                    if(value<best) { best=value; target=candidate; field=approach; }
                }
                if(target!=null)
                {
                    // Potential volunteers are still evacuees. They must yield
                    // to active handlers through the AFF; only the active
                    // obstacle manipulator ignores DFF/AFF (paper pp.3-6).
                    agent.AssignObstacle(target.id,target.position);
                    agent.desiredPos=SampleEvacuee(agent,field,occupied); continue;
                }
                // Other candidates need not obstruct the active handler; their Lw
                // remains intact while ordinary evacuation continues.
                agent.SetVolunteerState(PedestrianAgent.VolunteerState.None);
            }
            agent.desiredPos=SampleEvacuee(agent,ExitField(Knowledge[agent.AgentID]),occupied);
        }
        ResolveAndApply(step,plans,occupied,data);
    }

    private void ActivateReferenceHandlers(int step,SimulationData data,HashSet<Vector2Int> reserved)
    {
        foreach(var obstacle in Obstacles)
        {
            if(obstacle.status!=PaperObstacleStatus.Unmoved || obstacle.worker>=0) continue;
            var adjacent=obstacle.candidates.Where(id=>!byId[id].IsActiveVolunteer() &&
                PaperGrid.Adjacent(byId[id].gridPos,obstacle.position)).OrderBy(id=>id).ToList();
            if(adjacent.Count==0) continue;
            var worker=byId[adjacent[UnityEngine.Random.Range(0,adjacent.Count)]];
            if(!PaperObstaclePlanner.ChooseDestination(world,obstacle,worker,reserved,settings.paperDestinationRule,settings.paperDestinationExitDistance,3,settings.paperSigmaMetric))
                continue; // No teleport or deletion when no valid destination exists.
            obstacle.worker=worker.AgentID; obstacle.status=PaperObstacleStatus.Moving;
            obstacle.workProgress=0;
            world.movingObstacles.Add(obstacle.position); reserved.Add(obstacle.destination);
            worker.SetVolunteerState(PedestrianAgent.VolunteerState.ActiveVolunteer); worker.AssignObstacle(obstacle.id,obstacle.position);
            foreach(var other in Obstacles) if(other!=obstacle) other.candidates.Remove(worker.AgentID);
            data.RecordObstacleEvent(step,obstacle,"activate",worker.AgentID);
        }
    }

    private static void Seal(Coordination.Snapshot snapshot)
    {
        snapshot.snapshotId="";
        using(var sha=System.Security.Cryptography.SHA256.Create())
            snapshot.snapshotId=BitConverter.ToString(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(JsonUtility.ToJson(snapshot))))
                .Replace("-","").ToLowerInvariant();
    }
    public Coordination.Snapshot BuildCoordinationSnapshot(int step,bool freeOnly=false)
    {
        if(fieldRevision!=world.ObstacleRevision) {fields.Clear();fieldRevision=world.ObstacleRevision;}
        var snapshot=new Coordination.Snapshot {step=step,worldRevision=world.ObstacleRevision,
            candidates=agents.Where(a=>!freeOnly || !reservations.HasAgent(a.AgentID)).OrderBy(a=>a.AgentID)
                .Select(a=>new Coordination.Candidate {agentId=a.AgentID,x=a.gridPos.x,y=a.gridPos.y,evacuated=a.IsEvacuated(),handling=a.IsActiveVolunteer()}).ToArray(),
            tasks=Obstacles.Where(o=>!freeOnly || !reservations.HasTask(o.id)).OrderBy(o=>o.id)
                .Select(o=>new Coordination.Task {obstacleId=o.id,x=o.position.x,y=o.position.y,settled=o.status==PaperObstacleStatus.Settled,
                    handled=o.worker>=0,status=o.status.ToString()}).ToArray()};
        var edges=new List<Coordination.Edge>();
        foreach(var task in snapshot.tasks)
        {
            var obstacle=Obstacles.First(o=>o.id==task.obstacleId);
            if(obstacle.status!=PaperObstacleStatus.Unmoved || task.handled || ResearchEnvironment.PaperExitNonBlockage(world,obstacle.position)>=1) continue;
            var field=ApproachField(obstacle);
            foreach(var candidate in snapshot.candidates)
            {
                if(candidate.evacuated || candidate.handling || PaperGrid.Distance(byId[candidate.agentId].gridPos,obstacle.position)>settings.obstacleVisibilityRange) continue;
                float cost=field[candidate.x,candidate.y];
                if(float.IsInfinity(cost) || float.IsNaN(cost)) continue;
                edges.Add(new Coordination.Edge {agentId=candidate.agentId,obstacleId=task.obstacleId,approachCost=cost,
                    eligible=!reservations.Cooling(candidate.agentId,task.obstacleId,step),
                    consented=settings.volunteerDecisionMode!=SimulationManager.VolunteerDecisionMode.NoVolunteers && obstacle.candidates.Contains(candidate.agentId)});
            }
        }
        snapshot.edges=edges.OrderBy(e=>e.obstacleId).ThenBy(e=>e.agentId).ToArray();Seal(snapshot);return snapshot;
    }
    private void RecordReservations(int step,SimulationData data,IEnumerable<Coordination.ReservationEvent> events)
    {foreach(var e in events) if(e!=null) data.RecordReservation(step,e);}
    private IEnumerator UpdateCoordinationReservations(int step,SimulationData data)
    {
        var full=BuildCoordinationSnapshot(step);
        RecordReservations(step,data,reservations.Reconcile(full,settings.coordinationIdleSteps,settings.coordinationCooldownSteps));
        LastCoordinationSnapshot=BuildCoordinationSnapshot(step,true);
        LastCoordinationProposal=null;
        if(settings.paperExecutionMode==Coordination.ExecutionMode.LLMExtension)
        {
            yield return settings.DecideCoordination(LastCoordinationSnapshot,proposal=>LastCoordinationProposal=proposal);
            if(LastCoordinationProposal==null) yield break;
            // Rebuild after the asynchronous wait: revision alone cannot detect moved agents.
            if(JsonUtility.ToJson(BuildCoordinationSnapshot(step,true))!=JsonUtility.ToJson(LastCoordinationSnapshot))
            {LastCoordinationProposal=null;data.RecordDispatchApplication(LastCoordinationSnapshot,false,"stale_world_after_request");settings.RejectCoordination("stale_world_after_request");yield break;}
        }
        else LastCoordinationProposal=settings.paperExecutionMode==Coordination.ExecutionMode.OptimizedExtension ? Coordination.OptimalDispatcher.Propose(LastCoordinationSnapshot) : Coordination.LocalDispatcher.Propose(LastCoordinationSnapshot);
        string error;
        if(!Coordination.ProposalValidator.Validate(LastCoordinationSnapshot,LastCoordinationProposal,step,world.ObstacleRevision,out error))
            throw new InvalidOperationException("Local proposal rejected: "+error);
        data.RecordCoordination(LastCoordinationSnapshot,LastCoordinationProposal);
        RecordReservations(step,data,reservations.Commit(LastCoordinationSnapshot,LastCoordinationProposal));
        if(settings.paperExecutionMode==Coordination.ExecutionMode.LLMExtension)data.RecordDispatchApplication(LastCoordinationSnapshot,true,"");
    }
    private void ActivateReservedHandlers(int step,SimulationData data,HashSet<Vector2Int> reserved)
    {
        foreach(var reservation in reservations.Entries.ToArray())
        {
            var obstacle=Obstacles.First(o=>o.id==reservation.obstacleId);var worker=byId[reservation.agentId];
            if(worker.IsEvacuated() || worker.IsActiveVolunteer() || obstacle.worker>=0 || obstacle.status!=PaperObstacleStatus.Unmoved ||
                !obstacle.candidates.Contains(worker.AgentID) || !PaperGrid.Adjacent(worker.gridPos,obstacle.position)) continue;
            if(!PaperObstaclePlanner.ChooseDestination(world,obstacle,worker,reserved,settings.paperDestinationRule,settings.paperDestinationExitDistance,3,settings.paperSigmaMetric)) continue;
            obstacle.worker=worker.AgentID;obstacle.status=PaperObstacleStatus.Moving;obstacle.workProgress=0;
            world.movingObstacles.Add(obstacle.position);reserved.Add(obstacle.destination);
            worker.SetVolunteerState(PedestrianAgent.VolunteerState.ActiveVolunteer);worker.AssignObstacle(obstacle.id,obstacle.position);
            foreach(var other in Obstacles) if(other!=obstacle) other.candidates.Remove(worker.AgentID);
            data.RecordObstacleEvent(step,obstacle,"activate",worker.AgentID);
            RecordReservations(step,data,new[]{reservations.Release(worker.AgentID,"activated",step)});
        }
    }

    private Vector2Int DeterministicStep(PedestrianAgent agent,float[,] field,HashSet<Vector2Int> occupied)
    {
        var best=agent.gridPos; float value=field[best.x,best.y];
        foreach(var direction in PaperGrid.Moore)
        {
            var cell=agent.gridPos+direction;
            if(!world.IsWalkable(cell.x,cell.y) || occupied.Contains(cell) || world.cells[cell.x,cell.y]==CellType.Exit) continue;
            if(field[cell.x,cell.y]<value) {value=field[cell.x,cell.y];best=cell;}
        }
        return best;
    }
    private Vector2Int SampleEvacuee(PedestrianAgent agent,float[,] field,HashSet<Vector2Int> occupied)
    {
        float ks=settings.kStatic,kd=settings.kDynamic,ka=settings.kAnticipation;
        if(settings.movementStrategy==PedestrianAgent.MovementStrategy.Static) {kd=0;ka=0;}
        if(settings.movementStrategy==PedestrianAgent.MovementStrategy.Dynamic) {ks=0;ka=0;}
        if(settings.movementStrategy==PedestrianAgent.MovementStrategy.Anticipation) {ks=0;kd=0;}
        var cells=new List<Vector2Int>{agent.gridPos};
        foreach(var direction in PaperGrid.Moore)
        { var cell=agent.gridPos+direction; if(world.IsWalkable(cell.x,cell.y) && !occupied.Contains(cell)) cells.Add(cell); }
        var weights=new float[cells.Count]; float max=float.NegativeInfinity,total=0;
        for(int i=0;i<cells.Count;i++)
        {
            var cell=cells[i]; float distance=field[cell.x,cell.y];
            weights[i]=ks>0 && float.IsInfinity(distance) ? float.NegativeInfinity :
                (-(ks==0 ? 0 : ks*distance)+kd*agent.TraceAdjustedValue(cell)-ka*anticipation.GetValue(cell))/Mathf.Max(0.01f,settings.movementTemperature);
            max=Mathf.Max(max,weights[i]);
        }
        if(float.IsNegativeInfinity(max)) return agent.gridPos;
        for(int i=0;i<weights.Length;i++) {weights[i]=Mathf.Exp(weights[i]-max);total+=weights[i];}
        float sample=UnityEngine.Random.value*total;
        for(int i=0;i<weights.Length;i++) {sample-=weights[i];if(sample<=0) return cells[i];}
        return cells[cells.Count-1];
    }

    private void ResolveAndApply(int step,Dictionary<int,PaperMove> plans,HashSet<Vector2Int> occupied,SimulationData data)
    {
        var requests=new Dictionary<Vector2Int,List<PedestrianAgent>>();
        Action<Vector2Int,PedestrianAgent> request=(cell,agent)=>{
            if(!requests.TryGetValue(cell,out var contenders)) requests[cell]=contenders=new List<PedestrianAgent>();
            if(!contenders.Contains(agent)) contenders.Add(agent);
        };
        foreach(var agent in agents)
        {
            if(agent.IsEvacuated()) continue;
            request(agent.desiredPos,agent);
            if(plans.TryGetValue(agent.AgentID,out var plan)) request(plan.obstacleTo,agent);
        }
        var rejected=new HashSet<int>();
        foreach(var entry in requests)
        {
            if(entry.Value.Count<=1) continue;
            Conflicts++;
            var stationary=entry.Value.Find(a=>a.gridPos==entry.Key && a.desiredPos==entry.Key);
            var winner=stationary!=null ? stationary : game.ResolveConflict(entry.Value);
            foreach(var agent in entry.Value) if(agent!=winner) rejected.Add(agent.AgentID);
        }
        foreach(var agent in agents) if(rejected.Contains(agent.AgentID)) agent.desiredPos=agent.gridPos;
        foreach(var plan in plans.Values)
        {
            var obstacle=plan.obstacle;
            if(rejected.Contains(plan.agent.AgentID) || plan.kind==PaperManipulation.Wait)
            {
                if(!plan.preparingWork) obstacle.stalled++;
                data.RecordVolunteerWork(step,plan.agent.AgentID,obstacle.id,obstacle.workProgress,false);continue;
            }
            if(plan.obstacleTo!=plan.obstacleFrom)
            {
                if(!world.MoveObstacle(plan.obstacleFrom,plan.obstacleTo)) throw new InvalidOperationException("Invalid atomic obstacle move");
                obstacle.position=plan.obstacleTo;
                foreach(var agent in agents) if(agent.HasAssignedObstacle() && agent.GetAssignedObstacleId()==obstacle.id) agent.AssignObstacle(obstacle.id,obstacle.position);
            }
            obstacle.stalled=0; Manipulations++;
            data.RecordVolunteerWork(step,plan.agent.AgentID,obstacle.id,obstacle.workProgress,true);
            obstacle.workProgress=0;
            data.RecordObstacleEvent(step,obstacle,plan.kind.ToString().ToLowerInvariant(),plan.agent.AgentID);
            if(obstacle.position==obstacle.destination)
            {
                world.SettleObstacle(obstacle.position); obstacle.status=PaperObstacleStatus.Settled;
                completedWorkers.Add(plan.agent.AgentID); obstacle.candidates.Clear();
                data.RecordObstacleEvent(step,obstacle,"settle",plan.agent.AgentID);
            }
        }
    }
    public void AfterCommit(int step,SimulationData data)
    {
        foreach(var id in completedWorkers)
        { byId[id].SetVolunteerState(PedestrianAgent.VolunteerState.None); foreach(var obstacle in Obstacles) if(obstacle.worker==id) obstacle.worker=-1; }
        foreach(var obstacle in Obstacles) data.RecordObstacleState(step,obstacle);
        anticipation.UpdateField(agents);
    }
    private void RefreshRoles()
    {
        foreach(var agent in agents)
        {
            if(agent.IsEvacuated()) continue;
            var active=Obstacles.Find(o=>o.worker==agent.AgentID && o.status==PaperObstacleStatus.Moving);
            if(active!=null) {agent.SetVolunteerState(PedestrianAgent.VolunteerState.ActiveVolunteer);agent.AssignObstacle(active.id,active.position);continue;}
            bool potential=Obstacles.Any(o=>o.status==PaperObstacleStatus.Unmoved && o.worker<0 && o.candidates.Contains(agent.AgentID));
            agent.SetVolunteerState(potential ? PedestrianAgent.VolunteerState.PotentialVolunteer : PedestrianAgent.VolunteerState.None);
        }
    }
    private void Finish(PaperObstacle obstacle,PaperObstacleStatus status)
    {
        obstacle.status=status; world.movingObstacles.Remove(obstacle.position); obstacle.candidates.Clear();
        if(status==PaperObstacleStatus.Settled) world.SettleObstacle(obstacle.position);
        else foreach(var knowledge in Knowledge.Values) knowledge.Decide(obstacle.id,false);
        if(obstacle.worker>=0) byId[obstacle.worker].SetVolunteerState(PedestrianAgent.VolunteerState.None);
        obstacle.worker=-1;
    }
    private void UpdateDensity(PaperObstacle obstacle)
    {
        int area=0,count=0;
        for(int x=1;x<world.width-1;x++) for(int y=1;y<world.height-1;y++)
            if(PaperGrid.Distance(new Vector2Int(x,y),obstacle.position)<=settings.obstacleVisibilityRange && world.IsWalkable(x,y)) area++;
        foreach(var agent in agents) if(!agent.IsEvacuated() && !agent.IsActiveVolunteer() &&
            PaperGrid.Distance(agent.gridPos,obstacle.position)<=settings.obstacleVisibilityRange) count++;
        obstacle.recentDensity.Enqueue(area>0 ? (float)count/area : 0);
        while(obstacle.recentDensity.Count>Mathf.Max(1,settings.paperDensityWindow)) obstacle.recentDensity.Dequeue();
    }
    private bool ShouldAbandon(PaperObstacle obstacle)
    {
        if(obstacle.recentDensity.Count<Mathf.Max(1,settings.paperDensityWindow) || obstacle.recentDensity.Average()>=settings.paperAbandonDensity) return false;
        return ResearchEnvironment.PaperExitNonBlockage(world,obstacle.position)>0f;
    }
}
