# Testing

## Commands

```bash
make test      # Run all tests
make verify    # Compile check + test
make smoke     # Start service, curl endpoints, stop
```

Or directly:

```bash
uv run pytest tests/ -v
```

## Test Categories

### Unit Tests

Pure function tests for config, skill parsing, validation, metrics, and logging.

```bash
uv run pytest tests/test_config.py tests/test_skills.py tests/test_skills_extra.py tests/test_metrics.py tests/test_logging.py -v
```

### CLI Tests

Tests for the `skills-gateway` CLI commands.

```bash
uv run pytest tests/test_cli.py -v
```

### Endpoint Tests

HTTP tests against a running Starlette app in dev-none mode.

```bash
uv run pytest tests/test_endpoints.py -v
```

### Auth Config Tests

Tests for all auth modes and validation.

```bash
uv run pytest tests/test_auth.py -v
```

### Test Fixtures

Located in `tests/fixtures/skills/`:

- `valid-skill/SKILL.md` — Complete frontmatter with all required and recommended fields
- `invalid-skill/SKILL.md` — Missing the required `name` field
- `bad-yaml/SKILL.md` — Unparseable YAML frontmatter

## Adding Tests

1. Create `tests/test_<feature>.py`
2. Use `pytest` fixtures (`tmp_path`, `monkeypatch`) for isolation
3. Run: `uv run pytest tests/ -v`

## Smoke Tests

Smoke tests start the service, curl endpoints, and verify responses:

```bash
make smoke
```

This requires `~/skills` to exist with at least one valid skill.
