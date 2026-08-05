# Astatide Skills Gateway

This repository serves a reviewed, version-controlled Agent Skills catalog over Streamable HTTP at `/mcp`.

The service reads committed files and exposes four read-only MCP tools. It does not download, execute, or synchronize skills at runtime. Cloudflare Access and the Cloudflare MCP Server Portal own production authentication and aggregation; Coolify builds and runs this Compose application.

## Catalog

The catalog contains 55 exported skills: 51 pinned upstream skills and 4 repository-owned zero-token architecture skills. The source repository, exact commit, source path, profile, and trust classification for every export are recorded in [`catalog.yaml`](catalog.yaml).

Profiles are `engineering-core`, `web-engineering`, `mcp-and-infrastructure`, `agent-manager`, `production-engineering`, `video-and-media`, `zero-token-architecture`, and `catalog-admin`.

The engineering profile includes the selected Superpowers workflow and Sentry `code-review`/`commit`. Web engineering includes Vercel React, composition-patterns, web-design, and CLI skills, Microsoft `playwright-cli` for browser interaction, test generation, screenshots, tracing, and request mocking, OpenAI `figma-generate-design` and the historical official `frontend-skill` for high-craft visual direction, Addy Osmani’s `frontend-ui-engineering` for accessible component architecture and responsive production UI, official shadcn/ui component composition and design-system guidance, Vercel `building-components` for composable accessible component APIs, design tokens, state, polymorphism, and publishing, plus Anthropic browser testing and frontend design. MCP/infrastructure includes Anthropic `mcp-builder` and OpenAI `cloudflare-deploy`. Agent-manager includes Matt Pocock’s specification, prototyping, domain-modeling, and handoff workflows. Production-engineering includes Addy Osmani’s source-driven, doubt-driven, simplification, security, and shipping workflows. Video-and-media includes Remotion’s official `remotion-best-practices` skill for timing, transitions, captions, audio, FFmpeg, silence detection, visualization, Three.js, sequencing, fonts, trimming, and rendering. Zero-token-architecture contains four local skills for secret boundaries, evidence-gated integration, least-privilege capability design, and exporting repeated reasoning into deterministic artifacts. Catalog-admin includes Sentry `skill-scanner`, Anthropic `skill-creator`, Superpowers `writing-skills`, and Vercel `find-skills`.

`next-best-practices` is not exported. Vercel’s current `next-skills` repository explicitly says it is no longer a skill: Next.js now delivers version-matched guidance through bundled docs and generated `AGENTS.md`/`CLAUDE.md` files. It remains recorded as blocked in `catalog.yaml`; no stale or invented replacement is included.

OpenAI removed `frontend-skill` from the current `openai/skills` branch. The catalog therefore pins the last official commit containing it and labels it `historical-official`; update or remove it when OpenAI publishes a successor.

## Zero-token-export policy

- No API keys, OAuth tokens, cookies, or environment variables enter the container.
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
          |  OAuth, Access policy, server selection
          v
Cloudflare Tunnel -> cloudflared -> skills-gateway:8091 -> committed /skills files
```

The origin must be protected by Cloudflare Access. The repository has no application-level OAuth or token store.

## Local run

Prerequisites: Docker Engine and Docker Compose.

Run the same definition used by Coolify:

```bash
docker compose up -d --build
docker compose ps
docker compose exec -T skills-gateway python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8091/health').read().decode())"
docker compose logs --tail=100 skills-gateway
docker compose down
```

The service is intentionally published only through Compose `expose`; in production, Coolify maps its domain to exposed port `8091`.

## Coolify deployment

Create a Docker Compose resource in the existing Gateway project using:

1. Repository: `https://github.com/Astatide1337/Skills-MCP-Gateway`
2. Branch: `main`
3. Compose file: `compose.yaml`
4. Service: `skills-gateway`
5. Port: `8091`
6. Do not assign a Coolify domain. The application is published only by its Cloudflare Tunnel.
7. Add `CLOUDFLARE_SKILLS_TUNNEL_TOKEN` as a Coolify runtime variable.

Deploy. Coolify owns builds, runtime logs, restart policy, health checks, redeployment, and rollback to a previous Git commit. `cloudflared` owns the outbound-only Cloudflare connection; no host-side setup or repository `.env` file is required.

## Cloudflare Portal setup

In Cloudflare Zero Trust, add this service under MCP servers with:

```text
https://skills.astatide.com/mcp
```

Keep the Portal owner-only policy and enable only the Skills Gateway server for your personal portal. The client-facing URL remains:

```text
https://mcp.astatide.com/mcp
```

The Portal can expose or hide individual upstream servers and tools. After adding the upstream, force a sync and verify that the four catalog tools appear. The Portal's OAuth is separate from the upstream Access service token. [Cloudflare MCP Server Portals](https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/mcp-portals/)

## Validation and recovery

Validate the Compose file before publishing a change:

```bash
docker compose config --quiet
```

After deployment, check the Coolify health state and logs, then run:

```bash
curl -fsS https://<skills-origin-hostname>/health
```

Recovery is deterministic: redeploy the last known-good Git commit in Coolify. Configuration and skills are backed up by Git; Coolify stores deployment state and Cloudflare stores Access/Portal configuration. Rotate the Cloudflare service token if it is exposed, then update the Portal upstream headers.

## Updating skills

Review the upstream source and its license, checkout a new exact commit, replace only the selected exported directory, update `catalog.yaml`, validate frontmatter and the zero-token-export policy, then commit the diff. Do not add runtime downloaders or auto-update jobs. Dependency upgrades remain separate from skill updates.

## Security limitations

- The Docker image contains the committed skills and no runtime credentials.
- Skills are instructions, not a sandbox. Review every skill before merging it.
- The service relies on Cloudflare Access for production authentication; a directly reachable unprotected origin would not be safe.
- Coolify must not publish a public domain for this application; the tunnel is the only ingress.
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
- [Cloudflare Access service tokens](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/service-auth/service-token/)
- [Coolify Docker Compose deployments](https://coolify.io/docs/applications/build-packs/docker-compose)
