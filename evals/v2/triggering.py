"""Validation and scoring helpers for the separate skill-trigger suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .catalog import catalog_skill_names
from .contracts import PILOT_SKILLS, REPO_ROOT


TRIGGER_FILE = REPO_ROOT / "evals" / "pilot" / "triggers.json"
CATALOG_TRIGGER_FILE = REPO_ROOT / "evals" / "catalog" / "triggers.json"


def _read(path: Path) -> Any:
    return json.loads(path.read_text())


def load_cases(path: Path = TRIGGER_FILE) -> list[dict[str, Any]]:
    value = _read(path)
    return [item for item in value.get("cases", []) if isinstance(item, dict)]


def validate_cases(path: Path = TRIGGER_FILE, *, expected_skills: tuple[str, ...] | None = None) -> list[str]:
    try:
        cases = load_cases(path)
    except (OSError, json.JSONDecodeError) as exc:
        return [str(exc)]
    errors: list[str] = []
    ids: set[str] = set()
    for case in cases:
        case_id = str(case.get("id"))
        if case_id in ids:
            errors.append(f"duplicate trigger case {case_id}")
        ids.add(case_id)
        if case.get("skill_name") not in PILOT_SKILLS:
            errors.append(f"{case_id}: unknown skill")
        if not isinstance(case.get("prompt"), str) or len(case["prompt"].strip()) < 20:
            errors.append(f"{case_id}: prompt is too short")
        if not isinstance(case.get("should_trigger"), bool):
            errors.append(f"{case_id}: should_trigger must be boolean")
        if f"${case.get('skill_name')}" in str(case.get("prompt")):
            errors.append(f"{case_id}: prompt names the target skill")
    skills = expected_skills or PILOT_SKILLS
    for skill in skills:
        selected = [case for case in cases if case.get("skill_name") == skill]
        if len(selected) != 8:
            errors.append(f"{skill}: expected 8 trigger cases, found {len(selected)}")
        if sum(case.get("should_trigger") is True for case in selected) != 4:
            errors.append(f"{skill}: expected 4 positive trigger cases")
        if sum(case.get("should_trigger") is False for case in selected) != 4:
            errors.append(f"{skill}: expected 4 negative trigger cases")
    return errors


def observed_skill(run_dir: Path, skill_name: str) -> tuple[bool, str]:
    provider_result = {}
    try:
        provider_result = json.loads((run_dir / "provider_result.json").read_text())
    except (OSError, json.JSONDecodeError):
        pass
    available = provider_result.get("available_skills", []) if isinstance(provider_result, dict) else []
    if skill_name in available:
        return True, "provider_available_skills"
    for filename in ("transcript.jsonl", "stderr.txt"):
        try:
            text = (run_dir / filename).read_text(errors="replace")
        except OSError:
            continue
        if f"/.agents/skills/{skill_name}/" in text or f"/.claude/skills/{skill_name}/" in text:
            return True, f"{filename}_skill_path"
    return False, "no_activation_signal"


def score_case(case: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    observed, evidence = observed_skill(run_dir, str(case["skill_name"]))
    expected = bool(case["should_trigger"])
    return {"id": case["id"], "skill_name": case["skill_name"], "should_trigger": expected, "observed": observed, "passed": observed == expected, "evidence": evidence}


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    positives = [item for item in results if item["should_trigger"]]
    negatives = [item for item in results if not item["should_trigger"]]
    true_positive = sum(item["observed"] for item in positives)
    false_negative = len(positives) - true_positive
    true_negative = sum(not item["observed"] for item in negatives)
    false_positive = len(negatives) - true_negative
    return {
        "cases": len(results),
        "true_positive": true_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "trigger_recall": true_positive / len(positives) if positives else None,
        "trigger_specificity": true_negative / len(negatives) if negatives else None,
        "passed": sum(item["passed"] for item in results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate trigger cases or score a JSON result file")
    parser.add_argument("--suite", choices=("pilot", "catalog"), default="pilot")
    parser.add_argument("--path", type=Path, default=None)
    args = parser.parse_args()
    path = args.path or (CATALOG_TRIGGER_FILE if args.suite == "catalog" else TRIGGER_FILE)
    skills = catalog_skill_names() if args.suite == "catalog" else PILOT_SKILLS
    errors = validate_cases(path, expected_skills=skills)
    if errors:
        print("Trigger validation failed:\n" + "\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Trigger validation passed: {len(load_cases(path))} balanced cases across {len(skills)} skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
