using System;
using System.IO;
using System.Security.Cryptography;
using UnityEngine;

[Serializable]
public sealed class AgentStudyPlan
{
    [Serializable] public class SourceFile { public string path,sha256; }
    public string schema,planID,model,promptVersion,primaryContrast,multiplicityTreatment;
    public bool locked;
    public int horizon;
    public int[] developmentSeeds,calibrationSeeds,testSeeds;
    public string[] conditionKeys,informationConditions,policies;
    public SourceFile[] sourceFiles;
    public static string Hash(string path)
    {
        using(var sha=SHA256.Create())
        using(var file=File.OpenRead(path))
            return BitConverter.ToString(sha.ComputeHash(file)).Replace("-","").ToLowerInvariant();
    }
    public static AgentStudyPlan LoadAndValidate(string path,SimulationManager manager,int seed)
    {
        var plan=JsonUtility.FromJson<AgentStudyPlan>(File.ReadAllText(path));
        if(plan==null || !plan.locked || plan.schema!="agent-study-plan-v1" || string.IsNullOrEmpty(plan.planID) ||
            plan.horizon!=manager.maxSimulationSteps || plan.model!=manager.openAIModel ||
            plan.promptVersion!=AgentObservation.PromptVersion || string.IsNullOrEmpty(plan.primaryContrast) ||
            string.IsNullOrEmpty(plan.multiplicityTreatment) || plan.conditionKeys==null ||
            Array.IndexOf(plan.conditionKeys,manager.AgentConditionKey)<0 || plan.informationConditions==null ||
            Array.IndexOf(plan.informationConditions,manager.agentInformation.ToString())<0 || plan.policies==null ||
            Array.IndexOf(plan.policies,manager.volunteerDecisionMode.ToString())<0)
            throw new InvalidDataException("Study plan does not match the selected run");
        int[] seeds=manager.agentResearchPhase==AgentResearchPhase.FinalTest ? plan.testSeeds : plan.calibrationSeeds;
        if(seeds==null || Array.IndexOf(seeds,seed)<0) throw new InvalidDataException("Seed is not in this plan split");
        if(plan.developmentSeeds==null || plan.calibrationSeeds==null || plan.testSeeds==null)
            throw new InvalidDataException("Missing study split");
        foreach(int value in plan.testSeeds)
            if(Array.IndexOf(plan.calibrationSeeds,value)>=0 || Array.IndexOf(plan.developmentSeeds,value)>=0)
                throw new InvalidDataException("Study seed splits overlap");
        foreach(int value in plan.calibrationSeeds)
            if(Array.IndexOf(plan.developmentSeeds,value)>=0) throw new InvalidDataException("Study seed splits overlap");
        if(plan.sourceFiles==null || plan.sourceFiles.Length==0) throw new InvalidDataException("Missing source provenance");
        string root=Path.GetFullPath(Path.Combine(Application.dataPath,".."));
        foreach(var source in plan.sourceFiles)
        {
            string file=Path.GetFullPath(Path.Combine(root,source.path));
            if(!file.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase) || Hash(file)!=source.sha256)
                throw new InvalidDataException("Source changed since study lock: "+source.path);
        }
        if(manager.volunteerDecisionMode==SimulationManager.VolunteerDecisionMode.RandomMatched)
        {
            string calibration=Path.GetFullPath(manager.cooperationCalibrationPath);
            if(!Array.Exists(plan.sourceFiles,source=>Path.GetFullPath(Path.Combine(root,source.path))==calibration))
                throw new InvalidDataException("Selected calibration file is not frozen in this plan");
        }
        return plan;
    }
}
