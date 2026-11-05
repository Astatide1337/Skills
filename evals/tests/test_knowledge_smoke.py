"""Smoke acceptance must survive optimization and reject plausible bad CLI output."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / 'skills/follow-instructions/scripts/knowledge-smoke.py'
FAKE = '''#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
cache = pathlib.Path(os.environ['CBM_CACHE_DIR'])
cache.mkdir(parents=True, exist_ok=True)
assert os.environ['CBM_RUNTIME_DIR'] != os.environ.get('UNRELATED_RUNTIME')
mode = os.environ.get('FAKE_MODE', 'good')
if args == ['--version']: print('fake 0.12.1')
elif args[:2] == ['config', 'set']: (cache / 'ui').write_text(args[-1])
elif args[:2] == ['config', 'get']: print((cache / 'ui').read_text())
elif args[:2] == ['cli', 'index_repository']:
    app = pathlib.Path('app.py')
    (cache / 'symbol').write_text('replacement_symbol' if app.exists() and 'replacement_symbol' in app.read_text() else 'retired_symbol' if app.exists() else '')
    print(json.dumps({'status': 'error' if mode == 'index-error' else 'indexed'}))
else:
    symbol = (cache / 'symbol').read_text()
    rows = [[symbol, 'app.py', '1', '2']] if symbol else []
    if mode != 'wiped' or symbol: rows.append(['surviving_symbol', 'sentinel.py', '1', '2'])
    columns = ['f.name', 'f.file_path', 'f.start_line', 'f.end_line']
    value = {'columns': columns, 'rows': rows}
    if mode == 'empty': value['rows'] = []
    if mode == 'bad-rows': value['rows'] = {'surviving_symbol': True}
    if mode == 'bad-columns': value['columns'] = ['wrong']
    if mode == 'array': value = []
    print(json.dumps(value))
'''


class KnowledgeSmokeTests(unittest.TestCase):
    def exercise(self, mode, optimized):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            binary = root / 'fake'
            binary.write_text(FAKE)
            binary.chmod(0o700)
            output = root / 'artifacts'
            result = subprocess.run([sys.executable, *(['-O'] if optimized else []),
                                     str(SCRIPT), '--binary', str(binary), '--output', str(output)],
                                    env=dict(os.environ, FAKE_MODE=mode, PYTHONOPTIMIZE='1' if optimized else '0'),
                                    capture_output=True, text=True, check=False)
            receipt = json.loads((output / 'receipt.json').read_text())
            if mode == 'good':
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('surviving-file', receipt['verified'])
                self.assertIn('ignored-wiki-direct-search', receipt['verified'])
            else:
                self.assertNotEqual(result.returncode, 0, (mode, result.stdout))
                messages = {'index-error': 'index failed', 'empty': 'sentinel disappeared',
                            'bad-rows': 'invalid rows', 'bad-columns': 'unexpected columns',
                            'array': 'expected JSON object', 'wiped': 'sentinel disappeared'}
                self.assertIn(messages[mode], result.stderr)
                self.assertNotIn('verified', receipt)

    def test_good_schema_with_and_without_optimization(self):
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                self.exercise('good', optimized)

    def test_hostile_success_exit_cannot_produce_verified_receipt(self):
        for mode in ('index-error', 'empty', 'bad-rows', 'bad-columns', 'array', 'wiped'):
            for optimized in (False, True):
                with self.subTest(mode=mode, optimized=optimized):
                    self.exercise(mode, optimized)
