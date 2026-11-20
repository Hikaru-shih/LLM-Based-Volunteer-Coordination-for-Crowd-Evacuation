"""Persist an explicitly synthetic stage3 round-trip, never a provider or human result."""
import json
from pathlib import Path
import scenario_agent_contract as c
import scenario_agent_transport as t

def main():
    bundle=c.ROOT/'experiment_records/data/preparation/scenario_agent_stage3_20261116'
    out=c.ROOT/'experiment_records/data/validation/scenario_agent_stage3_20261116'
    c.require(not out.exists(),'Preserve previous validation')
    out.mkdir(parents=True)
    registration=out/'synthetic-registration.json'
    t.register(bundle,registration,'physical_choice',1,2026111631,synthetic=True)
    counter=[0]
    def synthetic_transport(payload,key,request_id,timeout):
        c.require(key=='','Synthetic execution must not load any credential')
        counter[0]+=1
        action='participate' if counter[0]%2 else 'decline_assistance'
        response={'id':'synthetic-stage3-'+str(counter[0]),'model':c.MODEL,'choices':[{'message':{'role':'assistant','content':json.dumps({'explanation':'Synthetic action-mapping fixture. No language model or human was consulted.','decision':action})},'finish_reason':'stop'}]}
        return 200,json.dumps(response).encode(),'synthetic-request-'+str(counter[0])
    result=t.run(registration,out/'synthetic-roundtrip',transport=synthetic_transport)
    c.require(result['completed']==16 and counter[0]==16,'Incomplete synthetic roundtrip')
    mapped=[]
    lookup={x['trialID']:x['case'] for x in c.read(registration)['trials']}
    for folder in sorted((out/'synthetic-roundtrip/trials').iterdir()):
        raw=(folder/'response.raw').read_text(encoding='utf-8')
        mapped.append(c.consume(lookup[folder.name],raw))
    c.require(sum(x['willing'] for x in mapped)==8,'Mapping balance drift')
    c.write_new(out/'typed-adapter-results.json',mapped)
    t.review_template(out/'synthetic-roundtrip',out/'reason-review.unreviewed.json')
    error_reg=out/'synthetic-error-registration.json';t.register(bundle,error_reg,'abstract_diagnostic',1,2026111632,synthetic=True)
    calls=[0]
    def failure(*args):calls[0]+=1;return 429,b'{"error":{"message":"Synthetic error preservation fixture"}}','synthetic-error'
    stopped=t.run(error_reg,out/'synthetic-stop',transport=failure)
    c.require(stopped['outcome']=='stopped' and calls[0]==1,'Failure was retried or ignored')
    receipt={'passed':True,'execution':'synthetic_test','newAPICalls':0,'newUnityRuns':0,'liveProviderSupportVerified':False,'rawRoundtripCases':16,'willing':8,'decline':8,'singleAttemptErrorFixture':True,'reasonReview':'not performed; template fields remain unreviewed','meaning':'Software integration only, not LLM behavior or semantic-gate passage','interfaceSHA256':c.sha((bundle/'INTERFACE.json').read_bytes())}
    c.write_new(out/'VALIDATION.json',receipt)
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
