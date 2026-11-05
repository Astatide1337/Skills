"""Exercise task registration shared by a checkout and its linked worktrees."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

GATE = Path(__file__).resolve().parents[2] / 'global-instructions/hooks/agent_gates.py'


class HookWorkspaceScopeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.target = self.root / 'target'
        self.other = self.root / 'other'
        self.target.mkdir()
        self.other.mkdir()
        self.marker = self.root / 'executed'
        self.checker = self.root / 'checker.py'
        self.checker.write_text(
            'import json,sys\nfrom pathlib import Path\n'
            f'Path({str(self.marker)!r}).touch()\n'
            "p=json.load(sys.stdin)\n"
            "print(json.dumps({'status':'block' if p.get('hook_event_name')=='PreToolUse' else 'incomplete',"
            "'reason':'Unfinished task'}))\n")
        self.env = {**os.environ, 'AGENT_GATES_STATE': str(self.root / 'state')}

    def invoke(self, mode, cwd, scope=None, active=False, event=None):
        payload = {'session_id': 'owned', 'cwd': cwd, 'tool_name': 'Bash',
                   'tool_input': {'command': 'pwd'}, 'stop_hook_active': active,
                   'hook_event_name': event or ('Stop' if mode == 'completion' else 'PreToolUse')}
        return subprocess.run(
            [sys.executable, str(GATE), mode, '--cwd', str(scope or self.target),
             sys.executable, str(self.checker)], input=json.dumps(payload),
            text=True, capture_output=True, env=self.env, timeout=5, check=False)

    def test_target_rejection_and_unrelated_session_without_checker_execution(self):
        for mode in ['completion', 'choice-guard']:
            with self.subTest(mode=mode):
                outside = self.invoke(mode, str(self.other))
                self.assertEqual(outside.returncode, 0, outside.stderr)
                self.assertEqual(json.loads(outside.stdout), {})
                self.assertFalse(self.marker.exists())
                self.assertFalse((self.root / 'state').exists())
                target = self.invoke(mode, str(self.target))
                self.assertTrue(self.marker.exists())
                if mode == 'choice-guard':
                    self.assertEqual(target.returncode, 2)
                else:
                    self.assertEqual(json.loads(target.stdout)['decision'], 'block')
                self.marker.unlink()
                # Scope checks outside the target must not change saved continuation state.
                before = {str(p): p.read_bytes() for p in (self.root / 'state').glob('*')} if (self.root / 'state').exists() else {}
                self.invoke(mode, str(self.other))
                after = {str(p): p.read_bytes() for p in (self.root / 'state').glob('*')} if (self.root / 'state').exists() else {}
                self.assertEqual(before, after)
            if (self.root / 'state').exists():
                import shutil
                shutil.rmtree(self.root / 'state')

    def test_invalid_scope_and_missing_event_cwd_do_not_run_checker(self):
        for mode in ['completion', 'choice-guard']:
            for cwd, scope in [(str(self.target), 'relative'), (None, self.target), ('relative', self.target)]:
                with self.subTest(mode=mode, cwd=cwd, scope=str(scope)):
                    result = self.invoke(mode, cwd, scope)
                    self.assertFalse(self.marker.exists())
                    if mode == 'choice-guard':
                        self.assertEqual(result.returncode, 2)
                        self.assertIn('Invalid hook workspace scope', result.stderr)
                    else:
                        value = json.loads(result.stdout)
                        self.assertEqual(value['decision'], 'block')
                        self.assertIn('Invalid hook workspace scope', value['reason'])

    def test_scope_errors_keep_completion_retry_limit(self):
        for active in [False, True]:
            self.assertEqual(json.loads(self.invoke('completion', None, active=active).stdout)['decision'], 'block')
        self.assertIn('unaccepted', json.loads(self.invoke('completion', None, active=True).stdout)['systemMessage'])
        self.assertFalse(self.marker.exists())

    def test_recovered_event_cwd_continues_the_same_acceptance_episode(self):
        self.assertEqual(json.loads(self.invoke('completion', None).stdout)['decision'], 'block')
        self.assertFalse(self.marker.exists())
        recovered = self.invoke('completion', str(self.target), active=True)
        self.assertEqual(json.loads(recovered.stdout)['decision'], 'block')
        self.assertTrue(self.marker.exists())
        exhausted = self.invoke('completion', str(self.target), active=True)
        self.assertIn('unaccepted', json.loads(exhausted.stdout)['systemMessage'])

    def test_missing_or_nondirectory_paths_are_unavailable_not_outside_scope(self):
        regular = self.root / 'file'
        regular.touch()
        dangling = self.root / 'dangling'
        dangling.symlink_to(self.root / 'missing')
        loop = self.root / 'loop'
        loop.symlink_to(loop.name)
        for mode in ['completion', 'choice-guard']:
            for bad in [self.root / 'missing', regular, dangling, loop]:
                for cwd, scope in [(str(self.target), bad), (str(bad), self.target)]:
                    with self.subTest(mode=mode, cwd=cwd, scope=str(scope)):
                        result = self.invoke(mode, cwd, scope)
                        self.assertFalse(self.marker.exists())
                        if mode == 'choice-guard':
                            self.assertEqual(result.returncode, 2)
                            self.assertIn('Invalid hook workspace scope', result.stderr)
                        else:
                            self.assertEqual(json.loads(result.stdout)['decision'], 'block')

    def test_canonical_alias_matches_but_descendant_is_a_distinct_session(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.target, target_is_directory=True)
        self.assertEqual(self.invoke('choice-guard', str(alias)).returncode, 2)
        self.marker.unlink()
        child = self.target / 'nested'
        child.mkdir()
        self.assertEqual(self.invoke('choice-guard', str(child)).returncode, 0)
        self.assertFalse(self.marker.exists())

    def test_interrupt_does_not_run_scoped_checker(self):
        result = self.invoke('completion', None, event='Interrupt')
        self.assertEqual(json.loads(result.stdout), {})
        self.assertFalse(self.marker.exists())

    def test_parent_acceptance_cannot_be_skipped_with_scope_option(self):
        result = self.invoke('accept', str(self.other))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'unavailable')
        self.assertFalse(self.marker.exists())


if __name__ == '__main__':
    unittest.main()
