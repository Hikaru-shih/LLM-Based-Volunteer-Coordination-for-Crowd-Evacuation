using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEngine;

public static class IndividualSamplingLock
{
    [Serializable] public class FileHash {public string path,sha256;}
    [Serializable] public class Document
    {
        public string schema,executionMode,planSHA256,promptSHA256,expectedProviderModel,lockID;
        public int sessionChoices;
        public FileHash[] artifacts,sourceFiles;
    }
    public static string FileSHA(string path){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
    public static string Identity(Document d)=>IndividualSamplingRunner.Hash(string.Join("\n",new[]{d.schema,d.executionMode,d.planSHA256,d.promptSHA256,d.expectedProviderModel,d.sessionChoices.ToString(System.Globalization.CultureInfo.InvariantCulture)})+"\n"+
        string.Join("\n",d.artifacts.OrderBy(f=>f.path,StringComparer.Ordinal).Select(f=>"A:"+f.path+":"+f.sha256).Concat(d.sourceFiles.OrderBy(f=>f.path,StringComparer.Ordinal).Select(f=>"S:"+f.path+":"+f.sha256))));
    private static string SafePath(string root,string relative)
    {
        string path=Path.GetFullPath(Path.Combine(root,relative));
        if(Path.IsPathRooted(relative) || !path.StartsWith(Path.GetFullPath(root)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Lock path escapes its root");return path;
    }
    public static Document Verify(string path,IndividualSamplingRunner.Plan plan,bool synthetic)
    {
        string root=Path.GetDirectoryName(Path.GetFullPath(path));
        System.Collections.Generic.Dictionary<string,object> obj;
        if(!StrictJson.TryObject(File.ReadAllText(path),out obj) || obj.Count!=9)throw new InvalidDataException("Malformed lock JSON");
        var d=JsonUtility.FromJson<Document>(File.ReadAllText(path));
        if(d.schema!="individual-sampling-lock-v1" || d.executionMode!=(synthetic?"synthetic_test":"api") || d.sessionChoices<1 || d.sessionChoices>1000 || string.IsNullOrEmpty(d.expectedProviderModel) ||
            d.artifacts==null || d.sourceFiles==null || d.lockID!=Identity(d))throw new InvalidDataException("Invalid lock identity/mode/limit");
        foreach(var f in d.artifacts)if(FileSHA(SafePath(root,f.path))!=f.sha256)throw new InvalidDataException("Frozen artifact changed");
        string[] required={"plan.json","design.json","prerequisites/comprehension/summary.json","prerequisites/comprehension/trace.jsonl","prerequisites/comprehension/public_rules.txt","prerequisites/diagnostic/summary.json","prerequisites/diagnostic/trace.jsonl","prerequisites/diagnostic/public_rules.txt","prerequisites/pilot/plan.json"};
        if(required.Any(p=>!d.artifacts.Any(f=>f.path==p)))throw new InvalidDataException("Incomplete prerequisite coverage");
        Assessment(root,"comprehension",LLMComprehensionSuite.Version,LLMComprehensionSuite.Questions(),plan.model,d);
        Assessment(root,"diagnostic",PayoffDiagnosticSuite.Version,PayoffDiagnosticSuite.Questions(),plan.model,d);
        var pilot=IndividualSamplingRunner.Load(Path.Combine(root,"prerequisites/pilot/plan.json"));
        if(pilot.model!=plan.model || pilot.purpose.StartsWith("Formal:",StringComparison.Ordinal))throw new InvalidDataException("Pilot is not independent/compatible");
        if(FileSHA(Path.Combine(root,"plan.json"))!=d.planSHA256 || JsonUtility.ToJson(IndividualSamplingRunner.Load(Path.Combine(root,"plan.json")))!=JsonUtility.ToJson(plan) ||
            !plan.purpose.StartsWith("Formal:",StringComparison.Ordinal) || d.promptSHA256!=PaperVolunteerPrompt.Hash("Core",AgentPromptWording.Standard))throw new InvalidDataException("Locked plan/prompt mismatch");
        string project=Path.GetDirectoryName(Application.dataPath);
        foreach(var f in d.sourceFiles)if(FileSHA(SafePath(project,f.path))!=f.sha256)throw new InvalidDataException("Frozen source changed");
        var actual=Directory.GetFiles(Path.Combine(Application.dataPath,"scripts"),"*.cs",SearchOption.AllDirectories).Select(f=>Path.GetRelativePath(project,f).Replace('\\','/')).OrderBy(f=>f,StringComparer.Ordinal);
        var declared=d.sourceFiles.Where(f=>f.path.StartsWith("Assets/scripts/",StringComparison.Ordinal) && f.path.EndsWith(".cs",StringComparison.Ordinal)).Select(f=>f.path).OrderBy(f=>f,StringComparer.Ordinal);
        if(!actual.SequenceEqual(declared))throw new InvalidDataException("Source inventory changed");
        return d;
    }
    [Serializable] private class Summary {public string suiteVersion,specVersion,model;public int totalQuestions,attempted,correct,invalid;public bool passed;}
    [Serializable] private class Trace {public string questionID,response,requestError;public bool transportSucceeded;}
    private static void Assessment(string root,string name,string version,LLMComprehensionSuite.Question[] questions,string model,Document d)
    {
        string folder=Path.Combine(root,"prerequisites",name);
        var s=JsonUtility.FromJson<Summary>(File.ReadAllText(Path.Combine(folder,"summary.json")));
        if(!s.passed || s.suiteVersion!=version || s.specVersion!=PaperVolunteerPrompt.Version || s.model!=model || s.totalQuestions!=questions.Length || s.attempted!=questions.Length || s.correct!=questions.Length || s.invalid!=0 ||
            FileSHA(Path.Combine(folder,"public_rules.txt"))!=d.promptSHA256)throw new InvalidDataException("Factual prerequisite not passed");
        var seen=new System.Collections.Generic.HashSet<string>();
        foreach(string line in File.ReadAllLines(Path.Combine(folder,"trace.jsonl")))
        {
            var t=JsonUtility.FromJson<Trace>(line);var q=questions.SingleOrDefault(v=>v.id==t.questionID);string content,error;
            if(q==null || !seen.Add(q.id) || !t.transportSucceeded || !string.IsNullOrEmpty(t.requestError) || !MatchesProvider(t.response,d.expectedProviderModel) ||
                !PersonalDecisionProtocol.EnvelopeContent(t.response,out content,out error) || !LLMComprehensionSuite.Evaluate(q,content).correct)throw new InvalidDataException("Raw prerequisite failed revalidation");
        }
        if(seen.Count!=questions.Length)throw new InvalidDataException("Factual prerequisite missing questions");
    }
    public static bool MatchesProvider(string response,string expected)
    {
        System.Collections.Generic.Dictionary<string,object> obj;object model;
        return StrictJson.TryObject(response,out obj) && obj.TryGetValue("model",out model) && model is string && (string)model==expected;
    }
    public static void Snapshot(string path,string destination)
    {
        var d=JsonUtility.FromJson<Document>(File.ReadAllText(path));string root=Path.GetDirectoryName(Path.GetFullPath(path));
        foreach(var f in d.artifacts)
        {string target=SafePath(destination,f.path);Directory.CreateDirectory(Path.GetDirectoryName(target));if(!File.Exists(target))File.Copy(SafePath(root,f.path),target);else if(FileSHA(target)!=f.sha256)throw new InvalidDataException("Output lock snapshot changed");}
        Directory.CreateDirectory(destination);string copy=Path.Combine(destination,"lock.json");
        if(!File.Exists(copy))File.Copy(path,copy);else if(FileSHA(copy)!=FileSHA(path))throw new InvalidDataException("Output lock changed");
    }
}
