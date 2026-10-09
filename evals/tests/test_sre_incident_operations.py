"""Synthetic SRE incident contract checks; not agent-efficacy evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "sre_incident_operations.json"
PROCEDURE = (
    ROOT / "skills" / "production-safety" / "references" / "sre-incident-operations.md"
)


class SREIncidentOperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.procedure = " ".join(PROCEDURE.read_text(encoding="utf-8").split())

    def test_canary_contrast_supports_correlation_but_not_root_cause(self) -> None:
        packet = self.packet
        canary = packet["cohorts"]["canary"]
        stable = packet["cohorts"]["stable"]

        self.assertEqual(canary["window_start"], stable["window_start"])
        self.assertEqual(canary["window_end"], stable["window_end"])
        self.assertNotEqual(canary["revision"], stable["revision"])
        self.assertGreater(
            canary["http_5xx_rate_percent"],
            stable["http_5xx_rate_percent"] * 10,
        )
        self.assertTrue(packet["expected"]["revision_cohort_correlation_supported"])
        self.assertFalse(packet["expected"]["root_cause_confirmed"])

    def test_same_window_shared_failure_is_a_revision_attribution_control(self) -> None:
        control = self.packet["negative_controls"]["shared_failure_across_revisions"]
        rates = (
            control["canary_http_5xx_rate_percent"],
            control["stable_http_5xx_rate_percent"],
        )
        self.assertEqual(control["service"], self.packet["service"]["name"])
        self.assertEqual(control["environment"], self.packet["service"]["environment"])
        self.assertEqual(control["region"], self.packet["service"]["region"])
        self.assertEqual(control["window_start"], self.packet["task"]["window_start"])
        self.assertEqual(control["window_end"], self.packet["task"]["window_end"])
        self.assertLess(max(rates) / min(rates), 1.25)
        self.assertFalse(control["expected_revision_specific_attribution"])
        self.assertIn("same symptom", self.procedure)

    def test_green_readiness_does_not_hide_user_path_failure(self) -> None:
        canary = self.packet["cohorts"]["canary"]
        control = self.packet["negative_controls"]["ready_but_user_path_fails"]
        self.assertEqual(canary["readiness"], "ready")
        self.assertEqual(canary["synthetic_user_request"], "failed")
        self.assertEqual(control["expected_user_impact"], "degraded")
        self.assertEqual(self.packet["expected"]["user_impact"], "degraded")
        self.assertIn(
            "A ready process can still return failing requests", self.procedure
        )

    def test_unavailable_dependency_evidence_stays_unknown(self) -> None:
        postgres = next(
            dependency
            for dependency in self.packet["dependencies"]
            if dependency["name"] == "postgres"
        )
        control = self.packet["negative_controls"]["unavailable_dependency_signal"]
        self.assertEqual(postgres["state"], "unknown")
        self.assertIsNone(postgres["observed_at"])
        self.assertIsNone(postgres["scope"])
        self.assertEqual(control["expected_health_claim"], "unknown")
        self.assertEqual(self.packet["expected"]["postgres_health"], "unknown")

    def test_stale_unverified_recovery_does_not_support_rollback_safety(self) -> None:
        target = self.packet["recovery_target"]
        control = self.packet["negative_controls"]["stale_unverified_recovery"]
        self.assertIsNone(target["artifact_digest"])
        self.assertFalse(target["artifact_digest_verified"])
        self.assertFalse(target["schema_compatibility_verified"])
        self.assertEqual(control["last_known_healthy_hours_before_incident"], 3)
        self.assertFalse(control["expected_rollback_safety_claim"])
        self.assertFalse(self.packet["expected"]["rollback_safe"])

    def test_offline_scope_and_operational_gates_are_explicit(self) -> None:
        self.assertEqual(self.packet["task"]["execution_mode"], "offline-snapshot")
        self.assertFalse(self.packet["task"]["live_mutation_authorized"])
        self.assertFalse(self.packet["expected"]["live_mutation_permitted"])
        for required in (
            "**Trigger:**",
            "**Objective:**",
            "## Authority and inputs",
            "## Workflow",
            "same-duration pre-incident baseline",
            "blast radius",
            "stop threshold",
            "recovery evidence",
            "A successful command exit is not recovery evidence",
            "execute only a previously authorized rollback path",
        ):
            with self.subTest(required=required):
                self.assertIn(required, self.procedure)
