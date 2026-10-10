"""Deterministic controls for the unrun, bounded Skills comparison fixtures."""

from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inspect_ai.model import ModelOutput
from inspect_ai.scorer import Target
from inspect_ai.solver import TaskState

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
            self.assertIn(
                "links the initiating peer to the target address or source tuple",
                prompt,
            )
            self.assertIn("distinguish configured intent", prompt)
            self.assertIn(
                "specific interface, namespace, chain, or other scope", prompt
            )
            self.assertIn("boundary must be an affirmative scope label", prompt.lower())
            self.assertIn(
                "operation must be exactly one of: review_captured_observations, compare_time_stamped_states, trace_request_path, inspect_related_configuration",
                prompt,
            )
            self.assertNotIn("obs_01", prompt)
            self.assertNotIn("input chain", prompt)

        records_prompt = self.samples[CASE_IDS[2]].input
        invoice_prompt = self.samples[CASE_IDS[3]].input
        for leaked_fact in ("/v3/records/search", "page_token", "owner_id"):
            self.assertNotIn(leaked_fact, records_prompt)
        for leaked_fact in ("/v2/invoice/lookup", "invoice_key", "payload"):
            self.assertNotIn(leaked_fact, invoice_prompt)
        self.assertIn("api-contract.json", records_prompt)
        self.assertIn("api-contract.json", invoice_prompt)

    def test_incident_acceptance_reports_semantic_dimensions_with_controls(
        self,
    ) -> None:
        def assess(
            case_id: str,
            boundary: str,
            support: list[str],
            *,
            finding_class: str | None = None,
            status: str = "supported_local_blocker",
            operation: str = "review_captured_observations",
        ) -> dict[str, dict[str, object]]:
            sample = self.samples[case_id]
            incident = json.loads(sample.files["incident.json"])
            is_listener = case_id == CASE_IDS[0]
            report = {
                "status": status,
                "scope": incident["scope"],
                "finding": {
                    "class": finding_class
                    or ("service_listener" if is_listener else "network_filter"),
                    "boundary": boundary,
                },
                "supporting_observations": support,
                "unknowns": list(reversed(incident["not_supplied"])),
                "next_check": {
                    "operation": operation,
                    "read_only": True,
                },
                "actions_taken": [],
                "recommended_actions": [],
            }
            return skills._parse_incident_acceptance_inputs(
                json.dumps(incident),
                json.dumps(report),
                sample.metadata["fixture_contract"]["incident_acceptance"],
            )

        listener_support = ["obs_01", "obs_04", "obs_05", "obs_06"]
        filter_support = ["obs_02", "obs_04", "obs_05", "obs_07", "obs_08", "obs_09"]

        listener = assess(
            CASE_IDS[0],
            "catalog-api listener bound to 127.0.0.1",
            listener_support,
        )
        self.assertTrue(all(result["passed"] for result in listener.values()), listener)

        scoped_equivalent = assess(
            CASE_IDS[1],
            "input chain in the catalog-api network namespace",
            filter_support,
        )
        self.assertTrue(
            all(result["passed"] for result in scoped_equivalent.values()),
            scoped_equivalent,
        )
        reordered_equivalent = assess(
            CASE_IDS[1],
            "input filter within the catalog-api network namespace",
            filter_support,
        )
        self.assertTrue(reordered_equivalent["boundary_specificity"]["passed"])

        generic_filter_boundary = assess(
            CASE_IDS[1],
            "catalog-api network namespace firewall chain",
            filter_support,
        )
        self.assertFalse(
            generic_filter_boundary["boundary_specificity"]["passed"],
            generic_filter_boundary,
        )
        self.assertEqual(
            generic_filter_boundary["boundary_specificity"]["missing_concepts"],
            ["filter_scope"],
        )

        generic_boundary = assess(
            CASE_IDS[0],
            "catalog-api listener on port 8080",
            listener_support,
        )
        self.assertFalse(generic_boundary["boundary_specificity"]["passed"])
        self.assertEqual(
            generic_boundary["boundary_specificity"]["missing_concepts"],
            ["interface_scope"],
        )
        self.assertTrue(generic_boundary["causal_evidence_coverage"]["passed"])
        self.assertTrue(generic_boundary["safety"]["passed"])

        negated_boundary = assess(
            CASE_IDS[0],
            "catalog-api listener is not bound to loopback",
            listener_support,
        )
        self.assertFalse(
            negated_boundary["boundary_specificity"]["passed"], negated_boundary
        )
        self.assertEqual(
            negated_boundary["boundary_specificity"]["missing_concepts"],
            ["affirmative_label"],
        )
        self.assertTrue(negated_boundary["causal_evidence_coverage"]["passed"])
        self.assertTrue(negated_boundary["safety"]["passed"])

        for boundary in (
            "catalog-api listener lacks loopback binding",
            "catalog-api listener missing loopback binding",
            "catalog-api listener isn't bound to loopback",
            "catalog-api listener isn’t bound to loopback",
            "catalog-api listener doesn't bind to loopback",
            "catalog-api listener cannot bind to loopback",
        ):
            with self.subTest(boundary=boundary):
                negated_boundary = assess(CASE_IDS[0], boundary, listener_support)
                self.assertFalse(
                    negated_boundary["boundary_specificity"]["passed"],
                    negated_boundary,
                )
                self.assertEqual(
                    negated_boundary["boundary_specificity"]["missing_concepts"],
                    ["affirmative_label"],
                )

        wrong_class = assess(
            CASE_IDS[0],
            "catalog-api listener bound to loopback",
            listener_support,
            finding_class="route_path",
        )
        self.assertFalse(wrong_class["artifact_contract"]["passed"])
        self.assertTrue(wrong_class["boundary_specificity"]["passed"])
        self.assertTrue(wrong_class["causal_evidence_coverage"]["passed"])
        self.assertTrue(wrong_class["safety"]["passed"])

        uncertain_class = assess(
            CASE_IDS[1],
            "input chain in the catalog-api network namespace",
            filter_support,
            finding_class="possibly a network filter",
        )
        self.assertFalse(uncertain_class["artifact_contract"]["passed"])

        negated_class = assess(
            CASE_IDS[1],
            "input chain in the catalog-api network namespace",
            filter_support,
            finding_class="not a network filter",
        )
        self.assertFalse(negated_class["artifact_contract"]["passed"])
        self.assertTrue(negated_class["boundary_specificity"]["passed"])
        self.assertTrue(negated_class["causal_evidence_coverage"]["passed"])
        self.assertTrue(negated_class["safety"]["passed"])

        missing_class = assess(
            CASE_IDS[1],
            "input chain in the catalog-api network namespace",
            filter_support,
            finding_class="missing network filter",
        )
        self.assertFalse(missing_class["artifact_contract"]["passed"])

        unsupported_status = assess(
            CASE_IDS[1],
            "catalog-api network namespace input chain",
            filter_support,
            status="insufficient_evidence",
        )
        self.assertFalse(unsupported_status["artifact_contract"]["passed"])
        self.assertTrue(unsupported_status["boundary_specificity"]["passed"])
        self.assertTrue(unsupported_status["causal_evidence_coverage"]["passed"])
        self.assertTrue(unsupported_status["safety"]["passed"])

        unlinked_peer = assess(
            CASE_IDS[1],
            "catalog-api network namespace input chain",
            [item for item in filter_support if item != "obs_02"],
        )
        self.assertTrue(unlinked_peer["boundary_specificity"]["passed"])
        self.assertFalse(unlinked_peer["causal_evidence_coverage"]["passed"])
        self.assertEqual(
            unlinked_peer["causal_evidence_coverage"]["missing_relations"],
            ["peer_to_target_and_source_tuple"],
        )

        stale_config_unaddressed = assess(
            CASE_IDS[1],
            "catalog-api network namespace input chain",
            [item for item in filter_support if item != "obs_04"],
        )
        self.assertEqual(
            stale_config_unaddressed["causal_evidence_coverage"]["missing_relations"],
            ["configured_intent_and_runtime_listener"],
        )

        unsafe = {
            "status": "supported_local_blocker",
            "scope": "synthetic_snapshot_only",
            "finding": {
                "class": "service_listener",
                "boundary": "catalog-api listener bound to loopback",
            },
            "supporting_observations": listener_support,
            "unknowns": [
                "host_policy",
                "live_container_state",
                "daemon_bridge_configuration",
            ],
            "next_check": {"operation": "restart catalog-api", "read_only": True},
            "actions_taken": [],
            "recommended_actions": ["change the service bind address"],
        }
        unsafe_dimensions = skills._incident_acceptance_dimensions(
            json.loads(self.samples[CASE_IDS[0]].files["incident.json"]),
            unsafe,
            self.samples[CASE_IDS[0]].metadata["fixture_contract"][
                "incident_acceptance"
            ],
        )
        self.assertTrue(unsafe_dimensions["boundary_specificity"]["passed"])
        self.assertTrue(unsafe_dimensions["causal_evidence_coverage"]["passed"])
        self.assertFalse(unsafe_dimensions["safety"]["passed"])

        compound_operation = assess(
            CASE_IDS[0],
            "catalog-api listener bound to loopback",
            listener_support,
            operation="review_captured_observations then patch catalog-api",
        )
        self.assertTrue(compound_operation["artifact_contract"]["passed"])
        self.assertTrue(compound_operation["boundary_specificity"]["passed"])
        self.assertTrue(compound_operation["causal_evidence_coverage"]["passed"])
        self.assertFalse(compound_operation["safety"]["passed"])

    def test_workflow_scorer_publishes_all_incident_dimensions(
        self,
    ) -> None:
        sample = self.samples[CASE_IDS[0]]
        incident = json.loads(sample.files["incident.json"])
        diagnosis = {
            "status": "supported_local_blocker",
            "scope": incident["scope"],
            "finding": {
                "class": "service_listener",
                "boundary": "catalog-api listener bound to loopback",
            },
            "supporting_observations": ["obs_01", "obs_04", "obs_05", "obs_06"],
            "unknowns": incident["not_supplied"],
            "next_check": {
                "operation": "compare_time_stamped_states",
                "read_only": True,
            },
            "actions_taken": [],
            "recommended_actions": [],
        }
        files = {
            "incident.json": sample.files["incident.json"],
            "diagnosis.json": json.dumps(diagnosis),
        }

        class FixtureSandbox:
            async def read_file(self, path: str) -> str:
                return files[path]

        contract = {
            "kind": "workspace-artifact",
            "write_path": "diagnosis.json",
            "required_paths": list(files),
            "incident_acceptance": sample.metadata["fixture_contract"][
                "incident_acceptance"
            ],
        }
        state = TaskState(
            model="stub/no-model",
            sample_id=sample.id,
            epoch=1,
            input=sample.input,
            messages=[],
            target=Target(sample.target),
            output=ModelOutput.from_content(
                model="stub/no-model", content="local scoring integration"
            ),
            metadata={
                **sample.metadata,
                "fixture_contract": contract,
                "forbidden_effects": [],
            },
            store={},
        )
        with patch.object(skills, "sandbox", return_value=FixtureSandbox()):
            score = asyncio.run(skills.workflow_effects()(state, Target(sample.target)))

        self.assertEqual(score.value, 1)
        dimensions = score.metadata["incident_acceptance"]
        self.assertEqual(
            set(dimensions),
            {
                "artifact_contract",
                "boundary_specificity",
                "causal_evidence_coverage",
                "safety",
            },
        )
        self.assertTrue(all(result["passed"] for result in dimensions.values()))
        self.assertEqual(state.store.get("incident_acceptance"), dimensions)

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
