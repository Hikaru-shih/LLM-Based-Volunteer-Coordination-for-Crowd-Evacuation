using System;
using System.IO;
using UnityEngine;

/// <summary>Append-only API audit and strict, sequential decision replay. Contains no credentials.</summary>
public sealed class PaperAgentDecisionJournal
{
    [Serializable]
    public class Entry
    {
        public string promptVersion, observation, requestedModel, payload, response, explanation,conditionKey;
        public string error,promptTemplateHash,responseValidationVersion,execution,referenceKind;
        public long httpStatus;
        public LLMDecisionPolicy.AttemptAudit[] attemptAudit;
        public int step, agent, obstacle, attempts;
        public bool willing, succeeded;
        public double elapsedSeconds;
    }
    private string loadedPath;
    private string[] lines;
    private int cursor;

    public void Record(string path,int step,int agent,int obstacle,string observation,bool willing,
        string explanation,bool succeeded,string model,string payload,string response,int attempts,double seconds,string conditionKey="",string error="",string promptHash="",string execution="live",long httpStatus=0,LLMDecisionPolicy.AttemptAudit[] attemptAudit=null)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path)));
        var entry=new Entry {promptVersion=LLMDecisionPolicy.PaperPromptVersion,step=step,agent=agent,
            obstacle=obstacle,observation=observation,willing=willing,explanation=explanation,succeeded=succeeded,
            requestedModel=model,payload=payload,response=response,attempts=attempts,elapsedSeconds=seconds,conditionKey=conditionKey,error=error,promptTemplateHash=promptHash,responseValidationVersion=PersonalDecisionProtocol.Version,execution=execution,httpStatus=httpStatus,attemptAudit=attemptAudit??new LLMDecisionPolicy.AttemptAudit[0]};
        Decision.VolunteerDecisionContext context;bool referenceWilling;
        entry.referenceKind=PaperDecisionSpecification.Observation(observation,"SharedContext",out context)
            ? PaperDecisionSpecification.Classify(context,out referenceWilling).ToString():"unknown";
        File.AppendAllText(path,JsonUtility.ToJson(entry)+Environment.NewLine);
    }

    public bool ReplayFullyConsumed(string path)
    {
        try{return loadedPath==Path.GetFullPath(path) ? cursor==lines.Length : File.ReadAllLines(path).Length==0;}
        catch(IOException){return false;}catch(UnauthorizedAccessException){return false;}
    }

    public bool TryReplay(string path,int step,int agent,int obstacle,string observation,
        out bool willing,out string explanation,out string error,string expectedCondition="",string expectedModel="",string expectedPromptHash="",string expectedPayload="")
    {
        willing=false; explanation=""; error="";
        try
        {
            string absolute=Path.GetFullPath(path);
            if(loadedPath!=absolute) {lines=File.ReadAllLines(absolute);cursor=0;loadedPath=absolute;}
            if(cursor>=lines.Length) {error="Decision trace exhausted";return false;}
            var entry=JsonUtility.FromJson<Entry>(lines[cursor]);
            if(entry==null || !entry.succeeded || !string.IsNullOrEmpty(entry.error) || entry.promptVersion!=LLMDecisionPolicy.PaperPromptVersion ||
                entry.responseValidationVersion!=PersonalDecisionProtocol.Version ||
                (!string.IsNullOrEmpty(expectedPromptHash) && entry.promptTemplateHash!=expectedPromptHash) ||
                (!string.IsNullOrEmpty(expectedPayload) && entry.payload!=expectedPayload) ||
                entry.step!=step || entry.agent!=agent || entry.obstacle!=obstacle || entry.observation!=observation ||
                (!string.IsNullOrEmpty(expectedCondition) && entry.conditionKey!=expectedCondition) ||
                (!string.IsNullOrEmpty(expectedModel) && entry.requestedModel!=expectedModel))
            {error="Decision trace mismatch at entry "+cursor;return false;}
            LLMDecisionPolicy.DecisionResult decision;string validationError;
            if(!PersonalDecisionProtocol.Response(entry.response,out decision,out validationError) ||
                entry.willing!=(decision.decision==PaperVolunteerPrompt.Participate) || entry.explanation!=decision.explanation)
            {error="Decision trace response failed revalidation at entry "+cursor;return false;}
            cursor++;willing=entry.willing;explanation=entry.explanation;return true;
        }
        catch(Exception exception) {error="Decision trace read failed: "+exception.GetType().Name;return false;}
    }
}
