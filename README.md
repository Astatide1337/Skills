# Skills Gateway

A production-grade MCP gateway that exposes skills as tools and resources via the Model Context Protocol.

## Quick Start

```bash
# Install dependencies
uv sync

# Run with dev auth (no authentication)
AUTH_MODE=dev-none SKILLS_DIR=~/skills uv run skills-gateway run

# Or use the CLI
skills-gateway run --auth-mode dev-none --skills-dir ~/skills
```

## CLI Commands

```bash
skills-gateway run                          # Start the gateway server
skills-gateway validate --skills-dir ./skill  # Validate skill manifests
skills-gateway list --skills-dir ./skills     # List available skills
skills-gateway inspect <skill-name>         # Inspect a single skill
skills-gateway doctor                       # Check configuration health
skills-gateway version                      # Show version info
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /mcp` | Streamable HTTP MCP endpoint |
| `GET /health` | Process liveness |
| `GET /ready` | Readiness checks |
| `GET /version` | Version and build info |
| `GET /inventory` | Skills inventory |
| `GET /metrics` | Prometheus metrics |
| `GET /docs` | Documentation index |

## MCP Tools

- `skills_list` — List all available skills
- `skills_search` — Search skills by name/description
- `skills_inspect` — Get full metadata and file tree
- `skill_read` — Read a skill file by path

## Configuration

See [docs/CONFIG.md](docs/CONFIG.md) for full configuration reference.

## Docker Deployment

```bash
cp .env.example .env   # required before first docker compose run
docker compose up -d --build
docker compose ps
curl http://localhost:8091/health
```

## Architecture

```
skills_gateway/
  config.py     — GatewayConfig, YAML loading, layered resolution
  auth.py       — Auth providers (Cloudflare Access, dev-none, internal-only)
  skills.py     — Skill parsing, catalog, validation
  resources.py  — MCP resource registration
  tools.py      — MCP tool registration
  routes.py     — HTTP endpoints (health, ready, version, inventory, metrics, docs)
  server.py     — App creation and run entry point
  cli.py        — CLI via typer
  logging.py    — Structured JSON/text logging
  metrics.py    — Prometheus metrics collection
```

## License

See individual skill directories for license information.
