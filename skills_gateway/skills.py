import re
from pathlib import Path
from typing import Any

import yaml


VALID_RISK_LEVELS = ("low", "medium", "high")
REQUIRED_FIELDS = ("name", "description")
RECOMMENDED_FIELDS = ("allowed-tools", "tags", "author", "license", "compatibility")
REQUIRED_METADATA = ("version",)


def parse_skill_frontmatter(skill_dir: Path) -> dict | None:
    md_file = skill_dir / "SKILL.md"
    if not md_file.exists():
        return None
    content = md_file.read_text(encoding="utf-8")
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _version_from_frontmatter(frontmatter: dict[str, Any]) -> str:
    version = frontmatter.get("version")
    if version:
        return str(version)
    metadata = frontmatter.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("version"):
        return str(metadata["version"])
    return ""


def normalize_skill_manifest(skill_dir: Path, frontmatter: dict[str, Any]) -> dict[str, Any]:
    """Normalize SKILL.md frontmatter into the canonical skill manifest shape.

    Backward compatibility:
    - `id` defaults to the skill directory name.
    - `entrypoint` defaults to `SKILL.md`.
    - `version` may be top-level or `metadata.version`.
    """
    metadata = frontmatter.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    entrypoint = str(frontmatter.get("entrypoint") or "SKILL.md")
    return {
        "id": str(frontmatter.get("id") or skill_dir.name),
        "name": frontmatter.get("name", ""),
        "description": frontmatter.get("description", ""),
        "version": _version_from_frontmatter(frontmatter),
        "entrypoint": entrypoint,
        "license": frontmatter.get("license", ""),
        "compatibility": frontmatter.get("compatibility", ""),
        "allowed_tools": frontmatter.get("allowed-tools", []),
        "risk_level": frontmatter.get("risk_level", "low"),
        "tags": frontmatter.get("tags", []),
        "files": frontmatter.get("files", []),
        "inputs": frontmatter.get("inputs", {}),
        "outputs": frontmatter.get("outputs", {}),
        "permissions": frontmatter.get("permissions", {}),
        "author": frontmatter.get("author", ""),
        "path": skill_dir.name,
        "metadata": metadata,
    }


def get_skills_catalog(skills_dir: Path) -> list[dict]:
    catalog = []
    if not skills_dir.exists():
        return catalog
    for entry in sorted(skills_dir.iterdir()):
        if entry.is_dir():
            frontmatter = parse_skill_frontmatter(entry)
            if frontmatter and frontmatter.get("name"):
                catalog.append(normalize_skill_manifest(entry, frontmatter))
    return catalog


def validate_skills(skills_dir: Path) -> dict[str, list[str]]:
    errors = []
    warnings = []
    if not skills_dir.exists():
        return {"errors": errors, "warnings": warnings}
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not (entry / "SKILL.md").exists():
            continue
        frontmatter = parse_skill_frontmatter(entry)
        if frontmatter is None:
            errors.append(f"{entry.name}: invalid SKILL.md — could not parse YAML frontmatter")
            continue

        manifest = normalize_skill_manifest(entry, frontmatter)

        for field in REQUIRED_FIELDS:
            if not manifest.get(field):
                errors.append(f"{entry.name}: missing required field '{field}' in frontmatter")

        explicit_id = frontmatter.get("id")
        if explicit_id and explicit_id != entry.name:
            errors.append(f"{entry.name}: id '{explicit_id}' must match skill directory name '{entry.name}'")

        if not manifest["version"]:
            errors.append(f"{entry.name}: missing required field 'metadata.version' or 'version' in frontmatter")

        entrypoint = manifest["entrypoint"]
        if not (entry / entrypoint).exists():
            errors.append(f"{entry.name}: entrypoint '{entrypoint}' does not exist")

        files = manifest.get("files", [])
        if files and not isinstance(files, list):
            errors.append(f"{entry.name}: field 'files' must be a list")
            files = []
        for listed_file in files:
            if not isinstance(listed_file, str):
                errors.append(f"{entry.name}: field 'files' entries must be strings")
                continue
            if not (entry / listed_file).exists():
                errors.append(f"{entry.name}: listed file '{listed_file}' does not exist")

        for field in RECOMMENDED_FIELDS:
            if field not in frontmatter:
                warnings.append(f"{entry.name}: missing recommended field '{field}' in frontmatter")

        risk = manifest.get("risk_level")
        if risk and risk not in VALID_RISK_LEVELS:
            errors.append(f"{entry.name}: invalid risk_level '{risk}' (must be low, medium, or high)")
    return {"errors": errors, "warnings": warnings}


def get_skill_file_tree(skill_dir: Path) -> list[str]:
    files = []
    if not skill_dir.exists():
        return files
    for f in sorted(skill_dir.rglob("*")):
        if f.is_file():
            files.append(str(f.relative_to(skill_dir)))
    return files
