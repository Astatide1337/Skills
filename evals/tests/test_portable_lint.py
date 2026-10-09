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


_RUNTIME_DIRECTORIES = []
_RUNTIMES = {}


def integration_runtime(language):
    supplied = os.environ.get('SKILLS_LINT_RUNTIME')
    if supplied and (language != 'python' or (Path(supplied) / 'python/bin/python').is_file()):
        return Path(supplied)
    # The trusted base PR workflow may still supply its older JS-only runtime.
    # Test setup explicitly provisions the missing Python tools in another
    # owned directory; the production lint command never installs anything.
    if language not in _RUNTIMES:
        directory = tempfile.TemporaryDirectory(prefix='skills-lint-tests-')
        _RUNTIME_DIRECTORIES.append(directory)
        runtime = Path(directory.name) / 'runtime'
        setup = SCRIPT.with_name('setup_portable_lint.py')
        installed = subprocess.run([sys.executable, str(setup), '--language', language,
                                   '--runtime', str(runtime)], capture_output=True, text=True, timeout=300)
        if installed.returncode:
            raise RuntimeError('Locked integration prerequisite failed: ' + installed.stdout[-2000:] + installed.stderr[-2000:])
        _RUNTIMES[language] = runtime
    return _RUNTIMES[language]


class PythonLintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = integration_runtime('python')

    def check(self, text):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'sample.py').write_text(text)
            # App configuration and suppressions must not hide this supplement.
            (root / 'ruff.toml').write_text('lint.ignore = ["F821"]\n')
            result = lint.run(root, ['sample.py'], 'python', self.runtime)
            self.assertEqual((root / 'sample.py').read_text(), text)
            self.assertEqual(set(p.name for p in root.iterdir()), {'sample.py', 'ruff.toml'})
            return result

    def comparison(self, before, after):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); old = root / 'old'; new = root / 'new'
            old.mkdir(); new.mkdir()
            (old / 'sample.py').write_text(before); (new / 'sample.py').write_text(after)
            return lint.run(new, ['sample.py'], 'python', self.runtime, baseline_workspace=old)

    def test_existing_debt_and_clean_change_is_accepted_with_raw_failure(self):
        result = self.comparison('print(missing)  # noqa: F821\n', '# clean comment\nprint(missing)  # noqa: F821\n')
        self.assertTrue(result['passed'])
        self.assertFalse(result['full_passed'])
        self.assertEqual(result['check']['status'], 'failed')
        self.assertEqual(sum(d['rule'] == 'F821' for d in result['diagnostics']), 1)
        self.assertEqual(sum(d['current']['rule'] == 'F821' for d in result['comparison']['existing']), 1)

    def test_introduced_and_identical_duplicate_diagnostics_reject(self):
        for after in ('print(missing)\nprint(other)\n', 'print(missing)\nprint(missing)\n'):
            with self.subTest(after=after):
                result = self.comparison('print(missing)\n', after)
                self.assertFalse(result['passed'])
                self.assertEqual(sum(d['current']['rule'] == 'F821' for d in result['comparison']['existing']), 1)
                self.assertEqual(sum(d['rule'] == 'F821' for d in result['comparison']['new_or_changed']), 1)

    def test_moved_unchanged_code_and_edited_diagnostic_span(self):
        moved = self.comparison('print(missing)\nx = 1\n', 'x = 1\nprint(missing)\n')
        self.assertTrue(moved['passed'])
        edited = self.comparison('print(missing)\n', 'print(missing + 1)\n')
        self.assertFalse(edited['passed'])
        self.assertEqual(sum(d['rule'] == 'F821' for d in edited['comparison']['new_or_changed']), 1)
        fixed = self.comparison('print(missing)\n', 'print("valid")\n')
        self.assertTrue(fixed['passed'])
        self.assertEqual(sum(d['rule'] == 'F821' for d in fixed['comparison']['resolved']), 1)

    def test_missing_invalid_and_same_workspace_baselines_unavailable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); (root / 'sample.py').write_text('x = 1\n')
            for baseline in (root, root / 'absent'):
                result = lint.run(root, ['sample.py'], 'python', self.runtime, baseline_workspace=baseline)
                self.assertFalse(result['passed'])
                self.assertEqual(result['comparison']['status'], 'unavailable')
            old = root / 'old'; old.mkdir(); (old / 'sample.py').write_text('def invalid(:\n')
            result = lint.run(root, ['sample.py'], 'python', self.runtime, baseline_workspace=old)
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
        self.assertTrue(self.check('def f() -> None:\n    raise ValueError("failed")\n')['passed'])

    def test_app_module_cannot_shadow_trusted_ruff(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'sample.py').write_text('print(missing_name)\n')
            (root / 'ruff.py').write_text('from pathlib import Path\nPath("executed").touch()\nprint("[]")\n')
            result = lint.run(root, ['sample.py'], 'python', self.runtime)
            self.assertFalse(result['passed'])
            self.assertIn('F821', result['check']['stdout'])
            self.assertFalse((root / 'executed').exists())

    def test_paths_and_empty_coverage_reject(self):
        with tempfile.TemporaryDirectory() as raw:
            for files in ([], ['../bad.py'], ['/tmp/bad.py'], ['-bad.py'], ['sample.ts']):
                with self.subTest(files=files), self.assertRaises((ValueError, OSError)):
                    lint.run(Path(raw), files, 'python', self.runtime)

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


    def test_strict_wrong_return_untyped_and_suppressions_fail(self):
        for source in ('def value() -> str:\n    return 1\n',
                       'def value(x):\n    return x\n',
                       '# mypy: ignore-errors\ndef value() -> str:\n    return 1  # type: ignore[return-value]\n'):
            with self.subTest(source=source):
                result = self.check(source)
                self.assertFalse(result['passed'])
                self.assertTrue(any(item['rule'].startswith('mypy/') for item in result['diagnostics']))
        self.assertTrue(self.check('def value(x: str) -> str:\n    return x\n')['passed'])

    def test_imported_snapshot_preserves_context_and_detects_suppressed_error(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); (root / 'pkg').mkdir()
            (root / 'pkg/imported.py').write_text('def value() -> str:\n    return 1  # type: ignore\n')
            (root / 'sample.py').write_text('from pkg.imported import value\nx: str = value()\n')
            result = lint.run(root, ['sample.py'], 'python', self.runtime)
            self.assertFalse(result['passed'])
            self.assertIn('pkg/imported.py', result['source_before'])
            self.assertTrue(any(item['file'] == 'pkg/imported.py' and item['rule'] == 'mypy/return-value' for item in result['diagnostics']))
            self.assertTrue(result['unchanged_inputs'])

    def test_missing_import_is_unavailable_for_debt(self):
        result = self.comparison('import absent_fixture_package\n', 'import absent_fixture_package\n')
        self.assertFalse(result['passed'])
        self.assertFalse(result['diagnostics_available'])
        self.assertEqual(result['comparison']['status'], 'unavailable')

    def test_new_file_is_full_checked_and_changed_context_is_not_inherited(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); old = root / 'old'; new = root / 'new'; old.mkdir(); new.mkdir()
            (old / 'sample.py').write_text('x = 1\n'); (new / 'sample.py').write_text('x = 2\n')
            (new / 'added.py').write_text('print(missing)\n')
            bad = lint.run(new, ['sample.py', 'added.py'], 'python', self.runtime, baseline_workspace=old)
            self.assertFalse(bad['passed'])
            self.assertEqual(bad['comparison']['new_files_full_checked'], ['added.py'])
            (new / 'added.py').write_text('x = 3\n')
            good = lint.run(new, ['sample.py', 'added.py'], 'python', self.runtime, baseline_workspace=old)
            self.assertTrue(good['passed'])
            (old / 'imported.py').write_text('x = 1\n'); (new / 'imported.py').write_text('x = 2\n')
            changed = lint.run(new, ['sample.py', 'added.py'], 'python', self.runtime, baseline_workspace=old)
            self.assertEqual(changed['comparison']['status'], 'unavailable')
            self.assertIn('context differs', changed['comparison']['reason'])

    def test_target_interpreter_version_controls_typeshed_and_venv_context(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); app = root / 'app'; app.mkdir()
            target = root / 'target'
            subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(target)], check=True, capture_output=True)
            executable = target / 'bin/python'
            (app / 'sample.py').write_text('from functools import Placeholder\nvalue = Placeholder\n')
            result = lint.run(app, ['sample.py'], 'python', self.runtime, python_executable=executable)
            observed = result['context']['python']['facts']['version']
            argv = result['checks'][1]['argv']
            self.assertEqual(argv[argv.index('--python-version') + 1], '.'.join(str(part) for part in observed[:2]))
            self.assertEqual(result['context']['python']['interpreter'], str(executable))
            self.assertIn(str(target), result['context']['python']['facts']['paths']['purelib'])
            if tuple(observed[:2]) < (3, 14):
                self.assertFalse(result['passed'])
                self.assertIn('mypy/attr-defined', {item['rule'] for item in result['diagnostics']})
            else:
                self.assertTrue(result['passed'])

    def test_large_real_diagnostics_survive_external_output_envelope(self):
        result = self.check('print(missing)\n' * 200)
        self.assertFalse(result['passed'])
        self.assertTrue(result['diagnostics_available'])
        self.assertGreater(len(result['check']['stdout'].encode()), 65536)
        self.assertEqual(sum(item['rule'] == 'F821' for item in result['diagnostics']), 200)

    def test_target_pth_external_import_root_is_unavailable_without_reading_it(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); app = root / 'app'; app.mkdir()
            target = root / 'target'; external = root / 'external'; external.mkdir()
            subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(target)],
                           check=True, capture_output=True)
            executable = target / 'bin/python'
            site = subprocess.run([str(executable), '-I', '-c',
                'import sysconfig; print(sysconfig.get_path("purelib"))'],
                check=True, capture_output=True, text=True).stdout.strip()
            pth = Path(site) / 'fixture.pth'; pth.write_text(str(external) + '\n')
            (external / 'fixturedep').mkdir()
            stub = external / 'fixturedep/__init__.pyi'; stub.write_text('value: str\n')
            source = 'from fixturedep import value\nresult: str = value\n'
            (app / 'sample.py').write_text(source)
            receipt = root / 'receipt.json'
            result = subprocess.run([sys.executable, str(SCRIPT), '--workspace', str(app),
                '--runtime', str(self.runtime), '--python-executable', str(executable),
                '--receipt', str(receipt), 'sample.py'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 3)
            unavailable = json.loads(receipt.read_text())
            self.assertFalse(unavailable['passed'])
            self.assertIn('site/.pth context', unavailable['unavailable'])
            self.assertEqual((app / 'sample.py').read_text(), source)
            self.assertEqual(stub.read_text(), 'value: str\n')
            # A regular .pth that does not introduce another root is recorded.
            pth.write_text('# bounded native context\n')
            (app / 'sample.py').write_text('value: str = "ok"\n')
            accepted = lint.run(app, ['sample.py'], 'python', self.runtime,
                                python_executable=executable)
            self.assertTrue(accepted['passed'])
            self.assertIn(str(pth), accepted['context']['inputs'])
            self.assertIn(str(target / 'pyvenv.cfg'), accepted['context']['inputs'])


class TypeScriptLintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = integration_runtime('typescript')

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
            self.assertEqual(sum(d['rule'] == '@typescript-eslint/no-floating-promises' for d in result['comparison']['new_or_changed']), 1)
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
        result = self.check('export const x = 1;\n', config=False)
        self.assertFalse(result['passed'])
        self.assertFalse(result['diagnostics_available'])


    def test_strict_compiler_unsafe_rules_and_native_type_suppression(self):
        for source, rule in (
            ('export const value: string = 1;\n', 'typescript/TS2322'),
            ('export function value(x) { return x; }\n', 'typescript/TS7006'),
            ('export const value: any = 1;\n', '@typescript-eslint/no-explicit-any'),
            ('declare const input: any;\ninput.member();\n', '@typescript-eslint/no-unsafe-call'),
            ('declare const input: any;\ndeclare function use(x: string): void;\nuse(input);\n', '@typescript-eslint/no-unsafe-argument'),
            ('// @ts-ignore\nexport const value: string = 1;\n', 'typescript/suppression'),
        ):
            with self.subTest(rule=rule):
                result = self.check(source)
                self.assertFalse(result['passed'])
                self.assertIn(rule, {item['rule'] for item in result['diagnostics']})

    def test_nearest_config_alias_and_import_identity_without_root_config(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); app = root / 'packages/app'; app.mkdir(parents=True)
            config = {'compilerOptions': {'target': 'ES2022', 'module': 'ESNext', 'moduleResolution': 'bundler',
                      'strict': False, 'paths': {'@local/*': ['./src/*']}}, 'include': ['src']}
            (app / 'tsconfig.json').write_text(json.dumps(config)); (app / 'src').mkdir()
            (app / 'src/value.ts').write_text('export const value: string = "known";\n')
            (app / 'src/sample.ts').write_text('import {value} from "@local/value";\nexport const result: string = value;\n')
            result = lint.run(root, ['packages/app/src/sample.ts'], 'typescript', self.runtime)
            self.assertTrue(result['passed'], result.get('diagnostic_error'))
            self.assertIn('packages/app/tsconfig.json', result['context']['configs'])
            self.assertIn(str(app / 'src/value.ts'), result['context']['inputs'])
            self.assertFalse((root / 'tsconfig.json').exists())
            (app / 'src/value.ts').write_text('export const value: number = 1;\n')
            failed = lint.run(root, ['packages/app/src/sample.ts'], 'typescript', self.runtime)
            self.assertFalse(failed['passed'])
            self.assertIn('typescript/TS2322', {item['rule'] for item in failed['diagnostics']})

    def test_javascript_native_checkjs_and_jsx_hooks_without_typed_context(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'jsconfig.json').write_text(json.dumps({'compilerOptions': {'allowJs': True, 'checkJs': False, 'target': 'ES2022'}, 'include': ['sample.js']}))
            (root / 'sample.js').write_text('/** @type {string} */\nexport const value = 1;\n')
            failed = lint.run(root, ['sample.js'], 'typescript', self.runtime)
            self.assertFalse(failed['passed'])
            self.assertIn('typescript/TS2322', {item['rule'] for item in failed['diagnostics']})
            (root / 'sample.js').write_text('/** @type {string} */\nexport const value = "known";\n')
            self.assertTrue(lint.run(root, ['sample.js'], 'typescript', self.runtime)['passed'])
            (root / 'sample.jsx').write_text('import {useState} from "react";\nexport function View({flag}) { if (flag) useState(0); return null; }\n')
            hooks = lint.run(root, ['sample.jsx'], 'typescript', self.runtime)
            self.assertFalse(hooks['passed'])
            self.assertFalse(hooks['diagnostics_available'])
            self.assertIn('react-hooks/rules-of-hooks', {item['rule'] for item in hooks['diagnostics']})

    def test_sensitive_import_context_is_unavailable_without_byte_hashes(self):
        for name in ('private/value.ts', '.config/value.ts', 'src/token-value.ts'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as raw:
                root = Path(raw); target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('export const value: number = 1;\n')
                (root / 'sample.ts').write_text('import {value} from "./' + name.removesuffix('.ts') + '";\nexport const result = value;\n')
                (root / 'tsconfig.json').write_text(json.dumps({'compilerOptions': {'target': 'ES2022'}, 'include': ['sample.ts']}))
                result = lint.run(root, ['sample.ts'], 'typescript', self.runtime)
                self.assertFalse(result['passed'])
                self.assertFalse(result['diagnostics_available'])
                raw = json.loads(result['check']['stdout'])
                self.assertNotIn(str(target), raw['context']['inputs'])

    def test_typed_react_hook_contract_and_missing_effect_dependency(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'tsconfig.json').write_text(json.dumps({'compilerOptions': {'strict': True, 'target': 'ES2022', 'jsx': 'react-jsx'}, 'include': ['sample.tsx', 'react.d.ts']}))
            # Real plugin/parser/compiler against a declared project module;
            # separately retained integration proof uses actual React19 packages.
            (root / 'react.d.ts').write_text('declare module "react" { export function useState(value: number): [number, (value: number) => void]; export function useEffect(effect: () => void, deps: unknown[]): void; }\n')
            sources = [
                ('import {useState} from "react";\nexport function View({flag}: {flag: boolean}): number { if (flag) useState(0); return 0; }\n', 'react-hooks/rules-of-hooks'),
                ('import {useEffect} from "react";\nexport function View({value}: {value: number}): number { useEffect(() => { console.log(value); }, []); return value; }\n', 'react-hooks/exhaustive-deps'),
                ('import {useState} from "react";\nexport function View(): number { const [value] = useState(0); return value; }\n', None),
            ]
            for source, rule in sources:
                with self.subTest(rule=rule):
                    (root / 'sample.tsx').write_text(source)
                    result = lint.run(root, ['sample.tsx'], 'typescript', self.runtime)
                    if rule:
                        self.assertFalse(result['passed'])
                        self.assertIn(rule, {item['rule'] for item in result['diagnostics']})
                    else:
                        self.assertTrue(result['passed'], result.get('diagnostic_error'))
                    self.assertEqual((root / 'sample.tsx').read_text(), source)


class DiscoveryTests(unittest.TestCase):
    def test_changed_accounts_added_deleted_generated_unmatched_and_spaces(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'old.py').write_text('x = 1\n')
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], check=True)
            (root / 'old.py').unlink()
            (root / 'file with spaces.py').write_text('x = 2\n')
            (root / 'note.txt').write_text('ordinary text')
            (root / 'dist').mkdir(); (root / 'dist/generated.ts').write_text('export const x = 1;\n')
            result = lint.discover(root, [], scope='changed', base='HEAD')
            self.assertEqual(result['selected'], ['file with spaces.py'])
            self.assertEqual(result['deleted'], ['old.py'])
            self.assertEqual(result['unmatched'], ['note.txt'])
            self.assertEqual(result['excluded'][0]['file'], 'dist/generated.ts')
            self.assertEqual(result['language_mapping'], {'file with spaces.py': 'python'})
            self.assertFalse(result['context_failures'])

    def test_directory_exposes_unsafe_selected_context_and_exclusions(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); (root / 'src').mkdir()
            (root / 'src/okay.py').write_text('x = 1\n')
            (root / 'src/escape.py').symlink_to('/etc/passwd')
            (root / 'src/.venv').mkdir(); (root / 'src/.venv/hidden.py').write_text('x = 1\n')
            result = lint.discover(root, [], scope='directory', source_dir='src')
            self.assertEqual(result['selected'], ['src/okay.py'])
            self.assertEqual({item['file'] for item in result['excluded']}, {'src/escape.py', 'src/.venv'})
            explicit = lint.discover(root, ['src/escape.py'])
            self.assertTrue(explicit['context_failures'])
            self.assertFalse(explicit['selected'])

    def test_explicit_unsupported_file_is_not_a_passing_skip(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); (root / 'note.txt').write_text('text')
            result = lint.discover(root, ['note.txt'])
            self.assertTrue(result['context_failures'])
            receipt = root.parent / (root.name + '-receipt.json')
            self.addCleanup(receipt.unlink, missing_ok=True)
            run = subprocess.run([sys.executable, str(SCRIPT), '--workspace', str(root), '--receipt', str(receipt), 'note.txt'], capture_output=True)
            self.assertEqual(run.returncode, 3)
            self.assertFalse(json.loads(receipt.read_text())['passed'])

    def test_non_git_and_bad_discovery_options_fail_usefully(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for kwargs in ({'scope': 'tracked'}, {'scope': 'changed', 'base': 'HEAD'},
                           {'scope': 'directory', 'source_dir': '../outside'}, {'scope': 'changed'}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    lint.discover(root, [], **kwargs)


class SetupTests(unittest.TestCase):
    def test_longer_version_prefixes_cannot_impersonate_exact_pins(self):
        helper = lint.runtime_helper()
        for package, observed in (('ruff', 'ruff 0.16.100'), ('mypy', 'mypy 2.4.01 (compiled: yes)')):
            with self.subTest(observed=observed), self.assertRaisesRegex(ValueError, 'requires'):
                helper.require_python_tool_version(package, observed)
        helper.require_python_tool_version('ruff', 'ruff 0.16.10')
        helper.require_python_tool_version('mypy', 'mypy 2.4.0 (compiled: yes)')

    def test_existing_foreign_runtime_is_preserved(self):
        setup = SCRIPT.with_name('setup_portable_lint.py')
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); (root / 'keep').write_text('custom runtime')
            run = subprocess.run([sys.executable, str(setup), '--language', 'python', '--runtime', str(root)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 3)
            self.assertIn('already exists', json.loads(run.stdout)['unavailable'])
            self.assertEqual(sorted(path.name for path in root.iterdir()), ['keep'])

    def test_real_doctor_is_read_only_and_reports_missing_runtime(self):
        runtime = integration_runtime('python')
        setup = SCRIPT.with_name('setup_portable_lint.py')
        before = {path.name: path.stat().st_mtime_ns for path in runtime.iterdir()}
        run = subprocess.run([sys.executable, str(setup), '--doctor', '--language', 'python', '--runtime', str(runtime)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)['tools']['mypy'], '2.4.0')
        self.assertEqual(before, {path.name: path.stat().st_mtime_ns for path in runtime.iterdir()})
        missing = subprocess.run([sys.executable, str(setup), '--doctor', '--language', 'python', '--runtime', str(runtime / 'missing')], capture_output=True, text=True)
        self.assertEqual(missing.returncode, 3)

    def test_missing_helper_blocks_doctor_and_setup_before_installation(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); skills = root / 'skills'
            shutil.copytree(ROOT / 'skills/code-review-and-quality', skills / 'code-review-and-quality')
            setup = skills / 'code-review-and-quality/scripts/setup_portable_lint.py'
            runtime = root / 'runtime'
            for mode in ([], ['--doctor']):
                result = subprocess.run([sys.executable, str(setup), '--language', 'python', '--runtime', str(runtime), *mode], capture_output=True, text=True)
                self.assertEqual(result.returncode, 3)
                self.assertIn('verify-work helper', json.loads(result.stdout)['unavailable'])
                self.assertFalse(runtime.exists())
            helper = skills / 'verify-work/scripts/check_profile.py'
            helper.parent.mkdir(parents=True)
            helper.write_text('def incompatible(): pass\n')
            result = subprocess.run([sys.executable, str(setup), '--doctor', '--language', 'python'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 3)
            self.assertIn('incompatible verify-work helper', json.loads(result.stdout)['unavailable'])

    def test_missing_prerequisite_fails_before_creating_runtime(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); runtime = root / 'runtime'
            env = os.environ.copy(); env['PATH'] = str(root)
            run = subprocess.run([sys.executable, str(SCRIPT.with_name('setup_portable_lint.py')), '--language', 'typescript', '--runtime', str(runtime)], env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 3)
            self.assertFalse(runtime.exists())


if __name__ == '__main__':
    unittest.main()
