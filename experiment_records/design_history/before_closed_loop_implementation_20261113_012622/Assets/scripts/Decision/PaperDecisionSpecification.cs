using System;

public static class PaperDecisionSpecification
{
    public enum DecisionKind { Invalid, NoGame, ReferenceBoundary, Choice }
    private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
    public static bool HasValidCosts(float cv,float av,float omega)
        => Finite(cv) && Finite(av) && Finite(omega) && 0<cv && cv<av && av<1 && omega>=0;
    public static DecisionKind Classify(Decision.VolunteerDecisionContext context,out bool ruleWilling)
    {
        ruleWilling=false;
        if(context==null || context.nearbyAgentCount<0 || !Finite(context.exitNonBlockage) || context.exitNonBlockage<0 || context.exitNonBlockage>1 ||
            !HasValidCosts(context.volunteerCost,context.failureCost,context.unwillingness))return DecisionKind.Invalid;
        if(context.nearbyAgentCount==0 || context.exitNonBlockage==1)return DecisionKind.NoGame;
        if(context.nearbyAgentCount==1){ruleWilling=context.exitNonBlockage==0;return DecisionKind.ReferenceBoundary;}
        return DecisionKind.Choice;
    }
    public static bool Observation(string json,string information,out Decision.VolunteerDecisionContext context)
    {
        context=null;System.Collections.Generic.Dictionary<string,object> obj;
        if(!StrictJson.TryObject(json,out obj) || (information!="Core" && information!="SharedContext") || (information=="Core" && obj.Count!=5))return false;
        string[] keys={"nearbyAgentCount","exitNonBlockage","volunteerCost","failureCost","unwillingness"};
        var numbers=new StrictJson.Number[5];
        for(int i=0;i<keys.Length;i++){object value;if(!obj.TryGetValue(keys[i],out value) || !(value is StrictJson.Number))return false;numbers[i]=(StrictJson.Number)value;}
        if(numbers[1].value<0 || numbers[1].value>1 || numbers[2].value<=0 || numbers[2].value>=numbers[3].value || numbers[3].value>=1 || numbers[4].value<0)return false;
        double n=numbers[0].value;if(n<0 || n>int.MaxValue || n!=Math.Truncate(n))return false;
        context=new Decision.VolunteerDecisionContext {nearbyAgentCount=(int)n,exitNonBlockage=(float)numbers[1].value,
            volunteerCost=(float)numbers[2].value,failureCost=(float)numbers[3].value,unwillingness=(float)numbers[4].value};
        bool rule;return Classify(context,out rule)!=DecisionKind.Invalid;
    }
    public static double Payoff(bool participates,bool anotherParticipates,double cv,double av)
    {
        if(!(0<cv && cv<av && av<1)) throw new ArgumentOutOfRangeException("costs");
        return participates ? 1-cv : anotherParticipates ? 1 : 1-av;
    }
}
