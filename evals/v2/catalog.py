"""Normalize the repository's skill eval manifests into v2 catalog cases.

The skill directories contain the current, user-authored tuning manifests under
``skills/*/evals/evals.json``.  They predate the v2 contract schema, so this
module adapts them at load time instead of rewriting them.  The original
``evals/catalog/heldout.json`` is preserved as frozen v1 evidence; the active
catalog uses the clean, versioned ``heldout-v2.json`` document.

The adapter deliberately treats ``skill_available`` as harness metadata: the
runner already invalidates a trial when the treatment/baseline skill boundary
is wrong.  It must not become a task-pass advantage for the treatment arm.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .contracts import CATALOG_ROOT, REPO_ROOT, _json


SKILLS_ROOT = REPO_ROOT / "skills"
CATALOG_TUNING_FILE = CATALOG_ROOT / "tuning-additional.json"
CATALOG_HELDOUT_FILE = CATALOG_ROOT / "heldout-v2.json"
CATALOG_HELDOUT_VERSION = 2


def _read_json(path: Path) -> Any:
    return _json(path)


def _terms(check: dict[str, Any]) -> list[str]:
    value = check.get("terms")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _normalize_check(check: dict[str, Any]) -> dict[str, Any] | None:
    check_type = str(check.get("type") or "")
    # This is verified by grade_trial before task graders run.  Applying it to
    # both arms would make every baseline fail for the intended reason.
    if check_type == "skill_available":
        return None
    normalized_type = {
        "final_response_nonempty": "response_nonempty",
        "response_regex_all": "response_regex",
        "file_contains_any": "file_contains_any",
    }.get(check_type, check_type)
    value: dict[str, Any] = {
        "id": str(check.get("id") or "unnamed-check"),
        "type": normalized_type,
        "description": str(check.get("text") or check.get("description") or check.get("id") or "contract check"),
        "required": True,
    }
    for key in ("terms", "patterns", "path", "needle", "min_chars", "command", "expected_exit", "tools", "calibration_good", "calibration_bad"):
        if key in check:
            value[key] = check[key]
    # The legacy manifests use a scalar ``needle`` for file_contains checks;
    # v2 contracts use a list-valued ``terms`` field.  Normalize at the
    # boundary so the strict validator and every grader see one shape.
    if normalized_type in {"file_contains", "file_contains_any", "file_not_contains"} and "terms" not in value:
        needle = value.get("needle")
        if isinstance(needle, str) and needle.strip():
            value["terms"] = [needle]
        elif isinstance(needle, list):
            value["terms"] = needle
    if check_type == "final_response_nonempty" and "min_chars" not in value:
        value["min_chars"] = 1
    if normalized_type in {"no_project_changes", "no_forbidden_tool_calls", "secret_canary_absent"}:
        value["critical"] = True
    return value


def _normalize_rubric(rubric: Any) -> list[dict[str, Any]]:
    if not isinstance(rubric, list):
        rubric = []
    result: list[dict[str, Any]] = []
    for index, item in enumerate(rubric):
        if not isinstance(item, dict):
            continue
        anchors = item.get("anchors") if isinstance(item.get("anchors"), dict) else {}
        # Legacy manifests use a 1/3/5 scale.  v2 uses 0/1/2 so that the
        # independent review schema has one unambiguous scale.
        normalized_anchors = {
            "0": str(anchors.get("0", anchors.get("1", "Fails the criterion."))),
            "1": str(anchors.get("1", anchors.get("3", "Partially satisfies the criterion."))),
            "2": str(anchors.get("2", anchors.get("5", "Fully satisfies the criterion."))),
        }
        if "3" in anchors:
            normalized_anchors["1"] = str(anchors["3"])
        if "5" in anchors:
            normalized_anchors["2"] = str(anchors["5"])
        result.append({
            "id": str(item.get("id") or f"criterion-{index + 1}"),
            "description": str(item.get("description") or item.get("id") or "Quality criterion"),
            "anchors": normalized_anchors,
        })
    if len(result) >= 2:
        return result
    return [
        {
            "id": "task-grounding",
            "description": "Addresses the supplied task with specific, internally consistent guidance.",
            "anchors": {"0": "Misses the task.", "1": "Addresses the task partially.", "2": "Addresses the task specifically and completely."},
        },
        {
            "id": "boundary-discipline",
            "description": "Respects constraints and does not overclaim work or evidence.",
            "anchors": {"0": "Changes scope or overclaims.", "1": "Mostly respects the boundary.", "2": "Explicitly preserves the boundary and evidence limits."},
        },
    ]


def _legacy_case(skill_name: str, entry: dict[str, Any], source: Path) -> dict[str, Any]:
    checks = [_normalize_check(check) for check in entry.get("checks", []) if isinstance(check, dict)]
    graders = [check for check in checks if check is not None]
    workspace_write = any(check.get("type") in {"project_changes_present", "file_exists", "file_contains", "file_contains_any", "file_not_contains", "file_not_exists"} for check in graders)
    expectations = entry.get("expectations") if isinstance(entry.get("expectations"), list) else []
    hard_requirements = [str(value) for value in expectations if str(value).strip()]
    if not hard_requirements:
        hard_requirements = [str(entry.get("expected_output") or "Satisfy the task contract.")]
    forbidden = [
        str(check.get("description"))
        for check in graders
        if check.get("type") == "response_not_contains"
    ]
    if not forbidden:
        forbidden = ["Do not claim work, verification, or mutation that the prompt does not authorize."]
    prompt = _strip_skill_invocation(skill_name, str(entry.get("prompt") or ""))
    return {
        "schema_version": 1,
        "id": f"legacy-{entry.get('id')}",
        "skill_name": skill_name,
        "split": "tuning",
        "prompt": prompt,
        "objective": str(entry.get("expected_output") or ""),
        "hard_requirements": hard_requirements,
        "forbidden_outcomes": forbidden,
        "execution": {
            "mode": "workspace_write" if workspace_write else "text_only",
            "allowed_tools": ["Read", "Write", "Edit"] if workspace_write else ["Read"],
        },
        "deterministic_graders": graders,
        "rubric": _normalize_rubric(entry.get("rubric")),
        "_source": str(source.relative_to(REPO_ROOT)),
        "_legacy": True,
}


def _strip_skill_invocation(skill_name: str, prompt: str) -> str:
    """Keep activation out of content A/B trials.

    Triggering is a separate suite.  Content trials must compare the same
    task with and without the copied skill, so explicit ``Use $skill`` control
    prefixes are removed from both legacy and frozen catalog cases.
    """

    return re.sub(rf"^\s*Use\s+\${re.escape(skill_name)}\.\s*", "", prompt, count=1, flags=re.IGNORECASE)


def legacy_case_entries() -> list[tuple[Path, dict[str, Any]]]:
    result: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(SKILLS_ROOT.glob("*/evals/evals.json")):
        try:
            document = _read_json(path)
        except (OSError, ValueError) as exc:
            raise ValueError(f"invalid skill eval manifest {path}: {exc}") from exc
        skill_name = document.get("skill_name") or path.parent.parent.name
        if not isinstance(skill_name, str):
            continue
        entries = document.get("evals")
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict):
                result.append((path, _legacy_case(skill_name, entry, path)))
    return result


def _entries_from_file(path: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Load exactly one strict catalog document, excluding archived siblings."""

    document = _read_json(path)
    if not isinstance(document, dict):
        raise ValueError(f"catalog document must be an object: {path}")
    inherited = {
        key: document.get(key)
        for key in (
            "schema_version",
            "skill_name",
            "objective",
            "hard_requirements",
            "forbidden_outcomes",
            "execution",
            "rubric",
            "holdout_version",
        )
        if key in document
    }
    cases = document.get("cases")
    if isinstance(cases, list):
        values = [{**inherited, **case} for case in cases if isinstance(case, dict)]
    elif "id" in document:
        values = [dict(document)]
    else:
        raise ValueError(f"catalog document needs cases or id: {path}")
    return [
        (path, {**case, "_source": str(path.resolve().relative_to(REPO_ROOT.resolve()))})
        for case in values
    ]


def catalog_case_entries() -> list[tuple[Path, dict[str, Any]]]:
    """Return tuning manifests plus the active versioned held-out cases."""

    entries = legacy_case_entries()
    entries.extend(_entries_from_file(CATALOG_TUNING_FILE))
    heldout_entries = _entries_from_file(CATALOG_HELDOUT_FILE)
    if any(case.get("holdout_version") != CATALOG_HELDOUT_VERSION for _source, case in heldout_entries):
        raise ValueError(
            f"active holdout must declare holdout_version={CATALOG_HELDOUT_VERSION}: {CATALOG_HELDOUT_FILE}"
        )
    entries.extend(heldout_entries)
    normalized: list[tuple[Path, dict[str, Any]]] = []
    for source, case in entries:
        if case.get("_legacy"):
            normalized.append((source, case))
            continue
        value = dict(case)
        skill_name = value.get("skill_name")
        if isinstance(skill_name, str) and isinstance(value.get("prompt"), str):
            value["prompt"] = _strip_skill_invocation(skill_name, value["prompt"])
        normalized.append((source, value))
    return normalized


def catalog_input_files() -> tuple[Path, ...]:
    """Return every file that contributes to the active catalog contract set."""

    skill_manifests = sorted(SKILLS_ROOT.glob("*/evals/evals.json"))
    return tuple([*skill_manifests, CATALOG_TUNING_FILE, CATALOG_HELDOUT_FILE])


def catalog_input_digest() -> str:
    """Hash active catalog inputs, including legacy manifests adapted as tuning."""

    digest = hashlib.sha256()
    for path in catalog_input_files():
        digest.update(str(path.resolve().relative_to(REPO_ROOT.resolve())).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def catalog_cases_for_skill(skill_name: str) -> list[dict[str, Any]]:
    cases = [case for _source, case in catalog_case_entries() if case.get("skill_name") == skill_name]
    return sorted(cases, key=lambda case: str(case.get("id", "")))


def catalog_skill_names() -> tuple[str, ...]:
    return tuple(sorted({str(case.get("skill_name")) for _source, case in catalog_case_entries() if case.get("skill_name")}))
