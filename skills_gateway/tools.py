import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from skills_gateway.skills import get_skills_catalog, parse_skill_frontmatter, get_skill_file_tree, normalize_skill_manifest
from skills_gateway.config import GatewayConfig
from skills_gateway.metrics import metrics
from skills_gateway.logging import log_event, new_request_id


def _profile_allowed_skill_ids(cfg: GatewayConfig) -> set[str] | None:
    if cfg.active_profile and cfg.active_profile in cfg.profiles:
        return set(cfg.profiles[cfg.active_profile].skills)
    return None


def _filter_catalog_for_profile(catalog: list[dict], cfg: GatewayConfig) -> list[dict]:
    allowed = _profile_allowed_skill_ids(cfg)
    if allowed is None:
        return catalog
    return [s for s in catalog if s["id"] in allowed]


def _json_error(code: str, message: str) -> str:
    return json.dumps({"error": {"code": code, "message": message}})


def list_skill_manifests(skills_dir: Path, cfg: GatewayConfig) -> list[dict[str, Any]]:
    return _filter_catalog_for_profile(get_skills_catalog(skills_dir), cfg)


def search_skill_manifests(skills_dir: Path, cfg: GatewayConfig, query: str) -> list[dict[str, Any]]:
    catalog = list_skill_manifests(skills_dir, cfg)
    results = []
    query_lower = query.lower()
    for skill in catalog:
        name = skill.get("name", "")
        desc = skill.get("description", "")
        score = 0
        if query_lower in name.lower():
            score += 10
        if query_lower in desc.lower():
            score += 5
        if name.lower().startswith(query_lower):
            score += 3
        if desc.lower().startswith(query_lower):
            score += 2
        if score > 0:
            results.append((score, skill))
    results.sort(key=lambda x: -x[0])
    return [
        {
            "id": skill["id"],
            "name": skill["name"],
            "description": skill["description"],
            "version": skill.get("version", ""),
            "path": skill.get("path", skill["id"]),
            "risk_level": skill.get("risk_level", "low"),
            "score": score,
        }
        for score, skill in results
    ]


def inspect_skill_manifest(skills_dir: Path, cfg: GatewayConfig, name: str) -> dict[str, Any]:
    allowed = _profile_allowed_skill_ids(cfg)
    if allowed is not None and name not in allowed:
        return {"error": {"code": "not_in_active_profile", "message": f"Skill '{name}' not in active profile '{cfg.active_profile}'"}}
    skill_dir = skills_dir / name
    if not skill_dir.exists() or not skill_dir.is_dir():
        return {"error": {"code": "not_found", "message": f"Skill '{name}' not found"}}
    frontmatter = parse_skill_frontmatter(skill_dir)
    if not frontmatter:
        return {"error": {"code": "invalid_skill", "message": f"Skill '{name}' has no valid SKILL.md"}}
    return {
        "manifest": normalize_skill_manifest(skill_dir, frontmatter),
        "metadata": frontmatter,
        "file_tree": get_skill_file_tree(skill_dir),
    }


def read_skill_file(skills_dir: Path, cfg: GatewayConfig, path: str) -> str:
    if ".." in path.split("/") or path.startswith("/"):
        return _json_error("invalid_path", "Invalid path")
    parts = [part for part in path.split("/") if part]
    if not parts:
        return _json_error("invalid_path", "Invalid path")
    skill_id = parts[0]
    allowed = _profile_allowed_skill_ids(cfg)
    if allowed is not None and skill_id not in allowed:
        return _json_error("not_in_active_profile", f"Skill '{skill_id}' not in active profile '{cfg.active_profile}'")
    file_path = skills_dir / path
    try:
        resolved_file = file_path.resolve()
        resolved_skills_dir = skills_dir.resolve()
        resolved_file.relative_to(resolved_skills_dir)
    except (ValueError, OSError):
        return _json_error("invalid_path", "Invalid path")
    if not file_path.exists() or not file_path.is_file():
        return _json_error("not_found", f"File '{path}' not found")
    return file_path.read_bytes().decode("utf-8", errors="replace")


def register_tools(mcp: FastMCP, skills_dir: Path, cfg: GatewayConfig):
    @mcp.tool()
    async def skills_search(query: str) -> str:
        """Search skills by name and description. Returns ranked matches with scores."""
        request_id = new_request_id()
        metrics.inc_counter("skill_searches_total")
        log_event("skill_search", f"Searching skills: query={query!r}", request_id=request_id, query=query)
        return json.dumps(search_skill_manifests(skills_dir, cfg, query), indent=2)

    @mcp.tool()
    async def skills_inspect(name: str) -> str:
        """Get full metadata and file tree for a single skill."""
        request_id = new_request_id()
        metrics.inc_counter("skill_inspects_total")
        log_event("skill_inspect", f"Inspecting skill: {name}", request_id=request_id, skill_name=name)
        return json.dumps(inspect_skill_manifest(skills_dir, cfg, name), indent=2)

    @mcp.tool()
    async def skills_list() -> str:
        """List all available skills with full metadata."""
        request_id = new_request_id()
        metrics.inc_counter("skill_lists_total")
        log_event("skill_list", "Listing skills", request_id=request_id, profile=cfg.active_profile)
        return json.dumps(list_skill_manifests(skills_dir, cfg), indent=2)

    @mcp.tool()
    async def skill_read(path: str) -> str:
        """Read an individual skill file by its path relative to the skills directory. Use skills_inspect first to discover the file tree, then read specific files. Path must not contain '..' or start with '/'."""
        request_id = new_request_id()
        metrics.inc_counter("skill_reads_total")
        log_event("skill_read", f"Reading skill file: {path}", request_id=request_id, path=path)
        return read_skill_file(skills_dir, cfg, path)
