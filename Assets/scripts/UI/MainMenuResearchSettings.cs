using System;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public partial class MainMenuSettingsController
{
    [Header("Research settings (created automatically when opening the main menu)")]
    public GameObject researchScenarioDropdown,maxAgentRequestsInput;
    public GameObject samplingXInput,samplingTauInput,samplingRepetitionsInput,samplingBudgetInput,samplingSeedInput,samplingPurposeInput;
    private GameObject payoffLabel,researchFeedback;
    private bool researchControlsBuilt;
    [Serializable] private class SamplingScenario
    {public string id="settings_scenario";public int nearbyAgentCount;public float exitNonBlockage,volunteerCost,failureCost,unwillingness;}
    [Serializable] private class SamplingPlan
    {
        public string schema="individual-sampling-v1",purpose,model,promptVersion=PaperVolunteerPrompt.Version;
        public int repetitions,orderSeed,maxHttpAttempts;public SamplingScenario[] scenarios;
    }
    private static void Label(GameObject obj,string value)
    {var tmp=obj.GetComponent<TMP_Text>();if(tmp!=null)tmp.text=value;var legacy=obj.GetComponent<Text>();if(legacy!=null)legacy.text=value;}
    private GameObject NewLabel(string name,string text)
    {
        var source=exitCountInput.transform.parent.GetChild(exitCountInput.transform.GetSiblingIndex()-1).gameObject;
        var label=Instantiate(source,source.transform.parent,false);label.name=name;Label(label,text);
        var rect=label.GetComponent<RectTransform>();rect.SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical,40);
        var tmp=label.GetComponent<TMP_Text>();if(tmp!=null){tmp.enableAutoSizing=true;tmp.fontSizeMin=14;tmp.fontSizeMax=24;tmp.raycastTarget=false;}
        var legacy=label.GetComponent<Text>();if(legacy!=null){legacy.resizeTextForBestFit=true;legacy.resizeTextMinSize=14;legacy.resizeTextMaxSize=24;legacy.raycastTarget=false;}
        return label;
    }
    private void Input(ref GameObject field,string name,string labelText,bool integer=false)
    {
        if(field!=null)return;NewLabel(name+"Label",labelText);
        field=Instantiate(exitCountInput,exitCountInput.transform.parent,false);field.name=name;
        var tmp=field.GetComponent<TMP_InputField>();if(tmp!=null){tmp.onValueChanged=new TMP_InputField.OnChangeEvent();tmp.onEndEdit=new TMP_InputField.SubmitEvent();tmp.characterLimit=0;tmp.contentType=integer?TMP_InputField.ContentType.IntegerNumber:TMP_InputField.ContentType.Standard;tmp.text="";}
        var legacy=field.GetComponent<InputField>();if(legacy!=null){legacy.onValueChanged=new InputField.OnChangeEvent();legacy.onEndEdit=new InputField.EndEditEvent();legacy.characterLimit=0;legacy.contentType=integer?InputField.ContentType.IntegerNumber:InputField.ContentType.Standard;legacy.text="";}
    }
    public void EnsureResearchControls()
    {
        if(researchControlsBuilt || exitCountInput==null || exitCountInput.transform.parent==null)return;
        researchControlsBuilt=true;
        NewLabel("ResearchSection","Evacuation");
        if(researchScenarioDropdown==null && volunteerDecisionModeDropdown!=null)
        {
            NewLabel("ResearchScenarioLabel","Scenario");
            researchScenarioDropdown=Instantiate(volunteerDecisionModeDropdown,exitCountInput.transform.parent,false);researchScenarioDropdown.name="researchScenarioDropdown";
            var tmp=researchScenarioDropdown.GetComponent<TMP_Dropdown>();if(tmp!=null)tmp.onValueChanged=new TMP_Dropdown.DropdownEvent();
            var legacy=researchScenarioDropdown.GetComponent<Dropdown>();if(legacy!=null)legacy.onValueChanged=new Dropdown.DropdownEvent();
        }
        SetDropdownOptions(researchScenarioDropdown,new System.Collections.Generic.List<string>{"Random Room","Open Room","Blocked Exit","Two Exits (1 Blocked)","Unequal Exits"});
        Input(ref volunteerCostInput,"volunteerCostInput","Help Cost (cv)");
        Input(ref failureCostInput,"failureCostInput","No-help Loss (av)");
        Input(ref unwillingnessOmegaInput,"unwillingnessOmegaInput","Unwillingness (omega)");
        Input(ref openAiModelInput,"openAiModelInput","LLM Model");
        Input(ref maxAgentRequestsInput,"maxAgentRequestsInput","LLM Limit / Run",true);
        payoffLabel=NewLabel("ResearchPayoffs","Payoffs: help 1-cv; others help 1; no help 1-av");
        payoffLabel.GetComponent<RectTransform>().SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical,80);
        NewLabel("UtilityRules","0 < cv < av < 1; omega >= 0. Run limit: 0 = unlimited.").GetComponent<RectTransform>().SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical,80);
        foreach(var input in new[]{volunteerCostInput,failureCostInput})
        {
            var tmp=input.GetComponent<TMP_InputField>();if(tmp!=null)tmp.onValueChanged.AddListener(_=>RefreshPayoffs());
            var legacy=input.GetComponent<InputField>();if(legacy!=null)legacy.onValueChanged.AddListener(_=>RefreshPayoffs());
        }
        NewLabel("SamplingSection","Fixed-state Sampling");
        NewLabel("SamplingRules","Sampling only; live crowd states are unchanged. X includes self; ratio 0-1. Reserve 3 requests per choice.").GetComponent<RectTransform>().SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical,110);
        Input(ref samplingXInput,"samplingXInput","Player Count (X)",true);
        Input(ref samplingTauInput,"samplingTauInput","Unblocked Ratio (tau)");
        Input(ref samplingRepetitionsInput,"samplingRepetitionsInput","Repeats",true);
        Input(ref samplingBudgetInput,"samplingBudgetInput","Request Limit",true);
        Input(ref samplingSeedInput,"samplingSeedInput","Order Seed",true);
        Input(ref samplingPurposeInput,"samplingPurposeInput","Purpose");
        var button=NewLabel("SaveSamplingPlan","Save Sampling Plan");
        var click=button.AddComponent<Button>();click.targetGraphic=button.GetComponent<Graphic>();click.onClick.AddListener(ExportSamplingPlan);
        var graphic=button.GetComponent<Graphic>();if(graphic!=null){graphic.raycastTarget=true;graphic.color=new Color(.15f,.7f,1f,1);}
        var workflow=NewLabel("SamplingWorkflow","Saves settings only. Stop Play, then open Research > Individual sampling to run.");
        workflow.GetComponent<RectTransform>().SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical,100);
        researchFeedback=NewLabel("ResearchSettingsStatus","");
        researchFeedback.GetComponent<RectTransform>().SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical,120);
    }
    private bool FloatInput(GameObject obj,float fallback,out float value)
    {
        if(obj==null){value=fallback;return true;}
        return float.TryParse(GetInputText(obj),NumberStyles.Float,CultureInfo.InvariantCulture,out value) && !float.IsNaN(value) && !float.IsInfinity(value);
    }
    private bool IntInput(GameObject obj,int fallback,out int value)
    {if(obj==null){value=fallback;return true;}return int.TryParse(GetInputText(obj),NumberStyles.Integer,CultureInfo.InvariantCulture,out value);}
    private bool Costs(out float cv,out float av,out float omega)
    {
        cv=av=omega=0;
        return FloatInput(volunteerCostInput,defaultVolunteerCost,out cv) && FloatInput(failureCostInput,defaultFailureCost,out av) &&
            FloatInput(unwillingnessOmegaInput,defaultUnwillingnessOmega,out omega) && PaperDecisionSpecification.HasValidCosts(cv,av,omega);
    }
    private bool ValidateResearchSettings()
    {
        float cv,av,omega;int budget;
        if(!Costs(out cv,out av,out omega)){UpdateResearchFeedback("Not saved: require 0 < cv < av < 1 and omega >= 0.");return false;}
        if(!IntInput(maxAgentRequestsInput,0,out budget) || budget<0){UpdateResearchFeedback("Not saved: evacuation request limit must be a nonnegative integer.");return false;}
        if(openAiModelInput!=null && string.IsNullOrWhiteSpace(GetInputText(openAiModelInput))){UpdateResearchFeedback("Not saved: model name is required.");return false;}
        if(samplingXInput!=null && !ValidSamplingInputs()){UpdateResearchFeedback("Not saved: sampling requires X >= 0, tau in [0,1], repeats 1..10000, HTTP cap >= 0 and a purpose.");return false;}
        return true;
    }
    private bool ValidSamplingInputs()
    {
        int x,repetitions,budget,seed;float tau;
        return IntInput(samplingXInput,2,out x) && x>=0 && FloatInput(samplingTauInput,.5f,out tau) && tau>=0 && tau<=1 &&
            IntInput(samplingRepetitionsInput,5,out repetitions) && repetitions>=1 && repetitions<=10000 &&
            IntInput(samplingBudgetInput,15,out budget) && budget>=0 && IntInput(samplingSeedInput,2026,out seed) && !string.IsNullOrWhiteSpace(GetInputText(samplingPurposeInput));
    }
    private void RefreshPayoffs()
    {
        float cv,av,omega;
        if(payoffLabel!=null)Label(payoffLabel,Costs(out cv,out av,out omega)?string.Format(CultureInfo.InvariantCulture,"Payoffs: help {0:G6}; others help 1; no help {1:G6}",1-cv,1-av):"Invalid costs: require 0 < cv < av < 1; omega >= 0.");
    }
    private void UpdateResearchFeedback(string message){if(researchFeedback!=null)Label(researchFeedback,message);else Debug.Log("[SETTINGS] "+message);}
    private void SaveResearchSettings()
    {
        SaveDropdownValue(researchScenarioDropdown,"sim.researchScenario");SaveInt(maxAgentRequestsInput,"sim.maxAgentRequestsPerRun");
        SaveInt(samplingXInput,"sampling.x");SaveFloat(samplingTauInput,"sampling.tau");SaveInt(samplingRepetitionsInput,"sampling.repetitions");
        SaveInt(samplingBudgetInput,"sampling.httpBudget");SaveInt(samplingSeedInput,"sampling.seed");SaveString(samplingPurposeInput,"sampling.purpose");
    }
    private void LoadResearchSettings()
    {
        SetDropdownValue(researchScenarioDropdown,Mathf.Clamp(PlayerPrefs.GetInt("sim.researchScenario",0),0,Enum.GetValues(typeof(ResearchScenario)).Length-1));
        SetText(maxAgentRequestsInput,PlayerPrefs.GetInt("sim.maxAgentRequestsPerRun",0).ToString(CultureInfo.InvariantCulture));
        SetText(samplingXInput,PlayerPrefs.GetInt("sampling.x",2).ToString(CultureInfo.InvariantCulture));
        SetText(samplingTauInput,PlayerPrefs.GetFloat("sampling.tau",.5f).ToString("G9",CultureInfo.InvariantCulture));
        SetText(samplingRepetitionsInput,PlayerPrefs.GetInt("sampling.repetitions",5).ToString(CultureInfo.InvariantCulture));
        SetText(samplingBudgetInput,PlayerPrefs.GetInt("sampling.httpBudget",15).ToString(CultureInfo.InvariantCulture));
        SetText(samplingSeedInput,PlayerPrefs.GetInt("sampling.seed",2026).ToString(CultureInfo.InvariantCulture));
        SetText(samplingPurposeInput,PlayerPrefs.GetString("sampling.purpose","Development: individual fixed-state sampling"));
        // Cost fields load later in LoadToUI; refresh then as well via onValueChanged.
    }
    public string ExportedSamplingPlanPath {get;private set;}
    public void ExportSamplingPlan()
    {
        if(!ValidateResearchSettings())return;
        float cv,av,omega,tau;int x,repetitions,budget,seed;
        Costs(out cv,out av,out omega);
        if(!IntInput(samplingXInput,2,out x) || x<0 || !FloatInput(samplingTauInput,.5f,out tau) || tau<0 || tau>1 ||
            !IntInput(samplingRepetitionsInput,5,out repetitions) || repetitions<1 || repetitions>10000 || !IntInput(samplingBudgetInput,15,out budget) || budget<0 || !IntInput(samplingSeedInput,2026,out seed) || string.IsNullOrWhiteSpace(GetInputText(samplingPurposeInput)))
        {UpdateResearchFeedback("Plan not exported: X >= 0; tau in [0,1]; repeats 1..10000; HTTP cap >= 0; purpose required.");return;}
        var plan=new SamplingPlan {purpose=GetInputText(samplingPurposeInput),model=GetInputText(openAiModelInput),repetitions=repetitions,orderSeed=seed,maxHttpAttempts=budget,
            scenarios=new[]{new SamplingScenario {nearbyAgentCount=x,exitNonBlockage=tau,volunteerCost=cv,failureCost=av,unwillingness=omega}}};
        try
        {
            string folder=Path.Combine(Application.isEditor?Path.GetDirectoryName(Application.dataPath):Application.persistentDataPath,"experiment_records","sampling_plans");Directory.CreateDirectory(folder);
            string path=Path.Combine(folder,"settings_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")+"_"+Guid.NewGuid().ToString("N").Substring(0,8)+".json");
            File.WriteAllText(path,JsonUtility.ToJson(plan,true));ExportedSamplingPlanPath=path;ApplySettings();
            File.WriteAllText(Path.Combine(folder,"latest.txt"),path);
            UpdateResearchFeedback("Plan saved. Stop Play, then open Research > Individual sampling.");
        }
        catch(Exception e) when(e is IOException || e is UnauthorizedAccessException){UpdateResearchFeedback("Could not export plan: "+e.GetType().Name);}
    }
}
