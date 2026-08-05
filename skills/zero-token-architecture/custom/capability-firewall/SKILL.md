---
name: capability-firewall
description: Minimize an agent or MCP surface by inventorying capabilities, assigning least-privilege classes, shaping narrow read-only tools, and placing explicit approval gates around side effects. Use when designing or hardening tool-enabled systems.
---

# Capability firewall

Make the available capability set smaller than the underlying provider API. A tool is an authority boundary, not a convenience wrapper.

## Workflow

1. Inventory every tool, resource, prompt, endpoint, and credential it can reach.
2. Classify each operation as metadata/read, bounded read, reversible write, irreversible write, or administration.
3. Remove unused operations. Default-deny arbitrary URLs, arbitrary headers, shell execution, file-system traversal, credential discovery, and bulk export.
4. Shape each remaining tool around one bounded intent with typed inputs, bounded pagination, field selection, timeouts, and stable errors.
5. Require explicit user approval for writes and administration. Show target, scope, affected records, and whether the action is reversible before execution.
6. Add idempotency and dry-run behavior where a provider supports it. Make retries safe or disallow them.
7. Verify that unauthorized operations fail closed and that a tool cannot escalate by passing provider-specific escape hatches.

## Zero-token rules

- The firewall holds provider credentials; the agent receives neither credentials nor unrestricted provider responses.
- Do not return raw authorization headers, signed URLs, cookies, secret configuration, or unbounded provider payloads.
- Use opaque identifiers and server-side lookups for follow-up operations.
- Log decisions and outcome metadata, never secrets or full sensitive payloads.

## Output

Produce a capability matrix with operation, data exposed, credential scope, side-effect class, approval requirement, limits, and verification result. List removed or blocked operations so later additions require an intentional review.
