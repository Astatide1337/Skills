# Skills MCP Gateway

An MCP server implementing the [Agent Skills](https://github.com/anthropics/agent-skills) open standard. Exposes skill knowledge as MCP resources and discovery tools, with Cloudflare Access OAuth for authentication.

## Architecture

```
┌──────────────┐     ┌─────────────┐     ┌───────────────┐     ┌──────────┐
│ MCP Client   │────▶│ Cloudflare  │────▶│ Skills MCP    │────▶│ ~/skills/│
│ (ChatGPT,    │     │ Access +    │     │ Gateway       │     │ (skills  │
│  Claude)     │◀────│ Tunnel      │◀────│ :8091/mcp     │◀────│  dir)    │
└──────────────┘     └─────────────┘     └───────────────┘     └──────────┘
                                              │
                                         ┌────▼────┐
                                         │ Docker  │
                                         │ Gateway │
                                         │ (internal│
                                         │  mcp)   │
                                         └─────────┘
```

- **External clients** authenticate via Cloudflare Access at the edge, then complete the MCP OAuth flow for a Bearer token
- **Internal Docker gateway** connects directly via Docker DNS — auth is bypassed for Docker-internal IPs

## Features

- **Skill discovery**: `skills_list`, `skills_search`, `skills_inspect` tools
- **Skill reading**: `skill_read` — fetch individual skill files on demand
- **MCP resources**: `skill://{path}` — every skill file registered as a resource
- **OAuth**: Full authorization code flow with PKCE, Cloudflare JWT verification, dynamic client registration
- **Containerized**: Docker image with `uv` for fast, reproducible builds

## Quick Start

```bash
cp .env.example .env
# Edit .env with your Cloudflare Access credentials
docker build -t skills-mcp .
docker run -d \
  -p 127.0.0.1:8091:8091 \
  -v /path/to/skills:/skills \
  --env-file .env \
  skills-mcp
```

## Environment Variables

| Variable | Description |
|---|---|
| `PUBLIC_BASE_URL` | Public-facing URL (e.g. `https://skills.example.com`) |
| `MCP_PATH` | MCP endpoint path (default `/mcp`) |
| `CLOUDFLARE_TEAM_DOMAIN` | Cloudflare Access team domain |
| `CLOUDFLARE_AUD` | Cloudflare Access audience tag |
| `SKILLS_DIR` | Path to skills directory (default `/skills`) |

## Tools

| Tool | Description |
|---|---|
| `skills_list` | List all available skills with full metadata |
| `skills_search` | Search skills by name and description |
| `skills_inspect` | Get full metadata and file tree for a skill |
| `skill_read` | Read an individual skill file by path |

## Skills Directory Structure

```
~/skills/
├── my-skill/
│   ├── SKILL.md          # Required: YAML frontmatter + markdown
│   ├── instructions.md
│   └── examples/
│       └── example.js
└── another-skill/
    └── SKILL.md
```

Each skill is a subdirectory with a `SKILL.md` containing YAML frontmatter (name, description, version, etc.). All files within are accessible via `skill_read` or the `skill://` resource URI.
