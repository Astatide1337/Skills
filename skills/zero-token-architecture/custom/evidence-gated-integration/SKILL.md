---
name: evidence-gated-integration
description: Build or review an external integration using primary-source evidence, exact versioned contracts, read-only verification, and an explicit blocked state for anything unproven. Use for MCP servers, OAuth, APIs, webhooks, and deployment integrations.
---

# Evidence-gated integration

Do not promote a plausible integration to production. Promote only a reproducible contract supported by current primary evidence.

## Workflow

1. Define the smallest desired capability and its non-goals.
2. Find the provider’s current official documentation, source, schema, or tests. Record URL, repository, exact commit or release, endpoint, transport, authentication method, scopes, and expected response shape.
3. Separate facts observed in sources from inferences and local observations. An inference is not an implementation contract.
4. Prefer a read-only probe or metadata call. Never use verification to create, delete, publish, modify, or send external data.
5. Capture concise evidence: command or request shape, status, sanitized response, and timestamp. Remove credentials and personal data before storing it.
6. Test failure modes: missing secret, invalid scope, wrong transport, unavailable endpoint, malformed response, timeout, and partial registration.
7. Record one of `verified`, `partially verified`, or `blocked`. A blocked integration gets no speculative configuration.

## Rules

- Pin source versions and do not copy a stale example merely because its shape looks familiar.
- Do not invent image names, flags, endpoints, headers, OAuth redirect URIs, or environment variables.
- Keep evidence outside runtime secrets and never paste bearer tokens into test output.
- If the official source does not prove a behavior, say exactly what remains unknown and what observation would resolve it.
- The final artifact must be runnable without an agent making a new inference.

## Output

Return a compact integration record: capability, source evidence, pinned version, contract, auth, read-only verification, result, and remaining blocker. Include the exact next human action only when required.
