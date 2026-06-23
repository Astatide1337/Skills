# Troubleshooting

## Gateway won't start

**Symptom:** `skills-gateway run` exits immediately.

**Checks:**
1. Run `skills-gateway doctor` to validate configuration
2. Verify `SKILLS_DIR` exists and contains valid skill directories
3. If using `cloudflare-access` mode, verify `CLOUDFLARE_TEAM_DOMAIN` and `CLOUDFLARE_AUD` are set

## Auth errors in production

**Symptom:** "Missing cloudflare_team_domain" or "Missing cloudflare_aud"

**Fix:**
```bash
export CLOUDFLARE_TEAM_DOMAIN="your-team.cloudflareaccess.com"
export CLOUDFLARE_AUD="your-aud-tag"
```

Or switch to dev mode for local testing:
```bash
AUTH_MODE=dev-none skills-gateway run
```

## Skills not showing up

**Symptom:** `/inventory` returns empty list, `skills_list` returns no skills.

**Checks:**
1. Verify `SKILLS_DIR` points to the correct directory
2. Each skill must have a `SKILL.md` file with valid YAML frontmatter
3. Required fields: `name`, `description`, `metadata.version`
4. Run `skills-gateway validate --skills-dir /path/to/skills` to check for errors
5. If a profile is active, verify the skill is in the profile's skill list

## Invalid skill errors

**Symptom:** Log shows `skill_invalid` events.

**Fix:**
- Check the skill's `SKILL.md` frontmatter for missing required fields
- Run `skills-gateway validate` to see specific errors
- Common issues: missing `name`, `description`, or `metadata.version`

## Docker healthcheck failing

**Symptom:** Container keeps restarting or shows `unhealthy`.

**Checks:**
1. `curl http://localhost:8091/health` from inside the container
2. Check logs: `docker compose logs skills-gateway`
3. Verify port 8091 isn't already in use on the host
4. Verify `.env` file exists with required variables

## Port already in use

**Symptom:** `Address already in use` error.

**Fix:**
```bash
skills-gateway run --port 8092
# or
PORT=8092 skills-gateway run
```

## Profile or catalog not found

**Symptom:** "Unknown active profile" or "Unknown active catalog" error.

**Fix:**
- Ensure the profile/catalog is defined in `skills-gateway.yaml`
- Check for typos in the profile/catalog name
- Run `skills-gateway doctor` to validate

## Metrics endpoint returns empty

**Symptom:** `/metrics` returns no data.

**Fix:**
- Verify `observability.metrics_enabled` is not set to `false`
- Metrics require at least one request to populate counters

## Tests failing

**Symptom:** `pytest` shows failures.

**Common causes:**
- `.env` file loaded at import time — tests use `monkeypatch.delenv()` to isolate
- If adding new env vars, update the `CF_ENV_VARS` tuple in `test_cli.py`
- Run `uv run pytest tests/ -v` for verbose output
