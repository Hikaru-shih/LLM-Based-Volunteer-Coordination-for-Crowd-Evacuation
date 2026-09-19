using UnityEngine;
using UnityEngine.UI;
using TMPro;
using Decision;

public class MainMenuSettingsController : MonoBehaviour
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

    [Header("Input Objects (Legacy InputField or TMP_InputField)")]
    public GameObject batchRunCountInput;
    public GameObject gridWidthInput;
    public GameObject gridHeightInput;
    public GameObject agentCountInput;
    public GameObject agentSpawnAreaWidthInput;
    public GameObject agentSpawnAreaHeightInput;
    public GameObject obstacleCountInput;
    public GameObject volunteerCountInput;
    public GameObject stepIntervalInput;
    public GameObject volunteerSelectionIntervalInput;
    public GameObject obstacleVisibilityRangeInput;
    public GameObject obstacleActionRangeInput;
    public GameObject maxLlmRequestsPerStepInput;
    public GameObject volunteerCostInput;
    public GameObject failureCostInput;
    public GameObject unwillingnessOmegaInput;
    public GameObject kStaticInput;
    public GameObject kDynamicInput;
    public GameObject kAnticipationInput;
    public GameObject temperatureInput;
    public GameObject openAiModelInput;
    public GameObject openAiKeyInput;
    public GameObject ninetyPercentFallbackStepsInput;

    [Header("Dropdown Objects (Legacy Dropdown or TMP_Dropdown)")]
    public GameObject volunteerDecisionModeDropdown;
    public GameObject movementStrategyDropdown;
    public GameObject conflictStrategyDropdown;

    [Header("Toggle Object")]
    public GameObject debugLlmDecisionFlowToggle;

    [Header("Defaults")]
    public int defaultBatchRunCount = 1;
    public int defaultGridWidth = 30;
    public int defaultGridHeight = 30;
    public int defaultAgentCount = 50;
    public int defaultAgentSpawnAreaWidth = 15;
    public int defaultAgentSpawnAreaHeight = 15;
    public int defaultObstacleCount = 40;
    public int defaultVolunteerCount = 5;
    public float defaultStepInterval = 0.30f;
    public int defaultVolunteerSelectionInterval = 6;
    public int defaultObstacleVisibilityRange = 5;
    public int defaultObstacleActionRange = 2;
    public int defaultMaxLlmRequestsPerStep = 3;
    public float defaultVolunteerCost = 1.0f;
    public float defaultFailureCost = 2.0f;
    public float defaultUnwillingnessOmega = 1.0f;
    public float defaultKStatic = 1.0f;
    public float defaultKDynamic = 1.0f;
    public float defaultKAnticipation = 1.0f;
    public float defaultTemperature = 1.0f;
    public string defaultOpenAiModel = "gpt-4.1";

    public bool defaultDebugLlmDecisionFlow = true;
    public int defaultNinetyPercentFallbackSteps = 150;

    void Start()
    {
        InitializeDropdownOptions();
        LoadToUI();
    }

    public void ApplySettings()
    {
        SaveInt(batchRunCountInput, BatchRunCountKey);
        SaveInt(gridWidthInput, GridWidthKey);
        SaveInt(gridHeightInput, GridHeightKey);
        SaveInt(agentCountInput, AgentCountKey);
        SaveInt(agentSpawnAreaWidthInput, AgentSpawnAreaWidthKey);
        SaveInt(agentSpawnAreaHeightInput, AgentSpawnAreaHeightKey);
        SaveInt(obstacleCountInput, ObstacleCountKey);
        SaveInt(volunteerCountInput, VolunteerCountKey);
        SaveInt(volunteerSelectionIntervalInput, VolunteerSelectionIntervalKey);
        SaveInt(obstacleVisibilityRangeInput, ObstacleVisibilityRangeKey);
        SaveInt(obstacleActionRangeInput, ObstacleActionRangeKey);
        SaveInt(maxLlmRequestsPerStepInput, MaxLlmRequestsPerStepKey);
        SaveInt(ninetyPercentFallbackStepsInput, NinetyPercentFallbackStepsKey);

        SaveFloat(stepIntervalInput, StepIntervalKey);
        SaveFloat(volunteerCostInput, VolunteerCostKey);
        SaveFloat(failureCostInput, FailureCostKey);
        SaveFloat(unwillingnessOmegaInput, UnwillingnessOmegaKey);
        SaveFloat(kStaticInput, KStaticKey);
        SaveFloat(kDynamicInput, KDynamicKey);
        SaveFloat(kAnticipationInput, KAnticipationKey);
        SaveFloat(temperatureInput, TemperatureKey);

        SaveString(openAiModelInput, OpenAiModelKey);
        if (openAiKeyInput != null) LocalOpenAIKey.Save(GetInputText(openAiKeyInput));

        SaveDropdownValue(volunteerDecisionModeDropdown, VolunteerDecisionModeKey);
        SaveDropdownValue(movementStrategyDropdown, MovementStrategyKey);
        SaveDropdownValue(conflictStrategyDropdown, ConflictStrategyKey);

        SaveToggleValue(debugLlmDecisionFlowToggle, DebugLlmDecisionFlowKey);

        PlayerPrefs.Save();
        Debug.Log("Main menu settings saved.");
    }

    private void LoadToUI()
    {
        SetText(batchRunCountInput, PlayerPrefs.GetInt(BatchRunCountKey, defaultBatchRunCount).ToString());
        SetText(gridWidthInput, PlayerPrefs.GetInt(GridWidthKey, defaultGridWidth).ToString());
        SetText(gridHeightInput, PlayerPrefs.GetInt(GridHeightKey, defaultGridHeight).ToString());
        SetText(agentCountInput, PlayerPrefs.GetInt(AgentCountKey, defaultAgentCount).ToString());
        SetText(agentSpawnAreaWidthInput, PlayerPrefs.GetInt(AgentSpawnAreaWidthKey, defaultAgentSpawnAreaWidth).ToString());
        SetText(agentSpawnAreaHeightInput, PlayerPrefs.GetInt(AgentSpawnAreaHeightKey, defaultAgentSpawnAreaHeight).ToString());
        SetText(obstacleCountInput, PlayerPrefs.GetInt(ObstacleCountKey, defaultObstacleCount).ToString());
        SetText(volunteerCountInput, PlayerPrefs.GetInt(VolunteerCountKey, defaultVolunteerCount).ToString());
        SetText(volunteerSelectionIntervalInput, PlayerPrefs.GetInt(VolunteerSelectionIntervalKey, defaultVolunteerSelectionInterval).ToString());
        SetText(obstacleVisibilityRangeInput, PlayerPrefs.GetInt(ObstacleVisibilityRangeKey, defaultObstacleVisibilityRange).ToString());
        SetText(obstacleActionRangeInput, PlayerPrefs.GetInt(ObstacleActionRangeKey, defaultObstacleActionRange).ToString());
        SetText(maxLlmRequestsPerStepInput, PlayerPrefs.GetInt(MaxLlmRequestsPerStepKey, defaultMaxLlmRequestsPerStep).ToString());
        SetText(ninetyPercentFallbackStepsInput, PlayerPrefs.GetInt(NinetyPercentFallbackStepsKey, defaultNinetyPercentFallbackSteps).ToString());

        SetText(stepIntervalInput, PlayerPrefs.GetFloat(StepIntervalKey, defaultStepInterval).ToString("F2"));
        SetText(volunteerCostInput, PlayerPrefs.GetFloat(VolunteerCostKey, defaultVolunteerCost).ToString("F2"));
        SetText(failureCostInput, PlayerPrefs.GetFloat(FailureCostKey, defaultFailureCost).ToString("F2"));
        SetText(unwillingnessOmegaInput, PlayerPrefs.GetFloat(UnwillingnessOmegaKey, defaultUnwillingnessOmega).ToString("F2"));
        SetText(kStaticInput, PlayerPrefs.GetFloat(KStaticKey, defaultKStatic).ToString("F2"));
        SetText(kDynamicInput, PlayerPrefs.GetFloat(KDynamicKey, defaultKDynamic).ToString("F2"));
        SetText(kAnticipationInput, PlayerPrefs.GetFloat(KAnticipationKey, defaultKAnticipation).ToString("F2"));
        SetText(temperatureInput, PlayerPrefs.GetFloat(TemperatureKey, defaultTemperature).ToString("F2"));

        SetText(openAiModelInput, PlayerPrefs.GetString(OpenAiModelKey, defaultOpenAiModel));
        SetText(openAiKeyInput, LocalOpenAIKey.Load());

        SetDropdownValue(volunteerDecisionModeDropdown, PlayerPrefs.GetInt(VolunteerDecisionModeKey, GetDropdownValue(volunteerDecisionModeDropdown, 0)));
        SetDropdownValue(movementStrategyDropdown, PlayerPrefs.GetInt(MovementStrategyKey, GetDropdownValue(movementStrategyDropdown, 0)));
        SetDropdownValue(conflictStrategyDropdown, PlayerPrefs.GetInt(ConflictStrategyKey, GetDropdownValue(conflictStrategyDropdown, 0)));

        SetToggleValue(debugLlmDecisionFlowToggle, PlayerPrefs.GetInt(DebugLlmDecisionFlowKey, defaultDebugLlmDecisionFlow ? 1 : 0) == 1);
    }

    private void InitializeDropdownOptions()
    {
        SetDropdownOptionsIfEmpty(
            volunteerDecisionModeDropdown,
            new System.Collections.Generic.List<string>
            {
                SimulationManager.VolunteerDecisionMode.OriginalGameTheory.ToString(),
                SimulationManager.VolunteerDecisionMode.LLM.ToString()
            });

        System.Collections.Generic.List<string> movementOptions = new System.Collections.Generic.List<string>();
        foreach (PedestrianAgent.MovementStrategy strategy in System.Enum.GetValues(typeof(PedestrianAgent.MovementStrategy)))
        {
            movementOptions.Add(strategy.ToString());
        }
        SetDropdownOptionsIfEmpty(movementStrategyDropdown, movementOptions);

        System.Collections.Generic.List<string> conflictOptions = new System.Collections.Generic.List<string>();
        foreach (YielderGame.Strategy strategy in System.Enum.GetValues(typeof(YielderGame.Strategy)))
        {
            conflictOptions.Add(strategy.ToString());
        }
        SetDropdownOptionsIfEmpty(conflictStrategyDropdown, conflictOptions);
    }

    private static void SetText(GameObject inputObject, string value)
    {
        if (inputObject == null)
            return;

        InputField legacy = inputObject.GetComponent<InputField>();
        if (legacy != null)
        {
            legacy.text = value;
            return;
        }

        TMP_InputField tmp = inputObject.GetComponent<TMP_InputField>();
        if (tmp != null)
        {
            tmp.text = value;
        }
    }

    private static string GetInputText(GameObject inputObject)
    {
        if (inputObject == null)
            return null;

        InputField legacy = inputObject.GetComponent<InputField>();
        if (legacy != null)
            return legacy.text;

        TMP_InputField tmp = inputObject.GetComponent<TMP_InputField>();
        if (tmp != null)
            return tmp.text;

        return null;
    }

    private static void SaveInt(GameObject inputObject, string key)
    {
        string text = GetInputText(inputObject);
        if (string.IsNullOrWhiteSpace(text))
            return;

        if (int.TryParse(text, out int parsed))
            PlayerPrefs.SetInt(key, parsed);
    }

    private static void SaveFloat(GameObject inputObject, string key)
    {
        string text = GetInputText(inputObject);
        if (string.IsNullOrWhiteSpace(text))
            return;

        if (float.TryParse(text, out float parsed))
            PlayerPrefs.SetFloat(key, parsed);
    }

    private static void SaveString(GameObject inputObject, string key)
    {
        string text = GetInputText(inputObject);
        if (text == null)
            return;

        PlayerPrefs.SetString(key, text);
    }

    private static void SaveDropdownValue(GameObject dropdownObject, string key)
    {
        if (dropdownObject == null)
            return;

        PlayerPrefs.SetInt(key, GetDropdownValue(dropdownObject, 0));
    }

    private static int GetDropdownValue(GameObject dropdownObject, int fallback)
    {
        if (dropdownObject == null)
            return fallback;

        Dropdown legacy = dropdownObject.GetComponent<Dropdown>();
        if (legacy != null)
            return legacy.value;

        TMP_Dropdown tmp = dropdownObject.GetComponent<TMP_Dropdown>();
        if (tmp != null)
            return tmp.value;

        return fallback;
    }

    private static void SetDropdownValue(GameObject dropdownObject, int value)
    {
        if (dropdownObject == null)
            return;

        Dropdown legacy = dropdownObject.GetComponent<Dropdown>();
        if (legacy != null)
        {
            if (legacy.options != null && legacy.options.Count > 0)
                legacy.value = Mathf.Clamp(value, 0, legacy.options.Count - 1);
            return;
        }

        TMP_Dropdown tmp = dropdownObject.GetComponent<TMP_Dropdown>();
        if (tmp != null && tmp.options != null && tmp.options.Count > 0)
        {
            tmp.value = Mathf.Clamp(value, 0, tmp.options.Count - 1);
        }
    }

    private static void SetDropdownOptionsIfEmpty(GameObject dropdownObject, System.Collections.Generic.List<string> options)
    {
        if (dropdownObject == null || options == null)
            return;

        Dropdown legacy = dropdownObject.GetComponent<Dropdown>();
        if (legacy != null)
        {
            if (legacy.options == null || legacy.options.Count == 0 || IsPlaceholderOptionsLegacy(legacy.options))
            {
                legacy.ClearOptions();
                legacy.AddOptions(options);
            }
            return;
        }

        TMP_Dropdown tmp = dropdownObject.GetComponent<TMP_Dropdown>();
        if (tmp != null && (tmp.options == null || tmp.options.Count == 0 || IsPlaceholderOptionsTmp(tmp.options)))
        {
            tmp.ClearOptions();
            tmp.AddOptions(options);
        }
    }

    private static bool IsPlaceholderOptionsLegacy(System.Collections.Generic.List<Dropdown.OptionData> options)
    {
        if (options == null || options.Count == 0)
            return false;

        int placeholders = 0;
        for (int i = 0; i < options.Count; i++)
        {
            string text = options[i] != null ? options[i].text : string.Empty;
            if (IsPlaceholderText(text))
                placeholders++;
        }

        return placeholders == options.Count;
    }

    private static bool IsPlaceholderOptionsTmp(System.Collections.Generic.List<TMP_Dropdown.OptionData> options)
    {
        if (options == null || options.Count == 0)
            return false;

        int placeholders = 0;
        for (int i = 0; i < options.Count; i++)
        {
            string text = options[i] != null ? options[i].text : string.Empty;
            if (IsPlaceholderText(text))
                placeholders++;
        }

        return placeholders == options.Count;
    }

    private static bool IsPlaceholderText(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return true;

        string normalized = text.Trim().ToLowerInvariant();
        return normalized.StartsWith("option");
    }

    private static void SaveToggleValue(GameObject toggleObject, string key)
    {
        if (toggleObject == null)
            return;

        Toggle toggle = toggleObject.GetComponent<Toggle>();
        if (toggle != null)
            PlayerPrefs.SetInt(key, toggle.isOn ? 1 : 0);
    }

    private static void SetToggleValue(GameObject toggleObject, bool value)
    {
        if (toggleObject == null)
            return;

        Toggle toggle = toggleObject.GetComponent<Toggle>();
        if (toggle != null)
            toggle.isOn = value;
    }
}