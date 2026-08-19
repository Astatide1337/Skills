# Infrastructure checks

Apply only the relevant sections. Start from repository configuration and verify current provider behavior from official documentation when defaults, command semantics, or recovery guarantees matter.

## Infrastructure as code

- Resolve the exact root module or stack, workspace, account/project, region, backend, and state identity.
- Treat state and saved plans as sensitive artifacts. They may contain secrets even when values are marked sensitive.
- Require appropriate access control, encryption, versioning/recovery, and locking for shared state. Never bypass a failed lock or force-unlock unless ownership is proven.
- Establish current remote objects before trusting a plan. Review replacements, destroys, imports/moves, provider changes, and unknown values separately.
- Apply the reviewed plan artifact when supported; a later fresh plan may contain different actions.
- Avoid direct state-file editing. Use supported state operations with a backup and explicit object addresses.
- Treat providers, modules, provisioners, external data, and hooks as executable trust boundaries: planning can access credentials and execute code.

## GitOps and reconcilers

- Identify the declarative source, exact revision, controller, scope, sync policy, health model, drift status, and last successful reconciliation.
- Change declared source rather than live state unless an emergency procedure explicitly requires otherwise.
- A live hotfix is incomplete until reconciled back into declared source or deliberately reverted.
- Do not disable reconciliation, pruning, policy, or health gates without a bounded duration, restoration step, and approval.
- Verify convergence to the intended revision and check for reconcile loops, unexpected pruning, or competing field owners.

## Kubernetes and clusters

- Verify context, cluster identity, namespace, resource UID, field managers/controllers, and manifest revision.
- Treat `diff` and server-side dry-run as read-like evidence with write-class authorization requirements; preview permission does not authorize apply.
- Review rollout strategy, probes, minimum availability, quota, scheduling, image identity, events, and traffic path.
- A completed rollout proves controller conditions, not user-visible application health. A stalled Deployment is reported; Kubernetes does not automatically roll it back.
- PodDisruptionBudgets govern voluntary evictions, not every outage or workload rollout. Check workload-specific update strategy too.
- Base64 does not protect Secret values. Account for encryption at rest, RBAC, indirect access through pod creation, external-secret reconciliation, rotation overlap, and log exposure.

## IAM and credentials

- Map the principal, trust policy, inherited permissions, resource policies, impersonation/pass-role paths, and effective scope.
- Prefer workload identity, federation, impersonation, or other short-lived credentials over static keys.
- Grant the smallest role at the smallest resource scope. Treat policy administration and service-account impersonation as escalation paths.
- Rotate in stages: activate replacement, move and verify every consumer, disable old credential, observe, then delete.
- Use audit logs and access analysis to find external, internal, and unused access. No recent use alone does not prove safe removal.

## Databases and persistent state

- Distinguish project, branch/database, endpoint, role, schema, environment, region, and authoritative writer.
- Test risky queries and migrations on an isolated current copy when meaningful; prove it cannot route production traffic or credentials.
- Verify the configured recovery window, not a remembered default. Prove restoration to an isolated target when feasible.
- Treat code rollback and data rollback separately. Prefer expand/contract migrations compatible with both application versions.
- For point-in-time or branch restore, record which endpoint moves, which old state remains, how completion is observed, and cleanup cost.

## Network, DNS, certificates, queues, and schedules

- Map producers, consumers, TTLs/caches, routing/failover, certificate/key holders, retry/dead-letter behavior, ordering, concurrency, and duplicate-delivery semantics.
- Rotate certificates and keys with overlap; verify every consumer before revocation.
- Lower DNS TTL early enough to take effect; verify authoritative answers and representative resolver/application paths.
- Pause or drain producers before incompatible queue changes; preserve dead-letter and replay capability.
- For scheduled jobs, prove singleton/concurrency behavior, missed-run semantics, time zone, retry bounds, and idempotency.

## Observability and recovery

- Define pre-change baselines and success/failure signals before writing.
- Preserve audit logs and telemetry through the operation; changing monitoring with the system can erase recovery evidence.
- Test alerts and recovery procedures proportionately to risk. A configured backup, dashboard, or alert does not prove restoration, visibility, or notification works.
