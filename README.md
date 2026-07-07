# Skills Gateway

Skills Gateway exposes agent skills as MCP tools and resources. It provides skill discovery, inspection, and file reading over the Model Context Protocol, with Cloudflare Access authentication for production deployments.

## Quick Start

```bash
# Install and run with dev auth
uv sync
uv run skills-gateway run --auth-mode dev-none --skills-dir ./skills
```

Default port: 8091. MCP endpoint at `/mcp`.

## CLI Commands

```bash
skills-gateway run                 # Start the gateway server
skills-gateway validate            # Validate skill manifests
skills-gateway list                # List available skills
skills-gateway inspect <name>     # Inspect a single skill
skills-gateway doctor              # Readiness and config checks
skills-gateway version             # Show version info
```

## Architecture

```
                   ┌─────────────────────────┐
                   │ Cloudflare Access (edge) │
                   │  → Cf-Access-Jwt-Assertion│
                   └───────────┬─────────────┘
                               │
                               ▼
                   ┌─────────────────────────┐
                   │     Skills Gateway       │
                   │      (FastMCP ASGI)      │
                   │                          │
                   │  Auth: CF Access JWKS    │
                   │  Tools: search/list/read │
                   │  Resources: skill files  │
                   │  Routes: HTTP endpoints  │
                   └───────────┬─────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
              Skills Catalog         Skill Files
              (SKILL.md parsing)     (path-traversal protected)
```

## Security

Skills Gateway supports two deployment postures:

1. **Edge-auth-only personal mode**: Cloudflare Access protects the hostname at the edge. The origin is private (127.0.0.1). App can use `dev-none`. Suitable for personal MCP usage.

2. **Defense-in-depth production mode**: Cloudflare Access at the edge + app-level CF Access JWT verification (`cloudflare-access` mode). Suitable for multi-user or zero-trust deployments.

See [SECURITY.md](SECURITY.md) for full details on authentication modes, JWT verification, internal bypass risks, and path traversal protections.

## Configuration

```bash
# Cloudflare Access (production)
export AUTH_MODE=cloudflare-access
export CLOUDFLARE_TEAM_DOMAIN=<team>.cloudflareaccess.com
export CLOUDFLARE_AUD=<application-audience-tag>
export PUBLIC_BASE_URL=https://skills.example.com

# Skills directory
export SKILLS_DIR=~/skills
```

See [docs/CONFIG.md](docs/CONFIG.md) for full configuration reference.

## MCP Tools

| Tool | Description |
|------|-------------|
| `skills_list` | List all available skills with metadata |
| `skills_search` | Search skills by name/description, ranked by relevance |
| `skills_inspect` | Get full metadata, manifest, and file tree for a skill |
| `skill_read` | Read a skill file by relative path (path-traversal protected) |

## Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | Public | Process liveness |
| `GET /ready` | Public | Readiness (skills dir, scan, auth config) |
| `GET /version` | Public | Version and build info |
| `GET /inventory` | Protected | Skills inventory, tools list, profiles |
| `GET /metrics` | Protected | Prometheus metrics |
| `GET /skills` | Protected | Full skills catalog |
| `GET /docs` | Public | Documentation index |
| `POST /mcp` | Protected | MCP protocol (initialize, tools/call) |

## Docker

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
curl http://localhost:8091/health
docker compose down
```

## Testing

```bash
uv run pytest -q
bash scripts/smoke-test.sh  # if available
```

## License

See individual skill directories for license information. Gateway code: repository license.