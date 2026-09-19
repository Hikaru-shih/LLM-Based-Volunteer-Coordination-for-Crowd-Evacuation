using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;
using System.Collections.Generic;
using Decision;

public class SimulationUIController : MonoBehaviour
{
    public SimulationManager simulationManager;
    public GridWorld gridWorld;

    public GameObject mainMenuPanel;
    public GameObject settingsPanel;
    public GameObject inGamePanel;

    [Header("Scene Navigation")]
    [Tooltip("If true, Start/Back buttons will load scenes instead of switching local panels")]
    public bool useSceneNavigation = false;
    public string mainMenuSceneName = "MainMenu";
    public string gameplaySceneName = "SampleScene";

    public Button startButton;
    public Button settingsButton;
    public Button exitButton;
    public Button backToMenuButton;
    public Button applySettingsButton;
    public Button pauseResumeButton;
    public Button resetButton;
    public Button settingsInGameButton;

    public InputField gridWidthInput;
    public InputField gridHeightInput;
    public InputField agentCountInput;
    public InputField obstacleCountInput;
    public InputField volunteerCountInput;
    public InputField stepIntervalInput;
    public InputField kStaticInput;
    public InputField kDynamicInput;
    public InputField kAnticipationInput;
    public InputField temperatureInput;
    public Dropdown movementStrategyDropdown;
    public Dropdown conflictStrategyDropdown;

    public Text currentStepText;
    public Text evacuatedCountText;
    public Text volunteerCountText;
    public Text evacueeCountText;
    public Text obstacleCountText;
    public Text simulationStatusText;

    private bool isPaused = false;

    void Start()
    {
        InitializeDropdowns();
        LoadCurrentParameters();

        BindButton(startButton, StartSimulation);
        BindButton(settingsButton, ShowSettings);
        BindButton(exitButton, ExitGame);
        BindButton(backToMenuButton, ShowMainMenu);
        BindButton(applySettingsButton, ApplyParameters);
        BindButton(pauseResumeButton, TogglePauseResume);
        BindButton(resetButton, ResetSimulation);
        BindButton(settingsInGameButton, ShowSettingsFromGame);

        if (useSceneNavigation)
            ShowInGame();
        else
            ShowMainMenu();
        InvokeRepeating("UpdateStatusDisplay", 0f, 0.5f);
    }

    void InitializeDropdowns()
    {
        if (movementStrategyDropdown != null)
        {
            movementStrategyDropdown.ClearOptions();
            List<string> movementOptions = new List<string>();
            foreach (PedestrianAgent.MovementStrategy strategy in System.Enum.GetValues(typeof(PedestrianAgent.MovementStrategy)))
            {
                movementOptions.Add(strategy.ToString());
            }
            movementStrategyDropdown.AddOptions(movementOptions);
        }

        if (conflictStrategyDropdown != null)
        {
            conflictStrategyDropdown.ClearOptions();
            List<string> conflictOptions = new List<string>();
            foreach (YielderGame.Strategy strategy in System.Enum.GetValues(typeof(YielderGame.Strategy)))
            {
                conflictOptions.Add(strategy.ToString());
            }
            conflictStrategyDropdown.AddOptions(conflictOptions);
        }
    }

    void LoadCurrentParameters()
    {
        if (simulationManager == null || gridWorld == null)
            return;

        if (gridWidthInput != null) gridWidthInput.text = gridWorld.width.ToString();
        if (gridHeightInput != null) gridHeightInput.text = gridWorld.height.ToString();
        if (agentCountInput != null) agentCountInput.text = simulationManager.agentCount.ToString();
        if (obstacleCountInput != null) obstacleCountInput.text = simulationManager.obstacleCount.ToString();
        if (volunteerCountInput != null) volunteerCountInput.text = simulationManager.volunteerCount.ToString();
        if (stepIntervalInput != null) stepIntervalInput.text = simulationManager.stepInterval.ToString("F2");
        if (kStaticInput != null) kStaticInput.text = simulationManager.kStatic.ToString("F2");
        if (kDynamicInput != null) kDynamicInput.text = simulationManager.kDynamic.ToString("F2");
        if (kAnticipationInput != null) kAnticipationInput.text = simulationManager.kAnticipation.ToString("F2");
        if (temperatureInput != null) temperatureInput.text = simulationManager.movementTemperature.ToString("F2");

        if (movementStrategyDropdown != null) movementStrategyDropdown.value = (int)simulationManager.movementStrategy;
        if (conflictStrategyDropdown != null) conflictStrategyDropdown.value = (int)simulationManager.conflictStrategy;
    }

    void ShowMainMenu()
    {
        if (useSceneNavigation)
        {
            if (string.IsNullOrEmpty(mainMenuSceneName))
            {
                Debug.LogError("Main menu scene name is empty.");
                return;
            }

            SceneManager.LoadScene(mainMenuSceneName);
            return;
        }

        mainMenuPanel.SetActive(true);
        settingsPanel.SetActive(false);
        inGamePanel.SetActive(false);
    }

    void ShowSettings()
    {
        SetPanelActive(mainMenuPanel, false);
        SetPanelActive(settingsPanel, true);
        SetPanelActive(inGamePanel, false);
    }

    void ShowSettingsFromGame()
    {
        SetPanelActive(mainMenuPanel, false);
        SetPanelActive(settingsPanel, true);
        SetPanelActive(inGamePanel, false);
    }

    void ShowInGame()
    {
        SetPanelActive(mainMenuPanel, false);
        SetPanelActive(settingsPanel, false);
        SetPanelActive(inGamePanel, true);
    }

    void StartSimulation()
    {
        if (useSceneNavigation)
        {
            if (string.IsNullOrEmpty(gameplaySceneName))
            {
                Debug.LogError("Gameplay scene name is empty.");
                return;
            }

            SceneManager.LoadScene(gameplaySceneName);
            return;
        }

        if (simulationManager == null)
        {
            Debug.LogError("SimulationManager is not assigned.");
            return;
        }

        simulationManager.ResetSimulation();
        simulationManager.ResumeSimulation();
        isPaused = false;
        UpdateButtonText();
        ShowInGame();
    }

    void TogglePauseResume()
    {
        if (simulationManager == null)
            return;

        if (simulationManager.IsSimulationRunning())
        {
            simulationManager.PauseSimulation();
            isPaused = true;
        }
        else
        {
            simulationManager.ResumeSimulation();
            isPaused = false;
        }
        UpdateButtonText();
    }

    void ResetSimulation()
    {
        if (simulationManager == null)
            return;

        simulationManager.ResetSimulation();
        isPaused = true;
        UpdateButtonText();
    }

    void ApplyParameters()
    {
        if (simulationManager == null || gridWorld == null)
        {
            Debug.LogError("SimulationManager or GridWorld is not assigned.");
            return;
        }

        if (gridWidthInput != null && gridHeightInput != null &&
            int.TryParse(gridWidthInput.text, out int width) && int.TryParse(gridHeightInput.text, out int height))
        {
            gridWorld.width = width;
            gridWorld.height = height;
            gridWorld.Init();
        }

        if (agentCountInput != null && int.TryParse(agentCountInput.text, out int agentCount))
            simulationManager.agentCount = agentCount;

        if (obstacleCountInput != null && int.TryParse(obstacleCountInput.text, out int obstacleCount))
            simulationManager.obstacleCount = obstacleCount;

        if (volunteerCountInput != null && int.TryParse(volunteerCountInput.text, out int volunteerCount))
            simulationManager.volunteerCount = volunteerCount;

        if (stepIntervalInput != null && float.TryParse(stepIntervalInput.text, out float stepInterval))
            simulationManager.stepInterval = stepInterval;

        if (kStaticInput != null && float.TryParse(kStaticInput.text, out float kStatic))
            simulationManager.kStatic = kStatic;

        if (kDynamicInput != null && float.TryParse(kDynamicInput.text, out float kDynamic))
            simulationManager.kDynamic = kDynamic;

        if (kAnticipationInput != null && float.TryParse(kAnticipationInput.text, out float kAnticipation))
            simulationManager.kAnticipation = kAnticipation;

        if (temperatureInput != null && float.TryParse(temperatureInput.text, out float temperature))
            simulationManager.movementTemperature = temperature;

        if (movementStrategyDropdown != null)
            simulationManager.movementStrategy = (PedestrianAgent.MovementStrategy)movementStrategyDropdown.value;

        if (conflictStrategyDropdown != null)
            simulationManager.conflictStrategy = (YielderGame.Strategy)conflictStrategyDropdown.value;

        Debug.Log("Parameters applied.");
    }

    void ExitGame()
    {
        Application.Quit();
    }

    void UpdateButtonText()
    {
        if (pauseResumeButton == null)
            return;

        Text label = pauseResumeButton.GetComponentInChildren<Text>();
        if (label != null)
            label.text = isPaused ? "Resume" : "Pause";
    }

    void UpdateStatusDisplay()
    {
        if (simulationManager == null) return;

        if (currentStepText != null)
            currentStepText.text = "Step: " + simulationManager.GetCurrentStep();
        if (evacuatedCountText != null)
            evacuatedCountText.text = "Evacuated: " + simulationManager.GetEvacuatedCount() + " / " + simulationManager.GetTotalAgents();
        if (volunteerCountText != null)
            volunteerCountText.text = "Volunteers: " + simulationManager.GetVolunteerCount();
        if (evacueeCountText != null)
            evacueeCountText.text = "Evacuees: " + simulationManager.GetEvacueeCount();
        if (obstacleCountText != null)
            obstacleCountText.text = "Obstacles: " + simulationManager.GetObstacleCount();
        // simulationStatusText.text = simulationManager.IsSimulationRunning() ? "Running" : "Paused"; // 暫時不顯示
    }

    private void BindButton(Button button, UnityEngine.Events.UnityAction action)
    {
        if (button == null || action == null)
            return;

        button.onClick.AddListener(action);
    }

    private void SetPanelActive(GameObject panel, bool active)
    {
        if (panel != null)
            panel.SetActive(active);
    }
}