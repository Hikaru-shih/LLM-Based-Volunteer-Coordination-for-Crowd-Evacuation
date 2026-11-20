using System;
using System.Collections.Generic;
using UnityEngine;

public static class PersonalDecisionProtocol
{
    public const string Version="paper-choice-response-v3";
    public const string ResponseFormat="{\"type\":\"json_schema\",\"json_schema\":{\"name\":\"paper_individual_choice\",\"strict\":true,\"schema\":{\"type\":\"object\",\"properties\":{\"explanation\":{\"type\":\"string\"},\"decision\":{\"type\":\"string\"}},\"required\":[\"explanation\",\"decision\"],\"additionalProperties\":false}}}";
    [Serializable] private sealed class Request
    {public string model;public LLMDecisionPolicy.LLMMessage[] messages;public float temperature=.15f;public int max_tokens=220;}
    public static string Payload(string model,string observation,string information,AgentPromptWording wording)
    {
        string json=JsonUtility.ToJson(new Request {model=model,messages=new[]{
            new LLMDecisionPolicy.LLMMessage("system","You represent one pedestrian making a personal participation decision in a simulated evacuation. Respond with strict JSON only."),
            new LLMDecisionPolicy.LLMMessage("user",PaperVolunteerPrompt.Build(observation,information,wording))}});
        return TransportPayload(model,json.Substring(0,json.Length-1)+",\"response_format\":"+ResponseFormat+"}");
    }
    // v3 requests explanation before action; no server enum, unchanged local two-label whitelist.
    // Task wording remains v5; transport profile remains luna-chat-none-v1.
    // Archived v1 studies remain bound to their frozen source snapshots.
    public static string TransportPayload(string model,string json)
    {
        if(model!="gpt-6-luna")return json;
        json=json.Replace("\"max_tokens\":","\"max_completion_tokens\":");
        if(json.Contains("\"reasoning_effort\""))return json;
        return json.Substring(0,json.Length-1)+",\"reasoning_effort\":\"none\"}";
    }
    public static bool Content(string body,out LLMDecisionPolicy.DecisionResult result,out string error)
    {
        result=null;error="invalid_decision_json";Dictionary<string,object> obj;
        if(body==null || body.Length>262144 || !StrictJson.TryObject(body,out obj) || obj.Count!=2)return false;
        object action,explanation;
        if(!obj.TryGetValue("decision",out action) || !(action is string) || !obj.TryGetValue("explanation",out explanation) || !(explanation is string))return false;
        if(!PaperVolunteerPrompt.IsDecision((string)action)){error="invalid_decision_action";return false;}
        result=new LLMDecisionPolicy.DecisionResult {decision=(string)action,explanation=(string)explanation};error="";return true;
    }
    public static bool EnvelopeContent(string raw,out string content,out string error)
    {
        content=null;error="invalid_response_envelope";Dictionary<string,object> root;object choices;
        if(!StrictJson.TryObject(raw,out root) || !root.TryGetValue("choices",out choices) || !(choices is List<object>))return false;
        var list=(List<object>)choices;if(list.Count!=1 || !(list[0] is Dictionary<string,object>))return false;
        var choice=(Dictionary<string,object>)list[0];object message,finish;
        if(!choice.TryGetValue("message",out message) || !(message is Dictionary<string,object>))return false;
        var msg=(Dictionary<string,object>)message;object role,refusal,text,tools;
        if(!msg.TryGetValue("role",out role) || !(role is string) || (string)role!="assistant")return false;
        if(msg.TryGetValue("refusal",out refusal) && refusal!=null)
        {if(!(refusal is string))return false;if(((string)refusal).Length>0){error="provider_refusal";return false;}}
        if(!choice.TryGetValue("finish_reason",out finish) || !(finish is string) || (string)finish!="stop")
        {error="incomplete_response";return false;}
        if(msg.TryGetValue("tool_calls",out tools) && tools!=null && (!(tools is List<object>) || ((List<object>)tools).Count>0))
        {error="unexpected_tool_calls";return false;}
        if(!msg.TryGetValue("content",out text) || !(text is string) || string.IsNullOrWhiteSpace((string)text))
        {error="empty_response";return false;}
        content=(string)text;error="";return true;
    }
    public static bool Response(string raw,out LLMDecisionPolicy.DecisionResult result,out string error)
    {result=null;string content;return EnvelopeContent(raw,out content,out error) && Content(content,out result,out error);}
}
