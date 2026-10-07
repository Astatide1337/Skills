"""Actual Ruff/ESLint regressions; absent integration tooling fails, never skips."""
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'skills/code-review-and-quality/scripts/portable_lint.py'
spec = importlib.util.spec_from_file_location('lint_profile', SCRIPT)
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)


class PythonLintTests(unittest.TestCase):
    def check(self, text):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'sample.py').write_text(text)
            # App configuration and suppressions must not hide this supplement.
            (root / 'ruff.toml').write_text('lint.ignore = ["F821"]\n')
            result = lint.run(root, ['sample.py'], 'python', None)
            self.assertEqual((root / 'sample.py').read_text(), text)
            self.assertEqual(set(p.name for p in root.iterdir()), {'sample.py', 'ruff.toml'})
            return result

    def comparison(self, before, after):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); old = root / 'old'; new = root / 'new'
            old.mkdir(); new.mkdir()
            (old / 'sample.py').write_text(before); (new / 'sample.py').write_text(after)
            return lint.run(new, ['sample.py'], 'python', None, baseline_workspace=old)

    def test_existing_debt_and_clean_change_is_accepted_with_raw_failure(self):
        result = self.comparison('print(missing)  # noqa: F821\n', '# clean comment\nprint(missing)  # noqa: F821\n')
        self.assertTrue(result['passed'])
        self.assertFalse(result['full_passed'])
        self.assertEqual(result['check']['status'], 'failed')
        self.assertEqual(len(result['diagnostics']), 1)
        self.assertEqual(len(result['comparison']['existing']), 1)

    def test_introduced_and_identical_duplicate_diagnostics_reject(self):
        for after in ('print(missing)\nprint(other)\n', 'print(missing)\nprint(missing)\n'):
            with self.subTest(after=after):
                result = self.comparison('print(missing)\n', after)
                self.assertFalse(result['passed'])
                self.assertEqual(len(result['comparison']['existing']), 1)
                self.assertEqual(len(result['comparison']['new_or_changed']), 1)

    def test_moved_unchanged_code_and_edited_diagnostic_span(self):
        moved = self.comparison('print(missing)\nx = 1\n', 'x = 1\nprint(missing)\n')
        self.assertTrue(moved['passed'])
        edited = self.comparison('print(missing)\n', 'print(missing + 1)\n')
        self.assertFalse(edited['passed'])
        self.assertEqual(len(edited['comparison']['new_or_changed']), 1)
        fixed = self.comparison('print(missing)\n', 'print("valid")\n')
        self.assertTrue(fixed['passed'])
        self.assertEqual(len(fixed['comparison']['resolved']), 1)

    def test_missing_invalid_and_same_workspace_baselines_unavailable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); (root / 'sample.py').write_text('x = 1\n')
            for baseline in (root, root / 'absent'):
                result = lint.run(root, ['sample.py'], 'python', None, baseline_workspace=baseline)
                self.assertFalse(result['passed'])
                self.assertEqual(result['comparison']['status'], 'unavailable')
            old = root / 'old'; old.mkdir(); (old / 'sample.py').write_text('def invalid(:\n')
            result = lint.run(root, ['sample.py'], 'python', None, baseline_workspace=old)
            self.assertFalse(result['passed'])
            self.assertEqual(result['comparison']['status'], 'unavailable')

    def test_incompatible_toolchain_never_becomes_passing_comparison(self):
        from unittest.mock import patch
        original = lint.full_check
        calls = 0
        def incompatible(*args):
            nonlocal calls
            result = original(*args); calls += 1
            if calls == 2:
                result['tools'] = {'ruff': 'different'}
            return result
        with patch.object(lint, 'full_check', incompatible):
            result = self.comparison('x = 1\n', 'x = 2\n')
        self.assertFalse(result['passed'])
        self.assertEqual(result['comparison']['status'], 'unavailable')
        self.assertIn('toolchain', result['comparison']['reason'])

    def test_undefined_name_and_suppression_fail(self):
        result = self.check('print(missing_name)  # noqa: F821\n')
        self.assertFalse(result['passed'])
        self.assertIn('F821', result['check']['stdout'])

    def test_finally_swallowing_exception_fails(self):
        result = self.check('def f():\n    try:\n        raise ValueError()\n    finally:\n        return 1\n')
        self.assertFalse(result['passed'])
        self.assertIn('B012', result['check']['stdout'])

    def test_useless_expression_fails(self):
        result = self.check('def f():\n    1 + 1\n')
        self.assertFalse(result['passed'])
        self.assertIn('B018', result['check']['stdout'])

    def test_valid_error_propagation_passes(self):
        self.assertTrue(self.check('def f():\n    raise ValueError("failed")\n')['passed'])

    def test_app_module_cannot_shadow_trusted_ruff(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'sample.py').write_text('print(missing_name)\n')
            (root / 'ruff.py').write_text('from pathlib import Path\nPath("executed").touch()\nprint("[]")\n')
            result = lint.run(root, ['sample.py'], 'python', None)
            self.assertFalse(result['passed'])
            self.assertIn('F821', result['check']['stdout'])
            self.assertFalse((root / 'executed').exists())

    def test_paths_and_empty_coverage_reject(self):
        with tempfile.TemporaryDirectory() as raw:
            for files in ([], ['../bad.py'], ['/tmp/bad.py'], ['-bad.py'], ['sample.ts']):
                with self.subTest(files=files), self.assertRaises((ValueError, OSError)):
                    lint.run(Path(raw), files, 'python', None)

    def test_receipt_cannot_write_to_baseline_checkout(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); old = root / 'old'; new = root / 'new'; old.mkdir(); new.mkdir()
            for path in (old, new):
                (path / 'sample.py').write_text('x = 1\n')
            receipt = old / 'receipt.json'
            result = subprocess.run([sys.executable, str(SCRIPT), '--workspace', str(new),
                '--language', 'python', '--mode', 'compare', '--baseline-workspace', str(old),
                '--receipt', str(receipt), 'sample.py'], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(receipt.exists())

    def test_receipt_collision_prevents_execution(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            workspace = root / 'app'; workspace.mkdir()
            (workspace / 'sample.py').write_text('x = 1\n')
            receipt = root / 'receipt.json'; receipt.write_text('keep')
            result = subprocess.run([sys.executable, str(SCRIPT), '--workspace', str(workspace),
                                     '--language', 'python', '--receipt', str(receipt), 'sample.py'], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(receipt.read_text(), 'keep')


class TypeScriptLintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Existing full-suite entry points also need the real integration tools.
        # No mocked substitute or passing skip; install only in an owned tempdir.
        runtime = os.environ.get('SKILLS_LINT_RUNTIME')
        if runtime:
            cls.runtime = Path(runtime)
        else:
            cls.directory = tempfile.TemporaryDirectory(prefix='skills-lint-tests-')
            cls.addClassCleanup(cls.directory.cleanup)
            cls.runtime = Path(cls.directory.name)
            source = ROOT / 'skills/code-review-and-quality/assets/portable-lint'
            for name in ('package.json', 'package-lock.json'):
                shutil.copyfile(source / name, cls.runtime / name)
            installed = subprocess.run(['npm', 'ci', '--prefix', str(cls.runtime),
                                        '--ignore-scripts', '--no-audit', '--no-fund'],
                                       capture_output=True, text=True, timeout=120)
            if installed.returncode:
                raise RuntimeError('Locked TypeScript integration prerequisite failed: ' + installed.stderr[-2000:])

    def check(self, text, *, config=True):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'sample.ts').write_text(text)
            if config:
                (root / 'tsconfig.json').write_text(json.dumps({'compilerOptions': {'strict': True, 'target': 'ES2022'}, 'include': ['sample.ts']}))
            result = lint.run(root, ['sample.ts'], 'typescript', self.runtime)
            self.assertEqual((root / 'sample.ts').read_text(), text)
            self.assertEqual(set(p.name for p in root.iterdir()), {'sample.ts', 'tsconfig.json'} if config else {'sample.ts'})
            return result

    def test_typescript_debt_comparison_retains_multiplicity_and_parser_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            old = Path(raw) / 'old'; new = Path(raw) / 'new'; old.mkdir(); new.mkdir()
            config = json.dumps({'compilerOptions': {'strict': True, 'target': 'ES2022'}, 'include': ['sample.ts']})
            for root in (old, new):
                (root / 'tsconfig.json').write_text(config)
            (old / 'sample.ts').write_text('Promise.resolve(1);\n')
            (new / 'sample.ts').write_text('// clean change\nPromise.resolve(1);\n')
            result = lint.run(new, ['sample.ts'], 'typescript', self.runtime, baseline_workspace=old)
            self.assertTrue(result['passed'], result)
            self.assertFalse(result['full_passed'])
            (new / 'sample.ts').write_text('Promise.resolve(1);\nPromise.resolve(1);\n')
            result = lint.run(new, ['sample.ts'], 'typescript', self.runtime, baseline_workspace=old)
            self.assertFalse(result['passed'])
            self.assertEqual(len(result['comparison']['new_or_changed']), 1)
            (old / 'tsconfig.json').unlink()
            result = lint.run(new, ['sample.ts'], 'typescript', self.runtime, baseline_workspace=old)
            self.assertFalse(result['passed'])
            self.assertEqual(result['comparison']['status'], 'unavailable')

    def test_floating_void_and_inline_ignore_fail(self):
        for text in ('Promise.resolve(1);\n', 'void Promise.resolve(1);\n',
                     '// eslint-disable-next-line @typescript-eslint/no-floating-promises\nPromise.resolve(1);\n'):
            with self.subTest(text=text):
                result = self.check(text)
                self.assertFalse(result['passed'])
                self.assertIn('no-floating-promises', result['check']['stdout'])

    def test_handled_promise_passes(self):
        self.assertTrue(self.check('Promise.resolve(1).catch(() => {});\n')['passed'])

    def test_misused_callback_fails(self):
        result = self.check('declare function onSave(cb: () => void): void;\nonSave(async () => {});\n')
        self.assertFalse(result['passed'])
        self.assertIn('no-misused-promises', result['check']['stdout'])

    def test_unsafe_external_assignment_and_return_fail(self):
        for text, rule in (
            ('const name: string = JSON.parse("null");\n', 'no-unsafe-assignment'),
            ('export function read(): string { return JSON.parse("null"); }\n', 'no-unsafe-return'),
        ):
            with self.subTest(rule=rule):
                result = self.check(text)
                self.assertFalse(result['passed'])
                self.assertIn(rule, result['check']['stdout'])

    def test_narrowing_cast_fails_but_validated_value_passes(self):
        bad = self.check('declare const input: unknown;\nconst value = input as string;\n')
        self.assertFalse(bad['passed'])
        self.assertIn('no-unsafe-type-assertion', bad['check']['stdout'])
        good = self.check('export function parse(input: unknown): string {\n'
                          '  if (typeof input !== "string") throw new Error("invalid input");\n'
                          '  return input;\n}\n')
        self.assertTrue(good['passed'])

    def test_missing_variant_fails_even_with_default_fallback(self):
        bad = self.check('export function label(state: "pending" | "saved"): string {\n'
                         '  switch (state) { case "pending": return "Waiting"; default: return "Done"; }\n}\n')
        self.assertFalse(bad['passed'])
        self.assertIn('switch-exhaustiveness-check', bad['check']['stdout'])
        good = self.check('export function label(state: "pending" | "saved"): string {\n'
                          '  switch (state) { case "pending": return "Waiting"; case "saved": return "Done"; }\n}\n')
        self.assertTrue(good['passed'])

    def test_valid_type_widening_and_local_array_need_no_new_types(self):
        self.assertTrue(self.check('const count = 1 as number | string;\n'
                                  'export function first(values: string[]): string | undefined { return values[0]; }\n')['passed'])

    def test_missing_project_is_unavailable(self):
        with self.assertRaisesRegex(ValueError, "expected a regular"):
            self.check('export const x = 1;\n', config=False)
