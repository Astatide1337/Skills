"""Load and normalize v2 task contracts.

Contracts may be authored as one JSON document per skill (with a ``cases``
array) or as one JSON document per case under ``evals/pilot/<skill>/``. The
normal form used by the runner is one dictionary per case.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
PILOT_ROOT = REPO_ROOT / "evals" / "pilot"
CATALOG_ROOT = REPO_ROOT / "evals" / "catalog"
PILOT_SKILLS = ("production-safety", "shadcn", "verify-work")


class DuplicateJSONKeyError(ValueError):
    """Raised when a contract document contains an ambiguous duplicate key."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise DuplicateJSONKeyError(f"duplicate JSON key: {key}")
        value[key] = child
    return value


def _json(path: Path) -> Any:
    return json.loads(path.read_text(), object_pairs_hook=_reject_duplicate_keys)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def discover_documents(root: Path = PILOT_ROOT) -> list[tuple[Path, dict[str, Any]]]:
    root = root.resolve()
    documents: list[tuple[Path, dict[str, Any]]] = []
    if not root.exists():
        return documents
    for path in sorted(root.rglob("*.json")):
        relative = path.relative_to(root)
        if "fixtures" in relative.parts:
            continue
        if path.name.startswith("_") or path.name in {"schema.json", "triggers.json"}:
            continue
        try:
            value = _json(path)
        except (OSError, json.JSONDecodeError, DuplicateJSONKeyError):
            continue
        if isinstance(value, dict):
            documents.append((path, value))
    return documents


def iter_cases(root: Path = PILOT_ROOT) -> Iterable[tuple[Path, dict[str, Any]]]:
    for source, document in discover_documents(root):
        inherited = {
            key: document.get(key)
            for key in ("schema_version", "skill_name", "objective", "hard_requirements", "forbidden_outcomes", "execution", "rubric")
            if key in document
        }
        cases = document.get("cases")
        if isinstance(cases, list):
            for case in cases:
                if isinstance(case, dict):
                    normalized = {**inherited, **case}
                    normalized["_source"] = str(source.resolve().relative_to(REPO_ROOT.resolve()))
                    yield source, normalized
            continue
        if "id" in document:
            normalized = dict(document)
            normalized["_source"] = str(source.resolve().relative_to(REPO_ROOT.resolve()))
            yield source, normalized


def load_case(skill_name: str, case_id: str, root: Path = PILOT_ROOT) -> dict[str, Any]:
    matches = [
        case
        for _source, case in iter_cases(root)
        if case.get("skill_name") == skill_name and str(case.get("id")) == case_id
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one contract for {skill_name}/{case_id}, found {len(matches)}")
    return matches[0]


def cases_for_skill(skill_name: str, root: Path = PILOT_ROOT) -> list[dict[str, Any]]:
    cases = [case for _source, case in iter_cases(root) if case.get("skill_name") == skill_name]
    return sorted(cases, key=lambda case: str(case.get("id", "")))


def fixture_path(case: dict[str, Any]) -> Path | None:
    fixture = case.get("fixture")
    if fixture in (None, {}):
        return None
    if isinstance(fixture, str):
        raw = fixture
    elif isinstance(fixture, dict):
        raw = fixture.get("path")
    else:
        return None
    if not isinstance(raw, str) or not raw:
        return None
    candidate = (REPO_ROOT / raw).resolve()
    try:
        candidate.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return None
    return candidate


def execution_mode(case: dict[str, Any]) -> str:
    execution = case.get("execution")
    if isinstance(execution, dict):
        mode = execution.get("mode", "text_only")
    else:
        mode = "text_only"
    if mode not in {"text_only", "workspace_write"}:
        raise ValueError(f"unsupported execution mode {mode!r} in {case.get('_source')}")
    return str(mode)


def reference_path(case: dict[str, Any], key: str) -> Path | None:
    reference = case.get(key)
    if isinstance(reference, str):
        raw = reference
    elif isinstance(reference, dict):
        raw = reference.get("path")
    else:
        raw = None
    if not isinstance(raw, str) or not raw:
        return None
    path = (REPO_ROOT / raw).resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return None
    return path


def reference_output_path(case: dict[str, Any], key: str) -> str | None:
    """Return the project-relative destination for a workspace reference.

    Text-only references are written to the response artifact. Workspace
    references need an explicit destination so the offline reference check
    can exercise the same file graders as a provider trial.
    """

    reference = case.get(key)
    if not isinstance(reference, dict):
        return None
    output = reference.get("output_path")
    if not isinstance(output, str) or not output.strip():
        return None
    candidate = Path(output)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    return output


def contract_digest(case: dict[str, Any]) -> str:
    """Return a stable digest for the task contract used in a trial."""

    payload = {key: value for key, value in case.items() if not key.startswith("_")}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def rubric(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in _as_list(case.get("rubric")) if isinstance(item, dict)]


def graders(case: dict[str, Any]) -> list[dict[str, Any]]:
    value = case.get("deterministic_graders")
    if value is None:
        value = case.get("graders")
    return [item for item in _as_list(value) if isinstance(item, dict)]
