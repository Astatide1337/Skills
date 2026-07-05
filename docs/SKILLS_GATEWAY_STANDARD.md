# Skills Gateway Standard

**Version:** 0.1.0
**Scope:** Skills Gateway maturity (not Gateway Console, not Agents Gateway)

This document defines what "gateway-grade" means for Skills Gateway. Every implementation ticket must conform to these specifications.

---

## 1. CLI

The `skills-gateway` CLI is the primary interface for running, validating, and inspecting the gateway.

### Commands

```
skills-gateway run [--config FILE] [--profile NAME] [--skills-dir DIR] [--host HOST] [--port PORT]
skills-gateway validate [--skills-dir DIR] [--config FILE]
skills-gateway list [--skills-dir DIR] [--profile NAME]
skills-gateway inspect <skill-name> [--skills-dir DIR]
skills-gateway doctor
skills-gateway version
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Validation failure |

### Config Resolution Order

1. CLI flags (highest priority)
2. Environment variables
3. Config file (`skills-gateway.yaml` or `--config` path)
4. Built-in defaults (lowest priority)

---

## 2. Config File

Format: YAML. Name: `skills-gateway.yaml`.

```yaml
service:
  host: "0.0.0.0"
  port: 8091
  mcp_path: "/mcp"

auth:
  mode: "cloudflare-access"  # cloudflare-access | dev-none | internal-only
  cloudflare_team_domain: ""  # or env: CLOUDFLARE_TEAM_DOMAIN
  cloudflare_aud: ""          # or env: CLOUDFLARE_AUD
  public_base_url: ""         # or env: PUBLIC_BASE_URL
  internal_bypass: false      # allow Docker-internal IP bypass

skills:
  dir: "./skills"              # or env: SKILLS_DIR

observability:
  log_level: "INFO"
  log_format: "json"           # json | text
  metrics_enabled: true

profiles: {}                    # see Section 5

catalogs: {}                   # see Section 6
```

---

## 3. Endpoints

### 3.1 MCP Endpoint

```
MCP_PATH (default /mcp)
```

Streamable HTTP MCP. All existing MCP tools and resources served here.

### 3.2 Health Endpoint

```
GET /health
```

Returns process liveness. Always returns 200 if the process is running.

```json
{
  "status": "alive",
  "service": "skills-gateway",
  "timestamp": "2026-06-17T12:00:00Z"
}
```

### 3.3 Readiness Endpoint

```
GET /ready
```

Returns 200 if the gateway can serve requests. Returns 503 if not ready.

Readiness checks:
- Skills directory exists and is readable
- Skill scan succeeds
- Auth config is valid for selected mode

```json
{
  "status": "ready",
  "service": "skills-gateway",
  "checks": {
    "skills_dir": "ok",
    "skills_scan": "ok",
    "auth_config": "ok"
  },
  "auth_mode": "cloudflare-access",
  "timestamp": "2026-06-17T12:00:00Z"
}
```

Failure example:

```json
{
  "status": "not_ready",
  "service": "skills-gateway",
  "checks": {
    "skills_dir": "ok",
    "skills_scan": "ok",
    "auth_config": "failed: missing CLOUDFLARE_TEAM_DOMAIN"
  },
  "auth_mode": "cloudflare-access",
  "timestamp": "2026-06-17T12:00:00Z"
}
```

### 3.4 Version Endpoint

```
GET /version
```

```json
{
  "service": "skills-gateway",
  "version": "0.1.0",
  "commit": "abc1234",
  "build_time": "2026-06-17T12:00:00Z"
}
```

`commit` and `build_time` default to `"unknown"` if not set at build time.

### 3.5 Inventory Endpoint

```
GET /inventory
```

```json
{
  "service": "skills-gateway",
  "type": "skills",
  "skills_count": 13,
  "skills_invalid_count": 0,
  "resources_count": 42,
  "tools": ["skills_list", "skills_search", "skills_inspect", "skill_read"],
  "profiles": ["repo-review", "ops"],
  "active_profile": null,
  "auth_mode": "cloudflare-access",
  "catalogs": ["local"],
  "active_catalog": "local"
}
```

### 3.6 Metrics Endpoint

```
GET /metrics
```

Prometheus text format. See Section 4 for metric definitions.

### 3.7 Docs Endpoint

```
GET /docs
```

Returns a JSON list of available documentation URLs (or simple informational page).

```json
{
  "service": "skills-gateway",
  "docs": {
    "config": "/docs/config",
    "profiles": "/docs/profiles",
    "catalogs": "/docs/catalogs",
    "auth": "/docs/auth",
    "health": "/health",
    "ready": "/ready",
    "version": "/version",
    "inventory": "/inventory",
    "metrics": "/metrics"
  }
}
```

---

## 4. Metrics

Format: Prometheus text exposition format.

| Metric Name | Type | Description |
|-------------|------|-------------|
| `skills_gateway_up` | gauge | 1 if process is alive |
| `skills_gateway_ready` | gauge | 1 if ready to serve |
| `skills_total` | gauge | Number of valid skills loaded |
| `skills_invalid_total` | gauge | Number of invalid skills detected |
| `skill_reads_total` | counter | Number of skill_read calls |
| `skill_searches_total` | counter | Number of skills_search calls |
| `skill_inspects_total` | counter | Number of skills_inspect calls |
| `skill_lists_total` | counter | Number of skills_list calls |
| `requests_total` | counter | Total HTTP requests |
| `request_errors_total` | counter | HTTP requests that resulted in errors |
| `request_duration_seconds` | histogram | Request latency |

Labels on counter/histogram metrics: `method`, `path`, `status`.

---

## 5. Profiles

A profile is a named working set of skills. When a profile is active, only those skills are exposed via MCP tools and resources.

### Config Format

```yaml
profiles:
  repo-review:
    skills:
      - pr-risk-review
      - codebase-map

  ops:
    skills:
      - log-triage
      - incident-summary
```

### Behavior

- `--profile NAME` or `profiles.NAME` in config activates the profile
- If no profile is selected, all valid skills are exposed
- `skills_list` and `skills_search` must respect active profile
- `skills_inspect` and `skill_read` for skills not in profile return not-found
- `/inventory` shows `active_profile`
- Unknown skill in profile list produces a warning in logs and readiness issue

### Profile JSON Shape (for /inventory)

```json
{
  "name": "repo-review",
  "skills": ["pr-risk-review", "codebase-map"]
}
```

---

## 6. Catalogs

A catalog describes where skills come from. Initial support: local directory.

### Config Format

```yaml
catalogs:
  local:
    type: local
    path: ./skills

  personal:
    type: local
    path: /home/user/skills
```

### Behavior

- `--catalog NAME` or `catalogs.NAME` in config selects the catalog
- Default catalog: `local` with path from `skills.dir`
- Path must exist and be readable at startup
- Missing catalog path produces readiness check failure
- `/inventory` shows available catalogs and active catalog

### Catalog JSON Shape (for /inventory)

```json
{
  "name": "local",
  "type": "local",
  "path": "./skills",
  "skills_count": 13
}
```

---

## 7. Structured Logging

### Required Fields

Every log event must include:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | When the event occurred |
| `level` | string | INFO, WARNING, ERROR, DEBUG |
| `service` | string | "skills-gateway" |
| `event` | string | Event type identifier |
| `request_id` | string | Unique per-request ID (if applicable) |
| `instance_id` | string | Service instance identifier |
| `environment` | string | "production" or "development" |
| `message` | string | Human-readable description |
| `duration_ms` | number | Operation duration (if applicable) |
| `error` | string | Error message (if applicable) |

### Required Events

| Event | When |
|-------|------|
| `service_start` | Process starts |
| `service_ready` | Service passes readiness checks |
| `skill_scan_started` | Skill directory scan begins |
| `skill_scan_completed` | Skill directory scan finishes |
| `skill_invalid` | Invalid skill detected |
| `skill_list` | skills_list tool called |
| `skill_search` | skills_search tool called |
| `skill_inspect` | skills_inspect tool called |
| `skill_read` | skill_read tool called |
| `auth_success` | Authentication succeeds |
| `auth_failure` | Authentication fails |
| `request_completed` | HTTP request finished |
| `auth_mode_set` | Auth mode is configured at startup |
| `profile_set` | Profile is activated |
| `catalog_set` | Catalog is selected |

### Log Format

- **Production:** JSON (one JSON object per line)
- **Development:** Human-readable text (key=value format)

Controlled by `observability.log_format` config.

### No Secrets in Logs

JWTs, access tokens, refresh tokens, client secrets, and audience tags must never appear in log output.

---

## 8. Auth Modes

| Mode | Description | Safety |
|------|-------------|--------|
| `cloudflare-access` | Full OAuth + Cloudflare JWT verification. Default. | Production-safe |
| `dev-none` | No auth. Only for local development. | UNSAFE — must be explicitly enabled |
| `internal-only` | Auth bypass for Docker-internal IPs only. No OAuth flow. | Semi-safe for locked networks |

### Behavior

- Mode selected via `auth.mode` config or `AUTH_MODE` env var
- `dev-none` must log a prominent WARNING on every startup
- `cloudflare-access` requires `CLOUDFLARE_TEAM_DOMAIN` and `CLOUDFLARE_AUD`
- `internal-only` makes Docker-internal IP bypass configurable, not hardcoded
- Active auth mode appears in `/ready`, `/inventory`, and startup logs
- Missing required config for selected mode is a readiness failure (not a crash)

---

## 9. Skill Manifest Schema

Skills are defined by YAML frontmatter in each skill directory's `SKILL.md`. The gateway normalizes that frontmatter into a canonical manifest shape.

### Canonical Fields

```yaml
id: string             # Optional — defaults to directory name; if present, must match directory name
name: string           # Required — human-readable skill name
description: string    # Required — what the skill does
version: string        # Required, or use metadata.version
entrypoint: string     # Optional — defaults to SKILL.md and must exist
risk_level: low | medium | high
allowed-tools: list    # Tools the skill may invoke
tags: list             # Searchable tags
author: string         # Skill author
license: string        # License identifier
compatibility: string  # Compatible platforms
files: list            # Additional files that must exist
inputs: object         # Declared input schema/metadata
outputs: object        # Declared output schema/metadata
permissions: object    # Declared permission requirements
metadata:
  version: string      # Backward-compatible version location
```

### Validation

- `name`, `description`, and version are required. Version may be top-level `version` or `metadata.version`.
- `id` defaults to the skill directory name. If explicitly provided, it must match the directory name.
- `entrypoint` defaults to `SKILL.md` and must point to an existing file.
- Listed files must exist and must be strings.
- `risk_level` must be `low`, `medium`, or `high`.
- Skills missing required fields are flagged as invalid.
- Invalid skills do not crash the gateway.
- Invalid skill count appears in `/inventory`.
- `skills-gateway validate` reports all validation errors with file paths.
- `skills-gateway doctor` includes skill validation in readiness check.

---

## 10. Deployment Files

Required:

```
Dockerfile              # Production image
docker-compose.yml      # Compose deployment
.env.example            # All env vars documented
.dockerignore           # Exclude non-essential files
```

Compose must include:
- `skills-gateway` service
- healthcheck (`curl -f http://localhost:8091/health`)
- mounted skills directory
- env file
- restart policy (`unless-stopped`)

---

## 11. Test Suite

### Required Categories

- Unit tests (config, validation, skills, profiles, catalogs, auth)
- Endpoint tests (health, ready, version, inventory, metrics)
- MCP tool tests (skills_list, skills_search, skills_inspect, skill_read)
- CLI tests (run, validate, list, inspect, doctor, version)
- Auth config tests (each mode)
- Smoke tests (running service verification)

### Commands

```
make test     # or just test — runs unit + integration
make smoke    # smoke test against running service
make verify   # compile + test + smoke
```

---

## 12. Documentation

Required docs:

| File | Content |
|------|---------|
| `README.md` | Overview, quickstart, architecture |
| `docs/CONFIG.md` | Config file format and options |
| `docs/PROFILES.md` | Profile system |
| `docs/CATALOGS.md` | Catalog system |
| `docs/AUTH.md` | Auth modes and setup |
| `docs/DEPLOYMENT.md` | Docker and deployment |
| `docs/OBSERVABILITY.md` | Logs and metrics |
| `docs/TESTING.md` | How to run tests |
| `docs/SECURITY.md` | Security considerations |
| `docs/TROUBLESHOOTING.md` | Common issues and fixes |

---

## 13. Build-Time Variables

Injected at Docker build time for `/version` endpoint:

| Variable | Flag | Default |
|----------|------|---------|
| `SKG_VERSION` | `--build-arg` | From pyproject.toml |
| `SKG_COMMIT` | `--build-arg` | `"unknown"` |
| `SKG_BUILD_TIME` | `--build-arg` | `"unknown"` |
