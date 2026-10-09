"""Deterministic validation for constrained, evidence-bounded final answers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


class _DuplicateKey(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateKey(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def parse_unique_json_object(content: str) -> dict[str, Any]:
    """Parse one JSON object and reject duplicate keys at every nesting level."""
    value = json.loads(content, object_pairs_hook=_unique_object)
    if not isinstance(value, dict):
        raise TypeError("expected a JSON object")
    return value


def _expected_value(
    field: str,
    directive: object,
    *,
    artifacts: Mapping[str, object],
    runner_acceptance: Mapping[str, object] | None,
) -> tuple[object, str | None]:
    if not isinstance(directive, Mapping):
        return None, f"invalid final-answer contract for {field}"

    if set(directive) == {"equals"}:
        return directive["equals"], None

    if set(directive) == {"artifact_field"}:
        source = directive["artifact_field"]
        if (
            not isinstance(source, Mapping)
            or set(source) != {"path", "field"}
            or not isinstance(source["path"], str)
            or not isinstance(source["field"], str)
        ):
            return None, f"invalid artifact binding for final-answer field {field}"
        artifact = artifacts.get(source["path"])
        if not isinstance(artifact, Mapping) or source["field"] not in artifact:
            return None, f"final-answer evidence is missing for field {field}"
        return artifact[source["field"]], None

    if set(directive) == {"runner_acceptance"}:
        outcomes = directive["runner_acceptance"]
        if (
            not isinstance(outcomes, Mapping)
            or set(outcomes) != {"passed", "failed"}
            or runner_acceptance is None
            or runner_acceptance.get("source") != "runner-owned"
            or type(runner_acceptance.get("exit_code")) is not int
        ):
            return None, f"runner-owned outcome is unavailable for field {field}"
        outcome = "passed" if runner_acceptance["exit_code"] == 0 else "failed"
        return outcomes[outcome], None

    return None, f"unsupported final-answer binding for field {field}"


def validate_final_answer(
    completion: str,
    contract: Mapping[str, object],
    *,
    artifacts: Mapping[str, object] | None = None,
    runner_acceptance: Mapping[str, object] | None = None,
) -> tuple[bool, str]:
    """Require exactly one JSON object whose fields match fixed runner evidence.

    This deliberately checks a narrow, constrained response format. It is not a
    semantic grader for arbitrary prose.
    """
    if not isinstance(contract, Mapping):
        return False, "invalid final-answer contract"
    fields = contract.get("fields")
    if (
        set(contract) != {"fields"}
        or not isinstance(fields, Mapping)
        or not fields
        or not all(isinstance(field, str) for field in fields)
    ):
        return False, "invalid final-answer contract"
    if not isinstance(completion, str) or not completion.strip():
        return False, "final answer is missing"

    try:
        answer = parse_unique_json_object(completion)
    except (TypeError, ValueError) as exc:
        return False, f"final answer must be one JSON object: {exc}"
    if set(answer) != set(fields):
        return False, "final answer has missing or extra keys"

    evidence = artifacts or {}
    for field, directive in fields.items():
        expected, error = _expected_value(
            field,
            directive,
            artifacts=evidence,
            runner_acceptance=runner_acceptance,
        )
        if error is not None:
            return False, error
        if answer[field] != expected:
            return False, f"final-answer field {field} conflicts with runner evidence"
    return True, "final answer matches the constrained evidence contract"
