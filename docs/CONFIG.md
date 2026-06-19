# Configuration Reference

Skills Gateway reads configuration from multiple sources with a defined priority:

1. **CLI flags** (highest priority)
2. **Environment variables**
3. **YAML config file** (`skills-gateway.yaml` or `--config` path)
4. **Built-in defaults** (lowest priority)

## Config File Format

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
  dir: "./skills"            # or env: SKILLS_DIR

observability:
  log_level: "INFO"
  log_format: "json"         # json | text
  metrics_enabled: true

profiles: {}
catalogs: {}
```

## Environment Variables

| Variable | Config Path | Default |
|----------|------------|---------|
| `AUTH_MODE` | `auth.mode` | `cloudflare-access` |
| `CLOUDFLARE_TEAM_DOMAIN` | `auth.cloudflare_team_domain` | (none) |
| `CLOUDFLARE_AUD` | `auth.cloudflare_aud` | (none) |
| `PUBLIC_BASE_URL` | `auth.public_base_url` | `https://skills.astatide.com` |
| `INTERNAL_BYPASS` | `auth.internal_bypass` | `false` |
| `HOST` | `service.host` | `0.0.0.0` |
| `PORT` | `service.port` | `8091` |
| `MCP_PATH` | `service.mcp_path` | `/mcp` |
| `SKILLS_DIR` | `skills.dir` | `~/skills` |
| `LOG_LEVEL` | `observability.log_level` | `INFO` |
| `LOG_FORMAT` | `observability.log_format` | `json` |
| `METRICS_ENABLED` | `observability.metrics_enabled` | `true` |
| `SKG_CONFIG` | (config file path) | `skills-gateway.yaml` |
| `SKG_ENVIRONMENT` | `environment` | `production` |
| `SKG_PROFILE` | `active_profile` | (none) |
| `SKG_CATALOG` | `active_catalog` | (none) |

## CLI Flags

```
skills-gateway run [--config FILE] [--host HOST] [--port PORT]
                   [--mcp-path PATH] [--skills-dir DIR]
                   [--auth-mode MODE] [--public-base-url URL]
                   [--profile NAME] [--catalog NAME]
```
