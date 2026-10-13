"""Model-free controls for the portable lint comparison transport."""
import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evals import skills


class ToolValueRunnerTests(unittest.TestCase):
    def test_dynamic_loader_without_module_registration(self):
        import subprocess
        import sys
        code = """import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('unregistered_tool_eval', 'evals/skills.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
config = module._ToolValueConfig('baseline', Path('/owned/runtime'))
assert config.mode == 'baseline' and config.runtime == Path('/owned/runtime')
try:
 config.mode = 'available'
except AttributeError:
 pass
else:
 raise AssertionError('configuration became mutable')
"""
        result = subprocess.run([sys.executable, '-c', code], cwd=skills.REPO_ROOT,
                                capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runtime_missing_relative_traversal_unowned_and_symlink(self):
        for path in ('missing', '/nonexistent-tool-runtime', '/tmp/../tmp'):
            with self.assertRaises(ValueError):
                skills._validate_tool_runtime(path)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with self.assertRaisesRegex(ValueError, 'marker'):
                skills._validate_tool_runtime(root)
            link = root / 'linked'
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                skills._validate_tool_runtime(link)
            marker = root / 'skills-portable-lint.json'
            marker.write_text(json.dumps({'owner': 'someone-else'}))
            with self.assertRaisesRegex(ValueError, 'ownership'):
                skills._validate_tool_runtime(root)

    def test_permissions_all_modes_and_generic_denies(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output = root / 'tool-value-output'
            output.mkdir(mode=0o700)
            for mode in ('baseline', 'available', 'assisted'):
                permissions = skills._native_permission_config(binary=Path('/usr/bin/true'),
                    workspace=root / 'workspace', home=root / 'home', sandbox_mode='workspace-write',
                    skills_root=skills.SKILLS_ROOT)
                self.assertEqual(permissions['permissions.skills-eval.filesystem'][':tmpdir'], 'deny')
                with patch.object(skills, '_validate_tool_runtime', return_value=root / 'runtime'), patch.object(skills, '_native_ephemeral_cache', return_value=root):
                    skills._tool_value_permissions(permissions, skills._ToolValueConfig(mode, root / 'runtime'), output, root / 'home', skills.SKILLS_ROOT)
                fs = permissions['permissions.skills-eval.filesystem']
                access = 'deny' if mode == 'baseline' else 'read'
                self.assertEqual(fs[str(root / 'runtime')], access)
                self.assertEqual(fs[str(skills.SKILLS_ROOT / 'code-review-and-quality/scripts')], access)
                self.assertEqual(fs[str(root / 'home/skills/code-review-and-quality/scripts')], access)
                self.assertEqual(fs[str(output)], 'write')
                for name in (':root', ':slash_tmp'):
                    self.assertEqual(fs[name], 'deny')
                self.assertFalse(permissions['permissions.skills-eval.network.enabled'])
                self.assertNotIn(str(root), fs)
                with patch.object(skills, '_validate_tool_runtime'), patch.object(skills, '_native_ephemeral_cache', return_value=root), self.assertRaises(ValueError):
                    skills._tool_value_permissions(permissions, skills._ToolValueConfig(mode, root / 'runtime'), root, root / 'home', skills.SKILLS_ROOT)

    def test_receipts_bounded_no_follow_regular_and_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'a.json').write_text('{"passed": true}')
            (root / 'b.json').symlink_to(root / 'a.json')
            (root / 'c.json').write_text('x' * 256001)
            (root / 'd.json').mkdir()
            os.mkfifo(root / 'e.json')
            events = skills._tool_value_receipts(root)
            rows = [json.loads(line) for line in events.splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['authenticity'], 'candidate-written; not authenticated')
            command = {'type': 'command_execution', 'command': 'python /actual/path', 'exit_code': 0, 'aggregated_output': 'findings'}
            events += json.dumps({'type': 'item.completed', 'item': command}) + '\n'
            evidence = skills._tool_evidence(events, skills._ToolValueConfig('available', root))
            self.assertEqual(evidence['completed_commands'], [command])
            self.assertEqual(len(evidence['candidate_receipts']), 1)

    def test_large_receipt_raw_capture_summary_and_hardlink_rejection(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output = root / 'output'
            output.mkdir()
            receipt = {'passed': False, 'unavailable': 'diagnostic unavailable',
                       'dependency_inputs': {'dummy': 'x' * 300000},
                       'checks': [{'exit_code': 3}], 'diagnostics': []}
            (output / 'a.json').write_text(json.dumps(receipt))
            (output / 'b.json').write_text('{"passed": true}')
            os.link(output / 'b.json', root / 'linked.json')
            with patch.object(skills, 'REPO_ROOT', root):
                records = [json.loads(line) for line in skills._tool_value_receipts(output).splitlines()]
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertLess(len(json.dumps(record)), 256000)
            self.assertNotIn('dependency_inputs', record['receipt'])
            self.assertEqual(record['receipt']['checks'], [{'exit_code': 3}])
            self.assertEqual(json.loads(Path(record['raw_path']).read_text()), receipt)
            self.assertEqual(Path(record['raw_path']).stat().st_mode & 0o777, 0o600)
            escaped = root / 'escaped'
            escaped.symlink_to(output, target_is_directory=True)
            self.assertEqual(skills._tool_value_receipts(escaped), '')

    def test_task_loader_modes_splits_and_early_validation(self):
        options = {'native_model': 'explicit-test-model', 'native_effort': 'medium', 'tool_runtime': '/owned/runtime'}
        tasks = []
        with patch.object(skills, '_validate_tool_runtime', return_value=Path('/owned/runtime')):
            for mode in ('baseline', 'available', 'assisted'):
                task = skills.tool_value_workflows(tool_mode=mode, **options)
                tasks.append(task)
                self.assertEqual(len(task.dataset), 2)
                self.assertEqual(len(task.scorer), 4)
                self.assertEqual(task.dataset[0].metadata['evaluation_suite'], 'tool-value-workflows')
            holdout = skills.tool_value_workflows(tool_mode='available', split='holdout', **options)
            self.assertEqual([sample.id for sample in holdout.dataset], ['tool-value-import-holdout'])
            with self.assertRaisesRegex(ValueError, 'outside explicit split'):
                skills.tool_value_workflows(tool_mode='baseline', case_ids=['tool-value-import-holdout'], **options)
            with self.assertRaisesRegex(ValueError, 'unknown harder'):
                skills.tool_value_workflows(tool_mode='baseline', case_ids=['unknown'], **options)
        for task in tasks[1:]:
            for left, right in zip(tasks[0].dataset, task.dataset):
                for field in ('input', 'files', 'target', 'setup'):
                    self.assertEqual(getattr(left, field), getattr(right, field))
                self.assertEqual(left.metadata['comparison_skills_identity'], right.metadata['comparison_skills_identity'])
                self.assertEqual(left.metadata['global_identity'], right.metadata['global_identity'])
        with patch.object(skills, '_challenge_workflows') as construct:
            with self.assertRaises(ValueError):
                skills.tool_value_workflows(tool_mode='baseline', **options)
            construct.assert_not_called()


class ToolValueLauncherTests(unittest.IsolatedAsyncioTestCase):
    async def test_launcher_transports_output_and_captures_before_cleanup(self):
        from contextlib import contextmanager
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            workspace = root / 'workspace'
            workspace.mkdir()
            home = root / 'home'
            home.mkdir()
            binary = root / 'codex'
            binary.write_bytes(b'fake native binary')
            runtime = root / 'runtime'
            runtime.mkdir()
            observed = {}

            @contextmanager
            def owned_home(*args, **kwargs):
                yield home

            async def execute(command, **kwargs):
                if command[0] == 'rm':
                    return SimpleNamespace(returncode=0)
                observed.update(kwargs)
                output = Path(kwargs['env']['TMPDIR'])
                observed['directory'] = output
                (output / 'diagnostic.json').write_text('{"findings": []}')
                return SimpleNamespace(success=True, returncode=0, stdout='', stderr='')

            fixture = SimpleNamespace(exec=AsyncMock(side_effect=execute), read_file=AsyncMock(return_value='done'))
            with patch.object(skills, '_validate_tool_runtime', return_value=runtime), patch.object(skills, '_native_codex_binary', return_value=binary), patch.object(skills, 'bwrap_preflight', return_value=None), patch.object(skills, 'isolated_codex_home', owned_home), patch.object(skills, '_native_ephemeral_cache', return_value=root), patch.object(skills, '_sandbox_workspace_path', AsyncMock(return_value=(workspace, None))), patch.object(skills, '_native_skill_startup', AsyncMock(return_value=({}, {'type': 'startup'}))), patch.object(skills, 'sandbox', return_value=fixture):
                completion, events = await skills.run_codex('organic fixture input', model='explicit-model',
                    with_skills=True, sandbox_mode='workspace-write', skills_root=skills.SKILLS_ROOT,
                    _tool_config=skills._ToolValueConfig('available', runtime))
            self.assertEqual(completion, 'done')
            self.assertFalse(observed['directory'].exists())
            self.assertTrue(observed['input'].startswith('Optional portable lint capability:'))
            self.assertIn('organic fixture input', observed['input'])
            self.assertNotIn('run portable lint diagnostics before', observed['input'])
            self.assertIn('skills_eval.tool_receipt', events)
            permission_receipt = json.loads(events.splitlines()[0])
            filesystem = permission_receipt['config']['permissions.skills-eval.filesystem']
            self.assertEqual(filesystem[str(runtime)], 'read')
            self.assertEqual(filesystem[str(observed['directory'])], 'write')
            self.assertEqual(filesystem[':slash_tmp'], 'deny')


@unittest.skipUnless(os.environ.get("SKILLS_CODEX_NATIVE_BINARY") and os.environ.get("SKILLS_LINT_RUNTIME"),
                     "explicit native binary and owned runtime required for no-model containment probe")
class NativeToolValueContainmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_startup_and_adapter_access_all_modes(self):
        import subprocess
        runtime = skills._validate_tool_runtime(os.environ["SKILLS_LINT_RUNTIME"])
        binary = skills._native_codex_binary()
        for mode in ('baseline', 'available', 'assisted'):
            with skills.frozen_skills(skills.SKILLS_ROOT) as catalog, skills.isolated_codex_home(True, skills_root=catalog) as raw_home, tempfile.TemporaryDirectory(prefix='probe-workspace-', dir=skills._native_ephemeral_cache()) as raw_workspace, tempfile.TemporaryDirectory(prefix='tool-value-', dir=skills._native_ephemeral_cache()) as raw_output:
                home, workspace, output = map(Path, (raw_home, raw_workspace, raw_output))
                home_canary = home / 'owned-canary.txt'
                home_canary.write_text('private owned canary')
                sibling_canary = output.parent / (output.name + '-owned-canary.txt')
                sibling_canary.write_text('private owned sibling canary')
                self.addCleanup(sibling_canary.unlink, missing_ok=True)
                (workspace / 'module.py').write_text('def increment(value: int) -> int:\n    return value + 1\n')
                permissions = skills._native_permission_config(binary=binary, workspace=workspace, home=home,
                    sandbox_mode='workspace-write', skills_root=catalog)
                skills._tool_value_permissions(permissions, skills._ToolValueConfig(mode, runtime), output, home, catalog)
                selectors, receipt = await skills._native_skill_startup(binary=binary, workspace=workspace,
                    home=home, permissions=permissions)
                self.assertEqual(receipt['model_turns'], 0)
                permissions.update(selectors)
                helper = home / 'skills/code-review-and-quality/scripts/portable_lint.py'
                probe = """import pathlib, subprocess, sys
helper, marker, workspace, runtime, output, mode, catalog_helper, repo_file, home_canary, sibling_canary = sys.argv[1:]
reads = []
for path in (helper, marker, catalog_helper):
    try:
        pathlib.Path(path).read_bytes()
        reads.append(True)
    except OSError:
        reads.append(False)
expected = mode != 'baseline'
assert reads == [expected, expected, expected], reads
for forbidden in ("/tmp/tool-value-forbidden", marker):
    try:
        with open(forbidden, "ab"):
            pass
    except OSError:
        continue
    raise AssertionError("unexpected external write permission: " + forbidden)
for private in (repo_file, home_canary, sibling_canary):
    try:
        pathlib.Path(private).read_bytes()
    except OSError:
        pass
    else:
        raise AssertionError("unexpected private file read permission")
# Some native mount scaffolding permits ephemeral shadow files. The parent
# process verifies that this cannot mutate the real owned sibling canary.
try:
    pathlib.Path(sibling_canary).write_text("candidate shadow write")
except OSError:
    pass
if expected:
    result = subprocess.run([sys.executable, '-B', helper, '--workspace', workspace,
        '--language', 'python', '--runtime', runtime, '--receipt', output + '/adapter.json',
        '--python-executable', runtime + '/python/bin/python', '--scope', 'explicit', 'module.py'], timeout=90)
    assert result.returncode == 0, result.returncode
"""
                result = await asyncio.to_thread(subprocess.run, [str(binary), *skills._native_config_overrides(permissions),
                    'sandbox', '--permission-profile', 'skills-eval', '--cd', str(workspace), str((runtime / 'python/bin/python').resolve()), '-I', '-B', '-c', probe,
                    str(helper), str(runtime / 'skills-portable-lint.json'), str(workspace), str(runtime), str(output), mode,
                    str(catalog / 'code-review-and-quality/scripts/portable_lint.py'), str(skills.REPO_ROOT / 'evals/skills.py'),
                    str(home_canary), str(sibling_canary)],
                    cwd=workspace, env={'HOME': str(home), 'CODEX_HOME': str(home), 'PATH': '/usr/bin:/bin',
                    'TMPDIR': str(output), 'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8'},
                    capture_output=True, text=True, timeout=120, check=False)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout + skills._tool_value_receipts(output))
                self.assertEqual(sibling_canary.read_text(), 'private owned sibling canary')
                self.assertEqual(home_canary.read_text(), 'private owned canary')
                if mode != 'baseline':
                    self.assertIn('skills_eval.tool_receipt', skills._tool_value_receipts(output))


if __name__ == '__main__':
    unittest.main()
