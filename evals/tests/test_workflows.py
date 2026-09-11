"""Deterministic contract checks for the task-playbook evaluation path."""

from __future__ import annotations

import json
import unittest

from inspect_ai.model import ModelOutput
from inspect_ai.solver import TaskState

from evals import skills


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
        self.assertEqual(
            (sample.metadata or {}).get("expected_workflows"),
            ["investigate/read", "issues/create"],
        )
        self.assertNotIn("expected_workflows", sample.input)

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

    def test_fixture_observations_use_successful_tool_events_not_final_prose(self) -> None:
        state = TaskState(
            model="mockllm/model",
            sample_id="fixture",
            epoch=1,
            input="task",
            messages=[],
        )
        state.output = ModelOutput.from_content(
            model="stub/native",
            content="I inspected lookup.py and created an issue.",
        )
        state.output.metadata = {
            "codex_jsonl": "\n".join(
                [
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "command_execution",
                                "command": "sed -n '1,40p' lookup.py",
                                "exit_code": 0,
                                "status": "completed",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "command_execution",
                                "command": "python tracker.py create --title t --body b",
                                "exit_code": 0,
                                "status": "completed",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "command_execution",
                                "command": "python tracker.py get fixture-1",
                                "exit_code": 0,
                                "status": "completed",
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "command_execution",
                                "command": "python tracker.py create --title failed --body failed",
                                "exit_code": 1,
                                "status": "completed",
                            },
                        }
                    ),
                ]
            )
        }
        self.assertEqual(
            skills._fixture_observations_from_events(state),
            ["owning-source-inspected", "issue-created", "issue-read-back"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
