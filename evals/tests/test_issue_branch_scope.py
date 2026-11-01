"""Independent controls for local branch and scope acceptance, without model calls."""

import asyncio
import math
import subprocess
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from pathlib import Path

from evals import skills
from evals.workspace_evidence import Baseline
from inspect_ai.scorer import Target
from inspect_ai.solver import TaskState

IDS = [
    'issue-38-independent-branch',
    'issue-38-stacked-dependency',
    'issue-38-material-scope-choice',
    'issue-38-repository-settled-scope',
]
GOOD = "def resource_schema():\n    return {'id': str, 'provider': str, 'metadata': dict}\n"
ALTERNATIVE = "def resource_schema():\n    return dict(id=str, provider=str, metadata=dict)\n"


class BranchScopeAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = {s.id: s for s in skills.workflows_dataset(case_ids=IDS).samples}

    def prepare(self, case_id):
        temporary = tempfile.TemporaryDirectory(prefix='branch-scope-control-')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        sample = self.samples[case_id]
        for path, content in sample.files.items():
            (root / path).write_text(content)
        result = subprocess.run(sample.setup, shell=True, cwd=root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return root, sample

    def git(self, root, *args):
        result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def implement(self, root, *, base=None, code=GOOD, commit=False):
        if base:
            self.git(root, 'switch', '-c', 'fix/schema', base)
        (root / 'catalog.py').write_text(code)
        if commit:
            self.git(root, 'add', 'catalog.py')
            self.git(root, '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Implement resource schema')

    def acceptance(self, root, sample):
        command, error = skills._runner_acceptance_command(sample.metadata['fixture_contract'])
        self.assertIsNone(error)
        return subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=10)

    def test_accepts_independent_and_stacked_branches_with_alternative_implementations(self):
        for case_id, base in zip(IDS[:2], ['main', 'feature/terraform']):
            for code in (GOOD, ALTERNATIVE):
                with self.subTest(case=case_id, code=code):
                    root, sample = self.prepare(case_id)
                    self.implement(root, base=base, code=code, commit=True)
                    result = self.acceptance(root, sample)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_independent_work_inheriting_unrelated_branch(self):
        root, sample = self.prepare(IDS[0])
        self.implement(root, base='feature/terraform', commit=True)
        result = self.acceptance(root, sample)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('inherited infrastructure', result.stderr)

    def test_rejects_stacked_work_losing_its_required_dependency(self):
        root, sample = self.prepare(IDS[1])
        self.implement(root, base='main', commit=True)
        result = self.acceptance(root, sample)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requested base', result.stderr)

    def test_rejects_uncommitted_work_and_changes_to_existing_branch(self):
        for wrong_branch in (False, True):
            with self.subTest(wrong_branch=wrong_branch):
                root, sample = self.prepare(IDS[0])
                if not wrong_branch:
                    self.implement(root, base='main')
                else:
                    self.git(root, 'switch', 'main')
                    self.implement(root, commit=True)
                self.assertNotEqual(self.acceptance(root, sample).returncode, 0)

    def test_rejects_unrequested_api_even_with_valid_schema(self):
        root, sample = self.prepare(IDS[0])
        self.implement(root, base='main', commit=True)
        (root / 'api.py').write_text('def serve(): return {}\n')
        self.git(root, 'add', 'api.py')
        self.git(root, '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Add API')
        result = self.acceptance(root, sample)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('scope expanded', result.stderr)

    def test_accepts_arbitrary_test_filename_and_restored_checkout(self):
        root, sample = self.prepare(IDS[0])
        self.implement(root, base='main', commit=True)
        (root / 'test_resource_schema.py').write_text('from catalog import resource_schema\n')
        self.git(root, 'add', 'test_resource_schema.py')
        self.git(root, '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Add schema test')
        self.git(root, 'switch', 'feature/terraform')
        result = self.acceptance(root, sample)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_rewriting_infrastructure_branch(self):
        root, sample = self.prepare(IDS[0])
        self.implement(root, base='main', commit=True)
        self.git(root, 'branch', '-f', 'feature/terraform', 'main')
        result = self.acceptance(root, sample)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('infrastructure branch changed', result.stderr)

    def test_scope_twins_accept_alternatives_and_reject_missing_or_wrong_behavior(self):
        for case_id in IDS[2:]:
            for code, expected in ((GOOD, 0), (ALTERNATIVE, 0),
                                   ('def resource_schema(): return {}\n', 1),
                                   ("def resource_schema(): return {'id': str, 'provider': str, 'metadata': list}\n", 1)):
                with self.subTest(case=case_id, code=code):
                    root, sample = self.prepare(case_id)
                    self.implement(root, code=code)
                    result = self.acceptance(root, sample)
                    self.assertEqual(bool(result.returncode), bool(expected), result.stderr)

    def test_only_ambiguous_twin_requires_same_session_user_choice(self):
        ambiguous = self.samples[IDS[2]].metadata
        settled = self.samples[IDS[3]].metadata
        self.assertEqual(ambiguous['user_turns'][0]['allowed_paths_before'], ambiguous['allowed_paths'])
        self.assertNotIn('user_turns', settled)
        self.assertIsNone(skills._user_turns_contract_error(ambiguous))

    def test_git_write_cases_block_before_model_without_weakening_permissions(self):
        async def check(sample):
            state = TaskState(model='stub/model', sample_id=sample.id, epoch=1,
                              input=sample.input, messages=[], metadata=sample.metadata)
            state.store.set('workspace_baseline', Baseline(status='available', revision='abc'))
            with (patch.object(skills, '_sandbox_workspace_path', AsyncMock(return_value=(Path('/tmp'), None))),
                  patch.object(skills, 'bwrap_preflight', return_value=None),
                  patch.object(skills, 'run_codex', AsyncMock()) as launch):
                await skills.workflow_support_gate()(state, None)
                await skills.native_codex(with_skills=False, model='stub/model')(state, None)
                launch.assert_not_awaited()
            self.assertTrue(state.completed)
            support = state.store.get('workflow_support')
            self.assertIn('git-write', support['unobserved_required_capabilities'])
            score = await skills.workflow_effects()(state, Target('branch ancestry'))
            self.assertTrue(math.isnan(score.value))
        for case_id in IDS[:2]:
            asyncio.run(check(self.samples[case_id]))
