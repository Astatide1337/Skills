# Skills Gateway Current State

This audit records the current known state of Skills Gateway against `README.md`, `ROADMAP.md`, and `docs/GATEWAY_PLATFORM_STANDARD.md`.

Status labels:

- Implemented: verified in inspected files.
- Partial: present but needs hardening or test confirmation.
- Missing: not verified or not present in inspected files.
- Unclear: requires local run or deeper file inspection.

## Verified repository facts

- Repository: `Astatide1337/Skills-MCP-Gateway`
- Default branch: `main`
- Package name: `skills-gateway`
- Python requirement: `>=3.12`
- CLI entry point: `skills-gateway = skills_gateway.cli:cli_main`
- FastMCP dependency: `fastmcp>=3.4.0`
- Config file: `skills-gateway.yaml`

## README claims

### Service purpose

Status: Implemented conceptually.

The README describes Skills Gateway as a production-grade MCP gateway that exposes skills as tools and resources through MCP.

Needs confirmation:

- Full MCP tool registration behavior.
- MCP resource registration behavior.
- Tool output schema stability.

### CLI commands

README claims:

- `skills-gateway run`
- `skills-gateway validate`
- `skills-gateway list`
- `skills-gateway inspect <skill-name>`
- `skills-gateway doctor`
- `skills-gateway version`

Status: Partial.

The project entry point exists in `pyproject.toml`, but each command should be confirmed against `skills_gateway/cli.py` and CLI tests.

### HTTP endpoints

README claims:

- `GET /mcp`
- `GET /health`
- `GET /ready`
- `GET /version`
- `GET /inventory`
- `GET /metrics`
- `GET /docs`

Status: Partial.

These endpoints are documented. Runtime behavior should be verified with a smoke test.

### MCP tools

README claims:

- `skills_list`
- `skills_search`
- `skills_inspect`
- `skill_read`

Status: Partial.

The tool names are documented. Need implementation and test confirmation.

## Config behavior

Status: Implemented/partial.

Verified config module behavior includes:

- Defaults for service host, port, and MCP path.
- Auth modes: `cloudflare-access`, `dev-none`, `internal-only`.
- Skills directory default.
- Observability config.
- Profiles and catalogs.
- Validation for auth config, port range, skill directory, active profile, active catalog, and catalog path.

Known gap:

- Existing environment variables are generic in places, such as `HOST`, `PORT`, `AUTH_MODE`, and `SKILLS_DIR`.
- Platform standard now prefers `SKG_`-prefixed variables and nested double-underscore env mapping.

## Platform standard alignment

### Required management endpoints

Status: Documented, needs smoke-test confirmation.

### MCP-first behavior

Status: Partial.

MCP tools are documented, but tool schemas and resource contracts need hardening.

### Tool result shape

Status: Missing/unclear.

Need to verify whether tools return a consistent `{ ok, data, error, meta }` shape.

### Resource URI conventions

Status: Missing/unclear.

Target resource URIs:

- `skill://{skill_id}/manifest`
- `skill://{skill_id}/entrypoint`
- `skill://{skill_id}/file/{path}`

Need implementation confirmation.

### Auth modes

Status: Partial.

Auth modes exist in config. Production safety behavior should be verified.

### Metrics

Status: Partial.

Metrics are documented. Need smoke-test confirmation and metric coverage review.

## Priority gaps

1. Confirm actual MCP tool registration and behavior.
2. Define and enforce the canonical `skill.yaml` schema.
3. Stabilize JSON output shapes for MCP tools.
4. Add or confirm MCP resources for skill manifests and files.
5. Standardize config around `SKG_` env vars while preserving compatibility.
6. Add smoke tests for management endpoints and MCP tools.
7. Improve `/inventory` and `/ready` detail if needed.

## Follow-up issues

- SKG-002: Define and validate canonical skill manifest schema.
- SKG-003: Harden MCP skill tools.

Additional recommended issue:

- SKG-004: Standardize config and service checks.
