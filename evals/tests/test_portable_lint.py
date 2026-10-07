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
