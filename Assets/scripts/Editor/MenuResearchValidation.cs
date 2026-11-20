using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public static class MenuResearchValidation
{
    private static int checks;
    private static void Check(bool ok,string why){checks++;if(!ok)throw new Exception(why);}
    private static void Invoke(object obj,string method)=>obj.GetType().GetMethod(method,BindingFlags.Instance|BindingFlags.NonPublic).Invoke(obj,null);
    private static void Text(GameObject obj,string text){var tmp=obj.GetComponent<TMP_InputField>();if(tmp!=null)tmp.text=text;else obj.GetComponent<InputField>().text=text;}
    private static string Text(GameObject obj){var tmp=obj.GetComponent<TMP_InputField>();return tmp!=null?tmp.text:obj.GetComponent<InputField>().text;}
    private static void Select(GameObject obj,int i){var tmp=obj.GetComponent<TMP_Dropdown>();if(tmp!=null)tmp.value=i;else obj.GetComponent<Dropdown>().value=i;}
    public static void Run()
    {
        checks=0;string root=Path.GetFullPath("tmp/menu-research-validation/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff"));Directory.CreateDirectory(root);
        var scene=EditorSceneManager.OpenScene("Assets/Scenes/MainMenu.unity");
        var menu=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<MainMenuSettingsController>(true)).Single();
        int before=menu.exitCountInput.transform.parent.childCount;menu.EnsureResearchControls();int after=menu.exitCountInput.transform.parent.childCount;
        Check(after>before+20,"Research controls not created in the real menu");menu.EnsureResearchControls();Check(menu.exitCountInput.transform.parent.childCount==after,"Duplicate controls created");
        Check(menu.researchScenarioDropdown!=null && menu.openAiModelInput!=null && menu.volunteerCostInput!=null && menu.samplingBudgetInput!=null,"Missing wired fields");
        Check(menu.exitCountInput.GetComponentInParent<ScrollRect>()!=null,"New controls outside scroll view");
        var obj=new GameObject("IsolatedResearchSettingsTest");var test=obj.AddComponent<MainMenuSettingsController>();
        foreach(string name in new[]{"researchScenarioDropdown","maxAgentRequestsInput","volunteerCostInput","failureCostInput","unwillingnessOmegaInput","openAiModelInput","samplingXInput","samplingTauInput","samplingRepetitionsInput","samplingBudgetInput","samplingSeedInput","samplingPurposeInput"})
        {var field=typeof(MainMenuSettingsController).GetField(name);field.SetValue(test,field.GetValue(menu));}
        string[] floats={"sim.volunteerCost","sim.failureCost","sim.unwillingnessOmega","sampling.tau"};
        string[] ints={"sim.researchScenario","sim.maxAgentRequestsPerRun","sampling.x","sampling.repetitions","sampling.httpBudget","sampling.seed"};
        string[] strings={"sim.openAIModel","sampling.purpose"};
        string[] keys=floats.Concat(ints).Concat(strings).ToArray();bool[] existed=keys.Select(PlayerPrefs.HasKey).ToArray();
        float[] oldF=floats.Select(k=>PlayerPrefs.GetFloat(k)).ToArray();int[] oldI=ints.Select(k=>PlayerPrefs.GetInt(k)).ToArray();string[] oldS=strings.Select(k=>PlayerPrefs.GetString(k)).ToArray();
        var manager=ResearchValidation.CreateManager(root);
        try
        {
            foreach(string key in keys)PlayerPrefs.DeleteKey(key);Invoke(test,"LoadToUI");
            Check(Text(test.volunteerCostInput)=="0.00499999989" || Math.Abs(float.Parse(Text(test.volunteerCostInput),System.Globalization.CultureInfo.InvariantCulture)-.005)<1e-7,"Default cost precision lost");
            Text(test.volunteerCostInput,"0.1");Text(test.failureCostInput,"0.7");Text(test.unwillingnessOmegaInput,"2.5");Text(test.openAiModelInput,"offline-menu-fixture");Text(test.maxAgentRequestsInput,"12");
            Text(test.samplingXInput,"4");Text(test.samplingTauInput,"0.25");Text(test.samplingRepetitionsInput,"7");Text(test.samplingBudgetInput,"21");Text(test.samplingSeedInput,"42");Text(test.samplingPurposeInput,"Development: menu export fixture");
            Select(test.researchScenarioDropdown,(int)ResearchScenario.SingleBlockedExit);test.ApplySettings();
            Invoke(manager,"LoadSettingsFromMainMenu");
            Check(manager.researchScenario==ResearchScenario.SingleBlockedExit && manager.maxAgentRequestsPerRun==12,"Gameplay did not receive scenario/budget");
            Check(Math.Abs(manager.volunteerCost-.1)<1e-6 && Math.Abs(manager.failureCost-.7)<1e-6 && Math.Abs(manager.unwillingnessOmega-2.5)<1e-6 && manager.openAIModel=="offline-menu-fixture","Gameplay did not receive utilities/model");
            Text(test.volunteerCostInput,"NaN");test.ApplySettings();Check(Math.Abs(PlayerPrefs.GetFloat("sim.volunteerCost")-.1)<1e-6,"Nonfinite utility saved");
            Text(test.volunteerCostInput,"0.8");test.ApplySettings();Check(Math.Abs(PlayerPrefs.GetFloat("sim.volunteerCost")-.1)<1e-6,"Invalid cost ordering saved");
            Check(!test.LastSettingsApplySucceeded,"Invalid settings reported success");
            var launcher=obj.AddComponent<MainMenuController>();launcher.settingsController=test;launcher.StartGame();
            Check(UnityEngine.SceneManagement.SceneManager.GetActiveScene().path=="Assets/Scenes/MainMenu.unity","Invalid settings launched gameplay");
            Text(test.volunteerCostInput,"0.1");Text(test.samplingTauInput,"1.5");Text(test.maxAgentRequestsInput,"99");test.ApplySettings();Check(PlayerPrefs.GetInt("sim.maxAgentRequestsPerRun")==12,"Invalid sampling input partially saved settings");
            Invoke(test,"LoadToUI");Check(Text(test.samplingTauInput)=="0.25" && Text(test.samplingRepetitionsInput)=="7" && Text(test.maxAgentRequestsInput)=="12","Sampling reload failed");
            test.ExportSamplingPlan();Check(File.Exists(test.ExportedSamplingPlanPath),"Menu plan export missing");
            var plan=IndividualSamplingRunner.Load(test.ExportedSamplingPlanPath);Check(plan.repetitions==7 && plan.maxHttpAttempts==21 && plan.orderSeed==42,"Exported plan count/budget mismatch");
            Check(plan.scenarios.Single().nearbyAgentCount==4 && plan.scenarios[0].exitNonBlockage==.25f && plan.scenarios[0].volunteerCost==.1f && plan.model=="offline-menu-fixture","Menu export not accepted by the actual sampler");
            Check(!IndividualSamplingRunner.Running,"Menu save unexpectedly dispatched API sampling");
            File.Copy(test.ExportedSamplingPlanPath,Path.Combine(root,"exported-plan.json"));
            foreach(ResearchScenario scenario in Enum.GetValues(typeof(ResearchScenario)))
            {Select(test.researchScenarioDropdown,(int)scenario);test.ApplySettings();Invoke(manager,"LoadSettingsFromMainMenu");Check(manager.researchScenario==scenario,"Scenario round-trip failed");}
        }
        finally
        {
            for(int i=0;i<floats.Length;i++)PlayerPrefs.SetFloat(floats[i],oldF[i]);for(int i=0;i<ints.Length;i++)PlayerPrefs.SetInt(ints[i],oldI[i]);for(int i=0;i<strings.Length;i++)PlayerPrefs.SetString(strings[i],oldS[i]);
            for(int i=0;i<keys.Length;i++)if(!existed[i])PlayerPrefs.DeleteKey(keys[i]);PlayerPrefs.Save();UnityEngine.Object.DestroyImmediate(obj);ResearchValidation.Cleanup();
        }
        // Existing fixed-state/physics regressions also compile against the new Settings integration.
        IndividualSamplingValidation.Run();
        File.WriteAllText(Path.Combine(root,"result.json"),"{\"passed\":true,\"checks\":"+checks+",\"remoteRequests\":0,\"savedScene\":false}");
        File.WriteAllText("tmp/menu-research-validation/latest.txt",root);Debug.Log("MENU_RESEARCH_VALIDATION_PASSED: "+checks+" checks; zero API; user preferences restored");
    }
}
