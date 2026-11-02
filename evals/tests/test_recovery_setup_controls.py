"""Functional controls for bounded recovery choices; commands still need semantic review."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evals import skills


class RecoverySetupControls(unittest.TestCase):
    def exercise(self, case_id, *, correct=True, hardcode=False, setup=True):
        sample = skills.workflows_dataset(case_ids=[case_id]).samples[0]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name, content in sample.files.items():
                (root / name).write_text(content)
            if setup and "prepare_fields.py" in sample.files:
                subprocess.run([sys.executable, "-B", "prepare_fields.py"], cwd=root, check=True)
            if correct:
                code = sample.metadata["fixture_contract"]["write_content"]
                if hardcode:
                    code = code.replace("row[ACTIVE_FIELD]", "row['active']")
                (root / "export.py").write_text(code)
            command, error = skills._runner_acceptance_command(sample.metadata["fixture_contract"])
            self.assertIsNone(error)
            return subprocess.run(command, cwd=root, capture_output=True, text=True,
                                  check=False, timeout=5)

    def test_direct_path_correct_export_accepted(self):
        result = self.exercise("issue-39-direct-path-after-repeated-probe")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_helper_completion_without_export_rejected(self):
        result = self.exercise("issue-39-direct-path-after-repeated-probe", correct=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requested active filter incomplete", result.stderr)

    def test_necessary_generation_then_export_accepted(self):
        result = self.exercise("issue-39-necessary-local-setup")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_necessary_generation_rejected(self):
        result = self.exercise("issue-39-necessary-local-setup", setup=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("generated_field", result.stderr)

    def test_hardcoded_generated_field_rejected(self):
        result = self.exercise("issue-39-necessary-local-setup", hardcode=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("generated field interface bypassed", result.stderr)
