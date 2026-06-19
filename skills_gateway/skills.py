import re
from pathlib import Path

import yaml


def parse_skill_frontmatter(skill_dir: Path) -> dict | None:
    md_file = skill_dir / "SKILL.md"
    if not md_file.exists():
        return None
    content = md_file.read_text(encoding="utf-8")
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def get_skills_catalog(skills_dir: Path) -> list[dict]:
    catalog = []
    if not skills_dir.exists():
        return catalog
    for entry in sorted(skills_dir.iterdir()):
        if entry.is_dir():
            frontmatter = parse_skill_frontmatter(entry)
            if frontmatter and frontmatter.get("name"):
                catalog.append({
                    "name": frontmatter["name"],
                    "description": frontmatter.get("description", ""),
                    "version": frontmatter.get("metadata", {}).get("version", ""),
                    "license": frontmatter.get("license", ""),
                    "compatibility": frontmatter.get("compatibility", ""),
                    "allowed_tools": frontmatter.get("allowed-tools", ""),
                    "path": str(entry.relative_to(skills_dir)),
                    "metadata": frontmatter.get("metadata", {}),
                })
    return catalog


REQUIRED_FIELDS = ("name", "description")
RECOMMENDED_FIELDS = ("allowed-tools", "tags", "author", "license", "compatibility")
REQUIRED_METADATA = ("version",)


def validate_skills(skills_dir: Path) -> list[str]:
    errors = []
    warnings = []
    if not skills_dir.exists():
        return errors
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not (entry / "SKILL.md").exists():
            continue
        frontmatter = parse_skill_frontmatter(entry)
        if frontmatter is None:
            errors.append(f"{entry.name}: invalid SKILL.md — could not parse YAML frontmatter")
            continue
        for field in REQUIRED_FIELDS:
            if not frontmatter.get(field):
                errors.append(f"{entry.name}: missing required field '{field}' in frontmatter")
        metadata = frontmatter.get("metadata", {})
        if isinstance(metadata, dict):
            if not metadata.get("version"):
                errors.append(f"{entry.name}: missing required field 'metadata.version' in frontmatter")
        for field in RECOMMENDED_FIELDS:
            if field not in frontmatter:
                warnings.append(f"{entry.name}: missing recommended field '{field}' in frontmatter")
        risk = frontmatter.get("risk_level")
        if risk and risk not in ("low", "medium", "high"):
            errors.append(f"{entry.name}: invalid risk_level '{risk}' (must be low, medium, or high)")
    return errors + warnings


def get_skill_file_tree(skill_dir: Path) -> list[str]:
    files = []
    if not skill_dir.exists():
        return files
    for f in sorted(skill_dir.rglob("*")):
        if f.is_file():
            files.append(str(f.relative_to(skill_dir)))
    return files
