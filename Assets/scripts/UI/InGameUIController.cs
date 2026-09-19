using UnityEngine;
using UnityEngine.UI;
using TMPro;

namespace UI
{
    public class InGameUIController : MonoBehaviour
    {
        public SimulationManager simulationManager;

        // InGame Panel 中的文字欄位
        public TextMeshProUGUI currentStepText;
        public TextMeshProUGUI evacuatedCountText;
        public TextMeshProUGUI totalCountText;
        public TextMeshProUGUI volunteerCountText;
        public TextMeshProUGUI stateText;
        public TextMeshProUGUI obstacleCountText;
        public TextMeshProUGUI roundText;

        public Button pauseResumeButton;
        public Button resetButton;

    void Start()
    {
        InvokeRepeating("UpdateStatusDisplay", 0f, 0.5f);
    }

    void UpdateStatusDisplay()
    {
        if (simulationManager == null) return;
        currentStepText.text = simulationManager.GetCurrentStep().ToString();
        evacuatedCountText.text = simulationManager.GetEvacuatedCount().ToString();
        int remaining = simulationManager.GetTotalAgents() - simulationManager.GetEvacuatedCount();
        totalCountText.text = remaining.ToString();
        volunteerCountText.text = simulationManager.GetVolunteerCount().ToString();
        stateText.text = simulationManager.IsSimulationRunning() ? "Running" : "Paused";
        obstacleCountText.text = simulationManager.GetObstacleCount().ToString();
        // 輪次顯示由 SimulationManager 主動呼叫 SetRoundText
    }

    public void SetRoundText(int current, int total)
    {
        if (roundText != null)
            roundText.text = current.ToString() + "/" + total.ToString();
    }
    }
}