using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

public static class LLMComprehensionRunner
{
    [Serializable] private class Trace
    {public string questionID,payload,response,content,requestError;public bool transportSucceeded;public int attempts;public LLMComprehensionSuite.Grade grade;}
    [Serializable] private class Summary
    {public string suiteVersion,specVersion,model,outcome;public int totalQuestions,attempted,correct,invalid,httpAttempts;public bool passed;}
    [Serializable] private class QuestionFile {public LLMComprehensionSuite.Question[] questions;}
    public static bool Running {get;private set;}
    public static string Status {get;private set;}="Not started";
    public static string Output {get;private set;}
    private static string root,id,model,outcome;
    private static LLMDecisionPolicy client;
    private static LLMComprehensionSuite.Question current;
    private static Summary summary;
    private static readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();
    private static AsyncOperation waiting;
    private static bool quit;
    private static double deadline;
    private static LLMComprehensionSuite.Question[] selectedQuestions;

    [MenuItem("Research/LLM comprehension/Open runner (no call)")]
    public static void Open() {EditorWindow.GetWindow<LLMComprehensionWindow>("LLM comprehension");}

    public static void Start(string selectedModel,int limit,string recordRoot=null,bool quitWhenDone=false,string credentialRoot=null,bool singlePlayerDiagnostic=false,bool fullPayoffDiagnostic=false)
    {
        if(Running || EditorApplication.isPlaying) throw new InvalidOperationException("Stop Play before starting an isolated comprehension check");
        selectedQuestions=fullPayoffDiagnostic?PayoffDiagnosticSuite.Questions():singlePlayerDiagnostic?SinglePlayerPayoffDiagnostic.Questions():LLMComprehensionSuite.Questions();
        if(singlePlayerDiagnostic)SinglePlayerPayoffDiagnostic.ValidateOffline();
        if(fullPayoffDiagnostic)PayoffDiagnosticSuite.ValidateOffline();
        if(limit<1 || limit>selectedQuestions.Length || string.IsNullOrWhiteSpace(selectedModel)) throw new ArgumentException("Choose a model and a question count within the current suite");
        root=Path.GetFullPath(recordRoot??AutomaticExperimentLog.DefaultRoot);
        id="comprehension_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")+"_"+Guid.NewGuid().ToString("N").Substring(0,8);
        Output=Path.Combine(root,"data","comprehension",id);Directory.CreateDirectory(Output);
        quit=quitWhenDone;model=selectedModel;
        summary=new Summary {suiteVersion=fullPayoffDiagnostic?PayoffDiagnosticSuite.Version:singlePlayerDiagnostic?SinglePlayerPayoffDiagnostic.Version:LLMComprehensionSuite.Version,specVersion=PaperVolunteerPrompt.Version,model=model,totalQuestions=selectedQuestions.Length};
        File.WriteAllText(Path.Combine(Output,"suite_key.json"),JsonUtility.ToJson(new QuestionFile {questions=selectedQuestions},true));
        File.WriteAllText(Path.Combine(Output,"public_rules.txt"),PaperVolunteerPrompt.Instructions("Core",AgentPromptWording.Standard));
        Running=true;outcome=null;waiting=null;stack.Clear();
        try
        {
            string key=credentialRoot==null ? LocalOpenAIKey.Load() : File.ReadAllText(Path.Combine(credentialRoot,"openai-key.local.txt")).Trim().TrimStart('\uFEFF');
            if(string.IsNullOrEmpty(key) || !LocalOpenAIKey.HasValidLocalFormat(key)) {Finish("invalid_local_credential");return;}
            client=new LLMDecisionPolicy(key,model);stack.Push(Questions(limit));deadline=EditorApplication.timeSinceStartup+600;
            EditorApplication.update+=Tick;EditorApplication.quitting+=Cancel;AssemblyReloadEvents.beforeAssemblyReload+=Cancel;
            Status="Running 0/"+limit+" (no evacuation simulation)";
        }
        catch(IOException) {Finish("invalid_credential_or_output_io");}
        catch(UnauthorizedAccessException) {Finish("invalid_credential_or_output_access");}
    }
    private static IEnumerator Questions(int limit)
    {
        var questions=selectedQuestions;
        for(int i=0;i<limit;i++)
        {
            current=questions[i];client.ResetRequestAudit();summary.attempted++;string content=null;
            Status="Question "+(i+1)+"/"+limit+": "+current.id;
            yield return client.RequestComprehension(LLMComprehensionSuite.Prompt(current).Replace("Comprehension task: "+LLMComprehensionSuite.Version,"Comprehension task: "+summary.suiteVersion),text=>content=text);
            var grade=content==null ? new LLMComprehensionSuite.Grade {error="request_or_envelope_failure"} : LLMComprehensionSuite.Evaluate(current,content);
            summary.httpAttempts+=client.LastAttempts;
            if(grade.correct) summary.correct++;
            if(!grade.valid) summary.invalid++;
            SaveTrace(content,grade);current=null;
            File.WriteAllText(Path.Combine(Output,"progress.json"),JsonUtility.ToJson(summary,true));
            if(!client.LastRequestSucceeded) {outcome="invalid_api_or_response";yield break;}
        }
        outcome=limit<questions.Length ? "partial_question_budget" : summary.correct==questions.Length ? "completed_pass" : "completed_not_passed";
    }
    private static void SaveTrace(string content,LLMComprehensionSuite.Grade grade)
    {
        File.AppendAllText(Path.Combine(Output,"trace.jsonl"),JsonUtility.ToJson(new Trace {questionID=current.id,
            payload=client.LastPayload,response=client.LastResponse,content=content,transportSucceeded=client.LastRequestSucceeded,
            attempts=client.LastAttempts,grade=grade,requestError=client.LastRequestError})+Environment.NewLine);
    }
    private static void Tick()
    {
        try
        {
            if(EditorApplication.timeSinceStartup>deadline) {Finish("interrupted_wall_clock_limit");return;}
            if(waiting!=null) {if(!waiting.isDone) return;waiting=null;}
            if(stack.Count==0) {Finish(outcome??"invalid_runner_state");return;}
            var routine=stack.Peek();
            if(!routine.MoveNext()) {stack.Pop();return;}
            if(routine.Current is IEnumerator nested) stack.Push(nested);
            else if(routine.Current is AsyncOperation operation) waiting=operation;
        }
        catch(Exception error) {Debug.LogWarning("[COMPREHENSION] Runner stopped: "+error.GetType().Name);Finish("invalid_runner_exception");}
    }
    public static void Cancel() {if(Running) Finish("interrupted_by_user_or_editor");}
    private static void Finish(string reason)
    {
        if(!Running) return;
        Running=false;EditorApplication.update-=Tick;EditorApplication.quitting-=Cancel;AssemblyReloadEvents.beforeAssemblyReload-=Cancel;
        if(current!=null && client!=null)
        {
            summary.httpAttempts+=client.LastAttempts;summary.invalid++;
            SaveTrace(null,new LLMComprehensionSuite.Grade {error="interrupted_in_flight"});current=null;
        }
        while(stack.Count>0)
        {
            try {(stack.Pop() as IDisposable)?.Dispose();}
            catch(Exception error) {Debug.LogWarning("[COMPREHENSION] Request cleanup: "+error.GetType().Name);}
        }
        summary.outcome=reason;summary.passed=reason=="completed_pass";
        File.WriteAllText(Path.Combine(Output,"summary.json"),JsonUtility.ToJson(summary,true));
        var record=new AutomaticAssessmentRecord {recordID=id,purpose="Check understanding of the paper's payoffs and task rules without prescribing cooperation",
            recordedAtUtc=DateTime.UtcNow.ToString("o"),kind="comprehension",model=model,specVersion=PaperVolunteerPrompt.Version,
            promptHash=PaperVolunteerPrompt.Hash("Core",AgentPromptWording.Standard),dataDirectory=Path.GetRelativePath(root,Output).Replace('\\','/'),
            outcome=reason,logicalCalls=summary.attempted,httpAttempts=summary.httpAttempts,passedChecks=summary.correct,totalChecks=selectedQuestions.Length,
            summary="Suite: "+summary.suiteVersion+". A pass requires all factual checks in this suite correct. Supplemental single-player diagnostics do not replace the original v3 assessment. Partial, invalid and interrupted assessments are not passes. This is a factual check, not a volunteering choice or evidence of general model competence."};
        try {AutomaticExperimentLog.PublishAssessment(root,record);}
        catch(Exception error) when(error is IOException || error is UnauthorizedAccessException)
        {File.WriteAllText(Path.Combine(Output,id+"_assessment_pending.json"),JsonUtility.ToJson(record,true));}
        Status=reason+": "+summary.correct+"/"+selectedQuestions.Length+" correct; "+summary.attempted+" logical calls";
        Debug.Log("[COMPREHENSION] "+Status+". Data: "+Output);
        if(quit) EditorApplication.Exit(reason=="completed_pass" ? 0 : 1);
    }
    // Explicit batch entry point. Use without -quit; it exits after the asynchronous assessment.
    public static void RunBatch()
    {
        var args=Environment.GetCommandLineArgs();
        Func<string,string,string> option=(name,fallback)=> {int index=Array.IndexOf(args,name);return index>=0 && index+1<args.Length?args[index+1]:fallback;};
        bool diagnostic=option("-singlePlayerDiagnostic","false")=="true";
        bool full=option("-payoffDiagnostic","false")=="true";
        int total=full?PayoffDiagnosticSuite.Questions().Length:diagnostic?SinglePlayerPayoffDiagnostic.Questions().Length:LLMComprehensionSuite.Questions().Length;
        Start(option("-comprehensionModel","gpt-4o-mini"),int.Parse(option("-comprehensionLimit",total.ToString())),
            option("-recordsRoot",AutomaticExperimentLog.DefaultRoot),true,option("-credentialRoot",null),diagnostic,full);
    }
}

