"""Lifecycle guards around runner-owned workspace setup."""

from __future__ import annotations

import unittest
import asyncio
import math
import hashlib
import json
import os
import sys
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
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.native_binary = Path(directory.name) / "native-codex"
        self.native_binary.write_bytes(b"\x7fELFoffline-test-double")
        self.native_binary.chmod(0o700)
        self.native_workspace = Path(directory.name) / "workspace"
        self.native_workspace.mkdir()
        locator = patch.object(skills, "_native_codex_binary", return_value=self.native_binary)
        locator.start()
        self.addCleanup(locator.stop)
        startup = patch.object(skills, "_native_skill_startup", AsyncMock(return_value=(
            {}, {"type":"skills_eval.native_skill_startup", "model_turns":0, "scope":"unit stub"})))
        startup.start()
        self.addCleanup(startup.stop)

    async def test_native_catalog_locator_resolves_frozen_bytes_only_when_installed(self):
        with tempfile.TemporaryDirectory(dir=skills.REPO_ROOT.parent) as directory:
            root = Path(directory)
            task_home = root / "task-home"
            (task_home / ".cache").mkdir(parents=True)
            auth = root / "auth.json"
            auth.write_text("{}")
            package = root / "catalog" / "example"
            package.mkdir(parents=True)
            (package / "SKILL.md").write_text("Frozen candidate instructions")
            with patch.object(Path, "home", return_value=task_home):
                for installed in (True, False):
                    async def execute(command, **kwargs):
                        if command[0] == str(self.native_binary):
                            home = Path(kwargs["env"]["CODEX_HOME"])
                            prompt = kwargs["input"]
                            if installed:
                                self.assertIn(f"Installed catalog filesystem root: {home}/skills/.", prompt)
                                self.assertEqual((home / "skills/example/SKILL.md").read_text(), "Frozen candidate instructions")
                                self.assertFalse((home / "skills/.system").exists())
                                self.assertTrue(prompt.endswith("User task"))
                            else:
                                self.assertEqual(prompt, "User task")
                                self.assertFalse((home / "skills").exists())
                        return SimpleNamespace(success=True, returncode=0, stdout="", stderr="")
                    sandbox = SimpleNamespace(exec=AsyncMock(side_effect=execute), read_file=AsyncMock(return_value="answer"))
                    with (patch.object(skills, "AUTH_FILE", auth),
                          patch.object(skills, "bwrap_preflight", return_value=None),
                          patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(self.native_workspace, None))),
                          patch.object(skills, "sandbox", return_value=sandbox)):
                        await skills.run_codex("User task", model="stub/model", with_skills=installed, sandbox_mode="read-only", skills_root=package.parent)

    async def test_shipped_routing_has_no_evaluator_hints(self):
        state = TaskState(model='stub/router', sample_id='route', epoch=1, input='Explain this parser.', messages=[])
        native = AsyncMock(return_value=('{"skills":[],"reason":"ordinary question"}', ''))
        with patch.object(skills, 'run_codex', native):
            result = await skills.route_codex(model='stub/router')(state, None)
        prompt = native.await_args.args[0]
        self.assertIn(skills.catalog_routing_index(), prompt)
        self.assertIn(skills.GLOBAL_INSTRUCTIONS.read_text(), prompt)
        self.assertNotIn('how (even when', prompt)
        self.assertNotIn('Do select verify-work when', prompt)
        self.assertEqual(result.output.metadata['routing_mode'], 'shipped-descriptions-global')
        with patch.object(skills, 'run_codex', native):
            result = await skills.route_codex(model='stub/router', enriched=True)(state, None)
        self.assertIn('Do select verify-work when', native.await_args.args[0])
        self.assertEqual(result.output.metadata['routing_mode'], 'enriched-diagnostic')

    async def test_global_rules_are_installed_separately_from_repository(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw); native = SimpleNamespace(read_file=AsyncMock(return_value='answer'),
                exec=AsyncMock(return_value=SimpleNamespace(success=True, returncode=0, stdout='', stderr='')))
            with (patch.object(skills, 'bwrap_preflight', return_value=None),
                  patch.object(skills, 'isolated_codex_home', return_value=skills.nullcontext(str(home))),
                  patch.object(skills, '_sandbox_workspace_path', AsyncMock(return_value=(self.native_workspace, None))),
                  patch.object(skills, 'sandbox', return_value=native)):
                await skills.run_codex('task', model='stub/model', with_skills=False,
                    sandbox_mode='workspace-write', global_rules='personal defaults')
                self.assertEqual((home / 'AGENTS.md').read_text(), 'personal defaults')

    async def test_construction_answers_required_but_artifact_prose_optional(self):
        cases = {s.id:s for s in skills.workflows_dataset()}
        for name in ('workflow-native-construction-boundary', 'workflow-native-construction-owner'):
            metadata = cases[name].metadata
            self.assertTrue(skills._response_required(metadata))
            state = TaskState(model='stub/model', sample_id=name, epoch=1, input='task', messages=[], metadata=metadata)
            state.output = ModelOutput.from_content(model='stub/no-model', content='')
            score = await skills.workflow_effects()(state, Target('expected answer'))
            self.assertEqual(score.value, 0)
            self.assertIn('response is missing', score.explanation)
        self.assertFalse(skills._response_required(cases['workflow-native-artifact-only'].metadata))

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
                    if command[0] == str(self.native_binary):
                        self.assertIn('model_reasoning_effort="medium"', command)
                        self.assertNotIn("--sandbox", command)
                        self.assertIn('permissions.skills-eval.extends=":read-only"', command)
                        self.assertIn("--strict-config", command)
                        self.assertIn("--ignore-user-config", command)
                        self.assertIn("--ignore-rules", command)
                        self.assertEqual(command[command.index("--model") + 1], "stub/model")
                        self.assertEqual(kwargs["input"], "supplied task only")
                        if isolated:
                            seen_directory = Path(command[command.index("--cd") + 1])
                            self.assertTrue(seen_directory.is_dir())
                            self.assertEqual(seen_directory.parent, skills._native_ephemeral_cache())
                            self.assertFalse(seen_directory.is_relative_to(Path("/tmp")))
                            self.assertEqual(list(seen_directory.iterdir()), [])
                        else:
                            self.assertNotIn("--cd", command)
                    return SimpleNamespace(success=True, returncode=0, stdout=events, stderr="")

                sandbox.exec = AsyncMock(side_effect=execute)
                with (
                    patch.object(skills, "bwrap_preflight", return_value=None),
                    patch.object(skills, "isolated_codex_home", return_value=skills.nullcontext(str(home))),
                    patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(self.native_workspace, None))),
                    patch.object(skills, "sandbox", return_value=sandbox),
                ):
                    answer, observed = await skills.run_codex(
                        "supplied task only", model="stub/model", with_skills=False,
                        sandbox_mode="read-only", effort="medium", isolate_workspace=isolated,
                    )
                self.assertEqual(answer, "answer")
                self.assertTrue(observed.endswith(events))
                receipt = json.loads(observed.splitlines()[0])
                self.assertEqual(receipt["type"], "skills_eval.native_permissions")
                self.assertEqual(receipt["native_binary_sha256"], hashlib.sha256(self.native_binary.read_bytes()).hexdigest())
                roots = receipt["config"]["permissions.skills-eval.workspace_roots"]
                self.assertEqual(roots, {str(seen_directory or self.native_workspace): True})
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

    async def test_failed_native_launch_retains_requested_policy_and_binary_hash(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            for failure in (None, TimeoutError("bounded launch timeout")):
                async def execute(command, **kwargs):
                    if command[0] == str(self.native_binary):
                        if failure is not None:
                            raise failure
                        return SimpleNamespace(success=False, returncode=1,
                            stdout="failed command event", stderr="unsupported capability")
                    return SimpleNamespace(success=True, returncode=0, stdout="", stderr="")
                execution = SimpleNamespace(exec=AsyncMock(side_effect=execute))
                with (self.subTest(failure=failure),
                      patch.object(skills, "bwrap_preflight", return_value=None),
                      patch.object(skills, "isolated_codex_home", return_value=skills.nullcontext(str(home))),
                      patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(self.native_workspace, None))),
                      patch.object(skills, "sandbox", return_value=execution)):
                    with self.assertRaises(RuntimeError) as raised:
                        await skills.run_codex("task", model="stub/model", with_skills=False, sandbox_mode="read-only")
                    detail = str(raised.exception)
                    self.assertIn("requested_permissions=", detail)
                    self.assertIn("skills_eval.native_permissions", detail)
                    self.assertIn(hashlib.sha256(self.native_binary.read_bytes()).hexdigest(), detail)
                    self.assertIn("bounded launch timeout" if failure else "unsupported capability", detail)
                    self.assertEqual(execution.exec.await_args_list[-1].args[0][:2], ["rm", "-f"])

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
        self.assertEqual(grader.await_count, 1)

    async def test_artifact_review_precedes_claims_and_cannot_be_rescued_by_narrative(self):
        state = self._workflow_state(forbidden=[])
        state.metadata.update({"artifact_first_review": True, "construction_rubric": {"ownership": "existing owner"}})
        state.output = ModelOutput.from_content(model="PRIVATE_MODEL", content="AUTHOR_NARRATIVE: everything is perfect")
        usage = '{"type":"turn.completed","usage":{"input_tokens":12,"cached_input_tokens":5,"output_tokens":3}}'
        responses = [('{"score":1,"explanation":"duplicate policy"}', usage),
                     ('{"score":4,"explanation":"clear report"}', usage)]

        async def launch(prompt, **kwargs):
            self.assertTrue(kwargs["isolate_workspace"])
            self.assertFalse(kwargs["with_skills"])
            if "AUTHOR_NARRATIVE" in prompt:
                self.assertEqual(state.store.get("artifact_review")["score"], 1)
            return responses.pop(0)

        grader = AsyncMock(side_effect=launch)
        with patch.object(skills, "workspace_evidence", AsyncMock(return_value="actual source and raw checks")), patch.object(skills, "run_codex", grader):
            result = await skills.native_behavior_grade(model="stub/grader")(state, Target("preserve ownership"))
        first, second = [call.args[0] for call in grader.await_args_list]
        self.assertNotIn("AUTHOR_NARRATIVE", first)
        self.assertNotIn("PRIVATE_MODEL", first)
        self.assertIn("actual source and raw checks", first)
        self.assertIn("existing owner", first)
        self.assertIn("AUTHOR_NARRATIVE", second)
        self.assertIn("duplicate policy", second)
        self.assertEqual(result.value, 1)
        self.assertEqual(result.metadata["grader_usage"]["input_tokens"], 24)
        self.assertEqual([p["phase"] for p in result.metadata["grader_phases"]], ["artifact-before-claims", "claims-after-artifact"])
        phase_records = result.metadata["grader_phases"]
        self.assertEqual(phase_records[0]["raw_completion"], '{"score":1,"explanation":"duplicate policy"}')
        self.assertEqual(
            phase_records[0]["raw_completion_sha256"],
            skills.hashlib.sha256(phase_records[0]["raw_completion"].encode()).hexdigest(),
        )
        self.assertEqual(phase_records[0]["raw_codex_jsonl"], usage)
        self.assertEqual(state.store.get("grader_phase_records"), phase_records)

    async def test_invalid_artifact_assessment_fails_closed_and_missing_usage_stays_unknown(self):
        for answer in ('{"score":true,"explanation":"wrong type"}', '[]', 'not JSON'):
            state = self._workflow_state(forbidden=[])
            state.metadata["artifact_first_review"] = True
            state.output = ModelOutput.from_content(model="stub/model", content="a report")
            grader = AsyncMock(side_effect=[(answer, ""), ('{"score":4,"explanation":"clear report"}', '{"type":"turn.completed","usage":{"input_tokens":12}}')])
            with patch.object(skills, "workspace_evidence", AsyncMock(return_value="raw evidence")), patch.object(skills, "run_codex", grader):
                result = await skills.native_behavior_grade(model="stub/grader")(state, Target("contract"))
            self.assertEqual(result.value, 0)
            self.assertNotIn("grader_usage", result.metadata)
            self.assertIn("usage", result.metadata["grader_phases"][1])

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

    def test_snapshot_and_logical_catalog_use_owned_cache_and_are_cleaned(self):
        with tempfile.TemporaryDirectory(dir=skills.REPO_ROOT.parent) as raw:
            root = Path(raw).resolve()
            home = root / "home"
            cache = home / ".cache"
            cache.mkdir(parents=True)
            catalog = root / "catalog"
            package = catalog / "example"
            package.mkdir(parents=True)
            (package / "SKILL.md").write_text("owned frozen instructions")
            (package / "reference.txt").write_text("owned reference bytes")
            auth = root / "dummy-auth.json"
            auth.write_text("{}")
            with patch.object(Path, "home", return_value=home), patch.object(skills, "AUTH_FILE", auth):
                with skills.frozen_skills(catalog) as snapshot:
                    snapshot_directory = snapshot.parent
                    self.assertEqual(snapshot_directory.parent, cache)
                    self.assertEqual(snapshot_directory.stat().st_mode & 0o777, 0o700)
                    self.assertFalse(snapshot.is_relative_to(Path("/tmp")))
                    self.assertEqual(skills._skills_identity(snapshot), skills._skills_identity(catalog))
                    with skills.isolated_codex_home(True, skills_root=snapshot) as isolated:
                        isolated_home = Path(isolated)
                        self.assertEqual(isolated_home.parent, cache)
                        for path in (snapshot / "example/SKILL.md", isolated_home / "skills/example/SKILL.md"):
                            self.assertEqual(path.read_text(), "owned frozen instructions")
                        config = skills._native_permission_config(binary=self.native_binary,
                            workspace=self.native_workspace, home=isolated_home,
                            sandbox_mode="workspace-write", skills_root=snapshot)
                        readable = config["permissions.skills-eval.filesystem"]
                        self.assertEqual(readable[str(snapshot)], "read")
                        self.assertEqual(readable[str(isolated_home / "skills")], "read")
                        self.assertNotIn(str(cache), readable)
                        self.assertNotIn(str(isolated_home), readable)
                        self.assertEqual(readable[":tmpdir"], "deny")
                        self.assertEqual(readable[":slash_tmp"], "deny")
                self.assertFalse(snapshot_directory.exists())
                self.assertFalse(isolated_home.exists())
                self.assertEqual(list(cache.iterdir()), [])
                with patch.dict(os.environ, {"TMPDIR":str(cache)}), self.assertRaisesRegex(RuntimeError, "denied temporary root"):
                    skills._native_ephemeral_cache()

    async def test_catalog_cache_in_denied_temp_root_stops_before_native_launch(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            (home / ".cache").mkdir()
            catalog = home / "catalog"
            package = catalog / "example"
            package.mkdir(parents=True)
            (package / "SKILL.md").write_text("owned instructions")
            state = self._workflow_state(forbidden=[])
            state.metadata = {"skill":"example"}
            launcher = AsyncMock()
            with (patch.object(Path, "home", return_value=home),
                  patch.object(skills, "_revision_identity", return_value="owned-fixture"),
                  patch.object(skills, "run_codex", launcher)):
                with self.assertRaisesRegex(RuntimeError, "denied temporary root"):
                    await skills.native_codex(with_skills=True, model="stub/model", skills_root=catalog)(state, None)
            launcher.assert_not_awaited()
            self.assertEqual(list((home / ".cache").iterdir()), [])

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

    async def test_native_tracker_socket_is_unavailable_before_any_launch(self):
        sample = next(sample for sample in skills.workflows_dataset().samples
            if sample.id == "workflow-investigate-create-issue")
        for stored_status in (None, {"status":"supported"}):
            with self.subTest(stored_status=stored_status):
                state = TaskState(model="stub/model", sample_id=sample.id,
                    epoch=1, input=sample.input, messages=[])
                state.metadata = dict(sample.metadata)
                state.store.set("workspace_baseline", Baseline(status="available", revision="abc"))
                if stored_status is not None:
                    state.store.set("workflow_support", stored_status)
                launcher = AsyncMock()
                resolver = AsyncMock()
                with (patch.object(skills, "run_codex", launcher),
                      patch.object(skills, "FakeTracker") as tracker,
                      patch.object(skills, "_sandbox_workspace_path", resolver),
                      patch.object(skills, "bwrap_preflight") as preflight):
                    if stored_status is None:
                        await skills.workflow_support_gate()(state, None)
                    result = await skills.native_codex(with_skills=False, model="stub/model")(state, None)
                support = result.store.get("workflow_support")
                self.assertEqual(support["status"], "unavailable")
                self.assertEqual(support["capabilities"], [])
                self.assertIn("Unix socket", support["reason"])
                self.assertIn("denied temporary root", support["reason"])
                self.assertTrue(result.completed)
                self.assertEqual(result.output.metadata["workflow_support_status"], "unavailable")
                launcher.assert_not_awaited()
                resolver.assert_not_awaited()
                tracker.assert_not_called()
                preflight.assert_not_called()
                score = await skills.workflow_effects()(result, Target("publication"))
                self.assertTrue(math.isnan(score.value))
                self.assertEqual(score.metadata["status"], "unavailable")
                self.assertTrue(score.metadata["acceptance_blocked"])

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


class ApprovalLifecycleTests(unittest.IsolatedAsyncioTestCase):
    """Adapter contract evidence only; these mocks are not model/reviewer runs."""

    @staticmethod
    def _sample():
        return next(s for s in skills.workflows_dataset()
                    if s.id == "workflow-native-plan-approved-continuation")

    @classmethod
    def _state(cls):
        sample = cls._sample()
        state = TaskState(model="gpt-6-luna", sample_id=sample.id, epoch=1,
                          input=sample.input, messages=[], metadata=sample.metadata)
        state.store.set("workspace_baseline", Baseline(status="available", revision="abc"))
        state.store.set("workflow_support", {"status": "supported"})
        return state

    def test_both_arms_receive_identical_frozen_project_facts(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            globals_by_arm = {}
            catalogs = {}
            for arm in ("candidate", "baseline"):
                globals_by_arm[arm] = root / f"{arm}-AGENTS.md"
                globals_by_arm[arm].write_text(skills.GLOBAL_INSTRUCTIONS.read_text() + f"\n{arm} guidance version\n")
                catalogs[arm] = root / arm / "skills"
                (catalogs[arm] / "follow-instructions").mkdir(parents=True)
                (catalogs[arm] / "follow-instructions/SKILL.md").write_text(f"{arm} instructions")
            options = dict(native_model="gpt-6-luna", include_behavior_grader=False,
                           case_ids=[self._sample().id], candidate_skills_root=str(catalogs["candidate"]),
                           candidate_global_instructions=str(globals_by_arm["candidate"]),
                           baseline_skills_root=str(catalogs["baseline"]),
                           baseline_global_instructions=str(globals_by_arm["baseline"]))
            candidate = skills.workflows(arm="candidate", **options).dataset[0]
            baseline = skills.workflows(arm="baseline", **options).dataset[0]
            self.assertNotEqual(candidate.metadata["global_identity"], baseline.metadata["global_identity"])
            self.assertNotEqual(candidate.metadata["comparison_skills_root"], baseline.metadata["comparison_skills_root"])
            for field in ("id", "input", "files", "setup"):
                self.assertEqual(getattr(candidate, field), getattr(baseline, field))
            for field in ("fixture_contract", "approval_turn", "required_capabilities", "allowed_paths"):
                self.assertEqual(candidate.metadata[field], baseline.metadata[field])

    async def test_observed_plan_precedes_confirmation_and_same_catalog_resume(self):
        state = self._state()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for path, text in self._sample().files.items():
                (root / path).write_text(text)
            package = root / "catalog" / "follow-instructions"
            package.mkdir(parents=True)
            instruction = package / "SKILL.md"
            instruction.write_text("FROZEN_GUIDANCE")
            loaded_roots = []
            plan = '<!doctype html><html><head><title>CSV proposal</title></head><body><main>Duplicate headers raise ValueError; interface unchanged.</main></body></html>'
            events = '{"type":"turn.completed","usage":{"input_tokens":12,"cached_input_tokens":5,"output_tokens":3}}'

            async def launch(prompt, **kwargs):
                loaded_roots.append(kwargs["skills_root"])
                self.assertEqual(kwargs["model"], "gpt-6-luna")
                self.assertEqual(kwargs["effort"], "medium")
                self.assertEqual((kwargs["skills_root"] / "follow-instructions/SKILL.md").read_text(), "FROZEN_GUIDANCE")
                self.assertEqual(kwargs["global_rules"], state.metadata["global_rules"])
                for hidden in ("fixture_contract", "comparison_arm", state.metadata["fixture_contract"]["heldout_test"]):
                    self.assertNotIn(hidden, prompt)
                if len(loaded_roots) == 1:
                    self.assertNotIn("User confirmation:", prompt)
                    (root / "proposal.html").write_text(plan)
                    instruction.write_text("CONCURRENT_EDIT")
                    return "Plan awaiting approval", events
                self.assertEqual(state.store.get("native_approval")["status"], "ready")
                self.assertIn(hashlib.sha256(plan.encode()).hexdigest(), prompt)
                self.assertIn(state.input_text, prompt)
                (root / "importer.py").write_text(state.metadata["fixture_contract"]["write_content"])
                return "Local regression passed; independent review unavailable", events

            launcher = AsyncMock(side_effect=launch)
            observed = Evidence(available=True, status="available", untracked_paths=("proposal.html",), has_changes=True)
            with (patch.object(skills, "run_codex", launcher),
                  patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(root, None))),
                  patch.object(skills, "collect_evidence", return_value=observed)):
                result = await skills.native_codex(with_skills=True, model="gpt-6-luna", inject_skill=False,
                                                  skills_root=package.parent)(state, None)
            self.assertEqual(launcher.await_count, 2)
            self.assertEqual(loaded_roots[0], loaded_roots[1])
            self.assertNotEqual(loaded_roots[0], package.parent)
            self.assertFalse(loaded_roots[0].exists())
            receipt = result.store.get("native_approval")
            self.assertEqual(receipt["status"], "resumed")
            self.assertEqual(receipt["source"], "runner-owned")
            self.assertEqual(receipt["preapproval_changed_paths"], ["proposal.html"])
            self.assertEqual(result.output.metadata["native_usage"], {"input_tokens":24,"cached_input_tokens":10,"output_tokens":6})

    async def test_preapproval_source_writes_or_git_edits_prevent_second_launch(self):
        for observation in (
            Evidence(available=True, status="available", tracked_worktree_paths=("importer.py",), untracked_paths=("proposal.html",)),
            Evidence(available=True, status="available", untracked_paths=("proposal.html",), git_metadata_changed=True),
            Evidence(available=True, status="available", untracked_paths=("proposal.html",), index_changed=True),
        ):
            state = self._state()
            launcher = AsyncMock(return_value=("claim that plan and implementation are done", ""))
            with (patch.object(skills, "run_codex", launcher),
                  patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(Path("/tmp"), None))),
                  patch.object(skills, "collect_evidence", return_value=observation)):
                result = await skills.native_codex(with_skills=False, model="gpt-6-luna")(state, None)
                score = await skills.workflow_effects()(result, Target("approved continuation"))
            launcher.assert_awaited_once()
            self.assertEqual(result.store.get("native_approval")["status"], "rejected")
            self.assertEqual(score.value, 0)

    async def test_missing_plan_or_incomplete_observation_never_supplies_confirmation(self):
        for observation in (
            Evidence(available=True, status="available"),
            Evidence(available=False, status="unavailable", reason="boundary unsupported"),
            Evidence(available=True, status="available", truncated=True),
        ):
            state = self._state()
            launcher = AsyncMock(return_value=("I created the plan", ""))
            with (
                tempfile.TemporaryDirectory() as raw,
                patch.object(skills, "run_codex", launcher),
                patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(Path(raw), None))),
                patch.object(skills, "collect_evidence", return_value=observation),
            ):
                result = await skills.native_codex(with_skills=False, model="gpt-6-luna")(state, None)
            launcher.assert_awaited_once()
            self.assertNotEqual(result.store.get("native_approval")["status"], "resumed")

    async def test_changed_plan_and_author_fabrication_do_not_establish_approval(self):
        state = self._state()
        state.output = ModelOutput.from_content(model="stub/no-model", content="done")
        state.output.metadata = {"native_approval": {"source":"runner-owned", "status":"resumed"}}
        missing = await skills.workflow_effects()(state, Target("approval required"))
        self.assertTrue(math.isnan(missing.value))
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            plan = '<!doctype html><html><title>Superseding plan</title><main>Changed scope</main></html>'
            (root / "proposal.html").write_text(plan)
            state.store.set("native_approval", {"source":"runner-owned", "status":"resumed", "plan_path":"proposal.html", "plan_sha256":"0"*64})
            with patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(root, None))):
                stale = await skills.workflow_effects()(state, Target("approval required"))
            self.assertEqual(stale.value, 0)
            self.assertIn("changed", stale.explanation)

    async def test_missing_approval_review_ci_and_merge_capabilities_block_before_native(self):
        for capability in ("approval-turn", "independent-review", "remote-ci", "native-reapproval-turn"):
            state = self._state()
            state.metadata.pop("approval_turn")
            state.metadata["required_capabilities"] = [capability]
            launcher = AsyncMock()
            with (patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(Path("/tmp"), None))),
                  patch.object(skills, "bwrap_preflight", return_value=None),
                  patch.object(skills, "run_codex", launcher)):
                await skills.workflow_support_gate()(state, None)
                result = await skills.native_codex(with_skills=False, model="gpt-6-luna")(state, None)
            launcher.assert_not_awaited()
            self.assertTrue(result.completed)
            self.assertIn(capability, result.store.get("workflow_support")["unobserved_required_capabilities"])
        state = self._state()
        state.metadata["forbidden_effects"] = ["merge"]
        with (patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(Path("/tmp"), None))),
              patch.object(skills, "bwrap_preflight", return_value=None)):
            support = await skills._workflow_support_status(state)
        self.assertEqual(support["status"], "blocked")
        self.assertIn("merge", support["unobserved_forbidden_effects"])

    def test_bounded_plan_observation_rejects_links_non_html_and_oversize(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            plan = root / "proposal.html"
            for text in ("not a document", "x" * (skills.MAX_ACCEPTANCE_TEST_BYTES + 1)):
                plan.write_text(text)
                self.assertIsNotNone(skills._plan_digest(root, plan.name)[1])
            plan.unlink()
            source = root / "source.html"
            source.write_text('<!doctype html><html><title>Plan</title><main>Scope</main></html>')
            plan.symlink_to(source)
            self.assertIsNotNone(skills._plan_digest(root, plan.name)[1])
            self.assertIsNotNone(skills._plan_digest(root, "../source.html")[1])

    def test_malformed_approval_contract_and_combined_lifecycle_are_unsupported(self):
        for key, value in (("plan_path", "../proposal.html"), ("allowed_paths", ["proposal.html", "checks.py"]),
                           ("confirmation", "I approve everything")):
            metadata = dict(self._sample().metadata)
            metadata["approval_turn"] = {**metadata["approval_turn"], key:value}
            self.assertIsNotNone(skills._approval_contract_error(metadata))
        metadata = dict(self._sample().metadata)
        metadata["interrupt_marker"] = ".pause"
        self.assertIn("unsupported", skills._approval_contract_error(metadata))

    def test_usage_unknown_fields_remain_unknown_across_multiple_turns(self):
        events = '\n'.join((
            '{"type":"turn.completed","usage":{"input_tokens":5,"output_tokens":2,"cached_input_tokens":1}}',
            '{"type":"turn.completed","usage":{"input_tokens":7,"output_tokens":3}}',
        ))
        self.assertEqual(skills._codex_usage(events), {"input_tokens":12,"output_tokens":5})


class NativeSkillStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_failure_prevents_any_native_model_execution(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            workspace = root / "workspace"
            home.mkdir()
            workspace.mkdir()
            binary = root / "native"
            binary.write_bytes(b"\x7fELFowned unit fixture")
            native = SimpleNamespace(exec=AsyncMock(), read_file=AsyncMock())
            with (patch.object(skills, "_native_codex_binary", return_value=binary),
                  patch.object(skills, "bwrap_preflight", return_value=None),
                  patch.object(skills, "isolated_codex_home", return_value=skills.nullcontext(str(home))),
                  patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(workspace, None))),
                  patch.object(skills, "_native_skill_startup", AsyncMock(side_effect=RuntimeError("owned initialization failure"))),
                  patch.object(skills, "sandbox", return_value=native)):
                with self.assertRaisesRegex(RuntimeError, "owned initialization failure"):
                    await skills.run_codex("owned task", model="stub/model", with_skills=False,
                        sandbox_mode="read-only")
            native.exec.assert_not_awaited()
            native.read_file.assert_not_awaited()

    async def test_generated_file_selectors_cover_new_bundles_without_a_static_name_list(self):
        import tomllib

        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw) / "home"
            home.mkdir()
            system = home / "skills/.system"
            files = [system / name / "SKILL.md" for name in ("skill-creator", "new-native-bundle")]

            async def initialize(*command, **kwargs):
                command = list(command)
                self.assertEqual(command[-3:-1], ["debug", "prompt-input"])
                self.assertNotIn("exec", command)
                self.assertEqual(kwargs["env"]["HOME"], str(home))
                self.assertEqual(kwargs["env"]["CODEX_HOME"], str(home))
                self.assertTrue(kwargs["start_new_session"])
                self.assertFalse((home / "config.toml").exists())
                for path in files:
                    path.parent.mkdir(parents=True)
                    path.write_text("owned native bundle")
                return SimpleNamespace(returncode=0, communicate=AsyncMock(return_value=(b"[]", b"")))

            with patch.object(skills.asyncio, "create_subprocess_exec", side_effect=initialize):
                config, receipt = await skills._native_skill_startup(binary=home / "native",
                    workspace=home, home=home, permissions={})
            self.assertEqual(config["skills.config"], [{"path":str(path), "enabled":False} for path in sorted(files)])
            overrides = skills._native_config_overrides(config)
            self.assertEqual(tomllib.loads(overrides[1])["skills"]["config"], config["skills.config"])
            self.assertEqual(receipt["model_turns"], 0)
            self.assertEqual(receipt["disabled_system_skill_files"], [str(path) for path in sorted(files)])
            self.assertFalse((home / "config.toml").exists())

    async def test_unavailable_initialization_and_external_bundle_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw) / "home"
            home.mkdir()
            for result in (SimpleNamespace(returncode=1, stdout="", stderr="owned failure"),
                           SimpleNamespace(returncode=0, stdout="not JSON", stderr=""),
                           SimpleNamespace(returncode=0, stdout="{}", stderr="")):
                process = SimpleNamespace(returncode=result.returncode,
                    communicate=AsyncMock(return_value=(result.stdout.encode(), result.stderr.encode())))
                with patch.object(skills.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)):
                    with self.assertRaisesRegex(RuntimeError, "initialization"):
                        await skills._native_skill_startup(binary=home / "native", workspace=home,
                            home=home, permissions={})
            outside = Path(raw) / "outside"
            outside.mkdir()
            (outside / "SKILL.md").write_text("owned excluded canary")
            system = home / "skills/.system"
            system.mkdir(parents=True)
            (system / "linked-bundle").symlink_to(outside, target_is_directory=True)
            process = SimpleNamespace(returncode=0, communicate=AsyncMock(return_value=(b"[]", b"")))
            with patch.object(skills.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)):
                with self.assertRaisesRegex(RuntimeError, "outside"):
                    await skills._native_skill_startup(binary=home / "native", workspace=home,
                        home=home, permissions={})

    async def test_cancelled_startup_reaps_its_owned_child_before_home_cleanup(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            binary = root / "owned-metadata-program"
            started = root / "started.json"
            binary.write_text(f"#!{sys.executable}\n"
                "import json,os,pathlib,time\n"
                f"pathlib.Path({str(started)!r}).write_text(json.dumps({{'pid':os.getpid()}}))\n"
                "time.sleep(60)\n"
                "home=pathlib.Path(os.environ['HOME']); home.mkdir(parents=True,exist_ok=True)\n"
                "(home/'late-write.txt').write_text('owned test canary')\n")
            binary.chmod(0o700)
            pending = asyncio.create_task(skills._native_skill_startup(binary=binary,
                workspace=root, home=home, permissions={}))
            try:
                async def wait_started():
                    while not started.exists():
                        await asyncio.sleep(0.01)
                await asyncio.wait_for(wait_started(), timeout=5)
                pid = json.loads(started.read_text())["pid"]
                pending.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await pending
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
                self.assertFalse((home / "late-write.txt").exists())
                home.rmdir()
                self.assertFalse(home.exists())
            finally:
                if not pending.done():
                    pending.cancel()
                    try:
                        await pending
                    except asyncio.CancelledError:
                        pass

    async def test_cancelled_startup_drains_descendant_pipes_after_leader_exit(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            binary = root / "owned-metadata-program"
            started = root / "started.json"
            binary.write_text(f"#!{sys.executable}\n"
                "import json,os,pathlib,time\n"
                "child=os.fork()\n"
                "if child: os._exit(0)\n"
                f"pathlib.Path({str(started)!r}).write_text(json.dumps({{'pid':os.getpid()}}))\n"
                "time.sleep(60)\n"
                "home=pathlib.Path(os.environ['HOME']); home.mkdir(parents=True,exist_ok=True)\n"
                "(home/'late-write.txt').write_text('owned test canary')\n")
            binary.chmod(0o700)
            children = []
            create_process = asyncio.create_subprocess_exec

            async def capture_process(*args, **kwargs):
                process = await create_process(*args, **kwargs)
                children.append(process)
                return process

            with patch.object(skills.asyncio, "create_subprocess_exec", side_effect=capture_process):
                pending = asyncio.create_task(skills._native_skill_startup(binary=binary,
                    workspace=root, home=home, permissions={}))
                try:
                    async def wait_started():
                        while not (started.exists() and children and children[0].returncode == 0):
                            await asyncio.sleep(0.01)
                    await asyncio.wait_for(wait_started(), timeout=5)
                    pid = json.loads(started.read_text())["pid"]
                    self.assertFalse(pending.done())
                    pending.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await asyncio.wait_for(pending, timeout=5)
                    self.assertTrue(children[0].stdout.at_eof())
                    self.assertTrue(children[0].stderr.at_eof())
                    status = Path(f"/proc/{pid}/stat")
                    if status.exists():
                        self.assertIn(status.read_text().split(")", 1)[1].strip().split()[0], {"Z", "X"})
                    self.assertFalse((home / "late-write.txt").exists())
                    home.rmdir()
                    self.assertFalse(home.exists())
                finally:
                    if not pending.done():
                        pending.cancel()
                        try:
                            await pending
                        except asyncio.CancelledError:
                            pass


class NativePermissionScopeTests(unittest.IsolatedAsyncioTestCase):
    def test_named_profiles_have_exact_scope_and_preserve_mode(self):
        import tomllib

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            workspace = root / "workspace"
            home = root / "home"
            catalog = root / "catalog"
            other_catalog = root / "other-catalog"
            for directory in (workspace, home, catalog, other_catalog):
                directory.mkdir()
            binary = root / "native-codex"
            for mode, installed in ((mode, installed) for mode in ("read-only", "workspace-write") for installed in (False, True)):
                with self.subTest(mode=mode, installed=installed):
                    config = skills._native_permission_config(binary=binary, workspace=workspace,
                        home=home, sandbox_mode=mode, skills_root=catalog if installed else None)
                    expected = {":root":"deny", ":minimal":"read", ":tmpdir":"deny", ":slash_tmp":"deny",
                        str(binary):"read", str(workspace):"write" if mode == "workspace-write" else "read",
                        str(home / "skills/.system"):"deny"}
                    if installed:
                        expected.update({str(catalog):"read", str(home / "skills"):"read"})
                    self.assertEqual(config["permissions.skills-eval.filesystem"], expected)
                    self.assertEqual(config["permissions.skills-eval.extends"], ":workspace" if mode == "workspace-write" else ":read-only")
                    self.assertFalse(config["permissions.skills-eval.network.enabled"])
                    self.assertEqual(config["default_permissions"], "skills-eval")
                    for forbidden in (str(root), str(home), str(home / "auth.json"), str(skills.AUTH_FILE), str(other_catalog), str(skills.REPO_ROOT / "evals")):
                        self.assertNotIn(forbidden, expected)
                    self.assertNotIn("sandbox_mode", config)
                    overrides = skills._native_config_overrides(config)
                    for index in range(0, len(overrides), 2):
                        self.assertEqual(overrides[index], "-c")
                        key, _ = overrides[index + 1].split("=", 1)
                        parsed = tomllib.loads(overrides[index + 1])
                        for part in key.split("."):
                            parsed = parsed[part]
                        self.assertEqual(parsed, config[key])
            with self.assertRaisesRegex(ValueError, "outside"):
                skills._native_permission_config(binary=binary, workspace=root, home=home,
                    sandbox_mode="workspace-write", skills_root=catalog)

    def test_locator_accepts_direct_elf_and_refuses_wrappers_or_bad_paths(self):
        with tempfile.TemporaryDirectory() as raw:
            binary = Path(raw) / "native"
            binary.write_bytes(b"\x7fELFowned-offline-fixture")
            binary.chmod(0o700)
            wrapper = Path(raw) / "codex.js"
            wrapper.write_text("#!/usr/bin/env node\n")
            wrapper.chmod(0o700)
            with patch.dict(os.environ, {}, clear=True), patch.object(skills.shutil, "which", return_value=str(binary)):
                self.assertEqual(skills._native_codex_binary(), binary)
            with patch.dict(os.environ, {"SKILLS_CODEX_NATIVE_BINARY":str(binary)}, clear=True), patch.object(skills.shutil, "which", return_value=str(wrapper)):
                self.assertEqual(skills._native_codex_binary(), binary)
            for locator in (str(wrapper), str(binary.parent), str(binary.parent / "missing"), "relative/native", ""):
                with self.subTest(locator=locator), patch.dict(os.environ, {"SKILLS_CODEX_NATIVE_BINARY":locator}, clear=True), self.assertRaisesRegex(RuntimeError, "SKILLS_CODEX_NATIVE_BINARY"):
                    skills._native_codex_binary()
            binary.chmod(0o600)
            with patch.dict(os.environ, {"SKILLS_CODEX_NATIVE_BINARY":str(binary)}, clear=True), self.assertRaises(RuntimeError):
                skills._native_codex_binary()

    async def test_invalid_locator_stops_before_auth_sandbox_or_model(self):
        with patch.dict(os.environ, {"SKILLS_CODEX_NATIVE_BINARY":"relative/wrapper"}, clear=True), \
             patch.object(skills, "isolated_codex_home") as auth_home, \
             patch.object(skills, "sandbox") as execution, \
             patch.object(skills, "bwrap_preflight") as preflight:
            with self.assertRaisesRegex(RuntimeError, "direct executable"):
                await skills.run_codex("task", model="stub/model", with_skills=False, sandbox_mode="read-only")
            auth_home.assert_not_called()
            execution.assert_not_called()
            preflight.assert_not_called()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
