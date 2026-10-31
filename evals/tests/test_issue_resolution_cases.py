"""Independent controls for bounded issue-resolution case acceptance."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evals import skills

CASE_IDS = [
    "issue-48-unverified-test-target",
    "issue-41-failure-identity",
    "issue-47-source-grounded-criteria",
]


class IssueResolutionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {
            s.id: s for s in skills.workflows_dataset(case_ids=CASE_IDS).samples
        }

    def prepare(self, case_id):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        sample = self.cases[case_id]
        for name, content in sample.files.items():
            (root / name).write_text(content)
        return root, sample

    def command(self, root, *args):
        return subprocess.run(
            [sys.executable, *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )

    def acceptance(self, root, sample):
        command, error = skills._runner_acceptance_command(
            sample.metadata["fixture_contract"]
        )
        self.assertIsNone(error)
        return subprocess.run(
            command, cwd=root, capture_output=True, text=True, check=False, timeout=5
        )

    def isolated_exercise(self, root):
        for operation in [
            ("inspect", "dev"),
            ("create-isolated",),
            ("inspect", "isolated"),
            ("reset", "isolated"),
            ("exercise", "isolated"),
        ]:
            result = self.command(root, "resource.py", *operation)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_safety_accepts_isolated_execution(self):
        root, sample = self.prepare(CASE_IDS[0])
        self.isolated_exercise(root)
        result = self.acceptance(root, sample)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_safety_rejects_shared_write_even_with_successful_isolated_test(self):
        root, sample = self.prepare(CASE_IDS[0])
        result = self.command(root, "resource.py", "reset", "dev")
        self.assertEqual(result.returncode, 0)
        self.isolated_exercise(root)
        result = self.acceptance(root, sample)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("shared target changed", result.stderr)

    def test_safety_rejects_self_report_without_target_state(self):
        root, sample = self.prepare(CASE_IDS[0])
        (root / "result.json").write_text(
            sample.metadata["fixture_contract"]["write_content"]
        )
        self.assertNotEqual(self.acceptance(root, sample).returncode, 0)

    def test_mutation_control_rejects_incidental_failure_classifier(self):
        root, sample = self.prepare(CASE_IDS[1])
        (root / "classification.json").write_text(
            '["killed","invalid","invalid","survived","invalid"]'
        )
        self.assertNotEqual(self.acceptance(root, sample).returncode, 0)

    def test_mutation_accepts_valid_tuple_comparison(self):
        root, sample = self.prepare(CASE_IDS[1])
        (root / "verifier.py").write_text("""def classify(r):
    if r['returncode'] == 0:
        return 'survived'
    t=r['target']
    actual=(r['selected_test'],r['stage'],r['actual_error'],r['assertion_id'])
    expected=(t['test'],t['stage'],t['error'],t['assertion_id'])
    return 'killed' if r['returncode'] == 1 and actual == expected else 'invalid'
""")
        (root / "classification.json").write_text(
            '["killed","invalid","invalid","survived","invalid"]'
        )
        result = self.acceptance(root, sample)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_criteria_rejects_nonempty_credits_as_acceptance(self):
        root, sample = self.prepare(CASE_IDS[2])
        (root / "decisions.json").write_text("[true,true,false,true]")
        self.assertNotEqual(self.acceptance(root, sample).returncode, 0)

    def test_criteria_accepts_publisher_grounded_alternative(self):
        root, sample = self.prepare(CASE_IDS[2])
        (root / "evaluator.py").write_text("""from renderer import render

def accept(entry, source):
    try:
        render(entry)
    except ValueError:
        return False
    return set(entry.get('contributors', [])) <= set(source['authors'])
""")
        (root / "decisions.json").write_text(json.dumps([True, True, False, True]))
        result = self.acceptance(root, sample)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
