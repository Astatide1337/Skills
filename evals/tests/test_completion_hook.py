"""Exercise the hook process and independent checker, not assistant wording."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).resolve().parents[2] / 'global-instructions/hooks/agent_gates.py'


class CompletionHookTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.checker = self.root / 'acceptance.py'
        self.env = {**os.environ, 'AGENT_GATES_STATE': str(self.root / 'state'),
                    'AGENT_VERIFY_TIMEOUT': '1'}

    def result(self, status, reason='Independent acceptance evidence'):
        self.checker.write_text('print(' + repr(json.dumps({'status': status, 'reason': reason})) + ')\n')

    def hook(self, active=False, event='Stop', **fields):
        body = {'session_id': 'owned', 'cwd': str(self.root),
                'hook_event_name': event, 'stop_hook_active': active, **fields}
        result = subprocess.run(
            [sys.executable, str(GATE), 'completion', sys.executable, str(self.checker)],
            input=json.dumps(body), capture_output=True, text=True, env=self.env,
            timeout=5, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_blocks_unfinished_parent_even_without_git_or_changes(self):
        self.result('incomplete', 'Required report is missing; create and check it.')
        result = self.hook(last_assistant_message='Everything is done.')
        self.assertEqual(result['decision'], 'block')
        self.assertIn('report is missing', result['reason'])

    def test_accepts_actual_artifact_after_continuation(self):
        self.checker.write_text("import json\nfrom pathlib import Path\n"
                                "ok=Path('report.txt').exists() and Path('report.txt').read_text()=='accepted\\n'\n"
                                "print(json.dumps({'status':'complete' if ok else 'incomplete','reason':'Expected report bytes'}))\n")
        self.assertEqual(self.hook()['decision'], 'block')
        (self.root / 'report.txt').write_text('accepted\n')
        self.assertEqual(self.hook(active=True), {})

    def test_legitimate_terminal_states_are_not_completion(self):
        for status in ['blocked', 'waiting', 'cancelled']:
            with self.subTest(status=status):
                self.result(status, 'Verified external dependency')
                result = self.hook()
                self.assertNotIn('decision', result)
                self.assertIn('Task not complete', result['systemMessage'])
                self.assertIn(status, result['systemMessage'])

    def test_interrupt_does_not_run_checker_or_prevent_cancellation(self):
        self.checker.write_text("raise RuntimeError('must not run')\n")
        self.assertEqual(self.hook(event='Interrupt'), {})

    def test_bad_checker_is_not_a_pass_and_does_not_loop_forever(self):
        for code in ['print("not JSON")\n', 'raise RuntimeError("instrument failure")\n',
                     'print(\'{"status":"complete"}\')\n']:
            self.checker.write_text(code)
            self.assertEqual(self.hook()['decision'], 'block')
            self.assertEqual(self.hook(active=True)['decision'], 'block')
            result = self.hook(active=True)
            self.assertNotIn('decision', result)
            self.assertIn('unaccepted', result['systemMessage'])

    def test_checker_timeout_reports_unavailable(self):
        self.checker.write_text('import time\ntime.sleep(20)\n')
        result = self.hook()
        self.assertEqual(result['decision'], 'block')
        self.assertIn('timed out', result['reason'])

    def test_new_user_turn_resets_budget_but_missing_state_does_not_loop(self):
        self.result('incomplete')
        result = self.hook(active=True)
        self.assertIn('state unavailable', result['systemMessage'])
        self.assertEqual(self.hook()['decision'], 'block')
        self.assertEqual(self.hook(active=True)['decision'], 'block')
        self.assertNotIn('decision', self.hook(active=True))
        self.assertEqual(self.hook()['decision'], 'block')

    def test_payload_cannot_choose_checker_or_claim_acceptance(self):
        self.result('incomplete')
        result = self.hook(command='echo complete', status='complete')
        self.assertEqual(result['decision'], 'block')

    def test_directory_change_preserves_same_checker_budget(self):
        self.result('incomplete')
        child = self.root / 'subdir'
        child.mkdir()
        self.assertEqual(self.hook()['decision'], 'block')
        self.assertEqual(self.hook(active=True, cwd=str(child))['decision'], 'block')
        self.assertNotIn('decision', self.hook(active=True))

    def test_corrupt_existing_state_never_resets_or_executes_checker(self):
        self.result('incomplete')
        self.hook()
        state = next((self.root / 'state').glob('owned-completion-*.json'))
        for content in ['{broken', '[]', '{"completion":{"key":true}}',
                        '{"completion":{"key":-1}}']:
            with self.subTest(content=content):
                state.write_text(content)
                self.checker.write_text("raise RuntimeError('must not execute')\n")
                for active in [False, True]:
                    result = self.hook(active=active)
                    self.assertNotIn('decision', result)
                    self.assertIn('This stop was not checked', result['systemMessage'])
                    self.assertNotIn('must not execute', result['systemMessage'])

    def test_legacy_hook_state_cannot_reset_completion_budget(self):
        self.result('incomplete')
        self.assertEqual(self.hook()['decision'], 'block')
        # Another concurrently registered hook may write its own session state.
        (self.root / 'state/owned.json').write_text('{"completion": {}}')
        self.assertEqual(self.hook(active=True)['decision'], 'block')
        (self.root / 'state/owned.json').write_text('{}')
        self.assertNotIn('decision', self.hook(active=True))


if __name__ == '__main__':
    unittest.main()
