# Observability

## Structured Logging

Skills Gateway emits structured logs in JSON (production) or text (development) format.

### Configuration

```yaml
observability:
  log_level: "INFO"      # DEBUG | INFO | WARNING | ERROR
  log_format: "json"     # json | text
```

### Required Log Fields

Every log event includes:

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 timestamp |
| `level` | Log level (INFO, WARNING, ERROR, DEBUG) |
| `service` | Always `skills-gateway` |
| `event` | Event type identifier |
| `request_id` | Unique per-request ID |
| `instance_id` | Service instance identifier |
| `environment` | `production` or `development` |
| `message` | Human-readable description |

### Key Events

| Event | When |
|-------|------|
| `service_start` | Process starts |
| `service_ready` | Readiness checks pass |
| `skill_scan_started` | Skill directory scan begins |
| `skill_scan_completed` | Scan finishes |
| `skill_invalid` | Invalid skill detected |
| `skill_list` | skills_list tool called |
| `skill_search` | skills_search tool called |
| `skill_inspect` | skills_inspect tool called |
| `skill_read` | skill_read tool called |
| `auth_success` | Authentication succeeds |
| `auth_failure` | Authentication fails |
| `auth_mode_set` | Auth mode configured at startup |
| `profile_set` | Profile activated |
| `catalog_set` | Catalog selected |

### No Secrets in Logs

JWTs, access tokens, refresh tokens, client secrets, and audience tags are never included in log output.

## Metrics

### Endpoint

```
GET /metrics
```

Returns Prometheus text exposition format.

### Available Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `skills_gateway_up` | gauge | 1 if process is alive |
| `skills_gateway_ready` | gauge | 1 if ready to serve |
| `skills_total` | gauge | Number of valid skills |
| `skills_invalid_total` | gauge | Number of invalid skills |
| `skill_reads_total` | counter | skill_read calls |
| `skill_searches_total` | counter | skills_search calls |
| `skill_inspects_total` | counter | skills_inspect calls |
| `skill_lists_total` | counter | skills_list calls |
| `requests_total` | counter | Total HTTP requests |
| `request_errors_total` | counter | HTTP error requests |
| `request_duration_seconds` | histogram | Request latency |

Labels on counter/histogram metrics: `method`, `path`, `status`.

### Disabling Metrics

```yaml
observability:
  metrics_enabled: false
```
