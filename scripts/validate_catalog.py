#!/usr/bin/env python3
"""Deterministic catalog and skill structure validation."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK = re.compile(r"\[[^]]*\]\(([^)]+)\)")
PLAYBOOK_NAMES = {
    "investigate.md",
    "design.md",
    "implement.md",
    "performance.md",
    "migrate-operate.md",
    "review.md",
    "issues.md",
    "document-teach.md",
    "custom.md",
    "parallel.md",
}
PLAYBOOK_SECTIONS = (
    "## When",
    "## Inputs to establish",
    "## Steps and decision points",
    "## Failure and recovery",
    "## Completion evidence",
    "## Example",
    "## Near-miss",
)
WORKFLOW_ROUTES = {
    "investigate/read",
    "design/plan",
    "design/prototype",
    "implement/bug",
    "implement/feature",
    "implement/refactor",
    "performance/measure",
    "performance/improve",
    "migrate-operate/upgrade",
    "migrate-operate/migrate",
    "migrate-operate/release",
    "migrate-operate/incident",
    "review/review",
    "review/rereview",
    "issues/draft",
    "issues/create",
    "issues/update",
    "issues/triage",
    "pull-requests/draft",
    "pull-requests/create",
    "pull-requests/monitor",
    "pull-requests/communicate",
    "document-teach/document",
    "document-teach/teach",
    "workflow-improvement/improve",
    "custom/compose",
}


def fail(message: str) -> None:
    raise ValueError(message)


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        fail(f"missing YAML frontmatter: {path.relative_to(ROOT)}")
    value = yaml.safe_load(match.group(1))
    if not isinstance(value, dict):
        fail(f"frontmatter is not a mapping: {path.relative_to(ROOT)}")
    return value


def validate_links(path: Path) -> None:
    for raw in LINK.findall(path.read_text()):
        target = raw.split("#", 1)[0]
        if not target or "://" in target or target.startswith("#"):
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(ROOT)
        except ValueError:
            fail(f"link escapes repository in {path.relative_to(ROOT)}: {raw}")
        if not resolved.exists():
            fail(f"broken link in {path.relative_to(ROOT)}: {raw}")


def main() -> None:
    catalog = yaml.safe_load((ROOT / "catalog.yaml").read_text())
    entries = catalog.get("skills") if isinstance(catalog, dict) else None
    if not isinstance(entries, list):
        fail("catalog.yaml needs a skills list")

    skill_files = sorted(SKILLS.glob("*/SKILL.md"))
    if len(entries) != len(skill_files):
        fail(f"catalog has {len(entries)} skills but filesystem has {len(skill_files)}")

    names: set[str] = set()
    catalog_paths = {entry.get("exported_path") for entry in entries}
    for skill_file in skill_files:
        data = frontmatter(skill_file)
        name = data.get("name")
        description = data.get("description")
        if not isinstance(name, str) or not NAME.fullmatch(name):
            fail(f"invalid skill name in {skill_file.relative_to(ROOT)}")
        if name != skill_file.parent.name or name in names or len(name) > 64:
            fail(f"duplicate or mismatched skill name: {name}")
        if not isinstance(description, str) or not 1 <= len(description) <= 1024:
            fail(f"invalid description for {name}")
        names.add(name)
        relative = str(skill_file.relative_to(ROOT))
        if relative not in catalog_paths:
            fail(f"skill missing from catalog: {relative}")

    for path in ROOT.glob("skills/**/*.md"):
        validate_links(path)

    coordinator = SKILLS / "follow-instructions"
    playbooks = {path.name for path in (coordinator / "playbooks").glob("*.md")}
    if playbooks != PLAYBOOK_NAMES:
        fail(
            "follow-instructions playbooks must be exactly "
            f"{sorted(PLAYBOOK_NAMES)}, found {sorted(playbooks)}"
        )
    for name in sorted(PLAYBOOK_NAMES):
        path = coordinator / "playbooks" / name
        text = path.read_text()
        missing_sections = [section for section in PLAYBOOK_SECTIONS if section not in text]
        if missing_sections:
            fail(f"playbook {path.relative_to(ROOT)} missing sections: {missing_sections}")

    cases = json.loads((ROOT / "evals/cases/catalog.json").read_text())
    if not isinstance(cases, list) or not cases:
        fail("Inspect dataset must be a non-empty JSON array")
    case_ids: set[str] = set()
    covered_skills: set[str] = set()
    for case in cases:
        case_id = case.get("id") if isinstance(case, dict) else None
        if not isinstance(case_id, str) or not NAME.fullmatch(case_id) or case_id in case_ids:
            fail(f"invalid or duplicate eval case id: {case_id!r}")
        if not all(isinstance(case.get(key), str) and case[key].strip() for key in ("input", "target")):
            fail(f"eval case {case_id} needs input and target")
        metadata = case.get("metadata")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("allow_changes"), bool):
            fail(f"eval case {case_id} needs explicit allow_changes")
        skill = metadata.get("skill")
        if not isinstance(skill, str) or skill not in names:
            fail(f"eval case {case_id} names an unknown skill: {skill!r}")
        if skill in covered_skills:
            fail(f"skill has more than one primary eval case: {skill}")
        covered_skills.add(skill)
        case_ids.add(case_id)

    missing_coverage = names - covered_skills
    if missing_coverage:
        fail(f"skills missing primary eval coverage: {sorted(missing_coverage)}")

    routing_path = ROOT / "evals/cases/routing.json"
    routing_cases = json.loads(routing_path.read_text())
    if not isinstance(routing_cases, list) or not routing_cases:
        fail("routing eval dataset must be a non-empty JSON array")
    routing_ids: set[str] = set()
    for case in routing_cases:
        case_id = case.get("id") if isinstance(case, dict) else None
        if not isinstance(case_id, str) or not NAME.fullmatch(case_id) or case_id in routing_ids:
            fail(f"invalid or duplicate routing case id: {case_id!r}")
        if not isinstance(case.get("input"), str) or not case["input"].strip():
            fail(f"routing case {case_id} needs input")
        metadata = case.get("metadata")
        expected = metadata.get("expected_skills") if isinstance(metadata, dict) else None
        if not isinstance(expected, list) or not all(
            isinstance(skill, str) and skill in names for skill in expected
        ):
            fail(f"routing case {case_id} needs known expected_skills")
        if metadata.get("route_kind") not in {"positive", "negative"}:
            fail(f"routing case {case_id} needs route_kind")
        routing_ids.add(case_id)

    workflows_path = ROOT / "evals/cases/workflows.json"
    workflow_cases = json.loads(workflows_path.read_text())
    if not isinstance(workflow_cases, list) or not workflow_cases:
        fail("workflow eval dataset must be a non-empty JSON array")
    workflow_ids: set[str] = set()
    for case in workflow_cases:
        case_id = case.get("id") if isinstance(case, dict) else None
        if not isinstance(case_id, str) or not NAME.fullmatch(case_id) or case_id in workflow_ids:
            fail(f"invalid or duplicate workflow case id: {case_id!r}")
        if not all(isinstance(case.get(key), str) and case[key].strip() for key in ("input", "target")):
            fail(f"workflow case {case_id} needs input and target")
        metadata = case.get("metadata")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("allow_changes"), bool):
            fail(f"workflow case {case_id} needs explicit allow_changes")
        expected_skills = metadata.get("expected_skills")
        if not isinstance(expected_skills, list) or not all(
            isinstance(skill, str) and skill in names for skill in expected_skills
        ):
            fail(f"workflow case {case_id} needs known expected_skills")
        optional_skills = metadata.get("optional_skills", [])
        if not isinstance(optional_skills, list) or not all(
            isinstance(skill, str) and skill in names for skill in optional_skills
        ):
            fail(f"workflow case {case_id} has invalid optional_skills")
        if set(expected_skills) & set(optional_skills):
            fail(f"workflow case {case_id} repeats a required skill as optional")
        expected_production = metadata.get("expected_production", "none")
        if expected_production not in {"none", "read", "write"}:
            fail(f"workflow case {case_id} has invalid expected_production")
        expected_workflows = metadata.get("expected_workflows")
        if not isinstance(expected_workflows, list) or not expected_workflows or not all(
            isinstance(route, str) and route in WORKFLOW_ROUTES
            for route in expected_workflows
        ):
            fail(f"workflow case {case_id} needs known expected_workflows")
        modifiers = metadata.get("expected_modifiers")
        if not isinstance(modifiers, list) or not all(
            modifier == "parallel" for modifier in modifiers
        ):
            fail(f"workflow case {case_id} has invalid expected_modifiers")
        for field in ("forbidden_effects", "required_observations"):
            values = metadata.get(field)
            if not isinstance(values, list) or not values or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                fail(f"workflow case {case_id} needs non-empty {field}")
        files = case.get("files", {})
        if not isinstance(files, dict) or not all(
            isinstance(path, str) and path and isinstance(content, str)
            for path, content in files.items()
        ):
            fail(f"workflow case {case_id} has invalid fixture files")
        execution_mode = metadata.get("execution_mode")
        if execution_mode not in {"routing-only", "execution-ready"}:
            fail(
                f"workflow case {case_id} needs execution_mode routing-only or execution-ready"
            )
        if execution_mode == "execution-ready" and not files:
            fail(f"execution-ready workflow case {case_id} has no fixture inputs")
        if execution_mode == "routing-only" and files:
            fail(f"routing-only workflow case {case_id} supplies executable files")
        contract = metadata.get("fixture_contract")
        if contract is not None:
            if execution_mode != "execution-ready" or not isinstance(contract, dict):
                fail(f"workflow case {case_id} has an invalid fixture contract")
        setup = case.get("setup")
        if setup is not None and (not isinstance(setup, str) or not setup.strip()):
            fail(f"workflow case {case_id} has invalid setup")
        workflow_ids.add(case_id)

    print(
        f"validated {len(skill_files)} skills, {len(cases)} behavior cases, "
        f"{len(routing_cases)} routing cases, and {len(workflow_cases)} workflow cases"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
