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
    private const string ObstacleHandlingModeKey = "sim.obstacleHandlingMode";
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
        LLM,
        NoVolunteers,
        MockHeuristic,
        RandomMatched
    }

    [Header("Reproducible research (Inspector)")]
    public ResearchScenario researchScenario = ResearchScenario.RandomRoom;
    [Header("Paper obstacle dynamics")]
    public ObstacleHandlingMode obstacleHandlingMode = ObstacleHandlingMode.PaperRelocation;
    [Header("Coordination extension (Local dispatcher)")]
    public Coordination.ExecutionMode paperExecutionMode=Coordination.ExecutionMode.PaperReference;
    public Coordination.AvailabilityMode coordinationAvailability=Coordination.AvailabilityMode.PolicyWillingness;
    [Min(1)] public int coordinationIdleSteps=30;
    [Min(1)] public int coordinationCooldownSteps=5;
    public PaperDestinationRule paperDestinationRule = PaperDestinationRule.NextToWallsOrObstacles;
    public float paperDestinationExitDistance = 2f;
    public float paperAbandonDensity = 0.01f;
    public int paperDensityWindow = 10;
    public int paperReplanAfterSteps = 10;
    public bool paperExitWidthWeighting = true;
    [Min(1)] public int paperManipulationSteps = 1;
    public PaperSigmaMetric paperSigmaMetric = PaperSigmaMetric.GridDistance;
    [Range(0,1)] public float paperDiffusion = 0.3f;
    [Range(0,1)] public float paperDecay = 0.1f;
    [Min(0)] public float paperAnticipationRadius = 6f;
    private PaperModelEngine paperModel;
    public PaperModelEngine PaperModel => paperModel;
    public int baseSeed = 2026;
    [Tooltip("0: run until everyone evacuates; positive values are an explicit validation watchdog, not a success threshold.")]
    public int maxSimulationSteps = 0;
    public int EffectiveVolunteerActionRange => obstacleHandlingMode==ObstacleHandlingMode.PaperRelocation || volunteerDecisionMode == VolunteerDecisionMode.OriginalGameTheory ? 1 : Mathf.Max(1, obstacleActionRange);
    public int researchExitWidth = 3;
    [Range(1,4)] public int exitCount = 4;
    public int EffectiveExitCount => researchScenario==ResearchScenario.RandomRoom || researchScenario==ResearchScenario.OpenRoom
        ? Mathf.Clamp(exitCount,1,4) : researchScenario==ResearchScenario.SingleBlockedExit ? 1 : 2;
    public int exitApproachDepth = 3;
    [Min(1)] public int obstacleRemovalWorkSteps = 5;
    private readonly Dictionary<int, int> obstacleWorkProgress = new Dictionary<int, int>();
    public float yielderDefectionCost = 1f;
    public float yielderFriction = 0f;
    public bool allowMockFallback = false;
    public bool useLLMAssignment = false;
    [System.NonSerialized] public string researchOutputFolder;
    [Header("Automatic experiment notebook")]
    public bool recordExperimentsAutomatically = true;
    [TextArea] public string experimentPurpose = "";
    [System.NonSerialized] public string experimentRecordsRootOverride;
    private string AutomaticPurpose => string.IsNullOrWhiteSpace(experimentPurpose)
        ? agentResearchPhase+" / "+volunteerDecisionMode+" / "+researchScenario+": evaluate evacuation and assistance; no custom objective supplied."
        : experimentPurpose;
    private string experimentID = System.DateTime.UtcNow.ToString("yyyy-MM-dd_HHmmss_fff") + "_" + System.Guid.NewGuid().ToString("N").Substring(0, 8);
    private int activeRunID = 1;
    private bool runExported;
    private string currentTermination = "running";
    private readonly System.Diagnostics.Stopwatch runClock = new System.Diagnostics.Stopwatch();
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
    [Tooltip("LegacyClearance only. PaperRelocation evaluates every eligible candidate before advancing the step.")]
    public int maxLLMRequestsPerStep = 3;
    [Tooltip("Optional JSONL decision trace for strict offline replay; empty means live API.")]
    public string paperDecisionReplayPath = "";
    public AgentInformationCondition agentInformation = AgentInformationCondition.Core;
    public AgentPromptWording agentPromptWording = AgentPromptWording.Standard;
    public AgentResearchPhase agentResearchPhase = AgentResearchPhase.Development;
    [Tooltip("Frozen JSON generated from separate calibration runs; required for RandomMatched.")]
    public string cooperationCalibrationPath = "";
    [Tooltip("FinalTest requires a locked plan produced by tools/research_plan.py.")]
    public string lockedStudyPlanPath = "";
    [System.NonSerialized] public ClosedLoopInitialState closedLoopInitialState;
    [System.NonSerialized] public System.Action closedLoopBeforeApiRequest;
    [System.NonSerialized] public bool closedLoopZeroStepValidation;
    [System.NonSerialized] public string closedLoopSourceSHA="",closedLoopStudyPlanID="",closedLoopLockPath="",closedLoopJobID="";
    public string lockedCoordinationStudyPlanPath="";
    private CoordinationStudyPlan.Job coordinationStudyJob;
    private string lockedStudyPlanID = "";
    private string activeAgentSettings;
    private bool activeResearchLocked;
    private string AgentSettingsIdentity => AgentConditionKey+"|"+volunteerDecisionMode+"|"+agentInformation+"|"+agentResearchPhase+"|"+openAIModel+"|"+paperDecisionReplayPath+"|"+cooperationCalibrationPath+"|"+maxAgentRequestsPerRun+"|"+enableCoordinationLiveRequests+"|"+maxCoordinationRequestsPerRun+"|"+coordinationMaxOutputTokens+"|"+coordinationMaxPromptChars+"|"+coordinationReplayPath+"|"+lockedCoordinationStudyPlanPath+"|"+closedLoopSourceSHA+"|"+closedLoopStudyPlanID+"|"+(closedLoopInitialState==null?"":closedLoopInitialState.Identity);
    [Tooltip("Zero disables the total live-request safety limit. Exceeding it invalidates, never skips candidates.")]
    public int maxAgentRequestsPerRun = 0;
    private CooperationCalibration cooperationCalibration;
    public string AgentConditionKey => (closedLoopInitialState==null ? "" : "closed-loop-v1|"+PersonalDecisionProtocol.Version+"|"+closedLoopInitialState.TemplateSHA+"|")+string.Join("|", new string[] {
        paperExecutionMode.ToString(),coordinationAvailability.ToString(),coordinationIdleSteps.ToString(),coordinationCooldownSteps.ToString(),
        agentPromptWording.ToString(),researchScenario.ToString(), world.width.ToString(), world.height.ToString(), agentCount.ToString(),
        obstacleCount.ToString(),EffectiveExitCount.ToString(),researchExitWidth.ToString(),agentSpawnAreaSize.x.ToString(),agentSpawnAreaSize.y.ToString(),
        paperManipulationSteps.ToString(),volunteerCost.ToString("R",System.Globalization.CultureInfo.InvariantCulture),
        failureCost.ToString("R",System.Globalization.CultureInfo.InvariantCulture),unwillingnessOmega.ToString("R",System.Globalization.CultureInfo.InvariantCulture),
        obstacleVisibilityRange.ToString(),maxSimulationSteps.ToString(),movementStrategy.ToString(),conflictStrategy.ToString(),
        paperExitWidthWeighting.ToString(),paperSigmaMetric.ToString(),paperDestinationRule.ToString(),
        paperDestinationExitDistance.ToString("R",System.Globalization.CultureInfo.InvariantCulture),paperAbandonDensity.ToString("R",System.Globalization.CultureInfo.InvariantCulture),
        paperDensityWindow.ToString(),paperReplanAfterSteps.ToString(),paperDiffusion.ToString("R",System.Globalization.CultureInfo.InvariantCulture),
        paperDecay.ToString("R",System.Globalization.CultureInfo.InvariantCulture),paperAnticipationRadius.ToString("R",System.Globalization.CultureInfo.InvariantCulture),
        world.cellSize.ToString("R",System.Globalization.CultureInfo.InvariantCulture),yielderDefectionCost.ToString("R",System.Globalization.CultureInfo.InvariantCulture),
        yielderFriction.ToString("R",System.Globalization.CultureInfo.InvariantCulture),exitApproachDepth.ToString(),stepInterval.ToString("R",System.Globalization.CultureInfo.InvariantCulture),
        kStatic.ToString("R",System.Globalization.CultureInfo.InvariantCulture),kDynamic.ToString("R",System.Globalization.CultureInfo.InvariantCulture),
        kAnticipation.ToString("R",System.Globalization.CultureInfo.InvariantCulture),movementTemperature.ToString("R",System.Globalization.CultureInfo.InvariantCulture)
    });
    public void ValidateAgentResearchSettings(int runSeed)
    {
        if(!System.Enum.IsDefined(typeof(Coordination.ExecutionMode),paperExecutionMode) ||
            !System.Enum.IsDefined(typeof(Coordination.AvailabilityMode),coordinationAvailability) || coordinationIdleSteps<1 || coordinationCooldownSteps<1)
            throw new System.InvalidOperationException("Invalid coordination configuration");
        if(paperExecutionMode!=Coordination.ExecutionMode.PaperReference && obstacleHandlingMode!=ObstacleHandlingMode.PaperRelocation)
            throw new System.InvalidOperationException("CoordinatedExtension requires PaperRelocation physics");
        if(coordinationAvailability==Coordination.AvailabilityMode.AllEligibleControl &&
            (paperExecutionMode==Coordination.ExecutionMode.PaperReference || volunteerDecisionMode==VolunteerDecisionMode.NoVolunteers))
            throw new System.InvalidOperationException("AllEligibleControl requires the extension and is not a NoVolunteers policy");
        if(!System.Enum.IsDefined(typeof(AgentInformationCondition),agentInformation) ||
            !System.Enum.IsDefined(typeof(VolunteerDecisionMode),volunteerDecisionMode) ||
            !System.Enum.IsDefined(typeof(AgentResearchPhase),agentResearchPhase) ||
            !System.Enum.IsDefined(typeof(AgentPromptWording),agentPromptWording))
            throw new System.InvalidOperationException("Unknown agent policy/information setting");
        if(agentResearchPhase!=AgentResearchPhase.Development &&
            (obstacleHandlingMode!=ObstacleHandlingMode.PaperRelocation || maxSimulationSteps<=0 || allowMockFallback))
            throw new System.InvalidOperationException("Calibration/test requires PaperRelocation, finite horizon and no mock fallback");
        if(paperExecutionMode==Coordination.ExecutionMode.LLMExtension)
        {
            if(maxCoordinationRequestsPerRun<1 || coordinationMaxOutputTokens<64 || coordinationMaxOutputTokens>16384 || coordinationMaxPromptChars<256 || string.IsNullOrWhiteSpace(openAIModel))
                throw new System.InvalidOperationException("Invalid LLM dispatch request/token/prompt limits");
            if(agentResearchPhase!=AgentResearchPhase.Development && string.IsNullOrEmpty(lockedCoordinationStudyPlanPath))
                throw new System.InvalidOperationException("LLM dispatch requires its locked coordination study plan outside Development");
        }
        if(!string.IsNullOrEmpty(coordinationReplayPath) && (paperExecutionMode!=Coordination.ExecutionMode.LLMExtension || batchRunCount!=1))
            throw new System.InvalidOperationException("Coordination replay requires one LLM Coordination run");
        lockedStudyPlanID="";coordinationStudyJob=null;
        if(!string.IsNullOrEmpty(lockedCoordinationStudyPlanPath))
        {
            if(!string.IsNullOrEmpty(lockedStudyPlanPath))throw new System.InvalidOperationException("Select one study lock, not both");
            coordinationStudyJob=CoordinationStudyPlan.Validate(lockedCoordinationStudyPlanPath,this,runSeed,out lockedStudyPlanID);
        }
        else if(closedLoopInitialState!=null && agentResearchPhase==AgentResearchPhase.FinalTest)
            lockedStudyPlanID=ClosedLoopStudyGuard.Validate(closedLoopLockPath,this,runSeed);
        else if(agentResearchPhase==AgentResearchPhase.FinalTest || !string.IsNullOrEmpty(lockedStudyPlanPath))
            lockedStudyPlanID=AgentStudyPlan.LoadAndValidate(lockedStudyPlanPath,this,runSeed).planID;
        if(agentResearchPhase!=AgentResearchPhase.Development &&
            (agentCount<=0 || world==null || world.width<3 || world.height<3 ||
             !PaperDecisionSpecification.HasValidCosts(volunteerCost,failureCost,unwillingnessOmega) || paperManipulationSteps<1 ||
             string.IsNullOrWhiteSpace(openAIModel)))
            throw new System.InvalidOperationException("Invalid study population, costs, world or model");
        cooperationCalibration=null;
        if(volunteerDecisionMode==VolunteerDecisionMode.RandomMatched)
        {
            if(obstacleHandlingMode!=ObstacleHandlingMode.PaperRelocation)
                throw new System.InvalidOperationException("RandomMatched requires PaperRelocation");
            cooperationCalibration=CooperationCalibration.Load(cooperationCalibrationPath,AgentConditionKey,
                openAIModel,agentInformation,runSeed,agentResearchPhase,closedLoopInitialState!=null,closedLoopInitialState==null?"":closedLoopInitialState.TemplateSHA,closedLoopSourceSHA,maxSimulationSteps);
        }
        if(!string.IsNullOrEmpty(paperDecisionReplayPath) && (batchRunCount!=1 || volunteerDecisionMode!=VolunteerDecisionMode.LLM))
            throw new System.InvalidOperationException("Strict replay requires a single LLM run and its matching trace");
    }

    [Header("LLM Coordination (separate from individual willingness)")]
    public bool enableCoordinationLiveRequests=false;
    public int maxCoordinationRequestsPerRun=20;
    public int coordinationMaxOutputTokens=1024;
    public int coordinationMaxPromptChars=60000;
    public string coordinationReplayPath="";
    private Coordination.LLMDispatchSession coordinationSession;
#if UNITY_EDITOR
    [System.NonSerialized] public Coordination.DispatchTransport coordinationTestTransport;
#endif
    private Coordination.DispatchOptions DispatchOptions => new Coordination.DispatchOptions {
        model=openAIModel,conditionKey=AgentConditionKey+"|"+Coordination.LLMDispatchProtocol.Version+"|"+maxCoordinationRequestsPerRun+"|"+coordinationMaxOutputTokens+"|"+coordinationMaxPromptChars,replayPath=coordinationReplayPath,enableLive=enableCoordinationLiveRequests,
        maxRequests=maxCoordinationRequestsPerRun,maxOutputTokens=coordinationMaxOutputTokens,maxPromptChars=coordinationMaxPromptChars};
    public void RejectCoordination(string reason)
    {simulationRunning=false;ExportFinishedRun("invalid_coordination_"+reason);}
    public IEnumerator DecideCoordination(Coordination.Snapshot snapshot,System.Action<Coordination.Proposal> callback)
    {
        simulationData.RecordDispatchStart(snapshot,Coordination.LLMDispatchSession.PayloadFor(snapshot,DispatchOptions));
        Coordination.Proposal result=null;Coordination.DispatchAudit audit=null;
        yield return coordinationSession.Decide(snapshot,(proposal,record)=>{result=proposal;audit=record;});
        if(audit!=null){simulationData.RecordDispatchAudit(audit);llmApiDecisionCallsThisRun+=audit.attempts;}
        if(!simulationRunning || activeAgentSettings!=AgentSettingsIdentity)
        {simulationData.RecordDispatchApplication(snapshot,false,"settings_changed_or_interrupted");RejectCoordination("settings_changed_or_interrupted");callback(null);yield break;}
        if(result==null){simulationData.RecordDispatchApplication(snapshot,false,audit?.error??"missing_result");RejectCoordination(audit?.error??"missing_result");callback(null);yield break;}
        callback(result);
    }

    private PaperAgentDecisionJournal paperDecisionJournal = new PaperAgentDecisionJournal();
    private DecisionRandomStream decisionRandom;
    public float volunteerCost = 0.005f;
    public float failureCost = 0.5f;
    public float unwillingnessOmega = 5f;

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
    private int individualPaperRequestsThisRun = 0;
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

        // Research runs use the reviewed Inspector profile, not stale menu preferences.
        if(agentResearchPhase==AgentResearchPhase.Development) LoadSettingsFromMainMenu();
        // Research profiles bypass menu prefs, but credentials are always loaded locally.
        openAIKey=LocalOpenAIKey.Load();
        for(int index=0;index<Mathf.Max(1,batchRunCount);index++)
            ValidateAgentResearchSettings(unchecked(baseSeed+index));

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
        if(PlayerPrefs.HasKey("sim.researchScenario"))
        {
            int selected=PlayerPrefs.GetInt("sim.researchScenario");
            if(System.Enum.IsDefined(typeof(ResearchScenario),selected))researchScenario=(ResearchScenario)selected;
        }
        if(PlayerPrefs.HasKey("sim.maxAgentRequestsPerRun"))maxAgentRequestsPerRun=Mathf.Max(0,PlayerPrefs.GetInt("sim.maxAgentRequestsPerRun"));

        if(PlayerPrefs.HasKey("sim.coordinationMode")) paperExecutionMode=(Coordination.ExecutionMode)PlayerPrefs.GetInt("sim.coordinationMode");
        if(PlayerPrefs.HasKey("sim.exitCount")) exitCount=Mathf.Clamp(PlayerPrefs.GetInt("sim.exitCount"),1,4);
        if(PlayerPrefs.HasKey("sim.agentInformation"))
            agentInformation=(AgentInformationCondition)PlayerPrefs.GetInt("sim.agentInformation");
        if(PlayerPrefs.HasKey(ObstacleHandlingModeKey))
        {
            int handling=PlayerPrefs.GetInt(ObstacleHandlingModeKey);
            obstacleHandlingMode=System.Enum.IsDefined(typeof(ObstacleHandlingMode),handling)
                ? (ObstacleHandlingMode)handling : ObstacleHandlingMode.PaperRelocation;
        }
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
        PlayerPrefs.SetInt("sim.coordinationMode",(int)paperExecutionMode);
        PlayerPrefs.SetInt("sim.exitCount",Mathf.Clamp(exitCount,1,4));
        PlayerPrefs.SetInt("sim.agentInformation",(int)agentInformation);
        PlayerPrefs.SetInt(ObstacleHandlingModeKey,(int)obstacleHandlingMode);
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

    private void StartSingleRun(int runID = 1)
    {
        if(closedLoopInitialState!=null)closedLoopInitialState.Validate(agentCount,unchecked(baseSeed+runID-1));
        ValidateAgentResearchSettings(unchecked(baseSeed + runID - 1));
        if(coordinationStudyJob!=null)
        {
            bool apiNeeded=paperExecutionMode==Coordination.ExecutionMode.LLMExtension ||
                (volunteerDecisionMode==VolunteerDecisionMode.LLM && coordinationAvailability!=Coordination.AvailabilityMode.AllEligibleControl);
            if(apiNeeded && (string.IsNullOrEmpty(openAIKey) || (paperExecutionMode==Coordination.ExecutionMode.LLMExtension && !enableCoordinationLiveRequests)))
                throw new System.InvalidOperationException("Scheduled LLM job requires configured key/live dispatch before its budget is claimed");
            CoordinationStudyPlan.Claim(experimentRecordsRootOverride??AutomaticExperimentLog.DefaultRoot,lockedStudyPlanID,coordinationStudyJob);
        }
        activeRunID = runID;
        currentTermination = "running";
        runClock.Restart();
        obstacleWorkProgress.Clear();
        runExported = false;
        agentManager?.DestroyAllAgents();
        Random.InitState(unchecked(baseSeed + runID - 1));
        decisionRandom = new DecisionRandomStream(DecisionRandomStream.SeedForRun(unchecked(baseSeed + runID - 1)));
        world.Init();
        world.paperNeighborhood = obstacleHandlingMode == ObstacleHandlingMode.PaperRelocation;
        Debug.Log("GridWorld initialized with size: " + world.width + "x" + world.height);
        if(closedLoopInitialState!=null)closedLoopInitialState.Configure(world);
        else ResearchEnvironment.Configure(world, researchScenario, obstacleCount, researchExitWidth, exitApproachDepth,exitCount);
        floorField = new StaticFloorField(world);
        dynamicFloorField = new DynamicFloorField(world);
        anticipationFloorField = new AnticipationFloorField(world);
        if(world.paperNeighborhood)
        {
            dynamicFloorField.diffusionRate=paperDiffusion;dynamicFloorField.decayRate=paperDecay;
            anticipationFloorField.influenceRadius=paperAnticipationRadius;
        }
        pathfinder = new AStarPathfinding(world);
        agentManager = new AgentManager(world, agentPrefab);
        yielderGame = new YielderGame(conflictStrategy) { defectionCost = yielderDefectionCost, friction = yielderFriction };
        volunteerDilemma = new VolunteerDilemma(agentManager, world, floorField) {
            observationRange = obstacleVisibilityRange, exitApproachDepth = exitApproachDepth,
            volunteerCost = volunteerCost, failureCost = failureCost, unwillingness = unwillingnessOmega
        };
        llmDecisionPolicy = new LLMDecisionPolicy(openAIKey, openAIModel);
        volunteerDilemma.SetLLMPolicy(llmDecisionPolicy);
        volunteerDilemma.decisionMode = useLLMVolunteerDecision ? VolunteerDilemma.DecisionMode.LLM : VolunteerDilemma.DecisionMode.Probabilistic;
        ConfigureVolunteerDecisionStrategy();
        paperDecisionJournal = new PaperAgentDecisionJournal();
        coordinationSession=null;
        if(paperExecutionMode==Coordination.ExecutionMode.LLMExtension)
        {
            Coordination.DispatchTransport transport=(payload,callback)=>Coordination.DispatchHttp.Send(openAIKey,payload,callback);
#if UNITY_EDITOR
            if(coordinationTestTransport!=null) transport=coordinationTestTransport;
#endif
            coordinationSession=new Coordination.LLMDispatchSession(DispatchOptions,transport);
        }
        simulationData = new SimulationData(conflictStrategy.ToString(), runID, researchOutputFolder, experimentID,
            recordExperimentsAutomatically ? experimentRecordsRootOverride??AutomaticExperimentLog.DefaultRoot : null,AutomaticPurpose);
        SpawnAgents();
        paperModel = obstacleHandlingMode == ObstacleHandlingMode.PaperRelocation
            ? new PaperModelEngine(this,world,agentManager.GetAgents(),dynamicFloorField,anticipationFloorField,yielderGame,DecidePaperVolunteer) : null;
        if(paperModel!=null && paperModel.InitialBlockedTaskCount==0)
            Debug.LogWarning("[VOLUNTEER] No unfinished obstacle blocks an exit. Paper recruitment will not trigger in this layout; choose a blocked-exit scenario for a functional test.");
        simulationData.SetSimulationParameters(kStatic, kDynamic, kAnticipation, movementTemperature,
            agentManager.GetAgentCount(), world.GetObstaclePositions().Count);
        activeAgentSettings=AgentSettingsIdentity;
        activeResearchLocked=agentResearchPhase!=AgentResearchPhase.Development || paperExecutionMode==Coordination.ExecutionMode.LLMExtension;
        simulationData.SetRunMetadata(JsonUtility.ToJson(CaptureConfiguration(), true));
        foreach (var agent in agentManager.GetAgents())
            simulationData.RecordPosition(0, agent.AgentID, agent.gridPos, agent.GetVolunteerState().ToString(), false);
        if(paperModel!=null) foreach(var obstacle in paperModel.Obstacles) simulationData.RecordObstacleState(0,obstacle);
        simulationRunning = true;
        currentStep = 0;
        timeSinceLastStep = 0f;
        elapsedTime = 0f;
        evacuatedCount = 0;
        llmApiDecisionCallsThisRun = 0;individualPaperRequestsThisRun=0;
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

        System.Func<float> decisionSample = null;
        if (obstacleHandlingMode == ObstacleHandlingMode.PaperRelocation)
        {
            if (decisionRandom == null)
                decisionRandom = new DecisionRandomStream(DecisionRandomStream.SeedForRun(unchecked(baseSeed + activeRunID - 1)));
            decisionSample = decisionRandom.NextValue;
        }
        if (volunteerDecisionMode == VolunteerDecisionMode.RandomMatched)
        {
            if(cooperationCalibration==null)
            { volunteerDecisionStrategy=null; return; } // Inspector configuration is validated before starting.
            volunteerDecisionStrategy = new RandomMatchedVolunteerStrategy(cooperationCalibration.probability,decisionSample);
        }
        else if (volunteerDecisionMode == VolunteerDecisionMode.LLM || volunteerDecisionMode == VolunteerDecisionMode.MockHeuristic)
            volunteerDecisionStrategy = new MockLLMVolunteerStrategy(decisionSample);
        else
            volunteerDecisionStrategy = new OriginalGameTheoryVolunteerStrategy(decisionSample);

        if (volunteerDilemma != null)
        {
            volunteerDilemma.decisionMode = useLLMVolunteerDecision
                ? VolunteerDilemma.DecisionMode.LLM
                : VolunteerDilemma.DecisionMode.Probabilistic;
        }
    }

    [ContextMenu("Apply Paper Reference Parameters (Paper Relocation)")]
    private void ApplyPaperReferenceParameters()
    {
        obstacleHandlingMode = ObstacleHandlingMode.PaperRelocation;
        paperExecutionMode=Coordination.ExecutionMode.PaperReference;coordinationAvailability=Coordination.AvailabilityMode.PolicyWillingness;
        paperDiffusion=0.3f;paperDecay=0.1f;paperAnticipationRadius=6;
        if(world!=null) world.cellSize=0.4f;
        volunteerDecisionMode = VolunteerDecisionMode.OriginalGameTheory;
        agentInformation=AgentInformationCondition.Core;agentPromptWording=AgentPromptWording.Standard;
        movementStrategy = PedestrianAgent.MovementStrategy.Combined;
        conflictStrategy = YielderGame.Strategy.PaperYielder;
        kStatic = 3f; kDynamic = 1f; kAnticipation = 5f; movementTemperature = 1f;
        yielderDefectionCost = 1f; yielderFriction = 0f;
        volunteerCost = 0.005f; failureCost = 0.5f; unwillingnessOmega = 5f;
        volunteerSelectionInterval = 1; obstacleVisibilityRange = 20; obstacleActionRange = 1;
        stepInterval = 0.3f; maxSimulationSteps = 0;
        allowMockFallback = false; useLLMAssignment = false;
        SyncCurrentValuesToMainMenuSettings();
        Debug.Log("Applied paper reference parameters and relocation dynamics. See model audit for explicit implementation choices.");
    }

    private IEnumerator BatchRunCoroutine()
    {
        List<int> stepsList = new List<int>();
        List<float> timeList = new List<float>();
        List<bool> completedList = new List<bool>();
        List<bool> validRuns = new List<bool>();

        for (int i = 0; i < batchRunCount; i++)
        {
            if (inGameUIController != null)
                inGameUIController.SetRoundText(i + 1, batchRunCount);
            simulationRunning = false; // 確保每輪開始前重置
            StartSingleRun(i + 1);
            // 等待本輪模擬結束
            while (simulationRunning)
                yield return null;
            // 每輪結束後記錄步數和時間
            bool valid = currentTermination == "completed" || currentTermination == "timeout";
            validRuns.Add(valid);
            bool completed = currentTermination == "completed";
            completedList.Add(completed);

            int completionSteps = completed ? currentStep : -1;
            float completionTime = completed ? elapsedTime : float.NaN;
            stepsList.Add(completionSteps);
            timeList.Add(completionTime);
            yield return new WaitForSeconds(0.5f); // 可調整每輪間隔
        }
        // batch 結束時一次性輸出所有資料
        // 輸出 batch summary
        ExportBatchSummary(stepsList, timeList, completedList, validRuns);
        if (inGameUIController != null)
            inGameUIController.SetRoundText(0, batchRunCount); // 清空或顯示完成
        Debug.Log($"Batch run {batchRunCount} completed.");
    }

    // 輸出 batch summary csv
    private void ExportBatchSummary(List<int> stepsList, List<float> timeList, List<bool> completedList, List<bool> validRuns)
    {
        if (stepsList.Count == 0) return;
        string folder = simulationData.DataFolderPath;
        string path = System.IO.Path.Combine(folder, experimentID + "_batch_summary.csv");
        var steps = new List<float>();
        var times = new List<float>();
        int validCount = validRuns.FindAll(v => v).Count;
        for (int i = 0; i < stepsList.Count; i++)
            if (completedList[i]) { steps.Add(stepsList[i]); times.Add(timeList[i]); }
        using (var writer = new System.IO.StreamWriter(path))
        {
            writer.WriteLine("SummaryMetric,successful_runs_only_T100; failures are right-censored at maxSimulationSteps");
            writer.WriteLine("BatchSize,Strategy,AvgStepsT100,StdStepsT100,AvgTimeT100,StdTimeT100,CompletedRuns100Pct,TimedOutRuns,CompletionRate100Pct,ValidRuns,InvalidRuns");
            writer.WriteLine(System.FormattableString.Invariant($"{stepsList.Count},{conflictStrategy},{SimulationData.Mean(steps):F4},{SimulationData.PopulationStd(steps):F4},{SimulationData.Mean(times):F4},{SimulationData.PopulationStd(times):F4},{steps.Count},{validCount - steps.Count},{(validCount > 0 ? (float)steps.Count / validCount : float.NaN):F4},{validCount},{stepsList.Count - validCount}"));
        }
    }

    private ResearchRunConfiguration CaptureConfiguration()
    {
        return new ResearchRunConfiguration {
            zeroStepValidation=closedLoopZeroStepValidation,geometryTemplateSHA=closedLoopInitialState==null?"":closedLoopInitialState.TemplateSHA,initialStateSHA=closedLoopInitialState==null?"":closedLoopInitialState.Identity,closedLoopSourceSHA=closedLoopSourceSHA,
            initialBlockedObstacles=closedLoopInitialState==null?-1:closedLoopInitialState.blocked,mirrored=closedLoopInitialState!=null && closedLoopInitialState.mirrored,
            schemaVersion = obstacleHandlingMode == ObstacleHandlingMode.PaperRelocation ? "4-paper-relocation" : "3-clearance-completion",
            modelScope = obstacleHandlingMode == ObstacleHandlingMode.PaperRelocation ? "Paper relocation implementation; numerical figure replication pending" : "Legacy clearance approximation",
            obstacleHandling = obstacleHandlingMode.ToString(),destinationRule = paperDestinationRule.ToString(),
            destinationExitDistance = paperDestinationExitDistance,abandonDensity = paperAbandonDensity,
            densityWindow = paperDensityWindow,replanAfterSteps = paperReplanAfterSteps,
            movableObstacles = paperModel!=null ? paperModel.Obstacles.Count : world.GetObstaclePositions().Count,
            immovableObstacles = world.immovableObstacles.Count,
            fixedObstaclePositions = new List<Vector2Int>(world.immovableObstacles).ToArray(),
            cellSize = world.cellSize,
            exitWidthWeighted = paperExitWidthWeighting,
            manipulationSteps = paperManipulationSteps,
            sigmaMetric = paperSigmaMetric.ToString(),
            experimentID = experimentID, runID = activeRunID, seed = unchecked(baseSeed + activeRunID - 1),
            unityVersion = Application.unityVersion, scenario = researchScenario.ToString(),
            movement = movementStrategy.ToString(), conflict = conflictStrategy.ToString(),
            volunteerPolicy = paperExecutionMode!=Coordination.ExecutionMode.PaperReference && coordinationAvailability==Coordination.AvailabilityMode.AllEligibleControl
                ? "AllEligibleControl" : volunteerDecisionMode.ToString(), model = openAIModel,
            coordinationProtocol=Coordination.LLMDispatchProtocol.Version,coordinationExecution=string.IsNullOrEmpty(coordinationReplayPath)?"live_or_disabled":"strict_replay",
            coordinationRequestLimit=maxCoordinationRequestsPerRun,coordinationOutputTokenLimit=coordinationMaxOutputTokens,coordinationPromptCharLimit=coordinationMaxPromptChars,
            executionMode=paperExecutionMode.ToString(),availabilityMode=coordinationAvailability.ToString(),
            dispatcher=paperExecutionMode==Coordination.ExecutionMode.PaperReference ? "paper-adjacent-random" : paperExecutionMode==Coordination.ExecutionMode.LLMExtension ? Coordination.LLMDispatchProtocol.Version : paperExecutionMode==Coordination.ExecutionMode.OptimizedExtension ? Coordination.OptimalDispatcher.Version : Coordination.LocalDispatcher.Version,
            reservationIdleSteps=coordinationIdleSteps,reservationCooldownSteps=coordinationCooldownSteps,
            paperPromptVersion = LLMDecisionPolicy.PaperPromptVersion,personalResponseVersion=PersonalDecisionProtocol.Version,
            paperPromptTemplateSHA256 = PaperVolunteerPrompt.Hash(agentInformation.ToString(),agentPromptWording),
            decisionRandomAlgorithm = obstacleHandlingMode==ObstacleHandlingMode.PaperRelocation ? DecisionRandomStream.Version : "Unity-shared-legacy",
            decisionSeed = DecisionRandomStream.SeedForRun(unchecked(baseSeed + activeRunID - 1)),
            observationScope = agentInformation.ToString(),promptWording=agentPromptWording.ToString(),
            coordinationStudyCell=coordinationStudyJob?.cellId??"",coordinationStudyGroup=coordinationStudyJob?.groupId??"",coordinationStudyJob=coordinationStudyJob?.jobID??"",
            researchPhase = agentResearchPhase.ToString(),conditionKey = AgentConditionKey,studyPlanID=string.IsNullOrEmpty(closedLoopStudyPlanID)?lockedStudyPlanID:closedLoopStudyPlanID,experimentPurpose=AutomaticPurpose,
            calibrationID = cooperationCalibration!=null ? cooperationCalibration.calibrationID : "",
            calibratedProbability = cooperationCalibration!=null ? cooperationCalibration.probability : -1f,
            maxAgentRequestsPerRun = maxAgentRequestsPerRun,
            decisionExecution = string.IsNullOrEmpty(paperDecisionReplayPath) ? "live" : "strict_replay",
            width = world.width, height = world.height, requestedAgents = agentCount,
            actualAgents = agentManager.GetAgentCount(), requestedObstacles = obstacleCount,
            actualObstacles = world.GetObstaclePositions().Count, maxSteps = maxSimulationSteps,
            visibilityRange = obstacleVisibilityRange, actionRange = EffectiveVolunteerActionRange,
            selectionInterval = obstacleHandlingMode==ObstacleHandlingMode.PaperRelocation || volunteerDecisionMode == VolunteerDecisionMode.OriginalGameTheory ? 1 : volunteerSelectionInterval, maxRequestsPerStep = obstacleHandlingMode==ObstacleHandlingMode.PaperRelocation ? 0 : maxLLMRequestsPerStep,
            approachDepth = exitApproachDepth, spawnWidth = agentSpawnAreaSize.x, spawnHeight = agentSpawnAreaSize.y,
            removalWorkSteps = obstacleRemovalWorkSteps,
            exitWidth = researchExitWidth,requestedExitCount=exitCount,actualExitCount=ResearchEnvironment.CountExitGroups(world), hasApiKey = !string.IsNullOrEmpty(openAIKey),
            allowMockFallback = allowMockFallback && obstacleHandlingMode==ObstacleHandlingMode.LegacyClearance, llmAssignment = useLLMAssignment && obstacleHandlingMode == ObstacleHandlingMode.LegacyClearance,
            stepInterval = stepInterval, kStatic = kStatic, kDynamic = kDynamic, kAnticipation = kAnticipation,
            temperature = movementTemperature, volunteerCost = volunteerCost, failureCost = failureCost,
            omega = unwillingnessOmega, dffDecay = dynamicFloorField.decayRate,
            dffDiffusion = dynamicFloorField.diffusionRate, anticipationRadius = anticipationFloorField.influenceRadius,
            defectionCost = yielderDefectionCost, friction = yielderFriction
        };
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

        if (timeSinceLastStep >= stepInterval)
        {
            timeSinceLastStep -= stepInterval;
            StartCoroutine(SimulationStepCoroutine());
        }

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

        if(world.paperNeighborhood)
        {
            var available=closedLoopInitialState==null ? new List<Vector2Int>() : new List<Vector2Int>(closedLoopInitialState.agentCells);
            if(closedLoopInitialState==null)for(int x=Mathf.Max(1,startX);x<Mathf.Min(world.width-1,endX);x++)
            for(int y=Mathf.Max(1,startY);y<Mathf.Min(world.height-1,endY);y++)
                if(world.IsWalkable(x,y)) available.Add(new Vector2Int(x,y));
            int count=Mathf.Min(agentCount,available.Count);
            for(int i=0;i<count;i++)
            {
                int selected=closedLoopInitialState==null?Random.Range(i,available.Count):i;var cell=available[selected];
                available[selected]=available[i];available[i]=cell;
                var agent=agentManager.SpawnAgent(cell);
                agent.SetVolunteerState(PedestrianAgent.VolunteerState.None);agent.SetFloorField(floorField);
                agent.SetDynamicField(dynamicFloorField);agent.SetAnticipationField(anticipationFloorField);
                agent.SetPathfinder(pathfinder);agent.SetMovementStrategy(movementStrategy);
                agent.SetMovementCoefficients(kStatic,kDynamic,kAnticipation,movementTemperature);
                agent.SetVolunteerActionRange(1);
            }
            if(count<agentCount) Debug.LogWarning("Requested crowd exceeds available spawn cells; actual count is exported.");
            return;
        }

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
            agent.SetVolunteerActionRange(EffectiveVolunteerActionRange);
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
        if(closedLoopZeroStepValidation)throw new System.InvalidOperationException("Zero-step final validation cannot simulate or call a model");
        isStepInProgress = true;
        yield return ExecuteSimulationStep();
        isStepInProgress = false;
        CheckSimulationComplete();
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
        if(activeResearchLocked && activeAgentSettings!=AgentSettingsIdentity)
        {
            simulationRunning=false;ExportFinishedRun("invalid_settings_changed");yield break;
        }
        currentStep++;
        elapsedTime = currentStep * stepInterval;
        llmRequestsThisStep = 0;

        if (agentManager == null || agentManager.GetAgentCount() == 0)
        {
            Debug.Log("No agents to simulate");
            yield break;
        }

        int conflictCount=0, volunteerActionsThisStep=0;
        if(paperModel!=null)
        {
            if(volunteerDecisionMode==VolunteerDecisionMode.LLM) floorField.Recompute();
            yield return paperModel.PrepareStep(currentStep,simulationData);
            if(!simulationRunning) yield break;
            conflictCount=paperModel.Conflicts; volunteerActionsThisStep=paperModel.Manipulations;
        }
        else
        {
        yield return UpdateDynamicVolunteerStatesCoroutine();
        if (!simulationRunning) yield break;
        anticipationFloorField.UpdateField(agentManager.GetAgents());

        var occupied = new HashSet<Vector2Int>();
        foreach (var agent in agentManager.GetAgents())
            if (!agent.IsEvacuated()) occupied.Add(agent.gridPos);

        foreach (PedestrianAgent agent in agentManager.GetAgents())
        {
            if (!agent.IsEvacuated())
            {
                agent.SetOccupancy(occupied);
                agent.ProposeMove();
            }
        }

        conflictCount = ResolveMovementConflicts();

        yield return ExecuteVolunteerActionsCoroutine(value => volunteerActionsThisStep = value);

        }

        foreach (PedestrianAgent agent in agentManager.GetAgents())
        {
            if (!agent.IsEvacuated())
            {
                agent.CommitMove();
            }
            if (agent.IsEvacuated() && agent.evacuationStep == -1)
            {
                agent.evacuationStep = currentStep;
                simulationData.RecordAgentEvacuation(agent.AgentID, currentStep, elapsedTime);
            }
            if (!agent.IsEvacuated() || agent.evacuationStep == currentStep)
                simulationData.RecordPosition(currentStep, agent.AgentID, agent.gridPos, agent.GetVolunteerState().ToString(), agent.IsEvacuated());
        }

        paperModel?.AfterCommit(currentStep,simulationData);
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
        int obstaclesRemaining = paperModel!=null ? paperModel.UnsettledCount : world.GetObstaclePositions().Count;
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
        return MovementConflictResolver.Resolve(agentManager.GetAgents(), yielderGame);
    }

    private IEnumerator DecidePaperVolunteer(PedestrianAgent agent,PaperObstacle obstacle,VolunteerDecisionContext context,
        System.Action<bool?,string,string> callback)
    {
        string source="game_theory", explanation="", failure="";
        bool willing=false;
        if(volunteerDecisionMode!=VolunteerDecisionMode.LLM)
        {
            source=volunteerDecisionMode==VolunteerDecisionMode.MockHeuristic ? "heuristic" :
                volunteerDecisionMode==VolunteerDecisionMode.RandomMatched ? "random_matched" : "game_theory";
            willing=volunteerDecisionStrategy.ShouldVolunteer(context);
        }
        else
        {
            string observation=AgentObservation.Serialize(context,agentInformation);
            string replayError;
            if(!PaperDecisionSpecification.HasValidCosts(context.volunteerCost,context.failureCost,context.unwillingness))
            {
                failure="invalid_game_payoffs";
                explanation="Paper decisions require 0 < volunteerCost < failureCost < 1 and finite omega >= 0. Apply the paper reference parameters.";
            }
            else if (!string.IsNullOrEmpty(paperDecisionReplayPath))
            {
                if (paperDecisionJournal.TryReplay(paperDecisionReplayPath,currentStep,agent.AgentID,obstacle.id,
                    observation,out willing,out explanation,out replayError,AgentConditionKey,openAIModel,PaperVolunteerPrompt.Hash(agentInformation.ToString(),agentPromptWording),
                    PersonalDecisionProtocol.Payload(openAIModel,observation,agentInformation.ToString(),agentPromptWording))) source="replay";
                else { failure="replay_mismatch"; explanation=replayError; }
            }
            else if(string.IsNullOrEmpty(openAIKey)) failure="missing_api_key";
            else if(maxAgentRequestsPerRun>0 && individualPaperRequestsThisRun>=maxAgentRequestsPerRun) failure="run_request_limit";
            else
            {
                // API latency pauses this CA step; request caps never exclude candidates.
                closedLoopBeforeApiRequest?.Invoke();
                llmRequestsThisStep++; individualPaperRequestsThisRun++; source="api";
                var llmContext=new LLMDecisionPolicy.VolunteerContext { sharedObservationJson=observation,informationCondition=agentInformation.ToString(),promptWording=agentPromptWording,agentId=agent.AgentID };
                var clock=System.Diagnostics.Stopwatch.StartNew();
                yield return llmDecisionPolicy.RequestVolunteerDecision(llmContext,(level,reason)=>{
                    willing=level!=VolunteerDilemma.CooperationLevel.Selfish; explanation=reason;
                });
                clock.Stop();
                source=llmDecisionPolicy.LastExecution=="synthetic_test"?"synthetic_test":"api";
                if(source=="api")llmApiDecisionCallsThisRun++;
                if(!llmDecisionPolicy.LastRequestSucceeded) failure=string.IsNullOrEmpty(llmDecisionPolicy.LastRequestError)?"api_failure":llmDecisionPolicy.LastRequestError;
                if(closedLoopInitialState!=null && llmDecisionPolicy.LastRequestSucceeded && !ClosedLoopStudyGuard.MatchesProvider(llmDecisionPolicy.LastResponse,openAIModel))failure="provider_model_drift";
                paperDecisionJournal.Record(simulationData.DecisionTracePath,currentStep,agent.AgentID,obstacle.id,
                    observation,willing,explanation,llmDecisionPolicy.LastRequestSucceeded && failure.Length==0,openAIModel,
                    llmDecisionPolicy.LastPayload,llmDecisionPolicy.LastResponse,llmDecisionPolicy.LastAttempts,clock.Elapsed.TotalSeconds,AgentConditionKey,
                    failure.Length>0?failure:llmDecisionPolicy.LastRequestError,PaperVolunteerPrompt.Hash(agentInformation.ToString(),agentPromptWording),
                    llmDecisionPolicy.LastExecution,llmDecisionPolicy.LastHttpStatus,llmDecisionPolicy.LastAttemptAudit);
            }
            if(failure.Length>0)
            {
                // Research comparisons never mix API decisions with heuristic substitutions.
                Debug.LogWarning($"[LLM-ERROR] step={currentStep} agent={agent.AgentID} obstacle={obstacle.id} model={openAIModel} source={source} error={failure} | reason={explanation}");
                simulationData.RecordLLMDecision(currentStep,agent.AgentID,"error",explanation,"error",failure);
                simulationRunning=false; ExportFinishedRun("invalid_llm_"+failure);
                callback(null,failure,"error"); yield break;
            }
        }
        if(volunteerDecisionMode==VolunteerDecisionMode.LLM && !willing)
            Debug.Log($"[LLM-DECLINED] step={currentStep} agent={agent.AgentID} obstacle={obstacle.id} model={openAIModel} source={source} X={context.nearbyAgentCount} tau={context.exitNonBlockage} | reason={(string.IsNullOrWhiteSpace(explanation)?"<empty explanation>":explanation)}");
        simulationData.RecordLLMDecision(currentStep,agent.AgentID,willing ? "volunteer" : "selfish",explanation,source,failure);
        callback(willing,explanation,source);
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

            if (dist <= EffectiveVolunteerActionRange)
            {
                obstacleWorkProgress.TryGetValue(obstacleId, out int work);
                work++;
                obstacleWorkProgress[obstacleId] = work;
                simulationData.RecordVolunteerWork(currentStep, volunteer.AgentID, obstacleId, work,
                    work >= Mathf.Max(1, obstacleRemovalWorkSteps));
                if (work < Mathf.Max(1, obstacleRemovalWorkSteps)) continue;
                if (!processedObstacles.Contains(obstacleId))
                {
                    processedObstacles.Add(obstacleId);
                    volunteerActionCount++;
                    volunteerDilemma.ExecuteVolunteerActionAtObstacle(volunteer, VolunteerDilemma.CooperationLevel.Cooperative, targetObstacle);
                    floorField.Recompute();
                    if (volunteerDecisionMode == VolunteerDecisionMode.LLM)
                    {
                        simulationData.RecordLLMDecision(currentStep, volunteer.AgentID, "volunteer", "assigned volunteer cleared obstacle", "action");
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
        // Clear completed/stale assignments every step, not just selection steps.
        CleanupInvalidVolunteerAssignments(allAgents, obstacleMap);
        // A visible obstacle at an otherwise open exit does not trigger a
        // volunteer game, but it must still enter the evacuee's bypass field.
        // Otherwise the base SFF keeps attracting the last pedestrian into a
        // local minimum behind an ordinary, visible obstacle.
        foreach (var agent in allAgents)
        {
            if (agent.IsEvacuated() || agent.GetVolunteerState() != PedestrianAgent.VolunteerState.None) continue;
            foreach (var obstacle in obstacles)
                if (Mathf.Abs(agent.gridPos.x - obstacle.x) + Mathf.Abs(agent.gridPos.y - obstacle.y) <= obstacleVisibilityRange
                    && ResearchEnvironment.ExitNonBlockage(world, obstacle, exitApproachDepth) >= 1f)
                    agent.RememberRejectedObstacle(obstacle);
        }

        if (volunteerDecisionMode == VolunteerDecisionMode.NoVolunteers || obstacles.Count == 0 || volunteerDecisionStrategy == null)
        {
            foreach (PedestrianAgent agent in allAgents)
            {
                if (!agent.IsEvacuated())
                {
                    agent.SetVolunteerState(PedestrianAgent.VolunteerState.None);
                    if (volunteerDecisionMode == VolunteerDecisionMode.NoVolunteers)
                        foreach (var obstacle in obstacles)
                            if (Mathf.Abs(agent.gridPos.x - obstacle.x) + Mathf.Abs(agent.gridPos.y - obstacle.y) <= obstacleVisibilityRange)
                                agent.RememberRejectedObstacle(obstacle);
                }
            }
            yield break;
        }

        if (volunteerDecisionMode != VolunteerDecisionMode.OriginalGameTheory && !ShouldRunVolunteerSelectionThisStep())
        {
            CleanupInvalidVolunteerAssignments(allAgents, obstacleMap);
            yield break;
        }

        List<PedestrianAgent> potentialVolunteers = new List<PedestrianAgent>();
        var eligibleCountByObstacle = new Dictionary<int, int>();
        var reservedObstacles = new HashSet<int>();
        foreach (var agent in allAgents)
            if (!agent.IsEvacuated() && agent.HasAssignedObstacle()) reservedObstacles.Add(agent.GetAssignedObstacleId());
        foreach (var entry in obstacleMap)
            eligibleCountByObstacle[entry.Key] = agentManager.GetAgentsNearPosition(entry.Value, obstacleVisibilityRange)
                .FindAll(a => a.GetVolunteerState() == PedestrianAgent.VolunteerState.None).Count;

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
            // Paper Stage 1: play only when this obstacle's Lv is empty.
            if (reservedObstacles.Contains(nearestObstacleId)) continue;

            int nearbyAgentCount = eligibleCountByObstacle[nearestObstacleId];
            float exitNonBlockage = ResearchEnvironment.ExitNonBlockage(world, nearestObstacle, exitApproachDepth);
            float blockageRatio = 1f - exitNonBlockage;
            if (exitNonBlockage >= 1f) continue;
            int currentVolunteerCount = potentialVolunteers.Count;

            VolunteerDecisionContext context = new VolunteerDecisionContext
            {
                nearbyAgentCount = nearbyAgentCount,
                exitNonBlockage = exitNonBlockage,
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
            string explanation = "";
            string source = volunteerDecisionMode == VolunteerDecisionMode.MockHeuristic ? "heuristic" : "game_theory";
            string fallbackReason = "";
            if (volunteerDecisionMode == VolunteerDecisionMode.LLM)
            {
                if (string.IsNullOrEmpty(openAIKey)) fallbackReason = "missing_api_key";
                else if (llmRequestsThisStep >= Mathf.Max(1, maxLLMRequestsPerStep))
                {
                    if (!allowMockFallback)
                    {
                        simulationData.RecordLLMDecision(currentStep, agent.AgentID, "deferred", "request budget reached", "budget");
                        continue;
                    }
                    fallbackReason = "request_cap";
                }
                else
                {
                    llmRequestsThisStep++;
                    llmApiDecisionCallsThisRun++;
                    source = "api";
                    VolunteerDilemma.CooperationLevel level = VolunteerDilemma.CooperationLevel.Selfish;
                    float obstacleToExitDist = GetObstacleDistanceToNearestExit(nearestObstacle);
                    int evacueesNearObstacle = CountEvacueesNearPosition(nearestObstacle, obstacleVisibilityRange);
                    float impact = EstimateEvacuationImpactScore(obstacleToExitDist, evacueesNearObstacle);
                    yield return volunteerDilemma.DecideVolunteerActionAsync(agent, nearestObstacle, obstacleToExitDist,
                        evacueesNearObstacle, impact, (result, reason) => { level = result; explanation = reason; });
                    shouldVolunteer = level != VolunteerDilemma.CooperationLevel.Selfish;
                    if (!llmDecisionPolicy.LastRequestSucceeded) fallbackReason = "api_failure";
                }
                if (fallbackReason.Length > 0)
                {
                    if (!allowMockFallback)
                    {
                        simulationData.RecordLLMDecision(currentStep, agent.AgentID, "error", explanation, "error", fallbackReason);
                        simulationRunning = false;
                        ExportFinishedRun("invalid_llm_" + fallbackReason);
                        yield break;
                    }
                    source = "mock";
                    llmMockFallbackCallsThisRun++;
                    shouldVolunteer = new MockLLMVolunteerStrategy().ShouldVolunteer(context);
                }
            }
            else shouldVolunteer = volunteerDecisionStrategy.ShouldVolunteer(context);

            simulationData.RecordLLMDecision(currentStep, agent.AgentID,
                shouldVolunteer ? "volunteer" : "selfish", explanation, source, fallbackReason);
            if (!shouldVolunteer) agent.RememberRejectedObstacle(nearestObstacle);

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
            if (useLLMAssignment && volunteerDecisionMode == VolunteerDecisionMode.LLM && !string.IsNullOrEmpty(openAIKey) && llmRequestsThisStep < Mathf.Max(1, maxLLMRequestsPerStep))
            {
                llmRequestsThisStep++;
                llmApiDecisionCallsThisRun++;
                yield return RequestLLMAssignment(candidatesByObstacle, unassignedObstacles, assignments);
            }

            if (assignments.Count == 0)
            {
                if (volunteerDecisionMode == VolunteerDecisionMode.OriginalGameTheory)
                    BuildAdjacentPaperAssignment(candidatesByObstacle, unassignedObstacles, assignments);
                else BuildGreedyAssignment(candidatesByObstacle, unassignedObstacles, assignments);
            }

            Dictionary<int, PedestrianAgent> candidateById = new Dictionary<int, PedestrianAgent>();
            foreach (PedestrianAgent candidate in potentialVolunteers)
            {
                candidateById[candidate.AgentID] = candidate;
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
                int candidateId = candidate.AgentID;
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
                int bestAgentId = bestAgent.AgentID;
                usedAgentIds.Add(bestAgentId);
                assignments[obstacleId] = bestAgentId;
            }
        }
    }

    private void BuildAdjacentPaperAssignment(Dictionary<int, List<PedestrianAgent>> candidatesByObstacle,
        Dictionary<int, Vector2Int> obstacles, Dictionary<int, int> assignments)
    {
        foreach (var entry in candidatesByObstacle)
        {
            var target = obstacles[entry.Key];
            var adjacent = entry.Value.FindAll(agent => !agent.IsEvacuated() && !agent.IsActiveVolunteer() &&
                Mathf.Abs(agent.gridPos.x - target.x) + Mathf.Abs(agent.gridPos.y - target.y) == 1);
            // Paper p.2 Stage 2: activate a randomly chosen ADJACENT candidate.
            // Never reserve an obstacle for a remote volunteer who may be blocked
            // by the other candidates already waiting beside it.
            if (adjacent.Count > 0) assignments[entry.Key] = adjacent[Random.Range(0, adjacent.Count)].AgentID;
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
                int candidateId = candidate.AgentID;
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
            int id = c.AgentID;
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
                int agentId = candidate.AgentID;
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
        if (!simulationRunning) return;
        int totalAgents = agentManager.GetAgentCount();
        int evacuatedCount = agentManager.GetEvacuatedCount();

        if (totalAgents == 0)
        {
            simulationRunning = false;
            ExportFinishedRun("invalid_no_agents");
            return;
        }
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
            
            ExportFinishedRun("completed");
        }
        else if (maxSimulationSteps > 0 && currentStep >= maxSimulationSteps && simulationRunning)
        {
            simulationRunning = false;
            ExportFinishedRun("timeout");
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


    private void ExportFinishedRun(string reason)
    {
        if (runExported || simulationData == null) return;
        if(activeResearchLocked && activeAgentSettings!=AgentSettingsIdentity) reason="invalid_settings_changed";
        if(!string.IsNullOrEmpty(paperDecisionReplayPath) && (reason=="completed" || reason=="timeout") &&
            !paperDecisionJournal.ReplayFullyConsumed(paperDecisionReplayPath)) reason="invalid_replay_unused_entries";
        if((reason=="completed" || reason=="timeout") && coordinationSession!=null && !coordinationSession.ReplayFullyConsumed)
            reason="invalid_coordination_replay_unused_entries";
        currentTermination = reason;
        runClock.Stop();
        simulationData.SetRuntimeMetrics(runClock.Elapsed.TotalSeconds, llmApiDecisionCallsThisRun, llmMockFallbackCallsThisRun);
        simulationData.SetTermination(reason);
        simulationData.SetSimulationStats(currentStep, elapsedTime);
        simulationData.ExportData();
        runExported = true;
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

    public string GetRunStateLabel()
    {
        if(simulationRunning) return isPaused ? "Paused" : "Running";
        if(currentTermination.StartsWith("invalid_llm_")) return "LLM error (see Console)";
        if(currentTermination.StartsWith("invalid_")) return "Invalid (see Console)";
        if(currentTermination=="completed") return "Completed";
        if(currentTermination=="timeout") return "Timed out";
        return "Stopped";
    }

    public int GetEvacueeCount()
    {
        return agentManager != null ? agentManager.GetAgentsByRole(PedestrianAgent.Role.Evacuee).Count : 0;
    }

    public int GetObstacleCount()
    {
        return paperModel!=null ? paperModel.UnsettledCount : (world != null ? world.GetObstaclePositions().Count : 0);
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

    private void RecordInterruptedRun(string reason)
    {
        if(recordExperimentsAutomatically && simulationData!=null && !runExported)
            ExportFinishedRun(reason);
    }
    void OnApplicationQuit() {RecordInterruptedRun("interrupted_application_exit");}
    void OnDestroy() {RecordInterruptedRun("interrupted_scene_unload");}

    public void ResetSimulation()
    {
        RecordInterruptedRun("interrupted_manual_reset");
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
