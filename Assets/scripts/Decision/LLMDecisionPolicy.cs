using System;
using System.Collections;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.Networking;

[Serializable]
public class LLMDecisionPolicy
{
    [Serializable]
    public class LLMMessage
    {
        public string role;
        public string content;

        public LLMMessage(string role, string content)
        {
            this.role = role;
            this.content = content;
        }
    }

    [Serializable]
    public class ChatRequest
    {
        [Serializable]
        public class ResponseFormat
        {
            public string type;

            public ResponseFormat(string type)
            {
                this.type = type;
            }
        }

        public string model;
        public List<LLMMessage> messages;
        public float temperature = 0.7f;
        public int max_tokens = 300;
        public ResponseFormat response_format;

        public ChatRequest(string model, List<LLMMessage> messages, float temperature, int maxTokens)
        {
            this.model = model;
            this.messages = messages;
            this.temperature = temperature;
            this.max_tokens = maxTokens;
            this.response_format = new ResponseFormat("json_object");
        }
    }

    [Serializable]
    public class ChatResponse
    {
        public Choice[] choices;
        public string model;
        public Usage usage;
    }

    [Serializable]
    public class Usage { public int prompt_tokens; public int completion_tokens; public int total_tokens; }

    [Serializable]
    public class Choice
    {
        public LLMMessage message;
    }

    [Serializable]
    public class VolunteerContext
    {
        public string sharedObservationJson;
        public string informationCondition;
        public AgentPromptWording promptWording;
        public int agentId;
        public string role;
        public int positionX;
        public int positionY;
        public int nearbyAgents;
        public float distanceToExit;
        public int currentVolunteers;
        public int nearbyObstacles;
        public string[] nearbyObstaclePositions; // 新增：附近障礙物位置
        public int mapWidth; // 新增：地圖寬度
        public int mapHeight; // 新增：地圖高度
        public int targetObstacleX;
        public int targetObstacleY;
        public float targetObstacleToExitDistance;
        public int evacueesNearTargetObstacle;
        public float estimatedEvacuationImpact;
        public float exitNonBlockage;
        public float volunteerCost;
        public float failureCost;
        public float unwillingness;
    }

    [Serializable]
    public class DecisionResult
    {
        public string decision;
        public string explanation;
    }

    [Serializable]
    public class AssignmentContext
    {
        public string candidatesJson;
        public string obstaclesJson;
        public string distancesJson;
    }

    [Serializable]
    public class AssignmentResult
    {
        public string assignments;
        public string explanation;
    }

    public string LastPayload { get; private set; }
    public string LastResponse { get; private set; }
    public int LastAttempts { get; private set; }
    public string LastRequestError { get; private set; }
    public void ResetRequestAudit()
    {LastRequestSucceeded=false;LastPayload=LastResponse=LastRequestError="";LastAttempts=0;LastHttpStatus=0;LastExecution="live";attemptAudit.Clear();}
    public const string PaperPromptVersion = AgentObservation.PromptVersion;
    [Serializable] public sealed class AttemptAudit {public int attempt;public long status;public string error;public double elapsedSeconds;}
    private readonly List<AttemptAudit> attemptAudit=new List<AttemptAudit>();
    public AttemptAudit[] LastAttemptAudit => attemptAudit.ToArray();
    public long LastHttpStatus {get;private set;}
    public string LastExecution {get;private set;}="live";
#if UNITY_EDITOR
    public delegate IEnumerator SyntheticTransport(string payload,Action<string,string> callback);
    [NonSerialized] public SyntheticTransport testTransport;
#endif
    private string apiKey;
    public bool LastRequestSucceeded { get; private set; }
    private string model;
    private const string OpenAIChatUrl = "https://api.openai.com/v1/chat/completions";
    private const int MaxRetries = 2;
    private const int RequestTimeoutSeconds = 25;
    public static bool IsRetryableStatus(long status) => status==0 || status==408 || status==409 || status==429 || status>=500;
    [Serializable] private class ErrorEnvelope { public ErrorDetail error; }
    [Serializable] private class ErrorDetail { public string code; public string type; }
    public static string SafeErrorCode(string body)
    {
        try
        {
            var error=JsonUtility.FromJson<ErrorEnvelope>(body)?.error;
            // Never print provider messages: they may echo credential fragments.
            foreach(string value in new[]{error?.code,error?.type})
                switch(value)
                {
                    case "insufficient_quota": case "credit_balance_exhausted":
                    case "organization_spend_limit_exceeded": case "organization_usage_limit_exceeded":
                    case "rate_limit_exceeded": case "rate_limit_error": case "slow_down":
                    case "invalid_api_key": case "model_not_found": return value;
                }
        }
        catch(ArgumentException) { }
        return "unclassified";
    }
    public static bool CanRetry(long status,string code) => IsRetryableStatus(status) &&
        code!="insufficient_quota" && code!="credit_balance_exhausted" &&
        code!="organization_spend_limit_exceeded" && code!="organization_usage_limit_exceeded";

    public LLMDecisionPolicy(string apiKey, string model = "gpt-4.1")
    {
        this.apiKey = apiKey;
        this.model = model;
    }

    public IEnumerator RequestComprehension(string prompt,Action<string> callback)
    {
        ResetRequestAudit();
        if(string.IsNullOrEmpty(apiKey)) {LastRequestError="missing_api_key";callback(null);yield break;}
        var request=new ChatRequest(model,new List<LLMMessage> {
            new LLMMessage("system","Answer factual comprehension questions about a specified simulation game. Do not choose a volunteering action. Return the requested JSON only."),
            new LLMMessage("user",prompt)},0f,160);
        string response=null,error="";
        yield return SendChatRequestWithRetry(request,text=>response=text,text=>error=text);
        if(response==null) {LastRequestError=error;Debug.LogWarning("[COMPREHENSION] Request failed: "+error);callback(null);yield break;}
        string content,errorCode;
        LastRequestSucceeded=PersonalDecisionProtocol.EnvelopeContent(response,out content,out errorCode);
        if(!LastRequestSucceeded)LastRequestError=errorCode;
        callback(content);
    }

    public IEnumerator RequestVolunteerDecision(VolunteerContext context, Action<VolunteerDilemma.CooperationLevel, string> callback)
    {
        ResetRequestAudit();
        if(context==null){LastRequestError="invalid_observation";callback?.Invoke(VolunteerDilemma.CooperationLevel.Selfish,LastRequestError);yield break;}
        bool personal=!string.IsNullOrEmpty(context.sharedObservationJson);
        string information=string.IsNullOrEmpty(context.informationCondition)?AgentInformationCondition.Core.ToString():context.informationCondition;
        if(personal)
        {
            Decision.VolunteerDecisionContext observation;bool rule;
            if(!PaperDecisionSpecification.Observation(context.sharedObservationJson,information,out observation))
            {LastRequestError="invalid_observation";callback?.Invoke(VolunteerDilemma.CooperationLevel.Selfish,LastRequestError);yield break;}
            var kind=PaperDecisionSpecification.Classify(observation,out rule);
            if(kind==PaperDecisionSpecification.DecisionKind.NoGame)
            {LastRequestError="no_game_state";callback?.Invoke(VolunteerDilemma.CooperationLevel.Selfish,LastRequestError);yield break;}

        }
        if(string.IsNullOrEmpty(apiKey))
        {LastRequestError="missing_api_key";callback?.Invoke(VolunteerDilemma.CooperationLevel.Selfish,LastRequestError);yield break;}
        string payload;
        if(personal)payload=PersonalDecisionProtocol.Payload(model,context.sharedObservationJson,information,context.promptWording);
        else payload=JsonUtility.ToJson(new ChatRequest(model,new List<LLMMessage> {
            new LLMMessage("system","You represent one pedestrian making a personal participation decision in a simulated evacuation. Respond with strict JSON only."),
            new LLMMessage("user",CreatePrompt(context))},.15f,220));
        string response=null,error="";
        yield return SendPayloadWithRetry(payload,text=>response=text,code=>error=code);
        if(response==null)
        {LastRequestError=error;callback?.Invoke(VolunteerDilemma.CooperationLevel.Selfish,error);yield break;}
        DecisionResult parsed;
        if(personal)
        {
            if(!PersonalDecisionProtocol.Response(response,out parsed,out error))
            {LastRequestError=error;callback?.Invoke(VolunteerDilemma.CooperationLevel.Selfish,error);yield break;}
        }
        else parsed=ParseDecisionResult(response);
        if(parsed==null){LastRequestError="invalid_legacy_response";callback?.Invoke(VolunteerDilemma.CooperationLevel.Selfish,LastRequestError);yield break;}
        LastRequestSucceeded=true;
        callback?.Invoke(VolunteerDecisionToCooperationLevel(parsed.decision),parsed.explanation??"");
    }

    public IEnumerator RequestVolunteerAssignment(AssignmentContext context, Action<Dictionary<int, int>, string> callback)
    {
        Dictionary<int, int> empty = new Dictionary<int, int>();
        if (string.IsNullOrEmpty(apiKey))
        {
            callback?.Invoke(empty, "openAI api key not configured");
            yield break;
        }

        string prompt =
            "You are assigning volunteers to obstacles in an evacuation simulation.\n" +
            "Use the provided distance rows only. Do not invent agent-obstacle pairs.\n" +
            "Objective: minimize total travel distance while keeping fairness (avoid extremely long assignments when alternatives exist).\n" +
            "At most one volunteer per obstacle and at most one obstacle per volunteer.\n" +
            "Return JSON only with keys assignments and explanation.\n" +
            "assignments format: [{\"agent_id\":123,\"obstacle_id\":456}]\n\n" +
            "candidates: " + context.candidatesJson + "\n" +
            "obstacles: " + context.obstaclesJson + "\n" +
            "distances: " + context.distancesJson + "\n";

        ChatRequest requestData = new ChatRequest(model, new List<LLMMessage>
        {
            new LLMMessage("system", "You are an evacuation coordination assistant. Respond with strict JSON only."),
            new LLMMessage("user", prompt)
        }, 0.05f, 420);

        string responseText = null;
        string error = string.Empty;
        yield return SendChatRequestWithRetry(requestData, text => responseText = text, err => error = err);
        if (string.IsNullOrEmpty(responseText))
        {
            callback?.Invoke(empty, "openai assignment request failed: " + error);
            yield break;
        }

        Dictionary<int, int> parsedAssignments = ParseAssignmentResult(responseText);
        callback?.Invoke(parsedAssignments, string.Empty);
    }

    private IEnumerator SendChatRequestWithRetry(ChatRequest requestData, Action<string> onResponse, Action<string> onError)
    {
        return SendPayloadWithRetry(JsonUtility.ToJson(requestData),onResponse,onError);
    }
    private IEnumerator SendPayloadWithRetry(string payload,Action<string> onResponse,Action<string> onError)
    {
        payload=PersonalDecisionProtocol.TransportPayload(model,payload);
        LastPayload=payload;attemptAudit.Clear();
#if UNITY_EDITOR
        if(testTransport!=null)
        {
            LastExecution="synthetic_test";string body=null,failure="";
            yield return testTransport(payload,(text,error)=>{body=text;failure=error;});
            if(body==null && string.IsNullOrEmpty(failure))failure="missing_transport_response";
            LastResponse=body??"";onResponse(body);onError(failure??"");yield break;
        }
#endif
        byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(payload);
        string lastError = "unknown error";

        for (int attempt = 0; attempt <= MaxRetries; attempt++)
        {
            if(attempt>0) yield return new WaitForSecondsRealtime(Mathf.Pow(2,attempt-1));
            LastAttempts = attempt + 1;
            using (UnityWebRequest request = new UnityWebRequest(OpenAIChatUrl, "POST"))
            {
                request.uploadHandler = new UploadHandlerRaw(bodyRaw);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.timeout = RequestTimeoutSeconds;
                request.SetRequestHeader("Content-Type", "application/json");
                request.SetRequestHeader("Authorization", "Bearer " + apiKey);

                var clock=System.Diagnostics.Stopwatch.StartNew();
                yield return request.SendWebRequest();clock.Stop();LastHttpStatus=request.responseCode;
                string safeCode=request.result==UnityWebRequest.Result.Success?"":SafeErrorCode(request.downloadHandler.text);
                attemptAudit.Add(new AttemptAudit {attempt=attempt+1,status=request.responseCode,error=safeCode,elapsedSeconds=clock.Elapsed.TotalSeconds});

                if (request.result == UnityWebRequest.Result.Success)
                {
                    LastResponse = request.downloadHandler.text;
                    onResponse?.Invoke(LastResponse);
                    onError?.Invoke(string.Empty);
                    yield break;
                }

                string code=SafeErrorCode(request.downloadHandler.text);
                lastError = "http_"+request.responseCode+"_"+code;
                Debug.LogWarning("[LLM] request attempt " + (attempt + 1) + " failed: " + lastError);
                if(!CanRetry(request.responseCode,code)) break;
            }
        }

        onResponse?.Invoke(null);
        onError?.Invoke(lastError);
    }

    private Dictionary<int, int> ParseAssignmentResult(string responseText)
    {
        Dictionary<int, int> result = new Dictionary<int, int>();
        try
        {
            ChatResponse apiResponse = JsonUtility.FromJson<ChatResponse>(responseText);
            if (apiResponse == null || apiResponse.choices == null || apiResponse.choices.Length == 0)
                return result;

            string content = apiResponse.choices[0].message.content;
            if (string.IsNullOrEmpty(content))
                return result;

            MatchCollection matches = Regex.Matches(
                content,
                "\\{[^{}]*\\\"agent_id\\\"\\s*:\\s*(\\d+)[^{}]*\\\"obstacle_id\\\"\\s*:\\s*(\\d+)[^{}]*\\}|\\{[^{}]*\\\"obstacle_id\\\"\\s*:\\s*(\\d+)[^{}]*\\\"agent_id\\\"\\s*:\\s*(\\d+)[^{}]*\\}",
                RegexOptions.IgnoreCase);

            for (int i = 0; i < matches.Count; i++)
            {
                Match m = matches[i];
                int agentId = -1;
                int obstacleId = -1;

                if (m.Groups[1].Success && m.Groups[2].Success)
                {
                    int.TryParse(m.Groups[1].Value, out agentId);
                    int.TryParse(m.Groups[2].Value, out obstacleId);
                }
                else if (m.Groups[3].Success && m.Groups[4].Success)
                {
                    int.TryParse(m.Groups[4].Value, out agentId);
                    int.TryParse(m.Groups[3].Value, out obstacleId);
                }

                if (agentId >= 0 && obstacleId >= 0)
                {
                    result[obstacleId] = agentId;
                }
            }
        }
        catch (Exception)
        {
            return new Dictionary<int, int>();
        }

        return result;
    }

    private string CreatePrompt(VolunteerContext context)
    {
        if (!string.IsNullOrEmpty(context.sharedObservationJson))
            return PaperVolunteerPrompt.Build(context.sharedObservationJson,
                string.IsNullOrEmpty(context.informationCondition) ? AgentInformationCondition.Core.ToString() : context.informationCondition,
                context.promptWording);
        string obstacleList = context.nearbyObstaclePositions.Length > 0 
            ? string.Join(", ", context.nearbyObstaclePositions) 
            : "none";
            
         return $"Given the following evacuation scenario for one candidate volunteer, decide whether the agent should volunteer to remove the target obstacle or remain selfish.\n" +
             "Reasoning priorities: evacuation impact first, then travel burden, then current volunteer load.\n" +
             "Return strict JSON only with keys decision and explanation. decision must be one of [\"volunteer\", \"selfish\"].\n\n" +
               "Scenario:\n" +
               $"agent_id: {context.agentId}\n" +
               $"agent_role: {context.role}\n" +
               $"position: ({context.positionX}, {context.positionY})\n" +
               $"nearby_agents: {context.nearbyAgents}\n" +
               $"exit_non_blockage_fraction: {context.exitNonBlockage}\n" +
               $"volunteer_cost: {context.volunteerCost}\nfailure_cost: {context.failureCost}\nunwillingness: {context.unwillingness}\n" +
               $"distance_to_exit: {context.distanceToExit}\n" +
               $"current_volunteers: {context.currentVolunteers}\n" +
               $"nearby_obstacles: {context.nearbyObstacles}\n" +
               $"nearby_obstacle_positions: {obstacleList}\n" +
             $"target_obstacle: ({context.targetObstacleX}, {context.targetObstacleY})\n" +
             $"target_obstacle_to_exit_distance: {context.targetObstacleToExitDistance:F2}\n" +
             $"evacuees_near_target_obstacle: {context.evacueesNearTargetObstacle}\n" +
             $"estimated_evacuation_impact: {context.estimatedEvacuationImpact:F2}\n" +
               $"map_size: {context.mapWidth}x{context.mapHeight}\n";
    }

    private DecisionResult ParseDecisionResult(string responseText)
    {
        try
        {
            ChatResponse apiResponse = JsonUtility.FromJson<ChatResponse>(responseText);
            
            if (apiResponse == null || apiResponse.choices == null || apiResponse.choices.Length == 0)
            {
                Debug.LogError("[LLM] No choices in API response");
                return null;
            }
            
            string messageContent = apiResponse.choices[0].message.content;
            if (string.IsNullOrEmpty(messageContent))
            {
                Debug.LogError("[LLM] Message content is empty");
                return null;
            }
            
            Debug.Log("[LLM] Raw message content: " + messageContent);
            
            int jsonStart = messageContent.IndexOf('{');
            int jsonEnd = messageContent.LastIndexOf('}');
            
            if (jsonStart < 0 || jsonEnd < 0 || jsonEnd <= jsonStart)
            {
                Debug.LogError("[LLM] No JSON found in message content");
                return null;
            }
            
            string jsonStr = messageContent.Substring(jsonStart, jsonEnd - jsonStart + 1);
            Debug.Log("[LLM] Extracted JSON: " + jsonStr);

            DecisionResult result = JsonUtility.FromJson<DecisionResult>(jsonStr);
            if (result == null || (!string.Equals(result.decision, "volunteer", StringComparison.OrdinalIgnoreCase)
                && !string.Equals(result.decision, "selfish", StringComparison.OrdinalIgnoreCase)
                && !string.Equals(result.decision, "participate", StringComparison.OrdinalIgnoreCase)
                && !string.Equals(result.decision, "decline_assistance", StringComparison.Ordinal))) return null;
            if (!string.IsNullOrEmpty(result.decision))
            {
                Debug.Log("[LLM] Extracted decision: " + result.decision);
            }
            
            return result;
        }
        catch (System.Exception e)
        {
            Debug.LogError("[LLM] Parse error: " + e.Message + "\n" + e.StackTrace);
            return null;
        }
    }

    private string ExtractJsonStringValue(string json, string key)
    {
        string pattern = "\\\"" + Regex.Escape(key) + "\\\"\\s*:\\s*\\\"([^\\\"]*)\\\"";
        Match m = Regex.Match(json, pattern, RegexOptions.IgnoreCase);
        return m.Success ? m.Groups[1].Value : string.Empty;
    }

    private VolunteerDilemma.CooperationLevel VolunteerDecisionToCooperationLevel(string value)
    {
        if (string.Equals(value, "volunteer", StringComparison.OrdinalIgnoreCase) || string.Equals(value, "participate", StringComparison.OrdinalIgnoreCase))
            return VolunteerDilemma.CooperationLevel.Cooperative;
        return VolunteerDilemma.CooperationLevel.Selfish;
    }
}
