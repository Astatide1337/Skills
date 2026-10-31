"""Calibrate format-case acceptance independently of candidate model output."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = {case['id']: case for case in json.loads(
    (ROOT / 'evals/cases/skills-comparison.json').read_text()
)}


class DeliveryContractControls(unittest.TestCase):
    def check_candidate(self, case_id, outputs, *, changed_source=False):
        case = CASES[case_id]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in case['files'].items():
                (root / name).write_text(content)
            for name, content in outputs.items():
                (root / name).write_text(content)
            if changed_source:
                (root / 'client.py').write_text('def fetch_status(*args): return None\n')
            # Execute the case's frozen acceptance, not a candidate-written check.
            return subprocess.run(
                [sys.executable, '-c', case['metadata']['fixture_contract']['acceptance_test']],
                cwd=root, capture_output=True, text=True, timeout=5, check=False,
            )

    def test_html_contract_accepts_distinct_valid_document(self):
        alternative = (
            '<!doctype html><html lang="fr"><head><title>Proposition</title>'
            '<meta name="viewport" content="width=device-width"></head>'
            '<body><main><h1>Approche</h1><section>Different valid organization.'
            '</section></main></body></html>'
        )
        result = self.check_candidate('workflow-native-contract-format-retained',
                                      {'plan.html': alternative})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_markdown_working_notes_do_not_satisfy_final_contract(self):
        result = self.check_candidate('workflow-native-contract-format-retained',
                                      {'report.md': '# Complete research\nUseful notes.'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FileNotFoundError', result.stderr)

    def test_extension_and_doctype_alone_are_insufficient(self):
        for content in ('# Plan\nMarkdown content.', '<!doctype html>'):
            with self.subTest(content=content):
                result = self.check_candidate('workflow-native-contract-format-retained',
                                              {'plan.html': content})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('AssertionError', result.stderr)

    def test_valid_artifact_does_not_excuse_unauthorized_implementation(self):
        contract = CASES['workflow-native-contract-format-retained']['metadata']['fixture_contract']
        result = self.check_candidate('workflow-native-contract-format-retained',
                                      {'plan.html': contract['write_content']}, changed_source=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('implementation changed during planning', result.stderr)

    def test_explicit_markdown_override_accepts_alternative_prose(self):
        result = self.check_candidate('workflow-native-contract-format-user-override',
                                      {'proposal.md': 'An alternative, concise plan in plain Markdown.'})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_markdown_comment_is_a_valid_alternative(self):
        result = self.check_candidate('workflow-native-contract-format-user-override', {
            'proposal.md': '<!-- Plan owner: CLI team -->\n# Retry plan\n\nUse bounded retries.',
        })
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_html_document_is_not_the_requested_markdown_plan(self):
        result = self.check_candidate('workflow-native-contract-format-user-override', {
            'proposal.md': '<!DOCTYPE HTML><html><body>A plan.</body></html>',
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requested Markdown plan missing', result.stderr)

    def test_html_default_cannot_override_explicit_markdown_request(self):
        result = self.check_candidate('workflow-native-contract-format-user-override',
                                      {'plan.html': '<!doctype html>'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FileNotFoundError', result.stderr)

    def test_extra_html_delivery_is_rejected_for_markdown_override(self):
        result = self.check_candidate('workflow-native-contract-format-user-override',
                                      {'proposal.md': 'A legitimate plan.', 'plan.html': '<!doctype html>'})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('explicit Markdown override ignored', result.stderr)


if __name__ == '__main__':
    unittest.main()
