"""Controls for synthetic selection decisions, not live model or T3 execution."""

from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from evals import skills


PREFIX = "workflow-native-agent-"
CASE_IDS = [PREFIX + suffix for suffix in (
    "generic-review", "named-unavailable", "role-reasoning",
    "explicit-effort", "worktree-candidate",
)]


class AgentSelectionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {
            s.id: s for s in skills.workflows_dataset(case_ids=CASE_IDS).samples
        }

    def prepare(self, suffix):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        sample = self.cases[PREFIX + suffix]
        for name, content in sample.files.items():
            (root / name).write_text(content)
        valid = json.loads(sample.metadata["fixture_contract"]["write_content"])
        return root, sample, valid

    def acceptance(self, root, sample, decision):
        (root / "decision.json").write_text(json.dumps(decision))
        command, error = skills._runner_acceptance_command(
            sample.metadata["fixture_contract"]
        )
        self.assertIsNone(error)
        return subprocess.run(
            command, cwd=root, capture_output=True, text=True,
            timeout=5, check=False,
        )

    def test_all_known_valid_decisions_pass(self):
        for case_id in CASE_IDS:
            with self.subTest(case=case_id):
                root, sample, valid = self.prepare(case_id.removeprefix(PREFIX))
                result = self.acceptance(root, sample, valid)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_generic_review_accepts_other_provider_and_both_option_formats(self):
        root, sample, valid = self.prepare("generic-review")
        valid["target"] = {
            "providerInstanceId": "fixture-judgment",
            "model": "judgment-worker",
            "options": {"effort": "high"},
        }
        self.assertEqual(self.acceptance(root, sample, valid).returncode, 0)
        valid["target"]["options"] = [{"id": "effort", "value": "high"}]
        self.assertEqual(self.acceptance(root, sample, valid).returncode, 0)

    def test_disabled_provider_and_unknown_model_are_rejected(self):
        root, sample, valid = self.prepare("generic-review")
        for replacement, message in [
            ({"providerInstanceId": "fixture-disabled", "model": "disabled-worker",
              "options": {"effort": "high"}}, "provider cannot run"),
            ({"providerInstanceId": "fixture-code", "model": "code-worker-high",
              "options": {"reasoningEffort": "high"}}, "model not advertised"),
        ]:
            with self.subTest(target=replacement):
                invalid = {**valid, "target": replacement}
                result = self.acceptance(root, sample, invalid)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_option_key_value_and_location_are_checked(self):
        root, sample, valid = self.prepare("role-reasoning")
        for options, message in [
            ({"effort": "high"}, "unsupported reasoning option key"),
            ({"reasoningEffort": "ultra"}, "unsupported reasoning value"),
            ({"reasoningEffort": "low"}, "insufficient requested reasoning"),
            ([{"id": "reasoningEffort", "value": "high"},
              {"id": "reasoningEffort", "value": "xhigh"}], "duplicate option"),
        ]:
            with self.subTest(options=options):
                invalid = copy.deepcopy(valid)
                invalid["target"]["options"] = options
                result = self.acceptance(root, sample, invalid)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
        invalid = copy.deepcopy(valid)
        invalid["effort"] = "high"
        self.assertIn("target.options", self.acceptance(root, sample, invalid).stderr)

    def test_hard_role_accepts_high_and_xhigh_not_one_model_ranking(self):
        root, sample, valid = self.prepare("role-reasoning")
        for effort in ["high", "xhigh"]:
            valid["target"] = {
                "providerInstanceId": "fixture-judgment",
                "model": "judgment-worker", "options": {"effort": effort},
            }
            result = self.acceptance(root, sample, valid)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_requested_unavailable_model_cannot_be_replaced(self):
        root, sample, valid = self.prepare("named-unavailable")
        valid["status"] = "ready"
        valid["target"] = {
            "providerInstanceId": "fixture-code", "model": "code-worker",
            "options": {"reasoningEffort": "high"},
        }
        result = self.acceptance(root, sample, valid)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("named model was substituted", result.stderr)

    def test_explicit_effort_cannot_be_raised(self):
        root, sample, valid = self.prepare("explicit-effort")
        valid["target"]["options"]["reasoningEffort"] = "high"
        result = self.acceptance(root, sample, valid)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit reasoning changed", result.stderr)

    def test_worktree_does_not_cover_dirty_delta_or_unreturned_review(self):
        root, sample, valid = self.prepare("worktree-candidate")
        for field in ["includes_working_delta", "review_ready"]:
            invalid = copy.deepcopy(valid)
            invalid["candidate"][field] = True
            result = self.acceptance(root, sample, invalid)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("dirty candidate falsely covered", result.stderr)
        valid["review_status"] = "complete"
        result = self.acceptance(root, sample, valid)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no returned review exists", result.stderr)

    def test_claimed_review_is_rejected_for_every_case(self):
        for case_id in CASE_IDS:
            with self.subTest(case=case_id):
                root, sample, valid = self.prepare(case_id.removeprefix(PREFIX))
                valid["review_status"] = "complete"
                result = self.acceptance(root, sample, valid)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("no returned review exists", result.stderr)

    def test_expected_decision_and_acceptance_are_not_candidate_inputs(self):
        for sample in self.cases.values():
            contract = sample.metadata["fixture_contract"]
            visible = sample.input + "\n" + "\n".join(sample.files.values())
            self.assertNotIn(contract["acceptance_test"], visible)
            self.assertNotIn(contract["write_content"], visible)
            self.assertEqual(sample.metadata["allowed_paths"], ["decision.json"])

    def test_editing_visible_capabilities_cannot_redefine_acceptance(self):
        root, sample, valid = self.prepare("generic-review")
        visible = json.loads((root / "capabilities.json").read_text())
        visible["providers"][-1]["canRunChildTask"] = True
        (root / "capabilities.json").write_text(json.dumps(visible))
        valid["target"] = {
            "providerInstanceId": "fixture-disabled", "model": "disabled-worker",
            "options": {"effort": "high"},
        }
        result = self.acceptance(root, sample, valid)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("provider cannot run", result.stderr)


if __name__ == "__main__":
    unittest.main()
