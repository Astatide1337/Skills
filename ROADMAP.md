# Skills Gateway Roadmap

Skills Gateway is the capability registry for the gateway platform. It discovers, validates, indexes, and exposes skills through MCP tools and resources.

## Role in the platform

Skills Gateway answers:

- What skills exist?
- What does each skill do?
- What files/instructions does a skill expose?
- What permissions/risk does a skill require?
- How can another gateway or MCP client inspect and read skill content safely?

Agents Gateway is responsible for task execution. Skills Gateway should remain focused on discovery, validation, metadata, and resource access.

## Core principles

1. MCP-first: every important capability should be available over MCP.
2. Read-mostly: this service should be safe to expose because it primarily lists, searches, inspects, and reads skills.
3. Stable contracts: tool outputs and resource URIs should be machine-readable and versioned.
4. Strict validation: invalid skills should never appear as usable capabilities.
5. Observable by default: health, readiness, inventory, metrics, and logs should explain service state.

## Milestones

### SKG-M0: Reality audit

- [ ] Compare README claims with implementation.
- [ ] Inventory current CLI commands, HTTP endpoints, MCP tools, resources, config fields, Docker files, and tests.
- [ ] Mark each claimed feature as implemented, partial, or missing.
- [ ] Document code/spec mismatches.

Acceptance criteria:

- [ ] `docs/CURRENT_STATE.md` exists.
- [ ] Every public feature claim is accounted for.

### SKG-M1: Skill manifest contract

- [ ] Define the canonical `skill.yaml` schema.
- [ ] Define required fields: `id`, `name`, `description`, `version`, `entrypoint`.
- [ ] Define optional fields: `risk_level`, `tags`, `files`, `inputs`, `outputs`, `permissions`, `author`.
- [ ] Validate `id` against directory name.
- [ ] Validate referenced files exist.
- [ ] Validate `risk_level` values.
- [ ] Add valid and invalid skill fixtures.

Acceptance criteria:

- [ ] Valid skills load into the catalog.
- [ ] Invalid skills are excluded from usable output.
- [ ] Validation errors are actionable.

### SKG-M2: MCP tool contract hardening

Required tools:

- [ ] `skills_list`
- [ ] `skills_search`
- [ ] `skills_inspect`
- [ ] `skill_read`

For each tool:

- [ ] Define input schema.
- [ ] Define stable JSON output schema.
- [ ] Return structured errors.
- [ ] Add unit/integration tests.
- [ ] Ensure active profile/catalog filtering is respected.

Acceptance criteria:

- [ ] A generic MCP client can list, search, inspect, and read skills.
- [ ] Tool output is stable enough for Agents Gateway to consume.

### SKG-M3: MCP resources

Define resource URIs:

```text
skill://{skill_id}/manifest
skill://{skill_id}/entrypoint
skill://{skill_id}/file/{path}
```

Todo:

- [ ] Register resource templates.
- [ ] Prevent path traversal.
- [ ] Enforce skill catalog visibility.
- [ ] Add tests for valid and invalid resource reads.

Acceptance criteria:

- [ ] MCP clients can read skill manifests and files through resource URIs.
- [ ] Path traversal attempts fail safely.

### SKG-M4: Config standardization

- [ ] Prefer `SKG_`-prefixed env vars.
- [ ] Support nested env vars such as `SKG_SERVICE__PORT`.
- [ ] Preserve backward compatibility for existing env vars where practical.
- [ ] Ensure precedence: CLI > env > YAML > defaults.
- [ ] Add config precedence tests.

Acceptance criteria:

- [ ] Custom config path works.
- [ ] Profiles/catalogs work from custom config.
- [ ] Production auth misconfiguration fails clearly.

### SKG-M5: Observability

- [ ] Improve `/inventory` schema.
- [ ] Track total skills and invalid skills.
- [ ] Track MCP tool calls and errors.
- [ ] Track request counts and durations.
- [ ] Add structured log events for skill scanning and tool calls.

Acceptance criteria:

- [ ] `/ready` explains readiness failures.
- [ ] `/metrics` changes after requests/tool calls.
- [ ] Logs include request IDs and do not expose secrets.

### SKG-M6: Docker and smoke test

- [ ] Add or update `scripts/smoke-test.sh`.
- [ ] Smoke test `/health`, `/ready`, `/version`, `/inventory`, `/metrics`.
- [ ] Smoke test all required MCP tools where practical.
- [ ] Ensure `docker compose up -d --build` works from a clean checkout.

Acceptance criteria:

- [ ] Smoke test exits nonzero on failure.
- [ ] Docker setup is reproducible from README instructions.

## Integration contract with Agents Gateway

Agents Gateway should consume Skills Gateway through stable MCP tools/resources rather than importing implementation code.

Minimum required contract:

- `skills_list` returns skill summaries.
- `skills_inspect` returns complete metadata and file tree.
- `skill_read` returns a specific skill file by path.
- Resource URIs expose manifests and files.

Future `skills-gateway` runtime in Agents Gateway should record the skill ID and version used for each task.
