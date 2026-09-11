"""Lifecycle guards around runner-owned workspace setup."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from inspect_ai.solver import TaskState

from evals import skills
from evals.workspace_evidence import Baseline


class WorkspaceBaselineLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_candidate_is_not_launched_when_baseline_is_missing(self) -> None:
        state = TaskState(
            model="mockllm/model",
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
            model="mockllm/model",
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
            model="mockllm/model",
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
            model="mockllm/model",
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
