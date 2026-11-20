using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using Decision;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

/// <summary>Offline regression checks against actual Unity components and exported files.</summary>
public static class ResearchValidation
{
    private static int assertions;
    private static readonly List<GameObject> objects = new List<GameObject>();
    private const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;
    private static string Output => Path.GetFullPath("tmp/research-validation");

    [MenuItem("Research/Validate simulation and paper equations")]
    public static void RunAll()
    {
        assertions = 0;
        Directory.CreateDirectory(Output);
        try
        {
            VolunteerEquation(); YielderEquation(); FieldEquations(); Conflicts(); AStarRetry();
            Exports(); SimulationLifecycle(); Reproducibility(); VolunteerActivationRegression(); ReferenceRoomCompletion();
            File.WriteAllText(Path.Combine(Output, "result.json"),
                $"{{\"passed\":true,\"assertions\":{assertions},\"unity\":\"{Application.unityVersion}\"}}");
            Debug.Log($"RESEARCH_VALIDATION_PASSED: {assertions} assertions");
        }
        catch (Exception error)
        {
            File.WriteAllText(Path.Combine(Output, "result.json"),
                "{\"passed\":false,\"error\":" + SimulationData.Csv(error.ToString()).Replace("\n", " ").Replace("\r", " ") + "}");
            Debug.LogException(error);
            throw;
        }
        finally { Cleanup(); }
    }
    public static void Cleanup()
    {
        foreach (var obj in objects) if (obj != null) Object.DestroyImmediate(obj);
        objects.Clear();
    }
    private static void Check(bool condition, string message)
    { assertions++; if (!condition) throw new Exception(message); }
    private static void Near(double actual, double expected, string message, double tolerance = 0.00001)
    { Check(Math.Abs(actual - expected) <= tolerance, $"{message}: expected {expected}, got {actual}"); }
    private static GameObject New(string name)
    { var obj = new GameObject(name); objects.Add(obj); return obj; }
    private static GridWorld World(int size = 9)
    { var world = New("ValidationWorld").AddComponent<GridWorld>(); world.width = world.height = size; world.Init(); return world; }
    private static PedestrianAgent Agent(GridWorld world, int x, int y)
    { var agent = New("ValidationAgent").AddComponent<PedestrianAgent>(); agent.Init(world, new Vector2Int(x, y)); return agent; }
    private static void VolunteerEquation()
    {
        var strategy = new OriginalGameTheoryVolunteerStrategy();
        var context = new VolunteerDecisionContext { nearbyAgentCount = 4, exitNonBlockage = 0.3f,
            volunteerCost = 0.1f, failureCost = 0.5f, unwillingness = 5f };
        double expected = 1 - Math.Pow(1 - Math.Exp(-1.5), 0.25) * Math.Pow(0.2, 1.0 / 3);
        Near(strategy.CalculateVolunteerProbability(context), expected, "Eq25");
        context.unwillingness = 0; Near(strategy.CalculateVolunteerProbability(context), 1, "omega=0");
        context.exitNonBlockage = 1; Near(strategy.CalculateVolunteerProbability(context), 0, "unblocked exit skips game");
        context.nearbyAgentCount = 1; context.exitNonBlockage = 0; Near(strategy.CalculateVolunteerProbability(context), 1, "lone agent fully blocked");
        context.exitNonBlockage = 0.2f; Near(strategy.CalculateVolunteerProbability(context), 0, "lone agent partially blocked");
    }
    private static void YielderEquation()
    {
        Near(YielderGame.CooperationProbability(3, 0.2f), Math.Sqrt(0.3), "Eq19");
        Near(YielderGame.CooperationProbability(3, 1), 1, "pure cooperative equilibrium");
        var world = World(); var a = Agent(world, 2, 2); var b = Agent(world, 3, 3);
        var contenders = new List<PedestrianAgent> { a, b };
        var game = new YielderGame(YielderGame.Strategy.PaperYielder) { defectionCost = 0 };
        Check(game.ResolveConflict(contenders) == null, "multiple defectors must block movement");
        game.defectionCost = 1; Check(game.ResolveConflict(contenders) != null, "all cooperators select a winner");
        game.friction = 1; Check(game.ResolveConflict(contenders) == null, "friction blocks movement");
    }
    private static void FieldEquations()
    {
        var world = World();
        world.SetExits(true, false, false, false, 3);
        Check(world.cells[4, 8] == CellType.Wall && world.exitPositions.Count == 3, "SetExits removes old exits");
        ResearchEnvironment.Configure(world, ResearchScenario.SingleBlockedExit, 3, 3, 3);
        Near(ResearchEnvironment.ExitNonBlockage(world, new Vector2Int(4, 1), 3), 0, "fully blocked tau");
        world.RemoveObstacleAt(3, 1);
        Near(ResearchEnvironment.ExitNonBlockage(world, new Vector2Int(4, 1), 3), 1.0 / 3, "partial tau");
        var sff = new StaticFloorField(world);
        Check(sff.GetDistance(new Vector2Int(4, 4)) < float.MaxValue, "base SFF ignores movable obstacles");
        Near(sff.GetDistance(new Vector2Int(4, 4)), 4 * Math.Exp(-1), "exit-width SFF cardinal metric");
        world.SetExits(true, true, false, false, 3);
        world.SetCellType(3, 1, CellType.Obstacle);
        var local = new StaticFloorField(world, world.GetObstaclePositions());
        Check(local.GetDistance(new Vector2Int(4, 2)) > local.GetDistance(new Vector2Int(4, 3)), "rejected blockers redirect toward open exit");
        world.SetExits(true, false, false, false, 3);
        var agent = Agent(world, 4, 4); var field = new DynamicFloorField(world) { decayRate = 0, diffusionRate = 0 };
        Near(field.GetValue(agent.gridPos), 0, "DFF starts at zero");
        agent.desiredPos = new Vector2Int(4, 5); agent.CommitMove(); field.UpdateField(new[] { agent });
        Near(field.GetValue(new Vector2Int(4, 4)), 1, "DFF deposits at departed cell");
        Near(field.GetValue(agent.gridPos), 0, "DFF does not deposit at destination");
        field.UpdateField(new[] { agent }); Near(field.GetValue(new Vector2Int(4, 4)), 1, "no duplicate trace");
        field.decayRate = 0.1f; field.diffusionRate = 0.3f; field.UpdateField(new[] { agent });
        Near(field.GetValue(new Vector2Int(4, 4)), 0.63, "Eq7 decay and diffusion");
        Near(field.GetValue(new Vector2Int(4, 5)), 0.0675, "Eq8 adjacent diffusion");
        Near(AnticipationFloorField.PaperDistance(Vector2Int.zero, new Vector2Int(2, 3)), 4, "Eq11 distance");
        Near(AnticipationFloorField.Contribution(new Vector2Int(4, 3), new Vector2Int(4, 4), new Vector2Int(4, 5), 6), 3, "AFF forward fan");
        Near(AnticipationFloorField.Contribution(new Vector2Int(4, 3), new Vector2Int(4, 4), new Vector2Int(4, 0), 6), 1, "AFF rear circle");
        var second = Agent(world, 4, 5);
        agent.SetVolunteerState(PedestrianAgent.VolunteerState.ActiveVolunteer); agent.AssignObstacle(1, new Vector2Int(4, 6));
        second.SetVolunteerState(PedestrianAgent.VolunteerState.ActiveVolunteer); second.AssignObstacle(2, new Vector2Int(4, 6));
        var aff = new AnticipationFloorField(world); aff.UpdateField(new[] { agent, second });
        Near(aff.GetValue(new Vector2Int(4, 6)), 6, "Eq14 sums overlapping fields");
        var volunteerField = new DynamicFloorField(world) { decayRate = 0, diffusionRate = 0 };
        agent.desiredPos = new Vector2Int(5, 5); agent.CommitMove(); volunteerField.UpdateField(new[] { agent });
        Near(volunteerField.GetValue(new Vector2Int(4, 5)), 0, "volunteer leaves no trace");
    }
    private static void Conflicts()
    {
        var world = World(); var a = Agent(world, 1, 2); var b = Agent(world, 2, 2); var c = Agent(world, 3, 3);
        a.desiredPos = b.gridPos; b.desiredPos = c.desiredPos = new Vector2Int(3, 2);
        var agents = new List<PedestrianAgent> { a, c, b };
        MovementConflictResolver.Resolve(agents, new YielderGame(YielderGame.Strategy.FirstCome));
        foreach (var agent in agents) agent.CommitMove();
        Check(agents.Select(agent => agent.gridPos).Distinct().Count() == 3, "rejection chain preserves unique occupancy");
        Check(a.gridPos == new Vector2Int(1, 2) && b.gridPos == new Vector2Int(2, 2), "chain propagates to origin");
        a.desiredPos = new Vector2Int(5, 2); a.CommitMove(); Check(a.gridPos == new Vector2Int(1, 2), "nonlocal movement rejected");
    }
    private static void AStarRetry()
    {
        var world = World(); world.SetExits(true, false, false, false, 3);
        var agent = Agent(world, 4, 6); agent.SetPathfinder(new AStarPathfinding(world));
        agent.SetMovementStrategy(PedestrianAgent.MovementStrategy.AStar);
        Vector2Int proposed = agent.ProposeMove(); agent.desiredPos = agent.gridPos; agent.CommitMove();
        Check(agent.ProposeMove() == proposed, "AStar retries rejected node");
        agent.CommitMove(); Vector2Int before = agent.gridPos;
        agent.ProposeMove(); agent.CommitMove(); Check(Mathf.Abs(agent.gridPos.x - before.x) + Mathf.Abs(agent.gridPos.y - before.y) == 1, "AStar remains adjacent after retry");
        var far = Agent(world, 4, 6); far.SetFloorField(new StaticFloorField(world)); far.SetMovementCoefficients(1000, 0, 0, 0.01f);
        far.SetMovementStrategy(PedestrianAgent.MovementStrategy.Static); Check(far.ProposeMove().y == 5, "stable softmax avoids underflow freeze");
    }
    private static void Exports()
    {
        var culture = CultureInfo.CurrentCulture;
        try
        {
            CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("de-DE");
            string id = "export_" + Guid.NewGuid().ToString("N");
            var data = new SimulationData("test", 1, Output, id);
            data.RecordAgentEvacuation(0, 1, 10); data.RecordAgentEvacuation(1, 2, 20);
            data.RecordLLMDecision(1, 0, "volunteer", "a, \"quote\"\nnext", "mock", "request_cap");
            data.SetSimulationStats(2, 20); data.SetTermination("completed"); data.ExportData();
            var row = File.ReadAllLines(Directory.GetFiles(Output, id + "*_global.csv").Single())[1].Split(',');
            Near(double.Parse(row[4], CultureInfo.InvariantCulture), 15, "exported mean");
            Near(double.Parse(row[7], CultureInfo.InvariantCulture), 5, "exported population SD");
            Check(row.Length == 13, "invariant numeric CSV culture");
            Check(SimulationData.Csv("a\"b") == "\"a\"\"b\"", "RFC4180 quote escaping");
            var empty = new SimulationData("test", 2, Output, id); empty.SetTermination("timeout"); empty.ExportData();
            Check(Directory.GetFiles(Output, id + "_run002*_global.csv").Length == 1, "zero-evacuation export exists");
        }
        finally { CultureInfo.CurrentCulture = culture; }
    }
    private static object Invoke(object obj, string name, params object[] args) => obj.GetType().GetMethod(name, Private).Invoke(obj, args);
    public static void Drain(IEnumerator routine)
    {
        while (routine.MoveNext()) if (routine.Current is IEnumerator nested) Drain(nested);
    }
    public static SimulationManager CreateManager(string output)
    {
        var manager = New("ValidationManager").AddComponent<SimulationManager>(); manager.enabled = false;
        manager.recordExperimentsAutomatically=false;
        manager.obstacleHandlingMode = ObstacleHandlingMode.LegacyClearance;
        manager.world = World(11); manager.agentPrefab = New("ValidationPrefab"); manager.agentPrefab.AddComponent<PedestrianAgent>();
        manager.agentCount = 1; manager.agentSpawnAreaSize = new Vector2Int(5, 5);
        manager.volunteerDecisionMode = SimulationManager.VolunteerDecisionMode.NoVolunteers;
        manager.movementStrategy = PedestrianAgent.MovementStrategy.Static;
        manager.researchScenario = ResearchScenario.OpenRoom;manager.exitCount=1; manager.debugLLMDecisionFlow = false;
        manager.researchOutputFolder = output;
        return manager;
    }
    public static void Begin(SimulationManager manager, int run = 1) { Invoke(manager, "StartSingleRun", run); }
    public static void Step(SimulationManager manager) { Drain((IEnumerator)Invoke(manager, "SimulationStepCoroutine")); }
    private static SimulationData Data(SimulationManager manager) => (SimulationData)typeof(SimulationManager).GetField("simulationData", Private).GetValue(manager);
    private static void SimulationLifecycle()
    {
        var manager = CreateManager(Output); manager.kStatic = 1000; Begin(manager);
        manager.GetAllAgents()[0].Init(manager.world, new Vector2Int(5, 1)); Step(manager);
        Check(!manager.IsSimulationRunning(), "single exit completes");
        Check(Data(manager).EvacuationRecordCount == 1, "final evacuee recorded in same step");
        Check(manager.GetAllAgents()[0].evacuationStep == 1, "evacuation timestamp not delayed");
        manager.researchScenario = ResearchScenario.SingleBlockedExit; manager.obstacleCount = 3;
        manager.maxSimulationSteps = 1; Begin(manager, 2); Step(manager);
        Check(!manager.IsSimulationRunning(), "timeout ends run");
        Check(Data(manager).EvacuationRecordCount == 0, "batch starts with independent records");
        manager.volunteerDecisionMode = SimulationManager.VolunteerDecisionMode.LLM; manager.obstacleVisibilityRange = 20;
        manager.allowMockFallback = false; manager.openAIKey = ""; Begin(manager, 3); Step(manager);
        Check(!manager.IsSimulationRunning(), "strict LLM missing key invalidates run");
        manager.volunteerDecisionMode = SimulationManager.VolunteerDecisionMode.OriginalGameTheory;
        manager.maxSimulationSteps = 50; manager.obstacleRemovalWorkSteps = 3;
        Begin(manager, 4); manager.GetAllAgents()[0].Init(manager.world, new Vector2Int(5, 2));
        Step(manager); Check(manager.world.cells[5, 1] == CellType.Obstacle, "clearance requires work step 1");
        Step(manager); Check(manager.world.cells[5, 1] == CellType.Obstacle, "clearance requires work step 2");
        Step(manager); Check(manager.world.cells[5, 1] == CellType.Empty, "clearance completes after configured work");
        manager.ResetSimulation();
    }
    private static void Reproducibility()
    {
        var manager = CreateManager(Output); manager.agentCount = 8; manager.researchScenario = ResearchScenario.RandomRoom;
        manager.obstacleCount = 5; Begin(manager);
        var positions = manager.GetAllAgents().Select(a => a.gridPos).ToArray();
        var obstacles = manager.world.GetObstaclePositions().ToArray();
        Begin(manager);
        Check(positions.SequenceEqual(manager.GetAllAgents().Select(a => a.gridPos)), "seed reproduces initial crowd");
        Check(obstacles.SequenceEqual(manager.world.GetObstaclePositions()), "seed reproduces obstacles");
        manager.ResetSimulation();
    }

    private static void VolunteerActivationRegression()
    {
        var manager = CreateManager(Output);
        manager.researchScenario = ResearchScenario.SingleBlockedExit;
        manager.volunteerDecisionMode = SimulationManager.VolunteerDecisionMode.OriginalGameTheory;
        manager.obstacleCount = 3; manager.obstacleVisibilityRange = 20;
        manager.obstacleActionRange = 2; // Legacy setting must not activate a nonadjacent paper volunteer.
        manager.volunteerSelectionInterval = 6; // Paper Stage 2 must still run each step.
        manager.maxSimulationSteps = 200; manager.agentCount = 2;
        Begin(manager);
        var agents = manager.GetAllAgents();
        agents[0].Init(manager.world, new Vector2Int(5, 7));
        agents[1].Init(manager.world, new Vector2Int(5, 2));
        Step(manager);
        Check(!agents[0].IsActiveVolunteer(), "remote candidate must not reserve obstacle");
        Check(agents[1].IsActiveVolunteer(), "adjacent candidate activates instead of remote candidate");
        Check(manager.EffectiveVolunteerActionRange == 1, "paper volunteer action requires adjacency");
        manager.ResetSimulation();

        manager.agentCount = 1; Begin(manager, 2);
        var lone = manager.GetAllAgents()[0]; lone.Init(manager.world, new Vector2Int(5, 3));
        Step(manager); Check(lone.IsPotentialVolunteer(), "candidate approaches before activation");
        Step(manager); Check(lone.IsActiveVolunteer(), "adjacent candidate activates off legacy interval");
        manager.ResetSimulation();

        manager.volunteerDecisionMode = SimulationManager.VolunteerDecisionMode.NoVolunteers;
        manager.maxSimulationSteps = 0; Begin(manager, 3); manager.currentStep = 200;
        Step(manager); Check(manager.IsSimulationRunning(), "no watchdog means no arbitrary 200-step termination");
        Check(manager.GetEvacuatedCount() == 0, "unreachable negative control is not forced to evacuate");
        manager.ResetSimulation();
    }

    private static void ReferenceRoomCompletion()
    {
        var manager = CreateManager(Output);
        manager.world.width = manager.world.height = 30;
        manager.agentCount = 50; manager.agentSpawnAreaSize = new Vector2Int(15, 15);
        manager.researchScenario = ResearchScenario.RandomRoom; manager.obstacleCount = 40;
        manager.volunteerDecisionMode = SimulationManager.VolunteerDecisionMode.OriginalGameTheory;
        manager.conflictStrategy = YielderGame.Strategy.PaperYielder;
        manager.movementStrategy = PedestrianAgent.MovementStrategy.Combined;
        manager.kStatic = 3; manager.kDynamic = 1; manager.kAnticipation = 5;
        manager.volunteerCost = 0.005f; manager.failureCost = 0.5f; manager.unwillingnessOmega = 5;
        manager.obstacleVisibilityRange = 20; manager.maxSimulationSteps = 200;
        for (int run = 1; run <= 30; run++)
        {
            Begin(manager, run);
            while (manager.IsSimulationRunning()) Step(manager);
            Check(manager.GetEvacuatedCount() == 50,
                $"four-exit 40-obstacle full evacuation: seed {manager.baseSeed + run - 1}");
        }
        manager.ResetSimulation();
    }
}
