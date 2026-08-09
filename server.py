from __future__ import annotations

import hmac
import os
import re
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, TokenVerifier
from starlette.responses import JSONResponse
import yaml


SKILLS_DIR = Path("/skills").resolve()
PORT = 8091
VERSION = "0.3.0"
CATALOG_PATH = Path("/app/catalog.yaml")
AUTH_TOKEN_ENV = "SKILLS_GATEWAY_AUTH_TOKEN"


def gateway_auth_token() -> str:
    token = os.environ.get(AUTH_TOKEN_ENV, "")
    if len(token) < 32:
        raise RuntimeError(f"{AUTH_TOKEN_ENV} must contain at least 32 characters")
    if token != token.strip() or any(character.isspace() for character in token):
        raise RuntimeError(f"{AUTH_TOKEN_ENV} must not contain whitespace")
    return token


class GatewayTokenVerifier(TokenVerifier):
    """Constant-time verifier for the portal-to-origin bearer credential."""

    def __init__(self, expected_token: str):
        super().__init__(required_scopes=["skills:read"])
        self._expected_token = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(token, self._expected_token):
            return None
        return AccessToken(
            token=token,
            client_id="skills-gateway-client",
            subject="skills-gateway-client",
            scopes=["skills:read"],
        )


def catalog_lock() -> dict:
    if not CATALOG_PATH.is_file():
        return {}
    value = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def skill_records() -> dict[str, dict]:
    return {
        str(record.get("exported_path")): record
        for record in catalog_lock().get("skills", [])
        if isinstance(record, dict) and record.get("exported_path")
    }


def frontmatter(skill_dir: Path) -> dict | None:
    path = skill_dir / "SKILL.md"
    if not path.is_file():
        return None
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", path.read_text(encoding="utf-8"), re.DOTALL)
    if not match:
        return None
    value = yaml.safe_load(match.group(1))
    return value if isinstance(value, dict) else None


def catalog() -> list[dict]:
    records = skill_records()
    entries = []
    for skill_file in sorted(SKILLS_DIR.rglob("SKILL.md") if SKILLS_DIR.is_dir() else []):
        if any(part.startswith(".") for part in skill_file.parts):
            continue
        directory = skill_file.parent
        metadata = frontmatter(directory)
        relative = str(skill_file.relative_to(SKILLS_DIR))
        record = records.get(f"skills/{relative}", {})
        if metadata and metadata.get("name"):
            skill_metadata = metadata.get("metadata", {})
            if not isinstance(skill_metadata, dict):
                skill_metadata = {}
            entries.append({
                "id": str(directory.relative_to(SKILLS_DIR)),
                "name": metadata["name"],
                "description": metadata.get("description", ""),
                "version": str(skill_metadata.get("version", metadata.get("version", ""))),
                "path": relative,
                "risk_level": metadata.get("risk_level", "low"),
                "profile": record.get("profile", "unclassified"),
                "trust": record.get("trust", "unclassified"),
                "source": record.get("source", {}),
            })
    return entries


def safe_skill_file(relative_path: str) -> Path | None:
    if not relative_path or relative_path.startswith("/") or ".." in Path(relative_path).parts:
        return None
    candidate = (SKILLS_DIR / relative_path).resolve()
    try:
        candidate.relative_to(SKILLS_DIR)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


mcp = FastMCP("Astatide Skills Gateway", auth=GatewayTokenVerifier(gateway_auth_token()))


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    return JSONResponse({"status": "ok", "skills": len(catalog()), "version": VERSION})


@mcp.custom_route("/version", methods=["GET"])
async def version(_request):
    return JSONResponse({"name": "astatide-skills-gateway", "version": VERSION})


@mcp.tool()
async def skills_list() -> list[dict]:
    """List the committed skills available from this gateway."""
    return catalog()


@mcp.tool()
async def skills_search(query: str) -> list[dict]:
    """Search skill names and descriptions using a deterministic substring match."""
    query = query.casefold()
    return [entry for entry in catalog() if query in (entry["name"] + " " + entry["description"]).casefold()]


@mcp.tool()
async def skills_inspect(name: str) -> dict:
    """Return a skill manifest and its committed file list."""
    candidates = [entry for entry in catalog() if entry["id"] == name or entry["name"] == name]
    if not candidates:
        return {"error": "skill_not_found"}
    entry = candidates[0]
    directory = SKILLS_DIR / Path(entry["path"]).parent
    metadata = frontmatter(directory) or {}
    return {"metadata": metadata, "catalog": entry, "files": sorted(str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file())}


@mcp.tool()
async def skill_read(path: str) -> str:
    """Read a committed skill file after path-traversal checks."""
    file_path = safe_skill_file(path)
    if not file_path:
        return "ERROR: skill file not found"
    return file_path.read_text(encoding="utf-8")


def main() -> None:
    if not SKILLS_DIR.is_dir():
        raise SystemExit(f"SKILLS_DIR does not exist: {SKILLS_DIR}")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=PORT, path="/mcp")


if __name__ == "__main__":
    main()
