---
name: follow-instructions
description: Use when a task activates another catalog skill or needs a tool, edit, external write, or completion claim. Classify the outcome, playbook, domains, and authority before acting; do not use for casual direct answers.
---

# Follow Instructions

Use this skill once as the task entry point. It selects a process, attaches
domain knowledge, and limits effects; it does not replace the owner skills.
Load the linked playbook and selected domain skills after classification. Do
not invoke `follow-instructions` recursively from a leaf skill.

For any request that needs a catalog workflow, include `follow-instructions` in
the selected skill set before its domain packages. Direct conceptual answers
remain the only bypass; selecting a domain package alone is not a substitute
for the coordinator.

## First classify the request

Parse the requested observable outcome, literal constraints, non-goals, source
or environment limits, requested artifact, and completion claim. Keep these
four dimensions separate:

| Dimension | Record | Examples |
| --- | --- | --- |
| Outcome and mode | One primary process | `investigate/read`, `implement/bug`, `review/rereview` |
| Domains | Peer expertise needed by the actual surface | `systematic-debugging`, `web-interface`, `security-and-hardening` |
| Follow-ons | Distinct requested deliverables in order | `issues/create`, `pull-requests/create` |
| Effects and authority | What may change, where, and why | workspace read; issue create; no PR/deploy |

Negative constraints win. A noun in the request does not grant access, a
review comment does not grant repair authority, and `allow_changes` concerns
workspace state only. Missing capability remains unavailable; it is not
silently treated as “not applicable.”

## Choose the lightest sufficient route

Select by the requested action and evidence, not by every subject mentioned.
Use one primary process for one outcome; add a follow-on only for a separate
deliverable. Add a `parallel` modifier only when independent work is useful
and the delegation tool and ownership boundary are real.

Keep the family and mode separate in a route record: `issues` + `draft`, not a
slash-qualified primary. A draft is copy only: `draft a PR/MR` selects
`pull-requests/draft`, while `open` or `create a draft PR/MR` selects
`pull-requests/create`; the verb is decisive. **Never downgrade an explicit
`open`, `create`, or `file` request to `pull-requests/draft` merely because the
requested remote artifact is marked draft.** The installed `pull-requests` skill
accompanies a PR/MR route; playbook names such as `issues` are not top-level
skills unless an installed package owns them. Publication read-back belongs to
its lifecycle route and does not automatically add `verify-work`; use that
domain for a separately requested claim or current-behavior check. Never put
`verify-work` in `follow_ons`; it is a domain entry. Keep `pull-requests` as the
lifecycle owner, not a peer domain, and do not add `pull-requests/monitor` merely
to read back a publication. Effects describe the requested operation, not this
classification-only response: an explicit production-like target permits
`production: read` for inspection even when mutation is prohibited; a fixture or
synthetic target has `production: none`. A resumed or interrupted **repair** is
still `implement/bug` with `workspace: write` when the corrected request retains
the repair, not a read-only route. Do not infer production authority from a
generic database, endpoint, or dependency mention: require an explicit live or
production-like boundary. `domains` names exact installed catalog packages; do
not invent labels such as `migration` or `backend` when no package owns that
name. An authorized synthetic or fixture incident is not a production effect
unless the request explicitly names a production-like target.

Keep the route fields internally consistent: every name in `domains` must also
appear in the selected catalog `skills` (and every selected non-coordinator,
non-lifecycle domain must be named in `domains`). `follow-instructions` is the
coordinator; `pull-requests` remains the lifecycle owner and is not a peer
domain.

Use the canonical route modes exactly as written in the table (`read`, `plan`,
`prototype`, `bug`, `feature`, `refactor`, `measure`, `improve`, `upgrade`,
`migrate`, `release`, `incident`, `review`, `rereview`, `draft`, `create`,
`monitor`, `communicate`, `verify`, `document`, `teach`, `improve`, or `compose`). Do not
replace a mode with a prose description. In particular, an unmatched but
authorized one-off process is `custom/compose`, not a free-form custom mode.

| Request shape | Primary route | Supporting playbook |
| --- | --- | --- |
| Read-only investigation, research, or explanation of an actual source | `investigate/read` | [investigate](playbooks/investigate.md) |
| Architecture, plan, or authorized isolated prototype | `design/plan` or `design/prototype` | [design](playbooks/design.md) |
| Fix a defect, add behavior, or preserve behavior while changing structure | `implement/bug`, `implement/feature`, or `implement/refactor` | [implement](playbooks/implement.md) |
| Measure or improve a performance problem | `performance/measure` or `performance/improve` | [performance](playbooks/performance.md) |
| Upgrade, migrate, release, or handle an incident | `migrate-operate/<mode>` | [migrate-operate](playbooks/migrate-operate.md) |
| Review, audit, or re-review a revision | `review/review` or `review/rereview` | [review](playbooks/review.md) |
| Establish whether a claim is true/current | `verify-work/verify` | [verify-work](../verify-work/SKILL.md) |
| Draft, create, update, or triage an issue | `issues/<mode>` | [issues](playbooks/issues.md) |
| Draft, create, monitor, or communicate on a PR/MR | existing `pull-requests/<mode>` | [pull-requests](../pull-requests/SKILL.md) |
| Explain source or produce documentation/teaching | `document-teach/document` or `document-teach/teach` | [document-teach](playbooks/document-teach.md) |
| Improve a reusable skill or workflow | `workflow-improvement/improve` | [create-workflow](../create-workflow/SKILL.md), [skill-creator](../skill-creator/SKILL.md) |
| Explicit bespoke task or no adequate composition | `custom/compose` | [custom](playbooks/custom.md) |

Plan-only migration uses `design/plan` with the applicable production and
security domains; it does not invent a `migrate-operate/plan` mode. A report or
handoff is not by itself a `document-teach` follow-on. Follow-ons name only a
distinct requested deliverable, and top-level `skills` contains installed
packages rather than playbook family names.

Direct conceptual questions, pasted-code answers, and ordinary drafting that
need no catalog workflow select no route. An unfamiliar language is still a
known task when its process is clear. A custom route is a last resort, not a
way around a failed safety or verification gate.

## Compose domains without granting effects

Attach only the expertise that owns a material decision. Typical attachments:

- causal bugs: [systematic-debugging](../systematic-debugging/SKILL.md);
- non-trivial boundaries: [architect](../architect/SKILL.md);
- quality or review: [code-review-and-quality](../code-review-and-quality/SKILL.md);
- secrets, auth, untrusted data, or agent boundaries: [security-and-hardening](../security-and-hardening/SKILL.md);
- production-like infrastructure, persistent data, or credentials: [production-safety](../production-safety/SKILL.md);
- incident mitigation followed by cause investigation: [systematic-debugging](../systematic-debugging/SKILL.md);
- source flow/history/teaching: `how`, `why`, or `teach` when separately requested;
- UI and real interactions: [web-interface](../web-interface/SKILL.md);
- external research: [internet-reach](../internet-reach/SKILL.md).

Domain knowledge does not authorize an operation. Keep specialized sensitive
procedures in their owner and preserve that owner's trigger. A production
plan, review-only request, or draft publication stops at its requested
boundary; merge and deploy remain separate explicit actions. The incident
route's default sequence is stabilize, then investigate the cause, so attach
`systematic-debugging` unless the request explicitly limits the work to
mitigation-only reporting.

## Initialize once and keep an instruction ledger

Before substantive action, read the global instructions, this skill, the
selected playbook, selected domain skills, and required references. Record
only obligations that can change permission, ordering, evidence, a stop
condition, or a completion claim:

`source · timing · pending/satisfied/not-applicable/blocked · concrete evidence`

Unknown is not “not applicable.” Reconcile the ledger when the user corrects
scope, a revision changes, a delegated artifact returns, or a task resumes.
Do not expose a full ledger for a trivial task unless an instruction blocks
progress or the user requests an audit.

The gates are ordered:

1. **Inspect:** identify the exact target, authoritative source, owner,
   callers, state, identities, and relevant filesystem/API boundaries.
2. **Causality/design:** state the current hypothesis or design choice, one
   plausible alternative, and the smallest observation that distinguishes
   them when behavior is unexplained. Do not patch an uninspected owner.
3. **Mutate:** confirm scope and authorization, affected consumers/writers,
   sensitive data, rollback, and the complete effect path before editing or
   writing externally. Never broaden secret access to resolve uncertainty.
4. **Publish:** inspect the final diff and current revision; run the relevant
   correctness, architecture, security, operational, and attribution checks;
   verify the remote artifact or submitted review after a write.
5. **Complete:** name the requested observable result and claim only what
   current evidence proves. Static structure or a green command is not runtime
   behavior.

For secrets, multiple processes, production-like state, or publication claims,
the handoff must include `Alternatives tested:`, `Boundary map:`, and `Effect
and evidence:` with unknowns named. Ordinary issue drafting or a direct answer
does not require a deployment-boundary report.

## Handle correction, recovery, and parallel work

If an obligation was skipped, stop mutation, name the risk, inspect existing
work for unsafe or misleading state, and revise or revert only within the
authorized scope. Do not defend a result because later evidence partly agrees.

Use [parallel](playbooks/parallel.md) only as a modifier to a valid primary
route. Establish shared interfaces and writers first; give each worker a
bounded input, owned files/resources, invariants, effects, and return artifact.
Inspect the actual returned diff or artifact and verify the integrated result.
If delegation is unavailable or coordination costs more than it saves, run
the same route sequentially without pretending parallelism occurred.

## Route notation

Keep the compact task record useful:

`Outcome / Route / Domains / Effects / Constraints / Done`

Example: `diagnose tenant lookup / investigate/read -> issues/create /
systematic-debugging / workspace read + supplied tracker issue-create /
no code edit, no PR / source finding, one issue fetched back, no unsupported
claim`.

Supporting procedures:

- [investigate](playbooks/investigate.md)
- [design](playbooks/design.md)
- [implement](playbooks/implement.md)
- [performance](playbooks/performance.md)
- [migrate-operate](playbooks/migrate-operate.md)
- [review](playbooks/review.md)
- [issues](playbooks/issues.md)
- [document-teach](playbooks/document-teach.md)
- [custom](playbooks/custom.md)
- [parallel](playbooks/parallel.md)
