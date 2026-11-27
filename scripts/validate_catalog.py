#!/usr/bin/env python3
"""Deterministic catalog and skill structure validation."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK = re.compile(r"\[[^]]*\]\(([^)]+)\)")
INLINE_MARKDOWN_PATH = re.compile(r"`([^`\n ]+\.md)(?:#[^`\n ]*)?`")
# Local routing budget (harness limit is 1,024). Room for what + when + key
# terms while keeping always-visible catalog metadata compact.
MAX_DESCRIPTION_CHARS = 200
PLAYBOOK_NAMES = {
    "investigate.md",
    "design.md",
    "implement.md",
    "performance.md",
    "migrate-operate.md",
    "review.md",
    "issues.md",
    "document-teach.md",
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
    "verify-work/verify",
}


def fail(message: str) -> None:
    raise ValueError(message)


def validate_description(name: str, description: object) -> None:
    if (not isinstance(description, str) or not description.strip()
            or len(description) > MAX_DESCRIPTION_CHARS
            or "\n" in description or "\r" in description):
        fail(
            f"description for {name} must be a non-empty, single-line trigger "
            f"of at most {MAX_DESCRIPTION_CHARS} characters"
        )


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


def validate_reference_routes(skill_dir: Path) -> None:
    """Every bundled Markdown reference needs a route from its skill entry."""
    owner = skill_dir.resolve()
    pending = [owner / "SKILL.md"]
    reached: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in reached:
            continue
        reached.add(path)
        text = path.read_text()
        for raw in LINK.findall(text) + INLINE_MARKDOWN_PATH.findall(text):
            target = (path.parent / raw.split("#", 1)[0]).resolve()
            if (target.is_relative_to(owner) and target.is_file()
                    and target.suffix == ".md"):
                pending.append(target)
    missing = {path.resolve() for path in owner.rglob("*.md")} - reached
    if missing:
        fail(f"unreachable Markdown in {owner.name}: "
             + ", ".join(str(path.relative_to(owner)) for path in sorted(missing)))


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
        validate_description(name, description)
        names.add(name)
        relative = str(skill_file.relative_to(ROOT))
        if relative not in catalog_paths:
            fail(f"skill missing from catalog: {relative}")

    for path in ROOT.glob("skills/**/*.md"):
        validate_links(path)
    for skill_file in skill_files:
        validate_reference_routes(skill_file.parent)

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

    print(f"validated {len(skill_files)} skills")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
