using System;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public static class SettingsMenuIntegration
{
    private const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
    private static void Invoke(object target,string name) => target.GetType().GetMethod(name,Private).Invoke(target,null);
    [MenuItem("Research/Integrate obstacle handling menu")]
    public static void UpgradeAndValidate()
    {
        var scene=EditorSceneManager.OpenScene("Assets/Scenes/MainMenu.unity");
        var settings=scene.GetRootGameObjects().SelectMany(o=>o.GetComponentsInChildren<MainMenuSettingsController>(true)).Single();
        var source=settings.volunteerDecisionModeDropdown;
        if(settings.exitCountInput==null) throw new Exception("Exit-count field migration failed");
        var exitInput=settings.exitCountInput;
        var exitLabel=exitInput.transform.parent.GetChild(exitInput.transform.GetSiblingIndex()-1).gameObject;
        exitInput.name="exitCountInput";exitLabel.name="ExitCountLabel";SetLabel(exitLabel,"Exit Count (1-4)");
        var tmpInput=exitInput.GetComponent<TMP_InputField>();
        if(tmpInput!=null) {tmpInput.contentType=TMP_InputField.ContentType.IntegerNumber;tmpInput.SetTextWithoutNotify("4");}
        var legacyInput=exitInput.GetComponent<InputField>();
        if(legacyInput!=null) {legacyInput.contentType=InputField.ContentType.IntegerNumber;legacyInput.SetTextWithoutNotify("4");}
        if(source==null) throw new Exception("Volunteer decision dropdown is not wired");
        if(settings.obstacleHandlingModeDropdown==null)
        {
            var parent=source.transform.parent;
            int labelIndex=source.transform.GetSiblingIndex()-1;
            var oldLabel=parent.GetChild(labelIndex);
            var label=UnityEngine.Object.Instantiate(oldLabel.gameObject,parent,false);
            label.name="ObstacleHandlingLabel";label.transform.SetSiblingIndex(labelIndex);
            SetLabel(label,"Obstacle Handling");
            var dropdown=UnityEngine.Object.Instantiate(source,parent,false);
            dropdown.name="obstacleHandlingModeDropdown";dropdown.transform.SetSiblingIndex(labelIndex+1);
            settings.obstacleHandlingModeDropdown=dropdown;
            SetLabel(oldLabel.gameObject,"Volunteer Decision");
        }
        if(settings.agentInformationDropdown==null)
        {
            var parent=source.transform.parent;
            var oldLabel=parent.GetChild(source.transform.GetSiblingIndex()-1);
            int index=source.transform.GetSiblingIndex()-1;
            var label=UnityEngine.Object.Instantiate(oldLabel.gameObject,parent,false);
            label.name="AgentInformationLabel";label.transform.SetSiblingIndex(index);SetLabel(label,"Agent Information");
            var dropdown=UnityEngine.Object.Instantiate(source,parent,false);
            dropdown.name="agentInformationDropdown";dropdown.transform.SetSiblingIndex(index+1);
            settings.agentInformationDropdown=dropdown;
        }
        if(settings.coordinationModeDropdown==null)
        {
            var parent=source.transform.parent;int index=source.transform.GetSiblingIndex()-1;
            var label=UnityEngine.Object.Instantiate(parent.GetChild(index).gameObject,parent,false);
            label.name="CoordinationModeLabel";label.transform.SetSiblingIndex(index);SetLabel(label,"Coordination Mode");
            var dropdown=UnityEngine.Object.Instantiate(source,parent,false);
            dropdown.name="coordinationModeDropdown";dropdown.transform.SetSiblingIndex(index+1);settings.coordinationModeDropdown=dropdown;
        }
        Invoke(settings,"InitializeDropdownOptions");
        EditorUtility.SetDirty(settings);EditorSceneManager.MarkSceneDirty(scene);
        if(!EditorSceneManager.SaveScene(scene)) throw new Exception("MainMenu scene save failed");
        Validate(settings);
        System.IO.Directory.CreateDirectory("tmp/menu-validation");
        System.IO.File.WriteAllText("tmp/menu-validation/result.json","{\"passed\":true,\"scene\":\"MainMenu\",\"obstacleOptions\":2,\"volunteerOptions\":5,\"conflictOptions\":5,\"roundTrips\":2}");
        Debug.Log("SETTINGS_MENU_VALIDATION_PASSED");
    }
    private static void SetLabel(GameObject label,string value)
    {
        var tmp=label.GetComponent<TMP_Text>();if(tmp!=null) tmp.text=value;
        var legacy=label.GetComponent<Text>();if(legacy!=null) legacy.text=value;
    }
    private static int Count(GameObject obj)
    { var tmp=obj.GetComponent<TMP_Dropdown>();return tmp!=null ? tmp.options.Count : obj.GetComponent<Dropdown>().options.Count; }
    private static void SetValue(GameObject obj,int value)
    { var tmp=obj.GetComponent<TMP_Dropdown>();if(tmp!=null) tmp.SetValueWithoutNotify(value);else obj.GetComponent<Dropdown>().SetValueWithoutNotify(value); }
    private static int Value(GameObject obj)
    {var tmp=obj.GetComponent<TMP_Dropdown>();return tmp!=null ? tmp.value : obj.GetComponent<Dropdown>().value;}
    private static void Validate(MainMenuSettingsController sceneSettings)
    {
        if(Count(sceneSettings.obstacleHandlingModeDropdown)!=2 || Count(sceneSettings.volunteerDecisionModeDropdown)!=5 || Count(sceneSettings.conflictStrategyDropdown)!=5 || Count(sceneSettings.agentInformationDropdown)!=2 || Count(sceneSettings.coordinationModeDropdown)!=4)
            throw new Exception("Enum dropdown options are stale");
        // Exercise actual save/load methods without changing unrelated user prefs
        // or touching the API-key input. Restore every key changed by this test.
        string[] keys={"sim.obstacleHandlingMode","sim.volunteerDecisionMode","sim.volunteerCost","sim.agentInformation","sim.coordinationMode"};
        bool[] existed=keys.Select(PlayerPrefs.HasKey).ToArray();
        int oldHandling=PlayerPrefs.GetInt(keys[0]),oldDecision=PlayerPrefs.GetInt(keys[1]);
        float oldCost=PlayerPrefs.GetFloat(keys[2]);
        int oldInformation=PlayerPrefs.GetInt(keys[3]);
        int oldCoordination=PlayerPrefs.GetInt(keys[4]);
        var obj=new GameObject("SettingsValidation");var test=obj.AddComponent<MainMenuSettingsController>();
        test.obstacleHandlingModeDropdown=sceneSettings.obstacleHandlingModeDropdown;
        test.agentInformationDropdown=sceneSettings.agentInformationDropdown;
        test.coordinationModeDropdown=sceneSettings.coordinationModeDropdown;
        test.volunteerDecisionModeDropdown=sceneSettings.volunteerDecisionModeDropdown;
        var input=new GameObject("Cost",typeof(RectTransform),typeof(InputField));test.volunteerCostInput=input;
        var manager=ResearchValidation.CreateManager(System.IO.Path.GetFullPath("tmp/menu-validation"));
        try
        {
            for(int mode=0;mode<2;mode++)
            {
                PlayerPrefs.SetInt(keys[0],mode);PlayerPrefs.SetInt(keys[1],1);PlayerPrefs.SetFloat(keys[2],0.005f);PlayerPrefs.SetInt(keys[3],mode);PlayerPrefs.SetInt(keys[4],mode);
                Invoke(test,"InitializeDropdownOptions");Invoke(test,"LoadToUI");
                if(Value(test.obstacleHandlingModeDropdown)!=mode || Value(test.volunteerDecisionModeDropdown)!=1 || Value(test.agentInformationDropdown)!=mode || Value(test.coordinationModeDropdown)!=mode)
                    throw new Exception("Saved options were not loaded");
                test.ApplySettings();
                if(PlayerPrefs.GetInt(keys[0])!=mode || Mathf.Abs(PlayerPrefs.GetFloat(keys[2])-0.005f)>0.000001f)
                    throw new Exception("Saving changed model selection or paper cost precision");
                Invoke(manager,"LoadSettingsFromMainMenu");
                if((int)manager.obstacleHandlingMode!=mode || manager.volunteerDecisionMode!=SimulationManager.VolunteerDecisionMode.LLM || (int)manager.agentInformation!=mode || (int)manager.paperExecutionMode!=mode)
                    throw new Exception("Gameplay did not receive independently selected modes");
            }
            PlayerPrefs.SetInt(keys[4],2);Invoke(test,"LoadToUI");
            if(Value(test.coordinationModeDropdown)!=2) throw new Exception("Optimal option not loaded");
            test.ApplySettings();Invoke(manager,"LoadSettingsFromMainMenu");
            if(manager.paperExecutionMode!=Coordination.ExecutionMode.OptimizedExtension) throw new Exception("Optimal option not round-tripped");
            PlayerPrefs.SetInt(keys[4],3);Invoke(test,"LoadToUI");
            if(Value(test.coordinationModeDropdown)!=3) throw new Exception("LLM coordination option not loaded");
            test.ApplySettings();Invoke(manager,"LoadSettingsFromMainMenu");
            if(manager.paperExecutionMode!=Coordination.ExecutionMode.LLMExtension) throw new Exception("LLM coordination option not round-tripped");
            PlayerPrefs.SetInt(keys[0],99);Invoke(test,"LoadToUI");Invoke(manager,"LoadSettingsFromMainMenu");
            if(Value(test.obstacleHandlingModeDropdown)!=0 || manager.obstacleHandlingMode!=ObstacleHandlingMode.PaperRelocation)
                throw new Exception("Invalid saved obstacle mode must use paper default");
        }
        finally
        {
            if(existed[0]) PlayerPrefs.SetInt(keys[0],oldHandling);else PlayerPrefs.DeleteKey(keys[0]);
            if(existed[1]) PlayerPrefs.SetInt(keys[1],oldDecision);else PlayerPrefs.DeleteKey(keys[1]);
            if(existed[2]) PlayerPrefs.SetFloat(keys[2],oldCost);else PlayerPrefs.DeleteKey(keys[2]);
            if(existed[3]) PlayerPrefs.SetInt(keys[3],oldInformation);else PlayerPrefs.DeleteKey(keys[3]);
            if(existed[4]) PlayerPrefs.SetInt(keys[4],oldCoordination);else PlayerPrefs.DeleteKey(keys[4]);PlayerPrefs.Save();
            UnityEngine.Object.DestroyImmediate(input);UnityEngine.Object.DestroyImmediate(obj);ResearchValidation.Cleanup();
        }
    }
}
