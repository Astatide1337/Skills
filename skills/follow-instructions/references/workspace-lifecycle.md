# Implementation workspace and resource lifecycle

Read when allocating, resuming or retiring an implementation workspace. This
is a proposed operational contract and requirements for future owner integration.
It installs no service, cleanup hook or lease mechanism. Mechanical guarantees
below are obligations of the actual allocator/resource owner, not capabilities
provided by these instructions. If support is unavailable, retain affected
state and report the missing capability; do not claim cleanup completed.

## Scope and routing

Default implementation to a task-owned Git worktree or isolated cloud workspace.
Reuse the task's scoped workspace on resume; an existing isolated checkout is
valid. Use the harness allocator and owner when available. Do not create a
nested worktree merely to satisfy this default. Read-only investigation,
explanation and review do not require allocation or retirement. An ordinary
small fix in an already scoped workspace needs no additional allocation ritual.

Follow the user's execution preference when the actual tools, repository access
and runtime support it. For this user, prefer Codex Cloud or kagent, the native
agent-work libvirt VM (`kagent-vm` on `sohim`), to move execution off the laptop.
kagent does not mean the kagent.dev Kubernetes framework. State the execution
host and any laptop fallback. T3 Code is the primary interface; a T3 thread or
delegation receipt alone does not prove remote execution. Verify the worker's
actual host/provider identity before claiming that work ran remotely.

Use [Fleet](https://github.com/Astatide1337/fleet)'s README,
[environment](https://github.com/Astatide1337/fleet/blob/main/docs/environment.md),
[operations](https://github.com/Astatide1337/fleet/blob/main/docs/operations.md)
and [kagent record](https://github.com/Astatide1337/fleet/blob/main/machines/kagent.md)
for machine procedures. Keep versions, endpoints and setup there. This contract
does not authorize remote setup or assert that an integration is verified.

## One owner and a durable record

For each task, one lifecycle owner coordinates allocation, acquisition/resume
and retirement across its participating machines and agents. Reuse the actual platform's task
record and resource controls; do not introduce a parallel service or ledger.
Separate resource owners may perform effects, but the lifecycle owner journals
their results. Record allocation intent durably before creating anything, then
persist exact identities as each effect succeeds, including partial allocation.
The record and recovery journal must survive removal of the workspace and its
task resources. Never store secrets in them.

The minimum information, using the owner's existing representation, is:

- Task and responsible owner; actual host/provider and engine identity;
  canonical repository and workspace paths or provider workspace identity.
- Intended base and implementation head; current head on acquisition; intended
  PR/MR, target and verified merge identity/method when available.
- Current lifecycle state, acquisition/lease holder and fencing version,
  allocation intent, completed effects and outstanding recovery steps.
- Each resource's exact identity, actual owner, creation association, consumers
  and declared disposal policy. Classify disposable, persistent or shared at
  creation; unknown classification requires retention.
- Evidence, retained data and recovery locations outside disposable state,
  retention reason and the next reconciliation action.

An interrupted allocation must be discoverable from intent and the real
allocator's creation records. If an effect's identity cannot be recovered,
retain possible matches and report ambiguity rather than deleting by name.

## States and authority

| State | Required transition evidence |
| --- | --- |
| Allocating | Durable intent exists; enter active after identities and acquisition are recorded. Interrupted effects remain recoverable. |
| Active / paused | Acquisition authorizes use; pause retains workspace and data. Resume uses the same owner protocol and rechecks identities. |
| Retiring | Eligibility is verified and exclusive retirement authority fences new and stale users before deletion starts. |
| Pending / retained | A machine, owner or check is unavailable, recovery is incomplete, or data requires preservation. Record the reason and retry/decision needed. |
| Retired | Exact disposable targets are verified absent, allocator metadata agrees, and a durable tombstone identifies completed retirement. |

Completion of an agent turn, an idle process list or lease expiration is not
deletion authority. No running process does not imply no lease. Idle, paused
and review-needed work is retained or escalated for a disposition decision under
the owner’s retention policy. Policy expiry does not establish retirement
eligibility or authorize deleting unmerged work.

Retirement requires a verified merge into the intended target, verified completion
and delivery to the intended durable target for non-merge work, or explicitly
authorized abandonment, plus safe disposition of all current data. Completion
alone does not authorize deleting the sole copy of a local-only deliverable. For squash
or rebase merges, associate the original submitted head with the actual merge
result using authoritative PR/MR evidence; ancestry alone may not show it.
Compare the current workspace head with that submitted head. Preserve later
commits and unpublished refs unless separately integrated or explicitly
authorized for disposal; a merged PR does not cover subsequent work.

Inspect tracked changes, untracked and ignored files, unpublished commits and
named databases before retirement. A clean Git status is insufficient. Keep
unknown or persistent data until preservation or disposal is resolved. Never
remove a primary checkout or a path whose identity is unverified.

## Acquisition and retirement protocol

Acquisition/resume and retirement must share an owner-enforced exclusive lease
and fencing mechanism. Every actor that can resume, mutate or delete must honor
it. Retirement denies new acquisition and rejects stale holders throughout
deletion. A local lock is sufficient only when it actually covers every actor;
it does not establish exclusion across independent machines or providers.

1. Reconcile the durable record with the actual host, allocator and resource
   owners. Gather merge or delivery evidence and data inventories. Evidence may be copied
   outside the workspace before taking the exclusive lease.
2. Acquire exclusive retirement authority, fence users and revalidate task,
   host/engine, canonical paths, current head, merge or delivery evidence, data inventory
   and exact resource identities under that authority. Recopy changed evidence
   or data before proceeding. If a writer cannot be fenced, retain the targets.
3. Stop only verified task-owned services through their actual owners. Preserve
   needed evidence and data outside every resource scheduled for disposal;
   check preservation succeeded. Keep recovery configuration and credentials
   available through the owner's secure mechanism until recovery is finished.
4. Retire exact resources declared disposable through their real owners.
   Journal each result durably. Remove the worktree and its registration
   through the allocator. Remove its branch separately only after checking
   integration, unpublished work and other worktree use. Do not force removal
   or use broad prune operations.
5. Verify absence on each actual target and consistency of allocator/resource
   metadata. Persist a tombstone before releasing retirement authority. Keep
   the journal until cleanup is verified; retain evidence under its policy.

On partial failure, preserve the journal, mark pending and retry only remaining
effects after reacquiring authority and revalidating identities. A missing
resource is success only when its recorded identity and owner metadata agree;
an unavailable endpoint is not absence. Repeated retirement must converge
without touching reused names or unrelated state. A retired task cannot resume
against deleted state; new allocation needs a new recorded identity.

Unreachable machines, unavailable owners and unsupported fencing leave work
pending or retained. Ask a human only for unresolved disposal or authority,
with the relevant evidence; do not repeatedly request approval for work already
authorized. Routine reconciliation should use the owner's existing controls.

## Docker, shared storage and remote workspaces

Before any Docker effect, verify the exact endpoint and daemon identity as well
as container, image and volume IDs against the creation record. Labels
corroborate ownership; they are not sole proof. Inspect all consumers, including
stopped containers. Retain shared tags and image digests used by other work;
do not infer exclusivity from a task-specific tag.

Disposability must have been declared at creation. Stopped, dangling or unused
state alone never establishes disposal authority. Persistent and unknown
volumes must never be automatically deleted. Preserve named databases and
their backing storage until their own data policy is satisfied.

Shared caches and pools have a separate quota/retention owner. Configure bounded
budgets per host for disposable workspaces/resources and shared storage, with
accounting that distinguishes them. Report unset budgets and pressure; do not
invent a TTL or delete unknown data to meet a budget. Retention policies need
an owner and preservation rules for idle, paused and review-needed work.

Cloud workspaces retire through the provider's actual owner and lifecycle
controls. Do not assume local Git/Docker APIs or local leases apply remotely.
Verify provider expiry and recovery limits before relying on saved task state.
Commit or export work and required evidence to durable storage outside the
expiring workspace before expiry, and verify readback from that storage.
Retaining a task record does not extend provider retention. Apply the identity,
exclusion, evidence and retry requirements to agent-controlled cleanup; when
those controls are unavailable, report provider-managed expiry separately from
verified owner retirement.

[OpenBot](https://github.com/nightly-labs/openbot) means nightly-labs/openbot.
Keep its persistent application state and credentials separate from disposable
T3 task worktrees; task completion never makes them disposable. Route engineering
delegation through the documented native T3 controls where supported. Fleet
owns machine-specific installation, persistent paths and operating procedures.

## Reconciliation and implementation acceptance

The owner reconciles its records, real allocations/resources and disk accounting
across reachable hosts. Report orphaned or ambiguous objects for retention and
resolution. Periodic jobs or completion hooks may invoke owner reconciliation;
a hook firing is not proof of successful retirement. Record each target's
verified result and unresolved reason without declaring fleet-wide success
when a machine is unreachable.

A future integration must demonstrate at least these cases:

| Case | Required observation |
| --- | --- |
| Normal retirement and repeat | Only exact disposable targets disappear; registration agrees; repeat has no additional effects. |
| Paused workspace; retention policy expires | Ignored database, untracked notes and unpublished work survive unchanged; expiry triggers retention or a disposition decision, not deletion. |
| Completed non-merge work | Delivery to the intended durable target is verified; unique local deliverables and unpublished work remain reachable before disposable workspace retirement. |
| Squash merge plus later commit | Merge is recognized; later work remains reachable and retained. |
| Endpoint mismatch; shared/persistent resources | Wrong daemon is rejected; shared tags/digests, stopped consumers and persistent/unknown volumes survive. |
| Concurrent resume | Real acquisition is excluded during deletion, including stale holders; resume cannot use deleted state. |
| Partial failure and retry | Inject failure between effects; durable recovery removes only remaining eligible targets. |
| Provider expiry with uncommitted work | Commit/export outside the expiring workspace and verify readback; distinguish provider-managed expiry from verified retirement. |
| Absent owner or unsupported fencing | Retain targets, record a pending reason and claim no retirement; an unfenceable writer prevents deletion. |
| Interrupted allocation | Intent and real creation records recover partial identities without deleting ambiguous matches. |
| Read-only task; ordinary small fix | Read-only work leaves state unchanged; small fix reuses its scoped workspace without unnecessary allocation or approval. |

Run these through the actual allocator/resource owner in a proven disposable
environment, including real concurrency, failure injection and retry. Report
which hosts, providers and engines were exercised. Simulations and supplied
fixture owners can validate bounded outcomes, but cannot prove production
fencing, Docker safety, Cloud/OpenBot integration or automatic fleet cleanup.
Do not claim guidance improvement without a measured baseline comparison.
Revise this contract when actual owner capabilities or failure evidence change.
