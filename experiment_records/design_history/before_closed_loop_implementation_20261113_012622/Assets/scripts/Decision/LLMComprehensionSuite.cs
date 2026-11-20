using System;
using System.Globalization;
using UnityEngine;

public static class LLMComprehensionSuite
{
    public const string Version="paper-comprehension-v3";
    [Serializable] public class Question { public string id,question,expectedAnswer; public bool numeric; }
    [Serializable] public class Answer { public string question_id,answer; }
    [Serializable] public class Grade { public bool valid,correct;public string answer,error; }
    public static Question[] Questions() => new[] {
        new Question {id="payoff_participate",numeric=true,expectedAnswer="0.98",question="For cv=0.02 and av=0.6, you participate and every other player declines. What is your normalized payoff? Return a numeric string."},
        new Question {id="payoff_free_ride",numeric=true,expectedAnswer="1",question="For cv=0.02 and av=0.6, you decline and at least one other player participates. What is your normalized payoff? Return a numeric string."},
        new Question {id="payoff_nobody",numeric=true,expectedAnswer="0.4",question="For cv=0.02 and av=0.6, you and all other players decline. What is your normalized payoff? Return a numeric string."},
        new Question {id="loss_meaning",expectedAnswer="B",question="What does av (failureCost) mean? A: injury risk caused by participating. B: loss when nobody volunteers. C: measured manipulation duration. Return A, B or C."},
        new Question {id="decline_not_escape",expectedAnswer="false",question="True or false: choosing decline_assistance guarantees that the pedestrian can leave the room. Return true or false."},
        new Question {id="candidate_not_handler",expectedAnswer="false",question="True or false: choosing participate instantly moves the obstacle and guarantees successful placement. Return true or false."},
        new Question {id="omega_not_personality",expectedAnswer="C",question="What is omega=5? A: a compulsory refusal. B: a danger or personality rating out of five. C: a nonnegative reference-model coefficient, separate from the payoff costs. Return A, B or C."},
        new Question {id="base_not_adjusted_law",expectedAnswer="false",question="True or false: the base payoff table alone completely specifies the reference simulator's exit-nonblockage/unwillingness adjustments. Return true or false."},
        new Question {id="reference_not_prescription",expectedAnswer="false",question="True or false: the reference model's separate single-player behavioral branch prescribes your action when your personal decision is requested. Return true or false."},
        new Question {id="blockage_scope",expectedAnswer="A",question="Given only Core observations with tau=0, what is known? A: the relevant exit is fully blocked. B: every exit in the room is blocked. C: the target obstacle is immovable. Return A, B or C."}
    };
    public static string Prompt(Question question)
    {
        string specification=PaperVolunteerPrompt.Instructions(AgentInformationCondition.Core.ToString(),AgentPromptWording.Standard);
        int first=specification.IndexOf("Actions:",StringComparison.Ordinal);
        int last=specification.IndexOf("This is a fresh individual decision",StringComparison.Ordinal);
        if(first<0 || last<=first) throw new InvalidOperationException("Public specification boundary changed; review comprehension suite");
        return "Comprehension task: "+Version+". Read the public game rules below. This is a factual question, not a request to choose whether to volunteer.\n"+
            specification.Substring(first,last-first)+
            "Answer only the following question. Return a JSON object with exactly question_id and answer, both strings; no explanation or participation decision.\n"+
            "question_id: "+question.id+"\nQuestion: "+question.question;
    }
    public static Grade Evaluate(Question question,string content)
    {
        try
        {
            System.Collections.Generic.Dictionary<string,object> parsed;object id,valueText;
            if(!StrictJson.TryObject(content,out parsed) || parsed.Count!=2 || !parsed.TryGetValue("question_id",out id) || !(id is string) ||
                (string)id!=question.id || !parsed.TryGetValue("answer",out valueText) || !(valueText is string) || string.IsNullOrWhiteSpace((string)valueText))
                return new Grade {error="invalid_comprehension_json"};
            string answer=((string)valueText).Trim();
            if(question.numeric)
            {
                double value;
                if(!double.TryParse(answer,NumberStyles.Float,CultureInfo.InvariantCulture,out value) || double.IsNaN(value) || double.IsInfinity(value))
                    return new Grade {answer=answer,error="not_a_finite_numeric_answer"};
                double expected=double.Parse(question.expectedAnswer,CultureInfo.InvariantCulture);
                return new Grade {valid=true,correct=Math.Abs(value-expected)<=1e-6,answer=answer};
            }
            bool boolean=question.expectedAnswer=="true" || question.expectedAnswer=="false";
            bool allowed=boolean ? string.Equals(answer,"true",StringComparison.OrdinalIgnoreCase) || string.Equals(answer,"false",StringComparison.OrdinalIgnoreCase)
                : answer.Length==1 && "ABC".Contains(answer.ToUpperInvariant());
            return new Grade {valid=allowed,correct=allowed && string.Equals(answer,question.expectedAnswer,StringComparison.OrdinalIgnoreCase),
                answer=answer,error=allowed ? null : "answer_outside_allowed_options"};
        }
        catch(ArgumentException) {return new Grade {error="malformed_json"};}
    }
}
