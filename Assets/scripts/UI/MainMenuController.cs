using UnityEngine;
using UnityEngine.SceneManagement;

public class MainMenuController : MonoBehaviour
{
    [Header("Scene Names")]
    [Tooltip("Scene loaded when player clicks Start")]
    public string gameplaySceneName = "SampleScene";

    [Header("Optional Panels")]
    public GameObject mainPanel;
    public GameObject settingsPanel;

    [Header("Optional Settings")]
    public MainMenuSettingsController settingsController;

    void Awake()
    {
        AutoAssignPanelsIfNeeded();

        if (settingsController == null)
            settingsController = GetComponent<MainMenuSettingsController>();
    }

#if UNITY_EDITOR
    void OnValidate()
    {
        AutoAssignPanelsIfNeeded();
    }
#endif

    void Start()
    {
        ShowMainPanel();
    }

    public void StartGame()
    {
        if (settingsController != null)
            settingsController.ApplySettings();

        if (string.IsNullOrEmpty(gameplaySceneName))
        {
            Debug.LogError("Gameplay scene name is empty.");
            return;
        }

        SceneManager.LoadScene(gameplaySceneName);
    }

    public void ShowSettings()
    {
        if (mainPanel != null)
            mainPanel.SetActive(false);

        if (settingsPanel != null)
            settingsPanel.SetActive(true);
    }

    public void ShowMainPanel()
    {
        if (mainPanel != null)
            mainPanel.SetActive(true);

        if (settingsPanel != null)
            settingsPanel.SetActive(false);
    }

    public void QuitGame()
    {
        Application.Quit();
    }

    private void AutoAssignPanelsIfNeeded()
    {
        if (mainPanel == null)
        {
            mainPanel = FindPanelByName("MainPanel");
        }

        if (settingsPanel == null)
        {
            settingsPanel = FindPanelByName("SettingsPanel");
        }
    }

    private GameObject FindPanelByName(string panelName)
    {
        Transform[] allChildren = GetComponentsInChildren<Transform>(true);
        for (int i = 0; i < allChildren.Length; i++)
        {
            if (allChildren[i].name == panelName)
            {
                return allChildren[i].gameObject;
            }
        }

        GameObject sceneObject = GameObject.Find(panelName);
        return sceneObject;
    }
}