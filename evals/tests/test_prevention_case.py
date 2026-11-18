"""Calibrate the two-caller provenance fixture against alternate repairs."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evals.skills import _runner_acceptance_command


class PreventionFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cases = Path(__file__).resolve().parents[1] / "cases/skills-comparison.json"
        cls.case = next(case for case in json.loads(cases.read_text())
                        if case["id"] == "prevention-audit-entry")

    def evaluate(self, flows):
        command, error = _runner_acceptance_command(
            self.case["metadata"]["fixture_contract"], completion_marker="CHECKED")
        self.assertIsNone(error)
        with tempfile.TemporaryDirectory() as folder:
            for name, content in self.case["files"].items():
                (Path(folder) / name).write_text(flows if name == "flows.py" else content)
            result = subprocess.run([sys.executable, *command[1:]], cwd=folder,
                                    text=True, capture_output=True, timeout=5)
            return result.returncode == 0 and "CHECKED" in result.stdout.splitlines()

    def test_owning_boundary_and_compatible_alternatives(self):
        before = self.case["files"]["flows.py"]
        queue_fixed = before.replace('msg.get("origin", "worker")', '"worker"')
        both_fixed = queue_fixed.replace('msg.get("origin", "operator")', '"operator"')
        alternate = both_fixed.replace('append("worker", msg["text"])',
                                       'dict(text=msg["text"], origin="worker")')
        for label, candidate, accepted in [
            ("original", before, False), ("one caller", queue_fixed, False),
            ("trusted entry points", both_fixed, True), ("alternate representation", alternate, True),
            ("invented legacy origin", both_fixed.replace('row.get("origin")',
                                                          'row.get("origin", "operator")'), False),
        ]:
            with self.subTest(label=label):
                self.assertEqual(self.evaluate(candidate), accepted)
