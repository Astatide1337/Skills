---
name: follow-instructions
description: "Use for substantial engineering work, unclear causes or consequential changes. Clear local corrections use the short path."
---

# Follow instructions

Choose a workflow once per task. Reconsider it when the requested outcome or
scope changes, not whenever another skill is loaded. Other skills must not call
this coordinator recursively. Read the repository instructions and apply the
[execution boundary](references/principles/authority-and-claims.md#execution-boundary).
Use the supplied skill path rather than guessing an install directory. Resolve
relative links from the directory containing the owning `SKILL.md`.

Keep the requested outcome, permitted actions, output format and acceptance
criteria through planning, delegation and handoff. Include them in worker
briefs and check the final result against them. Skills describe how to work;
they do not grant permission to edit, publish, merge or deploy. For conflicting
instructions or uncertainty about permission, use
[authority and claims](references/principles/authority-and-claims.md).

## Short task path

Inspect the implementation, caller and available check first. Use this path
when the intended behavior and responsible code are clear and no
[review-risk trigger](references/principles/authority-and-claims.md#review-risk-triggers)
applies. A small pure-function correction may qualify; line count alone does
not decide. Always honor explicit skill requests and repository procedures.

1. Establish the expected result. For a bug, reproduce the original failure.
2. Make the smallest authorized correction. Preserve negative cases.
3. Run the focused check on the final code and inspect the diff. Exercise the
   requested behavior; a build alone does not prove a user interaction works.
4. For local-only work, report the result and relevant limits, then finish.
   Otherwise follow [PR delivery](../pull-requests/SKILL.md#complete-authorized-delivery),
   including independent review. Reviewing your own diff does not replace it.

This path already covers diagnosis, verification and author review. Do not load
more procedures to repeat those steps. Local-only work without a review-risk
trigger needs no formal plan, invented alternatives, checkpoint, reflection or
independent reviewer. PR delivery still requires independent review. Switch to
the full route if the cause, ownership or check becomes unclear, evidence
contradicts the explanation, or a review-risk trigger appears. Keep required
checks and genuine blockers visible.

## Engineer, verify, improve

One engineer integrates the result. A fresh reviewer checks substantive work.
These responsibilities do not require a standing team of agents.

For implementation, understand the problem, choose the smallest complete change,
implement it, remove unnecessary code, verify it, obtain required review, repair
findings and rerun affected checks. Use [code cleanup](../code-review-and-quality/SKILL.md) before final verification
when the diff contains unnecessary code. Use `unslop` for substantial prose, preserving facts and
uncertainty. Before finishing, check that the result meets the request and that
each completion claim has evidence. Skip steps that do not apply to read-only,
plan-only or short-path work.

Requirements bind the result and permitted actions. Defaults allow a justified
alternative. Examples illustrate a decision; they do not require the same
architecture or visual style. Use existing tools for repeatable mechanical work
and judgment for choices that depend on context. Changing a method must not
weaken the task's acceptance criteria.

For a consequential choice, unclear quality standard or stalled approach, read
[engineering judgment](references/engineering-judgment.md). Load only material
that helps make the current decision.

## Route other work

Choose one primary route. Add a follow-on only for another requested deliverable.
Read that playbook and the domain skills needed for the work.

| Request | Route | Procedure |
| --- | --- | --- |
| Diagnosis or explanation | `investigate/read` | [investigate](playbooks/investigate.md) |
| Product problem, feature scope or acceptance | `design/plan` | [product](../product/SKILL.md) |
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


Use [systematic-debugging](../systematic-debugging/SKILL.md) for unclear causes,
[architect](../architect/SKILL.md) for unclear ownership or interfaces,
[code-review-and-quality](../code-review-and-quality/SKILL.md) for substantive
review, [security-and-hardening](../security-and-hardening/SKILL.md) for trust
boundaries, [production-safety](../production-safety/SKILL.md) for operational
state or credentials, and [web-interface](../web-interface/SKILL.md) for UI work.
Select `how`, `why`, `teach` and `unslop` for their requested outputs,
not incidental words in the task. If a task needs an unusual combination, use
existing methods in a temporary sequence; do not create a permanent framework.

For a difficult decision, consult the [principle index](references/principles.md)
or a relevant [worked example](references/case-studies.md).

## Authority and delivery

Use [plans and authority](references/approved-plans.md) for substantial implementation,
substantial design or an explicit approval requirement. Reuse authorization already given.
Implementation follows the user's standing PR-delivery policy unless a local-only
request or another restriction overrides it. Keep the original objective and
follow [delivery completion](../pull-requests/SKILL.md#complete-authorized-delivery).
Fix ordinary failed checks and in-scope findings; do not hand them back as finished
work. Read-only and local-only requests keep their own stopping conditions.

## Documentation boundary

Keep task notes, research, drafts, scripts and experiments in a temporary
workspace outside the project, for example:

```sh
mktemp -d "${TMPDIR:-/tmp}/agent-work.XXXXXX"
```

Choose the working method and scratch files within the task's existing
permissions; no extra approval is needed. Keep the project checkout for intended
deliverables. Add project documentation when requested, required by the repository,
or needed to keep existing instructions accurate after the change. Include what
a future reader needs to use or maintain the result. Comments should explain a
useful reason, invariant or constraint. Unless the user asks to version them,
keep one-off audits, experiment results and PR progress in task artifacts or the
PR. Keep reusable instructions in their owning skill and regression cases in
the test suite; do not turn the catalog into a history of its development.

Before handoff, remove scratch material and unnecessary work narration added by
this task. Preserve existing material and other people's edits. Use the checkpoint
procedure below when work must survive beyond temporary storage.

## Effort and continuation

For substantive work, use the existing task record:
`Outcome / Route / Domains / Effects / Constraints (including format) / Done`.
Include only facts that affect the next action, its order, permission or
completion. Link requirements, the current revision and uncommitted changes,
evidence and unresolved decisions there. A simple answer needs no formal record.

For authorized delegation, use [agent and reasoning selection](references/agent-selection.md).
Match the model and effort to the role, difficulty and available capabilities.
Keep the parent model, global settings and quota unchanged. Set a budget before
optional experiments; do not invent a small trial budget to stop authorized
delivery early.

For substantive work, discover the repository's
[codebase knowledge](references/codebase-knowledge.md) before planning or review.
Build missing knowledge during authorized implementation. Read-only work uses
existing knowledge or source search. Verify source links against the current tree.
A clear local correction does not need a repository-wide indexing pass.

When delegation is available, delegate context gathering and exploration to an
efficient model. Without it, perform bounded local investigation and record the
capability limit; ordinary work continues. Give it a
bounded question and require relevant source paths, revisions and missing
context. Keep architecture and subtle bug analysis with the frontier owner,
who checks the cited sources. Delegate browser work to a capable economical
model with the actual browser tools and image input. If that capability is
unavailable, record the limit and use the supported fallback; do not pretend
an API-only model inspected a screen. Children return work to the parent and
never delegate further.

When delegating independent units, use [parallel](playbooks/parallel.md) to
assign ownership and integrate the results. Prove one complete
unit first. Use [self-reflect](../self-reflect/SKILL.md) when repeated failure or
stalled progress calls for a different observation, not at every completion.
For a recorded or repeated mistake, use
[learn from repeats](../self-reflect/references/learn-from-repeats.md); apply its
proposed changes only with the user's approval.

Across handoff or compaction, retain the objective, accepted decisions, unfinished
checks, next action and exact blockers. Use
[durable checkpoints](references/durable-checkpoints.md) before an expected
interruption or when work outlives the session.

## Evidence and completion

Inspect the responsible code and authoritative inputs before changing behavior.
Reuse evidence only while the relevant source, environment, requirement, fixture
and tested artifact or instance remain unchanged. Rerun affected checks after a
change. Preserve original reproductions and negative cases. Distinguish passed,
failed, skipped and not-run checks. Investigate safe recovery before declaring a
capability unavailable; do not drop a required check because its tool is missing.

Validate machine-readable files you deliver with their parser or schema checker
after the last write. Passing tests on the inputs or generator do not establish
that the resulting file is valid.

Review the final result and affected consumers. Required independent review must
cover that result; self-review and an unanswered review request do not count.
When publication is authorized, inspect the remote object to verify the write.
Report the result, meaningful decisions, checks and limits supported by the
evidence. Stop before unrequested actions.
