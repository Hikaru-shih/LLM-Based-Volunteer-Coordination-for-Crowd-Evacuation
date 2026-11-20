using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class PaperModelValidation
{
    private static int checks;
    private static void Check(bool condition,string message)
    { checks++; if(!condition) throw new Exception(message); }
    private static SimulationManager Manager(int size=11)
    {
        var manager=ResearchValidation.CreateManager(Path.GetFullPath("tmp/paper-validation/unit"));
        manager.obstacleHandlingMode=ObstacleHandlingMode.PaperRelocation;
        manager.volunteerDecisionMode=SimulationManager.VolunteerDecisionMode.OriginalGameTheory;
        manager.world.width=manager.world.height=size;
        manager.world.cellSize=0.4f;
        manager.kStatic=3;manager.kDynamic=1;manager.kAnticipation=5;
        manager.conflictStrategy=Decision.YielderGame.Strategy.PaperYielder;
        manager.movementStrategy=PedestrianAgent.MovementStrategy.Combined;
        manager.volunteerCost=0.005f;manager.failureCost=0.5f;manager.unwillingnessOmega=5;
        manager.obstacleVisibilityRange=20;manager.obstacleCount=5;
        manager.maxSimulationSteps=1000;
        return manager;
    }
    private static PaperMove Plan(SimulationManager manager,Vector2Int workerPosition,Vector2Int obstaclePosition,Vector2Int destination,bool preferPull=true)
    {
        manager.world.Init(); manager.world.paperNeighborhood=true;
        manager.world.SetCellType(obstaclePosition.x,obstaclePosition.y,CellType.Obstacle);
        var agent=manager.agentPrefab.GetComponent<PedestrianAgent>();agent.Init(manager.world,workerPosition);
        return PaperObstaclePlanner.Plan(manager.world,new PaperObstacle {position=obstaclePosition,destination=destination,hasDestination=true},
            agent,new HashSet<Vector2Int>{workerPosition},preferPull);
    }

    [MenuItem("Research/Validate paper relocation model")]
    public static void RunAll()
    {
        checks=0; Directory.CreateDirectory("tmp/paper-validation");
        try
        {
            ManipulationRules(); KnowledgeAndFields(); Abandonment(); WorkTiming(); VolunteerCurves();
            RunMatrix();
            File.WriteAllText("tmp/paper-validation/result.json",$"{{\"passed\":true,\"checks\":{checks},\"unity\":\"{Application.unityVersion}\",\"remoteRequests\":0}}");
            Debug.Log($"PAPER_MODEL_VALIDATION_PASSED: {checks} checks");
        }
        catch(Exception error)
        {
            File.WriteAllText("tmp/paper-validation/failure.txt",error.ToString());
            Debug.LogException(error);throw;
        }
        finally {ResearchValidation.Cleanup();}
    }
    public static void RunWithLegacyRegression()
    { ResearchValidation.RunAll();RunAll(); }
    public static void RunCompleteAudit()
    { RunWithLegacyRegression();RunExitWidthStudy();RunExitWidthControl(); }

    public static void RunExitWidthStudy()
    { RunExitWidthStudy(true); }
    public static void RunExitWidthControl()
    { RunExitWidthStudy(false); }
    private static void RunExitWidthStudy(bool weighted)
    {
        Directory.CreateDirectory("tmp/paper-validation");
        var manager=Manager(50);manager.researchOutputFolder=Path.GetFullPath("tmp/paper-validation/figure3_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss"));
        manager.researchScenario=ResearchScenario.AsymmetricOpenExits;manager.agentCount=750;manager.paperExitWidthWeighting=weighted;
        manager.agentSpawnAreaSize=new Vector2Int(48,48);manager.obstacleCount=0;
        manager.volunteerDecisionMode=SimulationManager.VolunteerDecisionMode.NoVolunteers;
        manager.kAnticipation=0;manager.maxSimulationSteps=1500;
        try
        {
            using(var writer=new StreamWriter(weighted ? "tmp/paper-validation/figure3_exit_width.csv" : "tmp/paper-validation/figure3_exit_width_unweighted.csv"))
            {
                writer.WriteLine("Run,Seed,ExitAWidth2,ExitBWidth4,ExitBShare,T100");
                for(int run=1;run<=100;run++)
                {
                    ResearchValidation.Begin(manager,run);
                    while(manager.IsSimulationRunning()) ResearchValidation.Step(manager);
                    int a=manager.GetAllAgents().Count(agent=>agent.IsEvacuated() && agent.gridPos.y==0);
                    int b=manager.GetAllAgents().Count(agent=>agent.IsEvacuated() && agent.gridPos.y==49);
                    if(a+b!=750) throw new Exception($"Fig3 study did not fully evacuate: run {run}, {a+b}/750");
                    writer.WriteLine(System.FormattableString.Invariant($"{run},{2025+run},{a},{b},{(float)b/750:F6},{manager.currentStep}"));
                    writer.Flush();
                }
            }
            manager.ResetSimulation();Debug.Log("FIGURE3_EXIT_WIDTH_STUDY_PASSED: 100 completed runs, width weighting="+weighted);
        }
        finally {ResearchValidation.Cleanup();}
    }

    private static void ManipulationRules()
    {
        var manager=Manager();
        var push=Plan(manager,new Vector2Int(5,5),new Vector2Int(5,4),new Vector2Int(5,2));
        Check(push.kind==PaperManipulation.Push && push.agentTo==new Vector2Int(5,4) && push.obstacleTo==new Vector2Int(5,3),"Fig6 push");
        var pull=Plan(manager,new Vector2Int(5,4),new Vector2Int(5,3),new Vector2Int(5,6));
        Check(pull.kind==PaperManipulation.Pull && pull.obstacleTo==new Vector2Int(5,4) && pull.agentTo==new Vector2Int(5,5),"Fig6 pull");
        var rotate=Plan(manager,new Vector2Int(5,5),new Vector2Int(5,4),new Vector2Int(7,4));
        Check(rotate.kind==PaperManipulation.Rotate && rotate.agentTo==rotate.agentFrom && rotate.obstacleTo==new Vector2Int(6,4),"Eq15 rotation");
        var reposition=Plan(manager,new Vector2Int(5,4),new Vector2Int(5,3),new Vector2Int(5,6),false);
        Check(reposition.kind==PaperManipulation.Reposition && reposition.obstacleTo==reposition.obstacleFrom &&
            PaperGrid.Adjacent(reposition.agentTo,reposition.obstacleFrom),"Fig6 reposition without moving obstacle");
        Check(PaperGrid.Rotate45(new Vector2Int(1,1),new Vector2Int(-1,1))==new Vector2Int(0,1),"Eq15 half-away rounding");
        var world=manager.world;
        int count=world.GetObstaclePositions().Count;
        Check(world.MoveObstacle(new Vector2Int(5,3),new Vector2Int(5,2)),"physical obstacle translation");
        Check(world.GetObstaclePositions().Count==count,"obstacle conservation");
        world.SettleObstacle(new Vector2Int(5,2));
        Check(!world.MoveObstacle(new Vector2Int(5,2),new Vector2Int(5,1)),"settled obstacle stays in room and cannot move again");
        world.SetExits(true,false,false,false,1);world.paperNeighborhood=true;
        var sff=new StaticFloorField(world);
        Check(Mathf.Abs(sff.GetDistance(new Vector2Int(6,1))-1.5f*Mathf.Exp(-1))<0.00001f,"SFF Moore diagonal cost");
        world.Init();world.paperNeighborhood=true;world.SetExits(true,false,false,false,3);
        world.SetCellType(5,1,CellType.Obstacle);
        var worker=manager.agentPrefab.GetComponent<PedestrianAgent>();worker.Init(world,new Vector2Int(5,2));
        var target=new PaperObstacle{position=new Vector2Int(5,1)};
        Check(PaperObstaclePlanner.ChooseDestination(world,target,worker,new HashSet<Vector2Int>(),PaperDestinationRule.NextToWallsOrObstacles,2),"geometric sigma destination exists");
        var geometricDestination=target.destination;
        Check(target.destination!=worker.gridPos,"destination excludes volunteer's own position");
        Check(PaperObstaclePlanner.ChooseDestination(world,target,worker,new HashSet<Vector2Int>(),PaperDestinationRule.NextToWallsOrObstacles,2,3,PaperSigmaMetric.ExitFloorField),"author-style SFF sigma destination exists");
        Check(target.destination!=geometricDestination && PaperGrid.ExitField(world,new HashSet<Vector2Int>())[target.destination.x,target.destination.y]>=2,"sigma metric choice is explicit and effective");
        ResearchValidation.Cleanup();
    }
    private static void KnowledgeAndFields()
    {
        var knowledge=new PaperKnowledge();
        knowledge.Decide(1,true);knowledge.Decide(2,true);knowledge.Decide(3,false);
        Check(knowledge.willing.SetEquals(new[]{1,2}) && knowledge.refused.SetEquals(new[]{3}),"multiple-obstacle Lw/Lb");
        knowledge.Decide(1,false);Check(!knowledge.willing.Contains(1) && knowledge.refused.Contains(1),"decision lists remain disjoint");
        var manager=Manager();manager.researchScenario=ResearchScenario.SingleBlockedExit;
        manager.agentCount=2;ResearchValidation.Begin(manager);
        foreach(var agent in manager.GetAllAgents()) agent.Init(manager.world,new Vector2Int(5+agent.AgentID,3));
        ResearchValidation.Step(manager);
        Check(manager.PaperModel.Obstacles.All(o=>o.id>=0),"stable nonnegative obstacle IDs");
        Check(manager.PaperModel.Knowledge.Values.Any(k=>k.willing.Count>1),"overlapping interference regions evaluated per obstacle");
        manager.ResetSimulation();ResearchValidation.Cleanup();
    }
    private static void Abandonment()
    {
        var manager=Manager();manager.agentCount=1;manager.researchScenario=ResearchScenario.TwoExitsOneBlocked;
        manager.paperDensityWindow=1;manager.paperAbandonDensity=1;ResearchValidation.Begin(manager);
        var agent=manager.GetAllAgents()[0];agent.Init(manager.world,new Vector2Int(5,2));
        var obstacle=manager.PaperModel.Obstacles.First(o=>o.position==new Vector2Int(5,1));
        Check(ResearchEnvironment.PaperExitNonBlockage(manager.world,obstacle.position)==0,"Moore-neighbor tau fully blocked");
        var edge=manager.PaperModel.Obstacles.First(o=>o.position==new Vector2Int(3,1));
        manager.world.MoveObstacle(edge.position,new Vector2Int(3,2));edge.position=new Vector2Int(3,2);
        edge.status=PaperObstacleStatus.Settled;manager.world.SettleObstacle(edge.position);
        Check(Mathf.Abs(ResearchEnvironment.PaperExitNonBlockage(manager.world,obstacle.position)-0.2f)<0.00001f,"Moore-neighbor tau partial blockage");
        obstacle.worker=agent.AgentID;obstacle.status=PaperObstacleStatus.Moving;
        agent.SetVolunteerState(PedestrianAgent.VolunteerState.ActiveVolunteer);agent.AssignObstacle(obstacle.id,obstacle.position);
        manager.world.movingObstacles.Add(obstacle.position);
        ResearchValidation.Step(manager);
        Check(obstacle.status==PaperObstacleStatus.Abandoned && obstacle.worker==-1 && agent.GetAssignedObstacleId()!=obstacle.id,"low-density moving average releases obstacle's volunteer");
        Check(manager.world.cells[obstacle.position.x,obstacle.position.y]==CellType.Obstacle,"abandonment retains physical obstacle");
        Check(!manager.world.settledObstacles.Contains(obstacle.position),"abandonment is not permanent destination settlement");
        manager.paperAbandonDensity=0;ResearchValidation.Step(manager);
        Check(obstacle.status==PaperObstacleStatus.Unmoved || obstacle.status==PaperObstacleStatus.Moving,"abandoned obstacle can resume under renewed demand");
        manager.ResetSimulation();ResearchValidation.Cleanup();
        manager=Manager();manager.agentCount=1;manager.researchScenario=ResearchScenario.SingleBlockedExit;
        manager.volunteerDecisionMode=SimulationManager.VolunteerDecisionMode.NoVolunteers;manager.maxSimulationSteps=50;
        ResearchValidation.Begin(manager);
        while(manager.IsSimulationRunning()) ResearchValidation.Step(manager);
        Check(manager.GetEvacuatedCount()==0,"fully blocked Moore exit cannot be bypassed diagonally without relocation");
        manager.ResetSimulation();ResearchValidation.Cleanup();
    }
    private static void WorkTiming()
    {
        var manager=Manager();manager.agentCount=1;manager.researchScenario=ResearchScenario.SingleBlockedExit;
        manager.paperManipulationSteps=3;ResearchValidation.Begin(manager);
        var agent=manager.GetAllAgents()[0];agent.Init(manager.world,new Vector2Int(5,2));
        var obstacle=manager.PaperModel.Obstacles.First(o=>o.position==new Vector2Int(5,1));
        obstacle.worker=agent.AgentID;obstacle.status=PaperObstacleStatus.Moving;
        obstacle.destination=new Vector2Int(5,5);obstacle.hasDestination=true;
        agent.SetVolunteerState(PedestrianAgent.VolunteerState.ActiveVolunteer);agent.AssignObstacle(obstacle.id,obstacle.position);
        manager.world.movingObstacles.Add(obstacle.position);
        var origin=obstacle.position;
        ResearchValidation.Step(manager);ResearchValidation.Step(manager);
        Check(obstacle.position==origin && obstacle.workProgress==2 && obstacle.stalled==0,"tv work delay does not move or count as deadlock");
        ResearchValidation.Step(manager);
        Check(obstacle.position!=origin && obstacle.workProgress==0,"tv completed before next physical manipulation");
        manager.ResetSimulation();ResearchValidation.Cleanup();
    }
    private static void RunMatrix()
    {
        string folder=Path.GetFullPath("tmp/paper-validation/runs_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss"));
        int runs=0,completed=0,moves=0,steps=0;
        foreach(var scenario in new[]{ResearchScenario.OpenRoom,ResearchScenario.SingleBlockedExit,ResearchScenario.TwoExitsOneBlocked,ResearchScenario.RandomRoom})
        {
            var manager=Manager(30);manager.researchOutputFolder=folder;manager.agentCount=50;
            manager.agentSpawnAreaSize=new Vector2Int(24,24);manager.researchScenario=scenario;
            if(scenario==ResearchScenario.RandomRoom) {manager.obstacleCount=40;manager.agentSpawnAreaSize=new Vector2Int(15,15);}
            for(int run=1;run<=30;run++)
            {
                ResearchValidation.Begin(manager,run);
                int initialObstacles=manager.world.GetObstaclePositions().Count;
                while(manager.IsSimulationRunning())
                {
                    var before=manager.GetAllAgents().ToDictionary(a=>a.AgentID,a=>a.gridPos);
                    var beforeObstacles=manager.PaperModel.Obstacles.ToDictionary(o=>o.id,o=>o.position);
                    ResearchValidation.Step(manager);steps++;
                    var live=manager.GetAllAgents().Where(a=>!a.IsEvacuated()).ToArray();
                    Check(live.Select(a=>a.gridPos).Distinct().Count()==live.Length,"no agent overlap");
                    Check(manager.world.GetObstaclePositions().Count==initialObstacles,"physical obstacle conservation at every step");
                    foreach(var agent in manager.GetAllAgents())
                    {
                        var old=before[agent.AgentID];
                        Check(agent.gridPos==old || PaperGrid.Adjacent(agent.gridPos,old),"agent Moore locality");
                        if(!agent.IsEvacuated()) Check(manager.world.IsWalkable(agent.gridPos.x,agent.gridPos.y),"agent does not overlap obstacle");
                    }
                    foreach(var obstacle in manager.PaperModel.Obstacles)
                    {
                        var old=beforeObstacles[obstacle.id];
                        Check(obstacle.position==old || PaperGrid.Adjacent(obstacle.position,old),"obstacle Moore locality");
                        if(obstacle.position!=old) moves++;
                        Check(manager.world.cells[obstacle.position.x,obstacle.position.y]==CellType.Obstacle,"registry matches grid");
                    }
                }
                runs++;bool all=manager.GetEvacuatedCount()==50;if(all)completed++;
                if(!all) throw new Exception($"Relocation full evacuation failed: {scenario},seed={2025+run},evacuated={manager.GetEvacuatedCount()}/50");
            }
            manager.ResetSimulation();ResearchValidation.Cleanup();
        }
        Check(moves>0,"matrix actually performs obstacle relocation");
        Directory.CreateDirectory(folder);
        File.WriteAllText(Path.Combine(folder,"matrix_result.json"),$"{{\"runs\":{runs},\"completed100\":{completed},\"steps\":{steps},\"obstacleMoves\":{moves},\"watchdog\":1000}}");
    }

    private static void VolunteerCurves()
    {
        var strategy=new Decision.OriginalGameTheoryVolunteerStrategy();
        using(var writer=new StreamWriter("tmp/paper-validation/figure7_analytic.csv"))
        {
            writer.WriteLine("X,Tau,Beta,Q,AllDefectProbability,ExpectedWaitSteps");
            foreach(float tau in new[]{0.1f,0.9f}) foreach(float beta in new[]{0.1f,0.5f,0.9f})
            {
                double previousQ=-1,previousAll=-1;
                for(int players=2;players<=10;players++)
                {
                    var context=new Decision.VolunteerDecisionContext {nearbyAgentCount=players,exitNonBlockage=tau,
                        unwillingness=5,volunteerCost=beta*0.5f,failureCost=0.5f};
                    double q=1-strategy.CalculateVolunteerProbability(context);
                    double expected=Math.Pow(1-Math.Exp(-5*tau),1.0/players)*Math.Pow(beta,1.0/(players-1));
                    double all=Math.Pow(q,players);
                    Check(Math.Abs(q-expected)<0.00001,"Fig7 Eq25 analytical probability");
                    Check(Math.Abs(all-(1-Math.Exp(-5*tau))*Math.Pow(beta,(double)players/(players-1)))<0.00001,"Fig7 Eq24 all-defect probability");
                    Check(q>=previousQ && all>=previousAll,"Fig7 bystander monotonicity");
                    previousQ=q;previousAll=all;
                    writer.WriteLine(System.FormattableString.Invariant($"{players},{tau},{beta},{q:F8},{all:F8},{1/(1-all):F8}"));
                }
            }
        }
    }
}
