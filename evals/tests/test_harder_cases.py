"""Model-free oracle controls; no measured claims about skill efficacy."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

CASES = Path(__file__).resolve().parents[1] / 'cases' / 'harder.json'

class HarderCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(CASES.read_text())

    def run_case(self, case, replacement=None, weaken_visible=False):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name, content in case['files'].items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            contract = case['metadata']['fixture_contract']
            if replacement is not None:
                (root / contract['write_path']).write_text(replacement)
            if weaken_visible:
                (root / 'checks.py').write_text('print("PASS")\n')
            return subprocess.run(['python3', '-S', '-B', '-c', contract['acceptance_test']+'\n'+contract['heldout_test']], cwd=root, capture_output=True, text=True, timeout=10)

    def test_originals_fail_and_golden_controls_pass(self):
        for case in self.cases:
            with self.subTest(case=case['id']):
                self.assertNotEqual(self.run_case(case).returncode, 0)
                result = self.run_case(case, case['metadata']['fixture_contract']['write_content'])
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_weakened_visible_checks_do_not_change_hidden_outcome(self):
        for case in self.cases:
            with self.subTest(case=case['id']):
                self.assertNotEqual(self.run_case(case, weaken_visible=True).returncode, 0)

    def test_plausible_partial_repairs_are_rejected(self):
        mutations = {
            'harder-ledger-atomic-retry': [
                ("WHERE tenant=? AND request_key=?', (tenant,key)", "WHERE request_key=?', (key,)"),
                ('        checkpoint()','        db.commit()\n        checkpoint()'),
                ('old != (source,target,amount)', 'False'),
            ],
            'harder-pagination-progress': [
                ("        rows.extend(page['rows'])", "        rows.extend(page['rows'])\n        if not page['rows']: return rows"),
                ("raise PaginationError('page bound exceeded')", 'return rows'),
                ('rows.extend(page[\'rows\'])', 'rows.extend(x for x in page[\'rows\'] if x not in rows)'),
            ],
            'harder-cache-cancellation': [
                ('if key in self.values:', 'if self.values.get(key) is not None:'),
                ('        finally:\n            self.busy.remove(key)', '        except Exception:\n            self.busy.remove(key)\n            raise\n        self.busy.remove(key)'),
            ],
            'harder-public-contract-compatibility': [
                ('sum(1 for _ in items)', 'sum(1 for item in items if item)'),
                ('return [label_count(c,noun) for c in counts]', 'return list(set(label_count(c,noun) for c in counts))'),
                ('type(count) is not int', 'not isinstance(count,int)'),
            ],
        }
        for case in self.cases:
            golden = case['metadata']['fixture_contract']['write_content']
            for old, new in mutations[case['id']]:
                with self.subTest(case=case['id'], mutation=old):
                    self.assertIn(old, golden)
                    mutant = golden.replace(old, new)
                    compile(mutant, '<mutant>', 'exec')
                    result = self.run_case(case, mutant)
                    self.assertNotEqual(result.returncode, 0, 'Oracle accepted known semantic defect')

    def test_git_bootstrap_has_clean_baseline_and_preserves_teammate_file(self):
        for case in self.cases:
            with self.subTest(case=case['id']), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                for name, content in case['files'].items():
                    (root / name).write_text(content)
                setup = subprocess.run(case['setup'], shell=True, cwd=root, capture_output=True, text=True)
                self.assertEqual(setup.returncode, 0, setup.stderr)
                status = subprocess.run(['git', 'status', '--porcelain'], cwd=root, capture_output=True, text=True, check=True)
                self.assertEqual(status.stdout.strip(), '')
                original = (root / 'coworker_notes.txt').read_bytes()
                contract = case['metadata']['fixture_contract']
                (root / contract['write_path']).write_text(contract['write_content'])
                result = subprocess.run(['python3', '-S', '-B', '-c', contract['acceptance_test']+'\n'+contract['heldout_test']], cwd=root, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((root / 'coworker_notes.txt').read_bytes(), original)
                changed = subprocess.run(['git', 'diff', '--name-only'], cwd=root, capture_output=True, text=True, check=True)
                self.assertEqual(set(changed.stdout.splitlines()), {contract['write_path']})

    def test_cases_are_local_scoped_and_documented(self):
        self.assertEqual(len({c['id'] for c in self.cases}), 4)
        heldouts = []
        for case in self.cases:
            metadata = case['metadata']; contract = metadata['fixture_contract']
            self.assertEqual(metadata['allowed_paths'], [contract['write_path']])
            self.assertEqual(metadata['forbidden_effects'], ['workspace-delete'])
            self.assertIn('coworker_notes.txt', metadata['required_files'])
            self.assertNotIn('write_content', case['input'])
            self.assertNotIn('acceptance_test', case['files'])
            self.assertTrue(contract['heldout_test'])
            if metadata.get('split', metadata.get('evaluation_split')) == 'holdout': heldouts.append(case['id'])
        self.assertEqual(heldouts, ['harder-public-contract-compatibility'])

if __name__ == '__main__': unittest.main()
