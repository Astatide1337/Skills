# Migrate / operate / release / incident

## When

Use for an upgrade, data or contract migration, release, or incident response
that touches production-like infrastructure, persistent state, credentials,
or an external service. A plan-only request stops before mutation.

Read [`production-safety`](../../production-safety/SKILL.md) first; add
[`security-and-hardening`](../../security-and-hardening/SKILL.md) for secrets,
identity, untrusted inputs, or permissions, and [`verify-work`](../../verify-work/SKILL.md)
for the claimed result.

## Inputs to establish

- exact target/environment, revision/versions, owner/controller, identity and
  authorization;
- topology, consumers, active writers/reconciliation, data/contracts,
  backups/recovery, health, and current failure/impact;
- operation mode, blast radius, sequencing, rollback, and stop conditions.

## Steps and decision points

1. Start read-only. Inspect authoritative desired and actual state, dependencies,
   versions and migration notes with the permitted read tools. An authorized
   `kubectl get` is inspection; it is not an `apply`. Never infer “production”
   or “latest.”
2. For upgrades, update only required callers/configuration and run compatibility
   checks. For migrations, validate representative data, completeness,
   idempotency/retry, and recovery before executing authorized steps.
3. For a release, identify the exact artifact and explicit release authority,
   then use the existing delivery path and observe revision/health. For an
   incident, stabilize with the least disruptive authorized action, preserving
   evidence, then investigate root cause separately.
4. Execute one scoped change at a time, inspect immediate state, and verify
   convergence, dependencies, alerts, and the requested behavior. A build or
   merge does not prove a deployment.

## Failure and recovery

If target identity, consumers, writer ownership, recovery, rollback, or
authorization is unknown, stop before mutation and report the exact gap. An
ambiguous/failed write is inspected before retrying. Report mitigation separately
from unresolved root cause; do not expose secrets to guess a path.

## Completion evidence

Return achieved state, exact versions/revisions, observations at the relevant
runtime layer, recovery/rollback status, remaining risk, and deferred steps.
Keep static, CI, deployed, and user-visible evidence distinct.

## Example

Upgrade a pinned library by reading its version-matched migration notes,
updating the affected caller, running compatibility tests, and reporting the
tested version; do not deploy without a separate release request.

## Near-miss

“Plan a production migration; do not execute it” inventories consumers and
recovery steps and may use authorized read-only inspection, but does not run
mutating commands such as `kubectl apply`, mutate data, or claim a rollout.
