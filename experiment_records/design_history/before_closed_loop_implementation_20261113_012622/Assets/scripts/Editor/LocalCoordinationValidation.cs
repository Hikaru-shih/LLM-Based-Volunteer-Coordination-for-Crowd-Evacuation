using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Coordination;
using UnityEngine;

public static class LocalCoordinationValidation
{
    public static void CaptureReference()
    {
        string root=Path.GetFullPath("tmp/coordination-reference-before");
        foreach(var scenario in new[]{ResearchScenario.SingleBlockedExit,ResearchScenario.TwoExitsOneBlocked,ResearchScenario.RandomRoom})
        foreach(int seed in new[]{2026,2027})
        {
            var manager=Make(Path.Combine(root,scenario+"_"+seed),scenario,seed);
            try {ResearchValidation.Begin(manager);while(manager.IsSimulationRunning()) ResearchValidation.Step(manager);}
            finally {manager.ResetSimulation();ResearchValidation.Cleanup();}
        }
        Debug.Log("COORDINATION_REFERENCE_BASELINE_CAPTURED: six bounded no-API fixtures");
    }
    public static ExecutionMode ExtensionMode=ExecutionMode.CoordinatedExtension;
    private static int checks;
    private static string runFolder,runId;
    private static void Check(bool condition,string message) {checks++;if(!condition) throw new Exception(message);}
    public static void Run()
    {
        runId=DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")+"_"+Guid.NewGuid().ToString("N").Substring(0,6);
        runFolder=Path.GetFullPath("tmp/local-coordination-validation/runs/"+runId);
        checks=0;CoordinationContractValidation.Run();PureReservations();
        string before=Path.GetFullPath("tmp/coordination-reference-before"),after=Path.Combine(runFolder,"reference-after");
        foreach(var scenario in new[]{ResearchScenario.SingleBlockedExit,ResearchScenario.TwoExitsOneBlocked,ResearchScenario.RandomRoom})
        foreach(int seed in new[]{2026,2027})
        {
            string name=scenario+"_"+seed;
            var manager=Make(Path.Combine(after,name),scenario,seed);
            try {ResearchValidation.Begin(manager);while(manager.IsSimulationRunning()) ResearchValidation.Step(manager);}
            finally {manager.ResetSimulation();ResearchValidation.Cleanup();}
            foreach(string suffix in new[]{"_trajectories.csv","_obstacles.csv","_obstacle_events.csv","_paper_decisions.csv","_volunteer_work.csv","_diagnostics.csv"})
            {
                string a=Directory.GetFiles(Path.Combine(before,name),"*"+suffix).SingleOrDefault();
                string b=Directory.GetFiles(Path.Combine(after,name),"*"+suffix).SingleOrDefault();
                Check((a==null && b==null) || (a!=null && b!=null && File.ReadAllText(a)==File.ReadAllText(b)),"Paper-reference trajectory/event regression: "+name+suffix);
            }
        }
        UnreachableFixture();NoLegalPlacementFixture();
        ExtensionFixture("controlled",AvailabilityMode.AllEligibleControl,SimulationManager.VolunteerDecisionMode.OriginalGameTheory,true);
        ExtensionFixture("game_theory",AvailabilityMode.PolicyWillingness,SimulationManager.VolunteerDecisionMode.OriginalGameTheory,true);
        ExtensionFixture("no_volunteers",AvailabilityMode.PolicyWillingness,SimulationManager.VolunteerDecisionMode.NoVolunteers,false);
        Directory.CreateDirectory("tmp/local-coordination-validation");
        File.WriteAllText("tmp/local-coordination-validation/result.json","{\"passed\":true,\"checks\":"+checks+",\"referenceFixtures\":6,\"extensionFixtures\":3,\"remoteRequests\":0,\"runId\":\""+runId+"\"}");
        Debug.Log("LOCAL_COORDINATION_VALIDATION_PASSED: "+checks+" checks, six reference regressions, three bounded extension fixtures; no API");
    }
    private static void PureReservations()
    {
        var snapshot=new Snapshot {snapshotId="test",step=1,worldRevision=1,
            candidates=new[]{new Candidate {agentId=0},new Candidate {agentId=1}},
            tasks=new[]{new Task {obstacleId=0},new Task {obstacleId=1}},
            edges=new[]{new Edge {agentId=0,obstacleId=0,eligible=true,consented=true,approachCost=1},
                new Edge {agentId=0,obstacleId=1,eligible=true,consented=true,approachCost=2},
                new Edge {agentId=1,obstacleId=0,eligible=true,consented=true,approachCost=2}}};
        var proposal=LocalDispatcher.Propose(snapshot);
        Check(proposal.assignments.Length==1 && proposal.assignments[0].agentId==0 && proposal.assignments[0].obstacleId==0,"Greedy policy order changed");
        // This example intentionally demonstrates that greedy is not maximum-cardinality.
        var book=new ReservationBook();book.Commit(snapshot,proposal);
        snapshot.step=2;Check(book.Reconcile(snapshot,3,2).Count==0,"Reservation disappeared before idle limit");
        snapshot.edges[0].approachCost=.5f;snapshot.step=3;Check(book.Reconcile(snapshot,3,2).Count==0,"Progress did not preserve reservation");
        snapshot.step=6;Check(book.Reconcile(snapshot,3,2).Single().reason=="no_progress" && book.Cooling(0,0,6),"Idle release/cooldown failed");
        Check(!book.Cooling(0,0,8),"Cooldown never expires");
        snapshot.step=8;book.Commit(snapshot,LocalDispatcher.Propose(snapshot));snapshot.edges[0].consented=false;
        Check(book.Reconcile(snapshot,3,2).Single().reason=="eligibility_or_consent_lost","Refused edge retained");
        snapshot.edges[0].consented=true;book.Commit(snapshot,LocalDispatcher.Propose(snapshot));
        bool rejected=false;try {book.Commit(snapshot,LocalDispatcher.Propose(snapshot));} catch(InvalidOperationException) {rejected=true;}
        Check(rejected && book.Entries.Count()==1,"Existing reservation was overwritten or partially committed");
        snapshot.tasks[0].settled=true;
        Check(book.Reconcile(snapshot,3,2).Single().reason=="task_unavailable","Completed task retained");
        snapshot.tasks[0].settled=false;book.Commit(snapshot,LocalDispatcher.Propose(snapshot));snapshot.candidates[0].evacuated=true;
        Check(book.Reconcile(snapshot,3,2).Single().reason=="agent_unavailable","Evacuated agent retained");
    }
    private static void UnreachableFixture()
    {
        var m=Make(Path.Combine(runFolder,"unreachable"),ResearchScenario.SingleBlockedExit,2026);
        m.paperExecutionMode=ExtensionMode;
        try
        {
            ResearchValidation.Begin(m);
            for(int x=1;x<m.world.width-1;x++) m.world.SetImmovableObstacle(new Vector2Int(x,2));
            var snapshot=m.PaperModel.BuildCoordinationSnapshot(0);
            Check(snapshot.edges.Length==0,"Unreachable approach remained eligible");
            Check(LocalDispatcher.Propose(snapshot).assignments.Length==0,"Unreachable task was assigned");
        }
        finally {m.ResetSimulation();ResearchValidation.Cleanup();}
    }
    private static void NoLegalPlacementFixture()
    {
        var m=Make(Path.Combine(runFolder,"no_legal_placement"),ResearchScenario.SingleBlockedExit,2026);
        m.paperExecutionMode=ExtensionMode;m.coordinationAvailability=AvailabilityMode.AllEligibleControl;
        m.paperDestinationExitDistance=1000;m.coordinationIdleSteps=2;m.coordinationCooldownSteps=2;
        try
        {
            ResearchValidation.Begin(m);
            foreach(var a in m.GetAllAgents()) a.Init(m.world,new Vector2Int(a.AgentID==0?3:7,2));
            for(int i=0;i<4;i++)
            {
                ResearchValidation.Step(m);
                Check(!m.GetAllAgents().Any(a=>a.IsActiveVolunteer()) && m.PaperModel.Manipulations==0,"Handler activated without a legal placement");
                Check(m.PaperModel.Obstacles.All(o=>o.status==PaperObstacleStatus.Unmoved),"Impossible placement moved an obstacle");
            }
            Check(m.PaperModel.Reservations.Entries.All(r=>r.createdStep>1),"Impossible placement reservation was never released");
        }
        finally {m.ResetSimulation();ResearchValidation.Cleanup();}
    }
    private static void ExtensionFixture(string name,AvailabilityMode availability,SimulationManager.VolunteerDecisionMode policy,bool expectMoves)
    {
        string folder=Path.Combine(runFolder,name);
        var m=Make(folder,ResearchScenario.SingleBlockedExit,2026);
        m.paperExecutionMode=ExtensionMode;m.coordinationAvailability=availability;m.volunteerDecisionMode=policy;
        int changes=0;
        try
        {
            ResearchValidation.Begin(m);
            while(m.IsSimulationRunning())
            {
                ResearchValidation.Step(m);changes+=m.PaperModel.Manipulations;
                var reservations=m.PaperModel.Reservations.Entries.ToArray();
                Check(reservations.Select(r=>r.agentId).Distinct().Count()==reservations.Length &&
                    reservations.Select(r=>r.obstacleId).Distinct().Count()==reservations.Length,"Reservation uniqueness failed");
                foreach(var r in reservations)
                    Check(m.PaperModel.Obstacles.First(o=>o.id==r.obstacleId).candidates.Contains(r.agentId),"Nonconsenting agent reserved");
                var snapshot=m.PaperModel.LastCoordinationSnapshot;
                string error;Check(ProposalValidator.Validate(snapshot,m.PaperModel.LastCoordinationProposal,snapshot.step,snapshot.worldRevision,out error),"Runtime proposal failed its shared validator");
            }
            Check(expectMoves ? changes>0 : changes==0,"Unexpected physical manipulation result");
            Check(Directory.GetFiles(folder,"*_coordination_snapshots.jsonl").Length==1,"Snapshot export missing");
        }
        finally {m.ResetSimulation();ResearchValidation.Cleanup();}
    }

    private static SimulationManager Make(string output,ResearchScenario scenario,int seed)
    {
        var m=ResearchValidation.CreateManager(output);m.obstacleHandlingMode=ObstacleHandlingMode.PaperRelocation;
        m.volunteerDecisionMode=SimulationManager.VolunteerDecisionMode.OriginalGameTheory;m.researchScenario=scenario;
        m.baseSeed=seed;m.agentCount=2;m.obstacleCount=5;m.exitCount=1;m.world.cellSize=.4f;
        m.kStatic=3;m.kDynamic=1;m.kAnticipation=5;m.movementTemperature=1;
        m.volunteerCost=.005f;m.failureCost=.5f;m.unwillingnessOmega=5;m.obstacleVisibilityRange=20;
        m.conflictStrategy=Decision.YielderGame.Strategy.PaperYielder;m.movementStrategy=PedestrianAgent.MovementStrategy.Combined;
        m.paperDiffusion=.3f;m.paperDecay=.1f;m.paperAnticipationRadius=6;m.yielderDefectionCost=1;m.maxSimulationSteps=40;
        return m;
    }
}
