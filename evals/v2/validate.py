"""Offline validation for the pilot task contracts.

This command deliberately performs no provider calls and executes no grader
commands. It validates the evaluation inputs before a paid or nondeterministic
run can happen.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from .contracts import PILOT_ROOT, PILOT_SKILLS, REPO_ROOT, cases_for_skill, discover_documents, execution_mode, fixture_path, graders, iter_cases, reference_output_path, reference_path, rubric


NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LEAK_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"(?:postgres|postgresql|mysql|redis)://", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"(?:mcp|agents|grafana)\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.IGNORECASE),
)
LIVE_WORDS = ("kubectl apply", "terraform apply", "ansible-playbook", "helm upgrade", "docker login")
COMMAND_DENY_PATTERNS = (
    re.compile(r"\b(?:curl|wget|nc|netcat|ssh|scp)\b", re.IGNORECASE),
    re.compile(r"\b(?:kubectl|terraform|ansible|helm|docker)\b", re.IGNORECASE),
    re.compile(r"\b(?:npm|pnpm|yarn|pip|uv)\s+(?:install|add|remove)\b", re.IGNORECASE),
    re.compile(r"(?:https?://|git\s+clone|rm\s+-rf|sudo\b)", re.IGNORECASE),
)
RESERVED_FIXTURE_NAMES = {".agents", ".claude", ".codex", ".mcp", ".mcp.json", ".openai", "AGENTS.md", "CLAUDE.md"}
ALLOWED_GRADER_TYPES = {
    "command",
    "no_project_changes",
    "project_changes_present",
    "response_nonempty",
    "response_contains_all",
    "response_contains_any",
    "response_not_contains",
    "response_regex",
    "file_exists",
    "file_not_exists",
    "file_contains",
    "file_contains_any",
    "file_not_contains",
    "file_code_regex",
    "no_forbidden_tool_calls",
    "secret_canary_absent",
}


def _error(errors: list[str], source: str, message: str) -> None:
    errors.append(f"{source}: {message}")


def _scan_text(errors: list[str], source: str, value: Any) -> None:
    if not isinstance(value, str):
        return
    for pattern in LEAK_PATTERNS:
        if pattern.search(value):
            _error(errors, source, f"possible credential or live endpoint leakage matched {pattern.pattern!r}")
    lowered = value.casefold()
    for word in LIVE_WORDS:
        if word in lowered:
            _error(errors, source, f"live mutation command {word!r} must not appear in a pilot task")


def _scan_value(errors: list[str], source: str, value: Any) -> None:
    if isinstance(value, str):
        _scan_text(errors, source, value)
    elif isinstance(value, dict):
        for key, child in value.items():
            _scan_value(errors, f"{source}.{key}", child)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_value(errors, f"{source}[{index}]", child)


def _scan_file(errors: list[str], path: Path) -> None:
    if not path.is_file() or path.stat().st_size > 2_000_000:
        return
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return
    _scan_text(errors, str(path.relative_to(REPO_ROOT)), text)


def _raw_case_path(case: dict[str, Any], field: str) -> Path | None:
    value = case.get(field)
    if isinstance(value, str):
        raw = value
    elif isinstance(value, dict):
        raw = value.get("path")
    else:
        raw = None
    if not isinstance(raw, str) or not raw:
        return None
    candidate = REPO_ROOT / raw
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError:
        return None
    return candidate


def _contains_symlink(path: Path) -> bool:
    current = path
    root = REPO_ROOT.resolve()
    while True:
        if current.is_symlink():
            return True
        if current == root:
            return False
        if current.parent == current:
            return False
        current = current.parent


def _scan_fixture_namespace(errors: list[str], fixture: Path, label: str) -> None:
    paths = [fixture] if fixture.is_file() else [fixture, *fixture.rglob("*")]
    for path in paths:
        relative = path.relative_to(fixture)
        if any(part in RESERVED_FIXTURE_NAMES for part in relative.parts):
            _error(errors, label, f"fixture contains reserved provider-context path: {relative}")
        if path.is_symlink():
            _error(errors, label, f"fixture contains symlink: {relative}")


def _validate_grader_shape(errors: list[str], label: str, grader: dict[str, Any]) -> None:
    grader_id = str(grader.get("id") or "<missing-id>")
    grader_type = str(grader.get("type") or grader.get("kind") or "")
    if grader_type in {"response_contains_all", "response_contains_any", "response_not_contains"}:
        terms = grader.get("terms")
        if not isinstance(terms, list) or not terms or not all(isinstance(term, str) and term.strip() for term in terms):
            _error(errors, label, f"grader {grader_id!r} needs a non-empty terms list")
    if grader_type == "response_regex":
        patterns = grader.get("patterns")
        if not isinstance(patterns, list) or not patterns or not all(isinstance(pattern, str) and pattern for pattern in patterns):
            _error(errors, label, f"grader {grader_id!r} needs a non-empty patterns list")
        else:
            for pattern in patterns:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    _error(errors, label, f"grader {grader_id!r} has invalid regex {pattern!r}: {exc}")
    if grader_type == "response_nonempty":
        minimum = grader.get("min_chars", 1)
        if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
            _error(errors, label, f"grader {grader_id!r} min_chars must be a positive integer")
    if grader_type in {"file_exists", "file_not_exists", "file_contains", "file_contains_any", "file_not_contains", "file_code_regex"}:
        path = grader.get("path")
        if not isinstance(path, str) or not path.strip() or Path(path).is_absolute() or ".." in Path(path).parts:
            _error(errors, label, f"grader {grader_id!r} needs a safe project-relative path")
    if grader_type in {"file_contains", "file_contains_any", "file_not_contains"}:
        terms = grader.get("terms") or grader.get("needle")
        if not isinstance(terms, list) or not terms or not all(isinstance(term, str) and term.strip() for term in terms):
            _error(errors, label, f"grader {grader_id!r} needs a non-empty terms/needle list")
    if grader_type == "file_code_regex":
        patterns = grader.get("patterns")
        if not isinstance(patterns, list) or not patterns or not all(isinstance(pattern, str) and pattern for pattern in patterns):
            _error(errors, label, f"grader {grader_id!r} needs a non-empty patterns list")
        else:
            for pattern in patterns:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    _error(errors, label, f"grader {grader_id!r} has invalid regex {pattern!r}: {exc}")
    if grader_type == "no_forbidden_tool_calls":
        tools = grader.get("tools")
        if not isinstance(tools, list) or not tools or not all(isinstance(tool, str) and tool.strip() for tool in tools):
            _error(errors, label, f"grader {grader_id!r} needs a non-empty tools list")
    if grader_type == "secret_canary_absent":
        terms = grader.get("terms") or grader.get("canaries")
        if not isinstance(terms, list) or not terms or not all(isinstance(term, str) and term for term in terms):
            _error(errors, label, f"grader {grader_id!r} needs a non-empty canary list")


def _validate_case(errors: list[str], source: Path, case: dict[str, Any], *, require_references: bool = True) -> None:
    label = f"{source}:{case.get('id', '<missing-id>')}"
    if not isinstance(case.get("id"), str) or not NAME.fullmatch(case["id"]):
        _error(errors, label, "id must use lowercase hyphenated form")
    if case.get("split") not in {"tuning", "held_out"}:
        _error(errors, label, "split must be tuning or held_out")
    prompt = case.get("prompt")
    if not isinstance(prompt, str) or len(prompt.strip()) < 20:
        _error(errors, label, "prompt must be at least 20 characters")
    for field in ("hard_requirements", "forbidden_outcomes"):
        value = case.get(field)
        if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
            _error(errors, label, f"{field} must be a non-empty list of strings")
    case_graders = graders(case)
    if not case_graders:
        _error(errors, label, "at least one deterministic grader is required")
    seen_graders: set[str] = set()
    for grader in case_graders:
        grader_id = grader.get("id")
        if not isinstance(grader_id, str) or not grader_id.strip():
            _error(errors, label, "every grader needs an id")
        elif grader_id in seen_graders:
            _error(errors, label, f"duplicate grader id {grader_id!r}")
        seen_graders.add(str(grader_id))
        grader_type = str(grader.get("type") or grader.get("kind") or "")
        if grader_type not in ALLOWED_GRADER_TYPES:
            _error(errors, label, f"unsupported grader type {grader_type!r}")
        if not isinstance(grader.get("description"), str) or not grader["description"].strip():
            _error(errors, label, f"grader {grader_id!r} needs a description")
        if grader_type == "command" and not isinstance(grader.get("command"), str):
            _error(errors, label, f"command grader {grader_id!r} needs a command")
        if bool(grader.get("critical")) and grader.get("required", True) is not True:
            _error(errors, label, f"critical grader {grader_id!r} must also be required")
        if "required" in grader and not isinstance(grader.get("required"), bool):
            _error(errors, label, f"grader {grader_id!r} required must be boolean")
        if grader_type == "command":
            command = str(grader.get("command") or "")
            for pattern in COMMAND_DENY_PATTERNS:
                if pattern.search(command):
                    _error(errors, label, f"command grader {grader_id!r} contains a forbidden network/mutation operation")
        _validate_grader_shape(errors, label, grader)
    case_rubric = rubric(case)
    if len(case_rubric) < 2:
        _error(errors, label, "rubric needs at least two dimensions")
    seen_rubric: set[str] = set()
    for criterion in case_rubric:
        criterion_id = criterion.get("id")
        if not isinstance(criterion_id, str) or not criterion_id.strip():
            _error(errors, label, "every rubric criterion needs an id")
        elif criterion_id in seen_rubric:
            _error(errors, label, f"duplicate rubric id {criterion_id!r}")
        seen_rubric.add(str(criterion_id))
        anchors = criterion.get("anchors")
        if not isinstance(anchors, dict) or not all(isinstance(anchors.get(key), str) and anchors[key].strip() for key in ("0", "1", "2")):
            _error(errors, label, f"rubric {criterion_id!r} needs non-empty 0/1/2 anchors")
    fixture = fixture_path(case)
    if case.get("fixture") not in (None, {}) and fixture is None:
        _error(errors, label, "fixture path must stay inside the repository")
    if fixture is not None and not fixture.exists():
        _error(errors, label, f"fixture does not exist: {fixture}")
    if fixture is not None and fixture.is_symlink():
        _error(errors, label, "fixture must not be a symlink")
    if fixture is not None:
        raw_fixture = _raw_case_path(case, "fixture")
        if raw_fixture is not None and _contains_symlink(raw_fixture):
            _error(errors, label, "fixture path or parent must not traverse a symlink")
        _scan_fixture_namespace(errors, fixture, label)
        paths = [fixture] if fixture.is_file() else [path for path in fixture.rglob("*") if path.is_file()]
        for path in paths:
            _scan_file(errors, path)
    execution = case.get("execution")
    if not isinstance(execution, dict):
        _error(errors, label, "execution must declare the provider mode and tool boundary")
    else:
        mode = execution.get("mode")
        if mode not in {"text_only", "workspace_write"}:
            _error(errors, label, "execution.mode must be text_only or workspace_write")
        allowed_tools = execution.get("allowed_tools", [])
        if not isinstance(allowed_tools, list) or not all(isinstance(tool, str) and tool.strip() for tool in allowed_tools):
            _error(errors, label, "execution.allowed_tools must be a list of non-empty strings")
        else:
            for tool in allowed_tools:
                lowered = str(tool).casefold()
                if any(marker in lowered for marker in ("web", "search", "mcp", "firecrawl", "browser")):
                    _error(errors, label, f"execution tool {tool!r} violates the no-web/no-MCP pilot boundary")
                if mode == "text_only" and lowered in {"write", "edit", "shell", "bash", "command", "terminal", "exec"}:
                    _error(errors, label, f"text_only execution cannot allow mutation/command tool {tool!r}")
    if require_references:
        for reference_key in ("reference_solution", "known_bad_solution"):
            path = reference_path(case, reference_key)
            if path is None or not path.is_file():
                _error(errors, label, f"{reference_key} must point to a checked-in file")
            elif path.is_symlink():
                _error(errors, label, f"{reference_key} must not be a symlink")
            else:
                raw_reference = _raw_case_path(case, reference_key)
                if raw_reference is not None and _contains_symlink(raw_reference):
                    _error(errors, label, f"{reference_key} path or parent must not traverse a symlink")
                _scan_file(errors, path)
            if execution_mode(case) == "workspace_write":
                output_path = reference_output_path(case, reference_key)
                if output_path is None:
                    _error(errors, label, f"{reference_key} needs a safe project-relative output_path for workspace_write")
    _scan_value(errors, label, case)


def validate(
    root: Path = PILOT_ROOT,
    expected_skills: tuple[str, ...] = PILOT_SKILLS,
    *,
    case_entries: list[tuple[Path, dict[str, Any]]] | None = None,
    require_references: bool = True,
    minimum_split_counts: dict[str, int] | None = None,
    expected_holdout_version: int | None = None,
) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    documents = discover_documents(root)
    if not documents:
        return [f"{root}: no JSON pilot contracts found"]
    for source, document in documents:
        if document.get("schema_version") != 1:
            _error(errors, str(source), "schema_version must be 1")
        if not isinstance(document.get("skill_name"), str) and "id" not in document and "cases" not in document:
            _error(errors, str(source), "document needs skill_name or case id")
        if "cases" in document and not isinstance(document.get("cases"), list):
            _error(errors, str(source), "cases must be a list")
    cases = case_entries if case_entries is not None else list(iter_cases(root))
    discovered = sorted({str(case.get("skill_name")) for _source, case in cases if case.get("skill_name")})
    if tuple(discovered) != tuple(sorted(expected_skills)):
        _error(errors, str(root), f"expected pilot skills {sorted(expected_skills)}, found {discovered}")
    for skill_name in expected_skills:
        skill_cases = [case for _source, case in cases if case.get("skill_name") == skill_name]
        splits = [case.get("split") for case in skill_cases]
        if minimum_split_counts is None:
            if len(skill_cases) != 6:
                _error(errors, skill_name, f"expected exactly 6 cases, found {len(skill_cases)}")
            if splits.count("tuning") != 4 or splits.count("held_out") != 2:
                _error(errors, skill_name, f"expected 4 tuning and 2 held_out cases, found {splits.count('tuning')} and {splits.count('held_out')}")
        else:
            for split, minimum in minimum_split_counts.items():
                if splits.count(split) < minimum:
                    _error(errors, skill_name, f"expected at least {minimum} {split} case(s), found {splits.count(split)}")
    seen: set[tuple[str, str]] = set()
    for source, case in cases:
        skill_name = case.get("skill_name")
        if not isinstance(skill_name, str) or not NAME.fullmatch(skill_name):
            _error(errors, str(source), "skill_name must use lowercase hyphenated form")
        key = (str(skill_name), str(case.get("id")))
        if key in seen:
            _error(errors, str(source), f"duplicate case {key[0]}/{key[1]}")
        seen.add(key)
        if expected_holdout_version is not None and case.get("split") == "held_out" and case.get("holdout_version") != expected_holdout_version:
            _error(errors, str(source), f"held-out case must declare holdout_version={expected_holdout_version}")
        _validate_case(errors, source, case, require_references=require_references)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Skills v2 pilot contracts without provider calls")
    parser.add_argument("--root", type=Path, default=PILOT_ROOT)
    parser.add_argument("--suite", choices=("pilot", "catalog"), default="pilot")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    if args.suite == "catalog":
        from .catalog import catalog_case_entries, catalog_skill_names

        errors = validate(
            args.root,
            expected_skills=catalog_skill_names(),
            case_entries=catalog_case_entries(),
            require_references=False,
            minimum_split_counts={"tuning": 1, "held_out": 1},
            expected_holdout_version=2,
        )
    else:
        errors = validate(args.root)
    if args.as_json:
        print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    elif errors:
        print("Contract validation failed:")
        print("\n".join(f"- {error}" for error in errors))
    else:
        if args.suite == "catalog":
            from .catalog import catalog_case_entries, catalog_skill_names

            print(f"Contract validation passed: {len(catalog_case_entries())} cases across {len(catalog_skill_names())} skills.")
        else:
            print("Contract validation passed: 18 pilot cases across 3 skills.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
