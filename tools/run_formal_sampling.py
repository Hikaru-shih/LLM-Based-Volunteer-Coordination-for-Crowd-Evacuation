"""Preview or execute locked Unity sessions; never copies credentials or retries failed sessions."""
import argparse
import json
import os
import subprocess
from pathlib import Path
from formal_sampling import verify
from individual_analysis import read,require,write_json


def run(bundle,project,output,unity,credentials,records,execute=False,max_sessions=100):
    bundle,project,output=Path(bundle).resolve(),Path(project).resolve(),Path(output).resolve()
    require(not output.is_relative_to(bundle) and not bundle.is_relative_to(output) and not output.is_relative_to(project/'Assets'),'Output must be outside the bundle and Unity Assets')
    lock=verify(bundle,project);plan=read(bundle/'plan.json')
    eligible=sum(s['nearbyAgentCount']>0 and s['exitNonBlockage']<1 for s in plan['scenarios'])*plan['repetitions']
    preview=dict(lockID=lock['lockID'],executionMode=lock['executionMode'],eligibleChoices=eligible,sessionChoices=lock['sessionChoices'],
                 estimatedSessions=(eligible+lock['sessionChoices']-1)//lock['sessionChoices'],maxHttpReservations=plan['maxHttpAttempts'],output=str(output),execute=execute)
    if not execute:return preview
    require(lock['executionMode']=='api','Synthetic bundles cannot enter the live driver')
    require(Path(unity).is_file() and (Path(credentials)/'openai-key.local.txt').is_file(),'Unity executable/local credential file missing')
    require(type(max_sessions) is int and max_sessions>0,'Invalid session limit')
    for session in range(max_sessions):
        verify(bundle,project)
        if (output/'ledger.json').exists():require(read(output/'ledger.json').get('formalLockID')==lock['lockID'],'Resume folder belongs to another study')
        progress=read(output/'progress.json') if (output/'progress.json').exists() else None
        if progress:require(progress['outcome'] in ('completed','session_choice_limit'),'Previous session failed/interrupted; review before resuming')
        if progress and progress['outcome'].startswith('completed'):
            require(progress['outcome']=='completed','Completed data contain invalid records; review instead of rerunning')
            return dict(preview,outcome='completed',sessionsThisInvocation=session)
        output.mkdir(parents=True,exist_ok=True)
        logs=output/'session_logs';logs.mkdir(exist_ok=True)
        log=logs/f'session_{len(list(logs.glob("*.log")))+1:04d}.log'
        command=[str(unity),'-batchmode','-nographics','-projectPath',str(project),'-executeMethod','IndividualSamplingBatch.Run',
                 '-samplingPlan',str(bundle/'plan.json'),'-samplingOutput',str(output),'-studyLock',str(bundle/'lock.json'),
                 '-credentialRoot',str(Path(credentials).resolve()),'-recordsRoot',str(Path(records).resolve()),'-logFile',str(log)]
        with (logs/(log.stem+'.process.txt')).open('w',encoding='utf-8') as stream:
            result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=4000,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        require(result.returncode==0,'Unity session failed; inspect logs; no automatic failure retry')
        progress=read(output/'progress.json')
        require(progress['outcome'] in ('completed','session_choice_limit'),'Session stopped invalid/interrupted; inspect before resume')
        if progress['outcome']=='completed':return dict(preview,outcome='completed',sessionsThisInvocation=session+1)
    return dict(preview,outcome='driver_session_limit',sessionsThisInvocation=max_sessions)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--project-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--unity',type=Path,required=True);p.add_argument('--credential-root',type=Path,required=True);p.add_argument('--records-root',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--max-sessions',type=int,default=100);a=p.parse_args()
    result=run(a.bundle,a.project_root,a.output,a.unity,a.credential_root,a.records_root,a.execute,a.max_sessions);print(json.dumps(result,indent=2))
