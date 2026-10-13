"""Functional controls for portable lint fixtures, without model calls."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CASES = Path(__file__).resolve().parents[1] / 'cases' / 'tool-value.json'


class ToolValueCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(CASES.read_text())

    def materialize(self, root, case, sources=None):
        for name, content in {**case['files'], **(sources or {})}.items():
            (root / name).write_text(content)

    def outcomes(self, case, sources=None, weaken=False):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.materialize(root, case, sources)
            if weaken:
                (root / 'checks.py').write_text('print("PASS")\n')
            return {name: subprocess.run(
                [sys.executable, '-S', '-B', '-c', code], cwd=root,
                capture_output=True, text=True, timeout=10, check=False,
            ) for name, code in case['metadata']['fixture_contract']['acceptance_groups'].items()}

    def test_baselines_and_independent_single_repairs(self):
        for case in self.cases:
            clean = case['id'].endswith('-clean')
            controls = case['metadata']['tool_value_controls']
            with self.subTest(case=case['id']):
                baseline = self.outcomes(case)
                for group, result in baseline.items():
                    self.assertEqual(result.returncode == 0, clean or group == "regression_contract", group + result.stderr)
                for group, result in self.outcomes(case, controls['all_fixed_sources']).items():
                    self.assertEqual(result.returncode, 0, group + result.stderr)
                for fix, control in controls['single_fix_matrix'].items():
                    results = self.outcomes(case, control['sources'])
                    if clean:
                        self.assertTrue(all(r.returncode == 0 for r in results.values()))
                    else:
                        actual = {g for g, r in results.items() if r.returncode == 0}
                        self.assertEqual(actual, set(control['passing_groups']), fix)
                        self.assertEqual(set(results) - actual, set(control['failing_groups']))

    def test_native_smoke_is_narrow_and_cannot_replace_oracle(self):
        for case in self.cases:
            with self.subTest(case=case['id']), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                self.materialize(root, case)
                result = subprocess.run([sys.executable, '-B', 'checks.py'], cwd=root, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                if not case['id'].endswith('-clean'):
                    self.assertTrue(any(r.returncode for r in self.outcomes(case, weaken=True).values()))

    def test_scope_baseline_and_hidden_contract(self):
        self.assertEqual([c['id'] for c in self.cases], [
            'tool-value-import-development', 'tool-value-import-clean', 'tool-value-import-holdout'])
        self.assertEqual([c['metadata']['split'] for c in self.cases], ['development', 'development', 'holdout'])
        self.assertEqual(self.cases[0]['input'], self.cases[1]['input'])
        for case in self.cases:
            self.assertIn('Non-string keys/prefixes and arbitrary malformed objects', case['files']['README.md'])
            metadata = case['metadata']
            contract = metadata['fixture_contract']
            fixed = metadata['tool_value_controls']['all_fixed_sources']
            self.assertEqual(set(metadata['allowed_paths']), set(fixed))
            self.assertEqual(contract['golden_files'], fixed)
            self.assertEqual(contract['write_path'], 'checks.py')
            self.assertEqual(contract['write_content'], case['files']['checks.py'])
            lines = sum(len(case['files'][n].splitlines()) for n in fixed)
            self.assertTrue(100 <= lines <= 200, lines)
            for marker in ('all_fixed_sources', 'single_fix_matrix', 'acceptance_groups', 'golden_files', 'F821', 'B012', 'mypy'):
                self.assertNotIn(marker, case['input'] + ''.join(case['files'].values()))
            with tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                self.materialize(root, case)
                setup = subprocess.run(case['setup'], shell=True, cwd=root, capture_output=True, text=True, check=False)
                self.assertEqual(setup.returncode, 0, setup.stderr)
                status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True)
                self.assertEqual(status, '')
                notes = (root / 'coworker_notes.txt').read_bytes()
                self.materialize(root, case, fixed)
                changed = subprocess.check_output(['git', 'diff', '--name-only'], cwd=root, text=True)
                self.assertLessEqual(set(changed.splitlines()), set(metadata['allowed_paths']))
                self.assertEqual(notes, (root / 'coworker_notes.txt').read_bytes())

    def test_fixed_sources_pass_available_supplemental_profile(self):
        repo = CASES.parents[2]
        ruff = shutil.which('ruff') or str(repo / '.venv/bin/ruff')
        for case in self.cases:
            with self.subTest(case=case['id']), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                fixed = case['metadata']['tool_value_controls']['all_fixed_sources']
                self.materialize(root, case, fixed)
                if Path(ruff).exists():
                    result = subprocess.run([ruff, 'check', '--isolated', '--select', 'F,B012,B018', *fixed], cwd=root, capture_output=True, text=True, check=False)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    if not case['id'].endswith('-clean'):
                        self.materialize(root, case)
                        result = subprocess.run([ruff, 'check', '--isolated', '--select', 'F,B012,B018', *fixed], cwd=root, capture_output=True, text=True, check=False)
                        self.assertIn('F821', result.stdout)
                        self.assertIn('B012', result.stdout)
                        self.materialize(root, case, fixed)

    @unittest.skipUnless(shutil.which('mypy') or os.environ.get('SKILLS_LINT_RUNTIME'), 'strict mypy unavailable; set SKILLS_LINT_RUNTIME for locked integration')
    def test_strict_mypy_fixed_and_defective_sources(self):
        for case in self.cases:
            with self.subTest(case=case['id']), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                fixed = case['metadata']['tool_value_controls']['all_fixed_sources']
                self.materialize(root, case, fixed)
                runtime = os.environ.get('SKILLS_LINT_RUNTIME')
                command = ([str(Path(runtime) / 'python/bin/python'), '-I', '-m', 'mypy'] if runtime else [shutil.which('mypy')])
                command += ['--strict', '--config-file', '/dev/null', '--no-incremental', '--cache-dir', '/dev/null', *fixed]
                result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if not case['id'].endswith('-clean'):
                    self.materialize(root, case)
                    result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('[return-value]', result.stdout)



if __name__ == '__main__':
    unittest.main()
