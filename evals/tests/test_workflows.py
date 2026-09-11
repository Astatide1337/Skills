"""Deterministic contract checks for the task-playbook evaluation path."""

from __future__ import annotations

import json
import unittest

from inspect_ai.model import ModelOutput
from inspect_ai.solver import TaskState

from evals import skills
from evals.fake_tracker import validate_publication


class WorkflowContractTests(unittest.TestCase):
    def test_legacy_and_extended_schemas_preserve_provider_compatibility(self) -> None:
        legacy = json.loads(skills.LEGACY_ROUTE_SCHEMA.read_text())
        extended = json.loads(skills.ROUTE_SCHEMA.read_text())
        workflow = json.loads(skills.WORKFLOW_ROUTE_SCHEMA.read_text())
        self.assertEqual(legacy["required"], ["skills", "reason"])
        self.assertNotIn("workflow", legacy["properties"])
        self.assertIn("workflow", extended["properties"])
        self.assertNotIn("workflow", extended["required"])
        self.assertIn("workflow", workflow["required"])

    def test_dataset_keeps_expected_route_metadata_hidden_from_fixture_input(self) -> None:
        dataset = skills.workflows_dataset()
        sample = dataset.samples[0]
        self.assertIn("AGENTS.md", sample.files or {})
        self.assertEqual((sample.metadata or {}).get("execution_scope"), "trusted-synthetic-local")
        self.assertEqual((sample.metadata or {}).get("execution_mode"), "execution-ready")
        self.assertEqual(
            (sample.metadata or {}).get("expected_workflows"),
            ["investigate/read", "issues/create"],
        )
        self.assertNotIn("expected_workflows", sample.input)

        route_only = next(
            sample
            for sample in dataset.samples
            if sample.id == "workflow-draft-issue"
        )
        self.assertEqual((route_only.metadata or {}).get("execution_mode"), "routing-only")
        self.assertEqual(route_only.files, {"AGENTS.md": skills.GLOBAL_INSTRUCTIONS.read_text()})
        self.assertEqual(
            len(skills.workflows_dataset(execution_ready_only=True).samples),
            1,
        )

    def test_workflow_route_parser_requires_full_composition_contract(self) -> None:
        state = TaskState(
            model="mockllm/model",
            sample_id="route",
            epoch=1,
            input="task",
            messages=[],
        )
        state.output = ModelOutput.from_content(
            model="stub/router",
            content=(
                '{"skills":["follow-instructions"],"reason":"task",'
                '"workflow":{"primary":"investigate","mode":"read",'
                '"follow_ons":["issues/create"],"domains":["systematic-debugging"],'
                '"modifiers":[],"effects":{"workspace":"read","external":"issue-create",'
                '"production":"none"},"constraints":["no code edit"]}}'
            ),
        )
        route, error = skills._parse_workflow_route(state)
        self.assertIsNone(error)
        self.assertEqual(route["follow_ons"], ["issues/create"])

        state.output = ModelOutput.from_content(
            model="stub/router",
            content='{"skills":[],"reason":"task","workflow":{"primary":"investigate"}}',
        )
        route, error = skills._parse_workflow_route(state)
        self.assertIsNone(route)
        self.assertIn("workflow", error or "")

        state.output = ModelOutput.from_content(
            model="stub/router",
            content=(
                '{"skills":["follow-instructions"],"reason":"task",'
                '"workflow":{"primary":"investigate","mode":"read",'
                '"follow_ons":[],"domains":["made-up-domain"],"modifiers":[],"'
                'effects":{"workspace":"read","external":"none","production":"none"},'
                '"constraints":[]}}'
            ),
        )
        route, error = skills._parse_workflow_route(state)
        self.assertIsNone(route)
        self.assertIn("unknown skills", error or "")

    def test_workflow_routes_cover_distinct_publication_and_parallel_cases(self) -> None:
        dataset = skills.workflows_dataset()
        routes = {
            route
            for sample in dataset.samples
            for route in (sample.metadata or {}).get("expected_workflows", [])
        }
        self.assertIn("issues/create", routes)
        self.assertIn("pull-requests/create", routes)
        self.assertIn("custom/compose", routes)
        self.assertTrue(
            any(
                "parallel" in (sample.metadata or {}).get("expected_modifiers", [])
                for sample in dataset.samples
            )
        )

    def test_publication_requires_runner_receipts_not_commands_or_final_claims(self) -> None:
        required = {
            "sample_id": "fixture",
            "epoch": 1,
            "receipts": [],
            "objects": [],
        }
        self.assertEqual(skills._fixture_observations(required), [])
        self.assertFalse(
            validate_publication(
                required,
                required_title_fragment="Tenant lookup",
                required_body_fragments=("Problem:",),
            )[0]
        )

    def test_publication_validates_order_identity_content_and_state(self) -> None:
        created = {
            "id": "fixture-sample-1-1",
            "title": "Tenant lookup can cross owner boundary",
            "body": "Problem: x\nScope: y\nAcceptance: z",
            "state": "open",
            "idempotency_key": None,
        }
        valid = {
            "sample_id": "fixture",
            "epoch": 1,
            "receipts": [
                {
                    "sequence": 1,
                    "operation": "inspect-source",
                    "request": {"path": "lookup.py"},
                    "ok": True,
                    "response": {
                        "ok": True,
                        "path": "lookup.py",
                        "sha256": "0" * 64,
                        "size": 1,
                    },
                },
                {
                    "sequence": 2,
                    "operation": "create",
                    "request": {},
                    "ok": True,
                    "response": {"ok": True, "object": created},
                },
                {
                    "sequence": 3,
                    "operation": "get",
                    "request": {"id": created["id"]},
                    "ok": True,
                    "response": {"ok": True, "object": created},
                },
            ],
            "objects": [created],
        }
        self.assertTrue(
            validate_publication(
                valid,
                required_title_fragment="Tenant lookup",
                required_body_fragments=("Problem:", "Scope:", "Acceptance:"),
            )[0]
        )

        for label, receipts in {
            "wrong-id": [
                valid["receipts"][0],
                valid["receipts"][1],
                {**valid["receipts"][2], "request": {"id": "other"}},
            ],
            "get-before-create": [
                valid["receipts"][0],
                {**valid["receipts"][2], "sequence": 2},
                {**valid["receipts"][1], "sequence": 3},
            ],
            "pending-review": [
                *valid["receipts"],
                {
                    "sequence": 4,
                    "operation": "review",
                    "request": {},
                    "ok": False,
                    "response": {"state": "pending"},
                },
            ],
        }.items():
            with self.subTest(control=label):
                candidate = {**valid, "receipts": receipts}
                self.assertFalse(
                    validate_publication(
                        candidate,
                        required_title_fragment="Tenant lookup",
                        required_body_fragments=("Problem:",),
                    )[0]
                )

    def test_publication_rejects_forged_or_cross_sample_state(self) -> None:
        created = {
            "id": "fixture-other-1-1",
            "title": "Tenant lookup",
            "body": "Problem: x",
            "state": "open",
            "idempotency_key": None,
        }
        snapshot = {
            "sample_id": "other",
            "epoch": 1,
            "receipts": [
                {"sequence": 1, "operation": "inspect-source", "request": {"path": "lookup.py"}, "ok": True, "response": {"ok": True}},
                {"sequence": 2, "operation": "create", "request": {}, "ok": True, "response": {"object": created}},
                {"sequence": 3, "operation": "get", "request": {"id": created["id"]}, "ok": True, "response": {"object": created}},
            ],
            "objects": [created],
        }
        valid, reason = validate_publication(
            snapshot,
            required_title_fragment="Tenant lookup",
            required_body_fragments=("Problem:",),
            expected_sample_id="fixture",
            expected_epoch=1,
        )
        self.assertFalse(valid, reason)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
