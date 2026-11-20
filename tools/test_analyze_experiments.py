import math
import unittest
import json
import tempfile
from pathlib import Path
from analyze_experiments import bootstrap_mean, paired_comparisons, summarize, wilson, load_run


def run(policy, seed, time, success=True, valid=True):
    return dict(scenario="test", policy=policy, model="", seed=seed, signature="same-physical-settings",
                valid=valid, t90_steps=time if success else math.nan, restricted_mean_steps=time,
                t100_steps=time if success else math.nan,
                evacuation_fraction=1 if success else 0, api_decisions=0, mock_decisions=0)


class AnalysisTests(unittest.TestCase):
    def test_censoring_not_fast_failure(self):
        rows = [run("OriginalGameTheory", 1, 180), run("OriginalGameTheory", 2, 200, success=False),
                run("OriginalGameTheory", 3, 0, valid=False)]
        row = summarize(rows)[0]
        self.assertEqual(row["mean_t90_success_steps"], 180)
        self.assertEqual(row["mean_restricted_steps"], 190)
        self.assertEqual(row["success90_rate"], 0.5)
        self.assertEqual(row["invalid_runs"], 1)

    def test_pair_by_seed_and_include_failures(self):
        rows = [run("OriginalGameTheory", 1, 200, success=False), run("MockHeuristic", 1, 100),
                run("OriginalGameTheory", 2, 100), run("MockHeuristic", 3, 1)]
        row = paired_comparisons(rows)[0]
        self.assertEqual(row["pairs"], 1)
        self.assertEqual(row["mean_delta_restricted_steps"], -100)
        self.assertTrue(math.isnan(row["ci95_low"]))

    def test_duplicate_pairs_are_rejected(self):
        with self.assertRaises(ValueError):
            paired_comparisons([run("OriginalGameTheory", 1, 10), run("OriginalGameTheory", 1, 10)])

    def test_empty_group_has_no_fabricated_time(self):
        row = summarize([run("LLM", 1, 0, valid=False)])[0]
        self.assertTrue(math.isnan(row["mean_t90_success_steps"]))
        self.assertTrue(math.isnan(row["success90_rate"]))

    def test_ninety_percent_is_not_completed(self):
        partial = run("OriginalGameTheory", 1, 180)
        partial["t100_steps"] = math.nan
        row = summarize([partial])[0]
        self.assertEqual(row["success90"], 1)
        self.assertEqual(row["completed100"], 0)
        self.assertEqual(row["completion100_rate"], 0)
        self.assertTrue(math.isnan(row["mean_t100_success_steps"]))

    def test_confidence_intervals(self):
        low, high = wilson(0, 30)
        self.assertAlmostEqual(low, 0)
        self.assertGreater(high, 0)
        self.assertLess(high, 0.2)
        self.assertEqual(bootstrap_mean([1, 2, 3]), bootstrap_mean([1, 2, 3]))

    def test_unbounded_completion_has_no_fabricated_fixed_horizon(self):
        with tempfile.TemporaryDirectory() as folder:
            prefix = Path(folder) / "run"
            config = dict(schemaVersion="3-clearance-completion", actualAgents=1, maxSteps=0,
                          volunteerPolicy="OriginalGameTheory", scenario="OpenRoom", seed=42, runID=1)
            Path(str(prefix) + "_config.json").write_text(json.dumps(config), encoding="utf-8")
            Path(str(prefix) + "_global.csv").write_text("Termination,TotalSteps,EvacuatedCount\ncompleted,300,1\n", encoding="utf-8")
            Path(str(prefix) + "_agents.csv").write_text("AgentID,EvacuationStep\n0,300\n", encoding="utf-8")
            row = load_run(Path(str(prefix) + "_config.json"))
            self.assertTrue(row["valid"])
            self.assertEqual(row["t100_steps"], 300)
            self.assertTrue(math.isnan(row["restricted_mean_steps"]))

    def test_relocation_identity_cannot_change_between_steps(self):
        with tempfile.TemporaryDirectory() as folder:
            prefix=Path(folder)/"run"
            config=dict(schemaVersion="4-paper-relocation",actualAgents=1,maxSteps=10,movableObstacles=1,
                        volunteerPolicy="OriginalGameTheory",scenario="SingleBlockedExit",seed=42,runID=1)
            Path(str(prefix)+"_config.json").write_text(json.dumps(config),encoding="utf-8")
            Path(str(prefix)+"_global.csv").write_text("Termination,TotalSteps,EvacuatedCount\ncompleted,2,1\n",encoding="utf-8")
            Path(str(prefix)+"_agents.csv").write_text("AgentID,EvacuationStep\n0,2\n",encoding="utf-8")
            path=Path(str(prefix)+"_obstacles.csv")
            path.write_text("Step,ObstacleID,X,Y,Status\n0,0,1,1,Unmoved\n1,1,1,2,Settled\n",encoding="utf-8")
            with self.assertRaises(ValueError):
                load_run(Path(str(prefix)+"_config.json"))
            path.write_text("Step,ObstacleID,X,Y,Status\n0,0,1,1,Unmoved\n1,0,1,2,Settled\n",encoding="utf-8")
            row=load_run(Path(str(prefix)+"_config.json"))
            self.assertEqual(row["settled_obstacles"],1)
            self.assertEqual(row["relocation_moves"],0)


if __name__ == "__main__":
    unittest.main()
