---
name: follow-instructions
description: Route engineering work through the smallest applicable procedure and evidence gates.
---

# Follow instructions

Initialize once when catalog skills apply. Choose the procedure that reaches
the requested result; leaf skills must not call this coordinator recursively.
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
| Explicit bespoke composition | `custom/compose` | [custom](playbooks/custom.md) |
| Establish whether a claim is true | `verify-work/verify` | [verify-work](../verify-work/SKILL.md) |

Attach expertise only where it changes a decision: unclear causes use
[systematic-debugging](../systematic-debugging/SKILL.md); unclear boundaries use
[architect](../architect/SKILL.md); material review uses
[code-review-and-quality](../code-review-and-quality/SKILL.md); trust boundaries
use [security-and-hardening](../security-and-hardening/SKILL.md); production-like
state or credentials use [production-safety](../production-safety/SKILL.md);
real UI work uses [web-interface](../web-interface/SKILL.md). Use `how`, `why`,
`teach`, `deslop`, `unslop`, or [internet-reach](../internet-reach/SKILL.md) for
the corresponding requested deliverable, not incidental subject words.

Use the [principle index](references/principles.md) only for a material choice,
then read the relevant detail. Source context is optional:
[provenance](references/principles-background.md),
[case studies](references/case-studies.md), and
[observed failures](references/failure-to-checks.md).

## Effort and continuation

Keep only obligations that can change action, order, permission, stopping or
completion in the task record:
`Outcome / Route / Domains / Effects / Constraints / Done`.
A simple answer needs no formal record. Use current CLI/model settings; when
controls exist, start routine work at the configured ordinary effort and
escalate for demonstrated uncertainty. Do not change the user's model or quota
settings without authority, or claim a setting change that the harness cannot
make. Agree a finite experiment/retry budget for prolonged work.

Use [parallel](playbooks/parallel.md) only when independent ownership, a real
delegation tool and a benefit justify it. Prove one complete unit first. Use
[self-reflect](../self-reflect/SKILL.md) when repeated failure or stalled progress
requires a new observation; ordinary completion needs no extra reflection.
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
