using System;
using System.IO;
using UnityEngine;
using Decision;

public enum AgentInformationCondition { SharedContext, Core }
public enum AgentPromptWording { Standard, Alternate }
public enum AgentResearchPhase { Development, Calibration, FinalTest }

public static class AgentObservation
{
    [Serializable] private class Core
    {
        public int nearbyAgentCount;
        public float exitNonBlockage, volunteerCost, failureCost, unwillingness;
    }
    public const string PromptVersion=PaperVolunteerPrompt.Version;
    public static string Serialize(VolunteerDecisionContext context,AgentInformationCondition condition)
    {
        if(condition==AgentInformationCondition.SharedContext) return JsonUtility.ToJson(context);
        return JsonUtility.ToJson(new Core {nearbyAgentCount=context.nearbyAgentCount,
            exitNonBlockage=context.exitNonBlockage,volunteerCost=context.volunteerCost,
            failureCost=context.failureCost,unwillingness=context.unwillingness});
    }
}

[Serializable]
public sealed class CooperationCalibration
{
    public string schema, calibrationID, split, model, promptVersion, informationCondition, conditionKey;
    public int decisions;
    public float probability;
    public int[] seeds;
    public string[] sourceHashes;
    public string responseProtocol,geometryTemplateSHA,productionSourceSHA;
    public int horizon;

    public static CooperationCalibration Load(string path,string conditionKey,string model,
        AgentInformationCondition condition,int testSeed,AgentResearchPhase phase,bool requireV2=false,string geometryTemplateSHA="",string productionSourceSHA="",int horizon=0)
    {
        var value=JsonUtility.FromJson<CooperationCalibration>(File.ReadAllText(path));
        if(value==null || (value.schema!="cooperation-calibration-v1" && value.schema!="cooperation-calibration-v2") || value.split!="Calibration" ||
            string.IsNullOrEmpty(value.calibrationID) || value.promptVersion!=AgentObservation.PromptVersion ||
            value.conditionKey!=conditionKey || value.model!=model || value.informationCondition!=condition.ToString() ||
            value.decisions<=0 || float.IsNaN(value.probability) || value.probability<0 || value.probability>1 ||
            value.seeds==null || value.seeds.Length==0 || value.sourceHashes==null || value.sourceHashes.Length==0)
            throw new InvalidDataException("Invalid or incompatible cooperation calibration");
        if(requireV2 && (value.schema!="cooperation-calibration-v2" || value.responseProtocol!=PersonalDecisionProtocol.Version ||
            value.geometryTemplateSHA!=geometryTemplateSHA || value.productionSourceSHA!=productionSourceSHA || value.horizon!=horizon))
            throw new InvalidDataException("Closed-loop calibration version/geometry/source/horizon mismatch");
        if(phase==AgentResearchPhase.FinalTest && Array.IndexOf(value.seeds,testSeed)>=0)
            throw new InvalidDataException("Test seed overlaps calibration data");
        return value;
    }
}

namespace Decision
{
    public sealed class RandomMatchedVolunteerStrategy : IVolunteerDecisionStrategy
    {
        private readonly float probability;
        private readonly Func<float> sample;
        public RandomMatchedVolunteerStrategy(float probability,Func<float> sample)
        {
            if(float.IsNaN(probability) || probability<0 || probability>1 || sample==null)
                throw new ArgumentException("A calibrated probability and independent RNG are required");
            this.probability=probability;this.sample=sample;
        }
        public bool ShouldVolunteer(VolunteerDecisionContext context) => sample()<probability;
    }
}
