---
name: zero-token-boundary
description: Design or review agent workflows so secrets, credentials, cookies, and unnecessary sensitive data never enter model context, tool arguments, logs, or generated artifacts. Use for MCP, API, automation, and integration architecture.
---

# Zero-token boundary

Treat the model as an untrusted data plane. The model may reason over a narrow result, but it must not receive credentials or become the transport for secrets.

## Workflow

1. Draw the request path from user to tool to provider and label every boundary.
2. Classify each field as public, operational, sensitive, or secret. Reject any design that passes secret material through prompts, MCP arguments, URLs, logs, errors, or files in the working tree.
3. Replace secret-bearing values with server-side capability references. Resolve credentials only inside the provider adapter or platform secret store.
4. Return the smallest useful projection: identifiers, status, selected fields, and bounded text. Prefer opaque handles for large or sensitive results.
5. Set explicit limits for size, fields, destinations, retention, and lifetime. Default to no outbound destination and no persistence.
6. Redact before logging or returning errors. Never “temporarily” print a token to debug authentication.
7. Verify the boundary with a negative test: secret values must not appear in tool input/output, logs, traces, saved files, or repository changes.

## Design rules

- A token is a capability held by infrastructure, not data available to an agent.
- Server-side fetch plus a narrow projection is safer than asking an agent to fetch or relay raw content.
- Do not accept arbitrary URLs, headers, shell commands, or credential names from an agent.
- If a secret would be required in model context, stop and redesign the interface.
- State residual risks explicitly when a platform exposes injected environment variables through inspection; do not call that a true secret boundary.

## Output

Produce a boundary table with: actor, data allowed, credential owner, destination allow-list, retention, and verification evidence. Mark unresolved assumptions as blocked rather than filling them with guessed behavior.
