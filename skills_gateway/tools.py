import json
from pathlib import Path

from fastmcp import FastMCP

from skills_gateway.skills import get_skills_catalog, parse_skill_frontmatter, get_skill_file_tree
from skills_gateway.config import GatewayConfig
from skills_gateway.metrics import metrics
from skills_gateway.logging import log_event, new_request_id


def register_tools(mcp: FastMCP, skills_dir: Path, cfg: GatewayConfig):
    @mcp.tool()
    async def skills_search(query: str) -> str:
        """Search skills by name and description. Returns ranked matches with scores."""
        request_id = new_request_id()
        metrics.inc_counter("skill_searches_total")
        log_event("skill_search", f"Searching skills: query={query!r}", request_id=request_id, query=query)
        catalog = get_skills_catalog(skills_dir)
        if cfg.active_profile and cfg.active_profile in cfg.profiles:
            allowed = set(cfg.profiles[cfg.active_profile].skills)
            catalog = [s for s in catalog if s["name"] in allowed]
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
        ranked = []
        for score, skill in results:
            ranked.append({
                "name": skill["name"],
                "description": skill["description"],
                "version": skill.get("version", ""),
                "score": score,
            })
        return json.dumps(ranked, indent=2)

    @mcp.tool()
    async def skills_inspect(name: str) -> str:
        """Get full metadata and file tree for a single skill."""
        request_id = new_request_id()
        metrics.inc_counter("skill_inspects_total")
        log_event("skill_inspect", f"Inspecting skill: {name}", request_id=request_id, skill_name=name)
        if cfg.active_profile and cfg.active_profile in cfg.profiles:
            allowed = set(cfg.profiles[cfg.active_profile].skills)
            if name not in allowed:
                return json.dumps({"error": f"Skill '{name}' not in active profile '{cfg.active_profile}'"})
        skill_dir = skills_dir / name
        if not skill_dir.exists() or not skill_dir.is_dir():
            return json.dumps({"error": f"Skill '{name}' not found"})
        frontmatter = parse_skill_frontmatter(skill_dir)
        if not frontmatter:
            return json.dumps({"error": f"Skill '{name}' has no valid SKILL.md"})
        tree = get_skill_file_tree(skill_dir)
        result = {
            "metadata": frontmatter,
            "file_tree": tree,
        }
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def skills_list() -> str:
        """List all available skills with full metadata."""
        request_id = new_request_id()
        metrics.inc_counter("skill_lists_total")
        log_event("skill_list", "Listing skills", request_id=request_id, profile=cfg.active_profile)
        catalog = get_skills_catalog(skills_dir)
        if cfg.active_profile and cfg.active_profile in cfg.profiles:
            allowed = set(cfg.profiles[cfg.active_profile].skills)
            catalog = [s for s in catalog if s["name"] in allowed]
        return json.dumps(catalog, indent=2)

    @mcp.tool()
    async def skill_read(path: str) -> str:
        """Read an individual skill file by its path relative to the skills directory. Use skills_inspect first to discover the file tree, then read specific files. Path must not contain '..' or start with '/'."""
        request_id = new_request_id()
        metrics.inc_counter("skill_reads_total")
        log_event("skill_read", f"Reading skill file: {path}", request_id=request_id, path=path)
        if ".." in path.split("/") or path.startswith("/"):
            return json.dumps({"error": "Invalid path"})
        file_path = skills_dir / path
        if not file_path.exists() or not file_path.is_file():
            return json.dumps({"error": f"File '{path}' not found"})
        return file_path.read_bytes().decode("utf-8", errors="replace")
