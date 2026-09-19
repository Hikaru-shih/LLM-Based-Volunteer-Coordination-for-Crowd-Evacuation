using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using Decision;

public class SimulationManager : MonoBehaviour
{
    private const string BatchRunCountKey = "sim.batchRunCount";
    private const string GridWidthKey = "sim.gridWidth";
    private const string GridHeightKey = "sim.gridHeight";
    private const string AgentCountKey = "sim.agentCount";
    private const string AgentSpawnAreaWidthKey = "sim.agentSpawnAreaWidth";
    private const string AgentSpawnAreaHeightKey = "sim.agentSpawnAreaHeight";
    private const string ObstacleCountKey = "sim.obstacleCount";
    private const string VolunteerCountKey = "sim.volunteerCount";
    private const string StepIntervalKey = "sim.stepInterval";
    private const string VolunteerDecisionModeKey = "sim.volunteerDecisionMode";
    private const string VolunteerSelectionIntervalKey = "sim.volunteerSelectionInterval";
    private const string ObstacleVisibilityRangeKey = "sim.obstacleVisibilityRange";
    private const string ObstacleActionRangeKey = "sim.obstacleActionRange";
    private const string MaxLlmRequestsPerStepKey = "sim.maxLlmRequestsPerStep";
    private const string VolunteerCostKey = "sim.volunteerCost";
    private const string FailureCostKey = "sim.failureCost";
    private const string UnwillingnessOmegaKey = "sim.unwillingnessOmega";
    private const string KStaticKey = "sim.kStatic";
    private const string KDynamicKey = "sim.kDynamic";
    private const string KAnticipationKey = "sim.kAnticipation";
    private const string TemperatureKey = "sim.temperature";
    private const string MovementStrategyKey = "sim.movementStrategy";
    private const string ConflictStrategyKey = "sim.conflictStrategy";
    private const string OpenAiModelKey = "sim.openAIModel";

    private const string DebugLlmDecisionFlowKey = "sim.debugLLMDecisionFlow";
    private const string NinetyPercentFallbackStepsKey = "sim.ninetyPercentFallbackSteps";

    public enum VolunteerDecisionMode
    {
        OriginalGameTheory,
        LLM
    }

    private bool isPaused = false;
    [Header("Batch Run")]
    [Tooltip("How many times to run the simulation in batch mode (set in Inspector)")]
    public int batchRunCount = 1;
    [Header("Environment Settings")]
    public GridWorld world;
    
    [Header("Simulation Settings")]
    public int agentCount = 50;
    public float stepInterval = 0.3f;
    public Vector2Int agentSpawnAreaSize = new Vector2Int(15, 15);
    
    [Header("Agent Prefab")]
    public GameObject agentPrefab;
    
    [Header("Conflict Resolution")]
    public YielderGame.Strategy conflictStrategy = YielderGame.Strategy.Probabilistic;
    
    [Header("Simulation Settings")]
    public int volunteerCount = 5;
    public int obstacleCount = 40;
    public PedestrianAgent.MovementStrategy movementStrategy = PedestrianAgent.MovementStrategy.Combined;

    [Header("Dynamic Volunteer Model")]
    public VolunteerDecisionMode volunteerDecisionMode = VolunteerDecisionMode.OriginalGameTheory;
    public int volunteerSelectionInterval = 6;
    public int obstacleVisibilityRange = 5;
    public int obstacleActionRange = 2;
    public int maxLLMRequestsPerStep = 3;
    public float volunteerCost = 1.0f;
    public float failureCost = 2.0f;
    public float unwillingnessOmega = 1.0f;

    [Header("Floor Field Weights")]
    public float kStatic = 1.0f;
    public float kDynamic = 1.0f;
    public float kAnticipation = 1.0f;
    public float movementTemperature = 1.0f;

    [Header("OpenAI LLM")]
    [HideInInspector] public bool useLLMVolunteerDecision = false;
    [System.NonSerialized] public string openAIKey = "";
    public string openAIModel = "gpt-4.1";

    [Header("LLM Debug")]
    public bool debugLLMDecisionFlow = true;

    private AgentManager agentManager;
    private YielderGame yielderGame;
    private VolunteerDilemma volunteerDilemma;
    private LLMDecisionPolicy llmDecisionPolicy;
    private bool isStepInProgress = false;
    private IVolunteerDecisionStrategy volunteerDecisionStrategy;
    private SimulationData simulationData;
    private StaticFloorField floorField;
    private DynamicFloorField dynamicFloorField;
    private AnticipationFloorField anticipationFloorField;
    private AStarPathfinding pathfinder;
    private float timeSinceLastStep = 0f;
    public int currentStep = 0;
    private bool simulationRunning = false;
    
    private int evacuatedCount = 0;
    private int totalEvacuated = 0;
    private float elapsedTime = 0f;
    private bool llmKeyWarningLogged = false;
    private int llmApiDecisionCallsThisRun = 0;
    private int llmMockFallbackCallsThisRun = 0;
    private int llmRequestsThisStep = 0;
    private int stepsToNinetyPercent = -1;
    private float timeToNinetyPercent = -1f;

    [Header("Summary Metrics")]
    [Tooltip("Fallback steps used when a run never reaches 90% evacuation")]
    public int ninetyPercentFallbackSteps = 150;

    [Header("In-Game UI Controller")]
    public GameObject inGameUIControllerObj;
    private UI.InGameUIController inGameUIController;

    void Awake()
    {
        if (inGameUIControllerObj != null)
            inGameUIController = inGameUIControllerObj.GetComponent<UI.InGameUIController>();
    }

    void Start()
    {
        if (!world)
        {
            Debug.LogError("GridWorld not assigned to SimulationManager!");
            return;
        }

        LoadSettingsFromMainMenu();

        if (batchRunCount > 1)
        {
            StartCoroutine(BatchRunCoroutine());
        }
        else
        {
            StartSingleRun();
        }
    }

    private void LoadSettingsFromMainMenu()
    {
        if (world == null)
            return;

        if (PlayerPrefs.HasKey(BatchRunCountKey))
            batchRunCount = Mathf.Max(1, PlayerPrefs.GetInt(BatchRunCountKey));

        if (PlayerPrefs.HasKey(GridWidthKey))
            world.width = PlayerPrefs.GetInt(GridWidthKey);

        if (PlayerPrefs.HasKey(GridHeightKey))
            world.height = PlayerPrefs.GetInt(GridHeightKey);

        if (PlayerPrefs.HasKey(AgentCountKey))
            agentCount = PlayerPrefs.GetInt(AgentCountKey);

        if (PlayerPrefs.HasKey(AgentSpawnAreaWidthKey))
            agentSpawnAreaSize.x = Mathf.Max(1, PlayerPrefs.GetInt(AgentSpawnAreaWidthKey));

        if (PlayerPrefs.HasKey(AgentSpawnAreaHeightKey))
            agentSpawnAreaSize.y = Mathf.Max(1, PlayerPrefs.GetInt(AgentSpawnAreaHeightKey));

        if (PlayerPrefs.HasKey(ObstacleCountKey))
            obstacleCount = PlayerPrefs.GetInt(ObstacleCountKey);

        if (PlayerPrefs.HasKey(VolunteerCountKey))
            volunteerCount = PlayerPrefs.GetInt(VolunteerCountKey);

        if (PlayerPrefs.HasKey(StepIntervalKey))
            stepInterval = PlayerPrefs.GetFloat(StepIntervalKey);

        if (PlayerPrefs.HasKey(VolunteerDecisionModeKey))
            volunteerDecisionMode = (VolunteerDecisionMode)PlayerPrefs.GetInt(VolunteerDecisionModeKey);

        if (PlayerPrefs.HasKey(VolunteerSelectionIntervalKey))
            volunteerSelectionInterval = Mathf.Max(1, PlayerPrefs.GetInt(VolunteerSelectionIntervalKey));

        if (PlayerPrefs.HasKey(ObstacleVisibilityRangeKey))
            obstacleVisibilityRange = Mathf.Max(1, PlayerPrefs.GetInt(ObstacleVisibilityRangeKey));

        if (PlayerPrefs.HasKey(ObstacleActionRangeKey))
            obstacleActionRange = Mathf.Max(1, PlayerPrefs.GetInt(ObstacleActionRangeKey));

        if (PlayerPrefs.HasKey(MaxLlmRequestsPerStepKey))
            maxLLMRequestsPerStep = Mathf.Max(1, PlayerPrefs.GetInt(MaxLlmRequestsPerStepKey));

        if (PlayerPrefs.HasKey(VolunteerCostKey))
            volunteerCost = PlayerPrefs.GetFloat(VolunteerCostKey);

        if (PlayerPrefs.HasKey(FailureCostKey))
            failureCost = PlayerPrefs.GetFloat(FailureCostKey);

        if (PlayerPrefs.HasKey(UnwillingnessOmegaKey))
            unwillingnessOmega = PlayerPrefs.GetFloat(UnwillingnessOmegaKey);

        if (PlayerPrefs.HasKey(KStaticKey))
            kStatic = PlayerPrefs.GetFloat(KStaticKey);

        if (PlayerPrefs.HasKey(KDynamicKey))
            kDynamic = PlayerPrefs.GetFloat(KDynamicKey);

        if (PlayerPrefs.HasKey(KAnticipationKey))
            kAnticipation = PlayerPrefs.GetFloat(KAnticipationKey);

        if (PlayerPrefs.HasKey(TemperatureKey))
            movementTemperature = PlayerPrefs.GetFloat(TemperatureKey);

        if (PlayerPrefs.HasKey(MovementStrategyKey))
            movementStrategy = (PedestrianAgent.MovementStrategy)PlayerPrefs.GetInt(MovementStrategyKey);

        if (PlayerPrefs.HasKey(ConflictStrategyKey))
            conflictStrategy = (YielderGame.Strategy)PlayerPrefs.GetInt(ConflictStrategyKey);

        if (PlayerPrefs.HasKey(OpenAiModelKey))
            openAIModel = PlayerPrefs.GetString(OpenAiModelKey);

        openAIKey = LocalOpenAIKey.Load();

        if (PlayerPrefs.HasKey(DebugLlmDecisionFlowKey))
            debugLLMDecisionFlow = PlayerPrefs.GetInt(DebugLlmDecisionFlowKey) == 1;

        if (PlayerPrefs.HasKey(NinetyPercentFallbackStepsKey))
            ninetyPercentFallbackSteps = Mathf.Max(1, PlayerPrefs.GetInt(NinetyPercentFallbackStepsKey));

        useLLMVolunteerDecision = (volunteerDecisionMode == VolunteerDecisionMode.LLM);
    }

    [ContextMenu("Sync Current Values To MainMenu Settings")]
    private void SyncCurrentValuesToMainMenuSettings()
    {
        if (world != null)
        {
            PlayerPrefs.SetInt(GridWidthKey, world.width);
            PlayerPrefs.SetInt(GridHeightKey, world.height);
        }

        PlayerPrefs.SetInt(BatchRunCountKey, Mathf.Max(1, batchRunCount));
        PlayerPrefs.SetInt(AgentCountKey, Mathf.Max(1, agentCount));
        PlayerPrefs.SetInt(AgentSpawnAreaWidthKey, Mathf.Max(1, agentSpawnAreaSize.x));
        PlayerPrefs.SetInt(AgentSpawnAreaHeightKey, Mathf.Max(1, agentSpawnAreaSize.y));
        PlayerPrefs.SetInt(ObstacleCountKey, Mathf.Max(0, obstacleCount));
        PlayerPrefs.SetInt(VolunteerCountKey, Mathf.Max(0, volunteerCount));
        PlayerPrefs.SetFloat(StepIntervalKey, Mathf.Max(0.01f, stepInterval));

        PlayerPrefs.SetInt(VolunteerDecisionModeKey, (int)volunteerDecisionMode);
        PlayerPrefs.SetInt(VolunteerSelectionIntervalKey, Mathf.Max(1, volunteerSelectionInterval));
        PlayerPrefs.SetInt(ObstacleVisibilityRangeKey, Mathf.Max(1, obstacleVisibilityRange));
        PlayerPrefs.SetInt(ObstacleActionRangeKey, Mathf.Max(1, obstacleActionRange));
        PlayerPrefs.SetInt(MaxLlmRequestsPerStepKey, Mathf.Max(1, maxLLMRequestsPerStep));
        PlayerPrefs.SetFloat(VolunteerCostKey, volunteerCost);
        PlayerPrefs.SetFloat(FailureCostKey, failureCost);
        PlayerPrefs.SetFloat(UnwillingnessOmegaKey, unwillingnessOmega);

        PlayerPrefs.SetFloat(KStaticKey, kStatic);
        PlayerPrefs.SetFloat(KDynamicKey, kDynamic);
        PlayerPrefs.SetFloat(KAnticipationKey, kAnticipation);
        PlayerPrefs.SetFloat(TemperatureKey, movementTemperature);
        PlayerPrefs.SetInt(MovementStrategyKey, (int)movementStrategy);
        PlayerPrefs.SetInt(ConflictStrategyKey, (int)conflictStrategy);

        PlayerPrefs.SetString(OpenAiModelKey, openAIModel ?? "");

        PlayerPrefs.SetInt(DebugLlmDecisionFlowKey, debugLLMDecisionFlow ? 1 : 0);
        PlayerPrefs.SetInt(NinetyPercentFallbackStepsKey, Mathf.Max(1, ninetyPercentFallbackSteps));

        PlayerPrefs.Save();
        Debug.Log("Current SimulationManager values synced to MainMenu settings.");
    }

    private void StartSingleRun()
    {
        world.Init();
        Debug.Log("GridWorld initialized with size: " + world.width + "x" + world.height);
        world.SetRandomObstacles(obstacleCount);
        floorField = new StaticFloorField(world);
        dynamicFloorField = new DynamicFloorField(world);
        anticipationFloorField = new AnticipationFloorField(world);
        pathfinder = new AStarPathfinding(world);
        agentManager = new AgentManager(world, agentPrefab);
        yielderGame = new YielderGame(conflictStrategy);
        volunteerDilemma = new VolunteerDilemma(agentManager, world, floorField);
        llmDecisionPolicy = new LLMDecisionPolicy(openAIKey, openAIModel);
        volunteerDilemma.SetLLMPolicy(llmDecisionPolicy);
        volunteerDilemma.decisionMode = useLLMVolunteerDecision ? VolunteerDilemma.DecisionMode.LLM : VolunteerDilemma.DecisionMode.Probabilistic;
        ConfigureVolunteerDecisionStrategy();
        // simulationData 只在 batch 開始時 new 一次
        if (simulationData == null)
        {
            simulationData = new SimulationData(conflictStrategy.ToString());
            simulationData.SetSimulationParameters(kStatic, kDynamic, kAnticipation, movementTemperature, agentCount, obstacleCount);
        }
        SpawnAgents();
        simulationRunning = true;
        currentStep = 0;
        timeSinceLastStep = 0f;
        elapsedTime = 0f;
        llmApiDecisionCallsThisRun = 0;
        llmMockFallbackCallsThisRun = 0;
        stepsToNinetyPercent = -1;
        timeToNinetyPercent = -1f;
        Debug.Log("Simulation initialized with " + agentCount + " agents");
        if (debugLLMDecisionFlow)
        {
            Debug.Log($"[LLM-DEBUG] Run config | mode={volunteerDecisionMode}, useLLMVolunteerDecision={useLLMVolunteerDecision}, hasKey={!string.IsNullOrEmpty(openAIKey)}, visibilityRange={obstacleVisibilityRange}, actionRange={obstacleActionRange}");
        }
    }

    private void ConfigureVolunteerDecisionStrategy()
    {
        // Keep legacy flag synchronized with the new enum mode to avoid split behavior.
        useLLMVolunteerDecision = (volunteerDecisionMode == VolunteerDecisionMode.LLM);

        if (volunteerDecisionMode == VolunteerDecisionMode.LLM)
            volunteerDecisionStrategy = new MockLLMVolunteerStrategy();
        else
            volunteerDecisionStrategy = new OriginalGameTheoryVolunteerStrategy();

        if (volunteerDilemma != null)
        {
            volunteerDilemma.decisionMode = useLLMVolunteerDecision
                ? VolunteerDilemma.DecisionMode.LLM
                : VolunteerDilemma.DecisionMode.Probabilistic;
        }
    }

    private IEnumerator BatchRunCoroutine()
    {
        // 只 new 一次 SimulationData
        simulationData = new SimulationData(conflictStrategy.ToString());
        simulationData.SetSimulationParameters(kStatic, kDynamic, kAnticipation, movementTemperature, agentCount, obstacleCount);

        // 用來統計每輪達到 90% 撤離的步數和時間
        List<int> stepsList = new List<int>();
        List<float> timeList = new List<float>();
        List<bool> reachedNinetyList = new List<bool>();

        for (int i = 0; i < batchRunCount; i++)
        {
            if (inGameUIController != null)
                inGameUIController.SetRoundText(i + 1, batchRunCount);
            simulationRunning = false; // 確保每輪開始前重置
            StartSingleRun();
            // 等待本輪模擬結束
            while (simulationRunning)
                yield return null;
            // 每輪結束後記錄步數和時間
            bool reachedNinety = stepsToNinetyPercent >= 0;
            reachedNinetyList.Add(reachedNinety);

            int steps90 = reachedNinety ? stepsToNinetyPercent : ninetyPercentFallbackSteps;
            float time90 = reachedNinety ? timeToNinetyPercent : ninetyPercentFallbackSteps * stepInterval;
            stepsList.Add(steps90);
            timeList.Add(time90);
            yield return new WaitForSeconds(0.5f); // 可調整每輪間隔
        }
        // batch 結束時一次性輸出所有資料
        if (simulationData != null)
            simulationData.ExportData();
        // 輸出 batch summary
        ExportBatchSummary(stepsList, timeList, reachedNinetyList);
        if (inGameUIController != null)
            inGameUIController.SetRoundText(0, batchRunCount); // 清空或顯示完成
        Debug.Log($"Batch run {batchRunCount} completed.");
    }

    // 輸出 batch summary csv
    private void ExportBatchSummary(List<int> stepsList, List<float> timeList, List<bool> reachedNinetyList)
    {
        if (stepsList.Count == 0) return;
        string dataFolderPath = System.IO.Path.Combine(Application.dataPath, "data");
        if (!System.IO.Directory.Exists(dataFolderPath))
            System.IO.Directory.CreateDirectory(dataFolderPath);
        string timestamp = System.DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
        string fileName = $"{timestamp}_batch_summary.csv";
        string filePath = System.IO.Path.Combine(dataFolderPath, fileName);
        float avgSteps = 0f, avgTime = 0f, stdSteps = 0f, stdTime = 0f;
        int minSteps = int.MaxValue, maxSteps = int.MinValue;
        float minTime = float.MaxValue, maxTime = float.MinValue;
        foreach (var s in stepsList) { avgSteps += s; if (s < minSteps) minSteps = s; if (s > maxSteps) maxSteps = s; }
        foreach (var t in timeList) { avgTime += t; if (t < minTime) minTime = t; if (t > maxTime) maxTime = t; }
        avgSteps /= stepsList.Count;
        avgTime /= timeList.Count;
        foreach (var s in stepsList) stdSteps += (s - avgSteps) * (s - avgSteps);
        foreach (var t in timeList) stdTime += (t - avgTime) * (t - avgTime);
        stdSteps = Mathf.Sqrt(stdSteps / stepsList.Count);
        stdTime = Mathf.Sqrt(stdTime / timeList.Count);
        int successRuns90 = reachedNinetyList.FindAll(x => x).Count;
        int failedRuns = reachedNinetyList.Count - successRuns90;
        using (var writer = new System.IO.StreamWriter(filePath))
        {
            writer.WriteLine($"Strategy,{conflictStrategy}");
            writer.WriteLine($"useLLMVolunteerDecision,{useLLMVolunteerDecision}");
            writer.WriteLine($"volunteerCount,{volunteerCount}");
            writer.WriteLine($"obstacleCount,{obstacleCount}");
            writer.WriteLine($"agentCount,{agentCount}");
            writer.WriteLine($"stepInterval,{stepInterval}");
            writer.WriteLine($"mapWidth,{world?.width ?? -1}");
            writer.WriteLine($"mapHeight,{world?.height ?? -1}");
            writer.WriteLine($"batchRunCount,{batchRunCount}");
            writer.WriteLine($"kStatic,{kStatic}");
            writer.WriteLine($"kDynamic,{kDynamic}");
            writer.WriteLine($"kAnticipation,{kAnticipation}");
            writer.WriteLine($"movementTemperature,{movementTemperature}");
            writer.WriteLine($"summaryMetric,90pct_evacuated");
            writer.WriteLine($"ninetyPercentFallbackSteps,{ninetyPercentFallbackSteps}");
            writer.WriteLine();
            writer.WriteLine("BatchSize,Strategy,AvgSteps,StdSteps,MinSteps,MaxSteps,AvgTime,StdTime,MinTime,MaxTime,Reached90PctAllRuns,SuccessRuns90Pct,FailedRuns");
            writer.WriteLine($"{stepsList.Count},{conflictStrategy},{avgSteps:F2},{stdSteps:F2},{minSteps},{maxSteps},{avgTime:F2},{stdTime:F2},{minTime:F2},{maxTime:F2},{(failedRuns == 0 ? "true" : "false")},{successRuns90},{failedRuns}");
        }
        Debug.Log($"Batch summary exported to {fileName}");
    }

    void OnValidate()
    {
        ConfigureVolunteerDecisionStrategy();

        if (yielderGame != null)
        {
            yielderGame.SetStrategy(conflictStrategy);
        }

        if (volunteerDilemma != null)
        {
            volunteerDilemma.decisionMode = (volunteerDecisionMode == VolunteerDecisionMode.LLM)
                ? VolunteerDilemma.DecisionMode.LLM
                : VolunteerDilemma.DecisionMode.Probabilistic;
            if (llmDecisionPolicy != null)
            {
                llmDecisionPolicy = new LLMDecisionPolicy(openAIKey, openAIModel);
                volunteerDilemma.SetLLMPolicy(llmDecisionPolicy);
            }
        }
    }

    void Update()
    {
        if (world == null)
            return;

        if (Input.GetKeyDown(KeyCode.Space))
        {
            TogglePause();
        }

        if (!simulationRunning || isStepInProgress || isPaused)
            return;

        if (yielderGame != null)
        {
            yielderGame.SetStrategy(conflictStrategy);
        }

        timeSinceLastStep += Time.deltaTime;
        elapsedTime += Time.deltaTime;

        if (timeSinceLastStep >= stepInterval)
        {
            timeSinceLastStep -= stepInterval;
            StartCoroutine(SimulationStepCoroutine());
        }

        CheckSimulationComplete();
    }

    private void SpawnAgents()
    {
        if (agentManager == null)
        {
            Debug.LogError("AgentManager not initialized!");
            return;
        }

        int startX = (world.width - agentSpawnAreaSize.x) / 2;
        int startY = (world.height - agentSpawnAreaSize.y) / 2;
        int endX = startX + agentSpawnAreaSize.x;
        int endY = startY + agentSpawnAreaSize.y;

        HashSet<Vector2Int> occupiedPositions = new HashSet<Vector2Int>();
        for (int i = 0; i < agentCount; i++)
        {
            int randomX = Random.Range(startX, endX);
            int randomY = Random.Range(startY, endY);
            Vector2Int spawnPos = new Vector2Int(randomX, randomY);

            if (!world.IsWalkable(randomX, randomY) || occupiedPositions.Contains(spawnPos) || !HasWalkableNeighbor(spawnPos))
            {
                spawnPos = FindNearbyWalkablePosition(randomX, randomY, occupiedPositions);
                if (spawnPos == new Vector2Int(-1, -1))
                {
                    Debug.LogWarning("Could not find valid spawn position for agent " + i);
                    i--;
                    continue;
                }
            }

            PedestrianAgent agent = agentManager.SpawnAgent(spawnPos);
            if (agent != null)
            {
                occupiedPositions.Add(spawnPos);
                agent.SetVolunteerState(PedestrianAgent.VolunteerState.None);
                agent.SetFloorField(floorField);
                agent.SetDynamicField(dynamicFloorField);
                agent.SetAnticipationField(anticipationFloorField);
                agent.SetPathfinder(pathfinder);
                agent.SetMovementStrategy(movementStrategy);
                agent.SetMovementCoefficients(kStatic, kDynamic, kAnticipation, movementTemperature);
                agent.SetVolunteerActionRange(obstacleActionRange);
            }
        }

        Debug.Log("Spawned " + agentManager.GetAgentCount() + " agents");
    }

    private Vector2Int FindNearbyWalkablePosition(int x, int y, HashSet<Vector2Int> occupied)
    {
        int searchRadius = 5;
        for (int dx = -searchRadius; dx <= searchRadius; dx++)
        {
            for (int dy = -searchRadius; dy <= searchRadius; dy++)
            {
                int newX = x + dx;
                int newY = y + dy;
                Vector2Int candidate = new Vector2Int(newX, newY);
                if (world.IsWalkable(newX, newY) && !occupied.Contains(candidate) && HasWalkableNeighbor(candidate))
                {
                    return candidate;
                }
            }
        }
        return new Vector2Int(-1, -1);
    }

    private bool HasWalkableNeighbor(Vector2Int pos)
    {
        Vector2Int[] dirs = new Vector2Int[]
        {
            new Vector2Int(0, -1),
            new Vector2Int(0, 1),
            new Vector2Int(-1, 0),
            new Vector2Int(1, 0)
        };

        for (int i = 0; i < dirs.Length; i++)
        {
            Vector2Int n = pos + dirs[i];
            if (world.IsWalkable(n.x, n.y) || (world.InBounds(n.x, n.y) && world.cells[n.x, n.y] == CellType.Exit))
            {
                return true;
            }
        }

        return false;
    }

    private IEnumerator SimulationStepCoroutine()
    {
        isStepInProgress = true;
        yield return ExecuteSimulationStep();
        isStepInProgress = false;
    }

    public void SimulationStep()
    {
        if (!isStepInProgress)
        {
            StartCoroutine(SimulationStepCoroutine());
        }
    }

    private IEnumerator ExecuteSimulationStep()
    {
        currentStep++;
        llmRequestsThisStep = 0;

        if (agentManager == null || agentManager.GetAgentCount() == 0)
        {
            Debug.Log("No agents to simulate");
            yield break;
        }

        yield return UpdateDynamicVolunteerStatesCoroutine();

        foreach (PedestrianAgent agent in agentManager.GetAgents())
        {
            if (!agent.IsEvacuated())
            {
                agent.ProposeMove();
            }
        }

        int conflictCount = ResolveMovementConflicts();

        int volunteerActionsThisStep = 0;
        yield return ExecuteVolunteerActionsCoroutine(value => volunteerActionsThisStep = value);

        foreach (PedestrianAgent agent in agentManager.GetAgents())
        {
            if (!agent.IsEvacuated())
            {
                agent.CommitMove();
            }
            else if (agent.evacuationStep == -1)
            {
                agent.evacuationStep = currentStep;
                simulationData.RecordAgentEvacuation(agent.gameObject.GetInstanceID(), currentStep, elapsedTime);
            }
        }

        evacuatedCount = agentManager.GetEvacuatedCount();

        int totalAgents = agentManager.GetAgentCount();
        int targetNinety = Mathf.CeilToInt(totalAgents * 0.90f);
        if (stepsToNinetyPercent < 0 && evacuatedCount >= targetNinety)
        {
            stepsToNinetyPercent = currentStep;
            timeToNinetyPercent = elapsedTime;
        }

        dynamicFloorField?.UpdateField(agentManager.GetAgents());
        anticipationFloorField?.UpdateField(agentManager.GetAgentsByRole(PedestrianAgent.Role.Volunteer));

        float avgDFF = CalculateAverageDFFValue();
        float avgAFF = CalculateAverageAFFValue();
        int obstaclesRemaining = world.GetObstaclePositions().Count;
        int agentsRemaining = agentManager.GetAgentCount() - agentManager.GetEvacuatedCount();

        simulationData.RecordStepDiagnostics(currentStep, agentsRemaining, conflictCount, volunteerActionsThisStep, 
                                             obstaclesRemaining, avgDFF, avgAFF);

        if (currentStep % 10 == 0)
        {
            Debug.Log("Step: " + currentStep + " | Evacuated: " + evacuatedCount + " / " + agentManager.GetAgentCount());
        }
    }

    private float CalculateAverageDFFValue()
    {
        if (dynamicFloorField == null)
            return 0f;

        float sum = 0f;
        int count = 0;

        foreach (PedestrianAgent agent in agentManager.GetAgents())
        {
            if (!agent.IsEvacuated())
            {
                sum += dynamicFloorField.GetValue(agent.GetGridPos());
                count++;
            }
        }

        return count > 0 ? sum / count : 0f;
    }

    private float CalculateAverageAFFValue()
    {
        if (anticipationFloorField == null)
            return 0f;

        float sum = 0f;
        int count = 0;

        foreach (PedestrianAgent agent in agentManager.GetAgents())
        {
            if (!agent.IsEvacuated())
            {
                sum += anticipationFloorField.GetValue(agent.GetGridPos());
                count++;
            }
        }

        return count > 0 ? sum / count : 0f;
    }

    private int ResolveMovementConflicts()
    {
        List<PedestrianAgent> agents = agentManager.GetAgents();
        
        Dictionary<Vector2Int, List<PedestrianAgent>> targetPositions = 
            new Dictionary<Vector2Int, List<PedestrianAgent>>();

        foreach (PedestrianAgent agent in agents)
        {
            if (agent.IsEvacuated())
                continue;

            Vector2Int desiredPos = agent.GetDesiredPos();
            
            if (!targetPositions.ContainsKey(desiredPos))
            {
                targetPositions[desiredPos] = new List<PedestrianAgent>();
            }
            targetPositions[desiredPos].Add(agent);
        }

        int conflictCount = 0;
        foreach (var entry in targetPositions)
        {
            Vector2Int targetPos = entry.Key;
            List<PedestrianAgent> agentsAtTarget = entry.Value;

            if (agentsAtTarget.Count > 1)
            {
                conflictCount++;

                // If someone is already standing on targetPos and chooses to stay,
                // keep that occupant to avoid two agents ending in the same cell.
                PedestrianAgent winner = null;
                for (int i = 0; i < agentsAtTarget.Count; i++)
                {
                    PedestrianAgent candidate = agentsAtTarget[i];
                    if (candidate.GetGridPos() == targetPos && candidate.GetDesiredPos() == targetPos)
                    {
                        winner = candidate;
                        break;
                    }
                }

                if (winner == null)
                {
                    winner = yielderGame.ResolveConflict(agentsAtTarget);
                }
                
                for (int i = 0; i < agentsAtTarget.Count; i++)
                {
                    PedestrianAgent agent = agentsAtTarget[i];
                    if (agent != winner)
                    {
                        agent.desiredPos = agent.GetGridPos();
                    }
                }
            }
        }

        if (currentStep % 20 == 0 && conflictCount > 0)
        {
            Debug.Log($"Step {currentStep}: {conflictCount} conflict(s) detected and resolved");
        }

        return conflictCount;
    }

    private IEnumerator ExecuteVolunteerActionsCoroutine(System.Action<int> callback)
    {
        List<PedestrianAgent> volunteers = GetAgentsByVolunteerState(PedestrianAgent.VolunteerState.ActiveVolunteer);
        int volunteerActionCount = 0;
        HashSet<int> processedObstacles = new HashSet<int>();
        List<Vector2Int> currentObstacles = world.GetObstaclePositions();
        Dictionary<int, Vector2Int> obstacleMap = BuildObstacleIdMap(currentObstacles);

        foreach (PedestrianAgent volunteer in volunteers)
        {
            if (volunteer.IsEvacuated())
                continue;

            if (!volunteer.HasAssignedObstacle())
            {
                volunteer.SetVolunteerState(PedestrianAgent.VolunteerState.None);
                continue;
            }

            int obstacleId = volunteer.GetAssignedObstacleId();
            if (!obstacleMap.ContainsKey(obstacleId))
            {
                volunteer.SetVolunteerState(PedestrianAgent.VolunteerState.None);
                continue;
            }

            Vector2Int targetObstacle = obstacleMap[obstacleId];
            int dist = Mathf.Abs(volunteer.GetGridPos().x - targetObstacle.x) + Mathf.Abs(volunteer.GetGridPos().y - targetObstacle.y);

            if (dist <= obstacleActionRange)
            {
                if (!processedObstacles.Contains(obstacleId))
                {
                    processedObstacles.Add(obstacleId);
                    volunteerActionCount++;
                    volunteerDilemma.ExecuteVolunteerActionAtObstacle(volunteer, VolunteerDilemma.CooperationLevel.Cooperative, targetObstacle);
                    if (volunteerDecisionMode == VolunteerDecisionMode.LLM)
                    {
                        simulationData.RecordLLMDecision(currentStep, volunteer.gameObject.GetInstanceID(), "volunteer", "assigned volunteer cleared obstacle");
                    }
                }

                volunteer.SetVolunteerState(PedestrianAgent.VolunteerState.None);
            }
        }

        callback?.Invoke(volunteerActionCount);
        yield break;
    }

    private IEnumerator UpdateDynamicVolunteerStatesCoroutine()
    {
        List<PedestrianAgent> allAgents = agentManager.GetAgents();
        List<Vector2Int> obstacles = world.GetObstaclePositions();
        Dictionary<int, Vector2Int> obstacleMap = BuildObstacleIdMap(obstacles);
        int consideredAgents = 0;
        int outOfVisibilityAgents = 0;
        int noObstacleAgents = 0;

        if (obstacles.Count == 0 || volunteerDecisionStrategy == null)
        {
            foreach (PedestrianAgent agent in allAgents)
            {
                if (!agent.IsEvacuated())
                {
                    agent.SetVolunteerState(PedestrianAgent.VolunteerState.None);
                }
            }
            yield break;
        }

        if (!ShouldRunVolunteerSelectionThisStep())
        {
            CleanupInvalidVolunteerAssignments(allAgents, obstacleMap);
            yield break;
        }

        // Keep original model behavior as-is, except active volunteers are assigned
        // a concrete obstacle target so they can move directly toward it.
        if (volunteerDecisionMode == VolunteerDecisionMode.OriginalGameTheory)
        {
            HandleOriginalVolunteerStates(allAgents, obstacles, obstacleMap);
            yield break;
        }

        List<PedestrianAgent> potentialVolunteers = new List<PedestrianAgent>();

        foreach (PedestrianAgent agent in allAgents)
        {
            if (agent.IsEvacuated())
                continue;

            if (agent.IsActiveVolunteer())
            {
                if (!agent.HasAssignedObstacle() || !obstacleMap.ContainsKey(agent.GetAssignedObstacleId()))
                {
                    agent.SetVolunteerState(PedestrianAgent.VolunteerState.None);
                }
                continue;
            }

            if (agent.IsPotentialVolunteer())
            {
                if (agent.HasAssignedObstacle() && obstacleMap.ContainsKey(agent.GetAssignedObstacleId()))
                {
                    potentialVolunteers.Add(agent);
                }
                else
                {
                    agent.SetVolunteerState(PedestrianAgent.VolunteerState.None);
                }
                continue;
            }

            Vector2Int nearestObstacle;
            float nearestDist;
            if (!TryGetNearestUnevaluatedVisibleObstacle(agent, obstacles, out nearestObstacle, out nearestDist))
            {
                // In LLM mode, allow re-evaluating the nearest visible obstacle to avoid
                // getting permanently stuck after all nearby obstacles were previously evaluated.
                if (volunteerDecisionMode == VolunteerDecisionMode.LLM)
                {
                    Vector2Int fallbackObstacle;
                    float fallbackDist;
                    if (TryGetNearestObstacle(agent.GetGridPos(), obstacles, out fallbackObstacle, out fallbackDist)
                        && fallbackDist <= obstacleVisibilityRange)
                    {
                        nearestObstacle = fallbackObstacle;
                        nearestDist = fallbackDist;
                    }
                    else
                    {
                        if (!TryGetNearestObstacle(agent.GetGridPos(), obstacles, out fallbackObstacle, out fallbackDist))
                            noObstacleAgents++;
                        else if (fallbackDist > obstacleVisibilityRange)
                            outOfVisibilityAgents++;
                        continue;
                    }
                }
                else
                {
                Vector2Int anyObstacle;
                float anyDist;
                if (!TryGetNearestObstacle(agent.GetGridPos(), obstacles, out anyObstacle, out anyDist))
                    noObstacleAgents++;
                else if (anyDist > obstacleVisibilityRange)
                    outOfVisibilityAgents++;
                continue;
                }
            }

            consideredAgents++;
            int nearestObstacleId = GetObstacleId(nearestObstacle);

            int nearbyAgentCount = agentManager.GetAgentsNearPosition(agent.GetGridPos(), obstacleVisibilityRange).Count;
            float blockageRatio = CalculateBlockageRatio(obstacles.Count);
            int currentVolunteerCount = potentialVolunteers.Count;

            VolunteerDecisionContext context = new VolunteerDecisionContext
            {
                nearbyAgentCount = Mathf.Max(2, nearbyAgentCount),
                obstacleCount = obstacles.Count,
                blockageRatio = blockageRatio,
                distanceToObstacle = nearestDist,
                currentVolunteerCount = currentVolunteerCount,
                volunteerCost = volunteerCost,
                failureCost = failureCost,
                unwillingness = unwillingnessOmega,
                agentPosition = agent.GetGridPos()
            };

            bool shouldVolunteer = false;

            if (volunteerDecisionMode == VolunteerDecisionMode.LLM)
            {
                if (string.IsNullOrEmpty(openAIKey))
                {
                    if (!llmKeyWarningLogged)
                    {
                        Debug.LogWarning("[LLM] openAIKey is empty. Fallback to mock LLM volunteer strategy.");
                        llmKeyWarningLogged = true;
                    }
                    llmMockFallbackCallsThisRun++;
                    if (debugLLMDecisionFlow)
                    {
                        Debug.Log($"[LLM-DEBUG] Step {currentStep} Agent {agent.gameObject.GetInstanceID()} -> MOCK fallback (no API key)");
                    }
                    shouldVolunteer = new MockLLMVolunteerStrategy().ShouldVolunteer(context);
                }
                else
                {
                    if (llmRequestsThisStep >= Mathf.Max(1, maxLLMRequestsPerStep))
                    {
                        llmMockFallbackCallsThisRun++;
                        if (debugLLMDecisionFlow)
                        {
                            Debug.Log($"[LLM-DEBUG] Step {currentStep} Agent {agent.gameObject.GetInstanceID()} -> MOCK fallback (request cap)");
                        }
                        shouldVolunteer = new MockLLMVolunteerStrategy().ShouldVolunteer(context);
                        goto LlmDecisionDone;
                    }

                    llmRequestsThisStep++;
                    llmApiDecisionCallsThisRun++;
                    if (debugLLMDecisionFlow)
                    {
                        Debug.Log($"[LLM-DEBUG] Step {currentStep} Agent {agent.gameObject.GetInstanceID()} -> API request");
                    }
                    VolunteerDilemma.CooperationLevel level = VolunteerDilemma.CooperationLevel.Selfish;
                    string explanation = string.Empty;
                    float obstacleToExitDist = GetObstacleDistanceToNearestExit(nearestObstacle);
                    int evacueesNearObstacle = CountEvacueesNearPosition(nearestObstacle, obstacleVisibilityRange);
                    float evacuationImpact = EstimateEvacuationImpactScore(obstacleToExitDist, evacueesNearObstacle);

                    yield return volunteerDilemma.DecideVolunteerActionAsync(agent, nearestObstacle, obstacleToExitDist, evacueesNearObstacle, evacuationImpact, (result, reason) =>
                    {
                        level = result;
                        explanation = reason;
                    });
                    shouldVolunteer = (level != VolunteerDilemma.CooperationLevel.Selfish);

                    if (!shouldVolunteer && IsLLMDecisionFailureReason(explanation))
                    {
                        llmMockFallbackCallsThisRun++;
                        if (debugLLMDecisionFlow)
                        {
                            Debug.Log($"[LLM-DEBUG] Step {currentStep} Agent {agent.gameObject.GetInstanceID()} -> MOCK fallback (api failure)");
                        }
                        shouldVolunteer = new MockLLMVolunteerStrategy().ShouldVolunteer(context);
                    }

                    simulationData.RecordLLMDecision(currentStep, agent.gameObject.GetInstanceID(), shouldVolunteer ? "volunteer" : "selfish", explanation);
                }

LlmDecisionDone:
                ;
            }
            else
            {
                shouldVolunteer = volunteerDecisionStrategy.ShouldVolunteer(context);
            }

            // In LLM mode, only mark evaluated once the agent actually volunteers for this obstacle.
            // This prevents permanently locking agents into "already evaluated" + always-selfish states.
            if (shouldVolunteer)
            {
                agent.MarkObstacleEvaluated(nearestObstacleId);
            }

            if (shouldVolunteer)
            {
                agent.SetVolunteerState(PedestrianAgent.VolunteerState.PotentialVolunteer);
                agent.AssignObstacle(nearestObstacleId, nearestObstacle);
                potentialVolunteers.Add(agent);
            }
        }

        if (debugLLMDecisionFlow && currentStep % 20 == 0)
        {
            Debug.Log($"[LLM-DEBUG] Step {currentStep} summary | mode={volunteerDecisionMode}, considered={consideredAgents}, potential={potentialVolunteers.Count}, outOfVisibility={outOfVisibilityAgents}, noObstacle={noObstacleAgents}, apiCalls={llmApiDecisionCallsThisRun}, mockCalls={llmMockFallbackCallsThisRun}");
        }

        HashSet<int> occupiedObstacleIds = new HashSet<int>();
        foreach (PedestrianAgent agent in allAgents)
        {
            if (agent.IsEvacuated() || !agent.IsActiveVolunteer() || !agent.HasAssignedObstacle())
                continue;

            int activeObstacleId = agent.GetAssignedObstacleId();
            if (obstacleMap.ContainsKey(activeObstacleId))
            {
                occupiedObstacleIds.Add(activeObstacleId);
            }
        }

        Dictionary<int, int> assignments = new Dictionary<int, int>();
        Dictionary<int, Vector2Int> unassignedObstacles = new Dictionary<int, Vector2Int>();
        foreach (KeyValuePair<int, Vector2Int> obstacleEntry in obstacleMap)
        {
            if (!occupiedObstacleIds.Contains(obstacleEntry.Key))
            {
                unassignedObstacles[obstacleEntry.Key] = obstacleEntry.Value;
            }
        }

        Dictionary<int, List<PedestrianAgent>> candidatesByObstacle = BuildCandidatesByObstacle(potentialVolunteers, unassignedObstacles);

        if (unassignedObstacles.Count > 0 && candidatesByObstacle.Count > 0)
        {
            if (volunteerDecisionMode == VolunteerDecisionMode.LLM && !string.IsNullOrEmpty(openAIKey) && llmRequestsThisStep < Mathf.Max(1, maxLLMRequestsPerStep))
            {
                llmRequestsThisStep++;
                llmApiDecisionCallsThisRun++;
                yield return RequestLLMAssignment(candidatesByObstacle, unassignedObstacles, assignments);
            }

            if (assignments.Count == 0)
            {
                BuildGreedyAssignment(candidatesByObstacle, unassignedObstacles, assignments);
            }

            Dictionary<int, PedestrianAgent> candidateById = new Dictionary<int, PedestrianAgent>();
            foreach (PedestrianAgent candidate in potentialVolunteers)
            {
                candidateById[candidate.gameObject.GetInstanceID()] = candidate;
            }

            foreach (KeyValuePair<int, int> assignment in assignments)
            {
                if (!unassignedObstacles.ContainsKey(assignment.Key) || !candidateById.ContainsKey(assignment.Value))
                    continue;

                PedestrianAgent selected = candidateById[assignment.Value];
                if (selected.IsEvacuated())
                    continue;

                selected.SetVolunteerState(PedestrianAgent.VolunteerState.ActiveVolunteer);
                selected.AssignObstacle(assignment.Key, unassignedObstacles[assignment.Key]);
            }
        }

        yield break;
    }

    private bool ShouldRunVolunteerSelectionThisStep()
    {
        int interval = Mathf.Max(1, volunteerSelectionInterval);
        if (currentStep == 1)
            return true;
        return (currentStep % interval) == 0;
    }

    private void CleanupInvalidVolunteerAssignments(List<PedestrianAgent> allAgents, Dictionary<int, Vector2Int> obstacleMap)
    {
        foreach (PedestrianAgent agent in allAgents)
        {
            if (agent.IsEvacuated())
                continue;

            if (agent.IsActiveVolunteer() || agent.IsPotentialVolunteer())
            {
                if (!agent.HasAssignedObstacle() || !obstacleMap.ContainsKey(agent.GetAssignedObstacleId()))
                {
                    agent.SetVolunteerState(PedestrianAgent.VolunteerState.None);
                }
            }
        }
    }

    private void HandleOriginalVolunteerStates(List<PedestrianAgent> allAgents, List<Vector2Int> obstacles, Dictionary<int, Vector2Int> obstacleMap)
    {
        // Original behavior: reset dynamic volunteer states every step.
        foreach (PedestrianAgent agent in allAgents)
        {
            if (!agent.IsEvacuated())
            {
                agent.SetVolunteerState(PedestrianAgent.VolunteerState.None);
            }
        }

        List<PedestrianAgent> visibleAgents = new List<PedestrianAgent>();
        Dictionary<int, float> visibleNearestObstacleDist = new Dictionary<int, float>();
        Dictionary<int, Vector2Int> visibleNearestObstaclePos = new Dictionary<int, Vector2Int>();
        foreach (PedestrianAgent agent in allAgents)
        {
            if (agent.IsEvacuated())
                continue;

            Vector2Int nearestObstacle;
            float nearestDist;
            if (!TryGetNearestObstacle(agent.GetGridPos(), obstacles, out nearestObstacle, out nearestDist))
                continue;

            if (nearestDist > obstacleVisibilityRange)
                continue;

            visibleAgents.Add(agent);
            int agentId = agent.gameObject.GetInstanceID();
            visibleNearestObstacleDist[agentId] = nearestDist;
            visibleNearestObstaclePos[agentId] = nearestObstacle;
        }

        List<PedestrianAgent> potentialVolunteers = new List<PedestrianAgent>();
        Dictionary<int, List<PedestrianAgent>> potentialByObstacle = new Dictionary<int, List<PedestrianAgent>>();
        foreach (PedestrianAgent agent in visibleAgents)
        {
            int agentId = agent.gameObject.GetInstanceID();
            float nearestDist = visibleNearestObstacleDist[agentId];
            Vector2Int nearestObstacle = visibleNearestObstaclePos[agentId];
            int nearestObstacleId = GetObstacleId(nearestObstacle);
            int nearbyAgentCount = agentManager.GetAgentsNearPosition(agent.GetGridPos(), obstacleVisibilityRange).Count;
            float blockageRatio = CalculateBlockageRatio(obstacles.Count);
            int currentVolunteerCount = potentialVolunteers.Count;

            VolunteerDecisionContext context = new VolunteerDecisionContext
            {
                nearbyAgentCount = Mathf.Max(2, nearbyAgentCount),
                obstacleCount = obstacles.Count,
                blockageRatio = blockageRatio,
                distanceToObstacle = nearestDist,
                currentVolunteerCount = currentVolunteerCount,
                volunteerCost = volunteerCost,
                failureCost = failureCost,
                unwillingness = unwillingnessOmega,
                agentPosition = agent.GetGridPos()
            };

            bool shouldVolunteer = volunteerDecisionStrategy.ShouldVolunteer(context);
            if (shouldVolunteer)
            {
                agent.SetVolunteerState(PedestrianAgent.VolunteerState.PotentialVolunteer);
                agent.AssignObstacle(nearestObstacleId, nearestObstacle);
                potentialVolunteers.Add(agent);

                if (!potentialByObstacle.ContainsKey(nearestObstacleId))
                {
                    potentialByObstacle[nearestObstacleId] = new List<PedestrianAgent>();
                }
                potentialByObstacle[nearestObstacleId].Add(agent);
            }
        }

        HashSet<int> usedAgentIds = new HashSet<int>();
        foreach (KeyValuePair<int, Vector2Int> obstacleEntry in obstacleMap)
        {
            int obstacleId = obstacleEntry.Key;
            Vector2Int obstaclePos = obstacleEntry.Value;

            if (!potentialByObstacle.ContainsKey(obstacleId))
                continue;

            List<PedestrianAgent> obstacleCandidates = potentialByObstacle[obstacleId];

            PedestrianAgent selected = null;
            float bestDist = float.MaxValue;
            for (int i = 0; i < obstacleCandidates.Count; i++)
            {
                PedestrianAgent candidate = obstacleCandidates[i];
                if (candidate.IsEvacuated())
                    continue;

                int candidateId = candidate.gameObject.GetInstanceID();
                if (usedAgentIds.Contains(candidateId))
                    continue;

                float dist = Mathf.Abs(candidate.GetGridPos().x - obstaclePos.x) + Mathf.Abs(candidate.GetGridPos().y - obstaclePos.y);
                if (dist < bestDist)
                {
                    bestDist = dist;
                    selected = candidate;
                }
            }

            if (selected != null)
            {
                usedAgentIds.Add(selected.gameObject.GetInstanceID());
                selected.SetVolunteerState(PedestrianAgent.VolunteerState.ActiveVolunteer);
                selected.AssignObstacle(obstacleId, obstaclePos);
            }
        }
    }

    private int GetObstacleId(Vector2Int obstaclePos)
    {
        int h = world != null ? Mathf.Max(1, world.height) : 1000;
        return obstaclePos.x * h + obstaclePos.y + 1;
    }

    private Dictionary<int, Vector2Int> BuildObstacleIdMap(List<Vector2Int> obstacles)
    {
        Dictionary<int, Vector2Int> map = new Dictionary<int, Vector2Int>();
        for (int i = 0; i < obstacles.Count; i++)
        {
            int obstacleId = GetObstacleId(obstacles[i]);
            map[obstacleId] = obstacles[i];
        }
        return map;
    }

    private bool TryGetNearestUnevaluatedVisibleObstacle(PedestrianAgent agent, List<Vector2Int> obstacles, out Vector2Int nearestObstacle, out float nearestDist)
    {
        nearestObstacle = new Vector2Int(-1, -1);
        nearestDist = float.MaxValue;

        for (int i = 0; i < obstacles.Count; i++)
        {
            Vector2Int obstacle = obstacles[i];
            int obstacleId = GetObstacleId(obstacle);
            if (agent.HasEvaluatedObstacle(obstacleId))
                continue;

            float dist = Mathf.Abs(obstacle.x - agent.GetGridPos().x) + Mathf.Abs(obstacle.y - agent.GetGridPos().y);
            if (dist > obstacleVisibilityRange)
                continue;

            if (dist < nearestDist)
            {
                nearestDist = dist;
                nearestObstacle = obstacle;
            }
        }

        return nearestObstacle.x >= 0;
    }

    private Dictionary<int, List<PedestrianAgent>> BuildCandidatesByObstacle(List<PedestrianAgent> candidates, Dictionary<int, Vector2Int> availableObstacles)
    {
        Dictionary<int, List<PedestrianAgent>> result = new Dictionary<int, List<PedestrianAgent>>();
        for (int i = 0; i < candidates.Count; i++)
        {
            PedestrianAgent candidate = candidates[i];
            if (candidate.IsEvacuated() || !candidate.HasAssignedObstacle() || candidate.IsActiveVolunteer())
                continue;

            int obstacleId = candidate.GetAssignedObstacleId();
            if (!availableObstacles.ContainsKey(obstacleId))
                continue;

            if (!result.ContainsKey(obstacleId))
            {
                result[obstacleId] = new List<PedestrianAgent>();
            }

            result[obstacleId].Add(candidate);
        }

        return result;
    }

    private void BuildGreedyAssignment(Dictionary<int, List<PedestrianAgent>> candidatesByObstacle, Dictionary<int, Vector2Int> obstacles, Dictionary<int, int> assignments)
    {
        HashSet<int> usedAgentIds = new HashSet<int>();

        foreach (KeyValuePair<int, List<PedestrianAgent>> obstacleCandidatesEntry in candidatesByObstacle)
        {
            int obstacleId = obstacleCandidatesEntry.Key;
            if (!obstacles.ContainsKey(obstacleId))
                continue;

            Vector2Int obstaclePos = obstacles[obstacleId];
            List<PedestrianAgent> candidates = obstacleCandidatesEntry.Value;

            PedestrianAgent bestAgent = null;
            float bestDist = float.MaxValue;

            for (int i = 0; i < candidates.Count; i++)
            {
                PedestrianAgent candidate = candidates[i];
                int candidateId = candidate.gameObject.GetInstanceID();
                if (candidate.IsEvacuated() || usedAgentIds.Contains(candidateId) || candidate.IsActiveVolunteer())
                    continue;

                float dist = Mathf.Abs(candidate.GetGridPos().x - obstaclePos.x) + Mathf.Abs(candidate.GetGridPos().y - obstaclePos.y);
                if (dist < bestDist)
                {
                    bestDist = dist;
                    bestAgent = candidate;
                }
            }

            if (bestAgent != null)
            {
                int bestAgentId = bestAgent.gameObject.GetInstanceID();
                usedAgentIds.Add(bestAgentId);
                assignments[obstacleId] = bestAgentId;
            }
        }
    }

    private float GetObstacleDistanceToNearestExit(Vector2Int obstacle)
    {
        if (world == null || world.exitPositions == null || world.exitPositions.Count == 0)
            return 0f;

        float bestDist = float.MaxValue;
        for (int i = 0; i < world.exitPositions.Count; i++)
        {
            Vector2Int exitPos = world.exitPositions[i];
            float dist = Mathf.Abs(obstacle.x - exitPos.x) + Mathf.Abs(obstacle.y - exitPos.y);
            if (dist < bestDist)
                bestDist = dist;
        }

        return bestDist;
    }

    private int CountEvacueesNearPosition(Vector2Int center, int radius)
    {
        if (agentManager == null)
            return 0;

        List<PedestrianAgent> nearby = agentManager.GetAgentsNearPosition(center, Mathf.Max(1, radius));
        int count = 0;
        for (int i = 0; i < nearby.Count; i++)
        {
            PedestrianAgent a = nearby[i];
            if (!a.IsEvacuated() && a.GetRole() == PedestrianAgent.Role.Evacuee)
                count++;
        }
        return count;
    }

    private float EstimateEvacuationImpactScore(float obstacleToExitDist, int evacueesNearObstacle)
    {
        float maxMapDist = Mathf.Max(1f, (world != null ? world.width + world.height : 100f));
        float exitProximityScore = 1f - Mathf.Clamp01(obstacleToExitDist / maxMapDist);
        float localDemandScore = Mathf.Clamp01(evacueesNearObstacle / Mathf.Max(1f, agentCount * 0.35f));

        // Higher score means this obstacle is more likely to affect evacuation flow.
        return Mathf.Clamp01(0.65f * exitProximityScore + 0.35f * localDemandScore);
    }

    private bool IsLLMDecisionFailureReason(string reason)
    {
        if (string.IsNullOrEmpty(reason))
            return false;

        string normalized = reason.ToLowerInvariant();
        return normalized.Contains("failed")
            || normalized.Contains("request")
            || normalized.Contains("parse")
            || normalized.Contains("not configured")
            || normalized.Contains("timeout")
            || normalized.Contains("error");
    }

    private IEnumerator RequestLLMAssignment(Dictionary<int, List<PedestrianAgent>> candidatesByObstacle, Dictionary<int, Vector2Int> obstacles, Dictionary<int, int> assignments)
    {
        List<PedestrianAgent> candidates = new List<PedestrianAgent>();
        HashSet<int> candidateIdSet = new HashSet<int>();
        HashSet<string> allowedPairs = new HashSet<string>();

        foreach (KeyValuePair<int, List<PedestrianAgent>> entry in candidatesByObstacle)
        {
            int obstacleId = entry.Key;
            List<PedestrianAgent> obstacleCandidates = entry.Value;
            for (int i = 0; i < obstacleCandidates.Count; i++)
            {
                PedestrianAgent candidate = obstacleCandidates[i];
                int candidateId = candidate.gameObject.GetInstanceID();
                if (!candidateIdSet.Contains(candidateId))
                {
                    candidateIdSet.Add(candidateId);
                    candidates.Add(candidate);
                }

                allowedPairs.Add(candidateId + ":" + obstacleId);
            }
        }

        List<int> candidateIds = new List<int>();
        string candidatesJson = "[";
        for (int i = 0; i < candidates.Count; i++)
        {
            PedestrianAgent c = candidates[i];
            int id = c.gameObject.GetInstanceID();
            candidateIds.Add(id);
            Vector2Int pos = c.GetGridPos();
            candidatesJson += (i > 0 ? "," : "") + "{\"agent_id\":" + id + ",\"x\":" + pos.x + ",\"y\":" + pos.y + "}";
        }
        candidatesJson += "]";

        List<int> obstacleIds = new List<int>(obstacles.Keys);
        string obstaclesJson = "[";
        for (int i = 0; i < obstacleIds.Count; i++)
        {
            int obstacleId = obstacleIds[i];
            Vector2Int pos = obstacles[obstacleId];
            obstaclesJson += (i > 0 ? "," : "") + "{\"obstacle_id\":" + obstacleId + ",\"x\":" + pos.x + ",\"y\":" + pos.y + "}";
        }
        obstaclesJson += "]";

        string distancesJson = "[";
        bool first = true;
        foreach (KeyValuePair<int, List<PedestrianAgent>> entry in candidatesByObstacle)
        {
            int obstacleId = entry.Key;
            if (!obstacles.ContainsKey(obstacleId))
                continue;

            Vector2Int obstaclePos = obstacles[obstacleId];
            List<PedestrianAgent> obstacleCandidates = entry.Value;
            for (int i = 0; i < obstacleCandidates.Count; i++)
            {
                PedestrianAgent candidate = obstacleCandidates[i];
                int agentId = candidate.gameObject.GetInstanceID();
                int dist = Mathf.Abs(candidate.GetGridPos().x - obstaclePos.x) + Mathf.Abs(candidate.GetGridPos().y - obstaclePos.y);
                if (!first) distancesJson += ",";
                distancesJson += "{\"agent_id\":" + agentId + ",\"obstacle_id\":" + obstacleId + ",\"distance\":" + dist + "}";
                first = false;
            }
        }
        distancesJson += "]";

        LLMDecisionPolicy.AssignmentContext context = new LLMDecisionPolicy.AssignmentContext
        {
            candidatesJson = candidatesJson,
            obstaclesJson = obstaclesJson,
            distancesJson = distancesJson
        };

        Dictionary<int, int> llmAssignments = new Dictionary<int, int>();
        yield return llmDecisionPolicy.RequestVolunteerAssignment(context, (result, explanation) =>
        {
            if (result != null)
            {
                llmAssignments = result;
            }
        });

        HashSet<int> usedAgentIds = new HashSet<int>();
        foreach (KeyValuePair<int, int> item in llmAssignments)
        {
            if (!obstacles.ContainsKey(item.Key))
                continue;

            string pairKey = item.Value + ":" + item.Key;
            if (!allowedPairs.Contains(pairKey))
                continue;

            if (usedAgentIds.Contains(item.Value))
                continue;

            bool foundCandidate = false;
            for (int i = 0; i < candidateIds.Count; i++)
            {
                if (candidateIds[i] == item.Value)
                {
                    foundCandidate = true;
                    break;
                }
            }

            if (!foundCandidate)
                continue;

            usedAgentIds.Add(item.Value);
            assignments[item.Key] = item.Value;
        }
    }

    private bool TryGetNearestObstacle(Vector2Int pos, List<Vector2Int> obstacles, out Vector2Int nearestObstacle, out float nearestDist)
    {
        nearestObstacle = new Vector2Int(-1, -1);
        nearestDist = float.MaxValue;

        foreach (Vector2Int obstacle in obstacles)
        {
            float dist = Mathf.Abs(obstacle.x - pos.x) + Mathf.Abs(obstacle.y - pos.y);
            if (dist < nearestDist)
            {
                nearestDist = dist;
                nearestObstacle = obstacle;
            }
        }

        return nearestObstacle.x >= 0;
    }

    private float CalculateBlockageRatio(int obstacleCountCurrent)
    {
        int exitCellCount = world != null ? Mathf.Max(1, world.exitPositions.Count) : 1;
        return Mathf.Clamp01((float)obstacleCountCurrent / exitCellCount);
    }

    private List<PedestrianAgent> GetAgentsByVolunteerState(PedestrianAgent.VolunteerState state)
    {
        List<PedestrianAgent> result = new List<PedestrianAgent>();
        List<PedestrianAgent> allAgents = agentManager.GetAgents();
        foreach (PedestrianAgent agent in allAgents)
        {
            if (!agent.IsEvacuated() && agent.GetVolunteerState() == state)
            {
                result.Add(agent);
            }
        }
        return result;
    }

    private void CheckSimulationComplete()
    {
        int totalAgents = agentManager.GetAgentCount();
        int evacuatedCount = agentManager.GetEvacuatedCount();

        if (evacuatedCount == totalAgents && totalAgents > 0)
        {
            simulationRunning = false;
            Debug.Log("=== SIMULATION COMPLETE ===");
            Debug.Log("Total Steps: " + currentStep);
            Debug.Log("Total Evacuated: " + evacuatedCount);
            Debug.Log("Average Time per Agent: " + (currentStep * stepInterval / evacuatedCount) + " seconds");
            Debug.Log("Help Actions: " + volunteerDilemma.GetHelpActionsCount());
            Debug.Log("Cooperative Volunteers: " + volunteerDilemma.GetCooperativeVolunteers());
            if (debugLLMDecisionFlow)
            {
                Debug.Log($"[LLM-DEBUG] Run summary | API calls: {llmApiDecisionCallsThisRun}, Mock fallback calls: {llmMockFallbackCallsThisRun}");
            }
            
            simulationData.SetSimulationStats(currentStep, elapsedTime);
            simulationData.ExportData();
        }
        else if (currentStep >= 200 && simulationRunning)
        {
            simulationRunning = false;
            Debug.Log("=== SIMULATION TIMEOUT (after " + currentStep + " steps) ===");
            Debug.Log("Evacuated: " + evacuatedCount + " / " + totalAgents);
            Debug.Log("Remaining: " + (totalAgents - evacuatedCount));
            if (debugLLMDecisionFlow)
            {
                Debug.Log($"[LLM-DEBUG] Run summary | API calls: {llmApiDecisionCallsThisRun}, Mock fallback calls: {llmMockFallbackCallsThisRun}");
            }
            
            List<PedestrianAgent> remainingAgents = agentManager.GetAgents();
            Debug.Log("\n=== Agents Still Trapped ===");
            
            int index = 0;
            foreach (PedestrianAgent agent in remainingAgents)
            {
                if (!agent.IsEvacuated())
                {
                    Vector2Int pos = agent.GetGridPos();
                    Vector2Int desired = agent.GetDesiredPos();
                    Debug.Log($"Agent {index}: at ({pos.x}, {pos.y}), desired: ({desired.x}, {desired.y})");
                    index++;
                }
            }
        }
    }


    public int GetCurrentStep()
    {
        return currentStep;
    }

    public int GetEvacuatedCount()
    {
        return evacuatedCount;
    }

    public int GetTotalAgents()
    {
        return agentManager != null ? agentManager.GetAgentCount() : 0;
    }

    public int GetVolunteerCount()
    {
        return agentManager != null ? agentManager.GetAgentsByRole(PedestrianAgent.Role.Volunteer).Count : 0;
    }

    public int GetEvacueeCount()
    {
        return agentManager != null ? agentManager.GetAgentsByRole(PedestrianAgent.Role.Evacuee).Count : 0;
    }

    public int GetObstacleCount()
    {
        return world != null ? world.GetObstaclePositions().Count : 0;
    }

    public bool IsSimulationRunning()
    {
        return simulationRunning;
    }

    public float GetDynamicFloorFieldValue(Vector2Int gridPos)
    {
        return dynamicFloorField != null ? dynamicFloorField.GetValue(gridPos) : 1f;
    }

    public float GetAnticipationFloorFieldValue(Vector2Int gridPos)
    {
        return anticipationFloorField != null ? anticipationFloorField.GetValue(gridPos) : 0f;
    }

    public List<PedestrianAgent> GetAllAgents()
    {
        return agentManager != null ? agentManager.GetAgents() : new List<PedestrianAgent>();
    }


    public void PauseSimulation()
    {
        simulationRunning = false;
        Debug.Log("Simulation paused at step " + currentStep);
    }

    public string GetConflictStrategyName()
    {
        return conflictStrategy.ToString();
    }

    public void ResumeSimulation()
    {
        simulationRunning = true;
        Debug.Log("Simulation resumed");
    }

    public void TogglePause()
    {
        isPaused = !isPaused;
        Debug.Log(isPaused ? "Simulation paused" : "Simulation resumed");
    }

    public void ResetSimulation()
    {
        simulationRunning = false;
        if (agentManager != null)
        {
            agentManager.DestroyAllAgents();
        }
        currentStep = 0;
        evacuatedCount = 0;
        timeSinceLastStep = 0f;
        Debug.Log("Simulation reset");
    }
}
