# Security review checklist

Use this as a bounded review aid; it does not replace the project's threat
model or the `security-and-hardening` skill.

Escalate to `security-and-hardening` when the change touches identity,
authorization or tenant scope, credentials or sensitive data, interpreter or
network/file boundaries, third-party callbacks, dependency/build execution,
deployment privilege, or when any check below reveals a plausible attack path.
Use its codebase-audit workflow when the requested scope extends beyond the
change under review.

For each changed trust boundary, record the input, owner, validation, and
failure behavior. Check:

- authentication and authorization are enforced on the server-side path;
- tenant, object, and role scope are checked before reads and writes;
- secrets are absent from source, logs, fixtures, diffs, and error messages;
- external data is treated as untrusted before parsing, rendering, or use in a
  command/query;
- SQL, shell, template, path, and URL construction uses the project's safe
  parameterized/allowlisted API;
- redirects, CORS, cookies, CSRF, and upload limits match the deployment model;
- errors fail closed and do not disclose tokens, stack traces, or protected
  identifiers;
- dependency and lockfile changes have a documented source and review outcome.

For every failed check, cite the changed path/symbol or state that the artifact
was unavailable. Do not infer that a test suite proves authorization or secret
handling without inspecting the relevant boundary.
