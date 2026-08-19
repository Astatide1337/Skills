---
name: security-and-hardening
description: Threat-model, review, implement, or verify security controls for application code, APIs, authentication and authorization, tenant data, secrets, dependencies, CI/CD, containers, Kubernetes/OpenShift, webhooks, uploads, server-side fetches, and LLM or agent features. Use for security audits, security-sensitive feature work, vulnerability remediation, abuse-case analysis, or hardening before release. Prioritize exploitable trust-boundary failures, preserve explicit read-only boundaries, and distinguish code security from authorization to change live systems.
---

# Security and Hardening

Secure the real boundary, then prove the control.

## 1. Establish scope and mode

Record:

- the requested mode: review, design, implement, verify, or remediate;
- the assets and security properties that matter;
- the exposed entry points and identities;
- the deployment and data environments in scope;
- the evidence available and what remains unknown.

Treat `review-only`, `do not edit`, `do not commit`, `do not push`, and `do not
deploy` as hard authorization boundaries. Access does not authorize mutation.

Use `production-safety` for live-system changes, credentials, production data,
or destructive remediation. Use `verify-work` to report what testing proves.

## 2. Model the attack path

Trace each relevant flow:

`attacker-controlled input -> parser/validator -> identity -> authorization -> side effect -> stored/output data`

For every trust boundary, identify:

- attacker and preconditions;
- asset and security property at risk;
- concrete abuse case;
- existing control and where it is enforced;
- bypasses, alternate paths, retries, races, and failure behavior;
- evidence that would demonstrate exploitability or mitigation.

Prioritize actual attack paths over an undifferentiated checklist. Do not call a
pattern vulnerable without showing attacker influence and a reachable sink; do
not call it safe because a scanner or happy-path test passes.

## 3. Apply the relevant control set

Read only the references needed for the task:

| Surface | Reference |
|---|---|
| APIs, browser applications, auth, tenant/object access, sessions, input/output | `references/application-security.md` |
| Webhooks, uploads, server-side URL fetches, third-party data, queues | `references/untrusted-integrations.md` |
| Dependencies, lockfiles, CI/CD, build artifacts, containers, clusters | `references/supply-chain-and-runtime.md` |
| Secrets, sensitive data, logging, backups, environments | `references/secrets-and-data.md` |
| LLM prompts, retrieval, model output, tools, agents | `references/agent-security.md` |

Discover the actual framework, package manager, authentication model, database,
container runtime, and delivery path. Do not assume Express, npm, MongoDB,
PostgreSQL, Docker, or Kubernetes from familiarity alone.

## 4. Design controls at the enforcement point

- Authenticate the caller and bind the credential to its intended audience,
  issuer, lifetime, and transport.
- Authorize every object, property, function, and sensitive business action on
  the server using the authenticated subject and current resource state.
- Parse once into a strict schema; allowlist mutable and returned fields; bound
  size, depth, rate, concurrency, and cost.
- Keep untrusted data out of interpreters. Use parameterized or structured APIs
  for queries, processes, templates, paths, and redirects.
- Minimize privilege, credential lifetime, exposed data, network reachability,
  and failure detail.
- Make externally retried side effects authentic, replay-aware, and idempotent.
- Fail closed for security decisions while preserving diagnosable audit events.

Framework defaults are inputs to the analysis, not proof of enforcement.

## 5. Implement narrowly

For an authorized change:

1. capture the failing abuse case or security invariant;
2. place the control at the narrowest shared enforcement boundary;
3. avoid unrelated dependency, auth, schema, or infrastructure changes;
4. preserve compatibility or provide an explicit migration path;
5. add negative tests before relying on the happy path;
6. inspect the diff for secret exposure and weakened adjacent controls.

Never copy real credentials or production personal data into tests, prompts,
fixtures, logs, screenshots, or reports. If a secret may have escaped, treat
rotation as a live-system operation under `production-safety`.

## 6. Verify adversarially

Test the control at the boundary it claims to protect. As relevant, cover:

- anonymous, valid, expired, revoked, and wrong-audience identities;
- a second ordinary user or tenant attempting the same object operation;
- role, method, field, identifier, and workflow-state manipulation;
- malformed, oversized, duplicated, replayed, concurrent, and rate-bound input;
- alternate endpoints, background workers, webhooks, redirects, and error paths;
- dependency/build provenance and the deployed configuration actually in use;
- absence of sensitive values from responses, logs, artifacts, and client state.

Use isolated accounts and owned fixtures. Do not probe third-party or production
systems beyond explicit authorization. A unit test, static analyzer, dependency
audit, CI pass, health endpoint, and live adversarial test are distinct evidence
layers; report them separately.

## 7. Report by risk

For each finding, provide:

- severity and confidence;
- exact evidence and affected boundary;
- attacker prerequisites and plausible impact;
- smallest credible remediation;
- verification and regression test;
- remaining uncertainty or accepted risk.

Lead with exploitable authorization, credential, code-execution, cross-tenant,
or sensitive-data failures. Do not inflate theoretical issues or bury serious
findings beneath generic hygiene.

## Stop conditions

Stop and report the gap when the target, identity model, tenant boundary,
authoritative environment, sensitive-data classification, or authorization to
test is unclear. Never turn missing evidence into a security guarantee.
