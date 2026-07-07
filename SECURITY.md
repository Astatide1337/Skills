# Security

Skills Gateway authenticates MCP clients using Cloudflare Access JWTs or local development bypasses. It supports two deployment postures.

## Deployment Modes

### 1. Edge-Auth-Only Personal Mode

```
Internet → Cloudflare Access (identity/login gate) → Private Origin (127.0.0.1)
```

- Cloudflare Access protects the hostname at the edge.
- The origin is bound to `127.0.0.1` — not directly reachable from the public internet.
- App auth can be `dev-none` because the edge already enforces identity.
- Suitable for personal MCP tool usage.

### 2. Defense-in-Depth Production Mode

```
Internet → Cloudflare Access → Origin validates CF JWT (RS256/JWKS)
```

- Cloudflare Access protects the hostname at the edge.
- The app also validates the CF Access JWT (`cloudflare-access` mode) for defense in depth.
- If the edge is bypassed or misconfigured, the origin still rejects unauthenticated requests.
- Suitable for multi-user or zero-trust production deployments.

## Authentication Modes

| Mode | Behavior | Default Production |
|------|----------|-------------------|
| `cloudflare-access` | Real CF Access JWT verification (RS256 + JWKS + audience + issuer + expiry). No token bypass. | Yes |
| `internal-only` | Same as cloudflare-access, plus Docker internal-IP bypass (must be explicitly enabled). | No |
| `dev-none` | No authentication. NOT for production. | No |

## Cloudflare Access JWT Verification

In `cloudflare-access` and `internal-only` modes, every MCP request is authenticated. The `CloudflareAccessOAuthProvider.load_access_token()` method:

1. Fetches Cloudflare JWKS from `https://<team>.cloudflareaccess.com/cdn-cgi/access/certs`
2. Verifies JWT signature against the fetched public key (RS256 only)
3. Validates `aud` (audience) matches configured `CLOUDFLARE_AUD`
4. Validates `iss` (issuer) matches `https://<team>.cloudflareaccess.com`
5. Rejects expired, unsigned, wrong-audience, wrong-issuer, or malformed JWTs

There is no "accept any Bearer token" or "decode-only" path. PyJWT's `jwt.decode()` with `algorithms=["RS256"]` rejects `alg: none`.

## Internal Bypass

The `internal_bypass` flag (`AuthConfig.internal_bypass`, env `INTERNAL_BYPASS`) allows Docker container IP addresses (`172.*`, `10.*`, `192.168.*`) to bypass JWT authentication. This is:

- **Disabled by default** (`internal_bypass: false`)
- Only applicable in `cloudflare-access` or `internal-only` modes
- Clearly labeled as a bypass in configuration
- NOT recommended for publicly-facing deployments

If you enable `internal_bypass`, anyone on the same Docker network / RFC1918 network can call the MCP endpoint without authentication. Use only in trusted, isolated environments.

## /authorize Endpoint

The `/authorize` (OAuth authorization) endpoint generates authorization codes for MCP clients. This endpoint:

- Does NOT perform in-app JWT verification in `dev-none` mode
- MUST be protected by Cloudflare Access at the edge (tunnel/firewall policy) in production
- Relies on the Cloudflare Access application policy to control who can initiate the OAuth flow

Unauthenticated callers cannot reach `/authorize` if Cloudflare Access is properly configured on the domain.

## Path Traversal Protection

All file read operations (`skill_read`) enforce:

- Reject paths containing `..`
- Reject paths starting with `/`
- Resolve requested path relative to the configured skills directory
- Use `Path.resolve()` and `Path.relative_to()` to detect traversal attempts

## Protected vs Public Endpoints

### Protected (require auth in non-dev-none modes)

| Path | Method |
|------|--------|
| `/mcp` | POST (MCP protocol calls) |
| `/authorize` | GET (OAuth flow start) |
| `/token` | POST (token exchange) |
| `/register` | POST (client registration) |
| `/skills` | GET |
| `/inventory` | GET |
| `/metrics` | GET |
| `/docs/*` | GET |

### Public (no auth, any mode)

| Path | Method |
|------|--------|
| `/health` | GET |
| `/ready` | GET |
| `/version` | GET |
| `/.well-known/*` | GET (OAuth discovery) |

## Recommendations

1. Always use `cloudflare-access` mode in production
2. Configure Cloudflare Access application policy on your domain
3. Set `CLOUDFLARE_TEAM_DOMAIN` and `CLOUDFLARE_AUD` via environment
4. Never set `internal_bypass=true` on public deployments
5. Run `skills-gateway doctor` to verify configuration
6. Review access logs regularly

## Reporting

If you find a security issue, open a GitHub issue or contact the maintainers directly.