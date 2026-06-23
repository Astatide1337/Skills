# Security Considerations

## Authentication

- **`dev-none` mode provides no authentication.** Never use in production.
- **`cloudflare-access` mode** is the recommended production auth. It validates JWTs from Cloudflare Access.
- **`internal-only` mode** allows Docker-internal IP bypass. Use only on trusted networks.

## Secrets Management

- Secrets (`CLOUDFLARE_TEAM_DOMAIN`, `CLOUDFLARE_AUD`) must be provided via environment variables or `.env` file
- `.env` is in `.gitignore` and must never be committed
- `.env.example` documents all variables with empty defaults

## No Secrets in Logs

Structured logging explicitly avoids logging:
- JWTs and access tokens
- Refresh tokens
- Client secrets
- Audience tags

## Path Traversal Protection

The `skill_read` tool rejects paths containing `..` or starting with `/`.

## Docker Security

- Skills directory is mounted read-only (`:ro`)
- Container runs as non-root by default with the Python slim image
- Healthcheck uses `curl` for liveness monitoring

## In-Memory OAuth State

Current implementation stores OAuth tokens in memory. This is sufficient for single-instance deployments. See [AUTH_SCALING_TODO.md](AUTH_SCALING_TODO.md) for multi-instance considerations.

## Reporting Security Issues

If you discover a security vulnerability, please report it responsibly.
