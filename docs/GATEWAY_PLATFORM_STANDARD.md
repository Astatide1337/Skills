# Gateway Platform Standard

This document defines the shared conventions for Skills Gateway and Agents Gateway.

## Service roles

Skills Gateway is the capability registry. It discovers, validates, searches, inspects, and exposes skill files/resources.

Agents Gateway is the execution and task lifecycle layer. It discovers agents, creates tasks, runs or delegates work, stores task state, emits events, and exposes artifacts.

The services should interoperate but remain independently useful.

## Required management endpoints

Every gateway should expose:

```text
GET /health       liveness
GET /ready        readiness with dependency checks
GET /version      service name and version
GET /inventory    machine-readable capabilities and counts
GET /metrics      Prometheus-compatible metrics
GET /docs         documentation or OpenAPI pointer
/mcp              MCP endpoint
```

## MCP-first rule

If an operation is important for an AI client, it should be available as an MCP tool or MCP resource. HTTP endpoints may exist for debugging, deployment, and conventional integrations, but MCP is the primary product surface.

## Tool result shape

MCP tools should return JSON-compatible objects with a stable shape:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "meta": {
    "gateway": "skills-gateway",
    "version": "0.1.0",
    "request_id": "..."
  }
}
```

Errors should use:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "not_found",
    "message": "Readable error message",
    "details": {}
  },
  "meta": {
    "gateway": "agents-gateway",
    "version": "0.1.0",
    "request_id": "..."
  }
}
```

## Error principles

- Do not leak secrets.
- Include stable error codes.
- Include human-readable messages.
- Include structured details when useful.
- Prefer explicit validation failures over silent exclusion, except invalid catalog entries should not be exposed as runnable.

## Auth modes

Both gateways should support:

- `dev-none`: no auth, explicit unsafe development mode.
- `internal-only`: localhost/Docker-internal access only.
- `cloudflare-access`: validate Cloudflare Access JWTs.

Production mode must not silently run with `dev-none`.

## Environment variable prefixes

Use gateway-specific prefixes:

```text
SKG_ for Skills Gateway
AGW_ for Agents Gateway
```

Nested config should use double underscores:

```text
SKG_SERVICE__PORT=8091
AGW_SERVICE__PORT=8092
AGW_STORAGE__SQLITE_PATH=./data/agents-gateway.db
```

Precedence should be:

```text
CLI flags > environment variables > YAML config > built-in defaults
```

## Resource URI conventions

Skills Gateway:

```text
skill://{skill_id}/manifest
skill://{skill_id}/entrypoint
skill://{skill_id}/file/{path}
```

Agents Gateway:

```text
agent://{agent_id}/manifest
task://{task_id}
task://{task_id}/events
task://{task_id}/artifacts/{artifact_name}
```

## Observability

Every service should expose structured logs with:

```text
timestamp
level
service
environment
event
request_id
message
duration_ms
error
```

Agents Gateway should also include `task_id` and `agent_id` where applicable.

## Metrics

Shared metrics:

```text
gateway_up
gateway_ready
requests_total
request_errors_total
request_duration_seconds
mcp_tool_calls_total
mcp_tool_errors_total
```

Skills Gateway metrics:

```text
skills_total
skills_invalid_total
skill_reads_total
```

Agents Gateway metrics:

```text
agents_total
agents_invalid_total
tasks_created_total
tasks_completed_total
tasks_failed_total
tasks_cancelled_total
active_runs
artifacts_total
runtime_errors_total
```

## Versioning

Tool output schemas and manifest schemas are contracts. Breaking changes should require a version bump and migration notes.

## Safety

- Discovery tools should be read-only.
- Execution must be explicit and task-scoped.
- Runtime adapters must not execute arbitrary user-provided shell commands.
- High-risk agents should support permission checks and approval gates.
