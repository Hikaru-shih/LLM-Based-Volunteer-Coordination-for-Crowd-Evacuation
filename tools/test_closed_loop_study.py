import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from closed_loop_study import restricted_time,primary_estimate,save,run


class GroupTests(unittest.TestCase):
    def test_replacement_seeds_and_full_balanced_matrix(self):
        from closed_loop_study import final_seed_blocks
        jobs=[dict(id=f'{seed}_{cell}_{policy}',seed=seed,cell=cell,policy=policy) for seed in range(53001,53031) for cell in range(10) for policy in (['OriginalGameTheory','LLM','NoVolunteers','RandomMatched'] if cell<8 else ['OriginalGameTheory','LLM','NoVolunteers'])]
        self.assertEqual(final_seed_blocks(dict(jobs=jobs)),list(range(53001,53031)))
        for bad in [jobs[:-1],jobs+[jobs[0]],jobs[:-1]+[dict(jobs[-1],seed=53031)],jobs[:-1]+[dict(jobs[-1],id=jobs[0]['id'])]]:
            with self.assertRaises(ValueError):final_seed_blocks(dict(jobs=bad))
    def test_replacement_seeds_cannot_enter_development(self):
        from closed_loop_study import campaign
        with tempfile.TemporaryDirectory() as f:
            for phase in ['Development','Calibration','Replay']:
                with self.assertRaises(ValueError):campaign(Path(f)/'plan.json',phase,[dict(id='protected',seed=53001)])
    def rows(self):
        return [dict(cell='c'+str(cell),seed=seed,policy=policy,blocked=2,horizon=300,initialStateSHA=str((cell,seed)),A_H=20+cell+(2 if policy=='LLM' else 0)) for seed in [1,2,3] for cell in range(8) for policy in ['OriginalGameTheory','LLM']]
    def test_non_evacuees_are_retained(self):
        self.assertEqual(restricted_time([],30,300),300)
        self.assertEqual(restricted_time([1,3],3,5),3)
        self.assertEqual(restricted_time([1,3],2,5),2)
        for steps,n,h in [([0],1,5),([6],1,5),([1,2],1,5),([],0,5)]:
            with self.assertRaises(ValueError):restricted_time(steps,n,h)
    def test_primary_is_seed_block_not_decision_pool(self):
        p=primary_estimate(self.rows(),[1,2,3]);self.assertEqual(p['estimate'],2);self.assertEqual(p['seedBlocks'],3);self.assertEqual(p['pointwise95'],[2,2])
    def test_missing_duplicate_or_unpaired_primary_rejected(self):
        r=self.rows()
        for bad in [r[:-1],r+[r[0]]]:
            with self.assertRaises(ValueError):primary_estimate(bad,[1,2,3])
        bad=copy.deepcopy(r);bad[1]['initialStateSHA']='different'
        with self.assertRaises(ValueError):primary_estimate(bad,[1,2,3])
        bad=copy.deepcopy(r);bad[1]['horizon']=299
        with self.assertRaises(ValueError):primary_estimate(bad,[1,2,3])
    def test_final_is_not_dispatched_without_opt_in(self):
        with tempfile.TemporaryDirectory() as f:
            root=Path(f);save(root/'plan.json',dict(phase='FinalTest',sourceSHA='fixture'))
            with patch('closed_loop_study.source_sha',return_value='fixture'),patch('closed_loop_study.subprocess.run') as invoke:
                with self.assertRaises(ValueError):run(root/'plan.json',root,root/'output')
                invoke.assert_not_called();self.assertFalse((root/'output').exists())
    def test_completed_partition_must_match_the_requested_jobs(self):
        with tempfile.TemporaryDirectory() as f:
            root=Path(f);plan=dict(phase='FinalTest',sourceSHA='fixture',jobs=[dict(id=str(i)) for i in range(4)])
            save(root/'plan.json',plan);out=root/'output';save(out/'registered-plan.json',plan)
            save(out/'executed-plan.json',dict(plan,jobs=plan['jobs'][::2]));save(out/'progress.json',dict(outcome='completed',completed=2))
            with patch('closed_loop_study.source_sha',return_value='fixture'),patch('closed_loop_study.subprocess.run') as invoke:
                self.assertEqual(run(root/'plan.json',root,out,lock=root/'lock',execute_final=True,partition='0/2')['outcome'],'completed_existing')
                with self.assertRaises(ValueError):run(root/'plan.json',root,out,lock=root/'lock',execute_final=True,partition='1/2')
                invoke.assert_not_called()
    def test_evidence_manifest_detects_mutated_raw_data(self):
        from closed_loop_release import seal_folder,verify_manifest
        with tempfile.TemporaryDirectory() as f:
            root=Path(f);(root/'raw.csv').write_text('a\n1\n')
            self.assertEqual(seal_folder(root),1);self.assertEqual(verify_manifest(root),1)
            (root/'extra.csv').write_text('unexpected')
            with self.assertRaises(ValueError):verify_manifest(root)
            (root/'extra.csv').unlink()
            (root/'raw.csv').write_text('a\n2\n')
            with self.assertRaises(ValueError):verify_manifest(root)
    def test_actual_preflight_rejects_steps_wrong_lock_or_missing_cases(self):
        from closed_loop_release import verify_preflight
        with tempfile.TemporaryDirectory() as f:
            path=Path(f)/'proof.json';proof=dict(passed=True,lockID='a',cases=76,remoteRequests=0,simulationSteps=0,formalJobsClaimed=0)
            save(path,proof);self.assertTrue(verify_preflight(path,'a')['passed'])
            for change in [dict(lockID='b'),dict(cases=75),dict(remoteRequests=1),dict(simulationSteps=1),dict(formalJobsClaimed=1)]:
                save(path,dict(proof,**change))
                with self.assertRaises(ValueError):verify_preflight(path,'a')
    def test_final_launch_requires_zero_step_proof_before_any_dispatch(self):
        from closed_loop_release import execute
        with tempfile.TemporaryDirectory() as f:
            root=Path(f)
            with patch('closed_loop_release.check',return_value=dict(lockID='a',finalJobsClaimed=0)),patch('closed_loop_release.s.run') as invoke:
                with self.assertRaises(FileNotFoundError):execute(root,[root/'a',root/'b'],[root/'out0',root/'out1'],root/'missing-proof.json')
                invoke.assert_not_called()
    def test_report_retains_timeout_and_separates_no_work(self):
        from closed_loop_report import summaries
        rows=[dict(cell='c',seed=seed,policy=policy,initialStateSHA=str(seed),horizon=300,A_H=(300 if policy=='NoVolunteers' else 10),fraction=(0 if policy=='NoVolunteers' else 1),termination=('timeout' if policy=='NoVolunteers' else 'completed'),effort=(0 if policy=='NoVolunteers' else 4),gini=(None if policy=='NoVolunteers' else .5),noWork=policy=='NoVolunteers',decisions=2,willing=1,httpAttempts=0) for seed in [1,2] for policy in ['LLM','NoVolunteers']]
        table,contrasts=summaries(rows);control=next(t for t in table if t['policy']=='NoVolunteers')
        self.assertEqual(control['timeouts'],2);self.assertEqual(control['mean_A_H'],300);self.assertIsNone(control['mean_gini_among_work_runs']);self.assertEqual(contrasts[0]['difference'],-290)


if __name__=='__main__':unittest.main()
