using System;
using System.IO;
using UnityEngine;
using Decision;

public static class PaperDecisionSpecificationValidation
{
    public static void Run()
    {
        PaperAgentContractValidation.Run();
        int checks=0;
        var strategy=new OriginalGameTheoryVolunteerStrategy(()=>0.5f);
        foreach(int x in new[]{1,2,5,20})
        foreach(float tau in new[]{0f,0.25f,0.75f,1f})
        foreach(float cv in new[]{0.0000005f,0.005f,0.1f})
        foreach(float omega in new[]{0f,1f,5f})
        {
            var c=new VolunteerDecisionContext {nearbyAgentCount=x,exitNonBlockage=tau,
                volunteerCost=cv,failureCost=0.5f,unwillingness=omega};
            double expected=tau>=1 ? 0 : x==1 ? (tau==0 ? 1 : 0) :
                1-Math.Pow(1-Math.Exp(-(double)omega*tau),1.0/x)*Math.Pow((double)cv/0.5,1.0/(x-1));
            if(Math.Abs(strategy.CalculateVolunteerProbability(c)-expected)>0.000001)
                throw new Exception("Eq.(25)/single-player/boundary check failed");
            checks++;
        }
        if(Math.Abs(PaperDecisionSpecification.Payoff(true,false,.005,.5)-.995)>1e-12 ||
            Math.Abs(PaperDecisionSpecification.Payoff(true,true,.005,.5)-.995)>1e-12 ||
            PaperDecisionSpecification.Payoff(false,true,.005,.5)!=1 ||
            PaperDecisionSpecification.Payoff(false,false,.005,.5)!=.5)
            throw new Exception("Eq.(20) payoff table mismatch");
        if(PaperDecisionSpecification.HasValidCosts(1,2,5) || PaperDecisionSpecification.HasValidCosts(.5f,.5f,5) ||
            PaperDecisionSpecification.HasValidCosts(float.NaN,.5f,5) || !PaperDecisionSpecification.HasValidCosts(.005f,.5f,5))
            throw new Exception("Paper cost-domain validation mismatch");
        foreach(string old in new[]{"selfish","volunteer","continue_evacuation","PARTICIPATE",""})
            if(PaperVolunteerPrompt.IsDecision(old)) throw new Exception("Non-v3 action accepted");
        if(!PaperVolunteerPrompt.IsDecision("participate") || !PaperVolunteerPrompt.IsDecision("decline_assistance"))
            throw new Exception("V3 actions rejected");
        Directory.CreateDirectory("tmp/paper-decision-specification");
        foreach(AgentInformationCondition information in Enum.GetValues(typeof(AgentInformationCondition)))
        foreach(AgentPromptWording wording in Enum.GetValues(typeof(AgentPromptWording)))
        {
            string text=PaperVolunteerPrompt.Instructions(information.ToString(),wording);
            if(!text.Contains("1-cv") || !text.Contains("1-av") || !text.Contains("NOT a risk") ||
                text.Contains("continue_evacuation") || text.Contains("exp(") || text.Contains("must participate"))
                throw new Exception("Prompt payoff/action/no-answer-leak contract failed");
            if(information==AgentInformationCondition.Core && text.Contains("distanceToObstacle"))
                throw new Exception("Core prompt leaked shared-context field semantics");
            File.WriteAllText("tmp/paper-decision-specification/"+information+"_"+wording+".txt",text);
            File.WriteAllText("tmp/paper-decision-specification/"+information+"_"+wording+".sha256",PaperVolunteerPrompt.Hash(information.ToString(),wording));
        }
        File.WriteAllText("tmp/paper-decision-specification/validation.json","{\"passed\":true,\"probabilityCases\":"+checks+",\"promptVersion\":\""+PaperVolunteerPrompt.Version+"\",\"remoteRequests\":0}");
        Debug.Log("PAPER_DECISION_SPECIFICATION_VALIDATION_PASSED: "+checks+" probability cases, payoff, actions, prompt contracts; no API or simulation");
    }
}
