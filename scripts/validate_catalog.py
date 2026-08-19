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

    cases = json.loads((ROOT / "evals/cases/catalog.json").read_text())
    if not isinstance(cases, list) or not cases:
        fail("Inspect dataset must be a non-empty JSON array")
    case_ids: set[str] = set()
    for case in cases:
        case_id = case.get("id") if isinstance(case, dict) else None
        if not isinstance(case_id, str) or not NAME.fullmatch(case_id) or case_id in case_ids:
            fail(f"invalid or duplicate eval case id: {case_id!r}")
        if not all(isinstance(case.get(key), str) and case[key].strip() for key in ("input", "target")):
            fail(f"eval case {case_id} needs input and target")
        metadata = case.get("metadata")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("allow_changes"), bool):
            fail(f"eval case {case_id} needs explicit allow_changes")
        case_ids.add(case_id)

    print(f"validated {len(skill_files)} skills and {len(cases)} Inspect cases")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
