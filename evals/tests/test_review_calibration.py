"""Model-free controls for objective review measurement and Inspect aggregation."""
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evals import skills
from evals.review_calibration import classify_review


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.policy = {'source_paths': ['source.py'], 'defects': [
            {'id': 'hidden', 'files': ['source.py'], 'fixes': {'source.py': 'value = 1\n'}}],
            'report_path': 'review.json', 'evidence_path': 'evidence.py', 'max_findings': 5, 'probe_timeout': 2}
        (self.root / 'source.py').write_text('value = 0\n')
        (self.root / 'evidence.py').write_text('import unittest\nimport source\nclass ReviewProof(unittest.TestCase):\n def test_value(self): self.assertEqual(source.value, 1)\n')
        self.finding = {'file': 'source.py', 'line': 1, 'title': 'arbitrary',
                        'description': 'No grading keywords needed', 'proof': 'ReviewProof.test_value'}

    def classify(self, findings):
        (self.root / 'review.json').write_text(json.dumps({'findings': findings}))
        return classify_review(self.root, self.policy)

    def test_actual_single_fix_duplicate_and_clean(self):
        result = self.classify([self.finding])
        self.assertEqual(result['status'], 'valid', result)
        self.assertTrue(result['complete_review'])
        result = self.classify([self.finding, self.finding])
        self.assertEqual((result['true_positives'], result['duplicates'], result['precision']), (1, 1, .5))
        self.policy['defects'] = []
        result = self.classify([])
        self.assertTrue(math.isnan(result['precision']))
        self.assertTrue(math.isnan(result['recall']))
        self.assertEqual(result['clean_no_findings'], 1)

    def test_forged_text_missing_and_hanging_proof(self):
        (self.root / 'evidence.py').write_text('import unittest\nclass ReviewProof(unittest.TestCase):\n def test_value(self): pass\n')
        self.assertEqual(self.classify([self.finding])['false_positives'], 1)
        self.finding['proof'] = 'ReviewProof.test_missing'
        result = self.classify([self.finding])
        self.assertEqual(result['false_positives'], 1)
        self.assertIn('malformed', str(result['findings']))
        (self.root / 'evidence.py').write_text('import unittest\nclass ReviewProof(unittest.TestCase):\n def test_missing(self):\n  while True: pass\n')
        self.policy['probe_timeout'] = .1
        self.assertIn('timeout', str(self.classify([self.finding])['findings']))

    def test_multiple_failing_subtests_are_one_behavioral_proof(self):
        (self.root / 'evidence.py').write_text('import unittest\nimport source\nclass ReviewProof(unittest.TestCase):\n def test_value(self):\n  for value in range(3):\n   with self.subTest(value=value): self.assertEqual(source.value, 1)\n')
        result = self.classify([self.finding])
        self.assertTrue(result['complete_review'], result)

    def test_wrong_exception_is_valid_behavioral_failure(self):
        (self.root / 'source.py').write_text('def work(): raise TypeError("wrong exception")\n')
        self.policy['defects'][0]['fixes']['source.py'] = 'def work(): raise ValueError("expected exception")\n'
        (self.root / 'evidence.py').write_text('import unittest\nimport source\nclass ReviewProof(unittest.TestCase):\n def test_value(self):\n  with self.assertRaises(ValueError): source.work()\n')
        result = self.classify([self.finding])
        self.assertTrue(result['complete_review'], result)

    def test_combined_nonisolating_proof(self):
        self.policy['defects'].append({'id': 'second', 'files': ['source.py'],
                                      'fixes': {'source.py': 'value = 0\nother = 1\n'}})
        self.policy['defects'][0]['fixes']['source.py'] = 'value = 1\nother = 0\n'
        (self.root / 'source.py').write_text('value = 0\nother = 0\n')
        (self.root / 'evidence.py').write_text('import unittest\nimport source\nclass ReviewProof(unittest.TestCase):\n def test_value(self): self.assertEqual((source.value, source.other), (1, 1))\n')
        self.assertEqual(self.classify([self.finding])['false_positives'], 1)

    def test_paths_selectors_symlinks_and_caps(self):
        for changes in ({'file': '../source.py'}, {'line': True}, {'line': 2},
                        {'proof': 'ReviewProof.test_value;exit()'}, {'description': ''}):
            self.assertFalse(self.classify([{**self.finding, **changes}])['schema_valid'])
        self.assertFalse(self.classify([self.finding] * 6)['schema_valid'])
        (self.root / 'evidence.py').unlink()
        (self.root / 'evidence.py').symlink_to(self.root / 'source.py')
        self.assertFalse(self.classify([self.finding])['schema_valid'])

    def test_infrastructure_unknown(self):
        with patch('evals.review_calibration.bwrap_preflight', return_value='blocked'):
            self.assertEqual(self.classify([self.finding])['status'], 'unavailable')
        with patch('evals.review_calibration._probe', side_effect=OSError('blocked')):
            self.assertEqual(self.classify([self.finding])['status'], 'unavailable')

    def test_task_loader_splits_and_capture(self):
        task = skills.review_workflows(native_model='explicit', native_effort='low')
        self.assertEqual(len(task.dataset), 2)
        self.assertEqual(len(task.scorer), 5)
        for sample in task.dataset:
            self.assertIn('review.json', sample.metadata['artifact_paths'])
            self.assertEqual(sample.metadata['evaluation_suite'], 'review-workflows')
        with self.assertRaisesRegex(ValueError, 'outside explicit split'):
            skills.review_workflows(native_model='explicit', native_effort='low', case_ids=['reviews-export-holdout'])


class AggregationTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_review_uses_directory_write_root_and_read_only_baseline(self):
        from unittest.mock import AsyncMock
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            workspace, home = root / 'workspace', root / 'home'
            workspace.mkdir()
            home.mkdir()
            binary = root / 'native'
            binary.write_bytes(b'\x7fELFunit-fixture')
            for name in ('source.py', 'README.md', 'review.json', 'evidence.py'):
                (workspace / name).write_text('fixture')
            (workspace / '.git').mkdir()
            startup = AsyncMock(side_effect=RuntimeError('stop before model execution'))
            with (patch.object(skills, '_native_codex_binary', return_value=binary),
                  patch.object(skills, 'bwrap_preflight', return_value=None),
                  patch.object(skills, 'isolated_codex_home', return_value=skills.nullcontext(str(home))),
                  patch.object(skills, '_sandbox_workspace_path', AsyncMock(return_value=(workspace, None))),
                  patch.object(skills, '_native_skill_startup', startup),
                  self.assertRaisesRegex(RuntimeError, 'stop before model')):
                await skills.run_codex('review', model='explicit', with_skills=False,
                                           sandbox_mode='workspace-write', review_artifacts=True)
            filesystem = startup.await_args.kwargs['permissions']['permissions.skills-eval.filesystem']
            self.assertEqual(filesystem[str(workspace)], 'write')
            for name in ('source.py', 'README.md', '.git'):
                self.assertEqual(filesystem[str(workspace / name)], 'read')
            for name in ('review.json', 'evidence.py'):
                self.assertNotIn(str(workspace / name), filesystem)

    async def test_runner_owned_acceptance_branch(self):
        import asyncio
        import subprocess
        from types import SimpleNamespace
        from unittest.mock import AsyncMock

        from inspect_ai.model import ModelOutput

        class Store(dict):
            def set(self, key, value):
                self[key] = value
        case = json.loads(skills.REVIEWS_CASES.read_text())[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in case['files'].items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            control = case['metadata']['review_controls']
            (root / 'review.json').write_text(json.dumps(control['gold_report']))
            (root / 'evidence.py').write_text(control['gold_evidence'])
            async def execute(command, **options):
                self.assertEqual(command[:4], ['python', '-S', '-B', '-c'])
                process = await asyncio.to_thread(subprocess.run, command, cwd=root, capture_output=True, text=True, timeout=55, check=False)
                return SimpleNamespace(success=process.returncode == 0, stdout=process.stdout, stderr=process.stderr)
            state = SimpleNamespace(metadata=case['metadata'], store=Store(),
                                    output=ModelOutput.from_content('stub/no-model', 'control'))
            with patch.object(skills, '_sandbox_workspace_path', AsyncMock(return_value=(root, None))), patch.object(
                    skills, 'sandbox', return_value=SimpleNamespace(exec=execute)):
                score = await skills.workflow_effects()(state, None)
            self.assertEqual(score.value, 1, score)
            self.assertEqual(state.store['review_calibration']['true_positives'], 3)
            state.store['workflow_support'] = {'status': 'blocked', 'reason': 'infrastructure'}
            with patch.object(skills, 'sandbox', side_effect=AssertionError('must not execute')):
                await skills.workflow_effects()(state, None)

    async def test_actual_inspect_nan_defect_clean_unavailable(self):
        from inspect_ai import Task, eval_async
        from inspect_ai.dataset import Sample
        from inspect_ai.solver import solver
        @solver
        def controls():
            async def solve(state, generate):
                state.store.set('review_calibration', state.metadata['calibration'])
                return state
            return solve
        defect = {'status': 'valid', 'schema_valid': True, 'precision': .5, 'recall': 1,
                  'clean_no_findings': float('nan'), 'complete_review': False}
        clean = {**defect, 'precision': float('nan'), 'recall': float('nan'),
                 'clean_no_findings': 1, 'complete_review': True}
        with tempfile.TemporaryDirectory() as directory:
            logs = await eval_async(Task(dataset=[Sample(input='control', metadata={'calibration': c})
                for c in [defect, clean, {'status': 'unavailable'}]], solver=controls(),
                scorer=skills.review_quality()), model='mockllm/model', log_dir=directory)
        self.assertEqual(logs[0].status, 'success', str(logs[0].error))
        scores = {s.name: s for s in logs[0].results.scores}
        self.assertEqual(scores['precision'].metrics['mean'].value, .5)
        self.assertEqual(scores['recall'].metrics['mean'].value, 1)
        self.assertEqual(scores['clean_no_findings'].metrics['accuracy'].value, 1)
        self.assertEqual(scores['complete_review'].metrics['accuracy'].value, .5)
