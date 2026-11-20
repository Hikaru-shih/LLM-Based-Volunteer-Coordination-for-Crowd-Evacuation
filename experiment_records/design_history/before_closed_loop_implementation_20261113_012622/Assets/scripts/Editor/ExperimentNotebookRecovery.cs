using System.IO;
using UnityEditor;
using UnityEngine;

[InitializeOnLoad]
public static class ExperimentNotebookRecovery
{
    static ExperimentNotebookRecovery() {EditorApplication.delayCall+=Recover;}
    [MenuItem("Research/Experiment notebook/Retry pending entries (no run)")]
    public static void Recover()
    {
        try
        {
            int count=AutomaticExperimentLog.RecoverPending(AutomaticExperimentLog.DefaultRoot)+
                AutomaticExperimentLog.RecoverAssessments(AutomaticExperimentLog.DefaultRoot);
            if(count>0) Debug.Log("[EXPERIMENT LOG] Recovered "+count+" pending notebook entries.");
        }
        catch(IOException) {Debug.LogWarning("[EXPERIMENT LOG] Pending entries remain; retry when the notebook is available.");}
        catch(System.UnauthorizedAccessException) {Debug.LogWarning("[EXPERIMENT LOG] Pending entries remain; notebook access is unavailable.");}
    }
}
