---
name: code-review-and-quality
description: When reviewing a diff or a material code change.
---

# Code Review and Quality

Review the original request, current diff, affected callers and verification
against the intended behavior. Return concrete findings, evidence and readiness
at the reviewed artifact. Prefer a change that improves code health over
blocking on personal preferences or perfection.

## Scope and inputs

Inspect the supplied project and named artifacts before declaring them missing.
Do not search parent directories, unrelated repositories, evaluator paths or
credentials for missing evidence. Review-only permits read-only inspection;
an explicit tool/application/network prohibition still applies. Offline or
text-only reviews use supplied source and release notes, with external
maintenance, vulnerability and license facts reported unknown. A review grants
no authority to edit, install, publish or deploy.

For an ordinary mechanical edit without
[review-risk triggers](../follow-instructions/references/principles/authority-and-claims.md#review-risk-triggers),
the coordinator's short path supplies author diff review. Load this skill when
review is requested or the risk warrants it.

## Review the behavior and boundary

1. Read the request, final diff, contracts and affected callers. Inspect tests
   for literal expected outcomes and meaningful negative cases; tests repeating
   implementation assumptions are weak evidence. Do not infer runtime success
   from source or a passing build.
2. Check correctness and state ownership first: errors, lifecycle, cancellation,
   retries, compatibility and identity. Verify evidence belongs to the final
   source/artifact and relevant running instance.
3. Check design and maintainability: unnecessary branches, duplicated state,
   leaky boundaries, unsafe casts, feature-specific logic in shared modules and
   abstractions without demonstrated consumers. Propose a concrete remedy that
   removes decisions rather than relocating complexity. Remove newly orphaned
   code only after checking callers and authority.
4. Screen security and performance only at affected boundaries. Do not invent
   vulnerability or latency claims. For an exploitable trust boundary, invoke
   [security-and-hardening](../security-and-hardening/SKILL.md) and state the
   attacker input, missing enforcement, reachable victim/asset, impact,
   remediation and negative test; authorization checks need two distinct
   ordinary identities. For a suspected performance regression, read
   [backend performance](references/backend-performance.md) and measure it.
5. Lead with material findings. Give location, failing behavior, consequence,
   smallest correction and relevant regression. Separate required fixes from
   optional suggestions and informational notes. Empty findings are valid
   after an actual review; a summary of the author's account is not review.

When discovery, assertions, scoring, a feature map, lint/import boundaries or
CI configuration lose coverage, require an explicit reason and a violating
fixture before accepting the replacement. Preserve failed, unavailable and
not-run checks; valid artifact-only output need not repeat its bytes in prose.

## Independent review

Apply the canonical
[review-risk triggers](../follow-instructions/references/principles/authority-and-claims.md#review-risk-triggers).
For those changes, a separate person or agent must inspect the current diff
and evidence before the integrating owner claims completion or recommends
merge. A different model is optional. The owner resolves material findings
and verifies the final artifact; green tests and the author's reread do not
satisfy this gate.

Keep an inspectable result identifying the reviewer, exact artifact, evidence
inspected and findings. Requested review without a returned result is pending.
If no reviewer is available, finish safe local work and report the gate pending.
After edits, have the reviewer cover the affected delta and current evidence;
repeat a full review only when that delta changes the wider conclusion.

## Select detail only when relevant

- Review comments to implement or dispute:
  [review feedback](references/review-feedback.md). Verify the premise first;
  technical evidence outranks preference. A judgment override does not waive
  required verification or independent review.
- Behavior-preserving cleanup:
  [simplification](references/behavior-preserving-simplification.md).
- Dependency additions/upgrades:
  [dependency review](references/dependency-review.md).
- Deeper affected security/performance surfaces:
  [security checklist](references/security-checklist.md) or
  [performance checklist](references/performance-checklist.md).

Resolve material in-scope findings, inspect the final diff and affected checks,
and confirm any required independent review covers the final artifact. Keep
unrelated cleanup separate. A readiness recommendation does not authorize
merge or deployment. Apply the shared
[execution boundary](../follow-instructions/references/principles/authority-and-claims.md#execution-boundary).
