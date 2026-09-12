"""Lifecycle guards around runner-owned workspace setup."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch
from pathlib import Path

from inspect_ai.solver import TaskState

from evals import skills
from evals.workspace_evidence import Baseline


class WorkspaceBaselineLifecycleTests(unittest.IsolatedAsyncioTestCase):
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
