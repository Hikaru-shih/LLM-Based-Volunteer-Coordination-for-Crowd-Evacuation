using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

// Fixed observations only: this runner never starts evacuation physics.
public static class IndividualSamplingRunner
{
    [Serializable] public class Scenario
    {
        public string id="example";
        public int nearbyAgentCount=2;
        public float exitNonBlockage=.5f,volunteerCost=.005f,failureCost=.5f,unwillingness=5;
        public Decision.VolunteerDecisionContext Context() => new Decision.VolunteerDecisionContext {
            nearbyAgentCount=nearbyAgentCount,exitNonBlockage=exitNonBlockage,volunteerCost=volunteerCost,failureCost=failureCost,unwillingness=unwillingness};
    }
    [Serializable] public class Plan
    {
        public string schema="individual-sampling-v1",purpose="Development: scenario-dependent personal choices",model="gpt-4o-mini";
        public string promptVersion=PaperVolunteerPrompt.Version;
        public int repetitions=5,orderSeed=2026,maxHttpAttempts=45;
        public Scenario[] scenarios=new[]{new Scenario {id="single_partial",nearbyAgentCount=1},new Scenario {id="two_partial"},new Scenario {id="two_blocked",exitNonBlockage=0}};
    }
    [Serializable] public class Trial
    {
        public int index,repetition,attempts;public string scenario,kind,observation,payload,response,error,execution,explanation,studyLockID;
        public bool valid,willing;public float referenceProbability;public double elapsedSeconds;
        public LLMDecisionPolicy.AttemptAudit[] attemptAudit;
    }
    [Serializable] private class Ledger {public int reservedAttempts;public string binding,executionMode,formalLockID;}
    [Serializable] private class Session {public string outcome;public int completed,total,reservedAttempts;}
    public static bool Running {get;private set;}
    public static string Status {get;private set;}="Not started";
    public static string Output {get;private set;}
    private static Plan plan;private static Ledger ledger;private static FileStream lease;
    private static string notebookRoot;
    private static int sessionLimit,sessionCalls;
    private static IndividualSamplingLock.Document studyLock;
    private static LLMDecisionPolicy client;private static Trial current;
    private static readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();
    private static AsyncOperation waiting;private static double deadline;private static int total;
    public static string Hash(string text) {using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-","").ToLowerInvariant();}
    public static Plan Load(string path)
    {
        string text=File.ReadAllText(path);Dictionary<string,object> json;
        string[] keys={"schema","purpose","model","promptVersion","repetitions","orderSeed","maxHttpAttempts","scenarios"};
        if(!StrictJson.TryObject(text,out json) || json.Count!=keys.Length || keys.Any(k=>!json.ContainsKey(k)) || !(json["scenarios"] is List<object>))throw new InvalidDataException("Plan fields must match the example exactly");
        foreach(string key in new[]{"schema","purpose","model","promptVersion"})if(!(json[key] is string))throw new InvalidDataException("Plan string field type");
        foreach(string key in new[]{"repetitions","orderSeed","maxHttpAttempts"})
        {var n=json[key] as StrictJson.Number;if(n==null || n.value!=Math.Truncate(n.value) || n.value<int.MinValue || n.value>int.MaxValue)throw new InvalidDataException("Plan integer field type");}
        foreach(object raw in (List<object>)json["scenarios"])
        {
            var s=raw as Dictionary<string,object>;
            string[] fields={"id","nearbyAgentCount","exitNonBlockage","volunteerCost","failureCost","unwillingness"};
            if(s==null || s.Count!=6 || fields.Any(k=>!s.ContainsKey(k)) || !(s["id"] is string))throw new InvalidDataException("Scenario fields must match the example exactly");
            var values=s.Where(k=>k.Key!="id").ToDictionary(k=>k.Key,k=>k.Value);
            Decision.VolunteerDecisionContext context;
            // Reuse double-domain validation before JsonUtility's float conversion.
            string observation="{"+string.Join(",",values.Select(k=>"\""+k.Key+"\":"+(k.Value is StrictJson.Number ? ((StrictJson.Number)k.Value).text:"null")))+"}";
            if(!PaperDecisionSpecification.Observation(observation,"Core",out context))throw new InvalidDataException("Invalid scenario domain/type");
        }
        var value=JsonUtility.FromJson<Plan>(text);Validate(value);return value;
    }
    public static void Validate(Plan p)
    {
        if(p==null || p.schema!="individual-sampling-v1" || p.promptVersion!=PaperVolunteerPrompt.Version || string.IsNullOrWhiteSpace(p.model) || string.IsNullOrWhiteSpace(p.purpose) ||
            p.repetitions<1 || p.repetitions>10000 || p.maxHttpAttempts<0 || p.scenarios==null || p.scenarios.Length<1 || (long)p.scenarios.Length*p.repetitions>100000)
            throw new ArgumentException("Invalid plan/version/count/budget");
        var ids=new HashSet<string>();
        foreach(var s in p.scenarios)
        {
            bool rule;
            if(s==null || string.IsNullOrWhiteSpace(s.id) || !ids.Add(s.id) || PaperDecisionSpecification.Classify(s.Context(),out rule)==PaperDecisionSpecification.DecisionKind.Invalid)
                throw new ArgumentException("Invalid or duplicate scenario; require X>=0, tau in [0,1], 0<cv<av<1, omega>=0");
        }
    }
    public static int[] Order(Plan p)
    {
        int[] order=Enumerable.Range(0,p.scenarios.Length*p.repetitions).ToArray();var rng=new System.Random(p.orderSeed);
        for(int i=order.Length-1;i>0;i--){int j=rng.Next(i+1);int tmp=order[i];order[i]=order[j];order[j]=tmp;}return order;
    }
    private static string SourceHash()
    {
        string[] paths={"Editor/IndividualSamplingRunner.cs","Decision/LLMDecisionPolicy.cs","Decision/PersonalDecisionProtocol.cs","Decision/StrictJson.cs","Decision/PaperVolunteerPrompt.cs","Decision/PaperDecisionSpecification.cs","Decision/AgentResearchSettings.cs","Decision/OriginalGameTheoryVolunteerStrategy.cs"};
        return Hash(string.Join("\n",paths.Select(p=>p+":"+Hash(File.ReadAllText(Path.Combine(Application.dataPath,"scripts",p))))));
    }
    private static string Binding(Plan p) => Hash(JsonUtility.ToJson(p)+PaperVolunteerPrompt.Hash("Core",AgentPromptWording.Standard)+PersonalDecisionProtocol.Version+SourceHash());
    private static string PathFor(int i) => Path.Combine(Output,"trials",i.ToString("D6")+".json");
    private static void Atomic(string path,string text)
    {string temp=path+".pending";File.WriteAllText(temp,text);if(File.Exists(path))File.Replace(temp,path,null);else File.Move(temp,path);}
    public static void Prepare(Plan p,string folder)
    {
        Validate(p);Directory.CreateDirectory(folder);Directory.CreateDirectory(Path.Combine(folder,"trials"));
        string path=Path.Combine(folder,"plan.json"),binding=Binding(p);
        if(File.Exists(path))
        {
            if(Binding(Load(path))!=binding || !File.Exists(Path.Combine(folder,"ledger.json")))throw new InvalidDataException("Resume plan/template/protocol mismatch");
            var saved=JsonUtility.FromJson<Ledger>(File.ReadAllText(Path.Combine(folder,"ledger.json")));
            if(saved.binding!=binding || saved.reservedAttempts<0 || saved.reservedAttempts>p.maxHttpAttempts)throw new InvalidDataException("Invalid resume ledger");
        }
        else
        {
            if(Directory.GetFiles(Path.Combine(folder,"trials")).Length!=0)throw new InvalidDataException("Nonempty unbound output");
            Atomic(path,JsonUtility.ToJson(p,true));
            Atomic(Path.Combine(folder,"ledger.json"),JsonUtility.ToJson(new Ledger {binding=binding},true));
            File.WriteAllText(Path.Combine(folder,"instructions.txt"),PaperVolunteerPrompt.Instructions("Core",AgentPromptWording.Standard));
            File.WriteAllText(Path.Combine(folder,"source.sha256"),SourceHash());
        }
    }
    public static void Start(Plan p,string folder,LLMDecisionPolicy syntheticClient=null,string credentialRoot=null,string recordsRoot=null,int sessionChoices=0,string studyLockPath=null)
    {
        if(Running || EditorApplication.isPlaying)throw new InvalidOperationException("Stop the active run/Play first");
        if(syntheticClient!=null && syntheticClient.testTransport==null)throw new ArgumentException("Explicit synthetic transport required");
        Validate(p);
        if(sessionChoices<0)throw new ArgumentException("Session limit must be nonnegative");
        studyLock=string.IsNullOrEmpty(studyLockPath)?null:IndividualSamplingLock.Verify(studyLockPath,p,syntheticClient!=null);
        if(p.purpose.StartsWith("Formal:",StringComparison.Ordinal) && studyLock==null)throw new InvalidDataException("Formal sampling requires a verified study lock");
        if(studyLock!=null && Path.GetFullPath(folder).StartsWith(Path.GetFullPath(Application.dataPath)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Formal output must be outside Assets");
        if(studyLock!=null && sessionChoices>studyLock.sessionChoices)throw new InvalidDataException("Session limit exceeds the lock");
        sessionLimit=sessionChoices>0?sessionChoices:studyLock?.sessionChoices??0;sessionCalls=0;
        Directory.CreateDirectory(folder);
        lease=new FileStream(Path.Combine(folder,"sampling.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None);
        try
        {
            Prepare(p,folder);plan=p;Output=Path.GetFullPath(folder);notebookRoot=Path.GetFullPath(recordsRoot??AutomaticExperimentLog.DefaultRoot);ledger=JsonUtility.FromJson<Ledger>(File.ReadAllText(Path.Combine(Output,"ledger.json")));
            string lockID=studyLock?.lockID??"";
            if(!string.IsNullOrEmpty(ledger.formalLockID) && ledger.formalLockID!=lockID)throw new InvalidDataException("Formal lock changed or omitted on resume");
            if(string.IsNullOrEmpty(ledger.formalLockID) && lockID!="" && Directory.GetFiles(Path.Combine(Output,"trials"),"*.json").Length>0)throw new InvalidDataException("Cannot relabel existing data as formal");
            ledger.formalLockID=lockID;
            if(studyLock!=null)IndividualSamplingLock.Snapshot(studyLockPath,Path.Combine(Output,"study_lock"));
            string mode=syntheticClient==null?"api":"synthetic_test";
            if(!string.IsNullOrEmpty(ledger.executionMode) && ledger.executionMode!=mode)throw new InvalidDataException("Cannot mix synthetic and live sampling");
            ledger.executionMode=mode;Atomic(Path.Combine(Output,"ledger.json"),JsonUtility.ToJson(ledger,true));
            string key=syntheticClient==null ? (credentialRoot==null ? LocalOpenAIKey.Load():File.ReadAllText(Path.Combine(credentialRoot,"openai-key.local.txt")).Trim().TrimStart('\uFEFF')):"";
            if(syntheticClient==null && (string.IsNullOrEmpty(key) || !LocalOpenAIKey.HasValidLocalFormat(key)))throw new InvalidOperationException("Configure a valid local API key before live sampling");
            client=syntheticClient??new LLMDecisionPolicy(key,p.model);total=p.scenarios.Length*p.repetitions;
            Running=true;waiting=null;current=null;stack.Clear();stack.Push(Sample());deadline=EditorApplication.timeSinceStartup+3600;
            EditorApplication.update+=Tick;EditorApplication.quitting+=Cancel;AssemblyReloadEvents.beforeAssemblyReload+=Cancel;
        }
        catch {lease.Dispose();lease=null;throw;}
    }
    private static IEnumerator Sample()
    {
        foreach(int index in Order(plan))
        {
            if(File.Exists(PathFor(index))) {ReadTrial(index);continue;}
            var s=plan.scenarios[index/plan.repetitions];var context=s.Context();bool rule;
            var kind=PaperDecisionSpecification.Classify(context,out rule);
            current=new Trial {index=index,repetition=index%plan.repetitions,scenario=s.id,kind=kind.ToString(),observation=AgentObservation.Serialize(context,AgentInformationCondition.Core),
                studyLockID=studyLock?.lockID??"",referenceProbability=new Decision.OriginalGameTheoryVolunteerStrategy().CalculateVolunteerProbability(context)};
            if(kind==PaperDecisionSpecification.DecisionKind.NoGame){current.execution="no_game";Save();continue;}
            if(sessionLimit>0 && sessionCalls>=sessionLimit){current=null;Finish("session_choice_limit");yield break;}
            // Reserve all three possible HTTP attempts BEFORE dispatch. Interrupted requests keep their reservation.
            if(ledger.reservedAttempts+3>plan.maxHttpAttempts){current=null;Finish("budget_exhausted");yield break;}
            sessionCalls++;ledger.reservedAttempts+=3;Atomic(Path.Combine(Output,"ledger.json"),JsonUtility.ToJson(ledger,true));
            Status="Sampling "+s.id+" repeat "+(current.repetition+1);
            double requestStarted=EditorApplication.timeSinceStartup;
            yield return client.RequestVolunteerDecision(new LLMDecisionPolicy.VolunteerContext {sharedObservationJson=current.observation,informationCondition="Core",promptWording=AgentPromptWording.Standard},
                (action,why)=>{current.willing=action==VolunteerDilemma.CooperationLevel.Cooperative;current.explanation=why;});
            current.valid=client.LastRequestSucceeded;current.payload=client.LastPayload;current.response=client.LastResponse;current.error=client.LastRequestError;
            current.execution=client.LastExecution;current.attempts=client.LastAttempts;current.attemptAudit=client.LastAttemptAudit;current.elapsedSeconds=EditorApplication.timeSinceStartup-requestStarted;
            if(current.valid && studyLock!=null && !IndividualSamplingLock.MatchesProvider(current.response,studyLock.expectedProviderModel))
            {current.valid=false;current.error="provider_model_drift";}
            bool valid=current.valid;Save();
            if(!valid){Finish("stopped_invalid_response");yield break;}
        }
        Finish(Directory.GetFiles(Path.Combine(Output,"trials"),"*.json").Select(f=>JsonUtility.FromJson<Trial>(File.ReadAllText(f))).Any(t=>t.execution!="no_game" && !t.valid)?"completed_with_invalid":"completed");
    }
    private static Trial ReadTrial(int index)
    {
        var t=JsonUtility.FromJson<Trial>(File.ReadAllText(PathFor(index)));var s=plan.scenarios[index/plan.repetitions];
        bool rule;var kind=PaperDecisionSpecification.Classify(s.Context(),out rule);
        if(t==null || (t.studyLockID??"")!=(studyLock?.lockID??"") || t.index!=index || t.repetition!=index%plan.repetitions || t.scenario!=s.id || t.kind!=kind.ToString() ||
            (t.execution=="no_game")!=(kind==PaperDecisionSpecification.DecisionKind.NoGame) ||
            t.observation!=AgentObservation.Serialize(s.Context(),AgentInformationCondition.Core))throw new InvalidDataException("Resume trial mismatch");
        if(t.execution!="no_game" && t.valid)
        {
            if(studyLock!=null && !IndividualSamplingLock.MatchesProvider(t.response,studyLock.expectedProviderModel))throw new InvalidDataException("Stored provider version changed");
            LLMDecisionPolicy.DecisionResult parsed;string error;
            if(!PersonalDecisionProtocol.Response(t.response,out parsed,out error) || t.willing!=(parsed.decision=="participate") || t.payload!=PersonalDecisionProtocol.Payload(plan.model,t.observation,"Core",AgentPromptWording.Standard))throw new InvalidDataException("Resume response/payload mismatch");
        }
        return t;
    }
    private static void Save(){Atomic(PathFor(current.index),JsonUtility.ToJson(current,true));current=null;}
    private static void Tick()
    {
        try
        {
            if(EditorApplication.timeSinceStartup>deadline){Finish("interrupted_wall_clock_limit");return;}
            if(waiting!=null){if(!waiting.isDone)return;waiting=null;}
            if(stack.Count==0){Finish("invalid_runner_state");return;}
            var routine=stack.Peek();if(!routine.MoveNext()){if(stack.Count>0 && ReferenceEquals(stack.Peek(),routine))stack.Pop();return;}
            if(routine.Current is IEnumerator nested)stack.Push(nested);else if(routine.Current is AsyncOperation async)waiting=async;
        }
        catch(Exception e){Debug.LogWarning("Sampling stopped: "+e.GetType().Name);Finish("invalid_runner_or_io");}
    }
    public static void Cancel(){if(Running)Finish("interrupted_by_user_or_editor");}
    private static void Finish(string outcome)
    {
        if(!Running)return;Running=false;EditorApplication.update-=Tick;EditorApplication.quitting-=Cancel;AssemblyReloadEvents.beforeAssemblyReload-=Cancel;
        try
        {
            if(current!=null)File.AppendAllText(Path.Combine(Output,"interruptions.jsonl"),JsonUtility.ToJson(new Trial {index=current.index,scenario=current.scenario,observation=current.observation,payload=client.LastPayload,response=client.LastResponse,error=outcome,execution="interrupted_unknown_result",attempts=client.LastAttempts,attemptAudit=client.LastAttemptAudit})+Environment.NewLine);
            while(stack.Count>0)(stack.Pop() as IDisposable)?.Dispose();
            int done=Directory.GetFiles(Path.Combine(Output,"trials"),"*.json").Length;
            Atomic(Path.Combine(Output,"progress.json"),JsonUtility.ToJson(new Session {outcome=outcome,completed=done,total=total,reservedAttempts=ledger.reservedAttempts},true));
            var record=new AutomaticAssessmentRecord {recordID="individual_sampling_"+Hash(Output).Substring(0,12)+"_"+DateTime.UtcNow.Ticks,purpose=plan.purpose,
                recordedAtUtc=DateTime.UtcNow.ToString("o"),kind="individual_sampling",model=plan.model,specVersion=plan.promptVersion,promptHash=PaperVolunteerPrompt.Hash("Core",AgentPromptWording.Standard),
                dataDirectory=Output,outcome=outcome,logicalCalls=Directory.GetFiles(Path.Combine(Output,"trials"),"*.json").Select(f=>JsonUtility.FromJson<Trial>(File.ReadAllText(f))).Count(t=>t.execution!="no_game"),httpAttempts=Directory.GetFiles(Path.Combine(Output,"trials"),"*.json").Select(f=>JsonUtility.FromJson<Trial>(File.ReadAllText(f))).Sum(t=>t.attempts),totalChecks=total,summary="Execution source: "+ledger.executionMode+". Fixed-state personal sampling; saved calls exclude interrupted unknown outcomes (see interruptions.jsonl). Counts include invalid records. Conservative reserved budget retained across interruptions. No human validation or evacuation simulation. Synthetic outputs are software tests only."};
            try{AutomaticExperimentLog.PublishAssessment(notebookRoot,record);}catch(Exception error) when(error is IOException || error is UnauthorizedAccessException){File.WriteAllText(Path.Combine(Output,record.recordID+"_assessment_pending.json"),JsonUtility.ToJson(record,true));}
            Status=outcome+": "+done+"/"+total+" saved; "+ledger.reservedAttempts+" reserved attempts";
        }
        finally{current=null;lease?.Dispose();lease=null;}
    }
    public static void TickForValidation(){Tick();}
}

public class IndividualSamplingWindow : EditorWindow
{
    private string planPath="research/individual_agent_v1/sampling-plan.example.json",folder="";private string message="";
    private IndividualSamplingRunner.Plan editing;private Vector2 scroll;
    private string formalLockPath="";private int sessionChoices=250;
    private void OnEnable()
    {
        string latest=Path.Combine(AutomaticExperimentLog.DefaultRoot,"sampling_plans","latest.txt");
        if(File.Exists(latest))
        {try{string saved=File.ReadAllText(latest).Trim();if(File.Exists(saved)){planPath=saved;editing=IndividualSamplingRunner.Load(saved);message="Loaded the latest plan exported from game Settings. No API request sent.";}}catch(Exception e){message="Could not load Settings export: "+e.GetType().Name;}}
    }
    [MenuItem("Research/Individual sampling/Open runner (no call)")]
    public static void Open()=>GetWindow<IndividualSamplingWindow>("Individual sampling");
    private void OnGUI()
    {
        EditorGUILayout.HelpBox("Core individual decisions; no evacuation simulation. Edit the plan JSON to configure X, tau, cv, av, omega and repetitions. Preview makes no API call. Live start uses the local key. Budget reserves 3 HTTP attempts per choice, including retries; this is not a monetary cap.",MessageType.Info);
        planPath=EditorGUILayout.TextField("Plan JSON",planPath);folder=EditorGUILayout.TextField("Output / resume folder",folder);
        formalLockPath=EditorGUILayout.TextField("Formal lock",formalLockPath);sessionChoices=EditorGUILayout.IntField("Choices / session",sessionChoices);
        using(new EditorGUI.DisabledScope(IndividualSamplingRunner.Running))
        {
            if(GUILayout.Button("Load plan into parameter editor"))
            {try{editing=IndividualSamplingRunner.Load(planPath);message="Loaded. Save edits before preview or start.";}catch(Exception e){message=e.Message;}}
            if(editing!=null)
            {
                scroll=EditorGUILayout.BeginScrollView(scroll,GUILayout.MaxHeight(360));
                editing.purpose=EditorGUILayout.TextField("Purpose",editing.purpose);editing.model=EditorGUILayout.TextField("Model",editing.model);
                editing.repetitions=EditorGUILayout.IntField("Repeats per scenario",editing.repetitions);
                editing.orderSeed=EditorGUILayout.IntField("Order seed",editing.orderSeed);editing.maxHttpAttempts=EditorGUILayout.IntField("HTTP reservation cap",editing.maxHttpAttempts);
                for(int i=0;i<editing.scenarios.Length;i++)
                {
                    var s=editing.scenarios[i];EditorGUILayout.Space();s.id=EditorGUILayout.TextField("Scenario ID",s.id);
                    s.nearbyAgentCount=EditorGUILayout.IntField("X (including self)",s.nearbyAgentCount);
                    s.exitNonBlockage=EditorGUILayout.FloatField("Tau (unblocked fraction)",s.exitNonBlockage);
                    s.volunteerCost=EditorGUILayout.FloatField("cv (help cost)",s.volunteerCost);
                    s.failureCost=EditorGUILayout.FloatField("av (nobody helps loss)",s.failureCost);
                    s.unwillingness=EditorGUILayout.FloatField("Omega",s.unwillingness);
                    EditorGUILayout.LabelField("Payoffs: help "+(1-s.volunteerCost)+"; free ride 1; nobody helps "+(1-s.failureCost));
                    if(GUILayout.Button("Remove scenario "+i)){editing.scenarios=editing.scenarios.Where((v,j)=>j!=i).ToArray();break;}
                }
                if(GUILayout.Button("Add scenario"))editing.scenarios=editing.scenarios.Concat(new[]{new IndividualSamplingRunner.Scenario {id="new_"+editing.scenarios.Length}}).ToArray();
                EditorGUILayout.EndScrollView();
                if(GUILayout.Button("Save parameters to plan JSON"))
                {try{IndividualSamplingRunner.Validate(editing);File.WriteAllText(planPath,JsonUtility.ToJson(editing,true));message="Saved. Preview/start reads this saved plan.";}catch(Exception e){message=e.Message;}}
            }
            if(GUILayout.Button("Preview / validate (no API)"))RunUI(false);
            if(GUILayout.Button("Start / resume bounded LIVE API sampling"))RunUI(true);
        }
        if(IndividualSamplingRunner.Running && GUILayout.Button("Cancel and preserve progress"))IndividualSamplingRunner.Cancel();
        EditorGUILayout.LabelField(message,EditorStyles.wordWrappedLabel);EditorGUILayout.LabelField(IndividualSamplingRunner.Status,EditorStyles.wordWrappedLabel);
        if(IndividualSamplingRunner.Running)Repaint();
    }
    private void RunUI(bool live)
    {
        try
        {
            var p=IndividualSamplingRunner.Load(planPath);
            message=p.scenarios.Length+" scenarios x "+p.repetitions+" repetitions; HTTP reservation cap "+p.maxHttpAttempts+". Payoffs: help=1-cv, free ride=1, nobody helps=1-av.";
            if(live){if(string.IsNullOrWhiteSpace(folder))folder=Path.Combine(AutomaticExperimentLog.DefaultRoot,"data","individual_sampling",DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")+"_"+Guid.NewGuid().ToString("N").Substring(0,8));IndividualSamplingRunner.Start(p,folder,sessionChoices:sessionChoices,studyLockPath:formalLockPath);}
        }
        catch(Exception e){message=e.GetType().Name+": "+e.Message;}
    }
}
