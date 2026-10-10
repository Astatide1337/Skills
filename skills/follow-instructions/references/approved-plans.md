# Approved engineering plans

Use for nontrivial feature or issue implementation after inspecting the actual
codebase. This is the coordinator's approval and continuation contract, not a
new workflow engine. Direct user and specific repository instructions win.
Read-only diagnosis, research and review remain read-only. A mechanical local
correction eligible for the coordinator's short path needs no HTML cycle.

## Investigate and present

Inspect the current revision, owners, conventions, callers, configuration,
tests and execution environment before choosing a design. For a bug, state the
evidenced root cause and desired behavior; preserve uncertainty when causation
is unproven. For exploration, present viable options, a recommendation and
material unknowns before asking the user to choose.

Use [html-artifacts](../../html-artifacts/SKILL.md) to produce one scannable
approval document containing:

- objective, requirement IDs, acceptance, exclusions and source findings;
- realistic caller flow, proposed types/interfaces, file placement and owners;
- chosen shape, rejected alternatives and proposed refactors with their purpose;
- integration sequence, edge/failure cases and independently expected checks;
- permitted effects, prerequisites, migration/rollback and unresolved facts.

Resolve material unknowns before dependent implementation. A relevant UI
decision also needs a clickable prototype using the application's actual
components and conventions in an isolated copy or authorized preview, with
reachable loading, empty, error and success states where applicable. Follow
[UI prototyping](../../web-interface/references/ui-prototyping.md); link that
preview from the document. A standalone imitation cannot prove the real
components or satisfy this gate. Label any unavailable preview as pending.

## Approval identity

Keep approval context in the existing task record, outside the app checkout
where practical: original objective and requirement IDs; repository/base
identity; HTML/prototype paths, version and digest; approved behavior,
interfaces and owners; exclusions and permitted effects; the exact user
confirmation; outstanding evidence gates. No approval database is needed.

Present the complete reviewable result before requesting a version-specific
greenlight. A rendered plan, navigation click, sample state or downloaded
checklist grants no authority. Reuse an existing explicit confirmation when it
covers this version and scope; do not ask twice. Clarify a confirmation whose
referent cannot be established. Investigation, authorized prototypes and safe
equivalent checks can continue while dependent implementation waits.

Record later approvals as explicitly superseding earlier ones. Keep approval
provenance distinct from author notes and check results. Use
[durable checkpoints](durable-checkpoints.md) when continuation needs to survive
interruption; its existing schema is sufficient.

## Continue the approved work

After greenlight, own the whole agreed result: implementation, affected real
journeys and native checks, supplemental checks, independent artifact review,
in-scope corrections, affected rechecks and a final scoped commit when included
in the approved delivery. Resolve the app's actual deterministic tools through
[verify-work](../../verify-work/SKILL.md), including installed per-app CLIs
where they apply. A build or simulated adapter cannot replace the requested
journey. Keep accepted, failed, skipped, unavailable and not-run results visible.

Push and PR/MR effects must be covered by the approved delivery when needed for
CI. Use [pull-requests](../../pull-requests/SKILL.md), inspect workflows before
push, and preserve explicit build/deployment prohibitions. Create the review
artifact as a draft, resolve in-scope findings and inspect current-head required
CI and mergeability before marking it ready for human review/merge. Never merge
or enable auto-merge as part of this delivery. Preserve unrelated user work.
If publication is excluded, report local readiness and the unproven remote gate.

## Materiality and recovery

Reviewer-driven simplification may remove decisions or duplication while
preserving approved behavior, interfaces, ownership, effects and acceptance.
The author assesses the request; review feedback is not authority. A material
architecture, public-contract, ownership, scope or verification change needs a
revised HTML plan and renewed confirmation before dependent work resumes.

When new evidence invalidates the plan, retain the discovery and its source,
stop dependent implementation and revise the affected plan. Continue independent
authorized work. Do not reinterpret acceptance or hide the discovery behind a
workaround. Use [self-reflect](../../self-reflect/SKILL.md) for repeated failure
or a stall: preserve the plan, failures, changes and unfinished checks, then
obtain one fresh diagnostic/review handoff when available. Its purpose is a
discriminating next action, not a mandatory committee for ordinary progress.

Before declaring a blocker, inspect the dependency, try safe supported
alternatives/equivalent checks and repair recoverable setup within authority.
Record what each proves and the remaining gap. Do not weaken verification,
bypass access or chain irreversible changes to remove a blocker. Existing
infrastructure/container approval boundaries still apply. Unavailable independent
review or CI remains an unfinished gate, even after useful local work is done.

## Completion and examples

Report the approved result, exact final artifact/revision, review evidence,
affected check results and any remaining gate. Readiness requires review and
checks for the current head; stale evidence and a local commit do not establish
remote readiness. After edits, refresh affected checks and reviewer coverage.

- **Success:** the user confirms plan v2 for a filter feature and draft PR.
  Implement all approved states, exercise the actual app, obtain independent
  review, fix in-scope findings and inspect CI at the final pushed head. Return
  the ready PR for human merge without merging it.
- **Changed plan:** a reviewer proposes replacing the approved public API.
  Show the revised interface and effects in v3; wait for confirmation before
  implementing that change. A duplicate private helper can be removed in scope.
- **Material discovery:** a test reveals that the proposed owner cannot enforce
  tenant isolation. Preserve the failing case, reopen that design decision and
  continue unrelated approved units while the revision awaits confirmation.
- **Tiny change:** an obvious pure-function correction has a clear owner,
  preserved interface, focused regression and no review-risk trigger. Use the
  short path; reclassify if inspection reveals a consequential boundary.
