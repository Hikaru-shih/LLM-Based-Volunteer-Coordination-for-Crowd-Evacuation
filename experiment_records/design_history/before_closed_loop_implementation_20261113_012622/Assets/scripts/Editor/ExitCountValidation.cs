using System;
using System.Reflection;
using UnityEngine;
using UnityEngine.UI;

public static class ExitCountValidation
{
    public static void Run()
    {
        bool had=PlayerPrefs.HasKey("sim.exitCount");int old=PlayerPrefs.GetInt("sim.exitCount");
        bool hadInterval=PlayerPrefs.HasKey("sim.volunteerSelectionInterval");int interval=PlayerPrefs.GetInt("sim.volunteerSelectionInterval");
        var obj=new GameObject("ExitCountContract",typeof(RectTransform));var field=obj.AddComponent<InputField>();
        var settings=obj.AddComponent<MainMenuSettingsController>();settings.exitCountInput=obj;
        var flags=BindingFlags.Instance|BindingFlags.NonPublic;
        var world=obj.AddComponent<GridWorld>();world.width=world.height=11;
        int checks=0;
        try
        {
            PlayerPrefs.SetInt("sim.volunteerSelectionInterval",777);
            foreach(int value in new[]{1,2,3,4,0,9})
            {
                field.text=value.ToString();settings.ApplySettings();
                int expected=Mathf.Clamp(value,1,4);
                if(PlayerPrefs.GetInt("sim.exitCount")!=expected || PlayerPrefs.GetInt("sim.volunteerSelectionInterval")!=777)
                    throw new Exception("Exit setting altered the legacy selection interval");checks++;
                typeof(MainMenuSettingsController).GetMethod("LoadToUI",flags).Invoke(settings,null);
                if(field.text!=expected.ToString()) throw new Exception("Exit count did not load");checks++;
            }
            foreach(var scenario in new[]{ResearchScenario.RandomRoom,ResearchScenario.OpenRoom})
            for(int count=1;count<=4;count++)
            {
                world.Init();ResearchEnvironment.Configure(world,scenario,0,3,3,count);
                if(ResearchEnvironment.CountExitGroups(world)!=count || world.exitPositions.Count!=3*count)
                    throw new Exception("Generated exit groups/width mismatch");checks++;
            }
            world.Init();ResearchEnvironment.Configure(world,ResearchScenario.SingleBlockedExit,5,3,3,4);
            if(ResearchEnvironment.CountExitGroups(world)!=1) throw new Exception("Fixed single-exit fixture was changed");checks++;
            world.Init();ResearchEnvironment.Configure(world,ResearchScenario.TwoExitsOneBlocked,5,3,3,4);
            if(ResearchEnvironment.CountExitGroups(world)!=2) throw new Exception("Fixed two-exit fixture was changed");checks++;
            Debug.Log("EXIT_COUNT_VALIDATION_PASSED: "+checks+" settings and geometry checks; no API or evacuation steps");
        }
        finally
        {
            if(had) PlayerPrefs.SetInt("sim.exitCount",old);else PlayerPrefs.DeleteKey("sim.exitCount");
            if(hadInterval) PlayerPrefs.SetInt("sim.volunteerSelectionInterval",interval);else PlayerPrefs.DeleteKey("sim.volunteerSelectionInterval");
            PlayerPrefs.Save();UnityEngine.Object.DestroyImmediate(obj);
        }
        SettingsMenuIntegration.UpgradeAndValidate();
    }
}
