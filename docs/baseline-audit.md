# Skills Gateway — Baseline Audit

**Ticket:** SKG-001.0
**Date:** 2026-06-18 (updated from 2026-06-17)
**Auditor:** Autonomous Agent

---

## 1. Repository Structure

```
skills-mcp/
├── .env.example          # 5 env vars documented
├── .gitignore            # .env, .venv/, __pycache__/
├── .venv/                # Python 3.14 venv (uv-managed)
├── Dockerfile            # python:3.12-slim + uv, copies skills_gateway/ package
├── README.md             # 78-line overview
├── pyproject.toml        # 5 deps, version 0.1.0, CLI entry point
├── server.py             # 4-line shim importing from skills_gateway package
├── uv.lock               # Lockfile
├── skills_gateway/       # Modular package (was monolithic server.py)
│   ├── __init__.py       # SERVICE_NAME = "skills-gateway"
│   ├── config.py         # Env-based configuration constants
│   ├── auth.py           # CloudflareAccessOAuthProvider + monkey-patches
│   ├── skills.py         # Pure skill parsing functions
│   ├── resources.py      # MCP resource registration
│   ├── tools.py           # MCP tool registration (4 tools)
│   ├── routes.py         # OAuth well-known endpoint registration
│   └── server.py         # Main entry point (create_app, main)
├── tests/
│   └── test_skills.py    # 12 unit tests for skills.py pure functions
└── docs/
    ├── SKILLS_GATEWAY_STANDARD.md  # Gateway-grade specification
    ├── baseline-audit.md           # This file
    └── agent-worklog.md            # Running work log
```

---

## 2. Current Architecture

### Package Layout

| Module | Lines | Responsibility |
|--------|-------|---------------|
| `config.py` | 13 | Env loading, constants (PUBLIC_BASE_URL, MCP_PATH, CLOUDFLARE_*, SKILLS_DIR, HOST, PORT) |
| `auth.py` | 322 | CloudflareAccessOAuthProvider, monkey-patches for ClientAuthenticator/TokenHandler/RequireAuthMiddleware |
| `skills.py` | 49 | `parse_skill_frontmatter()`, `get_skills_catalog()`, `get_skill_file_tree()` — all pure functions |
| `resources.py` | 39 | `register_resources(mcp, skills_dir)` — skill://index.json + per-file FunctionResources |
| `tools.py` | 71 | `register_tools(mcp, skills_dir)` — 4 MCP tools |
| `routes.py` | 29 | `register_routes(mcp)` — 2 OAuth well-known custom routes |
| `server.py` | 43 | `create_app()` assembles FastMCP, `main()` runs transport, `apply_auth_patches()` called at startup |

### Entrypoint

`server.py` (root) — 4-line shim:
```python
from skills_gateway.server import mcp, main
if __name__ == "__main__":
    main()
```

### Runtime

- **Transport:** Streamable HTTP MCP on port 8091, path `/mcp`
- **Framework:** FastMCP (>=3.4.0)
- **ASGI:** Uvicorn (via FastMCP)

### Dependencies (pyproject.toml)

| Package | Version | Purpose |
|---------|---------|---------|
| fastmcp | >=3.4.0 | MCP server framework |
| python-dotenv | >=1.2.2 | .env loading |
| pyjwt | >=2.13.0 | Cloudflare JWT verification |
| pyyaml | >=6.0 | SKILL.md frontmatter parsing |

Dev dependency (installed manually, not in pyproject.toml):
| pytest | >=9.1.0 | Test framework |

No CLI framework. No linting. No type checking.

---

## 3. Existing Features

### MCP Tools (4)

| Tool | Description | Module |
|------|-------------|--------|
| `skills_list` | List all available skills with full metadata | tools.py |
| `skills_search` | Search skills by name/description, ranked scoring | tools.py |
| `skills_inspect` | Full metadata + file tree for a single skill | tools.py |
| `skill_read` | Read individual skill file by relative path (path traversal guard) | tools.py |

### MCP Resources

- `skill://index.json` — full skills catalog (resources.py)
- `skill://{path}` — every skill file registered as a FunctionResource (resources.py)

### Custom Routes (2)

- `/.well-known/oauth-authorization-server` — OAuth discovery (routes.py)
- `/.well-known/oauth-protected-resource/mcp` — Protected resource metadata (routes.py)

### Auth System

- **CloudflareAccessOAuthProvider** — full OAuth2 authorization code + refresh flow
  - In-memory client/authorization code/access token/refresh token stores
  - Cloudflare JWT verification via JWK set
  - Dynamic client registration
  - PKCE support
  - Docker-internal IP bypass (172.*, 10.*, 192.168.*) — hardcoded
- **Monkey-patches** (applied via `apply_auth_patches()`):
  - `ClientAuthenticator.authenticate_request` — accepts Basic auth client_id
  - `TokenHandler.handle` — custom token handling accepting Basic client_id
  - `RequireAuthMiddleware._send_auth_error` — minimal auth error with resource metadata

### Skill Loading

- Reads from `SKILLS_DIR` (default `/skills`, env-configurable)
- Scans subdirectories for `SKILL.md` with YAML frontmatter
- Required field: `name` (others optional: description, metadata.version, license, compatibility, allowed-tools)
- Skills without `name` in frontmatter are silently skipped
- No validation, no error reporting for invalid skills

---

## 4. Current Limitations (Gap vs SKILLS_GATEWAY_STANDARD.md)

### Architecture

| # | Gap | Standard Section |
|---|-----|-----------------|
| 1 | No CLI (`skills-gateway run/validate/list/inspect/doctor/version`) | §1 |
| 2 | No config file (`skills-gateway.yaml`) — env vars only | §2 |
| 3 | No profiles (named working sets of skills) | §5 |
| 4 | No catalogs (multi-source skill directories) | §6 |
| 5 | No auth modes (`dev-none`, `internal-only`) — only `cloudflare-access` | §8 |

### Endpoints

| # | Missing Endpoint | Standard Section |
|---|------------------|-----------------|
| 6 | `GET /health` | §3.2 |
| 7 | `GET /ready` | §3.3 |
| 8 | `GET /version` | §3.4 |
| 9 | `GET /inventory` | §3.5 |
| 10 | `GET /metrics` | §3.6 |
| 11 | `GET /docs` | §3.7 |

### Observability

| # | Gap | Standard Section |
|---|-----|-----------------|
| 12 | No structured logging (JSON/text via config) | §7 |
| 13 | No request ID tracking | §7 |
| 14 | No structured log events (service_start, skill_scan_*, auth_*, etc.) | §7 |
| 15 | No Prometheus metrics (11 defined metric types) | §4 |

### Validation & Quality

| # | Gap |
|---|-----|
| 16 | No skill manifest schema validation |
| 17 | Only 12 unit tests covering `skills.py` — no endpoint, tool, CLI, or auth tests |
| 18 | No `Makefile` (no `make test`, `make smoke`, `make verify`) |
| 19 | No linting or type checking in CI |

### Auth & Security

| # | Gap |
|---|-----|
| 20 | Hard RuntimeError if CLOUDFLARE_TEAM_DOMAIN/CLOUDFLARE_AUD missing — no graceful degradation |
| 21 | Docker-internal IP bypass hardcoded in auth.py — not configurable |
| 22 | In-memory OAuth state — no persistence, no scaling |
| 23 | No `AUTH_MODE` selector env var |

### Deployment

| # | Gap |
|---|-----|
| 24 | No `docker-compose.yml` |
| 25 | No `.dockerignore` (only `.git` in .gitignore) |
| 26 | No healthcheck in Dockerfile |
| 27 | No non-root user in Dockerfile |
| 28 | No build-time variables (SKG_VERSION, SKG_COMMIT, SKG_BUILD_TIME) |
| 29 | Dockerfile uses python:3.12-slim but local Python is 3.14 |

### Documentation

| # | Missing Doc |
|---|------------|
| 30 | CONFIG.md |
| 31 | PROFILES.md |
| 32 | CATALOGS.md |
| 33 | AUTH.md |
| 34 | DEPLOYMENT.md |
| 35 | OBSERVABILITY.md |
| 36 | TESTING.md |
| 37 | SECURITY.md |
| 38 | TROUBLESHOOTING.md |

---

## 5. Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PUBLIC_BASE_URL` | `https://skills.astatide.com` | Yes (for OAuth) | Public URL |
| `MCP_PATH` | `/mcp` | No | MCP endpoint path |
| `CLOUDFLARE_TEAM_DOMAIN` | None | Yes (RuntimeError) | CF Access team domain |
| `CLOUDFLARE_AUD` | None | Yes (RuntimeError) | CF Access audience tag |
| `SKILLS_DIR` | `~/skills` → resolved to `/skills` | No | Skills directory path |
| `HOST` | `0.0.0.0` | No | Bind address |
| `PORT` | `8091` | No | Bind port |

7 env vars total. 2 are hard-required (crash on start if missing). No `AUTH_MODE` selector.

---

## 6. Docker Configuration

### Current Dockerfile

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev
COPY server.py ./
COPY skills_gateway/ ./skills_gateway/
ENV SKILLS_DIR=/skills
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8091
CMD ["uv", "run", "server.py"]
```

- No `.dockerignore`
- No healthcheck
- No non-root user
- No compose file
- Skills must be volume-mounted at `/skills`

### Current Run Command

```bash
docker build -t skills-mcp .
docker run -d \
  -p 127.0.0.1:8091:8091 \
  -v /path/to/skills:/skills \
  --env-file .env \
  skills-mcp
```

---

## 7. Test Coverage

### Existing

- `tests/test_skills.py` — 12 tests covering `skills.py` pure functions
- All PASS as of 2026-06-18

### Missing

- Endpoint tests (/health, /ready, /version, /inventory, /metrics)
- MCP tool integration tests
- Auth config tests
- CLI tests
- Smoke/e2e tests

### Commands

```bash
cd /home/ubuntu/skills-mcp
source .venv/bin/activate
CLOUDFLARE_TEAM_DOMAIN=test.example.com CLOUDFLARE_AUD=test-aud python -m pytest tests/ -v
# Result: 12 passed in 0.05s
```

---

## 8. Verification Commands

### Compile check

```bash
cd /home/ubuntu/skills-mcp
source .venv/bin/activate
python -m compileall . -q
# Result: PASS (all .py files compile, no output)
```

### Full import chain

```bash
CLOUDFLARE_TEAM_DOMAIN=test.example.com CLOUDFLARE_AUD=test-aud python -c "from skills_gateway.server import mcp, main; print('OK')"
# Result: OK (with INFO log lines about skills_dir and resources)
```

### Run attempt (without Cloudflare creds)

```bash
uv run server.py
# Expected: RuntimeError("Missing required env vars: CLOUDFLARE_TEAM_DOMAIN, CLOUDFLARE_AUD")
```

---

## 9. Risks

| Risk | Severity | Notes |
|------|----------|-------|
| Hard Cloudflare auth requirement | High | Cannot develop or test locally without CF creds |
| In-memory OAuth state | Medium | Lost on restart; no horizontal scaling |
| Only skills.py tested | Medium | Auth, endpoints, tools, CLI all untested |
| Monkey-patched auth middleware | Medium | Brittle, breaks on FastMCP/MCP SDK upgrades |
| Hardcoded Docker IP bypass | Medium | Security risk; not configurable |
| No skill validation | Low-Medium | Invalid skills silently disappear |
| No health/readiness/version/metrics | High | Cannot monitor service health |
| No structured logging | Medium | Cannot search/aggregate logs in production |
| Dockerfile uses Python 3.12 / local is 3.14 | Low | Potential compatibility drift |
| No .dockerignore | Low | Bulky context sent to Docker daemon |

---

## 10. Deployment Assumptions

- Skills Gateway runs behind Cloudflare Access + Tunnel
- Public URL is internet-reachable
- Skills directory is volume-mounted into container
- Only one instance (no scaling story)
- No service mesh or Kubernetes
- Manual Docker run, no compose

---

## 11. Recommended Next Ticket

**SKG-001.1 — CLI and Config System**

Add:
- `skills-gateway.yaml` config file support with full schema from §2 of the Standard
- CLI via `typer` or `click` with commands: `run`, `validate`, `list`, `inspect`, `doctor`, `version`
- Config resolution order: CLI flags > env vars > config file > defaults
- Auth modes: `cloudflare-access` (default), `dev-none`, `internal-only`
- `AUTH_MODE` env var support
