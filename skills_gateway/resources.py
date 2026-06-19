import json
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.resources import FunctionResource

from skills_gateway.skills import get_skills_catalog

import logging

logger = logging.getLogger("skills-gateway")


def register_resources(mcp: FastMCP, skills_dir: Path):
    @mcp.resource("skill://index.json")
    async def skill_index() -> str:
        return json.dumps(get_skills_catalog(skills_dir), indent=2)

    registered = 0
    if skills_dir.exists():
        for file_path in sorted(skills_dir.rglob("*")):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(skills_dir)
            uri = f"skill://{rel}"
            p = file_path

            def make_reader(path):
                return lambda: path.read_bytes().decode("utf-8", errors="replace")

            resource = FunctionResource(
                uri=uri,
                name=rel.name,
                mime_type="text/plain",
                fn=make_reader(p),
            )
            mcp.add_resource(resource)
            registered += 1
    logger.info("Registered %d skill file resources", registered)
