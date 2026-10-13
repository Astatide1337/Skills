"""Frozen behavioral oracle calibration, independent of candidate explanations."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

class AcceptedWorkTests(unittest.TestCase):
    def test_gold_original_and_incomplete_repairs(self):
        for case in json.loads((ROOT / 'evals/cases/accepted-work.json').read_text()):
            contract = case['metadata']['fixture_contract']
            variants = [None, contract['golden_files']]
            good_indices = {1}
            if case['id'] == 'accepted-policy-simplification':
                for alias in ['from policy import can as allowed\n', 'import policy\nallowed=policy.can\n']:
                    variants.append({**contract['golden_files'], 'api.py': alias})
                    good_indices.add(len(variants) - 1)
            for path, old, new in case['metadata']['calibration_mutants']:
                mutant = dict(contract['golden_files'])
                self.assertIn(old, mutant[path])
                mutant[path] = mutant[path].replace(old, new)
                variants.append(mutant)
            for index, replacements in enumerate(variants):
                with self.subTest(case=case['id'], variant=index), tempfile.TemporaryDirectory() as raw:
                    root = Path(raw)
                    for name, content in {**case['files'], **(replacements or {})}.items():
                        (root / name).write_text(content)
                    results = [subprocess.run([sys.executable, '-S', '-B', '-c', source],
                        cwd=root, capture_output=True, text=True, timeout=10, check=False)
                        for source in contract['acceptance_groups'].values()]
                    if index in good_indices:
                        self.assertTrue(all(r.returncode == 0 for r in results), [r.stderr for r in results])
                    else:
                        self.assertTrue(any(r.returncode != 0 for r in results), 'incomplete work accepted')

    def test_declared_split_and_shared_budget(self):
        from unittest.mock import patch

        from evals import skills
        plan = json.loads((ROOT / 'evals/accepted-work-plan.json').read_text())
        with patch.object(skills, '_validate_tool_runtime', return_value=Path('/owned/runtime')):
            for arm in plan['arms']:
                task = skills.accepted_workflows(native_model='frozen-model', native_effort='low',
                    tool_mode=arm, tool_runtime='/owned/runtime')
                self.assertEqual([s.id for s in task.dataset.samples], plan['cases']['development'])
                for sample in task.dataset.samples:
                    self.assertNotIn('golden_files', sample.input)
                    self.assertNotIn('calibration_mutants', sample.input)
                    self.assertEqual(sample.metadata['human_acceptance'], 'not observed')
                    self.assertIn('already approved', sample.input)
                    self.assertIn('keep source read-only', sample.input)
            with self.assertRaises(ValueError):
                skills.accepted_workflows(native_model='frozen-model', native_effort='low',
                    tool_mode='baseline', tool_runtime='/owned/runtime', case_ids=plan['cases']['holdout'])

if __name__ == '__main__':
    unittest.main()
