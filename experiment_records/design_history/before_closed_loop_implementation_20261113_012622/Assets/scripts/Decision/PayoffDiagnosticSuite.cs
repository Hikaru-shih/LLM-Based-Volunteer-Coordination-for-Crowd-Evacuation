using System;
using System.Linq;

// Factual questions only. Answers never prescribe a willingness decision.
public static class PayoffDiagnosticSuite
{
    public const string Version="paper-payoff-diagnostic-v2";
    public static LLMComprehensionSuite.Question[] Questions() => SinglePlayerPayoffDiagnostic.Questions().Concat(new[] {
        new LLMComprehensionSuite.Question {id="multi_help",numeric=true,expectedAnswer="0.95",question="Base payoff table only: X=5, tau=0.5, cv=0.05, av=0.5. You participate and all others decline. What is your payoff? Return a numeric string."},
        new LLMComprehensionSuite.Question {id="multi_free_ride",numeric=true,expectedAnswer="1",question="Base payoff table only: X=5, tau=0.5, cv=0.05, av=0.5. You decline and another player participates. What is your payoff? Return a numeric string."},
        new LLMComprehensionSuite.Question {id="multi_nobody",numeric=true,expectedAnswer="0.5",question="Base payoff table only: X=5, tau=0.5, cv=0.05, av=0.5. You and every other player decline. What is your payoff? Return a numeric string."},
        new LLMComprehensionSuite.Question {id="multi_high_help",numeric=true,expectedAnswer="0.8",question="Base payoff table only: X=5, tau=0, cv=0.2, av=0.5. You participate. What is your payoff? Return a numeric string."},
        new LLMComprehensionSuite.Question {id="multi_high_nobody",numeric=true,expectedAnswer="0.5",question="Base payoff table only: X=5, tau=0, cv=0.2, av=0.5. You and every other player decline. What is your payoff? Return a numeric string."}
    }).ToArray();
    public static void ValidateOffline()
    {
        var questions=Questions();
        if(questions.Select(q=>q.id).Distinct().Count()!=8)throw new Exception("Duplicate diagnostic ID");
        foreach(var q in questions)
        {
            string json="{\"question_id\":\""+q.id+"\",\"answer\":\""+q.expectedAnswer+"\"}";
            if(!LLMComprehensionSuite.Evaluate(q,json).correct)throw new Exception("Payoff diagnostic key failed");
            if(LLMComprehensionSuite.Evaluate(q,json.Replace(q.expectedAnswer+"\"}","-99\"}")).correct)throw new Exception("Wrong payoff accepted");
        }
    }
}
