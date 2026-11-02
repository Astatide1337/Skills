"""Exercise the hook process and independent checker, not assistant wording."""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
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

    def test_missing_checker_command_requests_recovery_not_usage_failure(self):
        result = subprocess.run(
            [sys.executable, str(GATE), 'completion'],
            input=json.dumps({'hook_event_name': 'Stop', 'session_id': 'owned',
                              'cwd': str(self.root), 'stop_hook_active': False}),
            capture_output=True, text=True, env=self.env, timeout=5, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        body = json.loads(result.stdout)
        self.assertEqual(body['decision'], 'block')
        self.assertIn('missing trusted acceptance checker', body['reason'])

    def test_checker_receives_event_context_but_derives_acceptance_from_artifact(self):
        self.checker.write_text('''import json, sys
from pathlib import Path
event = json.load(sys.stdin)
assert event['session_id'] == 'owned'
assert event['hook_event_name'] == 'Stop'
artifact = Path('report.txt')
ok = artifact.is_file() and artifact.read_text() == 'accepted\\n'
print(json.dumps({'status': 'complete' if ok else 'incomplete',
                  'reason': 'Observed report bytes, not event claims'}))
''')
        self.assertEqual(self.hook(status='complete')['decision'], 'block')
        (self.root / 'report.txt').write_text('accepted\n')
        self.assertEqual(self.hook(active=True), {})

    def test_changed_candidate_invalidates_separately_returned_review(self):
        self.checker.write_text('''import hashlib, json
from pathlib import Path
artifact = Path('module.txt')
review = Path('review.json')
valid = artifact.is_file() and artifact.read_text() in ('valid-a', 'valid-b')
returned = json.loads(review.read_text()) if review.is_file() else {}
accepted = valid and returned.get('candidate') == hashlib.sha256(artifact.read_bytes()).hexdigest() and returned.get('verdict') == 'accepted'
print(json.dumps({'status': 'complete' if accepted else 'incomplete',
                  'reason': 'Actual supported artifact and returned review must match'}))
''')
        import hashlib
        artifact = self.root / 'module.txt'
        artifact.write_text('valid-a')
        self.assertEqual(self.hook(last_assistant_message='Review passed')['decision'], 'block')
        for value in ['valid-a', 'valid-b']:
            artifact.write_text(value)
            (self.root / 'review.json').write_text(json.dumps({
                'candidate': hashlib.sha256(artifact.read_bytes()).hexdigest(),
                'verdict': 'accepted'}))
            self.assertEqual(self.hook(active=True), {})
        artifact.write_text('invalid')
        self.assertEqual(self.hook()['decision'], 'block')
        artifact.write_text('valid-a')
        self.assertEqual(self.hook()['decision'], 'block')
        # Protocol fixture only: the host must separately protect review provenance.

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


class ParentAcceptanceTests(unittest.TestCase):
    setUp = CompletionHookTests.setUp
    result = CompletionHookTests.result
    hook = CompletionHookTests.hook

    def accept(self, context=None, raw=None, command=None):
        result = subprocess.run(
            [sys.executable, str(GATE), 'accept',
             *(command if command is not None else [sys.executable, str(self.checker)])],
            input=raw if raw is not None else json.dumps(context or {}),
            cwd=self.root, capture_output=True, text=True, env=self.env,
            timeout=5, check=False)
        return result.returncode, json.loads(result.stdout)

    def test_worker_completed_does_not_accept_missing_work(self):
        self.result('incomplete', 'Required additional regression has not passed.')
        code, body = self.accept({'status': 'completed', 'latestTerminalStatus': 'completed',
                                  'last_assistant_message': 'All checks passed.'})
        self.assertEqual(code, 1)
        self.assertEqual(body['status'], 'incomplete')

    def test_exhausted_stop_budget_cannot_release_parent_acceptance(self):
        self.result('incomplete')
        self.hook()
        self.hook(active=True)
        self.assertIn('unaccepted', self.hook(active=True)['systemMessage'])
        for _ in range(3):
            self.assertEqual(self.accept()[0], 1)

    def test_external_terminal_states_are_not_success(self):
        for status in ['blocked', 'waiting', 'cancelled']:
            self.result(status)
            code, body = self.accept()
            self.assertEqual(code, 1)
            self.assertEqual(body['status'], status)

    def test_unavailable_checker_never_returns_success(self):
        for code in ['print("not JSON")\n', 'raise RuntimeError("broken")\n',
                     'print(\'{"status":"complete"}\')\n',
                     'print(\'{"status":"complete","reason":"fake"}\'); raise SystemExit(1)\n']:
            self.checker.write_text(code)
            exit_code, body = self.accept()
            self.assertEqual(exit_code, 2)
            self.assertEqual(body['status'], 'unavailable')
        self.assertEqual(self.accept(command=[])[0], 2)

    def test_timeout_cannot_accept(self):
        self.checker.write_text('import time\ntime.sleep(20)\n')
        code, body = self.accept()
        self.assertEqual(code, 2)
        self.assertIn('timed out', body['reason'])

    def stubborn_checker(self):
        child = ("import signal,time\nfrom pathlib import Path\n"
                 "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                 "Path('ready').touch()\ntime.sleep(2)\n"
                 "Path('late-write').touch()\ntime.sleep(30)\n")
        self.checker.write_text(
            "import os,subprocess,sys,time\nfrom pathlib import Path\n"
            "Path('checker-group').write_text(str(os.getpid()))\n"
            f"subprocess.Popen([sys.executable, '-c', {child!r}], "
            "stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
            "time.sleep(30)\n")

        def cleanup():
            group = self.root / 'checker-group'
            if group.exists():
                try:
                    os.killpg(int(group.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        self.addCleanup(cleanup)

    def test_timeout_stops_descendant_after_group_leader_exits(self):
        self.stubborn_checker()
        code, body = self.accept()
        self.assertEqual(code, 2)
        self.assertIn('timed out', body['reason'])
        self.assertTrue((self.root / 'ready').exists())
        time.sleep(2.2)
        self.assertFalse((self.root / 'late-write').exists())

    def test_cancellation_stops_checker_and_descendant(self):
        self.stubborn_checker()
        process = subprocess.Popen(
            [sys.executable, str(GATE), 'accept', sys.executable, str(self.checker)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=self.root, text=True, env={**self.env, 'AGENT_VERIFY_TIMEOUT': '30'})
        self.addCleanup(lambda: process.poll() is None and process.kill())
        process.stdin.write('{}')
        process.stdin.close()
        process.stdin = None
        deadline = time.monotonic() + 5
        while not (self.root / 'ready').exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue((self.root / 'ready').exists())
        process.terminate()
        process.communicate(timeout=5)
        self.assertNotEqual(process.returncode, 0)
        time.sleep(2.2)
        self.assertFalse((self.root / 'late-write').exists())

    def test_invalid_context_cannot_run_checker(self):
        marker = self.root / 'executed'
        self.checker.write_text('from pathlib import Path\nPath("executed").touch()\n')
        for context in ['', 'broken', '[]', 'null', 'true']:
            self.assertEqual(self.accept(raw=context)[0], 2)
        self.assertFalse(marker.exists())

    def test_parent_cwd_controls_execution_and_payload_does_not_choose_command(self):
        self.checker.write_text('''import json, sys
from pathlib import Path
event = json.load(sys.stdin)
ok = Path('artifact').read_text() == 'valid'
print(json.dumps({'status': 'complete' if ok else 'incomplete', 'reason': 'Current artifact checked'}))
''')
        (self.root / 'artifact').write_text('valid')
        self.assertEqual(self.accept({'cwd': '/nonexistent', 'command': 'exit 1'})[0], 0)
        (self.root / 'artifact').write_text('invalid')
        self.assertEqual(self.accept({'status': 'complete'})[0], 1)

    def test_valid_alternatives_pass_and_changed_source_requires_fresh_checks(self):
        self.checker.write_text('''import json
from pathlib import Path
source = Path('implementation.py').read_text()
namespace = {}
exec(compile(source, 'implementation.py', 'exec'), namespace)
ok = [namespace['plural'](n) for n in (0, 1, 2, 99)] == ['items', 'item', 'items', 'items']
print(json.dumps({'status': 'complete' if ok else 'incomplete', 'reason': 'Required counts checked on current source'}))
''')
        artifact = self.root / 'implementation.py'
        for code in ['def plural(n):\n return "item" if n == 1 else "items"\n',
                     'def plural(n):\n return {1: "item"}.get(n, "items")\n']:
            artifact.write_text(code)
            self.assertEqual(self.accept()[0], 0)
        artifact.write_text('def plural(n):\n return "item"\n')
        self.assertEqual(self.accept()[0], 1)
        artifact.unlink()
        self.assertEqual(self.accept()[0], 2)


if __name__ == '__main__':
    unittest.main()
