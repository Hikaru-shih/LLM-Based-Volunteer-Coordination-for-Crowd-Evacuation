using System;
using System.IO;
using Coordination;
using UnityEngine;

public static class CoordinationContractValidation
{
    public static void Run()
    {
        var snapshot=new Snapshot {snapshotId="synthetic",step=3,worldRevision=7,
            candidates=new[]{new Candidate {agentId=1},new Candidate {agentId=2}},
            tasks=new[]{new Task {obstacleId=10},new Task {obstacleId=11}},
            edges=new[]{new Edge {agentId=1,obstacleId=10,eligible=true,consented=true,approachCost=2},
                new Edge {agentId=2,obstacleId=10,eligible=true,consented=true,approachCost=3},
                new Edge {agentId=2,obstacleId=11,eligible=true,consented=false,approachCost=1}}};
        int checks=0;string error;
        Action<Proposal,bool> check=(proposal,expected)=>{
            if(ProposalValidator.Validate(snapshot,proposal,3,7,out error)!=expected) throw new Exception("Coordination contract failed: "+error);checks++;};
        var valid=new Proposal {snapshotId="synthetic",assignments=new[]{new Assignment {agentId=1,obstacleId=10}}};
        check(valid,true);
        check(new Proposal {snapshotId="synthetic",assignments=new Assignment[0]},true);
        check(new Proposal {snapshotId="old",assignments=valid.assignments},false);
        check(new Proposal {snapshotId="synthetic",assignments=new[]{new Assignment {agentId=2,obstacleId=11}}},false);
        check(new Proposal {snapshotId="synthetic",assignments=new[]{new Assignment {agentId=1,obstacleId=11}}},false);
        check(new Proposal {snapshotId="synthetic",assignments=new[]{new Assignment {agentId=1,obstacleId=10},new Assignment {agentId=2,obstacleId=10}}},false);
        check(new Proposal {snapshotId="synthetic",assignments=new[]{valid.assignments[0],valid.assignments[0]}},false);
        snapshot.candidates[0].evacuated=true;check(valid,false);snapshot.candidates[0].evacuated=false;
        snapshot.candidates[0].handling=true;check(valid,false);snapshot.candidates[0].handling=false;
        snapshot.tasks[0].settled=true;check(valid,false);snapshot.tasks[0].settled=false;
        snapshot.tasks[0].handled=true;check(valid,false);snapshot.tasks[0].handled=false;
        snapshot.edges[0].approachCost=float.NaN;check(valid,false);snapshot.edges[0].approachCost=2;
        if(ProposalValidator.Validate(snapshot,valid,4,7,out error) || ProposalValidator.Validate(snapshot,valid,3,8,out error))
            throw new Exception("Stale time/revision accepted");checks+=2;
        Directory.CreateDirectory("tmp/coordination-contract-validation");
        File.WriteAllText("tmp/coordination-contract-validation/result.json","{\"passed\":true,\"checks\":"+checks+",\"remoteRequests\":0,\"runtimeIntegrated\":false}");
        Debug.Log("COORDINATION_CONTRACT_VALIDATION_PASSED: "+checks+" pure checks; not integrated, no API or simulation");
    }
}
