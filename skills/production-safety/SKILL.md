---
name: production-safety
description: Use whenever work touches production or production-like databases, persistent data, VPS hosts, Docker Compose or Podman services, Kubernetes/OpenShift or other clusters, GitHub/GitLab delivery workflows, GitOps controllers, infrastructure-as-code and its state, cloud IAM, certificates, networking, DNS, storage, queues, scheduled jobs, backups, migrations, observability, authentication infrastructure, deployment state, or any external system where a wrong assumption can cause data loss, downtime, security impact, or difficult rollback. Begin read-only, establish the real topology and intent, and never treat access as authorization to mutate or destroy state.
---

# Production Safety

Observe first. Change only from verified state.

For any request to approve deletion or another destructive action, lead with
the decision (`not approved` while material facts are unknown), then explicitly
enumerate the safety gate: exact identity and environment, consumers and active
writers, reclaim/deletion behavior, unique state, usable recovery evidence,
rollback, blast radius, and authorization for that exact action. Do not compress
these into “verify dependencies and backups”; name every missing gate.

## 1. Establish the operation

Before changing anything, state:

- **Target:** exact environment, host, cluster, service, database, or external system.
- **Intent:** inspect, copy, restore, migrate, move, reconfigure, deploy, repair, or delete.
- **Source of truth:** which system/data/state is authoritative.
- **Authorization:** what the user explicitly asked to change.

Preserve semantic distinctions such as **copy vs move**, **restore vs replace**, **test vs production**, and **diagnose vs modify**.

## 2. Start read-only

Inspect before writing:

- current topology and roles;
- dependencies and traffic paths;
- current configuration;
- declared desired state, reconciliation owner, infrastructure state backend, and pending plan/diff when applicable;
- storage/data state;
- health and recent events/logs;
- replication/backup state when relevant;
- identity, assumed role/service account, effective privileges, and credential lifetime when relevant;
- the exact object/resource that would be changed.

Do not mutate the system merely to discover how it is configured.

For infrastructure-as-code, GitOps, IAM, Kubernetes, or managed-database work, read `references/infrastructure-checks.md` and apply only the relevant section.

For this catalog owner's recurring VPS, container, repository-delivery, database,
or live end-to-end work, also read `references/operator-profile.md`. These are
evidence-based defaults, not claims about the current target; verify them each time.

### Execution-mode gate

Resolve the prompt's tool and network boundary before probing. In a text-only,
offline, plan-only, or no-command task, do not run `kubectl`, `oc`, `dig`,
`curl`, `openssl`, cloud CLIs, package managers, or identity probes. Use only
the supplied evidence, label live topology and identity as unknown, and list
the exact read-only commands an authorized operator would run later. Never
turn a failed probe into evidence that a production dependency is absent.

## 3. Separate facts from assumptions

Keep a short list:

- **Known:** directly observed current state.
- **Unknown:** material facts not yet verified.
- **Assumed:** hypotheses that must not justify a risky action.

If a material safety fact is unknown, investigate it before proceeding.
Authorization is also a fact: do not infer that access, a read-only credential,
or a successful identity check authorizes a write. Record the requested scope
and exact approved action separately from the credentials available.

For any dependency or removal review, map all consumers before changing the
source: workloads, service accounts, operators/controllers, scheduled jobs,
external-secret or backup systems, dashboards, and human runbooks. “No consumer
found” is a verification result only after those categories were checked; do
not treat an empty search or an unknown topology as proof of safe removal.

Treat controllers and state engines as active writers. A manual live change can be reverted by reconciliation, overwrite another writer, or leave declared and actual state divergent. Establish ownership and the supported change path before writing.

## 4. Classify the proposed action

### Read-only

Examples: status, logs, describe/get, queries that do not mutate state.

Proceed when authorized access exists.

### Reversible write

Examples: a scoped configuration change with a known rollback, a deployment update, creating a new isolated resource.

Proceed only when the user's task authorizes changing that system and the rollback is understood.

### Destructive or difficult-to-reverse

Examples:

- dropping or clearing data;
- deleting persistent storage;
- reinitializing or reconfiguring database topology;
- force operations;
- destructive migrations;
- replacing authoritative data;
- removing DNS/network paths;
- force-unlocking or directly editing infrastructure state;
- broadening IAM trust or permissions, creating long-lived credentials, or disabling reconciliation or policy gates;
- replacing or rotating certificates, keys, or secrets without proving every consumer has transitioned;
- deleting production resources.

Do **not** execute until all of the following are established:

1. exact target and role;
2. why the action is necessary;
3. affected dependencies;
4. whether unique data/state exists;
5. backup/recovery status;
6. rollback or restoration path;
7. blast radius if the assumption is wrong;
8. explicit user authorization for the destructive action.
9. controller/state-lock/concurrency status and whether another writer can race or revert the change.

## 5. Prefer the least risky path

- Prefer inspection over mutation.
- Prefer copy over move when the task is a copy.
- Prefer additive/reversible changes before destructive replacement.
- Prefer a test/UAT path before production when it provides meaningful evidence.
- Preserve the authoritative source until the replacement is independently verified.
- Avoid broad commands when a scoped command can accomplish the task.

## 6. Execute incrementally

For an authorized write:

1. capture pre-change state;
2. make one scoped change;
3. inspect the immediate result;
4. verify health and dependencies;
5. continue only if the observed state matches expectations.

Do not batch risky changes that make the cause of failure ambiguous.

## 7. Verify recovery and outcome

When relevant:

- verify backups are usable, not merely present;
- verify restored/copied record counts and errors;
- verify replication/topology after database changes;
- verify routes/connectivity after network changes;
- verify workloads and user-visible health after deployment changes.
- verify reconciliation converges to the intended revision without unexplained drift;
- verify alerts, audit events, and error signals remain usable through the change.

A successful command exit is not sufficient proof.

Distinguish proof layers explicitly: static checks, local integration, CI,
deployed service/API behavior, and user-visible browser behavior answer different
questions. Do not report one as proof of another.

## Stop conditions

Stop before writing if:

- environment identity is uncertain;
- topology or dependency assumptions conflict with live evidence;
- the requested operation changed meaning;
- backup/recovery state is unknown for a destructive action;
- the rollback path is unclear;
- the blast radius cannot be bounded;
- the proposed action exceeds the user's authorization.

Report the evidence and ask for the missing decision rather than guessing.

## Execution boundary

Match the task's requested mode and the tools it authorizes.

- For prompt-only tasks that explicitly forbid workspace or tool use, use only
  the supplied text. `Review-only`, `diagnose`, and `do not edit` prohibit
  mutation, not observation: inspect in-scope supplied files with read-only
  tools unless the user also forbids that inspection. If required evidence is
  absent after checking the declared scope, identify the smallest artifact needed.
- For workspace-write requests, read only declared inputs and write only the declared output paths. Do not broaden the scope, probe credentials, inspect evaluator or harness metadata, or use network/MCP unless the task explicitly authorizes it.
- Never claim that a command, file change, deployment, or verification happened unless it actually happened and is supported by observed evidence.
