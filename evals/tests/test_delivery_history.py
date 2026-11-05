import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / 'skills/follow-instructions/scripts/delivery-history.py'


def record(task='t1', **changes):
    value = {'schema_version': 1, 'repository': 'repo', 'task_id': task, 'task_type': 'implementation',
             'started_at': '2026-01-01T10:00:00Z', 'recorded_at': '2026-01-02T10:00:00Z',
             'status': 'delivered',
             'sources': [{'role': role, 'locator': f'https://example.com/{role}'}
                         for role in ('request', 'state', 'delivery', 'acceptance')],
             'observations': [], 'followup': {'state': 'unknown', 'as_of': None, 'sources': []}}
    value.update(changes)
    return value


class DeliveryHistory(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, value):
        (self.root / name).write_text(json.dumps(value), encoding='utf-8')

    def run_cli(self, command='validate', *args, optimize=False):
        env = dict(os.environ)
        if optimize:
            env['PYTHONOPTIMIZE'] = '1'
        return subprocess.run([sys.executable, str(SCRIPT), command, str(self.root), *args],
                              capture_output=True, text=True, env=env, check=False, timeout=5)

    def test_accepts_scopes_reopen_not_defect_and_unknown_followup(self):
        a = record(observations=[{'id': 'o1', 'category': 'reopened', 'assessment': 'not-defect',
                                  'claim': 'A later request reopened the work.',
                                  'sources': [{'role': 'claim', 'locator': '/evidence/reopen'}]}])
        a['status'] = 'interrupted'
        a['sources'] = a['sources'][:2]
        a['task_type'] = 'review'
        self.put('a.json', a)
        self.assertEqual(self.run_cli().returncode, 0)

    def test_observation_events_do_not_overcount_tasks(self):
        item = {'category': 'user-correction', 'assessment': 'defect', 'claim': 'Correction recorded.',
                'sources': [{'role': 'claim', 'locator': '/claim'}]}
        value = record(observations=[dict(item, id='1'), dict(item, id='2')])
        self.put('one.json', value)
        result = self.run_cli('summary')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        counts = data['groups'][0]['observations']['user-correction']
        self.assertEqual((counts['events'], counts['tasks_affected']), (2, 1))
        self.assertEqual(data['coverage'], 'unverified')
        self.assertIsNone(data['inventory']['matching'])
        self.assertEqual(data['groups'][0]['followup'], {'unknown': 1})

    def test_rejects_delivered_missing_evidence(self):
        value = record(sources=[{'role': 'request', 'locator': '/r'}, {'role': 'state', 'locator': '/s'}])
        self.put('bad.json', value)
        self.assertNotEqual(self.run_cli().returncode, 0)

    def test_rejects_unknown_fields_empty_entries_and_duplicate_pairs(self):
        value = record()
        value['surprise'] = True
        self.put('bad.json', value)
        self.assertNotEqual(self.run_cli().returncode, 0)
        (self.root / 'bad.json').unlink()
        self.put('a.json', record())
        self.put('b.json', record())
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate', result.stderr)

    def test_rejects_duplicate_observation_id(self):
        item = {'id': 'same', 'category': 'reopened', 'assessment': 'undetermined', 'claim': 'Reopened.',
                'sources': [{'role': 'claim', 'locator': '/claim'}]}
        self.put('x.json', record(observations=[item, item]))
        self.assertNotEqual(self.run_cli().returncode, 0)

    def test_inventory_reconciliation_validate_and_summary(self):
        self.put('a.json', record())
        inv = self.root.parent / (self.root.name + '-inventory.json')
        inv.write_text(json.dumps([{'repository': 'repo', 'task_id': 't1'},
                                   {'repository': 'repo', 'task_id': 'missing'}]))
        args = ('--inventory', str(inv))
        try:
            result = self.run_cli('summary', *args)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stdout)['inventory']
            self.assertEqual(report['missing'], [['repo', 'missing']])
            self.assertEqual(report['matching'], 1)
            self.assertEqual(report['status'], 'mismatch')
            self.assertNotEqual(self.run_cli('validate', *args).returncode, 0)
        finally:
            inv.unlink(missing_ok=True)

    def test_duplicate_json_keys_rejected_even_under_optimization(self):
        (self.root / 'dup.json').write_text('{"schema_version":1,"schema_version":1}')
        result = self.run_cli(optimize=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate JSON key', result.stderr)

    def test_malformed_types_fail_without_traceback(self):
        for field, value in [('status', []), ('schema_version', True), ('task_id', ''),
                             ('observations', {}), ('followup', [])]:
            with self.subTest(field=field):
                self.put('bad.json', record(**{field: value}))
                result = self.run_cli()
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('Traceback', result.stderr)
        for field in ('category', 'assessment'):
            item = {'id': 'x', 'category': 'reopened', 'assessment': 'undetermined',
                    'claim': 'Needs assessment', 'sources': [{'role': 'claim', 'locator': '/evidence'}]}
            item[field] = []
            self.put('bad.json', record(observations=[item]))
            result = self.run_cli()
            self.assertEqual(result.returncode, 1)
            self.assertNotIn('Traceback', result.stderr)

    def test_category_evidence_roles_and_valid_scope_change(self):
        for category, roles in [('unsupported-claim', ['claim', 'trace']),
                                ('escaped-defect', ['detection', 'prior-delivery']),
                                ('scope-change', ['decision']), ('review-caught', ['review'])]:
            item = {'id': 'x', 'category': category, 'assessment': 'not-defect',
                    'claim': 'A recorded assessment, not a computed verdict.',
                    'sources': [{'role': role, 'locator': '/evidence'} for role in roles]}
            self.put('a.json', record(observations=[item]))
            result = self.run_cli()
            self.assertEqual(result.returncode, 0, result.stderr)
            item['sources'] = [{'role': 'state', 'locator': '/unrelated'}]
            self.put('a.json', record(observations=[item]))
            result = self.run_cli()
            self.assertEqual(result.returncode, 1)
            self.assertIn('required sources missing', result.stderr)

    def test_followup_and_timestamps_need_observed_sources(self):
        observed = {'state': 'observed', 'as_of': '2026-01-02T10:00:00Z',
                    'sources': [{'role': 'state', 'locator': '/followup'}]}
        self.put('a.json', record(followup=observed))
        self.assertEqual(self.run_cli().returncode, 0)
        for followup in [dict(observed, sources=[]), dict(observed, state='unknown'),
                         dict(observed, as_of='2027-01-01T00:00:00Z')]:
            self.put('a.json', record(followup=followup))
            self.assertEqual(self.run_cli().returncode, 1)
        self.put('a.json', record(started_at='2026-01-01T10:00:00'))
        self.assertEqual(self.run_cli().returncode, 1)

    def test_unsafe_or_nonjson_inputs_are_rejected(self):
        target = self.root / 'a.json'
        for text in ['NaN', '{"value": Infinity}', '[]', '{}', '{']:
            target.write_text(text)
            self.assertEqual(self.run_cli().returncode, 1)
        target.write_text(' ' * 1_000_001)
        self.assertIn('size limit', self.run_cli().stderr)
        target.unlink()
        target.symlink_to('/missing')
        self.assertEqual(self.run_cli().returncode, 1)
        target.unlink()
        os.mkfifo(target)
        self.assertEqual(self.run_cli().returncode, 1)

    def test_bad_locators_and_roles_are_rejected(self):
        for locator in ['done', 'https://user:secret@example.com/x', 'https://bad host/x',
                        '/path\ncontrol']:
            self.put('a.json', record(sources=[{'role': 'request', 'locator': locator}]))
            self.assertEqual(self.run_cli().returncode, 1)
        self.put('a.json', record(sources=[{'role': [], 'locator': '/x'}]))
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('Traceback', result.stderr)

    def test_empty_history_is_not_evidence_of_success(self):
        result = self.run_cli('summary')
        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report['groups'], [])
        self.assertEqual(report['coverage'], 'unverified')
        self.assertEqual(report['inventory']['status'], 'not-supplied')

    def test_padded_identities_cannot_inflate_task_counts(self):
        for field in ('repository', 'task_id', 'task_type'):
            self.put('bad.json', record(**{field: ' padded '}))
            result = self.run_cli()
            self.assertEqual(result.returncode, 1)
            self.assertIn('surrounding whitespace', result.stderr)
        item = {'id': ' padded ', 'category': 'reopened', 'assessment': 'undetermined',
                'claim': 'Recorded event', 'sources': [{'role': 'claim', 'locator': '/evidence'}]}
        self.put('bad.json', record(observations=[item]))
        self.assertIn('surrounding whitespace', self.run_cli().stderr)
        self.put('bad.json', record())
        inventory = self.root.parent / (self.root.name + '-inventory.json')
        try:
            inventory.write_text(json.dumps([{'repository': 'repo', 'task_id': ' t1 '}]))
            result = self.run_cli('validate', '--inventory', str(inventory))
            self.assertEqual(result.returncode, 1)
            self.assertIn('surrounding whitespace', result.stderr)
        finally:
            inventory.unlink(missing_ok=True)

    def test_command_does_not_write_to_snapshot_directory(self):
        self.put('a.json', record())
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.assertEqual(self.run_cli('summary').returncode, 0)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)


if __name__ == '__main__':
    unittest.main()
