# Auth Scaling Considerations

## Current State

Skills Gateway stores OAuth state in memory:

- Client registrations (`self._clients`)
- Authorization codes (`self._codes`)
- Access tokens (`self._access_tokens`)
- Refresh tokens (`self._refresh_tokens`)

This is acceptable for single-instance deployments.

## Scaling Limitations

In-memory OAuth state means:

- Tokens issued by one instance are not valid on another
- Client registrations are lost on restart
- Multiple replicas cannot share auth state
- No persistence across deployments

## Future Improvements

When horizontal scaling is needed, consider:

1. **External token store** — Redis or Valkey for shared token/state storage
2. **Database-backed client registry** — PostgreSQL or SQLite for client registrations
3. **Stateless JWT validation** — Rely solely on Cloudflare Access JWT verification (already supported) instead of local token storage
4. **Session affinity** — If multiple instances, route same client to same instance

## Recommended Path

For most deployments, the Cloudflare Access JWT path is already stateless. If `cloudflare-access` mode is used with valid CF tokens, no in-memory state is needed for token validation. The in-memory fallback is only for the local OAuth flow.

## TODO

- [ ] Add Redis token store option
- [ ] Add PostgreSQL client registry option
- [ ] Document multi-instance deployment patterns
- [ ] Add token revocation across instances
