using System;

// Supplemental factual diagnostic, not a participation policy or a replacement for v3.
public static class SinglePlayerPayoffDiagnostic
{
    public const string Version="paper-single-payoff-diagnostic-v1";
    public static LLMComprehensionSuite.Question[] Questions() => new[] {
        new LLMComprehensionSuite.Question {id="single_help_payoff",numeric=true,expectedAnswer="0.95",question="Use the base payoff table only. X=1 including you, tau=0.5, cv=0.05 and av=0.5. You participate. What is your normalized payoff? Return a numeric string."},
        new LLMComprehensionSuite.Question {id="single_decline_partial",numeric=true,expectedAnswer="0.5",question="Use the base payoff table only. X=1 including you, tau=0.5, cv=0.05 and av=0.5. You decline assistance and there are no other eligible players. What is your normalized payoff? Return a numeric string."},
        new LLMComprehensionSuite.Question {id="single_decline_blocked",numeric=true,expectedAnswer="0.5",question="Use the base payoff table only. X=1 including you, tau=0, cv=0.05 and av=0.5. You decline assistance and there are no other eligible players. What is your normalized payoff? Return a numeric string."}
    };
    public static void ValidateOffline()
    {
        foreach(var q in Questions())
        {
            string correct="{\"question_id\":\""+q.id+"\",\"answer\":\""+q.expectedAnswer+"\"}";
            if(!LLMComprehensionSuite.Evaluate(q,correct).correct)throw new Exception("Diagnostic answer key failed");
            string wrong="{\"question_id\":\""+q.id+"\",\"answer\":\"1\"}";
            if(LLMComprehensionSuite.Evaluate(q,wrong).correct)throw new Exception("Diagnostic accepted wrong single-player payoff");
        }
    }
}
