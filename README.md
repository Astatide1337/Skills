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

Skills Gateway verifies Cloudflare Access JWTs in production using real JWKS-based signature verification. See [SECURITY.md](SECURITY.md) for full details.

Quick summary:
- **`cloudflare-access`**: Real CF Access JWT verification (RS256 signature, audience, issuer, expiry). Default in production.
- **`internal-only`**: Same as cloudflare-access + optional Docker IP bypass.
- **`dev-none`**: No auth. Development only.
- **No bearer-token bypass**: Random `Authorization` headers rejected.
- **Path traversal protection**: `..`, absolute paths, symlink escapes blocked for `skill_read`.

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