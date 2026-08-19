# Application security

Use an explicit assurance target for substantial reviews. OWASP ASVS 5.0 is a
verification standard; Top 10 lists are awareness aids, not completeness claims.

## Identity and session boundary

- Prefer established authentication libraries and protocols. Validate token
  signature, issuer, audience, expiry, not-before time, and intended token type.
- Protect login, recovery, enrollment, credential change, and MFA flows against
  enumeration, credential stuffing, fixation, replay, and CSRF as applicable.
- Rotate session identifiers after authentication or privilege changes. Set
  cookie security attributes according to the actual same-site and HTTPS model.
- Require recent or stronger authentication for high-impact actions when the
  threat model warrants it. Invalidate or constrain existing sessions after
  security-sensitive account changes.

## Authorization and tenancy

- Start with object-level, property-level, and function-level authorization.
  Derive the subject from the verified identity, never a client-selected user ID.
- Enforce tenant scope in the shared data-access/service boundary and test with
  two distinct ordinary identities. Filtering a response after an unrestricted
  query is not an authorization control.
- Allowlist writable and returned fields. Prevent mass assignment and disclosure
  of internal, credential, recovery, billing, or role-management properties.
- Model workflow state: ownership alone may not permit approval, refund, export,
  invitation, role change, or other sensitive business actions.
- Deny by default. Test alternate HTTP methods, batch/GraphQL operations,
  background jobs, exports, and legacy endpoints.

## Input, output, and execution

- Parse into a strict schema and reject unexpected structure where practical.
  Bound strings, collections, nesting, numeric ranges, time windows, and cost.
- Use parameterized database APIs and structured process invocation. Never
  concatenate attacker-controlled data into SQL/NoSQL operators, shells, paths,
  templates, headers, or redirects.
- Encode for the output context. Treat rich HTML, Markdown, SVG, filenames, and
  downloaded content as active formats requiring explicit policy.
- Return minimal fields and stable generic errors; keep actionable detail in
  access-controlled logs with correlation IDs.

## Browser boundary

- Define the exact origin and credential model before setting CORS or CSRF
  controls. CORS is not authentication or server-side authorization.
- Use a restrictive, tested Content Security Policy as defense in depth. Avoid
  documenting one universal header value that breaks the application or creates
  a false guarantee.
- Keep durable authentication secrets out of script-readable browser storage
  when a server-managed session is feasible. Do not mistake storage choice for
  complete XSS resistance.
