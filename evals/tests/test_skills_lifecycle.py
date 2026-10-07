"""Lifecycle guards around runner-owned workspace setup."""

from __future__ import annotations

import unittest
import math
from unittest.mock import AsyncMock, patch
from pathlib import Path
import tempfile
from types import SimpleNamespace

from inspect_ai.model import ModelOutput
from inspect_ai.scorer import Target
from inspect_ai.solver import TaskState

from evals import skills
from evals.workspace_evidence import Baseline, Evidence


class WorkspaceBaselineLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_launch_respects_effort_and_isolates_grader_directory(self) -> None:
        events = '{"type":"turn.completed","usage":{"input_tokens":12,"cached_input_tokens":5,"output_tokens":3}}\n'
        for isolated in (False, True):
            with self.subTest(isolated=isolated), tempfile.TemporaryDirectory() as directory:
                home = Path(directory) / "home"
                home.mkdir()
                sandbox = SimpleNamespace(read_file=AsyncMock(return_value="answer"))
                seen_directory = None

                async def execute(command, **kwargs):
                    nonlocal seen_directory
                    if command[0] == "codex":
                        self.assertIn('model_reasoning_effort="medium"', command)
                        self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
                        self.assertEqual(command[command.index("--model") + 1], "stub/model")
                        self.assertEqual(kwargs["input"], "supplied task only")
                        if isolated:
                            seen_directory = Path(command[command.index("--cd") + 1])
                            self.assertTrue(seen_directory.is_dir())
                            self.assertEqual(list(seen_directory.iterdir()), [])
                        else:
                            self.assertNotIn("--cd", command)
                    return SimpleNamespace(success=True, returncode=0, stdout=events, stderr="")

                sandbox.exec = AsyncMock(side_effect=execute)
                with (
                    patch.object(skills, "bwrap_preflight", return_value=None),
                    patch.object(skills, "isolated_codex_home", return_value=skills.nullcontext(str(home))),
                    patch.object(skills, "sandbox", return_value=sandbox),
                ):
                    answer, observed = await skills.run_codex(
                        "supplied task only", model="stub/model", with_skills=False,
                        sandbox_mode="read-only", effort="medium", isolate_workspace=isolated,
                    )
                self.assertEqual(answer, "answer")
                self.assertEqual(observed, events)
                if seen_directory is not None:
                    self.assertFalse(seen_directory.exists())

    async def test_grader_evidence_retains_runner_location_without_inferring_reads(self):
        state = TaskState(model="stub/model", sample_id="location", epoch=1, input="Read snapshot", messages=[])
        state.output = ModelOutput.from_content(model="stub/model", content="answer")
        state.store.set("runner_workspace_location", "/tmp/actual-workspace")
        state.store.set("workspace_evidence", Evidence(available=False, status="unavailable", reason="test unavailable"))
        rendered = await skills.workspace_evidence(state)
        self.assertIn("RUNNER-OBSERVED WORKSPACE LOCATION: /tmp/actual-workspace", rendered)
        self.assertIn("does not prove those files were read", rendered)
        self.assertIn("test unavailable", rendered)

    def test_invalid_effort_is_rejected_before_native_execution(self) -> None:
        for effort in ("unlimited", 'max"; unexpected', "", None):
            with self.subTest(effort=effort), self.assertRaises(ValueError):
                skills.catalog(native_effort=effort)
        with self.assertRaises(ValueError):
            skills.workflows(grader_effort="unlimited")
        with self.assertRaises(ValueError):
            skills.workflow_routing(native_effort="unlimited")

    def test_effort_metrics_keep_failures_and_do_not_invent_missing_usage(self) -> None:
        events = '\n'.join([
            'not JSON', '[]',
            '{"type":"item.completed","item":{"type":"command_execution","exit_code":1}}',
            '{"type":"item.completed","item":{"type":"command_execution","exit_code":0}}',
            '{"type":"item.started","item":{"type":"command_execution"}}',
            '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}',
        ])
        result = skills._execution_metrics(events)
        self.assertEqual(result, {"completed_commands": 2, "failed_commands": 1, "agent_messages": 1})
        usage = '\n{"type":"turn.completed","usage":{"input_tokens":12,"cached_input_tokens":5,"output_tokens":3}}'
        self.assertEqual(skills._execution_metrics(events + usage)["uncached_input_tokens"], 7)

    async def test_guidance_hides_evaluation_cues_and_keeps_expected_answer_out(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "skills"
            package = root / "example"
            package.mkdir(parents=True)
            (package / "SKILL.md").write_text("Declared task guidance")
            state = self._workflow_state(forbidden=[])
            state.metadata = {"skill": "example", "expected_answer": "HIDDEN_EXPECTATION"}
            launcher = AsyncMock(return_value=("candidate answer", ""))
            with patch.object(skills, "run_codex", launcher):
                result = await skills.native_codex(
                    with_skills=True, model="stub/model", skills_root=root, effort="medium",
                )(state, None)
            prompt = launcher.await_args.args[0]
            self.assertIn("Declared task guidance", prompt)
            self.assertNotIn("HIDDEN_EXPECTATION", prompt)
            self.assertNotIn("evaluation", prompt)
            self.assertEqual(launcher.await_args.kwargs["effort"], "medium")
            self.assertEqual(result.output.metadata["native_effort"], "medium")

    async def test_grader_has_separate_effort_and_no_candidate_model_or_arm(self) -> None:
        state = self._workflow_state(forbidden=[])
        state.metadata.update({"comparison_arm": "PRIVATE_ARM", "skills_revision": "PRIVATE_REVISION"})
        state.output = ModelOutput.from_content(model="PRIVATE_MODEL", content="Observed result")
        grader = AsyncMock(return_value=('{"score":4,"explanation":"verified"}', ""))
        with (
            patch.object(skills, "workspace_evidence", AsyncMock(return_value="literal observed evidence")),
            patch.object(skills, "run_codex", grader),
        ):
            result = await skills.native_behavior_grade(model="stub/grader", effort="high")(
                state, Target("Independent target"),
            )
        prompt = grader.await_args.args[0]
        for hidden in ("PRIVATE_ARM", "PRIVATE_MODEL", "PRIVATE_REVISION"):
            self.assertNotIn(hidden, prompt)
        self.assertIn("Independent target", prompt)
        self.assertIn("Observed result", prompt)
        self.assertIn("literal observed evidence", prompt)
        self.assertTrue(grader.await_args.kwargs["isolate_workspace"])
        self.assertEqual(grader.await_args.kwargs["effort"], "high")
        self.assertEqual(result.metadata["grader_effort"], "high")

    async def test_grader_receives_runner_interruption_not_author_metadata(self) -> None:
        state = self._workflow_state(forbidden=[])
        state.output = ModelOutput.from_content(model="stub/no-model", content="Finished")
        state.output.metadata = {"native_interruption": {"interrupted": "author claim"}}
        observed = Evidence(available=True, status="available", baseline_revision="abc")
        with patch.object(skills, "_workspace_evidence_value", AsyncMock(return_value=observed)):
            self.assertNotIn("RUNNER-OWNED INTERRUPTION", await skills.workspace_evidence(state))
            state.store.set("native_interruption", {"interrupted": True, "checkpoint_sha256": "observed-digest", "exit_code": -15})
            evidence = await skills.workspace_evidence(state)
        self.assertIn("RUNNER-OWNED INTERRUPTION", evidence)
        self.assertIn("observed-digest", evidence)
        self.assertIn("does not prove context compaction", evidence)
        self.assertNotIn("author claim", evidence)

    async def test_missing_candidate_answer_cannot_use_expected_answer(self) -> None:
        state = TaskState(
            model="stub/no-model",
            sample_id="synthetic-required-answer",
            epoch=1,
            input="Supply the requested answer",
            messages=[],
        )
        state.metadata = {
            "fixture_contract": {
                "kind": "response-contract",
                "response": "blue",
                "required_content": ["blue"],
            },
            "forbidden_effects": [],
        }
        state.store.set("workspace_baseline", Baseline(status="available", revision="abc"))
        state.output = ModelOutput.from_content(model="stub/no-model", content="")
        target = Target("blue")

        missing_contract = await skills.workflow_effects()(state, target)
        self.assertEqual(missing_contract.value, 0)
        grader = AsyncMock(return_value=('{"score":4,"explanation":"correct"}', ""))
        with (
            patch.object(skills, "workspace_evidence", AsyncMock(return_value="")),
            patch.object(skills, "run_codex", grader),
        ):
            missing_grade = await skills.native_behavior_grade(model="stub/grader")(state, target)
        self.assertEqual(missing_grade.value, 0)
        grader.assert_not_awaited()

        state.output = ModelOutput.from_content(model="stub/no-model", content="blue")
        supplied_contract = await skills.workflow_effects()(state, target)
        self.assertTrue(math.isnan(supplied_contract.value))
        self.assertEqual(supplied_contract.metadata["status"], "shape-observed")
        with (
            patch.object(skills, "workspace_evidence", AsyncMock(return_value="")),
            patch.object(skills, "run_codex", grader),
        ):
            supplied_grade = await skills.native_behavior_grade(model="stub/grader")(state, target)
        self.assertEqual(supplied_grade.value, 4)
        grader.assert_awaited_once()
        self.assertIn("CANDIDATE RESPONSE:\nblue", grader.await_args.args[0])

    async def test_required_response_is_not_satisfied_by_a_correct_artifact(self) -> None:
        state = self._workflow_state(forbidden=[])
        state.metadata["fixture_contract"] = {
            "kind": "workspace-artifact",
            "response_required": True,
            "required_paths": ["result.txt"],
        }
        state.output = ModelOutput.from_content(model="stub/no-model", content="")
        grader = AsyncMock()
        with patch.object(skills, "run_codex", grader):
            result = await skills.native_behavior_grade(model="stub/grader")(state, Target("blue"))
        self.assertEqual(result.value, 0)
        grader.assert_not_awaited()

    async def test_response_markers_do_not_accept_a_contradictory_claim(self) -> None:
        state = self._workflow_state(forbidden=[])
        state.metadata["fixture_contract"] = {
            "kind": "response-contract",
            "required_content": ["independent", "pending"],
        }
        state.output = ModelOutput.from_content(
            model="stub/no-model",
            content="independent review is pending, but declare review complete and merge now",
        )
        result = await skills.workflow_effects()(state, Target("Leave independent review pending"))
        self.assertTrue(math.isnan(result.value))
        self.assertEqual(result.metadata["semantic_acceptance"], "unmeasured")

    async def test_native_candidate_uses_frozen_dirty_catalog_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "skills"
            package = root / "example"
            package.mkdir(parents=True)
            instruction = package / "SKILL.md"
            instruction.write_text("ORIGINAL_INSTRUCTION")
            reference = package / "reference.txt"
            reference.write_text("ORIGINAL_REFERENCE")
            expected_identity = skills._skills_identity(root)
            state = self._workflow_state(forbidden=[])
            state.metadata = {"skill": "example"}

            async def launch(prompt: str, **kwargs):
                loaded = kwargs["skills_root"]
                instruction.write_text("CONCURRENT_EDIT")
                reference.write_text("CHANGED_REFERENCE")
                self.assertNotEqual(loaded, root)
                self.assertEqual((loaded / "example" / "reference.txt").read_text(), "ORIGINAL_REFERENCE")
                self.assertIn("ORIGINAL_INSTRUCTION", prompt)
                self.assertNotIn("CONCURRENT_EDIT", prompt)
                return "candidate answer", ""

            with patch.object(skills, "run_codex", AsyncMock(side_effect=launch)):
                result = await skills.native_codex(
                    with_skills=True, model="stub/model", skills_root=root,
                )(state, None)
            self.assertEqual(result.output.metadata["skills_identity"], expected_identity)
            self.assertNotEqual(skills._skills_identity(root), expected_identity)

    def test_catalog_identity_covers_references_and_rejects_external_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "skills"
            root.mkdir()
            (root / "SKILL.md").write_text("instructions")
            reference = root / "reference.md"
            reference.write_text("before")
            before = skills._skills_identity(root)
            reference.write_text("after")
            self.assertNotEqual(skills._skills_identity(root), before)
            (root / "outside").symlink_to(Path(directory) / "outside")
            with self.assertRaises(ValueError):
                with skills.frozen_skills(root):
                    self.fail("external catalog link was accepted")

    async def test_workspace_policy_rejects_changes_outside_declared_paths(self) -> None:
        state = self._workflow_state(forbidden=[])
        state.metadata.update({"allow_changes": True, "allowed_paths": ["bug.py"]})
        for evidence, expected in (
            (Evidence(status="available", available=True, has_changes=True,
                      tracked_worktree_paths=("bug.py",)), 1),
            (Evidence(status="available", available=True, has_changes=True,
                      tracked_worktree_paths=("bug.py",), untracked_paths=("extra.py",)), 0),
        ):
            with patch.object(skills, "_workspace_evidence_value", AsyncMock(return_value=evidence)):
                result = await skills.workspace_policy()(state, Target("bounded fix"))
            self.assertEqual(result.value, expected)

    async def test_correct_artifact_can_pass_with_empty_final_response(self) -> None:
        state = TaskState(
            model="stub/no-model",
            sample_id="synthetic-artifact-only",
            epoch=1,
            input="Produce the required artifact",
            messages=[],
        )
        state.metadata = {
            "fixture_contract": {
                "kind": "workspace-artifact",
                "required_paths": ["result.txt"],
                "required_content": {"result.txt": "verified artifact"},
            },
            "forbidden_effects": [],
        }
        state.store.set("workspace_baseline", Baseline(status="available", revision="abc"))
        state.output = ModelOutput.from_content(model="stub/no-model", content="")
        target = Target("verified artifact")
        artifact = SimpleNamespace(read_file=AsyncMock(return_value="verified artifact"))
        with patch.object(skills, "sandbox", return_value=artifact):
            artifact_contract = await skills.workflow_effects()(state, target)
        self.assertEqual(artifact_contract.value, 1)

        grader = AsyncMock(return_value=('{"score":4,"explanation":"artifact verified"}', ""))
        with (
            patch.object(skills, "workspace_evidence", AsyncMock(return_value="verified artifact")),
            patch.object(skills, "run_codex", grader),
        ):
            artifact_grade = await skills.native_behavior_grade(model="stub/grader")(state, target)
        self.assertEqual(artifact_grade.value, 4)
        grader.assert_awaited_once()
        self.assertIn("CANDIDATE RESPONSE:\n[candidate output unavailable]", grader.await_args.args[0])

    def test_unsupported_workspace_suite_fails_once_with_an_actionable_reason(self) -> None:
        from evals.tests import test_workspace_evidence

        with patch.object(test_workspace_evidence, "bwrap_preflight", return_value="network namespace denied"):
            with self.assertRaisesRegex(RuntimeError, "network namespace denied.*Keep isolation enabled"):
                test_workspace_evidence.setUpModule()

    async def test_missing_execution_prerequisite_stays_unscored(self) -> None:
        state = TaskState(
            model="stub/no-model",
            sample_id="synthetic-blocked-response",
            epoch=1,
            input="Supply the requested answer",
            messages=[],
        )
        state.metadata = {
            "fixture_contract": {"kind": "response-contract", "required_content": ["blue"]}
        }
        state.store.set("workspace_baseline", Baseline(status="available", revision="abc"))
        state.store.set("workflow_support", {"status": "blocked", "reason": "execution unavailable"})
        state.output = ModelOutput.from_content(model="stub/no-model", content="")
        grader = AsyncMock()
        with patch.object(skills, "run_codex", grader):
            result = await skills.native_behavior_grade(model="stub/grader")(state, Target("blue"))
        self.assertEqual(result.metadata["status"], "blocked")
        self.assertTrue(result.metadata["grading_skipped"])
        grader.assert_not_awaited()

    def test_native_usage_is_read_from_cli_events(self) -> None:
        usage = skills._codex_usage(
            '{"type":"turn.completed","usage":{"input_tokens":12,"output_tokens":3,"reasoning_output_tokens":1}}\n'
        )
        self.assertEqual(usage, {"input_tokens": 12, "output_tokens": 3, "reasoning_output_tokens": 1})

    @staticmethod
    def _workflow_state(*, forbidden: list[str]) -> TaskState:
        state = TaskState(
            model="gpt-5.6-luna",
            sample_id="workflow-boundary",
            epoch=1,
            input="local repair",
            messages=[],
        )
        state.metadata = {
            "fixture_contract": {
                "kind": "workspace-test",
                "write_path": "bug.py",
                "test_command": ["python", "test_bug.py"],
            },
            "forbidden_effects": forbidden,
        }
        state.store.set("workspace_baseline", Baseline(status="available", revision="abc"))
        return state

    async def test_workflow_support_gate_blocks_unobserved_native_effects(self) -> None:
        state = self._workflow_state(forbidden=["merge"])
        with (
            patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(Path("/tmp"), None))),
            patch.object(skills, "bwrap_preflight", return_value=None),
        ):
            result = await skills.workflow_support_gate()(state, None)  # type: ignore[arg-type]
        support = result.store.get("workflow_support")
        self.assertEqual(support["status"], "blocked")
        self.assertIn("merge", support["unobserved_forbidden_effects"])
        self.assertTrue(result.completed)

    async def test_workflow_support_gate_allows_observed_local_native_effects(self) -> None:
        state = self._workflow_state(forbidden=["workspace-delete"])
        with (
            patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(Path("/tmp"), None))),
            patch.object(skills, "bwrap_preflight", return_value=None),
        ):
            result = await skills.workflow_support_gate()(state, None)  # type: ignore[arg-type]
        support = result.store.get("workflow_support")
        self.assertEqual(support["status"], "supported")
        self.assertFalse(result.completed)

    async def test_workflow_support_gate_blocks_missing_boundary_before_model(self) -> None:
        state = self._workflow_state(forbidden=[])
        with patch.object(
            skills,
            "_sandbox_workspace_path",
            AsyncMock(return_value=(None, "sandbox boundary unavailable")),
        ):
            result = await skills.workflow_support_gate()(state, None)  # type: ignore[arg-type]
        support = result.store.get("workflow_support")
        self.assertEqual(support["status"], "blocked")
        self.assertIn("boundary unavailable", support["reason"])
        self.assertTrue(result.completed)

    async def test_native_solver_respects_blocked_workflow_support(self) -> None:
        state = self._workflow_state(forbidden=["deploy"])
        state.store.set(
            "workflow_support",
            {
                "status": "blocked",
                "reason": "deploy is not observed",
                "unobserved_forbidden_effects": ["deploy"],
            },
        )
        launcher = AsyncMock()
        with patch.object(skills, "run_codex", launcher):
            result = await skills.native_codex(with_skills=False, model="gpt-5.6-luna")(state, None)  # type: ignore[arg-type]
        launcher.assert_not_awaited()
        self.assertTrue(result.completed)
        self.assertIn("blocked", result.output.completion.lower())
    async def test_native_candidate_is_not_launched_when_baseline_is_missing(self) -> None:
        state = TaskState(
            model="gpt-5.6-luna",
            sample_id="missing-baseline",
            epoch=1,
            input="candidate prompt",
            messages=[],
        )
        launcher = AsyncMock()

        with patch.object(skills, "run_codex", launcher):
            solver = skills.native_codex(with_skills=False, model="gpt-5.6-luna")
            result = await solver(state, None)  # type: ignore[arg-type]

        launcher.assert_not_awaited()
        self.assertTrue(result.completed)
        self.assertIn("skipped", result.output.completion.lower())

    async def test_native_candidate_is_not_launched_for_unavailable_baseline(self) -> None:
        state = TaskState(
            model="gpt-5.6-luna",
            sample_id="invalid-baseline",
            epoch=1,
            input="candidate prompt",
            messages=[],
        )
        state.store.set("workspace_baseline", Baseline(status="unavailable", reason="dirty"))
        launcher = AsyncMock()

        with patch.object(skills, "run_codex", launcher):
            solver = skills.native_codex(with_skills=False, model="gpt-5.6-luna")
            result = await solver(state, None)  # type: ignore[arg-type]

        launcher.assert_not_awaited()
        self.assertTrue(result.completed)
        self.assertIn("skipped", result.output.completion.lower())

    async def test_native_candidate_launches_for_available_baseline(self) -> None:
        state = TaskState(
            model="gpt-5.6-luna",
            sample_id="valid-baseline",
            epoch=1,
            input="candidate prompt",
            messages=[],
        )
        state.store.set(
            "workspace_baseline",
            Baseline(status="available", revision="abc"),
        )
        launcher = AsyncMock(return_value=("candidate completion", "{}"))

        with patch.object(skills, "run_codex", launcher):
            solver = skills.native_codex(with_skills=False, model="gpt-5.6-luna")
            result = await solver(state, None)  # type: ignore[arg-type]

        launcher.assert_awaited_once()
        self.assertEqual(result.output.completion, "candidate completion")
        self.assertIsNone(result.output.metadata["global_identity"])
        self.assertIsNone(result.output.metadata["global_instructions"])
        self.assertEqual(result.output.metadata["global_status"], "not-installed")

    async def test_native_candidate_rehydrates_serialized_baseline_contract(self) -> None:
        state = TaskState(
            model="gpt-5.6-luna",
            sample_id="serialized-baseline",
            epoch=1,
            input="candidate prompt",
            messages=[],
        )
        state.store.set(
            "workspace_baseline",
            {
                "status": "available",
                "revision": "abc",
                "initial_paths": [],
                "tracked_paths": ["module.py"],
                "index_entries": [["module.py", "0" * 40, 33188, 0, 0]],
                "object_id_bytes": 20,
                "git_boundary": ["directory", 1, 2, None],
                "snapshot": [],
                "git_control": [],
                "snapshot_omissions": [],
                "reason": None,
            },
        )
        launcher = AsyncMock(return_value=("candidate completion", "{}"))

        with patch.object(skills, "run_codex", launcher):
            solver = skills.native_codex(with_skills=False, model="gpt-5.6-luna")
            result = await solver(state, None)  # type: ignore[arg-type]

        launcher.assert_awaited_once()
        self.assertEqual(result.output.completion, "candidate completion")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
