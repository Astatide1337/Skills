# Astatide Skills Gateway

This repository serves a reviewed, version-controlled Agent Skills catalog over Streamable HTTP at `/mcp`.

The service reads committed files and exposes four read-only MCP tools. It does not download, execute, or synchronize skills at runtime. The Cloudflare MCP Server Portal owns user authentication and aggregation. A separate bearer credential authenticates the Portal to this origin; Coolify builds and runs this Compose application and stores that credential.

## Catalog

The catalog contains 51 exported skills. The source repository, exact commit, source path, profile, and trust classification for every export are recorded in [`catalog.yaml`](catalog.yaml).

Profiles are `engineering-core`, `web-engineering`, `mcp-and-infrastructure`, `agent-manager`, `production-engineering`, `video-and-media`, `zero-token-architecture`, and `catalog-admin`.

The engineering profile includes the selected Superpowers workflow and Sentry `code-review`/`commit`. Web engineering includes Vercel React, composition-patterns, web-design, and CLI skills, Microsoft `playwright-cli` for browser interaction, test generation, screenshots, tracing, and request mocking, OpenAI `figma-generate-design` and the historical official `frontend-skill` for high-craft visual direction, Addy Osmani’s `frontend-ui-engineering` for accessible component architecture and responsive production UI, official shadcn/ui component composition and design-system guidance, Vercel `building-components` for composable accessible component APIs, design tokens, state, polymorphism, and publishing, plus Anthropic browser testing and frontend design. MCP/infrastructure includes Anthropic `mcp-builder` and OpenAI `cloudflare-deploy`. Agent-manager includes Matt Pocock’s specification, prototyping, domain-modeling, and handoff workflows. Production-engineering includes Addy Osmani’s source-driven, doubt-driven, simplification, security, and shipping workflows. Video-and-media includes Remotion’s official `remotion-best-practices` skill for timing, transitions, captions, audio, FFmpeg, silence detection, visualization, Three.js, sequencing, fonts, trimming, and rendering. Zero-token-architecture contains four local skills for secret boundaries, evidence-gated integration, least-privilege capability design, and exporting repeated reasoning into deterministic artifacts. Catalog-admin includes Sentry `skill-scanner`, Anthropic `skill-creator`, Superpowers `writing-skills`, and Vercel `find-skills`.

`next-best-practices` is not exported. Vercel’s current `next-skills` repository explicitly says it is no longer a skill: Next.js now delivers version-matched guidance through bundled docs and generated `AGENTS.md`/`CLAUDE.md` files. It remains recorded as blocked in `catalog.yaml`; no stale or invented replacement is included.

OpenAI removed `frontend-skill` from the current `openai/skills` branch. The catalog therefore pins the last official commit containing it and labels it `historical-official`; update or remove it when OpenAI publishes a successor.

## Zero-token-export policy

- No upstream API keys, OAuth tokens, or cookies are embedded in the image or exported skill content.
- The only application secret is the Portal-to-origin bearer credential supplied at runtime through `SKILLS_GATEWAY_AUTH_TOKEN`.
- Skills are static files baked into the image; the gateway performs no outbound requests after startup.
- Skill-bundled scripts are served as files but never executed by this MCP server.
- The gateway exposes only `skills_list`, `skills_search`, `skills_inspect`, and `skill_read`.
- Skills cannot call MCP tools themselves, and must not collect credentials, print secrets, add hidden telemetry, or instruct agents to export tokens.

The Sentry `skill-scanner` is included for catalog review, not as an automatic runtime security guarantee. Human review is required before changing `catalog.yaml`.

## Production architecture

```text
ChatGPT / Claude / Codex
          |
          v
Cloudflare MCP Portal: https://mcp.astatide.com/mcp
          |  owner OAuth, Access policy, server selection
          v
origin bearer auth -> skills-gateway:8091 -> committed /skills files
```

The `/mcp` origin requires `Authorization: Bearer <SKILLS_GATEWAY_AUTH_TOKEN>`. Health and version routes remain public for monitoring. The application has no user database or OAuth flow; owner identity is enforced by the Portal's Cloudflare Access policy.

## Local run

Prerequisites: Docker Engine, Docker Compose, and a random bearer credential of at least 32 characters exported as `SKILLS_GATEWAY_AUTH_TOKEN`.

Run the same definition used by Coolify:

```bash
export SKILLS_GATEWAY_AUTH_TOKEN="$(openssl rand -hex 32)"
docker compose up -d --build
docker compose ps
docker compose exec -T skills-gateway python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8091/health').read().decode())"
docker compose logs --tail=100 skills-gateway
docker compose down
```

The service is intentionally published only through Compose `expose`; in production, Coolify maps its domain to exposed port `8091`. The application does not join the Docker MCP Gateway network.

## Coolify deployment

The production service joins the host-local external `observability` network and exports traces and application metrics to Alloy over private OTLP/HTTP. Coolify may override the defaults with `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL`, `OTEL_TRACES_EXPORTER`, `OTEL_METRICS_EXPORTER`, and `OTEL_LOGS_EXPORTER`. No Grafana Cloud credential belongs in this application; Alloy owns the write-only cloud token.

Create a Docker Compose resource in the existing Gateway project using:

1. Repository: `https://github.com/Astatide1337/Skills-MCP-Gateway`
2. Branch: `main`
3. Compose file: `compose.yaml`
4. Service: `skills-gateway`
5. Port: `8091`
6. Domain: `https://skills.astatide.com`.
7. Add `SKILLS_GATEWAY_AUTH_TOKEN` as a locked secret. Generate a unique random value of at least 32 characters and do not reuse the Docker MCP Gateway token.

Coolify owns builds, runtime logs, restart policy, health checks, TLS, redeployment, and rollback to a previous Git commit. No host-side setup or repository `.env` file is required.

## Cloudflare Portal setup

In Cloudflare Zero Trust, add this service under MCP servers with:

```text
https://skills.astatide.com/mcp
```

Set its authentication type to bearer and provide the same `SKILLS_GATEWAY_AUTH_TOKEN` stored in Coolify. This credential is only for Portal-to-origin traffic; users continue to authenticate to the owner-only Portal with OAuth.

Keep the Portal owner-only policy and enable only the Skills Gateway server for your personal portal. The client-facing URL remains:

```text
https://mcp.astatide.com/mcp
```

The Portal can expose or hide individual upstream servers and tools. After adding the upstream, force a sync and verify that the four catalog tools appear. The Portal's owner OAuth is separate from the upstream origin bearer credential. [Cloudflare MCP Server Portals](https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/mcp-portals/)

For a no-downtime rollout, configure the bearer credential on the Cloudflare Skills Gateway MCP server first, then deploy the origin enforcement in Coolify. The existing origin ignores the added header until the authenticated release is live. For rotation, add the new credential to both control planes in one maintenance operation and immediately repeat the validation below.

## Validation and recovery

Validate the Compose file before publishing a change:

```bash
SKILLS_GATEWAY_AUTH_TOKEN=0123456789abcdef0123456789abcdef docker compose config --quiet
```

After deployment, check the Coolify health state and logs, then run:

```bash
curl -fsS https://skills.astatide.com/health
curl -sS -o /dev/null -w '%{http_code}\n' https://skills.astatide.com/mcp
curl -fsS -H "Authorization: Bearer $SKILLS_GATEWAY_AUTH_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke-test","version":"1"}}}' \
  https://skills.astatide.com/mcp
```

The unauthenticated MCP request must return `401`; the authenticated initialization must return a successful MCP response.

Recovery is deterministic: redeploy the last known-good Git commit in Coolify. Configuration and skills are backed up by Git; Coolify stores deployment state and Cloudflare stores Access/Portal configuration. If the origin bearer credential is exposed, rotate `SKILLS_GATEWAY_AUTH_TOKEN` in Coolify and the Skills Gateway MCP server configuration in Cloudflare.

## Updating skills

Review the upstream source and its license, checkout a new exact commit, replace only the selected exported directory, update `catalog.yaml`, validate frontmatter and the zero-token-export policy, then commit the diff. Do not add runtime downloaders or auto-update jobs. Dependency upgrades remain separate from skill updates.

## Security limitations

- The Docker image contains the committed skills and no runtime credentials.
- Skills are instructions, not a sandbox. Review every skill before merging it.
- The service requires a dedicated origin bearer credential while Cloudflare Access protects the owner-facing Portal.
- The VPS firewall should restrict ports 80/443 to Cloudflare IP ranges while preserving administrator access.
- The service exposes read-only catalog operations. It does not execute skill-bundled scripts.
- The Dockerfile pins both the Python base image and the UV builder image by digest.

## References

- [Agent Skills format](https://agentskills.io/specification)
- [OpenAI Skills catalog](https://github.com/openai/skills)
- [OpenAI frontend-skill at its last official commit](https://github.com/openai/skills/tree/30444aed500c00c85294d12074f6e3ee794f808a/skills/.curated/frontend-skill)
- [Official shadcn/ui skill](https://ui.shadcn.com/docs/skills)
- [shadcn/ui skill source](https://github.com/shadcn-ui/ui/tree/6cd3f4c65c361ab6554e06a77e6a0af9cf8b6e37/skills/shadcn)
- [Vercel building-components skill](https://github.com/vercel/components.build/tree/5719ce3c9df04265f8c12e4567c424c7c516b5e5/skills/building-components)
- [Vercel composition-patterns skill](https://github.com/vercel-labs/agent-skills/tree/a5343bd997c4cc4d8bf2ca61021bdc74b4d6c9d5/skills/composition-patterns)
- [Microsoft Playwright CLI skill](https://github.com/microsoft/playwright-cli/tree/72735e570555444aa1f0d13735f0a4cf4723b37f/skills/playwright-cli)
- [Matt Pocock prototype skill](https://github.com/mattpocock/skills/tree/fa460cbf095a893d14bf41d3db7798cada500259/skills/engineering/prototype)
- [Anthropic Skills catalog](https://github.com/anthropics/skills)
- [obra/superpowers](https://github.com/obra/superpowers)
- [Sentry Skills](https://github.com/getsentry/skills)
- [Vercel Agent Skills](https://github.com/vercel-labs/agent-skills)
- [Vercel Next.js Skills pointer](https://github.com/vercel-labs/next-skills)
- [Next.js agent skills](https://github.com/vercel/next.js/tree/canary/skills)
- [Remotion official skills](https://github.com/remotion-dev/skills)
- [Matt Pocock skills](https://github.com/mattpocock/skills)
- [Addy Osmani agent skills](https://github.com/addyosmani/agent-skills)
- [FastMCP Streamable HTTP](https://gofastmcp.com/servers/server)
- [Cloudflare MCP Server Portals](https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/mcp-portals/)
- [Coolify Docker Compose deployments](https://coolify.io/docs/applications/build-packs/docker-compose)
