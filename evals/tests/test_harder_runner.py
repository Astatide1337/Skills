"""Controls for harder fixtures reuse the native Inspect workflow runner."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evals import skills


class HarderRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        rows = json.loads(skills.COMPARISON_CASES.read_text())[:2]
        for row, split in zip(rows, ["development", "holdout"], strict=True):
            row["id"] = "harder-" + split
            row["metadata"]["split"] = split
            row["metadata"]["required_capabilities"] = ["workspace-read", "workspace-edit", "test-run"]
        self.path = root / "harder.json"
        self.path.write_text(json.dumps(rows))
        self.addCleanup(patch.stopall)
        patch.object(skills, "HARDER_CASES", self.path).start()
        self.globals = root / "AGENTS.md"
        self.globals.write_text("Never merge or deploy.\n")
        self.options = dict(native_model="explicit-test-model", native_effort="medium", global_instructions=str(self.globals))

    def test_default_is_development_and_objective_existing_scorers(self):
        task = skills.harder_workflows(**self.options)
        self.assertEqual([row.id for row in task.dataset], ["harder-development"])
        self.assertEqual(len(task.scorer), 3)
        self.assertEqual(task.dataset[0].metadata["user_interruptions_observation"], "unknown")
        self.assertEqual(task.dataset[0].metadata["native_model_requested"], "explicit-test-model")

    def test_holdout_selection_is_explicit_and_cannot_mix_splits(self):
        task = skills.harder_workflows(split="holdout", **self.options)
        self.assertEqual([row.id for row in task.dataset], ["harder-holdout"])
        with self.assertRaisesRegex(ValueError, "outside explicit split"):
            skills.harder_workflows(case_ids=["harder-holdout"], **self.options)
        with self.assertRaisesRegex(ValueError, "unknown harder"):
            skills.harder_workflows(case_ids=["comparison-incident-case-a"], **self.options)

    def test_arm_invariants_and_explicit_diagnostic(self):
        candidate = skills.harder_workflows(**self.options).dataset[0]
        baseline = skills.harder_workflows(arm="baseline", baseline_skills_root=str(skills.SKILLS_ROOT), **self.options).dataset[0]
        diagnostic = skills.harder_workflows(arm="no-catalog-diagnostic", **self.options).dataset[0]
        for other in (baseline, diagnostic):
            for field in ("input", "files", "target", "setup"):
                self.assertEqual(getattr(candidate, field), getattr(other, field))
            self.assertEqual(candidate.metadata["global_identity"], other.metadata["global_identity"])
        self.assertTrue(candidate.metadata["catalog_available"])
        self.assertTrue(baseline.metadata["catalog_available"])
        self.assertFalse(diagnostic.metadata["catalog_available"])
        self.assertIsNone(diagnostic.metadata["comparison_skills_identity"])
        with self.assertRaisesRegex(ValueError, "baseline comparison requires"):
            skills.harder_workflows(arm="baseline", **self.options)

    def test_explicit_model_settings_and_unique_ids(self):
        with self.assertRaisesRegex(ValueError, "explicit native_model"):
            skills.harder_workflows(native_model="", native_effort="medium")
        with self.assertRaisesRegex(ValueError, "native effort"):
            skills.harder_workflows(native_model="model", native_effort="automatic")
        with self.assertRaisesRegex(ValueError, "without duplicates"):
            skills.harder_workflows(case_ids=["harder-development"] * 2, **self.options)
        rows = json.loads(self.path.read_text())
        rows[0]["id"] = "comparison-incident-case-a"
        self.path.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError, "unique across"):
            skills.workflows_dataset(case_ids=["comparison-incident-case-a"])


class HarderSupportTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_harder_cases_use_observed_native_boundary(self):
        from inspect_ai.solver import TaskState
        from unittest.mock import AsyncMock
        rows = json.loads(skills.HARDER_CASES.read_text())
        for row in rows:
            state = TaskState(model="stub/model", sample_id=row["id"], epoch=1,
                              input=row["input"], messages=[], metadata=row["metadata"])
            with patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(skills.REPO_ROOT, None))), patch.object(skills, "bwrap_preflight", return_value=None):
                support = await skills._workflow_support_status(state)
            self.assertEqual(support["status"], "supported", support)

    async def test_unobserved_prohibited_effect_is_blocked_not_reinterpreted(self):
        from inspect_ai.solver import TaskState
        from unittest.mock import AsyncMock
        row = json.loads(skills.HARDER_CASES.read_text())[0]
        metadata = dict(row["metadata"], forbidden_effects=["production-deploy"])
        state = TaskState(model="stub/model", sample_id="unsupported", epoch=1,
                          input="request", messages=[], metadata=metadata)
        with patch.object(skills, "_sandbox_workspace_path", AsyncMock(return_value=(skills.REPO_ROOT, None))), patch.object(skills, "bwrap_preflight", return_value=None):
            support = await skills._workflow_support_status(state)
        self.assertEqual(support["status"], "blocked")
        self.assertIn("cannot observe absence of prohibited effects", support["reason"])
        self.assertEqual(support["unobserved_forbidden_effects"], ["production-deploy"])
