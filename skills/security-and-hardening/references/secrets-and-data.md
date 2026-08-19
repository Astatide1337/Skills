# Secrets and data

## Classification and minimization

- Identify credentials, tokens, personal data, tenant data, financial records,
  recovery material, encryption keys, and operationally sensitive metadata.
- Collect, return, log, cache, replicate, and retain only what the product needs.
  Define deletion, export, backup, and incident requirements before adding a new
  sensitive field.

## Secret handling

- Keep secrets out of source, patches, prompts, URLs, screenshots, fixtures,
  images, artifacts, shell history, and logs. Never print a whole environment file
  to retrieve one value; inspect only the named value or metadata required.
- Prefer short-lived workload identity. Scope secret access by workload and
  environment; separate preview/test and production values.
- Do not rely on `.gitignore`, masking, base64, or encryption-at-rest alone.
  Account for process listings, crash dumps, child processes, backups, caches,
  support tooling, and anyone able to create a workload using the secret.
- If exposure is plausible, revoke or rotate first using `production-safety`,
  then remove the value from current files and history. History rewriting alone
  does not invalidate a credential.

## Storage, logging, and cryptography

- Use maintained platform cryptography and key-management facilities; do not
  invent algorithms or encode passwords with reversible encryption.
- Select password hashing and parameters from current framework/platform guidance
  and tune for the deployment rather than hard-coding a universal work factor.
- Encrypt sensitive transport and storage where the threat model requires it,
  while separately enforcing authorization and key access.
- Structure logs around security events and correlation IDs. Redact or omit
  credentials, session material, request bodies, database URLs, and unnecessary
  identifiers. Test redaction failure paths.
- Treat backups, exports, analytics, replicas, and test copies as additional data
  systems with their own access, retention, deletion, and restoration controls.
