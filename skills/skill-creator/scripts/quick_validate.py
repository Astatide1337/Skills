#!/usr/bin/env python3
"""Validate one Agent Skill directory without running bundled code."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


ALLOWED_FRONTMATTER = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}


def validate_skill(raw_path: str | Path) -> tuple[bool, str]:
    skill_path = Path(raw_path)
    skill_md = skill_path / "SKILL.md"
    if not skill_md.is_file():
        return False, "SKILL.md not found"

    content = skill_md.read_text()
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", content, re.DOTALL)
    if not match:
        return False, "Invalid or missing YAML frontmatter"
    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return False, f"Invalid YAML frontmatter: {exc}"
    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be a mapping"

    unexpected = set(frontmatter) - ALLOWED_FRONTMATTER
    if unexpected:
        return False, f"Unexpected frontmatter keys: {', '.join(sorted(unexpected))}"

    name = frontmatter.get("name")
    description = frontmatter.get("description")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        return False, "name must be lowercase hyphen-case"
    if name != skill_path.name:
        return False, f"name {name!r} must match directory {skill_path.name!r}"
    if len(name) > 64:
        return False, "name exceeds 64 characters"
    if not isinstance(description, str) or not description.strip():
        return False, "description must be a non-empty string"
    if len(description) > 1024 or "<" in description or ">" in description:
        return False, "description exceeds limits or contains angle brackets"

    compatibility = frontmatter.get("compatibility")
    if compatibility is not None and (
        not isinstance(compatibility, str) or len(compatibility) > 500
    ):
        return False, "compatibility must be a string of at most 500 characters"

    for resource in ("scripts", "references", "assets", "agents"):
        directory = skill_path / resource
        if directory.exists() and any(path.is_symlink() for path in directory.rglob("*")):
            return False, f"symlinked resource found under {resource}"

    return True, "Skill is valid!"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: quick_validate.py <skill-directory>")
        raise SystemExit(2)
    valid, message = validate_skill(sys.argv[1])
    print(message)
    raise SystemExit(0 if valid else 1)
