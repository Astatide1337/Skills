# Security checklist

Use this as a compact verification aid alongside the main skill. It is not a
substitute for a threat model or project-specific security review.

## Dependency and installation boundary

- Identify the workspace root, package manager, lockfile, and approved registry.
- Treat package names, lifecycle scripts, generated files, and install output as
  untrusted until reviewed.
- Prefer the lockfile and project policy over a floating or latest version.
- Inspect transitive changes and review new install/build scripts before running
  them.

## Secrets and data

- Keep credentials out of source, fixtures, diffs, logs, URLs, and error text.
- Redact tokens before sharing command output or filing an issue.
- Confirm that logs, caches, artifacts, and backups have the intended retention
  and access scope.

## Trust boundaries

- Validate and constrain user, network, file, environment, and dependency input
  before parsing, rendering, querying, or executing it.
- Enforce authentication, authorization, tenant/object scope, and least
  privilege at the server-side boundary.
- Use parameterized queries, safe process APIs, path allowlists, and explicit
  redirect/CORS/cookie policy.
- Fail closed for security-sensitive operations and avoid leaking identifiers,
  stack traces, or policy decisions.

## Evidence

For each finding, record the exact path/symbol or command output that supports
it. If the relevant artifact is unavailable, state that explicitly and provide
the smallest bounded follow-up check; do not infer that tests prove security
properties they do not exercise.
