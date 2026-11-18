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
            ("discarded legacy origin", both_fixed.replace('row.get("origin")',
                'row.get("origin") if row.get("origin") in ("worker", "operator") else None'), False),
            ("invented legacy origin", both_fixed.replace('row.get("origin")',
                                                          'row.get("origin", "operator")'), False),
        ]:
            with self.subTest(label=label):
                self.assertEqual(self.evaluate(candidate), accepted)


class ReleaseCheckContinuation(unittest.TestCase):
    def test_normal_release_gate_decides_the_outcome(self):
        cases = Path(__file__).resolve().parents[1] / "cases/skills-comparison.json"
        case = next(case for case in json.loads(cases.read_text())
                    if case["id"] == "prevention-resume-release-check")
        command, error = _runner_acceptance_command(
            case["metadata"]["fixture_contract"], completion_marker="CHECKED")
        self.assertIsNone(error)
        original = case["files"]["verify_release.py"]
        guard = "artifact.is_file() and "
        alternatives = [
            ("prose-only closure", original, False),
            ("reject every release", "raise SystemExit(1)", False),
            ("reject a single missing locale", original.replace(
                guard, 'name == "assets/locale.bin" and not artifact.is_file() or ' + guard), False),
            ("presence check loses checksum", original.replace(
                'artifact.is_file() and hashlib.sha256(artifact.read_bytes()).hexdigest() != expected',
                'not artifact.is_file()'), False),
            ("explicit missing-or-mismatch", original.replace(guard, "not artifact.is_file() or "), True),
            ("required read fails closed", original.replace(guard, ""), True),
        ]
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            for name, content in case["files"].items():
                (workspace / name).write_text(content)
            for label, source, accepted in alternatives:
                with self.subTest(label=label):
                    (workspace / "verify_release.py").write_text(source)
                    result = subprocess.run([sys.executable, *command[1:]], cwd=workspace,
                                            text=True, capture_output=True, timeout=10)
                    passed = result.returncode == 0 and "CHECKED" in result.stdout.splitlines()
                    self.assertEqual(passed, accepted, msg=result.stderr)
