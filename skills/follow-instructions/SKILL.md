---
name: follow-instructions
description: Route substantive work through the applicable skills and evidence gates.
---

# Follow instructions

Use this skill once as the entry point for substantive engineering work. It
chooses a playbook, attaches only the domain skills that own the decisions,
and keeps authority and evidence visible. A leaf skill must not call this
skill recursively.

## Start with a proportionate task record

Record only items that can change an action, ordering, permission, stop
condition, or completion claim:

`Outcome / Route / Domains / Effects / Constraints / Done`

Read repository guidance and the selected playbook/domain skills before
substantive work. Reconcile the record when the user changes scope, a
revision changes, a delegated artifact returns, or the task resumes. A simple
answer or small explanation does not need a formal record.

## Choose the route

Keep the task outcome, supporting expertise, follow-ons, and permitted effects
separate. A skill name does not grant an effect. Negative constraints win.
Missing capability is unavailable, not silently “not applicable.” Use one
primary route and add a follow-on only for a distinct requested deliverable.

| Request | Route | Playbook |
| --- | --- | --- |
| Read-only diagnosis or explanation | `investigate/read` | [investigate](playbooks/investigate.md) |
| Architecture decision or plan | `design/plan` | [design](playbooks/design.md) |
| Authorized disposable experiment | `design/prototype` | [design](playbooks/design.md) |
| Defect, feature, or behavior-preserving structure change | `implement/bug`, `implement/feature`, or `implement/refactor` | [implement](playbooks/implement.md) |
| Performance baseline or measured improvement | `performance/measure` or `performance/improve` | [performance](playbooks/performance.md) |
| Upgrade, migration, release, or incident | `migrate-operate/<mode>` | [migrate-operate](playbooks/migrate-operate.md) |
| Review or re-review | `review/review` or `review/rereview` | [review](playbooks/review.md) |
| Issue draft/create/update/triage | `issues/<mode>` | [issues](playbooks/issues.md) |
| PR/MR lifecycle | existing `pull-requests/<mode>` | [pull-requests](../pull-requests/SKILL.md) |
| Documentation or teaching | `document-teach/document` or `document-teach/teach` | [document-teach](playbooks/document-teach.md) |
| Reusable workflow/skill improvement | `workflow-improvement/improve` | [create-workflow](../create-workflow/SKILL.md), [skill-creator](../skill-creator/SKILL.md) |
| Explicit bespoke composition | `custom/compose` | [custom](playbooks/custom.md) |

Use `verify-work/verify` as a primary route when the requested result is to
establish whether a claim is true. It is a domain package, not an issue or PR
follow-on. Use [parallel](playbooks/parallel.md) only as a modifier when
independent work, bounded ownership, and a real delegation tool exist.

Use [self-reflect](../self-reflect/SKILL.md) as a modifier when work is stuck,
prolonged, or settling. It reassesses the current route from evidence; it does
not replace the task playbook or grant another effect.

Attach expertise only for a material decision:

- causal bugs: [systematic-debugging](../systematic-debugging/SKILL.md);
- unclear boundaries: [architect](../architect/SKILL.md);
- quality/review: [code-review-and-quality](../code-review-and-quality/SKILL.md);
- secrets, identity, or untrusted data: [security-and-hardening](../security-and-hardening/SKILL.md);
- production-like state or credentials: [production-safety](../production-safety/SKILL.md);
- real UI interaction: [web-interface](../web-interface/SKILL.md);
- generated-code cleanup: [deslop](../deslop/SKILL.md); prose rewrites:
  [unslop](../unslop/SKILL.md);
- source flow/history/teaching: `how`, `why`, or `teach` when requested;
- external primary-source research: [internet-reach](../internet-reach/SKILL.md).

## Apply principles when their trigger is present

Read the index in [principles](references/principles.md), then load only the
linked detailed principle reference(s) whose trigger is present. Load the
existing owner skill for the decision as well. A principle changes a choice;
it is not a completion-report checklist.

| Trigger | Decision rule | Owner |
| --- | --- | --- |
| Scope or new moving parts | Solve the stated outcome with the simplest sufficient existing shape. | [create-workflow](../create-workflow/SKILL.md) |
| Shared state or interface | Establish data, callers, lifetime, and ownership before changing the owner. | [architect](../architect/SKILL.md) |
| Debugging | Preserve the failure, compare hypotheses, and test the responsible mechanism. | [systematic-debugging](../systematic-debugging/SKILL.md) |
| User/maintainer trade-off | Prefer a smaller understandable result and exercise relevant states. | [web-interface](../web-interface/SKILL.md), [teach](../teach/SKILL.md) |
| Consequence or uncertainty | Scale investigation, review, recovery, and evidence to the risk. | [production-safety](../production-safety/SKILL.md), [verify-work](../verify-work/SKILL.md) |
| Independent delegation | Split interfaces and writers first, then inspect and integrate returned work. | [parallel](playbooks/parallel.md) |
| Repeated failed approach | Revisit the shared premise before adding machinery. | [grilling](../grilling/SKILL.md) |

See [public case studies](references/case-studies.md) only when a decision
matches one of their triggers. They are source-grounded contrasts, not a
required reading curriculum.

## Pass the evidence gates

1. **Inspect.** Identify the exact target/revision, authoritative source,
   owner, callers, state, identities, and relevant filesystem/API boundary.
   Label observations, assumptions, and hypotheses separately.
2. **Causality or design.** State the current mechanism or design choice and
   one plausible alternative when uncertainty is material. Run the smallest
   authorized observation that distinguishes them. Do not patch an uninspected
   owner.
3. **Mutation.** Confirm exact authorization, affected consumers/writers,
   sensitive data, rollback, and final scope. Do not broaden secret access to
   resolve path or ownership uncertainty.
4. **Publication.** Inspect the complete diff/current revision, run relevant
   correctness/security/operational checks, and verify the actual remote write
   when publication was requested. Drafting is not creating; readiness is not
   merging or deploying.
5. **Completion.** Name the requested observable result, show evidence at the
   relevant layer, list material unknowns, and narrow the claim to what the
   evidence proves. A build, manifest, command exit, or model prose is not
   runtime proof by itself.

For secrets, multiple processes, production-like state, or a consequential
external write, report the boundary and effect only to the detail that changes
the decision. Ordinary publication does not require a fixed “alternatives,
boundary, and effects” template.

## Work, recover, and hand off

Follow the selected playbook's mode-specific inputs, decisions, recovery, and
completion evidence. Reuse valid evidence until the relevant code, environment,
or requirement changes. Preserve original regressions and negative cases. If a
required input or capability is unavailable, finish independent safe work and
name the exact blocker; never manufacture evidence or weaken acceptance.

Return the result, changed owner, meaningful design choices, actual checks,
publication/readback state when requested, and material limitations. Explain
only the principles that changed a decision. Keep temporary bespoke sequences
temporary, and stop before unrequested mutation.

## Playbooks

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
