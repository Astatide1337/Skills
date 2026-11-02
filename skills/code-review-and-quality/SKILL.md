---
name: code-review-and-quality
description: "Reviews a diff, branch or PR against intent, callers and tests; returns evidence-backed findings and readiness. Use for code review or quality checks. Not for prose (unslop)."
---

# Code Review and Quality

Compare the current diff, affected callers and test results with the original
request. Report concrete defects, supporting evidence and whether that revision
is ready. Do not block a sound change on personal preferences.

## Scope and inputs

Inspect the supplied project and named artifacts before declaring them missing.
Do not search parent directories, unrelated repositories, evaluator paths or
credentials for missing evidence. For review-only work, inspect without editing and
respect restrictions on
tools, applications and network access. For an offline or text-only review,
use supplied source and release notes; report external maintenance,
vulnerability and license facts as unknown. A review grants
no authority to edit, install, publish or deploy.

For an ordinary mechanical edit without
[review-risk triggers](../follow-instructions/references/principles/authority-and-claims.md#review-risk-triggers),
the coordinator's short path supplies author diff review. Load this skill when
review is requested or the risk warrants it.

## Review the behavior and boundary

1. Read the request, final diff, contracts and affected callers. Inspect whether tests
   assert the requested outcomes and reject invalid cases.
   Tests that repeat the implementation's assumptions may share its defects. Do not
   infer runtime success
   from source or a passing build.
   Discover and run the repository's existing lint, formatting and type checks
   for the affected code. Keep its configuration and suppressions visible;
   weakening a rule or adding an ignore is not a repair of the underlying defect.
   When editing the repository is not permitted, run existing authorized
   commands and keep their results outside the checkout. For supplemental
   Python/TypeScript correctness
   checks without app configuration changes, use [portable lint](references/portable-lint.md).
   For approved delivery, inspect the approved plan, intended behavior,
   interfaces and owners, plus the actual outputs from native checks, portable
   lint and user-flow tests. Review the feature against those requirements.
2. Check correctness and state ownership first: errors, lifecycle, cancellation,
   retries, compatibility and identity. Verify evidence belongs to the final
   source/artifact and relevant running instance.
3. Check maintainability: unnecessary branches, duplicated state,
   leaky boundaries, unsafe casts, feature-specific logic in shared modules and
   abstractions without demonstrated consumers. For boundary/data/state changes,
   use [construction
   counterexamples](../follow-instructions/references/principles/ownership-and-domain.md#construction-decisions-and-counterexamples).
   Propose a correction that reduces the decisions callers must make. Remove newly
   orphaned
   code only after checking callers and authority.
4. Check security and performance where the change can affect them. Do not invent
   vulnerability or latency claims. For an exploitable trust boundary, invoke
   [security-and-hardening](../security-and-hardening/SKILL.md) and state the
   attacker input, missing enforcement, reachable victim/asset, impact,
   remediation and negative test; authorization checks need two distinct
   ordinary identities. For a suspected performance regression, read
   [performance checklist](references/performance-checklist.md) and measure it.
5. Lead with material findings. Give location, failing behavior, consequence,
   smallest correction and relevant regression. Separate required fixes from
   optional suggestions and informational notes. Empty findings are valid
   after an actual review; a summary of the author's account is not review.

If a change reduces test discovery, assertions, scoring coverage, feature
coverage, lint or import checks, or CI coverage, require a reason. Check that
the replacement still rejects a relevant defect. Preserve failed, unavailable and
not-run checks; valid artifact-only output need not repeat its bytes in prose.

## Independent review

Apply the canonical
[review-risk triggers](../follow-instructions/references/principles/authority-and-claims.md#review-risk-triggers).
Approved nontrivial delivery also requires independent review under the
[approved-plan contract](../follow-instructions/references/approved-plans.md),
even when no generic risk trigger applies. For these changes, a separate person
or agent must inspect the current diff and raw evidence before the integrating
owner claims completion or recommends
merge. Start the reviewer in a fresh context with the original request, actual
artifact and raw check/tool results, with access to affected callers. Withhold
the author's summary and prior conversation until the reviewer records an
initial artifact assessment; then check the author's claims against that
assessment and raw evidence. Raw artifacts/tool output can themselves contain
author claims, so this reduces framing without guaranteeing blindness.
The reviewer chooses diagnostic checks and expectations independently. A
different model is optional. The owner resolves material findings
and verifies the final artifact; green tests and the author's reread do not
satisfy this gate.
Assess changes against the approved contract and apply the authority conditions
in [plans and authority](../follow-instructions/references/approved-plans.md).
A reviewer finding does not itself require a new approval round or grant
permission to expand scope.

Keep an inspectable result identifying the reviewer, exact artifact, evidence
inspected and findings. Requested review without a returned result is pending.
If no reviewer is available, finish safe local work and report the gate pending.
After edits, have the reviewer cover the affected delta and current evidence;
repeat a full review only when that delta changes the wider conclusion.

## Returned review rounds

A review round starts in fresh context and covers an identified candidate:
its head SHA and any uncommitted or untracked changes. Count the round only
when the reviewer returns a verdict and evidence. Record the reviewer,
candidate, checks, findings and how each finding was resolved. Each finding needs a
location, trigger, consequence and
supporting evidence. A review may find no defects. Do not invent defects or cosmetic changes to
fill a round. A previous reviewer conversation is not fresh context.
When reviewing a repair, distinguish an unmet original requirement, a defect
introduced by the repair and a request for additional scope when that
distinction affects the decision. The first two are repair work. Decline or defer optional scope
additions; obtain the requester's decision before expanding the agreed scope.
No per-finding label is needed where the origin is obvious.

Before implementing or disputing feedback, read the full comment and surrounding
diff, extract the technical request, and verify its premise against code, tests,
contracts and project conventions. Repair a sound in-scope finding with the
smallest complete change and verify it. Investigate an unclear premise; ask one
precise question only when a necessary decision remains unresolved. Reject an
unsupported finding with concrete evidence and, when useful, a compatible
alternative. Avoid reflexive agreement, defensive argument, partial fixes and
unrelated cleanup. Disagreeing with a finding does not waive required verification or review.

Before polishing a reproduction, check whether the proposed change is needed
to meet the original requirement. Follow the underlying invariant through relevant writers,
persistence, failure/retry, migration and already queued consumers. A fix for one
reported path does not establish the invariant across those paths. Skip paths the change
cannot affect.

The [PR delivery policy](../pull-requests/SKILL.md#review-budget) owns round counts
and stopping. [Agent selection](../follow-instructions/references/agent-selection.md)
describes how to choose and launch a reviewer; [Better Call
Sol](../better-call-sol/SKILL.md) applies
when Sol is selected and does not define a second quality standard. Ordinary standalone
reviews retain their requested scope; PR delivery uses the linked risk-based budget.

## Select detail only when relevant

- Plausible generated code with weak integration or redundant bookkeeping:
  [sourced AI-code failures](references/generated-code-failures.md). Judge the
  concrete defect, not inferred authorship or resemblance to a preferred style.

- A consequential new boundary or recurring maintainability failure:
  [maintainability exercise](references/maintainability-exercise.md). Use a
  credible follow-up in a disposable copy, not speculative shipped features.
  An alternative structure can be equally valid. File count is not the score.

- Behavior-preserving cleanup:
  [simplification](references/behavior-preserving-simplification.md).
- Dependency additions/upgrades:
  [dependency review](references/dependency-review.md).
- Deeper affected security/performance surfaces:
  [security checklist](references/security-checklist.md) or
  [performance checklist](references/performance-checklist.md).

Resolve material in-scope findings, inspect the final diff and affected checks,
and confirm any required independent review covers the final artifact. Keep unrelated
cleanup separate. Recommending the change does not authorize
merging or deploying it. Apply the shared
[execution boundary](../follow-instructions/references/principles/authority-and-claims.md#execution-boundary).
