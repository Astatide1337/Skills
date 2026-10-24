---
name: follow-instructions
description: "Selects the smallest workflow and supporting skills. Use whenever a catalog skill applies, including diagnosis, review, implementation, writing and retrospectives. Initialize once."
---

# Follow instructions

Initialize once when catalog skills apply. Choose the procedure that reaches
the requested result; leaf skills must not call this coordinator recursively.
Resolve each relative reference from the directory containing its owning
`SKILL.md`; use the supplied skill locator rather than guessing directories.
Read repository guidance and apply the shared
[execution boundary](references/principles/authority-and-claims.md#execution-boundary).
A skill supplies procedure, never permission to edit, publish, merge, or deploy.

## Short task path

First inspect the owner, caller and check to classify eligibility; a bug label
alone does not justify preloading diagnosis or verification skills, while
explicit skill requests and repository-required procedures apply immediately.

Use this inline procedure for a local task whose owner, intended behavior and
focused check are clear, provided the
[review-risk triggers](references/principles/authority-and-claims.md#review-risk-triggers)
are absent. An obvious pure-function correction can qualify; line count alone
cannot. Explicitly requested skills and repository-required procedures win.

1. Inspect the owner, relevant caller/contract and available check. Establish
   the expected result before editing. For a bug, observe the original failure.
2. Make the smallest authorized correction. Preserve existing negative cases.
3. Run the focused check on the final code and inspect the diff/scope. Exercise
   the actual requested path: a passing build cannot prove a user journey.
4. Report the observed result and material limits, then finish. A clean diff
   reread is author review, not independent review.

This path owns routine diagnosis, verification and diff review. Do not load
full playbooks, principle details or additional owner skills merely to repeat
these steps. No formal plan, competing hypotheses, durable checkpoint,
reflection or reviewer is required for this path. Escalate to the route below
if the cause, ownership or check becomes unclear, a check contradicts the
explanation, or a consequential boundary appears. Never use the short path to
skip a required check or silently downgrade a real blocker.

## Engineer, verify, improve

One engineer owns integration. A fresh reviewer challenges substantive work.
Improvement changes the reusable method, not the current task's acceptance.
These are responsibilities, not a mandatory agent roster.

Keep requirements, defaults and examples distinct. Requirements bind the result
and effects. Defaults may yield to a task-grounded better approach. Examples
illustrate judgment, not the only acceptable architecture or visual style.
Automate stable mechanics with existing tools, leaving contextual decisions to
the agent. A repeatable result is not necessarily correct.

For a consequential choice, unclear quality bar, or stalled approach, use
[engineering judgment](references/engineering-judgment.md). Do not load it for
an already-clear short-path edit. Select only resources that change a decision.

## Route other work

Keep outcome, supporting expertise, follow-ons and permitted effects separate.
Choose one primary route; add a follow-on for a distinct requested deliverable.
Read its playbook and only the domain skills owning material decisions.

| Request | Route | Procedure |
| --- | --- | --- |
| Diagnosis or explanation | `investigate/read` | [investigate](playbooks/investigate.md) |
| Architecture or authorized prototype | `design/plan` or `design/prototype` | [design](playbooks/design.md) |
| Bug, feature or refactor | `implement/bug`, `implement/feature`, `implement/refactor` | [implement](playbooks/implement.md) |
| Measure or improve performance | `performance/measure` or `performance/improve` | [performance](playbooks/performance.md) |
| Upgrade, migration, release or incident | `migrate-operate/<mode>` | [migrate-operate](playbooks/migrate-operate.md) |
| Review or re-review | `review/review` or `review/rereview` | [review](playbooks/review.md) |
| Issue draft/create/update/triage | `issues/<mode>` | [issues](playbooks/issues.md) |
| PR/MR lifecycle | `pull-requests/<mode>` | [pull-requests](../pull-requests/SKILL.md) |
| Documentation or teaching | `document-teach/document` or `document-teach/teach` | [document-teach](playbooks/document-teach.md) |
| Reusable workflow/skill improvement | `workflow-improvement/improve` | [create-workflow](../create-workflow/SKILL.md), [skill-creator](../skill-creator/SKILL.md) |
| Establish whether a claim is true | `verify-work/verify` | [verify-work](../verify-work/SKILL.md) |

Attach expertise only where it changes a decision: unclear causes use
[systematic-debugging](../systematic-debugging/SKILL.md); unclear boundaries use
[architect](../architect/SKILL.md); material review uses
[code-review-and-quality](../code-review-and-quality/SKILL.md); trust boundaries
use [security-and-hardening](../security-and-hardening/SKILL.md); production-like
state or credentials use [production-safety](../production-safety/SKILL.md);
real UI work uses [web-interface](../web-interface/SKILL.md). Use `how`, `why`,
`teach`, `deslop`, or `unslop` for the corresponding requested deliverable,
not incidental subject words. For a bespoke task, compose the closest existing
methods in a temporary sequence in this task record; do not create a new playbook
or persistent framework merely because the combination is unfamiliar.

Use the [principle index](references/principles.md) only for a material choice,
then read the relevant detail. Source context is optional:
[provenance](references/principles-background.md),
[case studies](references/case-studies.md), and
[observed failures](references/failure-to-checks.md).

## Authority and delivery

Use [plans and authority](references/approved-plans.md) for a substantial design
or an explicit approval gate. Reuse authorization already given. Keep required
outcomes, preferred methods and illustrative examples distinct; choose a justified
alternative when the default does not fit.

When implementation and PR/MR delivery are authorized, retain the original objective
and follow [delivery completion](../pull-requests/SKILL.md#complete-authorized-delivery).
Ordinary failed checks and in-scope findings create the next engineering action.
Read-only requests and local-only changes retain their own stopping conditions.

## Documentation boundary

When you need working files, create a task-specific temporary workspace outside
the project, for example with `mktemp -d "${TMPDIR:-/tmp}/agent-work.XXXXXX"`.
Use it freely for notes, research, plans, drafts, scripts, and experiments that
support the task. Choose the working method and artifacts yourself; routine
scratch work needs no additional permission within the task's existing authority.
Keep the project checkout for implementation and intended deliverables. Move
material into project docs when the user requests it, a repository requirement
applies, or changed behavior would otherwise leave existing instructions wrong.
Include only what a future reader needs to use or maintain the result. Source
comments should explain a useful reason, invariant, or constraint. Before
handoff, inspect the diff for scratch material and unnecessary narration from
your work; preserve existing and independently edited material. Use the existing
checkpoint procedure when work needs durable continuation beyond temporary storage.

## Effort and continuation

Keep only obligations that can change action, order, permission, stopping or
completion in the task record:
`Outcome / Route / Domains / Effects / Constraints / Done`.
For substantive work, link authoritative inputs, acceptance, candidate identity,
current evidence and unresolved decisions in that same record, not a new ledger.
A simple answer needs no formal record. Use current CLI/model settings; when
controls exist, start routine work at the configured ordinary effort and
escalate for demonstrated uncertainty. Do not change the user's model or quota
settings without authority, or claim a setting change that the harness cannot
make. Bound optional experiments and comparisons before running them; do not invent a
tiny budget as a stopping condition for already-authorized delivery.

Use [parallel](playbooks/parallel.md) only when independent ownership, a real
delegation tool and a benefit justify it. Prove one complete unit first. Use
[self-reflect](../self-reflect/SKILL.md) when repeated failure or stalled progress
requires a new observation; ordinary completion needs no extra reflection.
A correction of a recorded or repeated mistake uses
[learn from repeats](../self-reflect/references/learn-from-repeats.md); nothing
is applied without the user's approval.
Across handoff or compaction retain the objective, accepted decisions,
unfinished gates, next action and exact blockers. Use
[durable checkpoints](references/durable-checkpoints.md) for expected
interruption or work outliving the session, not every edit.

## Evidence and completion

Inspect the actual owner and authoritative inputs before changing behavior.
Reuse evidence only while relevant source, environment, requirement, fixture
and artifact/instance identity are unchanged; rerun affected checks after a
change. Preserve original reproducers and negative cases. Distinguish accepted,
failed, skipped and not-run checks. Diagnose safe recovery before declaring a
capability blocker; missing capability is unavailable, not silently inapplicable.

Review the final artifact and affected consumers. Required independent review
must cover that artifact; self-review or a requested-but-unreturned review does
not satisfy it. Inspect remote results only when publication was requested and
verify the actual write. Report the result, meaningful decisions, checks and
material limits at the layer proven. Stop before unrequested effects.
