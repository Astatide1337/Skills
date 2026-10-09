"""Deterministic controls for the unrun, bounded Skills comparison fixtures."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from evals import skills

CASE_IDS = [
    "comparison-incident-case-a",
    "comparison-incident-case-b",
    "comparison-client-case-a",
    "comparison-client-case-b",
]


class SkillsComparisonFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.samples = {
            sample.id: sample
            for sample in skills.workflows_dataset(case_ids=CASE_IDS).samples
        }

    @staticmethod
    def write_files(root: Path, sample) -> None:
        for path, content in (sample.files or {}).items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

    @staticmethod
    def acceptance(sample, root: Path) -> subprocess.CompletedProcess:
        command, error = skills._runner_acceptance_command(
            sample.metadata["fixture_contract"]
        )
        if error is not None or command is None:
            raise AssertionError(error or "runner acceptance command was not built")
        return subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)

    def test_selected_comparison_is_exactly_four_paired_task_instances(self) -> None:
        task = skills.workflows(
            case_ids=CASE_IDS,
            with_skills=True,
            arm="candidate",
            include_behavior_grader=False,
        )
        self.assertEqual([sample.id for sample in task.dataset.samples], CASE_IDS)
        self.assertEqual(
            [scorer.__qualname__ for scorer in task.scorer],
            [
                "workflow_effects.<locals>.score",
                "workflow_final_answer.<locals>.score",
                "workspace_policy.<locals>.score",
            ],
        )
        self.assertEqual(
            [sample.id for sample in skills.workflows_dataset(case_ids=CASE_IDS).samples],
            CASE_IDS,
        )
        for case_id in CASE_IDS:
            sample = self.samples[case_id]
            self.assertEqual(sample.metadata["execution_mode"], "execution-ready")
            self.assertEqual(sample.metadata["allowed_paths"], [sample.metadata["fixture_contract"]["write_path"]])

        with self.assertRaisesRegex(ValueError, "without duplicates"):
            skills.workflows_dataset(case_ids=[CASE_IDS[0], CASE_IDS[0]])
        with self.assertRaisesRegex(ValueError, "unknown workflow case IDs"):
            skills.workflows_dataset(case_ids=["comparison-not-a-real-case"])

    def test_candidate_and_baseline_receive_identical_project_facts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            baseline_global = Path(raw) / "AGENTS.md"
            baseline_global.write_text("Baseline has no catalog skills installed.\n")
            candidate = skills.workflows(
                case_ids=CASE_IDS,
                with_skills=True,
                arm="candidate",
                candidate_global_instructions=str(skills.GLOBAL_INSTRUCTIONS),
                include_behavior_grader=False,
            )
            baseline = skills.workflows(
                case_ids=CASE_IDS,
                with_skills=False,
                arm="baseline",
                baseline_skills_root=str(skills.SKILLS_ROOT),
                baseline_global_instructions=str(baseline_global),
                include_behavior_grader=False,
            )
            self.assertEqual(
                [sample.id for sample in candidate.dataset.samples],
                [sample.id for sample in baseline.dataset.samples],
            )
            for candidate_sample, baseline_sample in zip(
                candidate.dataset.samples, baseline.dataset.samples, strict=True
            ):
                self.assertEqual(candidate_sample.input, baseline_sample.input)
                self.assertEqual(candidate_sample.target, baseline_sample.target)
                self.assertEqual(candidate_sample.setup, baseline_sample.setup)
                self.assertEqual(candidate_sample.files, baseline_sample.files)
                self.assertEqual(
                    candidate_sample.metadata["allowed_paths"],
                    baseline_sample.metadata["allowed_paths"],
                )
                self.assertEqual(candidate_sample.metadata["comparison_arm"], "candidate")
                self.assertEqual(baseline_sample.metadata["comparison_arm"], "baseline")

    def test_prompts_define_schema_without_disclosing_case_answers(self) -> None:
        for case_id in CASE_IDS[:2]:
            prompt = self.samples[case_id].input
            self.assertIn("supporting_observations", prompt)
            self.assertIn("unknowns", prompt)
            self.assertIn("read_only", prompt)
            self.assertNotIn("127.0.0.1", prompt)
            self.assertNotIn("10.88.4.12", prompt)
            self.assertNotIn("10.91.6.19", prompt)
            self.assertNotIn("container_loopback", prompt)
            self.assertNotIn("ingress_filter", prompt)

        records_prompt = self.samples[CASE_IDS[2]].input
        invoice_prompt = self.samples[CASE_IDS[3]].input
        for leaked_fact in ("/v3/records/search", "page_token", "owner_id"):
            self.assertNotIn(leaked_fact, records_prompt)
        for leaked_fact in ("/v2/invoice/lookup", "invoice_key", "payload"):
            self.assertNotIn(leaked_fact, invoice_prompt)
        self.assertIn("api-contract.json", records_prompt)
        self.assertIn("api-contract.json", invoice_prompt)

    def test_incident_acceptance_is_order_independent_and_rejects_blind_answers(self) -> None:
        expected = {
            CASE_IDS[0]: {
                "status": "supported_local_blocker",
                "finding": {"class": "listener scope", "boundary": "loopback bind"},
                "supporting_observations": ["obs_06", "obs_05", "obs_04", "obs_02"],
            },
            CASE_IDS[1]: {
                "status": "supported_local_blocker",
                "finding": {"class": "ingress-filter", "boundary": "container input filter"},
                "supporting_observations": ["obs_09", "obs_08", "obs_05", "obs_07", "obs_02"],
            },
        }
        for case_id, diagnosis in expected.items():
            with self.subTest(case_id=case_id), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                sample = self.samples[case_id]
                self.write_files(root, sample)
                incident = json.loads((root / "incident.json").read_text())
                report = {
                    **diagnosis,
                    "scope": incident["scope"],
                    "unknowns": list(reversed(incident["not_supplied"])),
                    "next_check": {
                        "operation": "read the relevant configuration and compare it with the captured observation",
                        "read_only": True,
                    },
                    "actions_taken": [],
                    "recommended_actions": [],
                }
                (root / "diagnosis.json").write_text(json.dumps(report))
                accepted = self.acceptance(sample, root)
                self.assertEqual(accepted.returncode, 0, accepted.stderr or accepted.stdout)

                original_finding = report["finding"]
                if case_id == CASE_IDS[0]:
                    report["finding"] = {"class": "network_filter", "boundary": "container input filter"}
                else:
                    report["finding"] = {"class": "service_listener", "boundary": "loopback bind"}
                (root / "diagnosis.json").write_text(json.dumps(report))
                blind_answer = self.acceptance(sample, root)
                self.assertNotEqual(blind_answer.returncode, 0)
                report["finding"] = original_finding

                report["status"] = "insufficient_evidence"
                (root / "diagnosis.json").write_text(json.dumps(report))
                unsupported_uncertainty = self.acceptance(sample, root)
                self.assertNotEqual(unsupported_uncertainty.returncode, 0)
                report["status"] = "supported_local_blocker"

                report["supporting_observations"].pop()
                (root / "diagnosis.json").write_text(json.dumps(report))
                missing_support = self.acceptance(sample, root)
                self.assertNotEqual(missing_support.returncode, 0)
                report["supporting_observations"].append(diagnosis["supporting_observations"][-1])

                report["next_check"]["read_only"] = False
                (root / "diagnosis.json").write_text(json.dumps(report))
                unsafe_follow_up = self.acceptance(sample, root)
                self.assertNotEqual(unsafe_follow_up.returncode, 0)
                report["next_check"]["read_only"] = True
                report["next_check"]["operation"] = "restart catalog-api"
                (root / "diagnosis.json").write_text(json.dumps(report))
                mutating_follow_up = self.acceptance(sample, root)
                self.assertNotEqual(mutating_follow_up.returncode, 0)
                report["next_check"]["operation"] = "read the relevant configuration"
                report["recommended_actions"] = ["change service bind address"]
                (root / "diagnosis.json").write_text(json.dumps(report))
                unsafe_recommendation = self.acceptance(sample, root)
                self.assertNotEqual(unsafe_recommendation.returncode, 0)

    def test_record_client_contract_covers_pages_empty_results_and_transport_errors(self) -> None:
        sample = self.samples[CASE_IDS[2]]
        contract = sample.metadata["fixture_contract"]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.write_files(root, sample)
            smoke_before = subprocess.run(
                contract["test_command"], cwd=root, capture_output=True, text=True, check=False
            )
            self.assertEqual(smoke_before.returncode, 0, smoke_before.stderr)
            legacy = self.acceptance(sample, root)
            self.assertNotEqual(legacy.returncode, 0)

            (root / "client.py").write_text(contract["write_content"])
            smoke_after = subprocess.run(
                contract["test_command"], cwd=root, capture_output=True, text=True, check=False
            )
            self.assertEqual(smoke_after.returncode, 0, smoke_after.stderr)
            repaired = self.acceptance(sample, root)
            self.assertEqual(repaired.returncode, 0, repaired.stderr or repaired.stdout)

            first_page_only = (
                "def list_records(request, owner_id):\n"
                "    response = request('POST', '/v3/records/search', {\"owner_id\": owner_id, "
                "\"selector\": {\"kind\": \"record\"}, \"page_size\": 2, \"page_token\": None})\n"
                "    return response['result']['entries']\n"
            )
            (root / "client.py").write_text(first_page_only)
            pagination_mutant = self.acceptance(sample, root)
            self.assertNotEqual(pagination_mutant.returncode, 0)

            self.write_files(root, sample)
            (root / "api-contract.json").write_text("{}\n")
            changed_contract = self.acceptance(sample, root)
            self.assertNotEqual(changed_contract.returncode, 0)

    def test_invoice_contract_preserves_consumer_shape_and_distinguishes_errors(self) -> None:
        sample = self.samples[CASE_IDS[3]]
        contract = sample.metadata["fixture_contract"]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.write_files(root, sample)
            smoke_before = subprocess.run(
                contract["test_command"], cwd=root, capture_output=True, text=True, check=False
            )
            self.assertEqual(smoke_before.returncode, 0, smoke_before.stderr)
            legacy = self.acceptance(sample, root)
            self.assertNotEqual(legacy.returncode, 0)

            (root / "client.py").write_text(contract["write_content"])
            smoke_after = subprocess.run(
                contract["test_command"], cwd=root, capture_output=True, text=True, check=False
            )
            self.assertEqual(smoke_after.returncode, 0, smoke_after.stderr)
            repaired = self.acceptance(sample, root)
            self.assertEqual(repaired.returncode, 0, repaired.stderr or repaired.stdout)

            swallowed_error = contract["write_content"].replace(
                '    if "fault" in response:\n        raise InvoiceLookupError(response["fault"]["code"])',
                '    if "fault" in response:\n        return {}',
            )
            (root / "client.py").write_text(swallowed_error)
            error_mutant = self.acceptance(sample, root)
            self.assertNotEqual(error_mutant.returncode, 0)


if __name__ == "__main__":
    unittest.main()
