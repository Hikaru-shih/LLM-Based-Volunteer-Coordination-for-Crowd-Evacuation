using System;
using System.IO;
using System.Reflection;
using UnityEngine;

public static class PaperAgentContractValidation
{
    // Contract checks only: no simulation steps, API calls or experiment output.
    public static void Run()
    {
        string path=Path.Combine(Path.GetTempPath(),Guid.NewGuid()+".jsonl");
        try
        {
            ValidateRandomIsolation();
            ValidateResearchControls();
            ValidateStudyLock();
            if(LLMDecisionPolicy.SafeErrorCode("{\"error\":{\"code\":\"insufficient_quota\"}}")!="insufficient_quota" ||
                LLMDecisionPolicy.CanRetry(429,"insufficient_quota") || !LLMDecisionPolicy.CanRetry(429,"rate_limit_exceeded"))
                throw new Exception("Quota/rate error classification failed");
            if(LLMDecisionPolicy.IsRetryableStatus(401) || LLMDecisionPolicy.IsRetryableStatus(403) ||
                !LLMDecisionPolicy.IsRetryableStatus(429) || !LLMDecisionPolicy.IsRetryableStatus(503))
                throw new Exception("HTTP retry classification failed");
            if(LocalOpenAIKey.HasValidLocalFormat("example key") || LocalOpenAIKey.HasValidLocalFormat("\"example\"") ||
                !LocalOpenAIKey.HasValidLocalFormat("example-test-only"))
                throw new Exception("Local credential format classification failed");
            var journal=new PaperAgentDecisionJournal();
            string recordedContent=JsonUtility.ToJson(new LLMDecisionPolicy.DecisionResult {decision="participate",explanation="test"});
            string recordedBody=@"{""choices"":[{""finish_reason"":""stop"",""message"":"+JsonUtility.ToJson(new LLMDecisionPolicy.LLMMessage("assistant",recordedContent))+@"}]}";
            journal.Record(path,1,2,3,"observation",true,"test",true,"model","{}",recordedBody,1,0.5,"physical");
            bool willing;string explanation,error;
            if(journal.ReplayFullyConsumed(path)) throw new Exception("Unread trace was marked consumed");
            if(journal.TryReplay(path,1,2,3,"observation",out willing,out explanation,out error,"different","model"))
                throw new Exception("Changed prompt/physical condition accepted for replay");
            if(journal.TryReplay(path,1,2,3,"observation",out willing,out explanation,out error,"physical","different-model"))
                throw new Exception("Changed model accepted for replay");
            if(journal.TryReplay(path,1,2,4,"observation",out willing,out explanation,out error))
                throw new Exception("Wrong obstacle accepted");
            if(journal.TryReplay(path,1,2,3,"changed",out willing,out explanation,out error))
                throw new Exception("Changed observation accepted");
            if(!journal.TryReplay(path,1,2,3,"observation",out willing,out explanation,out error) || !willing)
                throw new Exception("Exact replay failed");
            if(!journal.ReplayFullyConsumed(path)) throw new Exception("Replay tail check failed");
            if(journal.TryReplay(path,1,2,3,"observation",out willing,out explanation,out error))
                throw new Exception("Exhausted trace accepted");
            var policy=new LLMDecisionPolicy("");
            var flags=BindingFlags.NonPublic|BindingFlags.Instance;
            string prompt=(string)typeof(LLMDecisionPolicy).GetMethod("CreatePrompt",flags).Invoke(policy,
                new object[]{new LLMDecisionPolicy.VolunteerContext {sharedObservationJson="{\"nearbyAgentCount\":4}"}});
            if(!prompt.Contains("decline_assistance") || !prompt.Contains("nearbyAgentCount") || prompt.Contains("selfish"))
                throw new Exception("Shared observation prompt contract failed");
            string alternate=(string)typeof(LLMDecisionPolicy).GetMethod("CreatePrompt",flags).Invoke(policy,
                new object[]{new LLMDecisionPolicy.VolunteerContext {sharedObservationJson="{\"nearbyAgentCount\":4}",
                    promptWording=AgentPromptWording.Alternate}});
            if(alternate==prompt || !alternate.Contains("decline_assistance") || alternate.Contains("selfish"))
                throw new Exception("Alternate neutral wording contract failed");
            var parse=typeof(LLMDecisionPolicy).GetMethod("ParseDecisionResult",flags);
            foreach(string decision in new[]{"participate","decline_assistance"})
            {
                string body=JsonUtility.ToJson(new LLMDecisionPolicy.ChatResponse {choices=new[]{new LLMDecisionPolicy.Choice {
                    message=new LLMDecisionPolicy.LLMMessage("assistant","{\"decision\":\""+decision+"\",\"explanation\":\"test\"}")}}});
                if(parse.Invoke(policy,new object[]{body})==null) throw new Exception("Neutral decision rejected");
            }
            Debug.Log("PAPER_AGENT_CONTRACT_VALIDATION_PASSED (no simulation/API)");
        }
        finally {if(File.Exists(path)) File.Delete(path);}
    }

    private static void ValidateStudyLock()
    {
        string path=Path.Combine(Path.GetTempPath(),System.Guid.NewGuid()+".json");
        var obj=new GameObject("StudyLockContractOnly");
        try
        {
            var manager=obj.AddComponent<SimulationManager>();
            manager.world=obj.AddComponent<GridWorld>();manager.world.width=manager.world.height=9;
            manager.agentCount=2;manager.maxSimulationSteps=100;manager.openAIModel="model";
            manager.agentResearchPhase=AgentResearchPhase.FinalTest;manager.lockedStudyPlanPath=path;
            string source="Assets/scripts/Decision/DecisionRandomStream.cs";
            var plan=new AgentStudyPlan {schema="agent-study-plan-v1",locked=true,planID="synthetic-contract",
                horizon=100,model="model",promptVersion=AgentObservation.PromptVersion,
                primaryContrast="test",multiplicityTreatment="descriptive",developmentSeeds=new[]{1},
                calibrationSeeds=new[]{2},testSeeds=new[]{3},conditionKeys=new[]{manager.AgentConditionKey},
                informationConditions=new[]{manager.agentInformation.ToString()},policies=new[]{manager.volunteerDecisionMode.ToString()},
                sourceFiles=new[]{new AgentStudyPlan.SourceFile {path=source,sha256=AgentStudyPlan.Hash(source)}}};
            File.WriteAllText(path,JsonUtility.ToJson(plan));
            manager.ValidateAgentResearchSettings(3);
            bool rejected=false;
            try {manager.ValidateAgentResearchSettings(2);} catch(InvalidDataException) {rejected=true;}
            if(!rejected) throw new Exception("Unplanned test seed accepted");
            plan.sourceFiles[0].sha256="changed";File.WriteAllText(path,JsonUtility.ToJson(plan));
            rejected=false;
            try {manager.ValidateAgentResearchSettings(3);} catch(InvalidDataException) {rejected=true;}
            if(!rejected) throw new Exception("Changed study source accepted");
        }
        finally {if(File.Exists(path)) File.Delete(path);UnityEngine.Object.DestroyImmediate(obj);}
    }

    private static void ValidateResearchControls()
    {
        var context=new Decision.VolunteerDecisionContext {nearbyAgentCount=8,exitNonBlockage=0.4f,
            distanceToObstacle=7,obstacleCount=9,volunteerCost=0.005f,failureCost=0.5f,unwillingness=5};
        string core=AgentObservation.Serialize(context,AgentInformationCondition.Core);
        string shared=AgentObservation.Serialize(context,AgentInformationCondition.SharedContext);
        if(core.Contains("distanceToObstacle") || core.Contains("agentPosition") || !core.Contains("nearbyAgentCount") ||
            !shared.Contains("distanceToObstacle")) throw new Exception("Information condition leaked fields");
        if(new Decision.RandomMatchedVolunteerStrategy(0,()=>0f).ShouldVolunteer(context) ||
            !new Decision.RandomMatchedVolunteerStrategy(1,()=>0.999f).ShouldVolunteer(context))
            throw new Exception("Calibrated endpoints changed");
        string path=Path.Combine(Path.GetTempPath(),System.Guid.NewGuid()+".json");
        try
        {
            var calibration=new CooperationCalibration {schema="cooperation-calibration-v1",calibrationID="test",
                split="Calibration",model="model",promptVersion=AgentObservation.PromptVersion,
                informationCondition="Core",conditionKey="physical",decisions=3,probability=0.5f,
                seeds=new[]{1,2},sourceHashes=new[]{"synthetic-test-only"}};
            File.WriteAllText(path,JsonUtility.ToJson(calibration));
            CooperationCalibration.Load(path,"physical","model",AgentInformationCondition.Core,3,AgentResearchPhase.FinalTest);
            bool rejected=false;
            try {CooperationCalibration.Load(path,"physical","model",AgentInformationCondition.Core,1,AgentResearchPhase.FinalTest);}
            catch(InvalidDataException) {rejected=true;}
            if(!rejected) throw new Exception("Calibration/test leakage accepted");
            rejected=false;
            try {CooperationCalibration.Load(path,"different","model",AgentInformationCondition.Core,3,AgentResearchPhase.FinalTest);}
            catch(InvalidDataException) {rejected=true;}
            if(!rejected) throw new Exception("Physical condition mismatch accepted");
        }
        finally {if(File.Exists(path)) File.Delete(path);}
    }

    private static void ValidateRandomIsolation()
    {
        var saved=UnityEngine.Random.state;
        GameObject obj=null;
        try
        {
            UnityEngine.Random.InitState(519);
            float expected=UnityEngine.Random.value;
            UnityEngine.Random.InitState(519);
            obj=new GameObject("DecisionContractOnly");
            var manager=obj.AddComponent<SimulationManager>();
            manager.obstacleHandlingMode=ObstacleHandlingMode.PaperRelocation;
            manager.volunteerDecisionMode=SimulationManager.VolunteerDecisionMode.OriginalGameTheory;
            var flags=BindingFlags.NonPublic|BindingFlags.Instance;
            var configure=typeof(SimulationManager).GetMethod("ConfigureVolunteerDecisionStrategy",flags);
            var field=typeof(SimulationManager).GetField("volunteerDecisionStrategy",flags);
            var context=new Decision.VolunteerDecisionContext {nearbyAgentCount=8,exitNonBlockage=0.4f,
                volunteerCost=0.005f,failureCost=0.5f,unwillingness=5f};
            foreach(var mode in new[]{SimulationManager.VolunteerDecisionMode.OriginalGameTheory,
                SimulationManager.VolunteerDecisionMode.MockHeuristic})
            {
                manager.volunteerDecisionMode=mode;configure.Invoke(manager,null);
                var strategy=(Decision.IVolunteerDecisionStrategy)field.GetValue(manager);
                for(int i=0;i<100;i++) strategy.ShouldVolunteer(context);
            }
            if(UnityEngine.Random.value!=expected) throw new Exception("Paper decisions consumed physical RNG");
            int seed=Decision.DecisionRandomStream.SeedForRun(519);
            var a=new Decision.DecisionRandomStream(seed);var b=new Decision.DecisionRandomStream(seed);
            for(int i=0;i<100;i++)
            {
                float value=a.NextValue();UnityEngine.Random.Range(0,100);
                if(value!=b.NextValue() || value<0 || value>=1) throw new Exception("Decision stream contract failed");
            }
            var yes=new Decision.OriginalGameTheoryVolunteerStrategy(()=>0f);
            var no=new Decision.OriginalGameTheoryVolunteerStrategy(()=>0.999999f);
            if(!yes.ShouldVolunteer(context) || no.ShouldVolunteer(context))
                throw new Exception("Probability sampling changed");
        }
        finally
        {
            if(obj!=null) UnityEngine.Object.DestroyImmediate(obj);
            UnityEngine.Random.state=saved;
        }
    }
}
