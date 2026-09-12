"""Deterministic contract checks for the task-playbook evaluation path."""

from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path

from inspect_ai.model import ModelOutput
from inspect_ai.solver import TaskState

from evals import skills
from evals.fake_tracker import FakeTracker, validate_publication


class WorkflowContractTests(unittest.TestCase):
    @staticmethod
    def _source_response(content: str = "def lookup():\n    return None\n") -> dict[str, object]:
        raw = content.encode()
        return {
            "ok": True,
            "source": "fixture-owned-read",
            "path": "lookup.py",
            "content": content,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
        }

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
            if sample.id == "workflow-update-issue"
        )
        self.assertEqual((route_only.metadata or {}).get("execution_mode"), "routing-only")
        self.assertEqual(route_only.files, {"AGENTS.md": skills.GLOBAL_INSTRUCTIONS.read_text()})
        self.assertEqual(
            len(skills.workflows_dataset(execution_ready_only=True).samples),
            7,
        )

    def test_workflow_route_parser_requires_full_composition_contract(self) -> None:
        state = TaskState(
            model="gpt-5.6-luna",
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

    def test_execution_ready_pilot_is_balanced_and_contract_bound(self) -> None:
        dataset = skills.workflows_dataset(execution_ready_only=True)
        cases = {sample.id: sample for sample in dataset.samples}
        self.assertEqual(
            set(cases),
            {
                "workflow-investigate-create-issue",
                "workflow-draft-issue",
                "workflow-fix-open-draft-pr",
                "workflow-native-local-repair",
                "workflow-custom-temporary",
                "workflow-parallel-safe",
                "workflow-correction-resume",
            },
        )
        for sample in cases.values():
            metadata = sample.metadata or {}
            self.assertEqual(metadata.get("execution_mode"), "execution-ready")
            self.assertIsInstance(metadata.get("fixture_contract"), dict)
            self.assertTrue(sample.files)

    def test_runner_acceptance_is_the_original_test_not_a_source_fragment(self) -> None:
        sample = next(
            sample
            for sample in skills.workflows_dataset(execution_ready_only=True).samples
            if sample.id == "workflow-native-local-repair"
        )
        contract = (sample.metadata or {}).get("fixture_contract")
        self.assertIsInstance(contract, dict)
        self.assertEqual(contract.get("acceptance_test"), sample.files["test_bug.py"])
        self.assertNotIn("required_content", contract)

    def test_runner_acceptance_distinguishes_fix_broken_code_and_replaced_test(self) -> None:
        sample = next(
            sample
            for sample in skills.workflows_dataset(execution_ready_only=True).samples
            if sample.id == "workflow-native-local-repair"
        )
        contract = (sample.metadata or {}).get("fixture_contract")
        self.assertIsInstance(contract, dict)
        acceptance_command, error = skills._runner_acceptance_command(contract)
        self.assertIsNone(error)
        self.assertIsNotNone(acceptance_command)
        command = acceptance_command or []
        original_bug = sample.files["bug.py"]
        original_test = sample.files["test_bug.py"]
        correct_bug = str(contract["write_content"])

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "bug.py").write_text(correct_bug)
            (workspace / "test_bug.py").write_text(original_test)
            fixed = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(fixed.returncode, 0, fixed.stderr)

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "bug.py").write_text(original_bug)
            (workspace / "test_bug.py").write_text(original_test)
            broken = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(broken.returncode, 0)

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "bug.py").write_text(original_bug)
            (workspace / "test_bug.py").write_text("print('ok')\n")
            weakened_test = subprocess.run(
                ["python", "-S", "-B", "test_bug.py"],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(weakened_test.returncode, 0, weakened_test.stderr)
            runner_check = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(runner_check.returncode, 0)

    def test_acceptance_order_controls_cover_the_final_artifact(self) -> None:
        task = skills.workflow_failed_outcome_smoke()
        samples = {sample.id: sample for sample in task.dataset}
        self.assertEqual(
            set(samples),
            {
                "workflow-failed-outcome-smoke",
                "workflow-acceptance-correct",
                "workflow-acceptance-replaced-test",
                "workflow-acceptance-final-artifact",
            },
        )
        for sample in samples.values():
            contract = (sample.metadata or {}).get("fixture_contract")
            self.assertIsInstance(contract, dict)
            self.assertEqual(contract.get("acceptance_test"), sample.files["test_bug.py"])
            self.assertEqual((contract.get("kind")), "workspace-test")
        final_artifact = samples["workflow-acceptance-final-artifact"]
        self.assertEqual(
            (final_artifact.metadata or {})["fixture_contract"]["test_command"],
            ["python", "supplemental.py"],
        )

    def test_final_artifact_control_passes_before_and_fails_after_restore(self) -> None:
        task = skills.workflow_failed_outcome_smoke()
        sample = next(
            sample
            for sample in task.dataset
            if sample.id == "workflow-acceptance-final-artifact"
        )
        contract = (sample.metadata or {}).get("fixture_contract")
        self.assertIsInstance(contract, dict)
        acceptance_command, error = skills._runner_acceptance_command(contract)
        self.assertIsNone(error)
        self.assertIsNotNone(acceptance_command)
        correct_bug = (
            "def search(actor, record):\n"
            "    if record.get('tenant') != actor:\n"
            "        raise PermissionError('tenant mismatch')\n"
            "    return record\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "bug.py").write_text(correct_bug)
            (workspace / "test_bug.py").write_text(sample.files["test_bug.py"])
            (workspace / "supplemental.py").write_text(sample.files["supplemental.py"])

            before = subprocess.run(
                acceptance_command or [],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(before.returncode, 0, before.stderr)

            supplemental = subprocess.run(
                ["python", "-S", "-B", "supplemental.py"],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(supplemental.returncode, 0, supplemental.stderr)

            after = subprocess.run(
                acceptance_command or [],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(after.returncode, 0)

    def test_standalone_verification_has_a_coherent_route(self) -> None:
        schema = json.loads(skills.WORKFLOW_ROUTE_SCHEMA.read_text())
        primary = schema["properties"]["workflow"]["properties"]["primary"]["enum"]
        follow_ons = schema["properties"]["workflow"]["properties"]["follow_ons"]["items"]["enum"]
        self.assertIn("verify-work", primary)
        self.assertNotIn("verify-work/verify", follow_ons)

    def test_comparison_arms_require_explicit_baseline_and_catalog_mode(self) -> None:
        with self.assertRaises(ValueError):
            skills.workflows(arm="baseline")
        with self.assertRaises(ValueError):
            skills.workflows(with_skills=True, arm="no-catalog-diagnostic")

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
            "idempotency_key": "fixture-key",
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
                    "response": self._source_response(),
                },
                {
                    "sequence": 2,
                    "operation": "create",
                    "request": {
                        "title": "Tenant lookup can cross owner boundary",
                        "body": "Problem: x\nScope: y\nAcceptance: z",
                        "idempotency_key": "fixture-key",
                    },
                    "ok": True,
                    "response": {"ok": True, "object": created, "replayed": False},
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
            "idempotency_key": "fixture-key",
        }
        snapshot = {
            "sample_id": "other",
            "epoch": 1,
            "receipts": [
                {"sequence": 1, "operation": "inspect-source", "request": {"path": "lookup.py"}, "ok": True, "response": self._source_response()},
                {"sequence": 2, "operation": "create", "request": {"title": "Tenant lookup", "body": "Problem: x", "idempotency_key": "fixture-key"}, "ok": True, "response": {"object": created, "replayed": False}},
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

    def test_fake_tracker_records_real_ordered_operations_and_rejects_ambiguous_create(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "lookup.py").write_text("def lookup():\n    return None\n")
            tracker = FakeTracker("sample-a", 2, workspace=workspace)
            tracker.start()
            try:
                self.assertTrue(
                    tracker._dispatch(
                        {"operation": "inspect-source", "path": "lookup.py"}
                    )["ok"]
                )
                created = tracker._dispatch(
                    {
                        "operation": "create",
                        "title": "Tenant lookup",
                        "body": "Problem: x\nScope: y\nAcceptance: z",
                        "idempotency_key": "sample-a-key",
                    }
                )
                self.assertTrue(created["ok"])
                object_id = created["object"]["id"]
                replay = tracker._dispatch(
                    {
                        "operation": "create",
                        "title": "Tenant lookup",
                        "body": "Problem: x\nScope: y\nAcceptance: z",
                        "idempotency_key": "sample-a-key",
                    }
                )
                self.assertTrue(replay["ok"])
                self.assertTrue(replay["replayed"])
                readback = tracker._dispatch({"operation": "get", "id": object_id})
                self.assertTrue(readback["ok"])
                valid_snapshot = tracker.snapshot()
                duplicate = tracker._dispatch(
                    {
                        "operation": "create",
                        "title": "Tenant lookup duplicate",
                        "body": "Problem: duplicate",
                    }
                )
                self.assertFalse(duplicate["ok"])
                snapshot = tracker.snapshot()
            finally:
                tracker.close()
        valid, reason = validate_publication(
            valid_snapshot,
            required_title_fragment="Tenant lookup",
            required_body_fragments=("Problem:", "Scope:", "Acceptance:"),
            expected_sample_id="sample-a",
            expected_epoch=2,
        )
        self.assertTrue(valid, reason)
        self.assertEqual(len(snapshot["objects"]), 1)
        self.assertEqual(
            [item["operation"] for item in snapshot["receipts"]],
            ["inspect-source", "create", "create", "get", "create"],
        )

    def test_source_receipt_is_runner_owned_and_ordered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "lookup.py").write_text("SOURCE = 'observed'\n")
            tracker = FakeTracker("socket-sample", 3, workspace=workspace)
            tracker.start()
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                    connection.connect(tracker.socket_path)
                    connection.sendall(
                        (json.dumps(
                            {
                                "operation": "inspect-source",
                                "path": "lookup.py",
                                "sha256": "0" * 64,
                                "size": 0,
                            }
                        ) + "\n").encode()
                    )
                    response = json.loads(connection.recv(4096))
                self.assertFalse(response["ok"])
                legitimate = tracker._dispatch(
                    {"operation": "inspect-source", "path": "lookup.py"}
                )
                self.assertEqual(legitimate["content"], "SOURCE = 'observed'\n")
                self.assertEqual(
                    legitimate["sha256"],
                    hashlib.sha256(b"SOURCE = 'observed'\n").hexdigest(),
                )
            finally:
                tracker.close()

    def test_publication_rejects_fabricated_source_and_late_inspection(self) -> None:
        created = {
            "id": "fixture-sample-1-1",
            "title": "Tenant lookup",
            "body": "Problem: x",
            "state": "open",
            "idempotency_key": "key",
        }
        source = self._source_response()
        valid_receipts = [
            {"sequence": 1, "operation": "inspect-source", "request": {"path": "lookup.py"}, "ok": True, "response": source},
            {"sequence": 2, "operation": "create", "request": {"title": "Tenant lookup", "body": "Problem: x", "idempotency_key": "key"}, "ok": True, "response": {"ok": True, "object": created, "replayed": False}},
            {"sequence": 3, "operation": "get", "request": {"id": created["id"]}, "ok": True, "response": {"ok": True, "object": created}},
        ]
        snapshot = {"sample_id": "fixture", "epoch": 1, "receipts": valid_receipts, "objects": [created]}
        forged = json.loads(json.dumps(snapshot))
        forged["receipts"][0]["response"]["content"] = "forged"
        self.assertFalse(
            validate_publication(
                forged,
                required_title_fragment="Tenant lookup",
                required_body_fragments=("Problem:",),
            )[0]
        )
        late = json.loads(json.dumps(snapshot))
        late["receipts"] = [
            valid_receipts[1],
            valid_receipts[0],
            valid_receipts[2],
        ]
        for sequence, receipt in enumerate(late["receipts"], start=1):
            receipt["sequence"] = sequence
        self.assertFalse(
            validate_publication(
                late,
                required_title_fragment="Tenant lookup",
                required_body_fragments=("Problem:",),
            )[0]
        )

    def test_idempotent_replay_is_one_object_and_conflicts_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as left_dir, tempfile.TemporaryDirectory() as right_dir:
            left = Path(left_dir)
            right = Path(right_dir)
            (left / "lookup.py").write_text("LEFT = True\n")
            (right / "lookup.py").write_text("RIGHT = True\n")
            first = FakeTracker("same-sample", 1, workspace=left)
            second = FakeTracker("same-sample", 2, workspace=right)
            first.start()
            second.start()
            try:
                for tracker in (first, second):
                    self.assertTrue(
                        tracker._dispatch(
                            {"operation": "inspect-source", "path": "lookup.py"}
                        )["ok"]
                    )
                initial = first._dispatch(
                    {
                        "operation": "create",
                        "title": "Tenant lookup",
                        "body": "Problem: x",
                        "idempotency_key": "retry-key",
                    }
                )
                self.assertTrue(initial["ok"])
                replay = first._dispatch(
                    {
                        "operation": "create",
                        "title": "Tenant lookup",
                        "body": "Problem: x",
                        "idempotency_key": "retry-key",
                    }
                )
                self.assertTrue(replay["ok"])
                self.assertTrue(replay["replayed"])
                conflict = first._dispatch(
                    {
                        "operation": "create",
                        "title": "Changed title",
                        "body": "Problem: x",
                        "idempotency_key": "retry-key",
                    }
                )
                self.assertFalse(conflict["ok"])
                self.assertEqual(len(first.snapshot()["objects"]), 1)
                second_initial = second._dispatch(
                    {
                        "operation": "create",
                        "title": "Tenant lookup",
                        "body": "Problem: x",
                        "idempotency_key": "retry-key",
                    }
                )
                self.assertTrue(second_initial["ok"])
                self.assertEqual(len(second.snapshot()["objects"]), 1)
                self.assertNotEqual(
                    initial["object"]["id"], second_initial["object"]["id"]
                )
            finally:
                first.close()
                second.close()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
