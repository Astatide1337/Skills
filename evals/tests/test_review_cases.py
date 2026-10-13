"""Behavioral and counterfactual controls for calibrated review fixtures."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CASES = Path(__file__).resolve().parents[1] / 'cases' / 'reviews.json'


class ReviewCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(CASES.read_text())

    def materialize(self, root, case, replacements=None):
        for name, content in case['files'].items():
            (root / name).write_text(content)
        for name, content in (replacements or {}).items():
            (root / name).write_text(content)

    def probe(self, case, selector, replacements=None, regression=False):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.materialize(root, case, replacements)
            controls = case['metadata']['review_controls']
            (root / 'evidence.py').write_text(controls['public_regressions' if regression else 'gold_evidence'])
            return subprocess.run([sys.executable, '-S', '-B', '-m', 'unittest', 'evidence' + ('.' + selector if selector else '')],
                                  cwd=root, capture_output=True, text=True, timeout=2, check=False)

    def test_single_fixes_isolate_each_behavioral_defect(self):
        for case in self.cases:
            policy = case['metadata']['fixture_contract']['review_acceptance']
            findings = case['metadata']['review_controls']['gold_report']['findings']
            for defect, finding in zip(policy['defects'], findings):
                with self.subTest(case=case['id'], defect=defect['id']):
                    self.assertNotEqual(self.probe(case, finding['proof']).returncode, 0)
                    result = self.probe(case, finding['proof'], defect['fixes'])
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for other in findings:
                        if other != finding:
                            self.assertNotEqual(self.probe(case, other['proof'], defect['fixes']).returncode, 0)

    def test_all_fixed_and_clean_pass_contract_regressions(self):
        for case in self.cases:
            controls = case['metadata']['review_controls']
            result = self.probe(case, '', controls['all_fixed_sources'], regression=True)
            if result.returncode:
                self.fail(result.stderr)
            if not case['metadata']['fixture_contract']['review_acceptance']['defects']:
                result = self.probe(case, '', regression=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def classify(self, case, report, evidence=None):
        from evals.review_calibration import classify_review
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.materialize(root, case)
            (root / 'review.json').write_text(json.dumps(report))
            (root / 'evidence.py').write_text(evidence or case['metadata']['review_controls']['gold_evidence'])
            return classify_review(root, case['metadata']['fixture_contract']['review_acceptance'])

    def test_golden_reports_have_calibrated_counts(self):
        from evals.workspace_evidence import bwrap_preflight
        error = bwrap_preflight()
        if error:
            self.skipTest('proof containment unavailable: ' + error)
        for case in self.cases:
            result = self.classify(case, case['metadata']['review_controls']['gold_report'])
            count = len(case['metadata']['fixture_contract']['review_acceptance']['defects'])
            self.assertEqual(result['status'], 'valid', result)
            self.assertEqual(result['true_positives'], count, result)
            self.assertEqual(result['false_positives'], 0, result)
            self.assertEqual(result['duplicates'], 0, result)
            self.assertTrue(result['complete_review'], result)

    def test_wrong_duplicate_and_missing_proofs_do_not_complete_review(self):
        from evals.workspace_evidence import bwrap_preflight
        error = bwrap_preflight()
        if error:
            self.skipTest('proof containment unavailable: ' + error)
        case = self.cases[0]
        finding = case['metadata']['review_controls']['gold_report']['findings'][0]
        wrong = dict(finding, file='worker.py', line=1)
        result = self.classify(case, {'findings': [wrong]})
        self.assertEqual(result['false_positives'], 1, result)
        self.assertFalse(result['complete_review'])
        result = self.classify(case, {'findings': [finding, finding]})
        self.assertEqual(result['true_positives'], 1, result)
        self.assertEqual(result['duplicates'], 1, result)
        self.assertFalse(result['complete_review'])
        result = self.classify(case, {'findings': [finding]}, case['files']['evidence.py'])
        self.assertEqual(result['false_positives'], 1, result)
        self.assertFalse(result['complete_review'])
        no_proof = dict(finding)
        no_proof.pop('proof')
        result = self.classify(case, {'findings': [no_proof]})
        self.assertFalse(result['schema_valid'], result)
        self.assertFalse(result['complete_review'])
        clean = self.cases[1]
        result = self.classify(clean, {'findings': [finding]})
        self.assertEqual(result['false_positives'], 1, result)
        self.assertFalse(result['complete_review'])

    def test_hidden_ordinals_and_forged_summary_cannot_earn_credit(self):
        case = self.cases[0]
        report = case['metadata']['review_controls']['gold_report']
        probes = 'import unittest\nfrom pathlib import Path\nclass ReviewProof(unittest.TestCase):\n'
        for index, finding in enumerate(report['findings'], 1):
            name = finding['proof'].split('.')[1]
            probes += f' def {name}(self): self.assertEqual(Path.cwd().name, {str(index)!r})\n'
        result = self.classify(case, report, probes)
        self.assertEqual(result['true_positives'], 0, result)
        forged = ('import sys\nfrom pathlib import Path\n'
                  'good = "!= request.tenant" in Path("service.py").read_text()\n'
                  'print("Ran 1 test\\n" + ("OK" if good else "FAILED (failures=1)"))\n'
                  'sys.exit(0 if good else 1)\n')
        result = self.classify(case, {'findings': report['findings'][:1]}, forged)
        self.assertEqual(result['true_positives'], 0, result)
        self.assertFalse(result['complete_review'])

    def test_scope_split_and_hidden_controls(self):
        self.assertEqual(len(self.cases), 3)
        self.assertEqual([c['metadata']['split'] for c in self.cases], ['development', 'development', 'holdout'])
        self.assertEqual(len({c['input'] for c in self.cases}), 1)
        for case in self.cases:
            metadata = case['metadata']
            contract = metadata['fixture_contract']
            policy = contract['review_acceptance']
            self.assertEqual(contract['kind'], 'workspace-artifact')
            self.assertEqual(metadata['allowed_paths'], ['review.json', 'evidence.py'])
            self.assertEqual(metadata['forbidden_effects'], ['workspace-delete'])
            self.assertEqual(metadata['required_capabilities'], ['workspace-read', 'workspace-edit', 'test-run'])
            self.assertTrue(set(policy['source_paths']).issubset(contract['required_paths']))
            self.assertEqual(case['files']['review.json'], '{}\n')
            self.assertNotIn('gold_report', case['files'])
            for defect in policy['defects']:
                self.assertNotIn(defect['id'], case['input'])
                self.assertNotIn(defect['id'], ''.join(case['files'].values()))
                self.assertEqual(set(defect['fixes']), set(defect['files']))

    def test_git_setup_is_clean_and_only_artifacts_change(self):
        for case in self.cases:
            with self.subTest(case=case['id']), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                self.materialize(root, case)
                setup = subprocess.run(case['setup'], shell=True, cwd=root, capture_output=True, text=True, check=False)
                self.assertEqual(setup.returncode, 0, setup.stderr)
                def changed(root=root):
                    return subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True)
                self.assertEqual(changed(), '')
                controls = case['metadata']['review_controls']
                (root / 'review.json').write_text(json.dumps(controls['gold_report']))
                (root / 'evidence.py').write_text(controls['gold_evidence'])
                names = subprocess.check_output(['git', 'diff', '--name-only'], cwd=root, text=True)
                self.assertEqual(set(names.splitlines()), {'review.json', 'evidence.py'})


if __name__ == '__main__':
    unittest.main()
