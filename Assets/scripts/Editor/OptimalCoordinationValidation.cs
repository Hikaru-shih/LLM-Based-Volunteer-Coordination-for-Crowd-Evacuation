using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Coordination;
using UnityEngine;

public static class OptimalCoordinationValidation
{
    private static int checks;
    private static void Check(bool ok,string message){checks++;if(!ok)throw new Exception(message);}
    private static void Oracle(Snapshot s,int i,HashSet<int> used,int count,double cost,ref int bestCount,ref double bestCost)
    {
        if(i==s.candidates.Length)
        {if(count>bestCount || (count==bestCount && cost<bestCost)){bestCount=count;bestCost=cost;}return;}
        Oracle(s,i+1,used,count,cost,ref bestCount,ref bestCost);
        var a=s.candidates[i];if(a.evacuated || a.handling)return;
        foreach(var e in s.edges.Where(e=>e.agentId==a.agentId && e.eligible && e.consented))
        {
            var t=s.tasks.Single(t=>t.obstacleId==e.obstacleId);
            if(t.settled || t.handled || !used.Add(e.obstacleId))continue;
            Oracle(s,i+1,used,count+1,cost+e.approachCost,ref bestCount,ref bestCost);used.Remove(e.obstacleId);
        }
    }
    public static void Run()
    {
        checks=0;var rng=new System.Random(20261111);
        for(int test=0;test<1500;test++)
        {
            int na=rng.Next(6),nt=rng.Next(6);var edges=new List<Edge>();
            for(int a=0;a<na;a++)for(int t=0;t<nt;t++)if(rng.NextDouble()<.65)
                edges.Add(new Edge {agentId=a*7+2,obstacleId=t*11+3,eligible=rng.Next(5)!=0,consented=rng.Next(5)!=0,approachCost=rng.Next(80)/4f});
            var s=new Snapshot {snapshotId="oracle-"+test,step=1,worldRevision=1,
                candidates=Enumerable.Range(0,na).Select(a=>new Candidate {agentId=a*7+2,evacuated=rng.Next(12)==0,handling=rng.Next(12)==0}).ToArray(),
                tasks=Enumerable.Range(0,nt).Select(t=>new Task {obstacleId=t*11+3,settled=rng.Next(12)==0,handled=rng.Next(12)==0}).ToArray(),edges=edges.ToArray()};
            var p=OptimalDispatcher.Propose(s);int count=-1;double cost=double.PositiveInfinity;
            Oracle(s,0,new HashSet<int>(),0,0,ref count,ref cost);
            double actual=p.assignments.Sum(a=>(double)s.edges.Single(e=>e.agentId==a.agentId && e.obstacleId==a.obstacleId).approachCost);
            Check(p.assignments.Length==count && Math.Abs(actual-cost)<1e-8,"Oracle mismatch "+test);
            string encoded=JsonUtility.ToJson(p);s.edges=s.edges.Reverse().ToArray();s.candidates=s.candidates.Reverse().ToArray();s.tasks=s.tasks.Reverse().ToArray();
            Check(encoded==JsonUtility.ToJson(OptimalDispatcher.Propose(s)),"Input-order nondeterminism");
        }
        // Explicit greedy counterexample: reverse residual arcs must recover two pairs.
        var example=new Snapshot {snapshotId="counterexample",candidates=new[]{new Candidate{agentId=0},new Candidate{agentId=1}},tasks=new[]{new Task{obstacleId=0},new Task{obstacleId=1}},
            edges=new[]{new Edge{agentId=0,obstacleId=0,eligible=true,consented=true,approachCost=1},new Edge{agentId=0,obstacleId=1,eligible=true,consented=true,approachCost=2},new Edge{agentId=1,obstacleId=0,eligible=true,consented=true,approachCost=2}}};
        Check(LocalDispatcher.Propose(example).assignments.Length==1 && OptimalDispatcher.Propose(example).assignments.Length==2,"Cardinality priority failed");
        string folder=Path.GetFullPath("tmp/optimal-coordination-validation/"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff"));Directory.CreateDirectory(folder);
        // Reuse the exact physical regression suite with the optimizer selected.
        LocalCoordinationValidation.ExtensionMode=ExecutionMode.OptimizedExtension;
        try{LocalCoordinationValidation.Run();}finally{LocalCoordinationValidation.ExtensionMode=ExecutionMode.CoordinatedExtension;}
        File.Copy("tmp/local-coordination-validation/result.json",Path.Combine(folder,"runtime_result.json"));
        File.WriteAllText(Path.Combine(folder,"solver_result.json"),"{\"passed\":true,\"oracleGraphs\":1500,\"checks\":"+checks+",\"remoteRequests\":0}");
        File.WriteAllText("tmp/optimal-coordination-validation/latest.txt",folder);
        SettingsMenuIntegration.UpgradeAndValidate();
        Debug.Log("OPTIMAL_COORDINATION_VALIDATION_PASSED: "+checks+" solver checks plus reference/runtime/menu regression; no API");
    }
}
