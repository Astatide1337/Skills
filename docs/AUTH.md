# Authentication

Skills Gateway supports three auth modes.

## Modes

### `cloudflare-access` (default)

Full OAuth 2.0 flow with Cloudflare Access as the identity provider. This is the production-recommended mode.

**Required configuration:**
- `CLOUDFLARE_TEAM_DOMAIN` — Your Cloudflare Access team domain
- `CLOUDFLARE_AUD` — Your Cloudflare Access application audience tag
- `PUBLIC_BASE_URL` — The public URL where the gateway is accessible

**Behavior:**
- MCP clients authenticate via OAuth against Cloudflare Access
- Local tokens are issued after CF JWT validation
- Docker-internal IP bypass available via `internal_bypass: true`

### `dev-none`

No authentication. All requests are auto-authenticated. **NOT for production use.**

**Behavior:**
- All MCP tool calls succeed without any authentication
- A warning is logged at startup
- `/ready` passes auth config check

**Enabling:**
```bash
AUTH_MODE=dev-none skills-gateway run
# or
skills-gateway run --auth-mode dev-none
```

### `internal-only`

Auth bypass for requests from Docker-internal IP addresses (172.x, 10.x, 192.168.x). External requests still require Cloudflare Access auth.

**Behavior:**
- Internal Docker requests are auto-authenticated
- External requests go through Cloudflare Access flow
- Requires CF credentials for external auth

## Configuration

```yaml
auth:
  mode: "cloudflare-access"  # or dev-none | internal-only
  cloudflare_team_domain: "your-team.cloudflareaccess.com"
  cloudflare_aud: "your-audience-tag"
  public_base_url: "https://skills.yourdomain.com"
  internal_bypass: false
```

## Auth Endpoints

| Endpoint | Description |
|----------|-------------|
| `/.well-known/oauth-authorization-server` | OAuth server metadata |
| `/.well-known/oauth-protected-resource/mcp` | Protected resource metadata |

## Scaling Considerations

See [AUTH_SCALING_TODO.md](AUTH_SCALING_TODO.md) for limitations of in-memory OAuth state when running multiple instances.
