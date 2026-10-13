"""Controls for separately measured engineering acceptance groups."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evals import skills


class EngineeringMetricsTests(unittest.TestCase):
    def test_group_validation_and_isolated_commands(self):
        commands, error = skills._runner_acceptance_groups({"acceptance_groups": {
            "feature_atomic": "assert True", "regression_tenants": "assert False"}})
        self.assertIsNone(error)
        self.assertEqual(list(commands), ["feature_atomic", "regression_tenants"])
        self.assertEqual(commands["feature_atomic"], ["python", "-S", "-B", "-c", "assert True\n"])
        for groups in ([], {"bad name": "assert True"}, {"valid": ""}, {"valid": None}):
            self.assertIsNotNone(skills._runner_acceptance_groups({"acceptance_groups": groups})[1])

    def test_group_aggregate_limit_and_existing_acceptance(self):
        self.assertIsNotNone(skills._runner_acceptance_groups({"acceptance_groups": {
            "first": "x" * 40000, "second": "x" * 40000}})[1])
        command, error = skills._runner_acceptance_command({"acceptance_test": "assert True", "heldout_test": "assert 1"})
        self.assertIsNone(error)
        self.assertIn("assert 1", command[-1])
        self.assertEqual(skills._runner_acceptance_groups({}), ({}, None))

    def test_usage_subsets_not_added(self):
        events = json.dumps({"type": "turn.completed", "usage": {
            "input_tokens": 100, "cached_input_tokens": 60,
            "output_tokens": 20, "reasoning_output_tokens": 10}})
        self.assertEqual(skills._codex_usage(events)["output_tokens"], 20)
        self.assertEqual(skills._execution_metrics(events)["uncached_input_tokens"], 40)
        self.assertIsNone(skills._codex_usage(""))

    def test_engineering_task_explicit_splits_and_shared_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = json.loads(skills.COMPARISON_CASES.read_text())[:2]
            for row, split in zip(rows, ["development", "holdout"]):
                row["id"] = "engineering-" + split
                row["metadata"]["split"] = split
            cases = root / "engineering.json"
            cases.write_text(json.dumps(rows))
            globals_path = root / "AGENTS.md"
            globals_path.write_text("Never merge or deploy.\n")
            options = {"native_model": "explicit", "native_effort": "low", "global_instructions": str(globals_path)}
            with patch.object(skills, "ENGINEERING_CASES", cases):
                candidate = skills.engineering_workflows(**options)
                baseline = skills.engineering_workflows(arm="baseline", baseline_skills_root=str(skills.SKILLS_ROOT), **options)
                self.assertEqual(candidate.dataset[0].files, baseline.dataset[0].files)
                self.assertEqual(candidate.dataset[0].metadata["global_identity"], baseline.dataset[0].metadata["global_identity"])
                self.assertEqual(len(candidate.scorer), 4)
                self.assertEqual(candidate.dataset[0].id, "engineering-development")
                with self.assertRaisesRegex(ValueError, "outside explicit split"):
                    skills.engineering_workflows(case_ids=["engineering-holdout"], **options)
                with self.assertRaisesRegex(ValueError, "baseline comparison requires"):
                    skills.engineering_workflows(arm="baseline", **options)


class ObservationTests(unittest.IsolatedAsyncioTestCase):
    async def test_unavailable_group_is_unknown_not_pass_or_failure(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock

        from inspect_ai.model import ModelOutput
        class Store(dict):
            def set(self, key, value):
                self[key] = value
        state = SimpleNamespace(
            metadata={"fixture_contract": {"acceptance_groups": {"feature_full": "assert True", "regression_public": "assert True"}}},
            store=Store(acceptance_groups={"feature_full": {"exit_code": 0}, "regression_public": {"exit_code": None, "execution_error": "timeout"}}),
            output=ModelOutput.from_content("stub", "done"),
        )
        evidence = SimpleNamespace(available=False, tracked_paths=(), untracked_paths=(), committed_paths=())
        with patch.object(skills, "_workspace_evidence_value", AsyncMock(return_value=evidence)):
            score = await skills.engineering_observations()(state, None)
        self.assertEqual(score.value["feature_full"], 1)
        self.assertNotEqual(score.value["regression_public"], score.value["regression_public"])
        self.assertNotEqual(score.value["complete_group_acceptance"], score.value["complete_group_acceptance"])
        self.assertIsNone(score.metadata["changed_file_count"])
        self.assertIsNone(score.metadata["repair_attempts"])

    async def test_inspect_aggregates_different_dimensions_without_false_zero(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock

        from inspect_ai import Task, eval_async
        from inspect_ai.dataset import Sample
        from inspect_ai.model import ModelOutput
        from inspect_ai.solver import solver

        @solver
        def observed_controls():
            async def solve(state, generate):
                name = state.input_text
                state.store.set("acceptance_groups", {name: {"exit_code": 0}})
                state.output = ModelOutput.from_content("stub/no-model", "done")
                return state
            return solve

        samples = [Sample(input=name, metadata={
            "fixture_contract": {"acceptance_groups": {name: "assert True"}},
            "evaluation_dimensions": ["feature_a", "regression_b"],
        }) for name in ["feature_a", "regression_b"]]
        evidence = SimpleNamespace(available=False, tracked_paths=(), untracked_paths=(), committed_paths=())
        with tempfile.TemporaryDirectory() as directory, patch.object(
            skills, "_workspace_evidence_value", AsyncMock(return_value=evidence)
        ):
            logs = await eval_async(Task(dataset=samples, solver=observed_controls(),
                scorer=skills.engineering_observations()), model="mockllm/model",
                log_dir=directory)
        self.assertEqual(logs[0].status, "success", str(logs[0].error))
        results = {item.name: item for item in logs[0].results.scores}
        self.assertEqual(results["feature_a"].metrics["accuracy"].value, 1)
        self.assertEqual(results["regression_b"].metrics["accuracy"].value, 1)
        self.assertEqual(results["complete_group_acceptance"].metrics["accuracy"].value, 1)

class ArtifactCaptureTests(unittest.TestCase):
    def test_raw_fixture_capture_is_private_and_rejects_links(self):
        import hashlib
        import stat

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); workspace = base / "workspace"; workspace.mkdir()
            (workspace / "source.py").write_text("token = None\n")
            secret = base / "outside"; secret.write_text("must not collect")
            (workspace / "linked.py").symlink_to(secret)
            receipt = skills._engineering_artifacts(workspace, ["source.py", "linked.py"], base / "out")
            destination = Path(receipt["directory"])
            self.assertEqual((destination / "source.py").read_text(), "token = None\n")
            self.assertEqual(receipt["sha256"]["source.py"], hashlib.sha256(b"token = None\n").hexdigest())
            self.assertFalse((destination / "linked.py").exists())
            self.assertIn("linked.py", receipt["omissions"])
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((destination / "source.py").stat().st_mode), 0o600)
            with self.assertRaises(ValueError):
                skills._engineering_artifacts(workspace, ["../outside"], base / "out")
