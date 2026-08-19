# Codebase security audit

Use this workflow for a repository-wide review. Remain read-only unless the user
separately authorizes remediation.

## 1. Bound the audit

- Establish repository root, requested revision, included applications,
  generated/vendored exclusions, deployment environments, and whether history,
  CI, infrastructure, and live behavior are in scope.
- Inventory languages, frameworks, entry points, package-manager roots,
  lockfiles, data stores, identity providers, external integrations, workers,
  deployment manifests, and public surfaces from repository evidence.
- Record unavailable components. Do not infer that an unseen service or
  configuration is safe.

## 2. Map architecture and trust

- Trace request, event, file, and job flows from external input through parsing,
  identity, authorization, business logic, storage, side effects, and output.
- Locate shared authentication, authorization, tenant-scoping, validation,
  serialization, logging, secret-loading, and outbound-request boundaries.
- Identify alternate routes: admin/debug endpoints, background workers,
  migrations, webhooks, imports/exports, scheduled jobs, legacy versions, and
  scripts with production access.

Build a compact coverage map linking each exposed surface to its enforcement
point and evidence. Use it to find missing paths rather than counting files.

## 3. Search for candidates safely

- Search for dangerous sinks and bypasses appropriate to the detected stack:
  dynamic queries, shell/process execution, unsafe deserialization, template or
  DOM injection, path construction, arbitrary URL fetches, redirects, weak
  randomness, disabled verification, permissive CORS, debug modes, and broad
  authorization fallbacks.
- Inspect credential-shaped assignments, environment access, logs, fixtures,
  manifests, CI variables, and history only when authorized. Report location and
  kind; never print a discovered secret value.
- Review dependency manifests, lockfiles, lifecycle scripts, container builds,
  CI includes/actions, and deployment configuration as executable supply-chain
  inputs.
- Treat searches and scanners as candidate generators. Confirm attacker control,
  reachability, missing control, affected environment, and impact in source.

Prefer repository-native analyzers and existing configuration. Do not install,
execute project code, fetch advisory data, inspect git history, or scan live
targets unless the requested mode authorizes it.

## 4. Inspect controls and tests

- Verify server-side object, property, function, tenant, and workflow-state
  authorization across every reachable path.
- Check strict boundary validation, output minimization/encoding, query/process
  parameterization, upload/fetch constraints, session handling, error behavior,
  rate/resource bounds, and audit events.
- Compare source defaults with production configuration without assuming either
  is deployed. Follow image/artifact identity when deployment is in scope.
- Inspect negative tests for anonymous, second-user/tenant, lower-role, malformed,
  replayed, duplicated, concurrent, and failure-path behavior. Coverage numbers
  do not prove security-property coverage.

## 5. Correlate and report

- Deduplicate multiple symptoms with one root enforcement failure.
- Classify each item as confirmed vulnerability, likely vulnerability requiring
  one bounded check, defense-in-depth gap, or hygiene observation.
- Rank by reachable impact and attacker prerequisites, not scanner severity
  alone. Keep speculative patterns out of the confirmed list.
- Cite exact path and symbol, trace source to sink/control, name the affected
  environment assumption, propose the smallest fix, and specify a regression test.
- End with audited coverage, excluded/unknown surfaces, tool limitations, and the
  highest-value next verification steps. Never claim the codebase is secure.
