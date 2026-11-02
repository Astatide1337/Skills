"""Subprocess protocol tests; the fixture is not a general intent classifier."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

GATE = Path(__file__).resolve().parents[2] / 'global-instructions/hooks/agent_gates.py'


class ChoiceGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.checker = self.root / 'checker.py'
        # Runtime-owned state stands for the actual unanswered format question.
        # Paths/actions are explicit fixture contracts, not shell heuristics.
        self.checker.write_text('''import json, sys
from pathlib import Path
p = json.load(sys.stdin)
authority = json.loads(Path('authority.json').read_text())
action = p['tool_input']
if p['tool_name'] == 'Read' or action.get('file_path') == 'independent.txt':
    status = 'allow'
elif p['tool_name'] == 'Write' and action.get('file_path') == 'public-format.toml':
    status = 'allow' if authority['format'] == 'toml' else 'block'
else:
    status = 'unavailable'
print(json.dumps({'status': status, 'reason': 'Explicit format dependency contract'}))
''')
        self.authority(None)

    def authority(self, answer):
        (self.root / 'authority.json').write_text(json.dumps({'format': answer}))

    def hook(self, tool='Write', path='public-format.toml', raw=None):
        event = {'hook_event_name': 'PreToolUse', 'session_id': 'owned',
                 'cwd': str(self.root), 'tool_name': tool, 'tool_input': {'file_path': path}}
        return subprocess.run(
            [sys.executable, str(GATE), 'choice-guard', sys.executable, str(self.checker)],
            input=json.dumps(event) if raw is None else raw,
            capture_output=True, text=True, timeout=5,
            env={**os.environ, 'AGENT_VERIFY_TIMEOUT': '1'}, check=False)

    def test_unanswered_choice_blocks_actual_dependent_write(self):
        result = self.hook()
        # Simulate the host dispatch boundary, not merely the checker's output.
        if result.returncode == 0:
            (self.root / 'public-format.toml').write_text('dependent bytes')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse((self.root / 'public-format.toml').exists())
        self.assertIn('block', result.stderr)

    def test_reads_and_independent_work_continue(self):
        for tool, path in [('Read', 'public-format.toml'), ('Write', 'independent.txt')]:
            with self.subTest(tool=tool):
                self.assertEqual(self.hook(tool, path).returncode, 0)

    def test_settled_or_later_authorized_choice_allows(self):
        self.assertEqual(self.hook().returncode, 2)
        self.authority('toml')
        self.assertEqual(self.hook().returncode, 0)
        self.authority('json')
        self.assertEqual(self.hook().returncode, 2)

    def test_unknown_action_is_unavailable_not_authorized(self):
        result = self.hook('Bash', 'unknown')
        self.assertEqual(result.returncode, 2)
        self.assertIn('unavailable', result.stderr)

    def test_protocol_errors_never_allow_action(self):
        for code in ['print("not json")', 'print(\'{"status":"allow"}\')',
                     'raise RuntimeError("failure")',
                     'import time; time.sleep(3)']:
            with self.subTest(code=code):
                self.checker.write_text(code)
                result = self.hook()
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('unavailable', result.stderr)

    def test_malformed_event_does_not_invoke_checker(self):
        self.checker.write_text('from pathlib import Path; Path("ran").touch()')
        self.assertEqual(self.hook(raw='null').returncode, 2)
        self.assertEqual(self.hook(raw='{').returncode, 2)
        self.assertFalse((self.root / 'ran').exists())

    def test_missing_checker_blocks_instead_of_nonblocking_usage_error(self):
        result = subprocess.run(
            [sys.executable, str(GATE), 'choice-guard'],
            input='{}', capture_output=True, text=True, check=False, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn('missing trusted choice checker', result.stderr)
