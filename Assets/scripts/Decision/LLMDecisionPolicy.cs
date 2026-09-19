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
    }

    [Serializable]
    public class Choice
    {
        public LLMMessage message;
    }

    [Serializable]
    public class VolunteerContext
    {
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

    private string apiKey;
    private string model;
    private const string OpenAIChatUrl = "https://api.openai.com/v1/chat/completions";
    private const int MaxRetries = 2;
    private const int RequestTimeoutSeconds = 25;

    public LLMDecisionPolicy(string apiKey, string model = "gpt-4.1")
    {
        this.apiKey = apiKey;
        this.model = model;
    }

    public IEnumerator RequestVolunteerDecision(VolunteerContext context, Action<VolunteerDilemma.CooperationLevel, string> callback)
    {
        if (string.IsNullOrEmpty(apiKey))
        {
            Debug.LogWarning("[LLM] OpenAI API key is not configured");
            callback?.Invoke(VolunteerDilemma.CooperationLevel.Selfish, "openAI api key not configured");
            yield break;
        }

        string prompt = CreatePrompt(context);
        ChatRequest requestData = new ChatRequest(model, new List<LLMMessage>
        {
            new LLMMessage("system", "You are an evacuation decision-making assistant. Respond with strict JSON only."),
            new LLMMessage("user", prompt)
        }, 0.15f, 220);

        string responseText = null;
        string error = string.Empty;
        Debug.Log("[LLM] Sending request to OpenAI for volunteer decision (agent " + context.agentId + ")");
        yield return SendChatRequestWithRetry(requestData, text => responseText = text, err => error = err);

        if (string.IsNullOrEmpty(responseText))
        {
            callback?.Invoke(VolunteerDilemma.CooperationLevel.Selfish, "openai request failed: " + error);
            yield break;
        }

        DecisionResult parsed = ParseDecisionResult(responseText);
        if (parsed == null || string.IsNullOrEmpty(parsed.decision))
        {
            Debug.LogError("[LLM] Failed to parse API response");
            callback?.Invoke(VolunteerDilemma.CooperationLevel.Selfish, "failed to parse llm response");
            yield break;
        }

        VolunteerDilemma.CooperationLevel decision = VolunteerDecisionToCooperationLevel(parsed.decision);
        Debug.Log("[LLM] Decision made: " + decision + " | Explanation: " + parsed.explanation);
        callback?.Invoke(decision, parsed.explanation ?? string.Empty);
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
        string payload = JsonUtility.ToJson(requestData);
        byte[] bodyRaw = System.Text.Encoding.UTF8.GetBytes(payload);
        string lastError = "unknown error";

        for (int attempt = 0; attempt <= MaxRetries; attempt++)
        {
            using (UnityWebRequest request = new UnityWebRequest(OpenAIChatUrl, "POST"))
            {
                request.uploadHandler = new UploadHandlerRaw(bodyRaw);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.timeout = RequestTimeoutSeconds;
                request.SetRequestHeader("Content-Type", "application/json");
                request.SetRequestHeader("Authorization", "Bearer " + apiKey);

                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    onResponse?.Invoke(request.downloadHandler.text);
                    onError?.Invoke(string.Empty);
                    yield break;
                }

                lastError = request.error + " (status=" + request.responseCode + ")";
                Debug.LogWarning("[LLM] request attempt " + (attempt + 1) + " failed: " + lastError);
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

            DecisionResult result = new DecisionResult();

            result.decision = ExtractJsonStringValue(jsonStr, "decision");
            result.explanation = ExtractJsonStringValue(jsonStr, "explanation");
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
        if (string.Equals(value, "volunteer", StringComparison.OrdinalIgnoreCase))
            return VolunteerDilemma.CooperationLevel.Cooperative;
        return VolunteerDilemma.CooperationLevel.Selfish;
    }
}