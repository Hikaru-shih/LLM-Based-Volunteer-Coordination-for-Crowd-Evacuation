using System;
using System.IO;
using UnityEngine;

public static class LLMComprehensionValidation
{
    public static void Run()
    {
        AutomaticExperimentLogValidation.Run();
        var questions=LLMComprehensionSuite.Questions();if(questions.Length!=10) throw new Exception("Unexpected suite size");
        int checks=0;
        foreach(var question in questions)
        {
            string correct=JsonUtility.ToJson(new LLMComprehensionSuite.Answer {question_id=question.id,answer=question.expectedAnswer});
            var grade=LLMComprehensionSuite.Evaluate(question,correct);
            if(!grade.valid || !grade.correct) throw new Exception("Correct answer rejected");checks++;
            string wrong=JsonUtility.ToJson(new LLMComprehensionSuite.Answer {question_id=question.id,answer=question.numeric ? "0.12345" : question.expectedAnswer=="false" ? "true" : "C"==question.expectedAnswer ? "A" : "C"});
            if(LLMComprehensionSuite.Evaluate(question,wrong).correct) throw new Exception("Incorrect answer accepted");checks++;
            if(LLMComprehensionSuite.Evaluate(question,"{\"question_id\":\"wrong\",\"answer\":\"1\"}").valid ||
                LLMComprehensionSuite.Evaluate(question,"not-json").valid) throw new Exception("Invalid envelope accepted");checks++;
            string prompt=LLMComprehensionSuite.Prompt(question);
            if(prompt.Contains("expectedAnswer") || prompt.Contains("Answer key") || prompt.Contains("Return a JSON object with exactly decision"))
                throw new Exception("Answer key or participation-output instruction leaked");checks++;
        }
        string root=Path.Combine(Path.GetTempPath(),"assessment-contract-"+Guid.NewGuid().ToString("N"));
        try
        {
            Directory.CreateDirectory(root);File.WriteAllText(Path.Combine(root,"EXPERIMENT_LOG.md"),"# Manual note\nPreserve this observation.\n");
            var record=new AutomaticAssessmentRecord {recordID="synthetic-comprehension-not-a-real-run",purpose="Test comprehension publication",
                kind="comprehension",model="synthetic",specVersion=PaperVolunteerPrompt.Version,recordedAtUtc=DateTime.UtcNow.ToString("o"),
                dataDirectory="data/comprehension/synthetic",outcome="partial_question_budget",summary="Synthetic contract check, not model evidence.",passedChecks=1,totalChecks=10,logicalCalls=1};
            AutomaticExperimentLog.PublishAssessment(root,record);AutomaticExperimentLog.PublishAssessment(root,record);
            if(File.ReadAllLines(Path.Combine(root,"ASSESSMENT_CATALOG.csv")).Length!=2 ||
                File.Exists(Path.Combine(root,"RUN_CATALOG.csv")) ||
                !File.ReadAllText(Path.Combine(root,"EXPERIMENT_LOG.md")).Contains("Preserve this observation."))
                throw new Exception("Assessment deduplication/separation/manual preservation failed");checks++;
            string folder=Path.Combine(root,"data/comprehension/pending");Directory.CreateDirectory(folder);
            record.recordID="synthetic-pending-assessment";
            File.WriteAllText(Path.Combine(folder,"retry_assessment_pending.json"),JsonUtility.ToJson(record));
            if(AutomaticExperimentLog.RecoverAssessments(root)!=1) throw new Exception("Assessment recovery failed");checks++;
        }
        finally {if(Directory.Exists(root)) Directory.Delete(root,true);}
        Directory.CreateDirectory("tmp/comprehension-validation");
        File.WriteAllText("tmp/comprehension-validation/result.json","{\"passed\":true,\"checks\":"+checks+",\"remoteRequests\":0,\"suite\":\""+LLMComprehensionSuite.Version+"\"}");
        Debug.Log("LLM_COMPREHENSION_VALIDATION_PASSED: "+checks+" offline checks; no API or evacuation steps");
    }
}
