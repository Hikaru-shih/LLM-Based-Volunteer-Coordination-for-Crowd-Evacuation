using System.IO;
using UnityEditor;
using UnityEngine;

public static class AgentResearchSetup
{
    private static SimulationManager Selected()
    {
        var manager=Selection.activeGameObject!=null ? Selection.activeGameObject.GetComponent<SimulationManager>() : null;
        if(manager==null) throw new System.InvalidOperationException("Select the SimulationManager GameObject first");
        return manager;
    }
    [MenuItem("Research/Agent study/Check selected settings (no run)")]
    public static void Validate()
    {
        var manager=Selected();manager.ValidateAgentResearchSettings(manager.baseSeed);
        Debug.Log("AGENT_SETTINGS_VALID: no simulation or API started. Condition: "+manager.AgentConditionKey);
    }
    [MenuItem("Research/Agent study/Export selected condition (no run)")]
    public static void Export()
    {
        var manager=Selected();
        string path=EditorUtility.SaveFilePanel("Save physical condition",Application.dataPath+"/..","agent-condition","json");
        if(string.IsNullOrEmpty(path)) return;
        File.WriteAllText(path,JsonUtility.ToJson(new Condition {conditionKey=manager.AgentConditionKey,
            horizon=manager.maxSimulationSteps,model=manager.openAIModel,promptVersion=AgentObservation.PromptVersion},true));
    }
    [System.Serializable] private class Condition {public string conditionKey,model,promptVersion;public int horizon;}
}
