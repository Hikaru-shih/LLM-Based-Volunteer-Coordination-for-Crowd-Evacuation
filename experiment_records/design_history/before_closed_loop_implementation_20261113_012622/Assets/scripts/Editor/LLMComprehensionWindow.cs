using UnityEditor;
using UnityEngine;

public class LLMComprehensionWindow : EditorWindow
{
    private string model="gpt-4o-mini";
    private int limit=LLMComprehensionSuite.Questions().Length;
    private void OnGUI()
    {
        EditorGUILayout.LabelField("Paper-task comprehension (Core)",EditorStyles.boldLabel);
        EditorGUILayout.HelpBox("Opening this window makes no API call. Start uses the local key. At most 10 logical calls / 30 HTTP attempts; no evacuation simulation. Passing means correct understanding, not choosing to help.",MessageType.Info);
        using(new EditorGUI.DisabledScope(LLMComprehensionRunner.Running))
        {
            model=EditorGUILayout.TextField("Model",model);limit=EditorGUILayout.IntSlider("Question limit",limit,1,LLMComprehensionSuite.Questions().Length);
            if(GUILayout.Button("Start bounded API check")) LLMComprehensionRunner.Start(model,limit);
        }
        if(LLMComprehensionRunner.Running && GUILayout.Button("Cancel and save partial record")) LLMComprehensionRunner.Cancel();
        EditorGUILayout.LabelField(LLMComprehensionRunner.Status,EditorStyles.wordWrappedLabel);
        if(!string.IsNullOrEmpty(LLMComprehensionRunner.Output) && GUILayout.Button("Open saved artifacts")) EditorUtility.RevealInFinder(LLMComprehensionRunner.Output);
        if(LLMComprehensionRunner.Running) Repaint();
    }
}
