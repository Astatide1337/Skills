"""Pedagogical-example consistency checks, not live-agent evaluations."""
from __future__ import annotations
import re
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "skills/verify-work/references/authorization-example.py"
SPEC = importlib.util.spec_from_file_location("authorization_example", EXAMPLE)
assert SPEC and SPEC.loader
example = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = example
SPEC.loader.exec_module(example)


class EngineeringExampleTests(unittest.TestCase):
    def test_two_different_valid_implementations_are_accepted(self):
        self.assertEqual(example.violations(example.centralized_edit), [])
        self.assertEqual(example.violations(example.policy_based_edit), [])

    def test_missing_tenant_check_is_rejected_for_the_right_reason(self):
        self.assertEqual(example.violations(example.happy_path_only), ["different-tenant"])

    def test_deny_everything_is_not_a_valid_security_fix(self):
        self.assertEqual(example.violations(example.deny_everything), ["owner"])

    def test_denial_after_mutation_is_rejected(self):
        def invalid(actor, document, label):
            document.label = label
            raise PermissionError("too late")
        failures = example.violations(invalid)
        self.assertIn("different-user", failures)
        self.assertIn("different-tenant", failures)
        self.assertIn("anonymous", failures)

    def test_claimed_success_without_persistence_is_rejected(self):
        self.assertIn("owner", example.violations(lambda actor, document, label: None))

    def test_readiness_does_not_hide_unexpected_exceptions(self):
        def broken(actor, document, label):
            raise RuntimeError("unavailable")
        self.assertEqual(len(example.violations(broken)), len(example.CASES))

    def test_example_entrypoint_runs_the_controls(self):
        result = subprocess.run([sys.executable, str(EXAMPLE)], capture_output=True,
                                text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("happy_path_only: rejected", result.stdout)
        self.assertIn("policy_based_edit: accepted", result.stdout)

    def test_existing_installer_copies_bundled_inputs_without_global_activation(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            global_skills = home / ".agents/skills"
            global_skills.mkdir(parents=True)
            sentinel = global_skills / "user-owned.txt"
            sentinel.write_text("preserve")
            target = home / "preview-skills"
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/install.sh"), "--all", "--target", str(target)],
                env={**os.environ, "HOME": str(home)}, capture_output=True, text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for relative in ("web-interface/references/composition-examples.md",
                             "web-interface/scripts/fetch_references.py",
                             "code-review-and-quality/references/generated-code-failures.md",
                             "verify-work/references/authorization-example.py",
                             "follow-instructions/references/engineering-judgment.md"):
                self.assertEqual((target / relative).read_bytes(),
                                 (ROOT / "skills" / relative).read_bytes())
            self.assertEqual(sentinel.read_text(), "preserve")
            self.assertEqual(list(global_skills.iterdir()), [sentinel])

    def test_sourced_references_have_resolvable_attributions_and_image_ids(self):
        base = ROOT / "skills/web-interface"
        content = (base / "references/composition-examples.md").read_text()
        definitions = dict(re.findall(r"^\[([^]]+)\]: (https://\S+)$", content, re.MULTILINE))
        image_ids = re.findall(r"!\[[^]]*\]\[([^]]+)\]", content)
        self.assertEqual(len(image_ids), 5)
        self.assertEqual(len(set(image_ids)), 5)
        for image_id in image_ids:
            self.assertIn(image_id, definitions)
        for source in ("source-apple", "source-stripe", "source-linear", "source-anthropic"):
            self.assertIn(source, definitions)
        self.assertFalse(list((base / "assets").glob("composition-*")))
        # This establishes reference wiring, not aesthetic quality or origin uptime.


if __name__ == "__main__":
    unittest.main()
